from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from apps.users.permissions import IsStaffOrAdmin
from .models import Stock
from .serializers import StockSerializer
from apps.users.utils import log_user_action

# Create your views here.

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    
    def get_permissions(self):
        return [IsStaffOrAdmin()]
    
    def create(self, request, *args, **kwargs):
        menu_item_id = request.data.get('menu_item')
        quantity = request.data.get('quantity', 0)

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({'quantity': 'Invalid quantity format.'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 0:
            return Response({'quantity': 'Quantity cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)

        if menu_item_id:
            try:
                existing_stock = Stock.objects.get(menu_item_id=menu_item_id)
                old_quantity = existing_stock.quantity
                existing_stock.quantity += quantity
                existing_stock.save()
                
                log_user_action(
                    user=request.user,
                    action='stock_updated',
                    resource_type='stock',
                    resource_id=existing_stock.id,
                    details={
                        'menu_item': existing_stock.menu_item.name,
                        'old_quantity': old_quantity,
                        'new_quantity': existing_stock.quantity,
                        'quantity_added': quantity
                    },
                    request=request
                )

                serializer = self.get_serializer(existing_stock)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Stock.DoesNotExist:
                pass
        
        # If it's a new stock entry for a menu item (Stock.DoesNotExist), then proceed to create.
        # The serializer's create method will handle the actual creation.
        response = super().create(request, *args, **kwargs)
        # Log creation of new stock record
        if response.status_code == status.HTTP_201_CREATED:
            log_user_action(
                user=request.user,
                action='create',
                resource_type='stock',
                resource_id=response.data['id'],
                details={'menu_item': response.data['menu_item_name'], 'quantity': response.data['quantity']},
                request=request
            )
        return response
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_quantity = instance.quantity
        
        # Get the new quantity from request data; use instance.quantity if not provided.
        new_quantity = request.data.get('quantity', old_quantity)
        try:
            new_quantity = int(new_quantity)
        except (ValueError, TypeError):
            return Response({'quantity': 'Invalid quantity format.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_quantity < 0:
            return Response({'quantity': 'Quantity cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate the change for logging
        quantity_changed = new_quantity - old_quantity

        # Update the instance quantity directly, then save
        instance.quantity = new_quantity
        instance.save(update_fields=['quantity'])
        
        # Log stock quantity update
        log_user_action(
            user=request.user,
            action='stock_updated',
            resource_type='stock',
            resource_id=instance.id,
            details={
                'menu_item': instance.menu_item.name,
                'old_quantity': old_quantity,
                'new_quantity': instance.quantity,
                'quantity_changed': quantity_changed
            },
            request=request
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

