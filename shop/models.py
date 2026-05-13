from django.db import models
from django.utils import timezone


class Order(models.Model):
    STATUS_NEW = "new"
    STATUS_PROCESSING = "processing"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_NEW, "Yangi"),
        (STATUS_PROCESSING, "Jarayonda"),
        (STATUS_DELIVERED, "Yetkazildi"),
        (STATUS_CANCELLED, "Bekor qilindi"),
    ]

    PAYMENT_CHOICES = [
        ("card", "Karta orqali"),
        ("cash", "Yetkazilganda naqd"),
        ("transfer", "Bank o'tkazmasi"),
    ]

    DELIVERY_CHOICES = [
        ("delivery", "Yetkazib berish"),
        ("pickup", "Olib ketish"),
    ]

    number = models.CharField("Buyurtma raqami", max_length=24, unique=True)
    full_name = models.CharField("Mijoz F.I.Sh.", max_length=80)
    email = models.EmailField("Email")
    phone = models.CharField("Telefon", max_length=24)
    city = models.CharField("Shahar", max_length=60)
    address = models.TextField("Manzil")
    payment_method = models.CharField("To'lov usuli", max_length=20, choices=PAYMENT_CHOICES)
    delivery_method = models.CharField("Yetkazish usuli", max_length=20, choices=DELIVERY_CHOICES, default="delivery")
    total = models.PositiveIntegerField("Jami summa")
    status = models.CharField("Holat", max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField("Yaratilgan vaqt", default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"

    def __str__(self):
        return f"{self.number} - {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Buyurtma")
    product_slug = models.SlugField("Mahsulot slug", max_length=120)
    product_name = models.CharField("Mahsulot nomi", max_length=160)
    product_image = models.URLField("Mahsulot rasmi", max_length=500, blank=True)
    unit_price = models.PositiveIntegerField("Dona narxi")
    quantity = models.PositiveIntegerField("Soni")
    subtotal = models.PositiveIntegerField("Jami")

    class Meta:
        verbose_name = "Buyurtma mahsuloti"
        verbose_name_plural = "Buyurtma mahsulotlari"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
