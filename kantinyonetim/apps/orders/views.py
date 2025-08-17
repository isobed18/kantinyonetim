from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsStaffOrAdmin
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from apps.stock.models import Stock
from apps.users.models import User
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from apps.users.utils import log_user_action, notify_staff_new_order, notify_order_status_change, create_notification
# Create your views here.

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()  # router icin default queryset
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', 'customer') in ['staff', 'admin']:
            return Order.objects.select_related('user').prefetch_related(
                'order_items__menu_item'
            ).all()
        if user.is_authenticated:
            return Order.objects.select_related('user').prefetch_related(
                'order_items__menu_item'
            ).filter(user=user)
        return Order.objects.none()

    def get_permissions(self):
        # authenticated userlarin kendi orderlarini create etme, okuma ve cancel etme islemlerine izin verme
        if self.action in ['create', 'list', 'retrieve', 'cancel']:
            return [IsAuthenticated()]
        # diger islemler (update/delete) staff/admin ile kisitli
        return [IsStaffOrAdmin()]

    def perform_create(self, serializer):
        # staff/admin diger userlar icin order create edebilir
        user = self.request.user
        if getattr(user, 'role', 'customer') in ['staff', 'admin']:
            target_user_id = self.request.data.get('user')
            if target_user_id:
                try:
                    target_user = User.objects.get(id=target_user_id)
                    order = serializer.save(user=target_user)
                    # actioni loglama
                    log_user_action(
                        user=user,
                        action='create',
                        resource_type='order',
                        resource_id=order.id,
                        details={'created_for': target_user.username},
                        request=self.request
                    )
                    # yeni order hakkinda staffi bilgilendirme
                    notify_staff_new_order(order, target_user)
                    return
                except User.DoesNotExist:
                    pass
        
        # Default: mevcut user icin create etme
        order = serializer.save(user=user)

        # yeni order hakkinda staffi bilgilendirme
        notify_staff_new_order(order, user)
        # musteriyi yeni orderi hakkinda bilgilendirme
        create_notification(
            recipient=user,
            notification_type='order_new',
            title='Order Received!',
            message=f'Your order #{order.id} has been successfully placed. Total: ₺{order.total}',
            priority='high',
            resource_type='order',
            resource_id=order.id
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        new_status = request.data.get('status', old_status)

        # eger order zaten cancelled ise status degisikligini engelleme
        if old_status == 'cancelled' and new_status != 'cancelled':
            return Response({'detail': 'Cannot change status of a cancelled order.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # orderi update etme
        response = super().update(request, *args, **kwargs)
        
        # eger status cancelleddan non-cancelled bir statusa degistiyse is_restockedi resetleme
        if old_status == 'cancelled' and instance.status != 'cancelled':
            instance.is_restocked = False
            instance.save(update_fields=['is_restocked'])

        # status degisti mi kontrol etme
        if old_status != instance.status:
            print(f"Order status changed from {old_status} to {instance.status} for order {instance.id}")
            print(f"User performing update: {request.user.username} (ID: {request.user.id}, IsAuthenticated: {request.user.is_authenticated})")
            # status degisikligini loglama
            # gereksiz log_user_action cagrısını kaldirma, notify_order_status_change tarafindan halledildi
            # log_user_action(
            #     user=request.user,
            #     action='order_status_changed',
            #     resource_type='order',
            #     resource_id=instance.id,
            #     details={
            #         'old_status': old_status,
            #         'new_status': instance.status,
            #         'customer': instance.user.username
            #     },
            #     request=request
            # )
            print(f"log_user_action for order status change called.")
            
            # bildirimleri gonderme
            notify_order_status_change(instance, old_status, instance.status, request.user, request)
        
        return response

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        order = self.get_object()

        # sadece order pending veya preparing ise restock etme
        if order.status in ['pending', 'preparing']:
            for item in order.order_items.select_related('menu_item').all():
                stock = Stock.objects.select_for_update().get(menu_item=item.menu_item)
                stock.quantity += item.quantity
                stock.save()
                log_user_action(
                    user=request.user,
                    action='item_cancelled',
                    resource_type='order_item',
                    resource_id=item.id,
                    details={'order_id': order.id, 'menu_item': item.menu_item.name, 'cancelled_quantity': item.quantity, 'full_cancellation': True, 'via_order_cancel': True},
                    request=request
                )
        
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        # musteriyi order cancel hakkinda bilgilendirme
        create_notification(
            recipient=order.user,
            notification_type='order_status',
            title='Order Cancelled',
            message=f'Your order #{order.id} has been cancelled.',
            priority='medium',
            resource_type='order',
            resource_id=order.id
        )
        return Response({'detail': 'Order cancelled.'}, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='reassign', permission_classes=[IsStaffOrAdmin])
    def reassign(self, request, pk=None):
        order = self.get_object()
        target_user_id = request.data.get('user')
        if not target_user_id:
            return Response({'user': 'Target user id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({'user': 'Target user not found.'}, status=status.HTTP_404_NOT_FOUND)
        order.user = target_user
        order.save(update_fields=['user'])
        # Log reassign action
        log_user_action(
            user=request.user,
            action='reassign',
            resource_type='order',
            resource_id=order.id,
            details={'old_customer': order.user.username, 'new_customer': target_user.username},
            request=request
        )
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='order',
            resource_id=instance.id,
            details={'order_id': instance.id, 'total': str(instance.total), 'customer': instance.user.username},
            request=request
        )
        return super().destroy(request, *args, **kwargs)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', 'customer') in ['staff', 'admin']:
            return OrderItem.objects.all().select_related('order__user', 'menu_item')
        if user.is_authenticated:
            return OrderItem.objects.filter(order__user=user).select_related('order__user', 'menu_item')
        return OrderItem.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsStaffOrAdmin()]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        # kaydetmeden once eski degerleri yakalama
        old_price_at_order_time = serializer.instance.price_at_order_time
        old_quantity = serializer.instance.quantity
        
        # instancei kaydetme (bu, validated_data based instancei update edecek)
        updated_instance = serializer.save()

        # price degisikligi olduysa loglama
        if old_price_at_order_time != updated_instance.price_at_order_time:
            log_user_action(
                user=self.request.user,
                action='price_changed',
                resource_type='order_item',
                resource_id=updated_instance.id,
                details={
                    'order_id': updated_instance.order.id,
                    'menu_item': updated_instance.menu_item.name,
                    'old_price': str(old_price_at_order_time),
                    'new_price': str(updated_instance.price_at_order_time)
                },
                request=self.request
            )
        # quantity degisikligi olduysa loglama
        if old_quantity != updated_instance.quantity:
            log_user_action(
                user=self.request.user,
                action='update',
                resource_type='order_item',
                resource_id=updated_instance.id,
                details={
                    'order_id': updated_instance.order.id,
                    'menu_item': updated_instance.menu_item.name,
                    'old_quantity': old_quantity,
                    'new_quantity': updated_instance.quantity
                },
                request=self.request
            )

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        user = request.user

        print(f"OrderItem cancel attempt by user: {user.username} (ID: {user.id}), Role: {getattr(user, 'role', 'N/A')}")
        print(f"Order Item ID: {instance.id}, Associated Order User ID: {instance.order.user_id}, Owner ID: {instance.order.user.id}, Request User ID: {user.id}")
        
        # owner veya staff/admin line itemlari cancel edebilir
        if not (getattr(user, 'role', 'customer') in ['staff', 'admin'] or instance.order.user.id == user.id):
            print("Permission denied for OrderItem cancel. User is not staff/admin and not order owner.")
            return Response({'detail': 'Not permitted to cancel this item.'}, status=status.HTTP_403_FORBIDDEN)
        print("Permission granted for OrderItem cancel.")

        # quantity ile partial cancellation destegi
        try:
            cancel_qty = int(request.data.get('quantity')) if 'quantity' in request.data else instance.quantity
        except Exception:
            return Response({'quantity': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)
        if cancel_qty <= 0:
            return Response({'quantity': 'Quantity must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)
        if cancel_qty > instance.quantity:
            return Response({'quantity': 'Cannot cancel more than existing quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if instance.order.status in ['pending', 'preparing']:
            stock = Stock.objects.select_for_update().get(menu_item=instance.menu_item)
            stock.quantity += cancel_qty
            stock.save()

        old_quantity = instance.quantity # degisiklikten once eski quantity'yi yakalama

        if cancel_qty == instance.quantity:
            log_user_action(
                user=request.user,
                action='item_cancelled',
                resource_type='order_item',
                resource_id=instance.id,
                details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'cancelled_quantity': cancel_qty, 'full_cancellation': True},
                request=request
            )
            instance.delete()
        else:
            instance.quantity -= cancel_qty
            instance.save(update_fields=['quantity'])
            log_user_action(
                user=request.user,
                action='item_cancelled',
                resource_type='order_item',
                resource_id=instance.id,
                details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'cancelled_quantity': cancel_qty, 'new_quantity': instance.quantity, 'full_cancellation': False},
                request=request
            )
        
        # musteriyi item cancel hakkinda bilgilendirme
        create_notification(
            recipient=instance.order.user,
            notification_type='order_status',
            title='Order Item Cancelled',
            message=f'{cancel_qty}x {instance.menu_item.name} from your order #{instance.order.id} has been cancelled.',
            priority='medium',
            resource_type='order_item',
            resource_id=instance.id
        )
        
        msg = 'Order item cancelled and restocked.' if instance.order.status in ['pending', 'preparing'] else 'Order item cancelled (no restock due to order status).'
        return Response({'detail': msg}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        # staff/admin veya orderin sahibi ise izin verme
        if not (getattr(user, 'role', 'customer') in ['staff', 'admin'] or instance.order.user_id == user.id):
            return Response({'detail': 'Not permitted to delete this item.'}, status=status.HTTP_403_FORBIDDEN)
        order = instance.order
        # sadece order henuz ready/completed/cancelled degilse restock etme
        if order.status in ['pending', 'preparing']:
            stock = Stock.objects.select_for_update().get(menu_item=instance.menu_item)
            stock.quantity += instance.quantity
            stock.save()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='order_item',
            resource_id=instance.id,
            details={'order_id': instance.order.id, 'menu_item': instance.menu_item.name, 'quantity': instance.quantity},
            request=request
        )
        return super().destroy(request, *args, **kwargs)