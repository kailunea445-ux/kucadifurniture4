# KODE LENGKAP FUNGSI CHECKOUT YANG DIPERBAIKI

## Alur Request Handler (Urutan Penting!)

```python
@login_required(login_url='/login/')
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    has_items = items.exists()
    
    # Perhitung total weight & price
    total_weight = sum(item.product.weight * item.quantity for item in items)
    total_price = sum(item.product.price * item.quantity for item in items)
    
    # Inisialisasi variabel
    courier_rates = []
    city_name = ''
    province = ''
    # ... (inisialisasi lainnya)
    
    # ============================================================
    # ✅ PENANGANAN #1: SUBMIT ORDER VIA AJAX FORMDATA
    # ============================================================
    # PENTING: CEK INI LEBIH DULU SEBELUM CEK HEADER XMLHttpRequest!
    if request.method == 'POST' and 'process_order' in request.POST:
        try:
            if not items.exists():
                return JsonResponse({'success': False, 'message': 'Keranjang kosong.'}, status=400)

            # Ambil data dari FormData (request.POST)
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

            # Validasi field wajib
            if not all([nomor_telepon, shipping_name, address_full, latitude, 
                       longitude, city_name, selected_rate]):
                missing_fields = []
                if not nomor_telepon: missing_fields.append('Nomor Telepon')
                if not shipping_name: missing_fields.append('Nama Penerima')
                if not address_full: missing_fields.append('Alamat Lengkap')
                if not city_name: missing_fields.append('Kota/Kabupaten')
                if not selected_rate: missing_fields.append('Kurir')
                
                return JsonResponse({
                    'success': False,
                    'message': f'Lengkapi field berikut: {", ".join(missing_fields)}'
                }, status=400)

            # Ubah city_id menjadi city_name jika perlu
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
                city_info = get_local_city_info(city_name)
                if city_info:
                    actual_city_name = city_info['city_name']
                    actual_province = city_info['province']

            # Parse selected_rate: "JNE||Regular||50000"
            courier = ''
            shipping_cost = Decimal('0.00')
            
            if selected_rate:
                try:
                    parts = selected_rate.split('||')
                    if len(parts) != 3:
                        raise ValueError(f"Format rate invalid: expected 3 parts, got {len(parts)}")
                    
                    courier_name, service, cost_str = parts
                    courier = f"{courier_name.strip()} {service.strip()}".strip()
                    shipping_cost = Decimal(cost_str.strip() or '0')
                        
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

            # Konversi lat/lng ke Decimal AMAN
            try:
                lat = Decimal(latitude or '0')
                lng = Decimal(longitude or '0')
            except:
                lat = Decimal('0')
                lng = Decimal('0')

            # BUAT ORDER
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
            )

            # BUAT ORDER ITEMS
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
            
            # HAPUS CART ITEMS
            items.delete()

            # RETURN JSON RESPONSE
            order_detail_url = reverse('order_detail', kwargs={'order_id': order.id})
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'redirect_url': order_detail_url,
                'message': 'Pesanan berhasil dibuat!'
            }, status=201)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ ERROR di checkout (process_order): {str(e)}")
            print(error_trace)
            
            return JsonResponse({
                'success': False,
                'message': f'Terjadi kesalahan saat membuat pesanan: {str(e)}'
            }, status=500)

    # ============================================================
    # ✅ PENANGANAN #2: HITUNG ONGKIR VIA AJAX JSON (DARI PETA)
    # ============================================================
    # Sekarang menggunakan try-except untuk JSON parsing yang aman
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
            print(f"⚠️ JSON Parse Error: {str(e)}")
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

    # ============================================================
    # ✅ PENANGANAN #3: HITUNG ONGKIR VIA FORM SUBMIT BIASA
    # ============================================================
    if request.method == 'POST' and 'calculate_shipping' in request.POST:
        city_name = request.POST.get('city_name', '').strip()
        district = request.POST.get('district', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        if city_name:
            city_info = get_local_city_info(city_name)
            if city_info:
                courier_rates = get_local_shipping_rates(city_info['city_id'], max(1, total_weight))
                shipping_calculated = True
                city_name = city_info['city_name']
                province = city_info['province']
            else:
                messages.error(request, 'Kota tidak ditemukan.')
        else:
            messages.error(request, 'Masukkan nama kota.')

    # ============================================================
    # ✅ PENANGANAN #4: RENDER FORM (GET REQUEST)
    # ============================================================
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
    }
    return render(request, 'marketplace/checkout.html', context)
```

---

## Import yang Diperlukan (pastikan ada di atas file)

```python
import json
import uuid
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
# ... import models lainnya ...
```

---

## Perbandingan Sebelum vs Sesudah

### ❌ SEBELUM (BERMASALAH)
```python
# Problem: Mengecek XMLHttpRequest DULUAN
if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
    data = json.loads(request.body.decode('utf-8') or '{}')  # CRASH jika FormData!
    # ...

if request.method == 'POST' and 'process_order' in request.POST:
    # ...
```

**Hasil:** Ketika submit order dengan FormData + header XMLHttpRequest, backend masuk kondisi pertama dan crash.

### ✅ SESUDAH (BENAR)
```python
# Solusi: CEK DULUAN apakah ini FormData order submission
if request.method == 'POST' and 'process_order' in request.POST:
    # Handle FormData dengan aman
    try:
        # ...
    except Exception as e:
        # Error handling yang proper
        return JsonResponse({'success': False, ...}, status=500)

# Kemudian: Cek AJAX JSON hitung ongkir dengan try-except
if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
    try:
        data = json.loads(request.body.decode('utf-8'))  # SAFE
        # ...
    except json.JSONDecodeError as e:
        # Handle JSON parse error
        return JsonResponse({'success': False, ...}, status=400)
```

**Hasil:** FormData dan JSON requests dihandle secara terpisah dengan benar.

---

## HTTP Status Codes

- ✅ **201 Created** - Order berhasil dibuat
- ✅ **200 OK** - Hitung ongkir berhasil
- ❌ **400 Bad Request** - Validasi gagal, JSON parse error
- ❌ **404 Not Found** - Kota tidak ditemukan
- ❌ **500 Internal Server Error** - Unexpected error

---

## Debugging Tips

1. **Cek Django logs** saat request masuk:
   ```
   python manage.py runserver  # Lihat console output
   ```

2. **Cek Firefox/Chrome DevTools**:
   - Tab Network → cari request POST ke `/cart/checkout/`
   - Lihat Response body untuk JSON detail
   - Lihat Console untuk JavaScript errors

3. **Cek print() debug statements**:
   ```python
   print(f"DEBUG: received city_name = {city_name}")
   print(f"DEBUG: selected_rate = {selected_rate}")
   ```

---

## Test Data yang Berguna

**Valid selected_rate format:**
```
"JNE||Regular||50000"
"GoSend||Same Day||75000"
"Tiki||Economy||35000"
```

**Valid city_name:**
```
"Purwokerto" (text)
"3310" (city_id)
```

**Valid coordinates:**
```
latitude: "-7.4244"
longitude: "109.2300"
```
