from django.db import models, transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = [('customer', 'Customer'), ('admin', 'Admin Toko')]
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    email = models.EmailField(unique=True)


class Category(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    weight = models.IntegerField()
    dimensions = models.CharField(max_length=100)
    stock = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Dikirim'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    invoice_number = models.CharField(max_length=50, unique=True)
    shipping_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address_full = models.TextField(blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    courier = models.CharField(max_length=50, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    midtrans_token = models.CharField(max_length=255, blank=True, null=True)
    expired_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


@receiver(pre_save, sender=Order)
def _store_previous_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        instance._previous_status = sender.objects.values_list('status', flat=True).get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def restock_products_on_order_cancel_or_expire(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status == instance.status:
        return

    if instance.status in ('cancelled', 'expired') and previous_status not in ('cancelled', 'expired'):
        with transaction.atomic():
            for item in instance.items.select_related('product'):
                product = item.product
                product.stock = (product.stock or 0) + item.quantity
                product.save(update_fields=['stock'])


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} wishlist {self.product.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    quantity = models.IntegerField()
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.price_per_unit * self.quantity


class CustomerService(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nomor WhatsApp")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    reply_message = models.TextField(blank=True, null=True, verbose_name="Pesan Balasan Admin")
    replied_at = models.DateTimeField(blank=True, null=True, verbose_name="Waktu Dibalas")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Customer Service Request'
        verbose_name_plural = 'Customer Service Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} from {self.name}"

class WarrantyClaim(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT)
    description = models.TextField()
    video_proof_path = models.FileField(upload_to='warranty_videos/')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved')], default='pending')


class PanduanRakit(models.Model):
    nama_produk = models.CharField(max_length=255)
    deskripsi_singkat = models.TextField()
    link_embed_youtube = models.URLField(help_text='Tulis URL embed YouTube, misal https://www.youtube.com/embed/xxxxxx')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Panduan Rakit'
        verbose_name_plural = 'Panduan Rakit'
        ordering = ['-created_at']

    def __str__(self):
        return self.nama_produk


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')

    def __str__(self):
        return f"Cart({self.user.username})"

    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
