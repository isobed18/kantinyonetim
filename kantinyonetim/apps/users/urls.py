from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('audit-logs/', UserViewSet.as_view({'get': 'audit_logs', 'post': 'create_audit_log'}), name='audit-logs'),
    path('notifications/', UserViewSet.as_view({'get': 'notifications'}), name='notifications'),
    path('notifications/<int:pk>/read/', UserViewSet.as_view({'post': 'mark_notification_read'}), name='mark-notification-read'),
]