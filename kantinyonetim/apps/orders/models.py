from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from apps.users.models import User
from django.apps import apps # apps i buraya import et


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.user.username} - {self.status}"

    def update_total(self):
        self.total = sum(item.line_total for item in self.order_items.all())
        self.save(update_fields=['total'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    # dongusel importu onlemek icin string referansi kullanma
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_order_time = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['order', 'menu_item']),
            models.Index(fields=['menu_item']),
        ]

    def save(self, *args, **kwargs):
        if self.price_at_order_time is None:
            # menu itemdan mevcut fiyati dinamik olarak fetch etme
            MenuItem = apps.get_model('menu', 'MenuItem')
            self.price_at_order_time = MenuItem.objects.get(pk=self.menu_item_id).price
            
        self.line_total = self.quantity * self.price_at_order_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} in Order {self.order.id}"


@receiver(post_save, sender=OrderItem)
def update_order_total_on_item_save(sender, instance, **kwargs):
    # siparis ogesi kaydedildiginde siparis toplamini guncelleme
    instance.order.update_total()

@receiver(post_delete, sender=OrderItem)
def update_order_total_on_item_delete(sender, instance, **kwargs):
    # siparis ogesi silindiginde siparis toplamini guncelleme
    instance.order.update_total()