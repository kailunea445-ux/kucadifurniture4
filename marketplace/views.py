import uuid
import json
import time
from decimal import Decimal
from datetime import timedelta

import midtransclient

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from marketplace.models import Product, Category, Cart, CartItem, Order, OrderItem, Wishlist, CustomerService, PanduanRakit
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed

# Master data lokal untuk provinsi dan kota agar endpoint tidak perlu memanggil RajaOngkir eksternal.
# =====================================================================
# 1. MASTER DATA WILAYAH LOKAL LENGKAP - FULL PULAU JAWA (119 Kota/Kab)
# =====================================================================
DATA_PROVINSI_LOKAL = [
    {"province_id": "3", "province": "Banten"},
    {"province_id": "6", "province": "DKI Jakarta"},
    {"province_id": "9", "province": "Jawa Barat"},
    {"province_id": "10", "province": "Jawa Tengah"},
    {"province_id": "5", "province": "DI Yogyakarta"},
    {"province_id": "11", "province": "Jawa Timur"}
]

DATA_KOTA_LOKAL = {
    "3": [  # BANTEN
        {"city_id": "301", "province_id": "3", "type": "Kabupaten", "city_name": "Lebak"},
        {"city_id": "302", "province_id": "3", "type": "Kabupaten", "city_name": "Pandeglang"},
        {"city_id": "303", "province_id": "3", "type": "Kabupaten", "city_name": "Serang"},
        {"city_id": "304", "province_id": "3", "type": "Kabupaten", "city_name": "Tangerang"},
        {"city_id": "305", "province_id": "3", "type": "Kota", "city_name": "Cilegon"},
        {"city_id": "306", "province_id": "3", "type": "Kota", "city_name": "Serang"},
        {"city_id": "307", "province_id": "3", "type": "Kota", "city_name": "Tangerang"},
        {"city_id": "308", "province_id": "3", "type": "Kota", "city_name": "Tangerang Selatan"}
    ],
    "6": [  # DKI JAKARTA
        {"city_id": "601", "province_id": "6", "type": "Kabupaten", "city_name": "Kepulauan Seribu"},
        {"city_id": "602", "province_id": "6", "type": "Kota", "city_name": "Jakarta Barat"},
        {"city_id": "603", "province_id": "6", "type": "Kota", "city_name": "Jakarta Pusat"},
        {"city_id": "604", "province_id": "6", "type": "Kota", "city_name": "Jakarta Selatan"},
        {"city_id": "605", "province_id": "6", "type": "Kota", "city_name": "Jakarta Timur"},
        {"city_id": "606", "province_id": "6", "type": "Kota", "city_name": "Jakarta Utara"}
    ],
    "9": [  # JAWA BARAT
        {"city_id": "901", "province_id": "9", "type": "Kabupaten", "city_name": "Bandung"},
        {"city_id": "902", "province_id": "9", "type": "Kabupaten", "city_name": "Bandung Barat"},
        {"city_id": "903", "province_id": "9", "type": "Kabupaten", "city_name": "Bekasi"},
        {"city_id": "904", "province_id": "9", "type": "Kabupaten", "city_name": "Bogor"},
        {"city_id": "905", "province_id": "9", "type": "Kabupaten", "city_name": "Ciamis"},
        {"city_id": "906", "province_id": "9", "type": "Kabupaten", "city_name": "Cianjur"},
        {"city_id": "907", "province_id": "9", "type": "Kabupaten", "city_name": "Cirebon"},
        {"city_id": "908", "province_id": "9", "type": "Kabupaten", "city_name": "Garut"},
        {"city_id": "909", "province_id": "9", "type": "Kabupaten", "city_name": "Indramayu"},
        {"city_id": "910", "province_id": "9", "type": "Kabupaten", "city_name": "Karawang"},
        {"city_id": "911", "province_id": "9", "type": "Kabupaten", "city_name": "Kuningan"},
        {"city_id": "912", "province_id": "9", "type": "Kabupaten", "city_name": "Majalengka"},
        {"city_id": "913", "province_id": "9", "type": "Kabupaten", "city_name": "Pangandaran"},
        {"city_id": "914", "province_id": "9", "type": "Kabupaten", "city_name": "Purwakarta"},
        {"city_id": "915", "province_id": "9", "type": "Kabupaten", "city_name": "Subang"},
        {"city_id": "916", "province_id": "9", "type": "Kabupaten", "city_name": "Sukabumi"},
        {"city_id": "917", "province_id": "9", "type": "Kabupaten", "city_name": "Sumedang"},
        {"city_id": "918", "province_id": "9", "type": "Kabupaten", "city_name": "Tasikmalaya"},
        {"city_id": "919", "province_id": "9", "type": "Kota", "city_name": "Bandung"},
        {"city_id": "920", "province_id": "9", "type": "Kota", "city_name": "Banjar"},
        {"city_id": "921", "province_id": "9", "type": "Kota", "city_name": "Bekasi"},
        {"city_id": "922", "province_id": "9", "type": "Kota", "city_name": "Bogor"},
        {"city_id": "923", "province_id": "9", "type": "Kota", "city_name": "Cimahi"},
        {"city_id": "924", "province_id": "9", "type": "Kota", "city_name": "Cirebon"},
        {"city_id": "925", "province_id": "9", "type": "Kota", "city_name": "Depok"},
        {"city_id": "926", "province_id": "9", "type": "Kota", "city_name": "Sukabumi"},
        {"city_id": "927", "province_id": "9", "type": "Kota", "city_name": "Tasikmalaya"}
    ],
    "10": [ # JAWA TENGAH
        {"city_id": "1001", "province_id": "10", "type": "Kabupaten", "city_name": "Banjarnegara"},
        {"city_id": "24", "province_id": "10", "type": "Kabupaten", "city_name": "Banyumas"}, 
        {"city_id": "1003", "province_id": "10", "type": "Kabupaten", "city_name": "Batang"},
        {"city_id": "1004", "province_id": "10", "type": "Kabupaten", "city_name": "Blora"},
        {"city_id": "1005", "province_id": "10", "type": "Kabupaten", "city_name": "Boyolali"},
        {"city_id": "1006", "province_id": "10", "type": "Kabupaten", "city_name": "Brebes"},
        {"city_id": "1007", "province_id": "10", "type": "Kabupaten", "city_name": "Cilacap"},
        {"city_id": "1008", "province_id": "10", "type": "Kabupaten", "city_name": "Demak"},
        {"city_id": "1009", "province_id": "10", "type": "Kabupaten", "city_name": "Grobogan"},
        {"city_id": "1010", "province_id": "10", "type": "Kabupaten", "city_name": "Jepara"},
        {"city_id": "1011", "province_id": "10", "type": "Kabupaten", "city_name": "Karanganyar"},
        {"city_id": "1012", "province_id": "10", "type": "Kabupaten", "city_name": "Kebumen"},
        {"city_id": "1013", "province_id": "10", "type": "Kabupaten", "city_name": "Kendal"},
        {"city_id": "1014", "province_id": "10", "type": "Kabupaten", "city_name": "Klaten"},
        {"city_id": "1015", "province_id": "10", "type": "Kabupaten", "city_name": "Kudus"},
        {"city_id": "1016", "province_id": "10", "type": "Kabupaten", "city_name": "Magelang"},
        {"city_id": "1017", "province_id": "10", "type": "Kabupaten", "city_name": "Pati"},
        {"city_id": "1018", "province_id": "10", "type": "Kabupaten", "city_name": "Pekalongan"},
        {"city_id": "1019", "province_id": "10", "type": "Kabupaten", "city_name": "Pemalang"},
        {"city_id": "1020", "province_id": "10", "type": "Kabupaten", "city_name": "Purbalingga"},
        {"city_id": "1021", "province_id": "10", "type": "Kabupaten", "city_name": "Purworejo"},
        {"city_id": "1022", "province_id": "10", "type": "Kabupaten", "city_name": "Rembang"},
        {"city_id": "1023", "province_id": "10", "type": "Kabupaten", "city_name": "Semarang"},
        {"city_id": "1024", "province_id": "10", "type": "Kabupaten", "city_name": "Sragen"},
        {"city_id": "1025", "province_id": "10", "type": "Kabupaten", "city_name": "Sukoharjo"},
        {"city_id": "1026", "province_id": "10", "type": "Kabupaten", "city_name": "Tegal"},
        {"city_id": "1027", "province_id": "10", "type": "Kabupaten", "city_name": "Temanggung"},
        {"city_id": "1028", "province_id": "10", "type": "Kabupaten", "city_name": "Wonogiri"},
        {"city_id": "1029", "province_id": "10", "type": "Kabupaten", "city_name": "Wonosobo"},
        {"city_id": "1030", "province_id": "10", "type": "Kota", "city_name": "Magelang"},
        {"city_id": "1031", "province_id": "10", "type": "Kota", "city_name": "Pekalongan"},
        {"city_id": "1032", "province_id": "10", "type": "Kota", "city_name": "Salatiga"},
        {"city_id": "1033", "province_id": "10", "type": "Kota", "city_name": "Semarang"},
        {"city_id": "1034", "province_id": "10", "type": "Kota", "city_name": "Surakarta"},
        {"city_id": "1035", "province_id": "10", "type": "Kota", "city_name": "Tegal"}
    ],
    "5": [  # DI YOGYAKARTA
        {"city_id": "501", "province_id": "5", "type": "Kabupaten", "city_name": "Bantul"},
        {"city_id": "502", "province_id": "5", "type": "Kabupaten", "city_name": "Gunungkidul"},
        {"city_id": "503", "province_id": "5", "type": "Kabupaten", "city_name": "Kulon Progo"},
        {"city_id": "504", "province_id": "5", "type": "Kabupaten", "city_name": "Sleman"},
        {"city_id": "505", "province_id": "5", "type": "Kota", "city_name": "Yogyakarta"}
    ],
    "11": [ # JAWA TIMUR
        {"city_id": "1101", "province_id": "11", "type": "Kabupaten", "city_name": "Bangkalan"},
        {"city_id": "1102", "province_id": "11", "type": "Kabupaten", "city_name": "Banyuwangi"},
        {"city_id": "1103", "province_id": "11", "type": "Kabupaten", "city_name": "Blitar"},
        {"city_id": "1104", "province_id": "11", "type": "Kabupaten", "city_name": "Bojonegoro"},
        {"city_id": "1105", "province_id": "11", "type": "Kabupaten", "city_name": "Bondowoso"},
        {"city_id": "1106", "province_id": "11", "type": "Kabupaten", "city_name": "Gresik"},
        {"city_id": "1107", "province_id": "11", "type": "Kabupaten", "city_name": "Jember"},
        {"city_id": "1108", "province_id": "11", "type": "Kabupaten", "city_name": "Jombang"},
        {"city_id": "1109", "province_id": "11", "type": "Kabupaten", "city_name": "Kediri"},
        {"city_id": "1110", "province_id": "11", "type": "Kabupaten", "city_name": "Lamongan"},
        {"city_id": "1111", "province_id": "11", "type": "Kabupaten", "city_name": "Lumajang"},
        {"city_id": "1112", "province_id": "11", "type": "Kabupaten", "city_name": "Madiun"},
        {"city_id": "1113", "province_id": "11", "type": "Kabupaten", "city_name": "Magetan"},
        {"city_id": "1114", "province_id": "11", "type": "Kabupaten", "city_name": "Malang"},
        {"city_id": "1115", "province_id": "11", "type": "Kabupaten", "city_name": "Mojokerto"},
        {"city_id": "1116", "province_id": "11", "type": "Kabupaten", "city_name": "Nganjuk"},
        {"city_id": "1117", "province_id": "11", "type": "Kabupaten", "city_name": "Ngawi"},
        {"city_id": "1118", "province_id": "11", "type": "Kabupaten", "city_name": "Pacitan"},
        {"city_id": "1119", "province_id": "11", "type": "Kabupaten", "city_name": "Pamekasan"},
        {"city_id": "1120", "province_id": "11", "type": "Kabupaten", "city_name": "Pasuruan"},
        {"city_id": "1121", "province_id": "11", "type": "Kabupaten", "city_name": "Ponorogo"},
        {"city_id": "1122", "province_id": "11", "type": "Kabupaten", "city_name": "Probolinggo"},
        {"city_id": "1123", "province_id": "11", "type": "Kabupaten", "city_name": "Sampang"},
        {"city_id": "1124", "province_id": "11", "type": "Kabupaten", "city_name": "Sidoarjo"},
        {"city_id": "1125", "province_id": "11", "type": "Kabupaten", "city_name": "Situbondo"},
        {"city_id": "1126", "province_id": "11", "type": "Kabupaten", "city_name": "Sumenep"},
        {"city_id": "1127", "province_id": "11", "type": "Kabupaten", "city_name": "Trenggalek"},
        {"city_id": "1128", "province_id": "11", "type": "Kabupaten", "city_name": "Tuban"},
        {"city_id": "1129", "province_id": "11", "type": "Kabupaten", "city_name": "Tulungagung"},
        {"city_id": "1130", "province_id": "11", "type": "Kota", "city_name": "Batu"},
        {"city_id": "1131", "province_id": "11", "type": "Kota", "city_name": "Blitar"},
        {"city_id": "1132", "province_id": "11", "type": "Kota", "city_name": "Kediri"},
        {"city_id": "1133", "province_id": "11", "type": "Kota", "city_name": "Madiun"},
        {"city_id": "1134", "province_id": "11", "type": "Kota", "city_name": "Malang"},
        {"city_id": "1135", "province_id": "11", "type": "Kota", "city_name": "Mojokerto"},
        {"city_id": "1136", "province_id": "11", "type": "Kota", "city_name": "Pasuruan"},
        {"city_id": "1137", "province_id": "11", "type": "Kota", "city_name": "Probolinggo"},
        {"city_id": "1138", "province_id": "11", "type": "Kota", "city_name": "Surabaya"}
    ]
}


# =====================================================================
# 2. LOGIKA ONGKIR OTOMATIS
# =====================================================================
# NOTE: Implementasi api_check_cost saat ini ada di bagian endpoint di bawah.

def katalog(request):
    """
    Paparan untuk menampilkan katalog produk utama dengan dukungan kategori dinamis dari navbar,
    serta mendukung fitur pencarian dan pengurutan produk.
    """
    # Ambil hanya kategori utama (parent) untuk menu navbar
    categories = Category.objects.filter(parent__isnull=True).order_by('name')

    # PILIH PRODUK YANG AKTIF (deleted_at harus NULL agar produk yang di-soft-delete tidak muncul)
    products = Product.objects.filter(deleted_at__isnull=True)

    # 1. FILTER BERDASARKAN KATEGORI
    query_filter = request.GET.get('kategori') or request.GET.get('category') or request.GET.get('sub')
    current_category = query_filter

    if query_filter:
        if query_filter == 'bestsellers':
            products = products.annotate(
                total_sold=Coalesce(
                    Sum('orderitem__quantity', filter=Q(orderitem__order__status__in=['paid', 'shipped', 'completed'])),
                    0
                )
            ).order_by('-total_sold', '-created_at')
        else:
            try:
                selected_category = Category.objects.get(slug=query_filter)
                if selected_category.children.exists():
                    child_ids = list(selected_category.children.values_list('id', flat=True))
                    products = products.filter(
                        Q(category_id=selected_category.id) | Q(category_id__in=child_ids)
                    )
                else:
                    products = products.filter(category_id=selected_category.id)
            except Category.DoesNotExist:
                pass

    # =========================================================================
    # BARU: 2. FITUR PENCARIAN (Hanya berdasarkan Nama agar lebih akurat)
    # =========================================================================
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(name__icontains=search_query)

    wishlisted_product_ids = []
    if request.user.is_authenticated:
        wishlisted_product_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    # 3. FITUR PENGURUTAN (SORTING)
    sort_by = request.GET.get('sort')
    if sort_by == 'harga_terendah':
        products = products.order_by('price')
    elif sort_by == 'harga_tertinggi':
        products = products.order_by('-price')
    elif sort_by == 'terbaru':
        products = products.order_by('-created_at')
    else:
        # Default sorting
        products = products.order_by('-created_at')

    # Mapping judul kategori dan deskripsi untuk tampilan halaman kategori
    category_labels = {
        'furnitur': ('KOLEKSI FURNITUR & TIDUR', 'Home > Furnitur & Tidur', 'Pilihan furniture ergonomis dan kasur premium untuk ruang tidur dan kerja yang modern.'),
        'penyimpanan': ('KOLEKSI PENYIMPANAN', 'Home > Penyimpanan', 'Solusi rak dan lemari lipat untuk tata ruang rumah yang lebih rapi dan elegan.'),
        'fitnes': ('KOLEKSI FITNES RUMAHAN', 'Home > Fitnes Rumahan', 'Alat olahraga compact dan gaya hidup aktif di rumah tanpa mengorbankan estetika.'),
        'bestsellers': ('KOLEKSI BESTSELLERS', 'Home > Bestsellers', 'Koleksi favorit pelanggan Kucadi dengan kualitas premium dan nilai D2C terbaik.'),
    }

    if query_filter:
        category_title, category_breadcrumb, category_description = category_labels.get(
            query_filter,
            (f"KOLEKSI {query_filter.replace('-', ' ').upper()}", f"Home > {query_filter.replace('-', ' ').title()}", 'Temukan pilihan produk Kucadi yang sesuai dengan preferensi Anda.')
        )
    else:
        category_title = ''
        category_breadcrumb = ''
        category_description = ''

    # Format harga untuk setiap produk: ribuan dipisah titik
    for prod in products:
        if prod.price is not None:
            try:
                prod.formatted_price = f"Rp{int(prod.price):,}".replace(",", ".")
            except Exception:
                prod.formatted_price = f"Rp{prod.price}"
        else:
            prod.formatted_price = "Rp0"

    context = {
        'products': products,
        'total_products': products.count(),
        'categories': categories,
        'current_category': current_category,
        'category_title': category_title,
        'category_breadcrumb': category_breadcrumb,
        'category_description': category_description,
        'search_query': search_query,
        'wishlisted_product_ids': wishlisted_product_ids,
    }

    return render(request, 'marketplace/katalog.html', context)


def bestseller_view(request):
    bestselling_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__status='paid'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:8]

    products_list = list(bestselling_products)

    if len(products_list) < 8:
        already_in = [p.id for p in products_list]
        needed = 8 - len(products_list)
        additional_products = Product.objects.exclude(id__in=already_in)[:needed]
        for prod in additional_products:
            prod.total_sold = 0
            products_list.append(prod)

    categories = Category.objects.all()

    return render(request, 'marketplace/bestseller.html', {
        'products': products_list,
        'categories': categories
    })


def product_detail(request, product_id):
    """
    Menampilkan detail produk berdasarkan ID yang dipilih dari halaman katalog.
    """
    try:
        # Ambil produk aktif berdasarkan ID
        product = Product.objects.get(id=product_id, deleted_at__isnull=True)
        if product.price is not None:
            try:
                product.formatted_price = f"Rp{int(product.price):,}".replace(",", ".")
            except Exception:
                product.formatted_price = f"Rp{product.price}"
        else:
            product.formatted_price = "Rp0"

        is_wishlisted = False
        if request.user.is_authenticated:
            is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()

        context = {
            'product': product,
            'is_wishlisted': is_wishlisted,
        }
        return render(request, 'marketplace/product_detail.html', context)
    except Product.DoesNotExist:
        return render(request, '404.html', status=404)


@login_required
def toggle_wishlist(request, product_id=None):
    """Toggle wishlist. Accepts either:
    - POST to /wishlist/toggle/ with JSON body {"product_id": 123}
    - POST to /wishlist/toggle/<int:product_id>/ (no body)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method tidak diizinkan.'}, status=405)

    pid = product_id
    # Try JSON body first
    if not pid:
        try:
            if request.content_type and 'application/json' in request.content_type:
                payload = json.loads(request.body.decode('utf-8') or '{}')
                pid = payload.get('product_id')
        except Exception:
            pid = None

    # Fallback to form-encoded POST
    if not pid:
        pid = request.POST.get('product_id')

    if not pid:
        return JsonResponse({'success': False, 'message': 'product_id diperlukan.'}, status=400)

    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'product_id harus berupa angka.'}, status=400)

    product = get_object_or_404(Product, id=pid, deleted_at__isnull=True)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
        return JsonResponse({'success': True, 'liked': False, 'action': 'removed'})

    Wishlist.objects.create(user=request.user, product=product)
    return JsonResponse({'success': True, 'liked': True, 'action': 'added'})


@login_required
def wishlist_view(request):
    wishlisted_products = Product.objects.filter(wishlisted_by__user=request.user, deleted_at__isnull=True)
    for prod in wishlisted_products:
        if prod.price is not None:
            try:
                prod.formatted_price = f"Rp{int(prod.price):,}".replace(",", ".")
            except Exception:
                prod.formatted_price = f"Rp{prod.price}"
        else:
            prod.formatted_price = "Rp0"

    context = {
        'products': wishlisted_products,
        'total_products': wishlisted_products.count(),
        'categories': Category.objects.filter(parent__isnull=True).order_by('name'),
        'current_category': '',
        'category_title': 'Wishlist Saya',
        'category_breadcrumb': 'Home > Wishlist',
        'category_description': 'Produk yang Anda simpan untuk dilihat kembali nanti.',
    }
    return render(request, 'marketplace/wishlist.html', context)


def _items_exist(items):
    if hasattr(items, 'exists'):
        return items.exists()
    return bool(items)


def _items_delete(items):
    if hasattr(items, 'delete'):
        items.delete()


@login_required
def buy_now(request, product_id):
    """Buat sesi checkout untuk satu produk dan langsung arahkan ke halaman checkout."""
    if request.user.is_superuser or request.user.is_staff:
        messages.error(request, 'Akun Admin/Staff tidak diizinkan melakukan transaksi pembelian.')
        return redirect('katalog')

    product = get_object_or_404(Product, id=product_id, deleted_at__isnull=True)
    if product.stock <= 0:
        messages.error(request, 'Maaf, produk tidak tersedia untuk dibeli langsung.')
        return redirect('product_detail', product_id=product.id)

    request.session['buy_now_product_id'] = product.id
    request.session['buy_now_quantity'] = 1
    return redirect('checkout')


def _get_midtrans_client(request=None):
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '')
    is_production = getattr(settings, 'MIDTRANS_IS_PRODUCTION', False)

    if not server_key:
        if request:
            messages.error(request, 'MIDTRANS_SERVER_KEY tidak ditemukan atau kosong. Periksa settings.py.')
        print('Midtrans settings missing: MIDTRANS_SERVER_KEY kosong')
        return None

    try:
        return midtransclient.Snap(
            is_production=is_production,
            server_key=server_key
        )
    except Exception as e:
        if request:
            messages.error(request, 'Gagal membuat Midtrans client. Periksa server key atau koneksi jaringan.')
        print('Midtrans client init failed:', str(e))
        return None


def _create_midtrans_transaction(order, shipping_name, phone, address_full, city, province, district, postal_code, courier, total_amount, shipping_cost, grand_total, request=None):
    client = _get_midtrans_client(request=request)
    if not client:
        return None

    try:
        order_id_midtrans = f"KUCADI-{order.id}-{int(time.time())}"
        gross_amount = int((Decimal(total_amount) + Decimal(shipping_cost)).quantize(Decimal('1')))
        print(f'INFO MIDTRANS: order_id={order_id_midtrans}, gross_amount={gross_amount}')

        payload = {
            'transaction_details': {
                'order_id': order_id_midtrans,
                'gross_amount': gross_amount,
            },
            'customer_details': {
                'first_name': shipping_name,
                'phone': phone,
                'billing_address': {
                    'first_name': shipping_name,
                    'phone': phone,
                    'address': address_full,
                    'city': city,
                    'postal_code': postal_code or '',
                    'country_code': 'IDN',
                },
                'shipping_address': {
                    'first_name': shipping_name,
                    'phone': phone,
                    'address': address_full,
                    'city': city,
                    'postal_code': postal_code or '',
                    'country_code': 'IDN',
                }
            },
            'callbacks': {
                'finish': 'http://127.0.0.1:8000/cart/checkout/',
                'error': 'http://127.0.0.1:8000/cart/checkout/',
                'pending': 'http://127.0.0.1:8000/cart/checkout/'
            },
            'custom_expiry': {
                'expiry_duration': 30,
                'unit': 'minute'
            }
        }

        try:
            response = client.create_transaction(payload)
            snap_token = response.get('token') or response.get('snap_token')
            if snap_token:
                order.midtrans_token = snap_token
                order.save(update_fields=['midtrans_token'])

            return {
                'snap_token': snap_token,
                'redirect_url': response.get('redirect_url'),
                'midtrans_order_id': order_id_midtrans,
            }
        except Exception as e:
            print('=== ERROR MIDTRANS DETAIL ===', str(e))
            print('ERROR MIDTRANS ASLI:', str(e))
            if request:
                messages.error(request, f'Gagal menghubungkan ke Midtrans: {str(e)}')
            return None
    except Exception as e:
        print('❌ Midtrans transaction creation failed:', str(e))
        if request:
            messages.error(request, 'Terjadi kesalahan saat membuat transaksi Midtrans. Silakan coba lagi nanti.')
        return None


# =========================================================================
# BARU: Fungsi untuk memproses penambahan produk ke keranjang belanja
# =========================================================================
@login_required
def add_to_cart(request, product_id):
    """
    Fungsi backend untuk memproses penambahan produk ke keranjang belanja.
    Hanya bisa diakses oleh user yang sudah login terautentikasi.
    """
    if request.user.is_superuser or request.user.is_staff:
        messages.error(request, 'Akun Admin/Staff tidak diizinkan melakukan transaksi pembelian.')
        return redirect('katalog')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, deleted_at__isnull=True)
        
        # Mengambil jumlah kuantitas yang dikirim dari form input template
        quantity = int(request.POST.get('quantity', 1))
        
        # Validasi batas stok keamanan backend
        if quantity > product.stock:
            messages.error(request, f"Gagal menambahkan. Stok yang tersedia hanya {product.stock} item.")
            return redirect('product_detail', product_id=product.id)
            
        # Dapatkan (atau buat) cart untuk user
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Tambah atau update CartItem
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not created:
            # Tambahkan quantity, tetapi jangan melebihi stok
            new_qty = item.quantity + quantity
            if new_qty > product.stock:
                item.quantity = product.stock
                messages.warning(request, f"Jumlah diubah sehingga tidak melebihi stok ({product.stock}).")
            else:
                item.quantity = new_qty
            item.save()
        messages.success(request, f"{product.name} sebanyak {quantity} item berhasil dimasukkan ke keranjang!")
        return redirect('product_detail', product_id=product.id)
        
    return redirect('katalog')


@login_required
def cart_detail(request):
    """Tampilkan halaman isi keranjang untuk user yang login."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    total_price = sum([(item.product.price * item.quantity) for item in items]) if items else 0

    context = {
        'cart': cart,
        'items': items,
        'total_price': total_price,
    }
    return render(request, 'marketplace/cart_detail.html', context)


@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        try:
            quantity = int(request.POST.get('quantity', item.quantity))
        except ValueError:
            quantity = item.quantity

        if quantity <= 0:
            item.delete()
            messages.success(request, 'Item dihapus dari keranjang.')
        else:
            if quantity > item.product.stock:
                item.quantity = item.product.stock
                messages.warning(request, f"Jumlah dikurangi agar tidak melebihi stok ({item.product.stock}).")
            else:
                item.quantity = quantity
            item.save()
            messages.success(request, 'Kuantitas berhasil diperbarui.')
    return redirect('cart_detail')


@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item dihapus dari keranjang.')
    return redirect('cart_detail')


def _generate_invoice_number():
    return f"KCD{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@login_required
def checkout(request):
    if request.user.is_superuser or request.user.is_staff:
        messages.error(request, 'Akun Admin/Staff tidak diizinkan melakukan transaksi pembelian.')
        return redirect('katalog')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    direct_product_id = request.session.get('buy_now_product_id')
    direct_quantity = int(request.session.get('buy_now_quantity', 1) or 1)

    if direct_product_id:
        direct_product = Product.objects.filter(id=direct_product_id, deleted_at__isnull=True).first()
        if direct_product and direct_product.stock > 0:
            items = [type('DirectItem', (), {'product': direct_product, 'quantity': direct_quantity})()]
            has_items = True
            direct_checkout = True
        else:
            request.session.pop('buy_now_product_id', None)
            request.session.pop('buy_now_quantity', None)
            items = cart.items.select_related('product')
            has_items = items.exists()
            direct_checkout = False
    else:
        items = cart.items.select_related('product')
        has_items = items.exists()
        direct_checkout = False

    # 1. PERHITUNGAN BERAT DAN HARGA
    # Menghitung total berat dan harga dengan aman
    total_weight = sum(item.product.weight * item.quantity for item in items)
    total_price = sum(item.product.price * item.quantity for item in items)
    
    # 2. INISIALISASI VARIABEL UNTUK FORM & ONGKIR
    courier_rates = []
    city_name = ''
    province = ''
    district = ''
    postal_code = ''
    address_full = ''
    shipping_address = ''
    latitude = ''
    longitude = ''
    shipping_name = request.user.get_full_name() or request.user.username
    nomor_telepon = getattr(request.user, 'phone', '')
    if nomor_telepon is None or str(nomor_telepon) == 'None':
        nomor_telepon = ''
    selected_rate = ''
    selected_cost = Decimal('0.00')
    shipping_calculated = False
    if request.method == 'POST' and 'process_order' in request.POST:
        try:
            if not _items_exist(items):
                return JsonResponse({'success': False, 'message': 'Keranjang kosong.'}, status=400)

            # Ambil semua field dari FormData (BUKAN dari JSON body!)
            nomor_telepon = request.POST.get('nomor_telepon', '').strip()
            shipping_name = request.POST.get('shipping_name', '').strip()
            address_full = request.POST.get('address_full', '').strip()
            shipping_address = request.POST.get('shipping_address', '').strip()
            latitude = request.POST.get('latitude', '').strip()
            longitude = request.POST.get('longitude', '').strip()
            province = request.POST.get('province', '').strip()
            city_name = request.POST.get('city_name', '').strip()
            district = request.POST.get('district', '').strip()
            postal_code = request.POST.get('postal_code', '').strip()
            selected_rate = request.POST.get('selected_rate', '').strip()

            # Validasi field yang wajib diisi
            # REQUIRED: shipping_name, nomor_telepon, address_full, city_name, selected_rate
            # OPTIONAL: latitude, longitude (fallback ke 0), postal_code, shipping_address, district
            
            required_fields = {
                'Nama Penerima': shipping_name,
                'Nomor Telepon': nomor_telepon,
                'Alamat Lengkap': address_full,
                'Kota/Kabupaten': city_name,
                'Kurir': selected_rate,
            }
            
            missing_fields = [field_name for field_name, value in required_fields.items() if not value]
            
            if missing_fields:
                error_msg = f"Lengkapi field berikut: {', '.join(missing_fields)}"
                print(f"⚠️ Validation Error: {error_msg}")
                print(f"  - shipping_name: '{shipping_name}'")
                print(f"  - nomor_telepon: '{nomor_telepon}'")
                print(f"  - address_full: '{address_full}'")
                print(f"  - city_name: '{city_name}'")
                print(f"  - selected_rate: '{selected_rate}'")
                
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)

            # Jika city_name berisi ID angka, ubah jadi nama teks asli sebelum disimpan ke DB
            actual_city_name = city_name
            actual_province = province
            
            if str(city_name).isdigit():
                city_info = get_local_city_info(city_name)
                if city_info:
                    actual_city_name = city_info['city_name']
                    actual_province = city_info['province']
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Kota tidak ditemukan dalam database lokal.'
                    }, status=404)
            else:
                # Validasi city_name text juga
                city_info = get_local_city_info(city_name)
                if city_info:
                    actual_city_name = city_info['city_name']
                    actual_province = city_info['province']

            # Parse selected_rate format: "Courier||Service||Cost"
            courier = ''
            shipping_cost = Decimal('0.00')
            
            if selected_rate:
                try:
                    parts = selected_rate.split('||')
                    if len(parts) != 3:
                        raise ValueError(f"Format rate invalid: expected 3 parts, got {len(parts)}")
                    
                    courier_name, service, cost_str = parts
                    courier = f"{courier_name.strip()} {service.strip()}".strip()
                    
                    # Convert cost string to Decimal dengan aman
                    try:
                        shipping_cost = Decimal(cost_str.strip() or '0')
                    except:
                        shipping_cost = Decimal('0')
                        
                except (ValueError, IndexError) as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Format kurir tidak valid: {str(e)}'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Pilihan kurir belum dipilih.'
                }, status=400)

            # Konversi latitude & longitude ke Decimal dengan aman
            # Jika kosong, gunakan default koordinat Indonesia (Purwokerto, Jawa Tengah)
            try:
                if latitude and str(latitude).strip():
                    lat = Decimal(latitude)
                else:
                    lat = Decimal('-7.4244')  # Default: Purwokerto
                    print(f"⚠️ Latitude kosong, menggunakan default: {lat}")
                    
                if longitude and str(longitude).strip():
                    lng = Decimal(longitude)
                else:
                    lng = Decimal('109.2300')  # Default: Purwokerto
                    print(f"⚠️ Longitude kosong, menggunakan default: {lng}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ Konversi lat/lng gagal: {str(e)}, menggunakan default")
                lat = Decimal('-7.4244')
                lng = Decimal('109.2300')

            # Pastikan stok masih mencukupi sebelum pesanan dibuat
            for item in items:
                if item.product.stock < item.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f'Stok tidak mencukupi untuk {item.product.name}. Tersedia {item.product.stock}.'
                    }, status=400)

            # Kurangi stok produk untuk memastikan ketersediaan saat menunggu pembayaran
            for item in items:
                product = item.product
                product.stock = max(0, product.stock - item.quantity)
                product.save(update_fields=['stock'])

            # Buat Order di database
            grand_total = total_price + shipping_cost
            
            order = Order.objects.create(
                user=request.user,
                invoice_number=_generate_invoice_number(),
                shipping_name=shipping_name,
                phone=nomor_telepon,
                address_full=address_full,
                shipping_address=shipping_address,
                latitude=lat,
                longitude=lng,
                province=actual_province,
                city=actual_city_name,
                district=district,
                postal_code=postal_code,
                courier=courier,
                total_amount=total_price,
                shipping_cost=shipping_cost,
                grand_total=grand_total,
                status='pending',
                expired_at=timezone.now() + timedelta(minutes=30),
            )

            # Buat OrderItem untuk setiap item di cart atau checkout langsung
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_per_unit=item.product.price
                )
                for item in items
            ]
            OrderItem.objects.bulk_create(order_items)

            # Coba membuat transaksi Midtrans Snap jika konfigurasi tersedia
            transaction_data = _create_midtrans_transaction(
                order,
                shipping_name,
                nomor_telepon,
                address_full,
                actual_city_name,
                actual_province,
                district,
                postal_code,
                courier,
                total_price,
                shipping_cost,
                grand_total,
                request=request
            )

            if not transaction_data or not transaction_data.get('snap_token'):
                # Rollback order and stock karena transaksi Midtrans gagal.
                for item in order.items.select_related('product'):
                    product = item.product
                    product.stock = (product.stock or 0) + item.quantity
                    product.save(update_fields=['stock'])
                order.status = 'cancelled'
                order.save(update_fields=['status'])

                return JsonResponse({
                    'success': False,
                    'message': 'Gagal membuat transaksi Midtrans. Pesanan dibatalkan, silakan coba kembali.'
                }, status=500)

            if direct_checkout:
                request.session.pop('buy_now_product_id', None)
                request.session.pop('buy_now_quantity', None)
            else:
                _items_delete(items)

            order_detail_url = reverse('order_detail', kwargs={'order_id': order.id})
            response_payload = {
                'success': True,
                'order_id': order.id,
                'redirect_url': order_detail_url,
                'message': 'Pesanan berhasil dibuat!'
            }

            response_payload['snap_token'] = transaction_data['snap_token']
            response_payload['midtrans_redirect_url'] = order_detail_url
            return JsonResponse(response_payload, status=201)

        except Exception as e:
            # Catch unexpected errors dan log dengan detail
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ ERROR di checkout (process_order):")
            print(f"  Message: {str(e)}")
            print(f"  Traceback:\n{error_trace}")
            print(f"  Request data: nomor_telepon={nomor_telepon}, shipping_name={shipping_name}")
            print(f"               address_full={address_full}, city_name={city_name}")
            print(f"               selected_rate={selected_rate}")
            
            return JsonResponse({
                'success': False,
                'message': f'Terjadi kesalahan saat membuat pesanan: {str(e)}'
            }, status=500)

    # 4. PENANGANAN HITUNG ONGKOS KIRIM VIA AJAX JSON (DARI PETA)
    # Sekarang gunakan try-except untuk parse JSON dengan aman
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body.decode('utf-8'))
            city_name = data.get('city_name', '').strip()
            latitude = data.get('latitude', '').strip()
            longitude = data.get('longitude', '').strip()

            if not city_name:
                return JsonResponse({'success': False, 'message': 'Nama kota wajib diisi.'}, status=400)

            city_info = get_local_city_info(city_name)
            if not city_info:
                return JsonResponse({'success': False, 'message': 'Kota tidak ditemukan.'}, status=404)

            rates = get_local_shipping_rates(city_info['city_id'], max(1, total_weight))
            return JsonResponse({
                'success': True,
                'rates': rates,
                'city': city_info['city_name'],
                'province': city_info['province'],
                'latitude': latitude,
                'longitude': longitude
            })
        except json.JSONDecodeError as e:
            # Jika parse JSON gagal, kemungkinan request body bukan JSON (mungkin FormData)
            # Ini terjadi jika header X-Requested-With ada tapi body FormData
            print(f"⚠️ JSON Parse Error (bukan JSON body): {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Request body harus JSON untuk endpoint hitung ongkir.'
            }, status=400)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ ERROR di checkout (AJAX hitung ongkir): {str(e)}")
            print(error_trace)
            
            return JsonResponse({
                'success': False,
                'message': f'Terjadi kesalahan saat menghitung ongkir: {str(e)}'
            }, status=500)

    # 5. PENANGANAN KLIK "HITUNG ONGKOS KIRIM" (FORM SUBMIT BIASA - HTML FORM)
    if request.method == 'POST' and 'calculate_shipping' in request.POST:
        city_name = request.POST.get('city_name', '').strip()
        # Pastikan kita juga mempertahankan kecamatan & kode pos saat penghitungan
        district = request.POST.get('district', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        if city_name:
            city_info = get_local_city_info(city_name)
            if city_info:
                courier_rates = get_local_shipping_rates(city_info['city_id'], max(1, total_weight))
                shipping_calculated = True

                # Kembalikan nama asli kota ke form agar tidak memunculkan angka ID di UI
                city_name = city_info['city_name']
                province = city_info['province']
            else:
                messages.error(request, 'Kota tidak ditemukan.')
        else:
            messages.error(request, 'Masukkan nama kota.')

    context = {
        'items': items,
        'has_items': has_items,
        'total_price': total_price,
        'total_weight': total_weight,
        'courier_rates': courier_rates,
        'shipping_calculated': shipping_calculated,
        'city_name': city_name,
        'province': province,
        'district': district,
        'postal_code': postal_code,
        'address_full': address_full,
        'shipping_address': shipping_address,
        'latitude': latitude,
        'longitude': longitude,
        'shipping_name': shipping_name,
        'nomor_telepon': nomor_telepon,
        'phone': nomor_telepon,
        'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
        'midtrans_is_production': getattr(settings, 'MIDTRANS_IS_PRODUCTION', False),
    }
    return render(request, 'marketplace/checkout.html', context)

@csrf_exempt
def midtrans_notification(request):
    """Endpoint untuk menerima Notification/Webhook dari Midtrans Snap.

    Midtrans mengirimkan payload JSON yang berisi `order_id` (sama dengan invoice_number)
    dan `transaction_status`. Untuk status `expire` / `cancel`, rollback stok dan set status.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('invalid json')

    order_id = payload.get('order_id') or payload.get('order_id_string')
    transaction_status = payload.get('transaction_status') or payload.get('status') or ''

    if not order_id:
        return HttpResponseBadRequest('missing order_id')

    try:
        order = Order.objects.filter(invoice_number=order_id).first()
        if not order and isinstance(order_id, str) and order_id.startswith('KUCADI-'):
            parts = order_id.split('-', 2)
            if len(parts) >= 3:
                try:
                    fallback_order_id = int(parts[1])
                    order = Order.objects.filter(id=fallback_order_id).first()
                except (ValueError, TypeError):
                    order = None

        if not order:
            return HttpResponse(status=404)

        status_lower = str(transaction_status).lower()

        # Jika sukses/settlement, tandai paid
        if status_lower in ('capture', 'settlement', 'paid'):
            order.status = 'paid'
            order.save()
            return JsonResponse({'status': 'ok'})

        # Untuk expire atau cancel, kembalikan stok dan ubah status jadi cancelled
        if status_lower in ('expire', 'expired', 'cancel', 'deny', 'failure'):
            if order.status not in ('cancelled',):
                for item in order.items.select_related('product'):
                    prod = item.product
                    prod.stock = (prod.stock or 0) + item.quantity
                    prod.save()
                order.status = 'cancelled'
                order.save()

        return JsonResponse({'status': 'ok'})
    except Exception as e:
        import traceback
        print('❌ Error processing Midtrans notification:', str(e))
        print(traceback.format_exc())
        return HttpResponse(status=500)


@csrf_exempt
def midtrans_webhook(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest('invalid json')

    order_id = data.get('order_id')
    transaction_status = data.get('transaction_status') or data.get('status')

    if not order_id or not transaction_status:
        return HttpResponseBadRequest('missing order_id or transaction_status')

    try:
        if isinstance(order_id, str) and order_id.startswith('KUCADI-'):
            parts = order_id.split('-', 2)
            if len(parts) >= 3:
                order = Order.objects.get(id=int(parts[1]))
            else:
                return HttpResponseBadRequest('invalid order_id format')
        else:
            order = Order.objects.get(invoice_number=order_id)

        status_lower = str(transaction_status).lower()
        if status_lower == 'expire':
            order.status = 'expired'
        elif status_lower == 'cancel':
            order.status = 'cancelled'
        elif status_lower in ('deny', 'failure'):
            order.status = 'cancelled'
        elif status_lower in ('settlement', 'capture', 'paid'):
            order.status = 'paid'

        order.save(update_fields=['status'])
        return JsonResponse({'status': 'ok', 'order_status': order.status})

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error'}, status=405)


def normalize_city_query(query):
    if not query:
        return ''

    normalized = str(query).lower().strip()
    normalized = normalized.replace('regency', '').replace('kabupaten', '').replace('kab.', '').replace('kota', '').strip()

    alias_map = {
        'purwokerto': 'banyumas',
        'kota purwokerto': 'banyumas',
        'kabupaten purwokerto': 'banyumas',
        'purwokerto selatan': 'banyumas',
        'purwokerto utara': 'banyumas',
        'purwokerto timur': 'banyumas',
        'purwokerto barat': 'banyumas',
    }

    return alias_map.get(normalized, normalized)


def find_local_city_by_id(city_id):
    try:
        target_id = int(city_id)
    except (ValueError, TypeError):
        return None

    for cities in DATA_KOTA_LOKAL.values():
        for city in cities:
            if int(city['city_id']) == target_id:
                return city
    return None


def get_local_province_name(province_id):
    province_id = str(province_id)
    for province in DATA_PROVINSI_LOKAL:
        if str(province['province_id']) == province_id:
            return province['province']
    return ''


def get_local_city_info(query):
    if str(query).isdigit():
        city = find_local_city_by_id(query)
        if city:
            return {
                'city_id': city['city_id'],
                'city_name': city['city_name'],
                'province': get_local_province_name(city['province_id']),
                'province_id': city['province_id'],
            }
        return None

    normalized_query = normalize_city_query(query)
    for cities in DATA_KOTA_LOKAL.values():
        for city in cities:
            city_name = city['city_name'].lower()
            if normalized_query == city_name or normalized_query in city_name or city_name in normalized_query:
                return {
                    'city_id': city['city_id'],
                    'city_name': city['city_name'],
                    'province': get_local_province_name(city['province_id']),
                    'province_id': city['province_id'],
                }
    return None


def get_local_shipping_rates(city_id, total_weight):
    try:
        city_id = int(city_id)
    except (ValueError, TypeError):
        return []

    province_id = None
    for pid, cities in DATA_KOTA_LOKAL.items():
        for city in cities:
            if int(city['city_id']) == city_id:
                province_id = int(pid)
                break
        if province_id is not None:
            break

    if province_id == 10:
        cost_base = 20000 if city_id == 24 else 35000
    elif province_id == 5:
        cost_base = 40000
    elif province_id == 9:
        cost_base = 55000
    elif province_id == 6:
        cost_base = 60000
    elif province_id == 3:
        cost_base = 65000
    elif province_id == 11:
        cost_base = 75000
    else:
        cost_base = 80000

    courier_list = ['jne', 'tiki', 'pos']
    rates = []

    for courier in courier_list:
        if courier == 'jne':
            cost_value = cost_base
        elif courier == 'tiki':
            cost_value = cost_base + 2000
        else:
            cost_value = cost_base + 1000

        if total_weight > 10000:
            cost_value += 5000
        elif total_weight > 5000:
            cost_value += 2500

        rates.append({
            'courier': courier.upper(),
            'service': 'REG',
            'description': f'Biaya layanan {courier.upper()}',
            'cost': cost_value,
            'etd': '1-2 Hari',
        })

    return rates


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related('product')
    total_items = sum(item.quantity for item in items)
    # Jika pesanan masih pending dan belum memiliki midtrans_token, cobalah membuat transaksi Snap
    if order.status == 'pending' and not order.midtrans_token:
        try:
            tx = _create_midtrans_transaction(
                order,
                order.shipping_name,
                order.phone,
                order.address_full,
                order.city,
                order.province,
                order.district,
                order.postal_code,
                order.courier,
                order.total_amount,
                order.shipping_cost,
                order.grand_total,
            )
            if tx and tx.get('snap_token'):
                # order.midtrans_token sudah di-set oleh _create_midtrans_transaction
                pass
        except Exception as e:
            print('❌ Gagal membuat Midtrans token di order_detail:', str(e))

    context = {
        'order': order,
        'items': items,
        'total_items': total_items,
        'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
        'midtrans_is_production': getattr(settings, 'MIDTRANS_IS_PRODUCTION', False),
    }
    return render(request, 'marketplace/order_detail.html', context)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'marketplace/order_history.html', {'orders': orders})


@login_required
def confirm_order_received(request, order_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ('dikirim', 'shipped'):
        order.status = 'completed'
        order.save(update_fields=['status'])
        messages.success(request, 'Pesanan telah dikonfirmasi diterima. Status diubah menjadi Selesai.')
    else:
        messages.error(request, 'Pesanan tidak dapat dikonfirmasi karena status belum Dikirim.')

    return redirect('order_history')


def helpdesk(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, 'Semua kolom harus diisi.')
            return redirect('helpdesk')

        CustomerService.objects.create(
            name=name,
            email=email,
            phone_number=phone_number,
            subject=subject,
            message=message_text,
        )
        messages.success(request, 'Keluhan Anda telah terkirim. Tim Customer Service akan segera menghubungi Anda.')
        return redirect('helpdesk')

    return render(request, 'marketplace/helpdesk.html')


def panduan_rakit(request):
    """Display all assembly guide videos configured in the admin."""
    panduan_list = PanduanRakit.objects.all()
    return render(request, 'marketplace/panduan_rakit.html', {'panduan_list': panduan_list})


# =========================================================================
# BARU: ENDPOINT AJAX UNTUK MENYUPLAI DATA DROPDOWN DI FRONTEND
# =========================================================================
# 1. UBAH NAMA FUNGSI INI (Hilangkan kata '_get')
def api_provinces(request):
    """Mengambil daftar provinsi dari master data lokal."""
    return JsonResponse({'success': True, 'data': DATA_PROVINSI_LOKAL})

# 2. TAMBAHKAN FUNGSI INI (Untuk mengambil data kota berdasarkan provinsi)
def api_cities(request):
    """Mengambil daftar kota dari master data lokal berdasarkan ID provinsi dari query string."""
    province_id = request.GET.get('province_id')
    cities = DATA_KOTA_LOKAL.get(str(province_id), []) if province_id else []
    return JsonResponse({'success': True, 'data': cities})

def api_check_cost(request):
    """Menghitung biaya ongkir berdasarkan kota tujuan, berat, dan kurir."""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            destination_city = int(data.get('city_id', 0) or 0)
            courier = data.get('courier', 'jne').lower()
            total_weight = int(data.get('weight', 1000) or 1000)

            province_id = None
            for pid, cities in DATA_KOTA_LOKAL.items():
                for city in cities:
                    if int(city['city_id']) == destination_city:
                        province_id = int(pid)
                        break
                if province_id is not None:
                    break

            if province_id == 10:
                cost_base = 20000 if destination_city == 24 else 35000
            elif province_id == 5:
                cost_base = 40000
            elif province_id == 9:
                cost_base = 55000
            elif province_id == 6:
                cost_base = 60000
            elif province_id == 3:
                cost_base = 65000
            elif province_id == 11:
                cost_base = 75000
            else:
                cost_base = 80000

            if courier == 'jne':
                cost_value = cost_base
            elif courier == 'tiki':
                cost_value = cost_base + 2000
            else:
                cost_value = cost_base + 1000

            if total_weight > 10000:
                cost_value += 5000
            elif total_weight > 5000:
                cost_value += 2500

            rates = [{
                'courier': courier.upper(),
                'service': 'REG',
                'description': f'Biaya layanan {courier.upper()}',
                'cost': cost_value,
                'etd': '1-2 Hari'
            }]

            return JsonResponse({'success': True, 'rates': rates})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Metode tidak diizinkan.'}, status=400)
