# Panduan Pengguna: Deni Labs Approval Flow (Odoo 19)

Selamat datang di panduan resmi penggunaan modul **Deni Labs: Approval Flow**. Modul ini dirancang untuk memberikan fleksibilitas maksimal dalam mengatur alur persetujuan (workflow) pada berbagai dokumen di Odoo tanpa memerlukan koding tambahan untuk setiap model.

---

## 1. Persiapan & Konfigurasi Awal

Sebelum mulai membuat alur persetujuan, pastikan pengguna (user) memiliki hak akses yang tepat.

**Pengaturan Hak Akses:**
1. Masuk ke Odoo dengan akun Administrator.
2. Buka menu **Settings > Users & Companies > Users**.
3. Pilih pengguna yang ingin diatur.
4. Pada tab **Access Rights**, cari bagian **Approvals**:
   - **Approval User**: Dapat mengajukan persetujuan, melihat permintaan sendiri, dan bertindak sebagai approver jika ditugaskan.
   - **Approval Manager**: Memiliki hak penuh untuk membuat konfigurasi workflow, melihat semua pengajuan, dan menyetujui tahap mana pun (Hak Akses Super/Bypass).

---

## 2. Cara Membuat Alur Persetujuan (Workflow)

Hanya **Approval Manager** yang dapat mengakses menu konfigurasi ini.

1. Buka aplikasi **Approvals** dari menu utama Odoo.
2. Buka menu **Configuration > Approval Workflows**.
3. Klik tombol **New** (Baru).

### Penjelasan Field Utama:
- **Name**: Nama workflow (contoh: "Persetujuan PO Nilai Tinggi").
- **Model**: Pilih model dokumen Odoo yang akan dikenakan persetujuan (contoh: `Sales Order`, `Purchase Order`).
- **Filter Domain**: Kondisi kapan workflow ini berlaku. Jika kosong `[]`, maka berlaku untuk **semua** dokumen di model tersebut.
- **Sequence**: Urutan prioritas. Jika ada beberapa workflow untuk 1 model, yang sekuensnya paling kecil dan domainnya cocok akan digunakan.
- **Escalation After (Days)**: Batas waktu sebelum sistem mengirimkan pengingat (notifikasi eskalasi) otomatis.

### Menambahkan Tahapan (Stages)
Di tab **Approval Stages**, klik *Add a line* untuk menambah tahap persetujuan:
1. **Stage Name**: Nama tahap (contoh: "Review Finance").
2. **Approver Type**:
   - **Specific User**: Selalu dikirim ke pengguna tertentu.
   - **User Group**: Dikirim ke grup/departemen tertentu (opsi: butuh persetujuan 1 orang saja atau semua orang di grup tsb).
   - **Dynamic Field**: Mengambil field bertipe *User* (Many2one res.users) dari dokumen asli (contoh: `user_id` atau Salesperson dokumen).

---

## 3. Skenario & Contoh Penggunaan

Berikut adalah 3 skenario implementasi di lapangan:

### Skenario 1: Persetujuan Sederhana (Sales Order Biasa)
**Tujuan**: Semua Sales Order (SO) harus disetujui oleh Manajer Penjualan sebelum bisa dikonfirmasi.
* **Model**: Sales Order (`sale.order`)
* **Filter Domain**: `[]` (Berlaku untuk semua)
* **Approval Stages (1 Tahap)**:
  - Stage Name: "Approval Sales Manager"
  - Approver Type: **Specific User**
  - Approver: Budi (Manajer Sales)

**Hasil**: Saat Sales membuat SO, tombol *Confirm* ditahan. Sales harus klik *Submit for Approval*. Budi akan mendapat notifikasi dan harus menyetujuinya agar SO bisa dikonfirmasi.

---

### Skenario 2: Persetujuan Berjenjang & Bersyarat (Purchase Order > Rp 10 Juta)
**Tujuan**: PO di atas Rp 10.000.000 butuh persetujuan berjenjang: Pertama oleh Manajer Departemen (dinamis), lalu oleh Direktur Keuangan.
* **Model**: Purchase Order (`purchase.order`)
* **Filter Domain**: `[('amount_total', '>=', 10000000)]`
* **Approval Stages (2 Tahap)**:
  1. **Tahap 1**:
     - Name: "Approval Manajer Pembuat"
     - Approver Type: **Dynamic Field**
     - User Field: Referensi ke field atasan si pembuat PO.
  2. **Tahap 2**:
     - Name: "Approval Direktur Keuangan"
     - Approver Type: **Specific User**
     - Approver: Siti (Direktur Keuangan)

**Hasil**: Jika total PO hanya 5 juta, dokumen lolos tanpa approval. Jika 15 juta, masuk ke atasan masing-masing pembuat PO. Setelah atasan setuju, notifikasi baru dikirim ke Siti.

---

### Skenario 3: Persetujuan Grup (Customer Invoice / Tagihan)
**Tujuan**: Tagihan besar membutuhkan persetujuan **salah satu** anggota dari divisi Finance.
* **Model**: Journal Entry / Invoice (`account.move`)
* **Filter Domain**: `[('move_type', '=', 'out_invoice'), ('amount_total', '>=', 50000000)]`
* **Approval Stages (1 Tahap)**:
  - Name: "Review Divisi Keuangan"
  - Approver Type: **User Group**
  - Approver Group: `Accounting / Accountant`
  - Require All Approvers: `Batal Centang` (Cukup 1 orang perwakilan)

**Hasil**: Seluruh anggota grup Akuntan mendapat notifikasi. Siapa pun yang pertama kali klik "Approve" akan meloloskan dokumen ini.

---

## 4. Panduan Aksi Pengguna (End-User)

### Mengajukan Persetujuan
1. Buka dokumen yang bersangkutan (misal: pesanan penjualan).
2. Klik tombol **Submit for Approval** di bagian atas kiri.
3. Status berubah menjadi **Pending Approval**. Dokumen ini sekarang terkunci/menunggu.

### Melakukan Persetujuan (Sebagai Approver)
1. Buka aplikasi **Approvals** dan lihat dasbor (My Approvals Dashboard).
2. Anda akan melihat jumlah dokumen yang menunggu tindakan Anda.
3. Klik pada dokumen, lalu Anda bisa memilih:
   - **Approve**: Menyetujui dokumen.
   - **Reject**: Menolak secara permanen (Wajib mengisi alasan).
   - **Return to Requester**: Mengembalikan untuk diperbaiki (Wajib mengisi alasan). Status akan kembali menjadi "Returned", lalu pembuat bisa merevisi dan klik Submit ulang.

### Melacak Riwayat (Audit Trail)
Setiap dokumen yang memiliki alur persetujuan memiliki tab **Approval History** (Riwayat Persetujuan) atau tercatat langsung di log **Chatter** (bagian bawah/samping kanan halaman). Anda dapat melihat secara transparan **siapa** yang menyetujui, **kapan**, dan **alasan** yang diberikan saat menolak/mengembalikan.

---

## 5. Untuk Developer: Menambahkan Model Baru

Modul ini sudah terintegrasi secara default dengan `sale.order`. Jika Anda ingin menambahkan penguncian persetujuan ke modul lain (seperti `purchase.order` atau model kustom Anda sendiri):

1. Masuk kode kustom modul (atau buat modul extension kecil).
2. `_inherit` mixin persetujuan di model Python Anda:
   ```python
   class PurchaseOrder(models.Model):
       _name = 'purchase.order'
       _inherit = ['purchase.order', 'approval.mixin']
   ```
3. Tambahkan tombol dan status di XML view:
   ```xml
   <button name="action_submit_for_approval" type="object" string="Submit for Approval"
           invisible="approval_state not in ('draft', 'returned')"/>
   <field name="approval_state" widget="badge"/>
   ```
4. Hadang method `button_confirm()` atau method eksekusi akhir Anda dengan pengecekan `approval_state`.

---
*Dibuat dengan dedikasi tinggi oleh tim Deni Labs.*
