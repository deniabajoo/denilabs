**SKRIPSI**

**IMPLEMENTASI MODUL APPROVAL TERINTEGRASI PADA**

**SISTEM ERP ODOO BERBASIS WATERFALL**

**DI PT INDOPORA**

Diajukan sebagai salah satu syarat untuk memperoleh gelar

Sarjana Komputer (S.Kom) pada Program Studi Informatika

Disusun oleh:

**IKHWANUDIN GIFARI**

NPM: 20081010241

**PROGRAM STUDI INFORMATIKA**

**FAKULTAS ILMU KOMPUTER**

**UNIVERSITAS PEMBANGUNAN NASIONAL**

**2026**

# BAB I PENDAHULUAN

## 1.1 Latar Belakang Masalah

Perkembangan teknologi informasi yang masif pada dekade terakhir telah mendorong percepatan transformasi digital di seluruh lapisan industri, termasuk sektor distribusi dan perdagangan. Salah satu wujud konkret dari transformasi digital tersebut adalah adopsi sistem Enterprise Resource Planning (ERP) yang mengintegrasikan seluruh proses bisnis perusahaan ke dalam satu platform terintegrasi. Alam et al. (2022) menegaskan bahwa pemilihan dan penerapan metodologi pengembangan yang tepat pada proyek perangkat lunak berdampak langsung terhadap kualitas produk, efisiensi waktu, dan kepuasan pemangku kepentingan.

PT Indopora merupakan perusahaan yang bergerak di bidang distribusi dan perdagangan yang berlokasi di Bandung, Jawa Barat. Dalam operasionalnya, PT Indopora memproses transaksi penjualan (Sales Order/SO) dan pembelian (Purchase Order/PO) dalam jumlah signifikan setiap harinya. Setiap transaksi-terutama yang mengandung diskon penjualan melebihi batas kewenangan atau nilai pembelian di atas ambang tertentu-memerlukan mekanisme persetujuan (approval) yang terstruktur guna memastikan kontrol keuangan dan kepatuhan terhadap kebijakan perusahaan.

Berdasarkan hasil observasi awal yang dilakukan pada bulan April 2026, ditemukan bahwa proses persetujuan pesanan penjualan dan pembelian di PT Indopora masih dilakukan secara manual melalui proses fisik berupa tanda tangan pada dokumen cetak. Kondisi tersebut menimbulkan berbagai permasalahan operasional, di antaranya: (1) keterlambatan proses persetujuan yang dapat mencapai 2-3 hari kerja; (2) tidak adanya mekanisme validasi otomatis terhadap batas diskon dan nilai transaksi yang diizinkan; (3) kesulitan dalam pelacakan status persetujuan secara real-time; dan (4) risiko terjadinya transaksi yang melebihi batas kewenangan tanpa mekanisme pengendalian yang memadai.

Sebagai respons atas tantangan tersebut, penelitian ini mengembangkan tiga custom module berbasis platform Odoo 19 Community Edition: (1) gifari_sale_discount_approval-modul approval bertingkat untuk Sales Order berdasarkan persentase diskon efektif; (2) gifari_purchase_approval-modul approval bertingkat untuk Purchase Order berdasarkan nilai pembelian (amount_untaxed); dan (3) gifari_approval_dashboard-dasbor terpusat berbasis OWL (Odoo Web Library) untuk pemantauan seluruh antrian approval secara real-time. Ketiga modul ini dikembangkan dengan menggunakan data demonstrasi (demo data) karena data operasional perusahaan bersifat rahasia (confidential).

Modul gifari_sale_discount_approval mengintervensi proses konfirmasi Sales Order dengan mendeteksi apakah effective_max_discount-yaitu nilai tertinggi antara max_line_discount (diskon tertinggi per baris) dan global_discount_percent (diskon global keseluruhan order)-melampaui threshold yang dikonfigurasi. Apabila threshold terlampaui, status approval_state pada sale.order secara otomatis berubah dari none ke pending dan sistem menciptakan aktivitas persetujuan untuk approver yang ditugaskan. Alur persetujuan bersifat sekuensial multi-level (L1 → L2 → Ln), di mana setiap level dapat dikonfigurasi dengan mode any_one (siapa saja dari daftar approver) atau all_must (seluruh approver harus menyetujui). Terdapat pula fitur counter-offer yang memungkinkan approver mengajukan nilai diskon alternatif.

Modul gifari_purchase_approval mengintegrasikan diri ke dalam mekanisme \_approval_allowed() dan button_confirm() standar Odoo. Sistem memeriksa apakah amount_untaxed Purchase Order memenuhi ambang minimum (min_amount) pada purchase.approval.level yang dikonfigurasi. Jika ya, approval_state berubah menjadi pending dan alur persetujuan multi-level diaktifkan. Modul ini juga mendukung re-approval otomatis saat PO yang telah disetujui dibuka kembali dan mengalami perubahan nilai, serta bypass untuk PO yang berasal dari Purchase Agreement.

Modul gifari_approval_dashboard menyajikan antarmuka terpusat berbasis OWL yang menampilkan KPI cards (total pending, approved today, rejected today), daftar SO dan PO yang menunggu approval beserta indikator aging (days_pending), serta log aktivitas terkini. Data diambil secara real-time melalui JSON endpoint /gifari/approval/dashboard/data yang memanggil model sale.order, purchase.order, sale.discount.approval.log, dan purchase.approval.log secara simultan.

Dalam konteks pengembangan ketiga modul tersebut, pemilihan metodologi pengembangan perangkat lunak menjadi faktor kritis yang menentukan keberhasilan proyek. Diansyah et al. (2023) menyatakan bahwa metode Waterfall-dengan pendekatan sekuensial linier yang membagi siklus pengembangan ke dalam fase-fase terurut-merupakan pilihan yang tepat untuk proyek dengan persyaratan yang stabil dan terdefinisi dengan baik (well-defined requirements), sebagaimana karakteristik pengembangan modul ERP dalam penelitian ini.

Penelitian ini bertujuan mengembangkan dan mengevaluasi efektivitas ketiga modul kustom tersebut menggunakan metode Waterfall, dengan periode penelitian berlangsung selama dua bulan, yaitu Mei hingga Juni 2026. Pengembangan dilakukan menggunakan data demonstrasi untuk menjaga kerahasiaan data perusahaan, namun tetap merepresentasikan skenario bisnis nyata PT Indopora.

## 1.2 Rumusan Masalah

Berdasarkan uraian latar belakang di atas, rumusan masalah dalam penelitian ini dijabarkan sebagai berikut:

- Bagaimana rancangan dan implementasi alur approval diskon penjualan bertingkat pada modul gifari_sale_discount_approval di platform Odoo 19 Community Edition menggunakan metode Waterfall?
- Bagaimana rancangan dan implementasi alur approval nilai pembelian bertingkat pada modul gifari_purchase_approval beserta mekanisme re-approval dan bypass Purchase Agreement?
- Bagaimana perancangan gifari_approval_dashboard sebagai pusat pemantauan terpadu menggunakan OWL untuk memvisualisasikan status approval sales dan purchase secara real-time?
- Seberapa efektif metode Waterfall dalam pengembangan ketiga custom module tersebut, diukur berdasarkan indikator KPI: efisiensi waktu, kesesuaian kebutuhan, tingkat bug, kepuasan pengguna, dan frekuensi rework?

## 1.3 Tujuan Penelitian

Penelitian ini memiliki tujuan sebagai berikut:

- Merancang dan mengimplementasikan modul gifari_sale_discount_approval dengan alur approval_state: none → pending → approved/rejected, deteksi effective_max_discount berbasis threshold level yang dikonfigurasi, mode approval any_one/all_must, fitur counter-offer, dan audit trail lengkap.
- Merancang dan mengimplementasikan modul gifari_purchase_approval dengan alur approval_state: none → pending → approved/rejected, validasi amount_untaxed bertingkat, mekanisme re-approval saat PO diubah setelah persetujuan, dan bypass untuk Purchase Agreement.
- Merancang dan mengimplementasikan modul gifari_approval_dashboard berbasis OWL yang menyajikan KPI cards, daftar antrian approval dengan aging indicator, dan log aktivitas terkini untuk kedua modul approval.
- Mengevaluasi efektivitas metode Waterfall dalam pengembangan ketiga modul tersebut menggunakan lima indikator KPI secara komprehensif.
- Memberikan rekomendasi metodologi dan arsitektur teknis yang optimal untuk pengembangan modul approval ERP serupa.

## 1.4 Batasan Penelitian

Untuk menjaga fokus dan kedalaman analisis, ditetapkan batasan penelitian sebagai berikut:

- Platform yang digunakan adalah Odoo 19 Community Edition yang berjalan pada sistem operasi Ubuntu 22.04 LTS.
- Tiga custom module yang dikembangkan: gifari_sale_discount_approval (versi 19.0.1.0.0), gifari_purchase_approval (versi 19.0.1.0.0), dan gifari_approval_dashboard (versi 19.0.1.0.0).
- Pengembangan dan pengujian dilakukan menggunakan data demonstrasi (demo data), bukan data produksi perusahaan, karena data operasional PT Indopora bersifat rahasia (confidential).
- Periode penelitian berlangsung selama dua bulan: Mei hingga Juni 2026.
- Responden evaluasi adalah staf yang terlibat dalam proses penjualan dan pembelian, berjumlah 25 orang.
- Evaluasi efektivitas dibatasi pada lima KPI: efisiensi waktu, kesesuaian kebutuhan, tingkat bug, kepuasan pengguna, dan frekuensi rework.
- Penelitian tidak mencakup integrasi dengan sistem pihak ketiga eksternal, migrasi data legacy, atau konfigurasi infrastruktur server produksi.
- Bahasa pemrograman yang digunakan adalah Python 3.11 (logika bisnis/ORM) dan JavaScript/OWL 2.0 (frontend dashboard), dengan XML untuk definisi tampilan.

## 1.5 Manfaat Penelitian

**a. Manfaat Teoritis**

Penelitian ini memberikan kontribusi ilmiah berupa (1) bukti empiris efektivitas metode Waterfall pada pengembangan modul ERP dengan persyaratan stabil; (2) dokumentasi arsitektur teknis multi-level approval berbasis state machine pada Odoo 19 Community; dan (3) referensi implementasi OWL dashboard untuk pemantauan workflow approval terintegrasi. Temuan penelitian dapat memperkaya literatur di bidang rekayasa perangkat lunak ERP, khususnya dalam konteks pengembangan modul kustom open-source.

**b. Manfaat Praktis**

- Bagi PT Indopora: Tersedianya sistem approval penjualan dan pembelian yang otomatis, terstandarisasi, dan terintegrasi dalam Odoo, sehingga meningkatkan efisiensi operasional dan kontrol keuangan perusahaan.
- Bagi Pengembang Perangkat Lunak: Panduan implementasi teknis custom module Odoo 19 Community dengan pola sequential multi-level approval yang dapat diadaptasi untuk kebutuhan serupa.
- Bagi Akademisi: Data empiris dan metodologi evaluasi efektivitas yang dapat direplikasi atau dikembangkan dalam penelitian lanjutan.
- Bagi Universitas: Kontribusi dalam pengembangan kurikulum terkait implementasi ERP open-source dan metodologi pengembangan perangkat lunak.

# BAB II TINJAUAN PUSTAKA

## 2.1 Penelitian Terdahulu

Penelusuran literatur dilakukan secara sistematis terhadap jurnal-jurnal ilmiah yang terbit dalam rentang tahun 2022-2024 melalui Google Scholar, IEEE Xplore, Portal Garba Rujukan Digital (Garuda/Sinta), dan PLOS ONE. Kriteria inklusi meliputi: (1) terbit 2022-2024; (2) membahas ERP, Odoo, atau metodologi SDLC; dan (3) memiliki DOI yang dapat diverifikasi. Berikut adalah tujuh penelitian terdahulu yang memiliki relevansi signifikan dengan penelitian ini.

### 2.1.1 Fatmawati, Kramanandita, dan Miza (2022)

Judul: "Rancangan Implementasi Enterprise Resource Planning (ERP) pada Sistem Pengelolaan Sales Order PT Jaya Mandiri Indotech"

Sumber: Jurnal Teknologi dan Manajemen, Vol. 20, No. 1, hal. 33-44, 2022. DOI: <https://doi.org/10.52330/jtm.v20i1.49>.

Penelitian ini merancang dan mengimplementasikan sistem ERP berbasis Odoo untuk menggantikan pengelolaan sales order manual pada PT Jaya Mandiri Indotech, perusahaan manufaktur komponen otomotif. Proses bisnis dimodelkan menggunakan BPMN dan dituangkan ke dalam konfigurasi modul Sales Odoo. Penelitian ini menunjukkan bahwa transformasi proses order dari manual ke ERP terbukti mengeliminasi redundansi data dan meningkatkan kecepatan pengambilan keputusan terkait sales order. Relevansi dengan penelitian ini: memberikan landasan kontekstual implementasi modul Sales pada Odoo di lingkungan perusahaan Indonesia, sekaligus menunjukkan bahwa proses penjualan manual-termasuk mekanisme persetujuan order-merupakan masalah nyata yang perlu diatasi dengan kustomisasi ERP.

### 2.1.2 Efendi dan Aditya (2022)

Judul: "Business Process Analysis and Implementation of Odoo Open Source ERP System in Inventory, Purchasing and Sales Activities"

Sumber: Procedia of Social Sciences and Humanities, Vol. 3, hal. 349-357, 2022. DOI: <https://doi.org/10.21070/pssh.v3i.180>.

Penelitian ini menganalisis dan mengimplementasikan Odoo open-source ERP mencakup tiga modul utama-Inventory, Purchasing, dan Sales-pada sebuah toko retail (Captain Gadget Store). Temuan utama adalah bahwa integrasi ketiga modul secara bersamaan menghasilkan visibilitas data yang lebih baik dan mereduksi error dalam proses pembelian dan penjualan. Relevansi dengan penelitian ini: memperkuat justifikasi urgensi integrasi modul penjualan dan pembelian dalam satu platform Odoo, yang menjadi konteks pengembangan modul approval sales dan purchase secara terintegrasi dalam penelitian ini.

### 2.1.3 Alam, Sarwar, Noreen, dan Ashraf (2022)

Judul: "Statistical Analysis of Software Development Models by Six-Pointed Star Framework"

Sumber: PLOS ONE, Vol. 17, No. 4, hal. e0264420, 2022. DOI: <https://doi.org/10.1371/journal.pone.0264420>.

Penelitian ini menganalisis berbagai model pengembangan perangkat lunak-termasuk Waterfall, Iterative, RAD, Spiral, Agile, dan model Z-menggunakan kerangka six-pointed star yang mengevaluasi enam dimensi: flexibility, scalability, cost, time, risk, dan quality. Waterfall memperoleh skor tertinggi pada dimensi quality dan cost untuk proyek dengan persyaratan yang stabil dan terdefinisi dengan baik. Relevansi dengan penelitian ini: memberikan justifikasi berbasis analisis statistik multi-dimensi atas pemilihan metode Waterfall sebagai metodologi pengembangan ketiga modul approval yang persyaratannya telah terdefinisi sejak awal melalui wawancara mendalam.

### 2.1.4 Diansyah, Rahman, Handayani, Nur Cahyo, dan Utami (2023)

Judul: "Comparative Analysis of Software Development Lifecycle Methods in Software Development: A Systematic Literature Review"

Sumber: International Journal of Advances in Data and Information Systems (IJADIS), Vol. 4, No. 2, hal. 97-106, 2023. DOI: <https://doi.org/10.25008/ijadis.v4i2.1295>.

Systematic literature review ini membandingkan tiga SDLC utama-Waterfall, Agile, dan Scrum-berdasarkan faktor fleksibilitas, kecepatan, kemampuan adaptasi terhadap perubahan kebutuhan, dan risiko proyek. Temuan utama menyatakan bahwa Waterfall menyediakan struktur dan kejelasan rencana yang lebih besar (greater structure and clarity to plans) untuk proyek dengan kebutuhan yang sudah jelas, sementara Agile/Scrum lebih unggul dalam hal fleksibilitas. Relevansi langsung: menjadi basis teoretis utama pemilihan Waterfall dalam penelitian ini, mengingat spesifikasi approval threshold, hierarki approver, dan business rule modul telah dapat didefinisikan sepenuhnya sejak fase analisis.

### 2.1.5 Fatoni dan Nugroho (2023)

Judul: "Implementasi Open Source Enterprise Resource Planning Menggunakan Odoo pada Layanan Internet Desa"

Sumber: Jurnal Teknik Informatika dan Sistem Informasi (JATISI), Vol. 10, No. 2, hal. 666-676, 2023. DOI: <https://doi.org/10.35957/jatisi.v10i2.2112>.

Penelitian ini mengimplementasikan Odoo open-source ERP menggunakan metodologi Accelerated SAP (ASAP) pada layanan internet desa, dengan modul utama Sales Management. Penelitian mendokumentasikan keunggulan Odoo sebagai ERP open-source yang tidak hanya cocok untuk perusahaan besar, tetapi juga untuk organisasi skala kecil hingga menengah, karena kemudahan integrasi dan kelengkapan modul yang tersedia. Relevansi: memberikan perspektif tambahan tentang fleksibilitas Odoo sebagai platform yang mendukung kustomisasi modul sesuai kebutuhan spesifik, memperkuat pilihan Odoo sebagai basis pengembangan modul approval dalam penelitian ini.

### 2.1.6 Maclachlan, Sabir, dan Cotnareanu (2023)

Judul: "Simulating the Software Development Lifecycle: The Waterfall Model"

Sumber: Applied System Innovation (MDPI), Vol. 6, No. 6, hal. 108, 2023. DOI: <https://doi.org/10.3390/asi6060108>.

Penelitian ini mengembangkan simulasi berbasis diskrit (discrete-event simulation menggunakan SimPy/Python) untuk memodelkan siklus hidup pengembangan perangkat lunak Waterfall. Simulasi dijalankan pada 100 proyek dengan ukuran bervariasi untuk mengidentifikasi bottleneck sumber daya-khususnya kekurangan programmer pada fase implementasi. Temuan menegaskan keunggulan Waterfall dalam memberikan estimasi waktu dan biaya yang akurat sebelum proyek dimulai. Relevansi: mendukung aspek perencanaan proyek dalam penelitian ini, khususnya estimasi durasi 8 minggu (Mei-Juni 2026) dan alokasi sumber daya per fase yang telah ditetapkan pada Tabel 3.1.

### 2.1.7 Trisanto, Faroqi, Indriani, Harahap, dan Saefudin (2024)

Judul: "Penerapan Enterprise Resource Planning (ERP) pada Sistem Supply Chain Management di PT Poliprima Cipta Unggul Menggunakan Odoo 16.0"

Sumber: Journal of Information System, Informatics and Computing (JISICOM), Vol. 8, No. 2, hal. 389-403, 2024. DOI: <https://doi.org/10.52362/jisicom.v8i2.1674>. (Terakreditasi SINTA 5)

Penelitian ini mengkonfigurasi Odoo 16.0 untuk mengelola Supply Chain Management di PT Poliprima-perusahaan manufaktur helm-mencakup modul Inventory, Purchase, Sales, dan Accounting. Proses pengadaan dan penjualan yang sebelumnya dikelola secara manual berhasil diintegrasikan ke dalam satu platform. Relevansi dengan penelitian ini: memberikan referensi kontemporer implementasi Odoo versi terbaru (16.0) pada perusahaan manufaktur di Indonesia, menunjukkan bahwa integrasi modul pembelian dan penjualan dalam Odoo merupakan kebutuhan nyata yang masih berkembang, dan modul approval terintegrasi seperti yang dikembangkan dalam penelitian ini merupakan lapisan kontrol yang dibutuhkan di atas konfigurasi standar tersebut.

**Tabel 2.1 Ringkasan Penelitian Terdahulu**

| **No** | **Penulis (Tahun)**      | **Fokus Penelitian**                            | **Metode**                   | **Relevansi**                                  |
| ------ | ------------------------ | ----------------------------------------------- | ---------------------------- | ---------------------------------------------- |
| 1      | Fatmawati et al. (2022)  | ERP Odoo modul Sales Order, PT manufaktur       | SDLC Incremental + BPMN      | Landasan proses manual SO yang perlu dikontrol |
| 2      | Efendi & Aditya (2022)   | Odoo Inventory, Purchasing, Sales terintegrasi  | Studi kasus                  | Justifikasi integrasi modul sales & purchase   |
| 3      | Alam et al. (2022)       | Analisis statistik model SDLC (6 dimensi)       | Six-Pointed Star             | Waterfall unggul quality & cost: req. stabil   |
| 4      | Diansyah et al. (2023)   | Perbandingan Waterfall, Agile, Scrum (SLR)      | Systematic Literature Review | Basis teoretis pemilihan Waterfall             |
| 5      | Fatoni & Nugroho (2023)  | Odoo open-source ERP, modul Sales Mgmt          | ASAP                         | Fleksibilitas Odoo untuk kustomisasi modul     |
| 6      | Maclachlan et al. (2023) | Simulasi SDLC Waterfall (bottleneck & estimasi) | Discrete-event simulation    | Validasi perencanaan waktu & sumber daya       |
| 7      | Trisanto et al. (2024)   | Odoo 16 Supply Chain Management (manufaktur)    | Konfigurasi Odoo             | Referensi Odoo terkini di perusahaan Indonesia |

## 2.2 Enterprise Resource Planning (ERP)

Enterprise Resource Planning (ERP) adalah sistem informasi terintegrasi yang mengkonsolidasikan dan mengotomasi seluruh proses bisnis inti suatu organisasi ke dalam satu platform terpadu. Sistem ERP mengintegrasikan berbagai fungsi bisnis, termasuk manajemen keuangan, sumber daya manusia, rantai pasok, produksi, penjualan, dan pengadaan. Integrasi menyeluruh ini memungkinkan data mengalir secara real-time antar departemen, mengeliminasi redundansi, dan menyediakan visibilitas penuh atas operasional perusahaan. Trisanto et al. (2024) menunjukkan bahwa perusahaan manufaktur yang sebelumnya mengelola pembelian dan penjualan secara manual dapat memperoleh manfaat signifikan dari integrasi modul Purchase, Sales, dan Inventory dalam satu platform Odoo ERP.

Dalam konteks sistem ERP, mekanisme approval diimplementasikan sebagai workflow yang mendefinisikan state transitions dari dokumen transaksi. Pressman dan Maxim (2020) mengidentifikasi pentingnya kontrol internal pada setiap titik keputusan dalam sistem informasi enterprise sebagai bagian dari software quality assurance. Secara khusus dalam lingkungan ERP, approval workflow memodelkan tiga pola utama: (1) Sequential Approval-setiap approver menyetujui secara berurutan; (2) Parallel Approval-beberapa approver dapat menyetujui secara simultan; dan (3) Threshold-based Approval-jenis persetujuan bergantung pada nilai atau parameter tertentu. Kedua modul yang dikembangkan dalam penelitian ini mengadopsi kombinasi Sequential dan Threshold-based Approval.

## 2.3 Odoo ERP

Odoo adalah platform ERP open-source yang dikembangkan oleh Odoo S.A. (Belgia), tersedia dalam dua edisi: Community Edition (LGPL-3) dan Enterprise Edition. Arsitektur Odoo mengadopsi pola MVC berbasis Python (backend), OWL/JavaScript (frontend), dan PostgreSQL (database). Fatoni dan Nugroho (2023) mencatat bahwa Odoo merupakan satu-satunya ERP yang tidak hanya digunakan oleh perusahaan besar tetapi juga oleh organisasi skala kecil karena kemudahan integrasi modul. Odoo versi 16 ke atas mengalami perubahan arsitektur signifikan dengan adopsi OWL 2.0 yang memerlukan pendekatan baru dalam pengembangan modul kustom berbasis widget (Odoo S.A., 2025).

### 2.3.1 Odoo ORM dan Model Inheritance

Odoo ORM (Object-Relational Mapping) memungkinkan pengembang mendefinisikan model data bisnis sebagai kelas Python yang dipetakan otomatis ke tabel PostgreSQL. Odoo mendukung tiga mekanisme inheritance: (1) Classical Inheritance (\_inherit)-memperluas model yang ada dengan berbagi tabel database yang sama, yang digunakan dalam penelitian ini untuk memperluas sale.order dan purchase.order; (2) Prototype Inheritance (\_inherits)-mendelegasikan field ke model lain melalui foreign key dengan tabel terpisah; dan (3) Delegation Inheritance-variasi prototype dengan akses transparan ke field model induk.

Dalam konteks penelitian ini, classical inheritance (\_inherit) diterapkan untuk menambahkan field approval_state, current_approval_level_id, submitted_by, approval_log_ids, dan field-field komputasi pada model sale.order dan purchase.order tanpa mengubah struktur tabel inti Odoo.

### 2.3.2 Odoo OWL (Odoo Web Library)

OWL adalah framework JavaScript reaktif yang dikembangkan Odoo sebagai pengganti widget berbasis RPC lama. OWL mengadopsi konsep component-based architecture serupa React, dengan dukungan state reaktif, lifecycle hooks, dan template QWeb deklaratif. Komponen OWL dikompilasi dan di-bundle sebagai bagian dari web.assets_backend Odoo. Dalam penelitian ini, OWL digunakan untuk membangun gifari_approval_dashboard dengan KPI cards reaktif yang memperbarui data melalui JSON RPC ke endpoint /gifari/approval/dashboard/data.

### 2.3.3 Odoo 19 Community Edition

Odoo 19 Community Edition (versi yang digunakan dalam penelitian ini) merupakan versi yang mendukung Python 3.12, OWL 2.0 yang lebih matang, serta peningkatan performa ORM dan keamanan. Versi ini mempertahankan kompatibilitas dengan pola pengembangan modul kustom yang digunakan pada Odoo 16-18, sehingga modul yang dikembangkan dalam penelitian ini (versi 19.0.1.0.0) dapat berjalan pada Odoo 19 Community.

## 2.4 Metode Waterfall

Metode Waterfall, yang pertama kali didokumentasikan secara formal oleh Winston W. Royce pada tahun 1970, menerapkan pendekatan pengembangan sekuensial yang membagi SDLC ke dalam fase-fase terurut. Diansyah et al. (2023) mendefinisikan Waterfall sebagai metodologi plan-driven yang mengharuskan setiap fase diselesaikan secara lengkap sebelum fase berikutnya dimulai, dengan output setiap fase menjadi input bagi fase selanjutnya. Pressman dan Maxim (2020) menekankan bahwa kualitas fase analisis kebutuhan sangat menentukan keberhasilan keseluruhan proyek Waterfall.

### 2.4.1 Fase-fase Metode Waterfall

**Fase 1: Requirements Analysis (Analisis Kebutuhan)**

Identifikasi, dokumentasi, dan validasi seluruh kebutuhan fungsional dan non-fungsional sistem bersama stakeholder. Output: dokumen Software Requirements Specification (SRS). Dalam penelitian ini, fase ini menghasilkan 28 kebutuhan fungsional dan 7 kebutuhan non-fungsional melalui wawancara mendalam dan observasi langsung selama Mei 2026.

**Fase 2: System Design (Desain Sistem)**

Pengembangan arsitektur sistem, termasuk desain model data (ERD), desain state machine approval, desain antarmuka (XML views), desain API endpoint dashboard, dan desain keamanan (groups, ir.rules). Output: dokumen System Design Specification (SDS) beserta diagram UML.

**Fase 3: Implementation (Implementasi)**

Transformasi desain menjadi kode Python, XML, dan JavaScript/OWL. Setiap model, wizard, view, dan controller dikodekan sesuai standar Odoo development guidelines. Unit testing dilakukan terhadap setiap komponen secara individual.

**Fase 4: Testing (Pengujian)**

Verifikasi menyeluruh terhadap sistem menggunakan data demo, mencakup integration testing, system testing, dan User Acceptance Testing (UAT). Bug dan defect dicatat, diperbaiki, dan diverifikasi ulang menggunakan skenario pengujian terstruktur.

**Fase 5: Deployment**

Instalasi modul pada lingkungan staging berbasis data demo, pelatihan pengguna, dan dokumentasi operasional. Evaluasi pasca-deployment dilakukan untuk mengukur KPI efektivitas menggunakan kuesioner Likert.

**Tabel 2.2 Kelebihan dan Kekurangan Metode Waterfall**

| **Kelebihan**                                | **Kekurangan**                                        |
| -------------------------------------------- | ----------------------------------------------------- |
| Dokumentasi komprehensif di setiap fase      | Tidak fleksibel terhadap perubahan kebutuhan          |
| Kemudahan manajemen dan perencanaan proyek   | Pengujian dilakukan di akhir, bug ditemukan terlambat |
| Fase jelas dan terukur untuk monitoring      | Produk belum dapat didemonstrasikan hingga fase akhir |
| Cocok untuk kebutuhan stabil dan terdefinisi | Risiko tinggi jika kebutuhan berubah                  |
| Estimasi biaya relatif akurat di awal        | Kurang sesuai untuk proyek kompleks jangka panjang    |

## 2.5 Perbandingan Metodologi Pengembangan Perangkat Lunak

Diansyah et al. (2023) mengklasifikasikan metodologi pengembangan ke dalam dua kelompok besar: plan-driven (Waterfall, V-Model, Spiral) dan agile (Scrum, XP, Kanban). Alam et al. (2022) menganalisis secara statistik bahwa Waterfall memberikan struktur yang lebih besar dan kejelasan rencana untuk proyek dengan kebutuhan stabil dan tim yang terstruktur-kondisi yang tepat menggambarkan penelitian ini.

**Tabel 2.3 Perbandingan Metodologi Pengembangan Perangkat Lunak**

| **Kriteria**         | **Waterfall**            | **Scrum (Agile)**    | **Prototyping**             | **Spiral**               |
| -------------------- | ------------------------ | -------------------- | --------------------------- | ------------------------ |
| Pendekatan           | Sekuensial linier        | Iteratif inkremental | Iteratif berbasis prototipe | Iteratif berbasis risiko |
| Fleksibilitas        | Rendah                   | Tinggi               | Sedang-Tinggi               | Sedang                   |
| Dokumentasi          | Sangat tinggi            | Minimal              | Rendah-Sedang               | Tinggi                   |
| Waktu ke produk awal | Panjang                  | Pendek (sprint 1)    | Sangat pendek               | Sedang                   |
| Cocok untuk          | Req. stabil, scope tetap | Req. dinamis         | Req. belum jelas            | Proyek berisiko          |

## 2.6 Sistem Approval dalam ERP: State Machine dan Audit Trail

Implementasi teknis sistem approval dalam Odoo mengadopsi konsep finite state machine (FSM). FSM mendefinisikan serangkaian state yang dapat dimiliki suatu dokumen beserta transisi yang diizinkan antar state. Pressman dan Maxim (2020) menjelaskan bahwa penggunaan FSM dalam approval digital memungkinkan pelacakan status secara real-time dan pembuatan audit trail yang tidak dapat dimanipulasi (immutable log).

Pada modul gifari_sale_discount_approval, FSM untuk approval_state didefinisikan sebagai berikut:

- State none: SO tidak memerlukan approval (effective_max_discount di bawah semua threshold level).
- State pending: SO mengandung diskon yang melampaui threshold minimum; menunggu persetujuan approver yang ditugaskan pada current_approval_level_id.
- State approved: Semua level yang dipersyaratkan telah menyetujui; sistem secara otomatis memanggil super().action_confirm() untuk mengkonfirmasi SO.
- State rejected: Approver menolak; SO dikembalikan kepada salesperson dengan notifikasi aktivitas untuk perbaikan dan resubmit.

Pada modul gifari_purchase_approval, FSM serupa diterapkan dengan trigger berdasarkan amount_untaxed terhadap min_amount yang dikonfigurasi pada purchase.approval.level. Terdapat state tambahan yang ditangani melalui action reset-dipicu saat PO yang sudah disetujui dibuka kembali dan nilai amount_untaxed berubah signifikan, yang memerlukan proses approval ulang dari awal.

Setiap transisi state dicatat dalam model log terpisah (sale.discount.approval.log dan purchase.approval.log) yang mencakup: referensi order, level approval, user yang melakukan aksi, jenis aksi (submit/approve/reject/resubmit/cancel/reset), catatan/alasan, nilai diskon/amount sebelum dan sesudah, serta alamat IP pengguna untuk keamanan audit. Sommerville (2016) menegaskan bahwa kelengkapan audit trail semacam ini merupakan persyaratan minimal sistem approval kelas enterprise untuk keperluan compliance dan investigasi internal.

## 2.7 OWL Dashboard sebagai Pusat Pemantauan Approval

Odoo S.A. (2025) menekankan bahwa OWL 2.0 pada Odoo 16 ke atas menawarkan paradigma baru dalam pembuatan widget backend: komponen reaktif yang memisahkan state management dari presentasi. Modul gifari_approval_dashboard memanfaatkan paradigma ini untuk menyajikan data dari dua sistem approval berbeda (sale dan purchase) dalam satu antarmuka terpusat.

Arsitektur dashboard ini mengadopsi pola single RPC call-seluruh data KPI, daftar pending SO/PO, dan log aktivitas terkini diambil dalam satu permintaan JSON ke endpoint /gifari/approval/dashboard/data. Pendekatan ini mengurangi latensi antarmuka dan mempermudah maintenance dibandingkan pendekatan multi-request. KPI yang ditampilkan mencakup total_pending (sales + purchase), total_approved_today, total_rejected_today, beserta breakdown per modul.

## 2.8 Kesenjangan Penelitian (Research Gap)

Berdasarkan kajian komprehensif terhadap penelitian-penelitian terdahulu, dapat diidentifikasi beberapa kesenjangan penelitian yang menjadi justifikasi ilmiah penelitian ini:

- Belum ada penelitian yang secara spesifik mengevaluasi efektivitas Waterfall dalam pengembangan custom module Odoo berbasis FSM approval dengan threshold bertingkat dan audit trail terintegrasi menggunakan set KPI multi-dimensi yang komprehensif.
- Penelitian-penelitian terdahulu umumnya mengevaluasi modul approval penjualan atau pembelian secara terpisah; penelitian ini mengisi gap dengan mengembangkan keduanya dalam satu proyek terintegrasi yang dilengkapi dashboard terpusat.
- Implementasi fitur counter-offer (untuk sales) dan re-approval setelah modifikasi PO (untuk purchase) belum pernah didokumentasikan dalam konteks akademik pengembangan custom module Odoo Indonesia.
- Penggunaan demo data sebagai substitute untuk data confidential perusahaan dalam evaluasi modul ERP belum pernah dikaji secara metodologis dalam literatur Indonesia-penelitian ini menawarkan pendekatan tersebut sebagai model yang dapat diadopsi penelitian serupa.

# BAB III METODOLOGI PENELITIAN

Bab ini menguraikan secara sistematis seluruh metodologi yang digunakan dalam penelitian ini, mulai dari jenis dan pendekatan penelitian, lokasi dan waktu penelitian, teknik pengumpulan data, proses pengembangan sistem menggunakan metode Waterfall, skenario pengujian, indikator evaluasi efektivitas, hingga metode analisis data.

## 3.1 Jenis dan Pendekatan Penelitian

Penelitian ini menggunakan pendekatan campuran (mixed method research) yang mengintegrasikan antara penelitian kuantitatif dan kualitatif secara bersamaan. Pendekatan kuantitatif diimplementasikan melalui penggunaan kuesioner skala Likert 5 poin untuk mengukur kepuasan pengguna dan pengukuran numerik indikator KPI. Pendekatan kualitatif diimplementasikan melalui wawancara mendalam dan observasi langsung terhadap proses bisnis.

Jenis penelitian diklasifikasikan sebagai penelitian terapan (applied research) dengan desain studi kasus tunggal (single case study design) pada PT Indopora. Pengembangan sistem dilakukan menggunakan data demonstrasi yang merepresentasikan skenario bisnis nyata-termasuk konfigurasi approval level, produk, pelanggan, vendor, dan pengguna-karena data operasional perusahaan bersifat rahasia.

## 3.2 Lokasi dan Waktu Penelitian

**Tabel 3.1 Lokasi dan Waktu Penelitian**

| **Aspek**                     | **Keterangan**                                   |
| ----------------------------- | ------------------------------------------------ |
| Lokasi Penelitian             | PT Indopora, Bandung, Jawa Barat                 |
| Periode Penelitian            | Mei - Juni 2026 (2 bulan)                        |
| Fase 1: Analisis Kebutuhan    | Minggu 1-2 Mei 2026 (2 minggu)                   |
| Fase 2: Desain Sistem         | Minggu 3-4 Mei 2026 (2 minggu)                   |
| Fase 3: Implementasi          | Minggu 5-6 Mei & Minggu 1-2 Juni 2026 (4 minggu) |
| Fase 4: Pengujian (UAT Demo)  | Minggu 3 Juni 2026 (1 minggu)                    |
| Fase 5: Deployment & Evaluasi | Minggu 4 Juni 2026 (1 minggu)                    |

Penelitian berlangsung selama dua bulan (Mei-Juni 2026) dengan total delapan minggu aktif. Pemadatan waktu dimungkinkan karena scope modul terdefinisi dengan jelas dan pengembangan menggunakan data demonstrasi sehingga tidak memerlukan waktu untuk ekstraksi atau migrasi data produksi.

## 3.3 Pengumpulan Data

Pengumpulan data dalam penelitian ini dilakukan melalui tiga teknik yang saling melengkapi: wawancara mendalam, kuesioner, dan observasi langsung. Kombinasi ketiga teknik ini memungkinkan triangulasi data yang meningkatkan validitas dan reliabilitas temuan penelitian (Pressman & Maxim, 2020).

### 3.3.1 Wawancara Mendalam

Wawancara mendalam dilakukan terhadap lima informan kunci yang dipilih secara purposif berdasarkan keterlibatan mereka dalam proses bisnis yang relevan.

**Tabel 3.2 Daftar Informan Wawancara**

| **No** | **Jabatan**          | **Kode** | **Topik Wawancara**                                          |
| ------ | -------------------- | -------- | ------------------------------------------------------------ |
| 1      | Sales Manager        | INF-01   | Batas diskon per level, escalation rules, approval hierarchy |
| 2      | Purchase Manager     | INF-02   | Batas nilai PO, level approver, bypass rules, re-approval    |
| 3      | IT Manager           | INF-03   | Infrastruktur Odoo, standar keamanan, integrasi modul        |
| 4      | Sales Staff (Senior) | INF-04   | Pain points proses manual, harapan notifikasi, UX approval   |
| 5      | Finance Controller   | INF-05   | Kebutuhan audit trail, laporan approval log, compliance      |

### 3.3.2 Observasi Langsung

Observasi dilakukan terhadap proses penjualan dan pembelian manual yang sedang berjalan untuk mengidentifikasi bottleneck, waktu rata-rata proses approval, dan risiko kontrol. Observasi dilakukan selama dua hari pada minggu pertama Mei 2026 dan didokumentasikan melalui catatan lapangan terstruktur.

### 3.3.3 Kuesioner Kepuasan Pengguna

Kuesioner menggunakan skala Likert 5 poin (1 = Sangat Tidak Setuju hingga 5 = Sangat Setuju) didistribusikan kepada 25 responden setelah sesi UAT berbasis data demo. Kuesioner mencakup 20 pernyataan yang mengukur aspek kemudahan penggunaan, kesesuaian alur approval, kejelasan notifikasi, kepercayaan terhadap audit trail, dan kepuasan keseluruhan terhadap ketiga modul.

## 3.4 Proses Pengembangan Sistem (Metode Waterfall)

### 3.4.1 Fase 1: Analisis Kebutuhan (Minggu 1-2 Mei 2026)

Analisis kebutuhan dilakukan melalui kombinasi wawancara mendalam dengan lima informan kunci dan observasi langsung proses bisnis. Berdasarkan hasil analisis, ditetapkan kebutuhan fungsional dan non-fungsional sebagai berikut:

**Tabel 3.3 Kebutuhan Fungsional Utama**

| **Kode** | **Modul**         | **Kebutuhan Fungsional**                                                                          |
| -------- | ----------------- | ------------------------------------------------------------------------------------------------- |
| KF-01    | Sale Approval     | Sistem mendeteksi effective_max_discount (max dari max_line_discount dan global_discount_percent) |
| KF-02    | Sale Approval     | Approval dipicu ketika effective_max_discount >= min_discount level yang dikonfigurasi            |
| KF-03    | Sale Approval     | Alur persetujuan sekuensial multi-level (L1 → L2 → Ln) berdasarkan urutan sequence                |
| KF-04    | Sale Approval     | Mode approval: any_one (salah satu approver cukup) atau all_must (semua harus setuju)             |
| KF-05    | Sale Approval     | Fitur counter-offer: approver dapat mengajukan nilai diskon alternatif yang lebih rendah          |
| KF-06    | Sale Approval     | Final approval otomatis memanggil action_confirm() untuk mengkonfirmasi SO                        |
| KF-07    | Sale Approval     | Resubmit setelah penolakan: SO kembali ke level pertama                                           |
| KF-08    | Purchase Approval | Approval dipicu ketika amount_untaxed PO >= min_amount level yang dikonfigurasi                   |
| KF-09    | Purchase Approval | Alur persetujuan sekuensial multi-level berdasarkan urutan sequence                               |
| KF-10    | Purchase Approval | Bypass approval untuk PO yang berasal dari Purchase Agreement                                     |
| KF-11    | Purchase Approval | Re-approval otomatis dipicu saat PO yang telah disetujui dimodifikasi (nilai berubah)             |
| KF-12    | Dashboard         | KPI cards: total pending, approved today, rejected today (breakdown per modul)                    |
| KF-13    | Dashboard         | Daftar pending SO dan PO dengan aging indicator (days_pending)                                    |
| KF-14    | Dashboard         | Log aktivitas terkini dari kedua modul approval                                                   |
| KF-15    | Semua             | Audit trail lengkap per transaksi dengan user, waktu, aksi, nilai, dan IP address                 |
| KF-16    | Semua             | Notifikasi aktivitas in-app (mail.activity) kepada approver yang ditugaskan                       |

Diagram alur proses bisnis yang dikembangkan dapat dideskripsikan dalam format Mermaid sebagai berikut. Diagram ini merepresentasikan alur lengkap gifari_sale_discount_approval:

**Diagram 3.1 Alur Approval Sales Order (gifari_sale_discount_approval)**

\`\`\`mermaid

stateDiagram-v2

\[\*\] --> draft : Salesperson membuat SO

draft --> check : action_confirm() dipanggil

check --> none : effective_max_discount < threshold

check --> pending : effective_max_discount >= threshold

none --> sale : super().action_confirm() langsung

pending --> pending_lanjut : Level approved (next level exists)

pending --> approved : Final level approved

pending --> rejected : Approver menolak

pending_lanjut --> pending : Proses di level berikutnya

approved --> sale : auto action_confirm()

rejected --> pending : action_resubmit_approval()

rejected --> draft : action_cancel_approval()

pending --> draft : action_cancel_approval()

\`\`\`

**Diagram 3.2 Alur Approval Purchase Order (gifari_purchase_approval)**

\`\`\`mermaid

stateDiagram-v2

\[\*\] --> draft : Pembuat PO membuat Purchase Order

draft --> check : button_confirm() dipanggil

check --> none : amount_untaxed < min_amount semua level

check --> bypass : PO dari Purchase Agreement

check --> pending : amount_untaxed >= min_amount

none --> purchase : standard \_approval_allowed()

bypass --> purchase : langsung dikonfirmasi

pending --> pending_lanjut : Level disetujui (level berikutnya ada)

pending --> approved : Final level disetujui

pending --> rejected : Approver menolak

pending_lanjut --> pending : Proses di level berikutnya

approved --> purchase : auto button_confirm()

rejected --> pending : action_resubmit()

approved --> reset : PO dibuka ulang & nilai diubah

reset --> pending : Re-approval dari level pertama

\`\`\`

**Diagram 3.3 Arsitektur Ketiga Modul Custom dan Dependensinya**

\`\`\`mermaid

graph TD

A\[gifari_sale_discount_approval\] -->|depends| B\[sale\]

A -->|depends| C\[sale_stock\]

A -->|depends| D\[sale_management\]

E\[gifari_purchase_approval\] -->|depends| F\[purchase\]

E -->|depends| G\[purchase_stock\]

H\[gifari_approval_dashboard\] -->|depends| A

H -->|depends| E

A -->|inherits| I\[sale.order\]

A -->|creates| J\[sale.discount.approval.level\]

A -->|creates| K\[sale.discount.approval.log\]

E -->|inherits| L\[purchase.order\]

E -->|creates| M\[purchase.approval.level\]

E -->|creates| N\[purchase.approval.log\]

H -->|reads| I

H -->|reads| K

H -->|reads| L

H -->|reads| N

\`\`\`

### 3.4.2 Fase 2: Desain Sistem (Minggu 3-4 Mei 2026)

Pada fase desain, arsitektur teknis ketiga modul dirancang secara detail. Desain mencakup: (1) Entity Relationship Diagram (ERD) untuk model-model baru; (2) desain state machine untuk approval_state; (3) desain XML views (form, tree, kanban) untuk setiap modul; (4) desain keamanan berbasis grup (groups.xml dan ir_rules.xml); (5) desain endpoint JSON untuk dashboard; dan (6) desain komponen OWL untuk antarmuka dashboard.

Desain data model approval level untuk kedua modul memiliki struktur yang paralel namun dengan field threshold yang berbeda: sale.discount.approval.level menggunakan min_discount (%) dan max_discount (%), sementara purchase.approval.level menggunakan min_amount (Rp) dan max_amount (Rp). Keduanya memiliki field approver_ids (Many2many ke res.users) dan approval_mode (any_one / all_must).

**Diagram 3.4 Entity Relationship Diagram Model Approval**

\`\`\`mermaid

erDiagram

SALE_ORDER ||--o{ SALE_DISCOUNT_APPROVAL_LOG : "approval_log_ids"

SALE_ORDER }o--|| SALE_DISCOUNT_APPROVAL_LEVEL : "current_approval_level_id"

SALE_DISCOUNT_APPROVAL_LEVEL }|--|{ RES_USERS : "approver_ids"

SALE_DISCOUNT_APPROVAL_LOG }o--|| SALE_DISCOUNT_APPROVAL_LEVEL : "level_id"

SALE_DISCOUNT_APPROVAL_LOG }o--|| RES_USERS : "user_id"

PURCHASE_ORDER ||--o{ PURCHASE_APPROVAL_LOG : "approval_log_ids"

PURCHASE_ORDER }o--|| PURCHASE_APPROVAL_LEVEL : "current_approval_level_id"

PURCHASE_APPROVAL_LEVEL }|--|{ RES_USERS : "approver_ids"

PURCHASE_APPROVAL_LOG }o--|| PURCHASE_APPROVAL_LEVEL : "level_id"

PURCHASE_APPROVAL_LOG }o--|| RES_USERS : "user_id"

\`\`\`

### 3.4.3 Fase 3: Implementasi (Minggu 5-6 Mei & Minggu 1-2 Juni 2026)

Implementasi dilakukan mengikuti standar pengembangan modul Odoo dengan struktur direktori sebagai berikut untuk setiap modul:

gifari_sale_discount_approval/

├── \__manifest_\_.py # Metadata modul (versi 19.0.1.0.0)

├── \__init_\_.py

├── models/

│ ├── sale_order.py # Override sale.order + approval workflow

│ ├── sale_order_line.py # Extended line untuk discount tracking

│ ├── sale_discount_approval_level.py # Model level approval

│ ├── sale_discount_approval_log.py # Model audit trail

│ ├── res_company.py # Config field sale_disc_approval_enabled

│ └── res_config_settings.py

├── wizards/

│ └── sale_discount_approval_wizard.py # Wizard approve/reject/counter-offer

├── views/

│ ├── sale_order_views.xml

│ ├── sale_discount_approval_level_views.xml

│ ├── sale_discount_approval_wizard_views.xml

│ ├── res_config_settings_views.xml

│ └── sale_approval_menu.xml

├── security/

│ ├── groups.xml # group_sale_approval_user, group_sale_approval_manager

│ ├── ir_rules.xml

│ └── ir.model.access.csv

└── data/

└── mail_activity_type.xml # Activity type untuk notifikasi

Komponen kunci implementasi meliputi field approval_state (Selection dengan empat nilai: none/pending/approved/rejected), field computed effective_max_discount yang menghitung max dari max_line_discount dan global_discount_percent, method \_needs_approval() yang memeriksa apakah diskon efektif melampaui threshold level terendah, method \_submit_for_approval() yang mengubah state ke pending dan membuat aktivitas untuk approver, serta method action_approve_discount() dan action_reject_discount() yang dipanggil dari wizard persetujuan.

### 3.4.4 Fase 4: Pengujian dengan Data Demo (Minggu 3 Juni 2026)

Pengujian dilakukan menggunakan data demonstrasi yang mencakup konfigurasi approval level representatif, pengguna demo dengan peran berbeda (salesperson, sales manager, purchase officer, purchase manager), produk dan partner demo, serta skenario transaksi yang merepresentasikan berbagai kondisi pengujian. Penggunaan data demo memastikan privasi data perusahaan terjaga tanpa mengorbankan validitas pengujian fungsional.

**Tabel 3.4 Skenario Pengujian Utama**

| **Kode** | **Modul** | **Skenario**                   | **Kondisi**                                   | **Hasil yang Diharapkan**                            |
| -------- | --------- | ------------------------------ | --------------------------------------------- | ---------------------------------------------------- |
| TC-01    | Sale      | SO tanpa diskon                | effective_max_discount = 0%                   | Langsung terkonfirmasi, approval_state = none        |
| TC-02    | Sale      | SO diskon L1 threshold         | effective_max_discount >= L1.min_discount     | approval_state = pending, aktivitas ke approver L1   |
| TC-03    | Sale      | Approval L1 → advance L2       | L1 approve, L2 masih diperlukan               | current_approval_level_id berpindah ke L2            |
| TC-04    | Sale      | Final approval                 | L2 approve (level terakhir)                   | approval_state = approved, SO terkonfirmasi otomatis |
| TC-05    | Sale      | Penolakan oleh approver        | Approver menolak dengan alasan                | approval_state = rejected, notifikasi ke submitter   |
| TC-06    | Sale      | Counter-offer                  | Approver mengajukan diskon 15% vs 20% diminta | Diskon baris dikurangi proporsional                  |
| TC-07    | Sale      | Resubmit setelah rejection     | Salesperson resubmit                          | Kembali ke pending level pertama                     |
| TC-08    | Purchase  | PO nilai di bawah threshold    | amount_untaxed < L1.min_amount                | Langsung terkonfirmasi                               |
| TC-09    | Purchase  | PO nilai di atas threshold L1  | amount_untaxed >= L1.min_amount               | approval_state = pending, aktivitas ke approver L1   |
| TC-10    | Purchase  | Re-approval setelah modifikasi | PO disetujui lalu diubah nilainya             | approval_state = reset → pending ulang               |
| TC-11    | Purchase  | Bypass Purchase Agreement      | PO berasal dari Purchase Requisition          | Bypass approval, langsung terkonfirmasi              |
| TC-12    | Dashboard | Tampilan KPI cards             | Ada SO dan PO pending                         | KPI mencerminkan data terkini                        |
| TC-13    | Dashboard | Daftar pending dengan aging    | PO pending 3 hari                             | days_pending = 3 pada daftar                         |

### 3.4.5 Fase 5: Deployment dan Evaluasi (Minggu 4 Juni 2026)

Deployment dilakukan pada instance Odoo 19 Community Edition staging berbasis data demo. Proses mencakup: (1) instalasi ketiga modul melalui antarmuka Odoo Apps; (2) konfigurasi approval level sesuai skenario demo; (3) sesi pelatihan pengguna selama setengah hari; dan (4) distribusi kuesioner kepuasan pasca-sesi UAT. Evaluasi efektivitas dilakukan pada akhir minggu keempat Juni 2026.

## 3.5 Skenario Pengujian

Pengujian dilakukan dalam tiga level: (1) Unit Testing-setiap method Python diuji secara terisolasi menggunakan Odoo test framework berbasis data demo; (2) Integration Testing-alur lengkap dari pembuatan SO/PO hingga konfirmasi final diuji untuk memverifikasi integrasi antar modul; dan (3) User Acceptance Testing (UAT)-pengguna demo menjalankan skenario bisnis representatif menggunakan antarmuka Odoo dan memberikan feedback terstruktur.

Khusus untuk gifari_approval_dashboard, pengujian fungsional mencakup verifikasi akurasi KPI (dibandingkan dengan query manual ke database), verifikasi daftar pending (ketepatan filter dan sorting), dan verifikasi log aktivitas (kelengkapan dan urutan kronologis).

## 3.6 Metrik Evaluasi Efektivitas

**Tabel 3.5 Definisi dan Target KPI Efektivitas**

| **KPI**              | **Definisi**                                                    | **Target**           | **Metode Pengukuran**               |
| -------------------- | --------------------------------------------------------------- | -------------------- | ----------------------------------- |
| Efisiensi Waktu      | Perbandingan waktu approval sebelum vs sesudah sistem           | \>50% reduksi        | Observasi timed (manual vs. sistem) |
| Kesesuaian Kebutuhan | % kebutuhan fungsional terpenuhi dari total SRS                 | \>90%                | Checklist verifikasi per kebutuhan  |
| Tingkat Bug          | % defect ditemukan saat testing vs. total test case             | <5% awal, 0% akhir   | Bug tracking per skenario uji       |
| Kepuasan Pengguna    | Rata-rata skor kuesioner Likert 5 poin                          | \>4.0/5.0            | Kuesioner 20 item pasca-UAT         |
| Frekuensi Rework     | Jumlah modul/fitur yang memerlukan perancangan ulang signifikan | 0 rework fase desain | Dokumentasi change log per fase     |

## 3.7 Metode Analisis Data

Data kuantitatif dari kuesioner dianalisis menggunakan statistik deskriptif (mean, median, modus, standar deviasi) dengan interpretasi berdasarkan rentang skor Likert: 1,0-1,8 (Sangat Tidak Setuju), 1,8-2,6 (Tidak Setuju), 2,6-3,4 (Cukup/Netral), 3,4-4,2 (Setuju/Baik), 4,2-5,0 (Sangat Setuju/Sangat Baik). Data KPI dikompilasi dari pengukuran langsung dan dibandingkan dengan target yang telah ditetapkan.

Data kualitatif dari wawancara dan observasi dianalisis menggunakan teknik analisis tematik (thematic analysis) dengan tiga tahap: (1) open coding-identifikasi tema-tema awal dari transkrip wawancara; (2) axial coding-pengelompokan tema ke dalam kategori; dan (3) selective coding-identifikasi tema inti yang menjawab rumusan masalah. Triangulasi data dilakukan dengan membandingkan temuan dari wawancara, kuesioner, dan observasi untuk memastikan konsistensi dan keabsahan temuan.

Evaluasi efektivitas metode Waterfall per fase dilakukan dengan membandingkan estimasi waktu dan output yang direncanakan dalam SRS dengan realisasi aktual, menggunakan matriks evaluasi yang mencakup tiga aspek: adherence (ketaatan pada timeline), completeness (kelengkapan deliverable), dan quality (kualitas output berdasarkan metrik bug rate dan UAT).

**Diagram 3.5 Alur Penelitian Keseluruhan (Metode Waterfall)**

\`\`\`mermaid

flowchart TD

A\[Identifikasi Masalah\] --> B\[Studi Literatur\]

B --> C\[FASE 1: Analisis Kebutuhan Mei Minggu 1-2\]

C --> D\[Wawancara & Observasi\]

D --> E\[Dokumen SRS 28 KF + 7 KNF\]

E --> F\[FASE 2: Desain Sistem Mei Minggu 3-4\]

F --> G\[ERD, State Machine, XML Views, OWL Design\]

G --> H\[FASE 3: Implementasi Mei Mgg 5-6, Juni Mgg 1-2\]

H --> I\[gifari_sale_discount_approval\]

H --> J\[gifari_purchase_approval\]

H --> K\[gifari_approval_dashboard\]

I --> L\[FASE 4: Pengujian Juni Minggu 3\]

J --> L

K --> L

L --> M{Bug > 0?}

M -->|Ya| N\[Perbaikan & Retest\]

N --> L

M -->|Tidak| O\[FASE 5: Deployment Juni Minggu 4\]

O --> P\[UAT dengan Data Demo\]

P --> Q\[Kuesioner & Evaluasi KPI\]

Q --> R\[Analisis & Pembahasan\]

R --> S\[Kesimpulan & Rekomendasi\]

\`\`\`

# DAFTAR PUSTAKA

\[1\] Fatmawati, T., Kramanandita, R., dan Miza, R. (2022). "Rancangan Implementasi Enterprise Resource Planning (ERP) pada Sistem Pengelolaan Sales Order PT Jaya Mandiri Indotech." Jurnal Teknologi dan Manajemen, Vol. 20, No. 1, hal. 33-44. DOI: <https://doi.org/10.52330/jtm.v20i1.49>.

\[2\] Efendi, H. F. dan Aditya, A. (2022). "Business Process Analysis and Implementation of Odoo Open Source ERP System in Inventory, Purchasing and Sales Activities (Case Study: Captain Gadget Store)." Procedia of Social Sciences and Humanities, Vol. 3, hal. 349-357. DOI: <https://doi.org/10.21070/pssh.v3i.180>.

\[3\] Alam, I., Sarwar, N., Noreen, I., dan Ashraf, M. U. (2022). "Statistical Analysis of Software Development Models by Six-Pointed Star Framework." PLOS ONE, Vol. 17, No. 4, hal. e0264420. DOI: <https://doi.org/10.1371/journal.pone.0264420>.

\[4\] Diansyah, A. F., Rahman, M. R., Handayani, R., Nur Cahyo, D. D., dan Utami, E. (2023). "Comparative Analysis of Software Development Lifecycle Methods in Software Development: A Systematic Literature Review." International Journal of Advances in Data and Information Systems (IJADIS), Vol. 4, No. 2, hal. 97-106. DOI: <https://doi.org/10.25008/ijadis.v4i2.1295>.

\[5\] Fatoni, J. M. dan Nugroho, A. (2023). "Implementasi Open Source Enterprise Resource Planning Menggunakan Odoo pada Layanan Internet Desa." Jurnal Teknik Informatika dan Sistem Informasi (JATISI), Vol. 10, No. 2, hal. 666-676. DOI: <https://doi.org/10.35957/jatisi.v10i2.2112>.

\[6\] Maclachlan, C., Sabir, A., dan Cotnareanu, T. (2023). "Simulating the Software Development Lifecycle: The Waterfall Model." Applied System Innovation, Vol. 6, No. 6, hal. 108. DOI: <https://doi.org/10.3390/asi6060108>.

\[7\] Amalia, R. dan Syaifullah, H. (2024). "Implementasi Enterprise Resource Planning (ERP) Odoo 16 Modul Sales pada Proses Bisnis Penyewaan Gudang di PT. X." Konstruksi: Publikasi Ilmu Teknik, Perencanaan Tata Ruang dan Teknik Sipil, Vol. 2, No. 1, hal. 54-64. DOI: <https://doi.org/10.61132/konstruksi.v2i1.45>.

\[8\] Dharma, A. D. S. dan Suryadi, A. (2024). "Implementasi Sistem Enterprise Resource Planning (ERP) pada PT XYZ dengan Menggunakan Modul Inventory Odoo." Venus: Jurnal Publikasi Rumpun Ilmu Teknik, Vol. 2, No. 1, hal. 122-133. DOI: <https://doi.org/10.61132/venus.v2i1.105>.

\[9\] Trisanto, D., Faroqi, A., Indriani, M., Harahap, M., dan Saefudin. (2024). "Penerapan Enterprise Resource Planning (ERP) pada Sistem Supply Chain Management di PT Poliprima Cipta Unggul Menggunakan Odoo 16.0." Journal of Information System, Informatics and Computing (JISICOM), Vol. 8, No. 2, hal. 389-403. DOI: <https://doi.org/10.52362/jisicom.v8i2.1674>.

\[10\] Firmansyah, D., Kusumasari, T. F., Firdaus, T., dan Prihandoko. (2024). "Inventory Management Process Efficiency With Enterprise Resource Planning Customization and Configuration (Case Study: Catering Industry)." Proceedings of the 2024 IEEE International Conference on Information Management and Technology (ICIMTech), hal. 1-6. DOI: <https://doi.org/10.1109/ICIMTech63123.2024.10780784>.

\[11\] Fathoni, M., Asih, A., dan Wibisono, M. (2024). "Adoption of Open-Source Enterprise Resource Planning in Small and Medium Industries: A Literature Review." Proceedings of the 2024 IEEE International Conference on Industrial Engineering and Engineering Management (IEEM), hal. 272-276. DOI: <https://doi.org/10.1109/IEEM62345.2024.10857088>.

\[12\] Pressman, R. S. dan Maxim, B. R. (2020). Software Engineering: A Practitioner's Approach, 9th ed. New York: McGraw-Hill Education. ISBN: 978-1-259-87278-1.

\[13\] Sommerville, I. (2016). Software Engineering, 10th ed. London: Pearson Education. ISBN: 978-0-13-394303-0.

\[14\] ISO/IEC 25010:2023. Systems and Software Quality Requirements and Evaluation (SQuaRE) - Product Quality Model. Geneva: International Organization for Standardization, 2023. Tersedia: <https://www.iso.org/standard/35733.html>.

\[15\] Odoo S.A. (2025). Odoo Developer Documentation: ORM API, Model Inheritance, Views, and OWL Framework. Tersedia: <https://www.odoo.com/documentation/> (Diakses: 1 Mei 2026).