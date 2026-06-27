"""
URL configuration for kucadi_project project.
Configured specifically for Kucadi Premium D2C Furniture Marketplace.
"""
from django.contrib import admin
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static
from marketplace import views

urlpatterns = [
    # Jalur Kontrol Back-Office / Panel Admin Kucadi
    path('admin/', admin.site.urls),
    
    # Halaman Utama: Etalase Katalog Furnitur Premium (Ala Burrow D2C)
    path('', views.katalog, name='katalog'),

    # -- Static / Specific routes FIRST to avoid collision with any dynamic catch-alls --
    # Wishlist: toggle dulu (tanpa argumen via JSON), lalu halaman wishlist
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist_id'),
    path('wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    # Midtrans webhook endpoints (handled in marketplace app)
    # Halaman Detail: Spesifikasi Fisik, Volume, Massa, & Tombol Aksi Produk
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/buy-now/', views.buy_now, name='buy_now'),

    # Keranjang Belanja
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/history/', views.order_history, name='order_history'),
    path('order/<int:order_id>/confirm-received/', views.confirm_order_received, name='confirm_order_received'),
    path('helpdesk/', views.helpdesk, name='helpdesk'),
    path('panduan-rakit/', views.panduan_rakit, name='panduan_rakit'),

    # 🌟 TAMBAHKAN DUA BARIS INI (Untuk API Dropdown Provinsi & Kota)
    path('api/provinces/', views.api_provinces, name='api_provinces'),
    path('marketplace/api/cities/', views.api_cities, name='api_cities'),
    path('api/cost/', views.api_check_cost, name='api_check_cost'),

    # Menghubungkan gerbang sistem login Google allauth
    path('accounts/', include('allauth.urls')),
    # Include marketplace routes (webhook, catalog, cart, etc.)
    path('', include('marketplace.urls')),
]

if settings.DEBUG:
    if getattr(settings, 'MEDIA_URL', None) and getattr(settings, 'MEDIA_ROOT', None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if getattr(settings, 'STATIC_URL', None) and getattr(settings, 'STATIC_ROOT', None):
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)