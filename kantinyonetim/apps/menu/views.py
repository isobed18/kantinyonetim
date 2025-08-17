from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from apps.users.permissions import IsStaffOrAdmin
from .models import MenuItem
from .serializers import MenuItemSerializer
from apps.users.utils import log_user_action
# Create your views here.

class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsStaffOrAdmin()]
    def get_serializer_context(self):
        return {'request': self.request}
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='menu_item',
            resource_id=instance.id,
            details={'menu_item_name': instance.name},
            request=request
        )
        return super().destroy(request, *args, **kwargs)
    