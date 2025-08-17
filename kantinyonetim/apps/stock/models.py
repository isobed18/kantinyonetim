from django.db import models
from apps.menu.models import MenuItem

class Stock(models.Model):
    menu_item = models.OneToOneField('menu.MenuItem', on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['menu_item']),
            models.Index(fields=['quantity']),
        ]

    def __str__(self):
        return f"{self.menu_item.name}: {self.quantity} units"