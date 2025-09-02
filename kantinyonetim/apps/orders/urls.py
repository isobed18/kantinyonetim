from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderItemViewSet,parse_voice_order, confirm_and_create_order

router = DefaultRouter()
router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('parse-voice-order/', parse_voice_order, name='parse-voice-order'), 
    path('confirm-order/', confirm_and_create_order, name='confirm-order'),
]
