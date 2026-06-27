import json
import types

from django.contrib import admin
from django.core.mail import send_mail
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings
from .models import User, Product, Order, OrderItem, WarrantyClaim, Category, CustomerService, PanduanRakit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # TAMBAHKAN 'parent' di list_display dan list_filter
    list_display = ('name', 'parent', 'slug')
    list_filter = ('parent',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'stock_status', 'image_preview')
    search_fields = ('name',)
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Informasi Produk', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Spesifikasi & Harga', {
            'fields': ('price', 'weight', 'dimensions', 'stock')
        }),
        ('Kategori & Status', {
            'fields': ('category', 'deleted_at')
        }),
    )

    def stock_status(self, obj):
        return 'In stock' if obj.stock and obj.stock > 0 else 'Out of stock'
    stock_status.short_description = 'Stock Status'

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover; border-radius: 4px;"/>'
        return '—'
    image_preview.short_description = 'Preview'
    image_preview.allow_tags = True


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_per_unit',)
    fields = ('product', 'quantity', 'price_per_unit')
    autocomplete_fields = ('product',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('id', 'user', 'status', 'grand_total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invoice_number', 'user__username')
    list_editable = ('status',)
    ordering = ('-created_at',)
    list_select_related = ('user',)
    date_hierarchy = 'created_at'
    list_per_page = 50


admin.site.register(User)
admin.site.register(OrderItem)
admin.site.register(WarrantyClaim)


@admin.register(CustomerService)
class CustomerServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'phone_number', 'resolved')
    fields = ('name', 'email', 'phone_number', 'buka_whatsapp', 'subject', 'message', 'reply_message', 'replied_at', 'resolved')
    readonly_fields = ('buka_whatsapp', 'replied_at')

    def buka_whatsapp(self, obj):
        if obj.phone_number:
            # Bersihkan karakter non-angka agar link wa.me valid
            nomor = ''.join(filter(str.isdigit, str(obj.phone_number)))
            if nomor.startswith('0'):
                nomor = '62' + nomor[1:]
            
            return format_html(
                '<a href="https://wa.me/{}?text=Halo%20{},%20kami%20dari%20Kucadi%20Furniture%20ingin%20merespon%20pesan%20Anda..." '
                'target="_blank" style="background-color: #25D366; color: white; padding: 8px 12px; '
                'border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">💬 Hubungi via WhatsApp</a>',
                nomor, obj.name
            )
        return "Nomor WhatsApp belum diisi oleh pelanggan."
        
    buka_whatsapp.short_description = 'Aksi WhatsApp'

    def save_model(self, request, obj, form, change):
        if obj.reply_message and 'reply_message' in form.changed_data:
            obj.replied_at = timezone.now()
            obj.resolved = True

            subject = f"Tanggapan Hubungi Kami: {obj.subject}"
            message = (
                f"Halo {obj.name},\n\n"
                "Terima kasih telah menghubungi Kucadi Furniture.\n\n"
                "Berikut adalah tanggapan dari tim kami mengenai pesan Anda:\n\n"
                f'"{obj.reply_message}"\n\n'
                "Salam hangat,\nTim Kucadi Furniture"
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@kucadifurniture.com')
            recipient_list = [obj.email]

            send_mail(subject, message, from_email, recipient_list, fail_silently=True)

        super().save_model(request, obj, form, change)


@admin.register(PanduanRakit)
class PanduanRakitAdmin(admin.ModelAdmin):
    list_display = ('nama_produk', 'link_embed_youtube')
    search_fields = ('nama_produk',)
    ordering = ('-nama_produk',)