from django.urls import path
from .views import index, login_view
from django.views.generic import TemplateView


urlpatterns = [
    path('', index, name='webui-index'),
    path('login/', login_view, name='webui-login'),
    path('orders/', TemplateView.as_view(template_name='webui/orders.html'), name='webui-orders'),
    path('stock/', TemplateView.as_view(template_name='webui/stock.html'), name='webui-stock'),
    path('menu/', TemplateView.as_view(template_name='webui/menu.html'), name='webui-menu'),
    path('orders/<int:pk>/', TemplateView.as_view(template_name='webui/order_detail.html'), name='webui-order-detail'),
    path('users/', TemplateView.as_view(template_name='webui/users.html'), name='webui-users'),
    path('logs/', TemplateView.as_view(template_name='webui/logs.html'), name='webui-logs'),
]


