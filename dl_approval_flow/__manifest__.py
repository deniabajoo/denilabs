# Copyright 2026 Deni Labs
{
    "name": "Deni Labs: Approval Flow",
    "version": "19.0.1.0.2",
    "summary": "Mesin persetujuan multi-tahap yang dapat dikonfigurasi untuk model Odoo apapun",
    "description": """
Deni Labs: Approval Flow — Mesin Persetujuan Multi-Tahap untuk Odoo 19
=======================================================================

Modul ini menyediakan sistem persetujuan (approval) yang fleksibel, dapat
dikonfigurasi, dan bisa diterapkan ke **model Odoo manapun** tanpa harus
memodifikasi kode modul yang sudah ada.

Fitur Utama
-----------

🔧 **Konfigurasi Workflow Berbasis UI**
    - Buat dan kelola konfigurasi workflow persetujuan langsung dari antarmuka
      Odoo tanpa menulis kode.
    - Pilih model target (Sale Order, Purchase Order, Invoice, dll.) dari
      dropdown.
    - Tentukan filter domain opsional untuk membatasi record mana saja yang
      memerlukan persetujuan (contoh: hanya SO dengan total ≥ Rp10.000.000).
    - Urutan prioritas konfigurasi — jika ada beberapa config untuk satu
      model, yang pertama cocok (berdasarkan sequence) yang digunakan.

📊 **Multi-Tahap Persetujuan (Approval Stages)**
    - Definisikan tahapan persetujuan berlapis (multi-level) per workflow.
    - Setiap tahap diproses secara berurutan berdasarkan nomor urut (sequence).
    - Tiga strategi penentuan approver per tahap:
        • **Specific User** — pengguna tetap yang ditentukan secara manual.
        • **User Group** — semua anggota grup keamanan Odoo; opsi untuk
          mengharuskan semua anggota grup menyetujui.
        • **Dynamic Field** — ambil approver dari field Many2one(res.users)
          pada dokumen sumber (misal: user_id, responsible_id).
    - User eskalasi (escalation user) per tahap untuk tindak lanjut jika
      melewati batas waktu.

📝 **Approval Request & Lifecycle**
    - Setiap pengajuan persetujuan menghasilkan record Approval Request
      dengan nomor referensi otomatis (sequence).
    - Siklus hidup lengkap:
        Draft → Pending Approval → Approved ✅
        Draft → Pending Approval → Rejected ❌
        Draft → Pending Approval → Returned 🔄 → Resubmit
    - Riwayat persetujuan (Approval History) tercatat per tahap, termasuk
      siapa yang menyetujui/menolak, kapan, dan alasannya.
    - Status persetujuan secara otomatis diperbarui pada dokumen sumber.

🔒 **Kontrol Akses & Keamanan**
    - Sistem grup keamanan: Approval User dan Approval Manager.
    - Hanya approver yang berwenang pada tahap saat ini yang bisa
      menyetujui, menolak, atau mengembalikan request.
    - Approval Manager memiliki akses penuh untuk bertindak pada semua
      tahap dan semua request.
    - Record rule multi-company untuk isolasi data antar perusahaan.

🧩 **Approval Mixin — Integrasi Zero-Touch**
    - Model AbstractModel `approval.mixin` menyediakan:
        • Field `approval_state` (Selection) untuk tracking status.
        • Smart button counter `approval_request_count`.
        • Method `action_submit_for_approval()` untuk memulai workflow.
        • Method `action_view_approval_requests()` untuk navigasi.
    - Untuk menambahkan approval ke model baru, cukup inherit mixin
      ini — tidak perlu menulis logika approval dari nol.

📦 **Integrasi Sale Order (Contoh Implementasi)**
    - Modul ini sudah menyertakan integrasi bawaan dengan Sale Order
      (`sale.order`) sebagai contoh implementasi.
    - Konfirmasi pesanan otomatis diblokir jika persetujuan belum selesai.
    - Tombol "Submit for Approval" dan badge status ditampilkan di form SO.
    - Reset ke draft otomatis mengembalikan status approval ke awal.

📧 **Notifikasi Email Otomatis**
    - Template email otomatis dikirim ke setiap approver saat request
      berpindah ke tahap mereka.
    - Notifikasi berisi informasi dokumen, nama workflow, dan link ke
      approval request.
    - Penanganan error — kegagalan pengiriman email tidak memblokir proses
      persetujuan.

⏰ **Eskalasi Otomatis (Cron Job)**
    - Scheduled action harian memeriksa semua request yang melewati
      batas waktu (deadline).
    - Request yang terlambat menghasilkan notifikasi chatter kepada
      escalation user yang ditentukan per tahap.
    - Jumlah hari eskalasi dapat dikonfigurasi per workflow (default: 7
      hari).

🗒️ **Audit Trail Lengkap via Chatter**
    - Semua perubahan status tercatat di chatter dokumen sumber:
        • Pembuatan request persetujuan
        • Perpindahan antar tahap (siapa yang approve, tahap mana)
        • Penolakan dan pengembalian beserta alasannya
        • Status akhir (approved/rejected)
    - Chatter juga aktif di model Approval Request itu sendiri.

📊 **OWL Dashboard — "My Pending Approvals"**
    - Dashboard OWL interaktif di backend menampilkan daftar persetujuan
      yang menunggu tindakan pengguna saat ini.
    - Live count badge memudahkan monitoring tanpa membuka menu.

🤖 **Server Action & Automated Action**
    - Server action bawaan `action_server_submit_approval` memungkinkan
      integrasi dengan Automated Actions (Base Automation).
    - Otomatisasi pengajuan persetujuan berdasarkan trigger seperti
      pembuatan record, perubahan field, atau jadwal tertentu.

💼 **Reject/Return Wizard**
    - Wizard modal untuk memasukkan alasan wajib sebelum menolak
      (reject) atau mengembalikan (return) request.
    - Alasan tercatat di history line dan diposting di chatter.

🏢 **Multi-Company Support**
    - Setiap konfigurasi workflow dapat dibatasi per perusahaan.
    - Record rule memastikan isolasi data antar company.
    - Mendukung penuh lingkungan multi-company Odoo.

Model yang Disediakan
---------------------
- `approval.workflow.config` — Konfigurasi master workflow persetujuan
- `approval.workflow.stage` — Tahapan dalam workflow
- `approval.request` — Request persetujuan per dokumen
- `approval.request.line` — Riwayat aksi per tahap (audit trail)
- `approval.mixin` — Abstract mixin untuk integrasi model
- `approval.action.wizard` — Wizard reject/return

Dependensi
----------
- base, mail, base_automation, sale
    """,
    "author": "Deni Labs",
    "website": "https://www.denilabs.com",
    "category": "Technical",
    "depends": ["base", "mail", "base_automation", "sale"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/approval_sequence.xml",
        "data/approval_email_template.xml",
        "data/approval_workflow_data.xml",
        "data/approval_cron.xml",
        "data/approval_server_action.xml",
        "views/approval_workflow_config_views.xml",
        "views/approval_request_views.xml",
        "views/sale_order_views.xml",
        "wizard/approval_action_wizard_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dl_approval_flow/static/src/js/my_approvals_dashboard.js",
            "dl_approval_flow/static/src/xml/my_approvals_dashboard.xml",
            "dl_approval_flow/static/src/scss/my_approvals_dashboard.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
    "images": ["static/description/images/Screenshot8-dashboard-screen.png"],
}
