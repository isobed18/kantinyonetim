from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem
from apps.stock.models import Stock
from apps.menu.models import MenuItem
from apps.users.utils import log_user_action

class OrderItemReadSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'price_at_order_time', 'line_total']

    def get_line_total(self, obj: OrderItem):
        try:
            return (obj.price_at_order_time or Decimal('0')) * obj.quantity
        except Exception:
            return Decimal('0')


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemReadSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'user_username', 'status', 'created_at', 'updated_at', 'order_items', 'total','notes']
        extra_kwargs = {
            'user': {'read_only': True},
        }

    def get_total(self, obj: Order):
        total = Decimal('0')
        for item in obj.order_items.all():
            price = item.price_at_order_time or Decimal('0')
            total += price * item.quantity
        return total


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'
        extra_kwargs = {
            # input icin zorunlu degil ama admin/staff yazarsa override eder yeni fiyat olur indirim vb icin
            'price_at_order_time': {'required': False},
        }

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        role = getattr(user, 'role', 'customer') if user and getattr(user, 'is_authenticated', False) else 'customer'

        # sahiplik kontrolu: musteriler sadece kendi orderlarina ekleyebilir
        order = attrs.get('order') or (getattr(self, 'instance', None).order if getattr(self, 'instance', None) else None)
        if order is None:
            raise serializers.ValidationError({'order': 'Order is required.'})
        if role not in ['staff', 'admin']:
            if not user or order.user_id != user.id:
                raise serializers.ValidationError({'order': 'You can only modify items for your own order.'})

        # lifecycle lock: order degistirilemez durumdaysa add/update yapmaya izin vermeme
        order_status = getattr(order, 'status', None)
        if order_status not in ['pending', 'preparing']:
            raise serializers.ValidationError({'order': f'Cannot modify items when order status is {order_status}.'})

        menu_item = attrs.get('menu_item') or getattr(getattr(self, 'instance', None), 'menu_item', None)
        quantity = attrs.get('quantity')
        if menu_item and quantity is not None:
            try:
                stock = Stock.objects.get(menu_item=menu_item)
                # On update, consider previous quantity
                existing_qty = getattr(self.instance, 'quantity', 0) if self.instance else 0
                delta = quantity - existing_qty
                if delta > 0 and stock.quantity < delta:
                    raise serializers.ValidationError({'quantity': f'Insufficient stock for {menu_item.name}.'})
            except Stock.DoesNotExist:
                raise serializers.ValidationError({'quantity': f'No stock information for {menu_item.name}.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        menu_item: MenuItem = validated_data['menu_item']
        quantity: int = validated_data['quantity']
        stock = Stock.objects.select_for_update().get(menu_item=menu_item)
        if stock.quantity < quantity:
            raise serializers.ValidationError({'quantity': 'Insufficient stock.'})
        # price karari icin snapshot: admin/staff icin override kararı, defaultı menu price
        role = getattr(getattr(request, 'user', None), 'role', 'customer') if request else 'customer'
        override_price = validated_data.pop('price_at_order_time', None)
        if role in ['staff', 'admin'] and override_price is not None:
            # normalize price ve dogrulama
            if not isinstance(override_price, Decimal):
                try:
                    override_price = Decimal(str(override_price))
                except Exception:
                    raise serializers.ValidationError({'price_at_order_time': 'Invalid price format.'})
            if override_price < 0:
                raise serializers.ValidationError({'price_at_order_time': 'Price must be non-negative.'})
            validated_data['price_at_order_time'] = override_price
        else:
            # staff/admin olmayan herkesin gonderdigi fiyati gormezden gel
            validated_data['price_at_order_time'] = menu_item.price

        # varsa varolan line ile birlestir. unique order line
        existing = OrderItem.objects.select_for_update().filter(order=validated_data['order'], menu_item=menu_item).first()
        if existing:
            # varolan snapshotla cakisiyor mu check
            new_price = validated_data['price_at_order_time']
            if new_price != existing.price_at_order_time and role in ['staff', 'admin']:
                raise serializers.ValidationError({'price_at_order_time': 'Line exists; adjust price via update first.'})
            
            # toplam quantityi guncellemeden once kontrol et
            combined_quantity = existing.quantity + quantity
            if stock.quantity < combined_quantity:
                raise serializers.ValidationError({'quantity': 'Insufficient stock for combined quantity.'})

            existing.quantity = combined_quantity # birlestirilmis quantityi assign et
            existing.save(update_fields=['quantity'])
            # stocktan dusme
            stock.quantity -= quantity
            stock.save()
            return existing

        order_item = super().create(validated_data)
        # stocktan dusme
        stock.quantity -= quantity
        stock.save()
        # orderitem creationını
        # The order total is automatically updated by signals after order item save
        log_user_action(
            user=request.user, # The user who initiated the order item creation
            action='order_item_added',
            resource_type='order_item',
            resource_id=order_item.id,
            details={
                'order_id': order_item.order.id,
                'menu_item': order_item.menu_item.name,
                'quantity': order_item.quantity,
                'price': str(order_item.price_at_order_time),
                'line_total': str(order_item.line_total),
                'order_total_after_add': str(order_item.order.total) # Log the updated order total
            },
            request=request
        )
        return order_item

    def update(self, instance, validated_data):
        request = self.context.get('request')
        
        # Disallow changing the parent order reference via update
        if 'order' in validated_data:
            raise serializers.ValidationError({'order': 'Changing the order reference is not allowed.'})
        new_menu_item = validated_data.get('menu_item', instance.menu_item)
        if new_menu_item and not new_menu_item.is_available:
            raise serializers.ValidationError({'menu_item': 'This item is not available.'})
        new_quantity = validated_data.get('quantity', instance.quantity)

        # Lifecycle lock: disallow update when order not modifiable
        if instance.order.status not in ['pending', 'preparing']:
            raise serializers.ValidationError({'order': f'Cannot modify items when order status is {instance.order.status}.'})

        if new_menu_item == instance.menu_item:
            # Adjust stock based on quantity delta
            delta = new_quantity - instance.quantity
            if delta != 0:
                stock = Stock.objects.select_for_update().get(menu_item=new_menu_item)
                if delta > 0 and stock.quantity < delta:
                    raise serializers.ValidationError({'quantity': 'Insufficient stock.'})
                stock.quantity -= delta
                stock.save()
        else:
            # Return previous quantity to old stock, deduct from new stock
            old_stock = Stock.objects.select_for_update().get(menu_item=instance.menu_item)
            new_stock = Stock.objects.select_for_update().get(menu_item=new_menu_item)
            # Return old
            old_stock.quantity += instance.quantity
            # Deduct new
            if new_stock.quantity < new_quantity:
                raise serializers.ValidationError({'quantity': 'Insufficient stock for the new item.'})
            new_stock.quantity -= new_quantity
            old_stock.save()
            new_stock.save()

        # Price override rules: staff/admin can change; default snapshot updates when menu item changes
        if 'price_at_order_time' in validated_data:
            role = getattr(request.user, 'role', 'customer') if request else 'customer'
            if role not in ['staff', 'admin']:
                # Ignore silent overrides from non-staff
                validated_data.pop('price_at_order_time', None)
            else:
                new_price = validated_data['price_at_order_time']
                if not isinstance(new_price, Decimal):
                    try:
                        new_price = Decimal(str(new_price))
                    except Exception:
                        raise serializers.ValidationError({'price_at_order_time': 'Invalid price format.'})
                if new_price < 0:
                    raise serializers.ValidationError({'price_at_order_time': 'Price must be non-negative.'})
                validated_data['price_at_order_time'] = new_price
        elif new_menu_item != instance.menu_item:
            validated_data['price_at_order_time'] = new_menu_item.price

        return super().update(instance, validated_data)

        