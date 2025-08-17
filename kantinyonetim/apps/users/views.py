from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import User, AuditLog, Notification
from .serializers import UserSerializer, AuditLogSerializer, NotificationSerializer
from .permissions import IsStaffOrAdmin
from .utils import log_user_action
from django.db.models import Q
from datetime import datetime, timedelta


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsStaffOrAdmin]
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', 'customer') in ['staff', 'admin']:
            return User.objects.all()
        if user.is_authenticated:
            return User.objects.filter(id=user.id)
        return User.objects.none()

    def update(self, request, *args, **kwargs):
        # Treat PUT as partial to avoid forcing all fields
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ['create', 'me', 'notifications', 'mark_notification_read']:
            return [IsAuthenticated()]
        # For other actions, apply staff/admin permissions
        return [IsStaffOrAdmin()]

    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search', permission_classes=[IsStaffOrAdmin])
    def search(self, request):
        username = request.query_params.get('username', '')
        if not username:
            return Response({'detail': 'Username parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(username__icontains=username)[:10]
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsStaffOrAdmin])
    def audit_logs(self, request):
        """Get audit logs with filtering and pagination"""
        logs = AuditLog.objects.select_related('user').all()
        
        # Apply filters
        user_filter = request.query_params.get('user', '')
        action_filter = request.query_params.get('action', '')
        resource_filter = request.query_params.get('resource_type', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        
        if user_filter:
            logs = logs.filter(user__username__icontains=user_filter)
        if action_filter:
            logs = logs.filter(action=action_filter)
        if resource_filter:
            logs = logs.filter(resource_type=resource_filter)
        if date_from:
            logs = logs.filter(timestamp__gte=date_from)
        if date_to:
            # Ensure date_to includes the entire day
            date_to_end_of_day = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1, microseconds=-1)
            logs = logs.filter(timestamp__lte=date_to_end_of_day)
        
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def notifications(self, request):
        """Get user's notifications"""
        user = request.user
        notifications = Notification.objects.filter(recipient=user).order_by('-created_at')
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_notification_read(self, request, pk=None):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=pk, recipient=request.user)
            notification.mark_as_read()
            return Response({'detail': 'Notification marked as read'})
        except Notification.DoesNotExist:
            return Response({'detail': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    def perform_create(self, serializer):
        user = serializer.save()
        # Log user creation
        log_user_action(
            user=self.request.user,
            action='user_created',
            resource_type='user',
            resource_id=user.id,
            details={'created_username': user.username, 'created_role': user.role},
            request=self.request
        )

    def perform_update(self, serializer):
        old_instance = self.get_object()
        user = serializer.save()
        # Log user modification
        log_user_action(
            user=self.request.user,
            action='user_modified',
            resource_type='user',
            resource_id=user.id,
            details={
                'modified_username': user.username,
                'old_role': old_instance.role,
                'new_role': user.role
            },
            request=self.request
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_user_action(
            user=request.user,
            action='delete',
            resource_type='user',
            resource_id=instance.id,
            details={'deleted_username': instance.username, 'deleted_role': instance.role},
            request=request
        )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        # Log logout action before token invalidation (if using a blacklist)
        log_user_action(
            user=request.user,
            action='logout',
            resource_type='user',
            resource_id=request.user.id,
            details={'status': 'success'},
            request=request
        )
        # Invalidate tokens if using a blacklist (Simple JWT handles this automatically on token refresh/verify if blacklist is enabled)
        # For explicit invalidation, you might need to import Token model from simple_jwt.token_blacklist.models
        # Or, if not using a blacklist, simply rely on client-side token removal.
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def create_audit_log(self, request):
        """Create an audit log entry from client side. For actions that occur purely on frontend."""
        action = request.data.get('action')
        resource_type = request.data.get('resource_type')
        resource_id = request.data.get('resource_id')
        details = request.data.get('details', {})
        
        if not action or not resource_type:
            return Response({'detail': 'Action and resource_type are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        log_user_action(
            user=request.user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request=request
        )
        return Response({'detail': 'Log recorded successfully.'}, status=status.HTTP_201_CREATED)

