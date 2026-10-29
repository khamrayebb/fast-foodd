from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def __str__(self):
        return self.name
    

class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Yangi"),
        ("confirmed", "Tasdiqlangan"),
        ("preparing", "Tayyorlanmoqda"),
        ("ready", "Tayyor"),
        ("delivering", "Yetkazilmoqda"),
        ("delivered", "Yetkazildi"),
        ("cancelled", "Bekor qilindi"),
    ]

    PAYMENT_CHOICES = [
        ("cash", "Naqd"),
        ("click", "Click"),
        ("payme", "Payme"),
    ]

    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    address = models.TextField()
    courier = models.ForeignKey(
    "auth.User",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="courier_orders",
)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="cash"
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    customer_latitude = models.DecimalField(
    max_digits=10,
    decimal_places=7,
    null=True,
    blank=True,
)

    customer_longitude = models.DecimalField(
    max_digits=10,
    decimal_places=7,
    null=True,
    blank=True,
)
    courier_latitude = models.DecimalField(
    max_digits=10,
    decimal_places=7,
    null=True,
    blank=True,
)

    courier_longitude = models.DecimalField(
    max_digits=10,
    decimal_places=7,
    null=True,
    blank=True,
)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    



class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("courier", "Kuryer"),
        ("user", "Foydalanuvchi"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="user",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"