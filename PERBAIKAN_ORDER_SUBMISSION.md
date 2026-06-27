# ✅ PERBAIKAN ORDER SUBMISSION FORM

## 📋 Ringkasan Masalah
**Masalah Lama:** Ketika tombol "Bayar & Selesaikan Pesanan" diklik, halaman berpindah ke halaman putih polos yang menampilkan JSON mentah:
```json
{"success": false, "message": "Lengkapi data alamat dan pilih kurir."}
```

**Penyebab:** Form menggunakan default HTML form submission (browser melakukan POST standar) alih-alih AJAX, sehingga browser menampilkan response sebagai plain text daripada diproses oleh JavaScript.

---

## 🔧 Solusi yang Diterapkan

### 1. **Form Structure** (checkout.html, line 21)
```html
<form method="post" class="space-y-6">
    {% csrf_token %}
    <!-- Form fields... -->
    
    <!-- DUA TOMBOL: masing-masing type="button" -->
    <button type="button" id="btn-hitunghongkir" ...>Hitung Ongkos Kirim</button>
    <button type="button" id="btn-bayar-pesanan" ...>Bayar & Selesaikan Pesanan</button>
</form>
```

**Kunci Penting:**
- `method="post"` hanya untuk metadata, tidak akan trigger default submission karena button adalah `type="button"`
- Tidak ada `action` attribute = form akan submit ke URL sekarang (`window.location.pathname`)
- Tidak ada `onsubmit` handler = kontrol penuh ada di JavaScript event listener

### 2. **JavaScript Event Listener** (checkout.html, script section)

#### **LANGKAH 1: Tangkap Click Event dengan `e.preventDefault()`**
```javascript
btnBayar.addEventListener('click', async function (e) {
    // 🔴 SANGAT PENTING: Cegah default form submission
    e.preventDefault();
    e.stopPropagation();
```

#### **LANGKAH 2: Validasi Form**
```javascript
    // Ambil referensi form
    const form = btnBayar.closest('form');
    
    // Validasi HTML5 required fields
    if (!form.checkValidity()) {
        form.reportValidity();  // Tampilkan error dari browser
        return;
    }
    
    // Validasi spesifik: kurir sudah dipilih?
    const selectedRateRadio = document.querySelector('input[name="selected_rate"]:checked');
    if (!selectedRateRadio) {
        alert('Silakan hitung ongkos kirim dan pilih kurir terlebih dahulu.');
        return;
    }
```

#### **LANGKAH 3: Set Loading State**
```javascript
    btnBayar.disabled = true;
    const originalText = btnBayar.textContent;
    btnBayar.textContent = '⏳ Memproses...';
```

#### **LANGKAH 4: Kumpulkan Data Form**
```javascript
    const formData = new FormData(form);
    formData.append('process_order', '1');  // Field khusus untuk backend
```

#### **LANGKAH 5: AJAX POST ke Backend**
```javascript
    const response = await fetch(window.location.pathname, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),  // CSRF protection
            'X-Requested-With': 'XMLHttpRequest'     // Hint ke Django ini AJAX
        },
        body: formData
    });
```

#### **LANGKAH 6: Parse Response JSON**
```javascript
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
```

#### **LANGKAH 7: Handle Response**
```javascript
    if (data.success === true) {
        // ✅ Sukses: Redirect ke halaman order detail
        if (data.redirect_url) {
            window.location.href = data.redirect_url;
        } else if (data.order_id) {
            window.location.href = `/order/${data.order_id}/`;
        }
    } else {
        // ❌ Error: Tampilkan pesan ke user, jangan reload halaman
        alert(`❌ Error: ${data.message}`);
        btnBayar.disabled = false;
        btnBayar.textContent = originalText;  // Restore button
    }
```

#### **LANGKAH 8: Error Handling**
```javascript
    } catch (error) {
        console.error('❌ AJAX Error:', error);
        alert(`❌ Gagal: ${error.message}`);
        
        // Restore button state agar user bisa retry
        btnBayar.disabled = false;
        btnBayar.textContent = originalText;
    }
```

---

## 🖥️ Backend Response Format (views.py)

Backend harus mengembalikan JSON dengan struktur:

```python
# ✅ Sukses
return JsonResponse({
    'success': True,
    'order_id': order.id,
    'redirect_url': reverse('order_detail', kwargs={'order_id': order.id}),
    'message': 'Pesanan berhasil dibuat!'
})

# ❌ Error
return JsonResponse({
    'success': False,
    'message': 'Lengkapi data alamat dan pilih kurir.'
}, status=400)
```

**Perbaikan di views.py (sudah dilakukan):**
```python
# Sebelum (line 420):
if request.method == 'POST' and 'process_order' in request.POST:
    # ... validasi dan create order ...
    return redirect('order_detail', order_id=order.id)  # ❌ SALAH!

# Sesudah:
if request.method == 'POST' and 'process_order' in request.POST:
    # ... validasi dan create order ...
    order_detail_url = reverse('order_detail', kwargs={'order_id': order.id})
    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'redirect_url': order_detail_url,
        'message': 'Pesanan berhasil dibuat!'
    })  # ✅ BENAR!
```

---

## 🧪 Cara Testing

### **Test Case 1: Form Incomplete (Harus Fail)**
1. Buka halaman `/cart/checkout/`
2. Kosongkan salah satu required field (misal: Nama Penerima)
3. Klik tombol "Bayar & Selesaikan Pesanan"
4. **Expected:** Error message "Please fill out this field" muncul dari browser validation
5. **Jangan:** Halaman tidak boleh pindah

### **Test Case 2: Kurir Belum Dipilih (Harus Fail)**
1. Isi semua required field
2. JANGAN klik "Hitung Ongkos Kirim"
3. Langsung klik "Bayar & Selesaikan Pesanan"
4. **Expected:** Alert: "Silakan hitung ongkos kirim dan pilih kurir terlebih dahulu."
5. **Jangan:** Halaman tidak boleh pindah

### **Test Case 3: Submit Sukses (Harus Succeed)**
1. Isi semua required field
2. Klik "Hitung Ongkos Kirim"
3. Tunggu sampai "Pilihan Kurir" muncul
4. Pilih salah satu radio button kurir
5. Klik "Bayar & Selesaikan Pesanan"
6. **Expected:** 
   - Tombol menjadi disabled dengan teks "⏳ Memproses..."
   - Setelah 1-2 detik, halaman pindah ke `/order/{order_id}/`
   - Halaman order detail menampilkan data pesanan
7. **Jangan:** Halaman tidak boleh menampilkan JSON mentah atau halaman putih

---

## 📊 Alur Data Lengkap

```
User klik "Bayar & Selesaikan Pesanan"
  ↓
JavaScript event listener tangkap click
  ├─ e.preventDefault() → block default form submission ✅
  ├─ Validasi form required fields
  ├─ Validasi kurir sudah dipilih
  └─ Set loading state (disable button, ganti text)
  ↓
FormData kumpulkan dari <form>
  ├─ shipping_name, nomor_telepon, province, city_name
  ├─ district, postal_code, address_full, shipping_address
  ├─ latitude, longitude
  ├─ selected_rate (dari radio button)
  ├─ csrfmiddlewaretoken (dari {% csrf_token %})
  └─ process_order: '1' (flag untuk backend)
  ↓
fetch() POST ke window.location.pathname (/cart/checkout/)
  ├─ Headers: X-CSRFToken, X-Requested-With: XMLHttpRequest
  └─ Body: FormData (multipart/form-data)
  ↓
Backend (views.py - checkout function)
  ├─ Cek 'process_order' in request.POST
  ├─ Validasi semua field
  ├─ Buat Order di database
  ├─ Buat OrderItem di database
  ├─ Delete CartItem (cart kosong)
  └─ Return JsonResponse: {success: true, redirect_url: ...}
  ↓
JavaScript parse response.json()
  ├─ Jika success == true:
  │  └─ window.location.href = redirect_url → Pindah ke order detail ✅
  └─ Jika success == false:
     ├─ alert(data.message) → Tampilkan error
     └─ Restore button state → User bisa retry
```

---

## 🐛 Troubleshooting

| Gejala | Penyebab | Solusi |
|--------|---------|--------|
| Halaman pindah ke JSON mentah | Form submit biasa, bukan AJAX | Pastikan `e.preventDefault()` dipanggil. Cek console untuk error |
| Tombol loading tapi tidak ada progress | AJAX request stuck | Cek network tab di DevTools. Backend mungkin error |
| Alert error muncul, tapi form bisa retry | Normal behavior | User perlu klik ulang tombol "Bayar" setelah memperbaiki data |
| Halaman pindah tapi order tidak dibuat | Backend error saat create Order | Cek Django logs dan database untuk error |
| CSRF token error | Cookies tidak dikirim | Pastikan `fetch()` tidak punya `credentials: 'omit'` |

---

## 📝 Debug Console

Kode sudah punya `console.log()` pada setiap langkah:

```javascript
console.log('✅ Click event tertangkap, default behavior dicegah');
console.log('✅ Kurir terpilih:', selectedRateRadio.value);
console.log('✅ Loading state aktif');
console.log('📋 Data form yang dikirim:');
console.log('🔐 CSRF Token:', csrfToken ? '✓ Ada' : '✗ MISSING!');
console.log('📡 Response status:', response.status);
console.log('📦 Response data:', data);
console.log('✅ Pesanan berhasil! Redirect ke:', data.redirect_url);
console.error('❌ AJAX Error:', error);
```

**Cara lihat Console:**
1. Buka halaman checkout di browser
2. Tekan `F12` → Tab "Console"
3. Klik tombol "Bayar & Selesaikan Pesanan"
4. Lihat message di console → Copy paste ke chat jika ada error

---

## ✅ Status Implementasi

- [x] Button: `type="button"` (bukan `type="submit"`)
- [x] Event listener: `click` event dengan `e.preventDefault()`
- [x] Form validation: HTML5 `checkValidity()`
- [x] Kurir validation: `querySelector('input[name="selected_rate"]:checked')`
- [x] Loading state: Disable button dan ganti text
- [x] FormData collection: Kumpulkan semua field form
- [x] AJAX fetch: POST dengan FormData dan CSRF header
- [x] Response handling: Parse JSON dan redirect atau show error
- [x] Error handling: try-catch dengan console.error dan alert
- [x] Button restore: Restore state jika error
- [x] Backend JSON response: Return JsonResponse dengan success/redirect_url
- [x] Console logging: Verbose logging untuk debugging
