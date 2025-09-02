from rest_framework import serializers
from .models import MenuItem
from apps.stock.models import Stock
from apps.users.utils import log_user_action
from django.db import transaction

class MenuItemSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(max_length=None, use_url=True)

    class Meta:
        model = MenuItem
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        menu_item = super().create(validated_data)
        Stock.objects.create(menu_item=menu_item, quantity=0)

        # menu ogesi olusturma logu
        request = self.context.get('request')
        if request:
            log_user_action(
                user=request.user,
                action='create',
                resource_type='menu_item',
                resource_id=menu_item.id,
                details={'item_name': menu_item.name, 'price': str(menu_item.price), 'initial_stock': 0},
                request=request
            )
        return menu_item

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')
        old_name = instance.name
        old_price = instance.price
        old_description = instance.description
        old_is_available = instance.is_available
        old_image = instance.image

        updated_instance = super().update(instance, validated_data)

        changes = {}
        if old_name != updated_instance.name: changes['name'] = {'old': old_name, 'new': updated_instance.name}
        if old_price != updated_instance.price: changes['price'] = {'old': str(old_price), 'new': str(updated_instance.price)}
        if old_description != updated_instance.description: changes['description'] = {'old': old_description, 'new': updated_instance.description}
        if old_is_available != updated_instance.is_available: changes['is_available'] = {'old': old_is_available, 'new': updated_instance.is_available}
        if old_image != updated_instance.image: changes['image'] = {'old': str(old_image), 'new': str(updated_instance.image)} # Basitçe string karşılaştırıyoruz

        if changes and request:
            log_user_action(
                user=request.user,
                action='update',
                resource_type='menu_item',
                resource_id=updated_instance.id,
                details={'item_name': updated_instance.name, 'changes': changes},
                request=request
            )
        return updated_instance