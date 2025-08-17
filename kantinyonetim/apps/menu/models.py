from django.db import models

class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('ana_yemek', 'Ana Yemek'),
        ('icecek', 'İçecek'),
        ('tatli', 'Tatlı'),
        ('aperatif', 'Aperatif'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True) 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ana_yemek')
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True) # Yeni fotoğraf alanı

    def __str__(self):
        return self.name