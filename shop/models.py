from django.db import models


class Category(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, default='')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    def __str__(self):
        return self.name_uz

    class Meta:
        ordering = ['sort_order', 'id']


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    def __str__(self):
        return self.name_uz

    class Meta:
        ordering = ['sort_order', 'id']


class UserProfile(models.Model):
    telegram_id = models.CharField(max_length=64, unique=True)
    language = models.CharField(max_length=4, blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.telegram_id}"


class Order(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ('new', 'New'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user} - {self.total}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product} x{self.quantity}"
