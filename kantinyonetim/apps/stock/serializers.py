from rest_framework import serializers
from .models import Stock
from apps.menu.models import MenuItem
 
class StockSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity']

    def validate(self, attrs):
        # Allow creating stock for existing menu items without strict validation
        menu_item = attrs.get('menu_item')
        if menu_item:
            try:
                MenuItem.objects.get(id=menu_item.id)
            except MenuItem.DoesNotExist:
                raise serializers.ValidationError({'menu_item': 'Menu item does not exist'})
        
        quantity = attrs.get('quantity', 0)
        if quantity < 0:
            raise serializers.ValidationError({'quantity': 'Quantity cannot be negative'})
        
        return attrs

    def create(self, validated_data):
        # If stock already exists for this menu item, just update quantity
        menu_item = validated_data['menu_item']
        try:
            existing_stock = Stock.objects.get(menu_item=menu_item)
            existing_stock.quantity += validated_data.get('quantity', 0)
            existing_stock.save()
            return existing_stock
        except Stock.DoesNotExist:
            return super().create(validated_data)

