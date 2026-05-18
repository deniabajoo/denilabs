import hashlib
import random
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember',
}

COMPANY_INFO = {
    'name': 'PT Indonesia Pondasi Raya Tbk',
    'street': 'Jl. Raya Cilegon KM. 3',
    'street2': 'Kelurahan Ramanuju, Kecamatan Purwakarta',
    'city': 'Cilegon',
    'zip': '42435',
    'phone': '(0254) 391811',
    'email': 'info@indopora.com',
    'website': 'https://www.indopora.com',
    'vat': '01.061.634.0-402.000',
    'company_registry': '8120209832068',
}

# Master data 75 pemasok anonim (sesuai NDA Lampiran A skripsi)
# Index 0-4: vendor "core" A1-A5 yang skornya hardcoded di Q1 2025 (Tabel 3.7 skripsi)
# Index 5-74: vendor anonim V006-V075 dengan distribusi 5 kategori konstruksi
VENDOR_MASTER = [
    # === 5 VENDOR CORE (A1-A5) — match Tabel 3.5 skripsi ===
    {
        'name': 'PT Baja Pondasi Sentosa',
        'street': 'Jl. Industri Krakatau No. 12',
        'city': 'Cilegon', 'zip': '42435',
        'phone': '(0254) 391001', 'email': 'sales@bajapondasi.co.id',
        'vat': '01.234.567.8-402.000',
        'category': 'baja',
    },
    {
        'name': 'CV Beton Karya Mandiri',
        'street': 'Jl. Industri Jababeka VII Blok C-5',
        'city': 'Bekasi', 'zip': '17530',
        'phone': '(021) 89831100', 'email': 'order@betonkaryamandiri.co.id',
        'vat': '02.345.678.9-413.000',
        'category': 'beton',
    },
    {
        'name': 'PT Hidrolik Teknik Prima',
        'street': 'Jl. Rungkut Industri III No. 25',
        'city': 'Surabaya', 'zip': '60293',
        'phone': '(031) 8431234', 'email': 'parts@hidrolikteknik.co.id',
        'vat': '03.456.789.0-606.000',
        'category': 'alat_berat',
    },
    {
        'name': 'UD Pracetak Sejahtera',
        'street': 'Jl. Raya Kaligawe KM 5',
        'city': 'Semarang', 'zip': '50118',
        'phone': '(024) 6580900', 'email': 'sales@pracetaksejahtera.co.id',
        'vat': '04.567.890.1-503.000',
        'category': 'beton',
    },
    {
        'name': 'PT Mitra Logistik Konstruksi',
        'street': 'Jl. Cakung Cilincing Raya No. 88',
        'city': 'Jakarta Utara', 'zip': '14140',
        'phone': '(021) 4490023', 'email': 'dispatch@mitralogistikkonstruksi.co.id',
        'vat': '05.678.901.2-007.000',
        'category': 'logistik',
    },
    # === V006-V025: BAJA & STRUKTUR LOGAM (20 vendor) ===
    {'name': 'PT Baja Cakrawala Nusantara', 'street': 'Jl. Industri Cilegon Blok A-3', 'city': 'Cilegon', 'zip': '42434', 'phone': '(0254) 391120', 'email': 'sales@bcnusantara.co.id', 'vat': '01.100.001.1-402.000', 'category': 'baja'},
    {'name': 'PT Wajatama Bangun Sentosa', 'street': 'Jl. Raya Bekasi KM 27', 'city': 'Bekasi', 'zip': '17132', 'phone': '(021) 88345670', 'email': 'order@wajatama.co.id', 'vat': '01.100.002.2-413.000', 'category': 'baja'},
    {'name': 'CV Logam Jaya Perkasa', 'street': 'Jl. Margomulyo Industri No. 22', 'city': 'Surabaya', 'zip': '60183', 'phone': '(031) 7491200', 'email': 'cs@logamjaya.co.id', 'vat': '01.100.003.3-606.000', 'category': 'baja'},
    {'name': 'PT Steel Indo Pratama', 'street': 'Kawasan MM2100 Blok JJ-8', 'city': 'Bekasi', 'zip': '17520', 'phone': '(021) 89982130', 'email': 'sales@steelindopratama.co.id', 'vat': '01.100.004.4-413.000', 'category': 'baja'},
    {'name': 'PT Tirta Baja Mandiri', 'street': 'Jl. Raya Serang KM 8', 'city': 'Tangerang', 'zip': '15710', 'phone': '(021) 59302245', 'email': 'order@tirtabaja.co.id', 'vat': '01.100.005.5-411.000', 'category': 'baja'},
    {'name': 'CV Karya Logam Mulia', 'street': 'Jl. Trans Sulawesi KM 12', 'city': 'Makassar', 'zip': '90245', 'phone': '(0411) 425100', 'email': 'admin@karyalogam.co.id', 'vat': '01.100.006.6-808.000', 'category': 'baja'},
    {'name': 'PT Sentral Baja Konstruksi', 'street': 'Jl. KIIC Lot K-15', 'city': 'Karawang', 'zip': '41361', 'phone': '(0267) 8639100', 'email': 'sales@sentralbaja.co.id', 'vat': '01.100.007.7-433.000', 'category': 'baja'},
    {'name': 'PT Anugrah Logam Sentosa', 'street': 'Jl. Industri Cikarang Blok B-7', 'city': 'Bekasi', 'zip': '17550', 'phone': '(021) 89901234', 'email': 'order@anugrahlogam.co.id', 'vat': '01.100.008.8-413.000', 'category': 'baja'},
    {'name': 'CV Bintang Baja Persada', 'street': 'Jl. Belmera KM 9', 'city': 'Medan', 'zip': '20371', 'phone': '(061) 6831200', 'email': 'sales@bintangbaja.co.id', 'vat': '01.100.009.9-122.000', 'category': 'baja'},
    {'name': 'PT Mega Steel Pratama', 'street': 'Jl. Industri III Blok DD-4', 'city': 'Cilegon', 'zip': '42435', 'phone': '(0254) 391750', 'email': 'cs@megasteel.co.id', 'vat': '01.100.010.0-402.000', 'category': 'baja'},
    {'name': 'PT Pratama Wire & Mesh', 'street': 'Jl. Raya Narogong KM 11', 'city': 'Bekasi', 'zip': '17117', 'phone': '(021) 82494500', 'email': 'order@pratamawire.co.id', 'vat': '01.100.011.1-413.000', 'category': 'baja'},
    {'name': 'CV Cipta Logam Abadi', 'street': 'Jl. Raya Tangerang-Serang KM 14', 'city': 'Tangerang', 'zip': '15810', 'phone': '(021) 59401200', 'email': 'admin@ciptalogam.co.id', 'vat': '01.100.012.2-411.000', 'category': 'baja'},
    {'name': 'PT Indo Steel Konstruksi', 'street': 'Jl. Raya Sukabumi KM 18', 'city': 'Bogor', 'zip': '16720', 'phone': '(0251) 8654300', 'email': 'sales@indosteelkon.co.id', 'vat': '01.100.013.3-425.000', 'category': 'baja'},
    {'name': 'CV Sumber Baja Sejati', 'street': 'Jl. Industri Pulogadung Blok F-12', 'city': 'Jakarta Timur', 'zip': '13260', 'phone': '(021) 4602100', 'email': 'order@sumberbaja.co.id', 'vat': '01.100.014.4-007.000', 'category': 'baja'},
    {'name': 'PT Garuda Logam Persada', 'street': 'Jl. Raya Pasuruan No. 88', 'city': 'Pasuruan', 'zip': '67152', 'phone': '(0343) 421500', 'email': 'sales@garudalogam.co.id', 'vat': '01.100.015.5-624.000', 'category': 'baja'},
    {'name': 'PT Karya Sheet Pile Indonesia', 'street': 'Jl. Raya Mauk KM 7', 'city': 'Tangerang', 'zip': '15510', 'phone': '(021) 59302200', 'email': 'order@karyasheetpile.co.id', 'vat': '01.100.016.6-411.000', 'category': 'baja'},
    {'name': 'CV Megah Baja Profil', 'street': 'Jl. Rungkut Industri V No. 8', 'city': 'Surabaya', 'zip': '60293', 'phone': '(031) 8438100', 'email': 'sales@megahbaja.co.id', 'vat': '01.100.017.7-606.000', 'category': 'baja'},
    {'name': 'PT Buana Logam Konstruksi', 'street': 'Jl. Raya Solo-Sragen KM 12', 'city': 'Surakarta', 'zip': '57175', 'phone': '(0271) 853900', 'email': 'order@buanalogam.co.id', 'vat': '01.100.018.8-528.000', 'category': 'baja'},
    {'name': 'PT Indo Pile Manufaktur', 'street': 'Jl. Industri Selatan IV Blok JJ-15', 'city': 'Bekasi', 'zip': '17530', 'phone': '(021) 89998200', 'email': 'sales@indopile.co.id', 'vat': '01.100.019.9-413.000', 'category': 'baja'},
    {'name': 'CV Tama Logam Sentosa', 'street': 'Jl. Raya Bypass Mojokerto KM 6', 'city': 'Mojokerto', 'zip': '61363', 'phone': '(0321) 590800', 'email': 'admin@tamalogam.co.id', 'vat': '01.100.020.0-643.000', 'category': 'baja'},
    # === V026-V040: BETON & MATERIAL KONSTRUKSI (15 vendor) ===
    {'name': 'PT Adhi Mix Pratama', 'street': 'Jl. Pondok Indah Raya No. 5', 'city': 'Jakarta Selatan', 'zip': '12310', 'phone': '(021) 75901100', 'email': 'order@adhimix.co.id', 'vat': '02.200.001.1-007.000', 'category': 'beton'},
    {'name': 'PT Indo Ready Mix', 'street': 'Jl. TB Simatupang No. 41', 'city': 'Jakarta Selatan', 'zip': '12550', 'phone': '(021) 78832100', 'email': 'sales@indoreadymix.co.id', 'vat': '02.200.002.2-007.000', 'category': 'beton'},
    {'name': 'CV Beton Cor Sejahtera', 'street': 'Jl. Raya Cibubur KM 14', 'city': 'Bogor', 'zip': '16968', 'phone': '(021) 84933200', 'email': 'order@betoncor.co.id', 'vat': '02.200.003.3-425.000', 'category': 'beton'},
    {'name': 'PT Holcim Mix Pratama', 'street': 'Jl. Jend. Sudirman Kav. 88', 'city': 'Jakarta Pusat', 'zip': '10220', 'phone': '(021) 51400600', 'email': 'cs@holcimmix.co.id', 'vat': '02.200.004.4-007.000', 'category': 'beton'},
    {'name': 'PT Semen Pratama Indonesia', 'street': 'Jl. Veteran No. 23', 'city': 'Gresik', 'zip': '61124', 'phone': '(031) 3981900', 'email': 'sales@semenpratama.co.id', 'vat': '02.200.005.5-612.000', 'category': 'beton'},
    {'name': 'CV Mortir Karya Bangun', 'street': 'Jl. Industri Cikande KM 12', 'city': 'Serang', 'zip': '42186', 'phone': '(0254) 401700', 'email': 'order@mortirkarya.co.id', 'vat': '02.200.006.6-402.000', 'category': 'beton'},
    {'name': 'PT Mega Concrete Sejahtera', 'street': 'Jl. Raya Cakung Cilincing No. 76', 'city': 'Jakarta Utara', 'zip': '14140', 'phone': '(021) 4490100', 'email': 'sales@megaconcrete.co.id', 'vat': '02.200.007.7-007.000', 'category': 'beton'},
    {'name': 'PT Agregat Konstruksi Indonesia', 'street': 'Jl. Raya Cipanas KM 8', 'city': 'Cianjur', 'zip': '43253', 'phone': '(0263) 512800', 'email': 'order@agregatindo.co.id', 'vat': '02.200.008.8-435.000', 'category': 'beton'},
    {'name': 'CV Beton Citra Mandiri', 'street': 'Jl. Raya Margahayu KM 5', 'city': 'Bandung', 'zip': '40286', 'phone': '(022) 5407900', 'email': 'sales@betoncitra.co.id', 'vat': '02.200.009.9-423.000', 'category': 'beton'},
    {'name': 'PT Admixture Pratama Indonesia', 'street': 'Jl. Industri Pulogadung Blok H-3', 'city': 'Jakarta Timur', 'zip': '13260', 'phone': '(021) 4602500', 'email': 'cs@admixturepratama.co.id', 'vat': '02.200.010.0-007.000', 'category': 'beton'},
    {'name': 'CV Karya Beton Persada', 'street': 'Jl. Raya Cangkringan KM 7', 'city': 'Sleman', 'zip': '55584', 'phone': '(0274) 868100', 'email': 'order@karyabeton.co.id', 'vat': '02.200.011.1-543.000', 'category': 'beton'},
    {'name': 'PT Indo Ready Concrete Sejahtera', 'street': 'Jl. Raya Wonokromo No. 156', 'city': 'Surabaya', 'zip': '60243', 'phone': '(031) 8290700', 'email': 'sales@indoreadyconcrete.co.id', 'vat': '02.200.012.2-606.000', 'category': 'beton'},
    {'name': 'PT Tiang Pancang Beton Nusantara', 'street': 'Jl. Raya Setu KM 9', 'city': 'Bekasi', 'zip': '17320', 'phone': '(021) 82618900', 'email': 'order@tpbnusantara.co.id', 'vat': '02.200.013.3-413.000', 'category': 'beton'},
    {'name': 'CV Pasir Beton Mandiri', 'street': 'Jl. Raya Cikeas KM 4', 'city': 'Bogor', 'zip': '16969', 'phone': '(021) 84939100', 'email': 'admin@pasirbeton.co.id', 'vat': '02.200.014.4-425.000', 'category': 'beton'},
    {'name': 'PT Sumber Agregat Nusantara', 'street': 'Jl. Industri Cilegon Blok F-22', 'city': 'Cilegon', 'zip': '42435', 'phone': '(0254) 392100', 'email': 'sales@sumberagregat.co.id', 'vat': '02.200.015.5-402.000', 'category': 'beton'},
    # === V041-V055: ALAT BERAT & SPAREPART (15 vendor) ===
    {'name': 'PT Trakindo Utama Cabang Jakarta', 'street': 'Jl. Cilandak KKO No. 1', 'city': 'Jakarta Selatan', 'zip': '12560', 'phone': '(021) 78832500', 'email': 'parts@trakindojkt.co.id', 'vat': '03.300.001.1-007.000', 'category': 'alat_berat'},
    {'name': 'PT Hexindo Adi Perkasa Sparepart', 'street': 'Jl. Pulo Lentut No. 8', 'city': 'Jakarta Timur', 'zip': '13920', 'phone': '(021) 4600100', 'email': 'sparepart@hexindo.co.id', 'vat': '03.300.002.2-007.000', 'category': 'alat_berat'},
    {'name': 'PT Intraco Penta Wahana', 'street': 'Jl. Raya Bekasi KM 23', 'city': 'Jakarta Timur', 'zip': '13910', 'phone': '(021) 4612100', 'email': 'sales@intracopenta.co.id', 'vat': '03.300.003.3-007.000', 'category': 'alat_berat'},
    {'name': 'CV Spare Part Indo Heavy', 'street': 'Jl. Raya Bypass Pasuruan KM 4', 'city': 'Pasuruan', 'zip': '67128', 'phone': '(0343) 421100', 'email': 'order@sparepartindo.co.id', 'vat': '03.300.004.4-624.000', 'category': 'alat_berat'},
    {'name': 'PT Mitra Hidrolik Konstruksi', 'street': 'Jl. Rungkut Industri V Blok C-3', 'city': 'Surabaya', 'zip': '60293', 'phone': '(031) 8438700', 'email': 'parts@mitrahidrolik.co.id', 'vat': '03.300.005.5-606.000', 'category': 'alat_berat'},
    {'name': 'PT Drilling Rig Pratama', 'street': 'Jl. Raya Cibitung KM 5', 'city': 'Bekasi', 'zip': '17520', 'phone': '(021) 88361200', 'email': 'sales@drillingrigpratama.co.id', 'vat': '03.300.006.6-413.000', 'category': 'alat_berat'},
    {'name': 'CV Hammer Indo Pratama', 'street': 'Jl. Raya Cipanas KM 14', 'city': 'Cianjur', 'zip': '43253', 'phone': '(0263) 513400', 'email': 'order@hammerindo.co.id', 'vat': '03.300.007.7-435.000', 'category': 'alat_berat'},
    {'name': 'PT Crane Service Indonesia', 'street': 'Jl. KH. Hasyim Ashari No. 12', 'city': 'Tangerang', 'zip': '15730', 'phone': '(021) 55793400', 'email': 'sales@craneservice.co.id', 'vat': '03.300.008.8-411.000', 'category': 'alat_berat'},
    {'name': 'PT Pile Driver Mandiri', 'street': 'Jl. Raya Mauk KM 11', 'city': 'Tangerang', 'zip': '15530', 'phone': '(021) 59308200', 'email': 'parts@piledrivermandiri.co.id', 'vat': '03.300.009.9-411.000', 'category': 'alat_berat'},
    {'name': 'PT Indomesin Konstruksi', 'street': 'Jl. Raya Narogong KM 8', 'city': 'Bekasi', 'zip': '17117', 'phone': '(021) 82499100', 'email': 'sales@indomesin.co.id', 'vat': '03.300.010.0-413.000', 'category': 'alat_berat'},
    {'name': 'CV Sparepart Heavy Equipment Sejahtera', 'street': 'Jl. Raya Belitung Industri', 'city': 'Tanjung Pandan', 'zip': '33411', 'phone': '(0719) 21450', 'email': 'order@sparesheavy.co.id', 'vat': '03.300.011.1-203.000', 'category': 'alat_berat'},
    {'name': 'PT Mega Hydraulic Indonesia', 'street': 'Jl. Industri Pulogadung Blok J-7', 'city': 'Jakarta Timur', 'zip': '13260', 'phone': '(021) 4602800', 'email': 'cs@megahydraulic.co.id', 'vat': '03.300.012.2-007.000', 'category': 'alat_berat'},
    {'name': 'PT Excavator Parts Indonesia', 'street': 'Jl. Raya Cilegon KM 12', 'city': 'Cilegon', 'zip': '42432', 'phone': '(0254) 391950', 'email': 'order@excavatorparts.co.id', 'vat': '03.300.013.3-402.000', 'category': 'alat_berat'},
    {'name': 'CV Pratama Mesin Konstruksi', 'street': 'Jl. Industri Medan Star KM 5', 'city': 'Medan', 'zip': '20371', 'phone': '(061) 6837100', 'email': 'sales@pratamamesin.co.id', 'vat': '03.300.014.4-122.000', 'category': 'alat_berat'},
    {'name': 'PT Indo Pile Hammer Service', 'street': 'Jl. Raya Cangkringan KM 11', 'city': 'Sleman', 'zip': '55584', 'phone': '(0274) 868700', 'email': 'service@indopilehammer.co.id', 'vat': '03.300.015.5-543.000', 'category': 'alat_berat'},
    # === V056-V070: BBM, PELUMAS & KIMIA KONSTRUKSI (15 vendor) ===
    {'name': 'PT Petrolab Indonesia', 'street': 'Jl. Industri Cikarang Blok M-3', 'city': 'Bekasi', 'zip': '17550', 'phone': '(021) 89905100', 'email': 'sales@petrolab.co.id', 'vat': '04.400.001.1-413.000', 'category': 'bbm_kimia'},
    {'name': 'PT Migas Pratama Indonesia', 'street': 'Jl. Raya Bogor KM 28', 'city': 'Depok', 'zip': '16956', 'phone': '(021) 87703100', 'email': 'order@migaspratama.co.id', 'vat': '04.400.002.2-403.000', 'category': 'bbm_kimia'},
    {'name': 'CV Pelumas Mesin Sejahtera', 'street': 'Jl. Raya Tangerang KM 17', 'city': 'Tangerang', 'zip': '15810', 'phone': '(021) 59409200', 'email': 'cs@pelumasmesin.co.id', 'vat': '04.400.003.3-411.000', 'category': 'bbm_kimia'},
    {'name': 'PT Shell Industri Mandiri', 'street': 'Jl. Yos Sudarso Kav. 88', 'city': 'Jakarta Utara', 'zip': '14350', 'phone': '(021) 65709100', 'email': 'industrial@shellindustri.co.id', 'vat': '04.400.004.4-007.000', 'category': 'bbm_kimia'},
    {'name': 'PT Total Oli Konstruksi', 'street': 'Jl. Industri Cilegon Blok H-4', 'city': 'Cilegon', 'zip': '42435', 'phone': '(0254) 392450', 'email': 'sales@totaloli.co.id', 'vat': '04.400.005.5-402.000', 'category': 'bbm_kimia'},
    {'name': 'CV Admixture Beton Pratama', 'street': 'Jl. Raya Setu KM 11', 'city': 'Bekasi', 'zip': '17320', 'phone': '(021) 82619100', 'email': 'order@admixturepratama.co.id', 'vat': '04.400.006.6-413.000', 'category': 'bbm_kimia'},
    {'name': 'PT Sika Chemical Indonesia', 'street': 'Jl. Raya Cibitung Industri KM 6', 'city': 'Bekasi', 'zip': '17520', 'phone': '(021) 88340700', 'email': 'sales@sikachemical.co.id', 'vat': '04.400.007.7-413.000', 'category': 'bbm_kimia'},
    {'name': 'PT BASF Konstruksi Indonesia', 'street': 'Jl. Boulevard Industri Blok C-8', 'city': 'Bekasi', 'zip': '17550', 'phone': '(021) 89909100', 'email': 'order@basfkonstruksi.co.id', 'vat': '04.400.008.8-413.000', 'category': 'bbm_kimia'},
    {'name': 'CV Grouting Chemical Mandiri', 'street': 'Jl. Raya Cipanas KM 6', 'city': 'Cianjur', 'zip': '43253', 'phone': '(0263) 514100', 'email': 'cs@groutingchemical.co.id', 'vat': '04.400.009.9-435.000', 'category': 'bbm_kimia'},
    {'name': 'PT Soil Improvement Indonesia', 'street': 'Jl. Industri Pulogadung Blok L-2', 'city': 'Jakarta Timur', 'zip': '13260', 'phone': '(021) 4603300', 'email': 'order@soilimprovement.co.id', 'vat': '04.400.010.0-007.000', 'category': 'bbm_kimia'},
    {'name': 'PT Pertamina Lubricants Cabang Jatim', 'street': 'Jl. Rungkut Industri III No. 88', 'city': 'Surabaya', 'zip': '60293', 'phone': '(031) 8439100', 'email': 'pertaminajatim@pertamina.com', 'vat': '04.400.011.1-606.000', 'category': 'bbm_kimia'},
    {'name': 'CV Bahan Bakar Pratama', 'street': 'Jl. Raya Tanjung Priok KM 4', 'city': 'Jakarta Utara', 'zip': '14310', 'phone': '(021) 4392100', 'email': 'order@bbpratama.co.id', 'vat': '04.400.012.2-007.000', 'category': 'bbm_kimia'},
    {'name': 'PT Mega Chem Konstruksi', 'street': 'Jl. Raya Mauk KM 9', 'city': 'Tangerang', 'zip': '15530', 'phone': '(021) 59307600', 'email': 'sales@megachem.co.id', 'vat': '04.400.013.3-411.000', 'category': 'bbm_kimia'},
    {'name': 'CV Solar Industri Pratama', 'street': 'Jl. Yos Sudarso No. 192', 'city': 'Medan', 'zip': '20242', 'phone': '(061) 6622300', 'email': 'order@solarindustri.co.id', 'vat': '04.400.014.4-122.000', 'category': 'bbm_kimia'},
    {'name': 'PT Pelumas Industri Sejahtera', 'street': 'Jl. Raya Belmera KM 7', 'city': 'Medan', 'zip': '20371', 'phone': '(061) 6831900', 'email': 'sales@pelumasindustri.co.id', 'vat': '04.400.015.5-122.000', 'category': 'bbm_kimia'},
    # === V071-V075: LOGISTIK & JASA PENDUKUNG (10 vendor → diisi 5, plus 5 sebelumnya menjadi 10 total dengan A5) ===
    {'name': 'PT Logistik Konstruksi Mandiri', 'street': 'Jl. Cakung Cilincing No. 56', 'city': 'Jakarta Utara', 'zip': '14140', 'phone': '(021) 44910200', 'email': 'dispatch@logistikkonstruksi.co.id', 'vat': '05.500.001.1-007.000', 'category': 'logistik'},
    {'name': 'CV Trans Heavy Equipment', 'street': 'Jl. Raya Bekasi KM 24', 'city': 'Jakarta Timur', 'zip': '13910', 'phone': '(021) 46127500', 'email': 'order@transheavy.co.id', 'vat': '05.500.002.2-007.000', 'category': 'logistik'},
    {'name': 'PT Pile Testing Indonesia', 'street': 'Jl. Industri Cilegon Blok K-7', 'city': 'Cilegon', 'zip': '42435', 'phone': '(0254) 392800', 'email': 'services@piletestingind.co.id', 'vat': '05.500.003.3-402.000', 'category': 'logistik'},
    {'name': 'CV Soil Investigation Mandiri', 'street': 'Jl. Raya Cipanas KM 9', 'city': 'Cianjur', 'zip': '43253', 'phone': '(0263) 514800', 'email': 'survey@soilinvestigation.co.id', 'vat': '05.500.004.4-435.000', 'category': 'logistik'},
    {'name': 'PT Transportasi Alat Berat Pratama', 'street': 'Jl. Industri Medan Star KM 8', 'city': 'Medan', 'zip': '20371', 'phone': '(061) 6838900', 'email': 'order@transportasialatberat.co.id', 'vat': '05.500.005.5-122.000', 'category': 'logistik'},
]

CATEGORY_SCORE_TEMPLATE = {
    'baja': {'C1': (82, 95), 'C2': (70, 88), 'C3': (75, 90), 'C4': (80, 95), 'C5': (72, 88)},
    'beton': {'C1': (78, 90), 'C2': (60, 78), 'C3': (82, 95), 'C4': (75, 90), 'C5': (75, 88)},
    'alat_berat': {'C1': (80, 92), 'C2': (78, 95), 'C3': (75, 88), 'C4': (70, 85), 'C5': (82, 95)},
    'bbm_kimia': {'C1': (78, 90), 'C2': (58, 75), 'C3': (80, 92), 'C4': (80, 92), 'C5': (72, 85)},
    'logistik': {'C1': (72, 85), 'C2': (62, 80), 'C3': (85, 95), 'C4': (70, 85), 'C5': (80, 92)},
}

# Skor mentah Tabel 3.7 skripsi (Q1 2025) — hardcoded untuk menjamin ranking match
# A4 = #1 (V=0,9392); A2 = #2 (V=0,9135); A1 = #3 (V=0,9039); A5 = #4 (V=0,8900); A3 = #5 (V=0,8382)
Q1_2025_HARDCODED_SCORES = {
    'PT Baja Pondasi Sentosa':       {'C1': 92.0, 'C2': 75.0, 'C3': 85.0, 'C4': 88.0, 'C5': 80.0},
    'CV Beton Karya Mandiri':        {'C1': 85.0, 'C2': 65.0, 'C3': 88.0, 'C4': 82.0, 'C5': 85.0},
    'PT Hidrolik Teknik Prima':      {'C1': 88.0, 'C2': 80.0, 'C3': 75.0, 'C4': 70.0, 'C5': 92.0},
    'UD Pracetak Sejahtera':         {'C1': 80.0, 'C2': 55.0, 'C3': 90.0, 'C4': 85.0, 'C5': 78.0},
    'PT Mitra Logistik Konstruksi':  {'C1': 82.0, 'C2': 70.0, 'C3': 92.0, 'C4': 75.0, 'C5': 85.0},
}

CORE_VENDOR_NAMES = list(Q1_2025_HARDCODED_SCORES.keys())

DEMO_USERS = [
    {
        'name': 'Budi Santoso',
        'login': 'evaluator_demo',
        'password': 'evaluator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_evaluator',
    },
    {
        'name': 'Siti Rahayu',
        'login': 'validator_demo',
        'password': 'validator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_validator',
    },
    {
        'name': 'Ahmad Hidayat',
        'login': 'configurator_demo',
        'password': 'configurator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_configurator',
    },
]


class ScoringPeriodDemoGenerator(models.Model):
    _inherit = 'scoring.period'

    @api.model
    def generate_demo_data(self):
        """Entry point: generate 8 quarterly historical + 6 monthly recent periods.

        Q1 2025 menggunakan 5 vendor core (A1–A5) dengan skor hardcoded Tabel 3.7 skripsi.
        Periode lain menggunakan 15–25 vendor aktif acak dari 75 master vendor.
        """
        existing_demo = self.search([
            ('name', 'like', 'Evaluasi Vendor - %'),
        ], limit=1)
        if existing_demo:
            raise UserError(
                "Demo data sudah pernah di-generate. "
                "Hapus periode evaluasi yang ada terlebih dahulu jika ingin generate ulang."
            )

        demo_users = self._ensure_demo_users()
        self._setup_company_info()
        vendors = self._ensure_demo_vendors()
        package = self.env.ref(
            'gifari_vendor_scoring.package_default_5c',
            raise_if_not_found=False,
        )
        if not package or not package.line_ids:
            raise UserError(
                "Paket Kriteria default tidak ditemukan atau kosong. "
                "Pastikan modul terinstall dengan benar."
            )

        quarterly_ids = self._generate_quarterly_periods(vendors, package, demo_users)
        monthly_ids = self._generate_monthly_periods(vendors, package, demo_users)
        generated_period_ids = quarterly_ids + monthly_ids

        return {
            'type': 'ir.actions.act_window',
            'name': 'Demo Data - Periode Evaluasi',
            'res_model': 'scoring.period',
            'view_mode': 'list,form',
            'domain': [('id', 'in', generated_period_ids)],
            'target': 'current',
        }

    @api.model
    def _setup_company_info(self):
        """Set the current company's identity to PT Indopora."""
        company = self.env.company
        indonesia = self.env['res.country'].search([
            ('code', '=', 'ID'),
        ], limit=1)
        update_vals = {
            'name': COMPANY_INFO['name'],
            'street': COMPANY_INFO['street'],
            'street2': COMPANY_INFO['street2'],
            'city': COMPANY_INFO['city'],
            'zip': COMPANY_INFO['zip'],
            'phone': COMPANY_INFO['phone'],
            'email': COMPANY_INFO['email'],
            'website': COMPANY_INFO['website'],
            'vat': COMPANY_INFO['vat'],
            'company_registry': COMPANY_INFO['company_registry'],
        }
        if indonesia:
            update_vals['country_id'] = indonesia.id
        company.write(update_vals)
        company.partner_id.write(update_vals)

    @api.model
    def _ensure_demo_vendors(self):
        """Find or create the 75 vendor partners (5 core + 70 anonim)."""
        partner_model = self.env['res.partner']
        vendor_records = partner_model
        for vendor_def in VENDOR_MASTER:
            vendor_vals = {
                key: value for key, value in vendor_def.items()
                if key != 'category'
            }
            existing = partner_model.search([
                ('name', '=', vendor_def['name']),
            ], limit=1)
            if existing:
                vendor_records |= existing
            else:
                vendor_records |= partner_model.create({
                    **vendor_vals,
                    'supplier_rank': 1,
                    'company_type': 'company',
                })
        return vendor_records

    @api.model
    def _ensure_demo_users(self):
        """Find or create 3 demo users with Evaluator, Validator, Configurator roles."""
        user_model = self.env['res.users'].with_context(no_reset_password=True)
        created_users = {}
        for user_def in DEMO_USERS:
            existing = user_model.search([
                ('login', '=', user_def['login']),
            ], limit=1)
            if existing:
                created_users[user_def['login']] = existing
            else:
                group = self.env.ref(user_def['group_xml_id'])
                new_user = user_model.create({
                    'name': user_def['name'],
                    'login': user_def['login'],
                    'password': user_def['password'],
                    'group_ids': [(4, group.id)],
                })
                created_users[user_def['login']] = new_user
        return created_users

    @api.model
    def _pick_active_vendors_for_period(self, vendors, period_seed, min_count=15, max_count=25):
        """Pick a deterministic random subset of vendors for a period.

        Seed dibangun dari nama periode agar hasil reproducible antar re-generate.
        """
        seed_hash = int(hashlib.md5(period_seed.encode('utf-8')).hexdigest()[:8], 16)
        rng = random.Random(seed_hash)
        active_count = rng.randint(min_count, max_count)
        vendor_list = list(vendors)
        return vendor_list, rng.sample(vendor_list, min(active_count, len(vendor_list)))

    @api.model
    def _generate_quarterly_periods(self, vendors, package, demo_users):
        """Generate 8 kuartal historis Q1 2024 – Q4 2025; semua state=validated.

        Q1 2025 khusus: hanya 5 vendor core (A1–A5) dengan skor hardcoded Tabel 3.7
        agar ranking identik dengan studi kasus skripsi.
        """
        evaluator = demo_users['evaluator_demo']
        validator = demo_users['validator_demo']
        generated_ids = []

        quarters = [
            (2024, 1), (2024, 2), (2024, 3), (2024, 4),
            (2025, 1), (2025, 2), (2025, 3), (2025, 4),
        ]
        for year, quarter in quarters:
            start_month = (quarter - 1) * 3 + 1
            period_start = date(year, start_month, 1)
            period_end = period_start + relativedelta(months=3, days=-1)
            period_name = "Evaluasi Vendor - Q%d %d" % (quarter, year)

            if year == 2025 and quarter == 1:
                # Studi kasus utama skripsi — gunakan A1–A5 saja
                period_vendors = self.env['res.partner'].browse([
                    vendor.id for vendor in vendors
                    if vendor.name in CORE_VENDOR_NAMES
                ])
                use_hardcoded = True
            else:
                _full_list, picked_list = self._pick_active_vendors_for_period(
                    vendors, period_name, min_count=15, max_count=25,
                )
                period_vendors = self.env['res.partner'].browse([v.id for v in picked_list])
                use_hardcoded = False

            period_criteria_vals = [
                (0, 0, {
                    'criterion_id': pkg_line.criterion_id.id,
                    'weight': pkg_line.weight,
                })
                for pkg_line in package.line_ids
            ]

            period = self.create({
                'name': period_name,
                'date_from': period_start,
                'date_to': period_end,
                'package_id': package.id,
                'evaluator_id': evaluator.id,
                'state': 'draft',
                'period_criterion_ids': period_criteria_vals,
                'partner_ids': [(6, 0, period_vendors.ids)],
            })

            self._create_vendor_scores(
                period, period_vendors, package,
                period_seed=period_name,
                use_hardcoded_q1_2025=use_hardcoded,
            )
            self._calculate_saw_silent(period)

            period.write({
                'state': 'validated',
                'validator_id': validator.id,
                'validation_date': fields.Datetime.from_string(
                    '%s 17:00:00' % period_end
                ),
            })
            generated_ids.append(period.id)

        return generated_ids

    @api.model
    def _generate_monthly_periods(self, vendors, package, demo_users):
        """Generate 6 bulan terkini November 2025 – April 2026.

        5 bulan pertama state=validated. Bulan terakhir state=scoring agar
        user dapat melanjutkan input/pengujian sistem.
        """
        evaluator = demo_users['evaluator_demo']
        validator = demo_users['validator_demo']
        generated_ids = []

        months = [
            (2025, 11), (2025, 12),
            (2026, 1), (2026, 2), (2026, 3), (2026, 4),
        ]
        for index, (year, month) in enumerate(months):
            period_start = date(year, month, 1)
            period_end = period_start + relativedelta(months=1, days=-1)
            month_label = INDONESIAN_MONTHS[month]
            period_name = "Evaluasi Vendor - %s %d" % (month_label, year)
            is_last_month = (index == len(months) - 1)

            _full_list, picked_list = self._pick_active_vendors_for_period(
                vendors, period_name, min_count=18, max_count=22,
            )
            period_vendors = self.env['res.partner'].browse([v.id for v in picked_list])

            period_criteria_vals = [
                (0, 0, {
                    'criterion_id': pkg_line.criterion_id.id,
                    'weight': pkg_line.weight,
                })
                for pkg_line in package.line_ids
            ]

            period = self.create({
                'name': period_name,
                'date_from': period_start,
                'date_to': period_end,
                'package_id': package.id,
                'evaluator_id': evaluator.id,
                'state': 'draft',
                'period_criterion_ids': period_criteria_vals,
                'partner_ids': [(6, 0, period_vendors.ids)],
            })

            self._create_vendor_scores(
                period, period_vendors, package,
                period_seed=period_name,
                use_hardcoded_q1_2025=False,
            )

            if is_last_month:
                # Bulan berjalan: tetap di state scoring agar user bisa lanjut input
                period.write({'state': 'scoring'})
            else:
                self._calculate_saw_silent(period)
                period.write({
                    'state': 'validated',
                    'validator_id': validator.id,
                    'validation_date': fields.Datetime.from_string(
                        '%s 17:00:00' % period_end
                    ),
                })

            generated_ids.append(period.id)

        return generated_ids

    @api.model
    def _create_vendor_scores(self, period, vendors, package, period_seed='',
                              use_hardcoded_q1_2025=False):
        """Create vendor.score + vendor.score.line for the given vendors.

        Jika use_hardcoded_q1_2025=True, skor mentah diambil dari Q1_2025_HARDCODED_SCORES
        agar ranking identik dengan Tabel 3.7 skripsi. Selain itu, skor di-random
        dengan profile per-kategori, di-seed deterministik berdasarkan periode.
        """
        score_model = self.env['vendor.score']
        seed_hash = int(hashlib.md5(period_seed.encode('utf-8')).hexdigest()[:8], 16) if period_seed else 0
        rng = random.Random(seed_hash)

        vendor_category_by_name = {entry['name']: entry['category'] for entry in VENDOR_MASTER}

        score_vals_batch = []
        for vendor in vendors:
            score_line_vals = []
            for pkg_line in package.line_ids:
                criterion_code = pkg_line.criterion_id.code

                if use_hardcoded_q1_2025 and vendor.name in Q1_2025_HARDCODED_SCORES:
                    raw = Q1_2025_HARDCODED_SCORES[vendor.name][criterion_code]
                else:
                    category = vendor_category_by_name.get(vendor.name, 'baja')
                    score_range = CATEGORY_SCORE_TEMPLATE[category].get(criterion_code, (70, 90))
                    if pkg_line.criterion_type == 'cost':
                        raw = round(rng.uniform(score_range[0], score_range[1]), 2)
                    else:
                        raw = float(rng.randint(score_range[0], score_range[1]))

                score_line_vals.append((0, 0, {
                    'criterion_id': pkg_line.criterion_id.id,
                    'raw_score': raw,
                }))

            score_vals_batch.append({
                'period_id': period.id,
                'partner_id': vendor.id,
                'score_line_ids': score_line_vals,
            })

        score_model.create(score_vals_batch)

    @api.model
    def _calculate_saw_silent(self, period):
        """Replicate SAW calculation without sending emails or creating activities."""
        criterion_matrix = {}
        for period_criterion in period.period_criterion_ids:
            criterion_matrix[period_criterion.criterion_id.id] = {
                'type': period_criterion.criterion_type,
                'weight_decimal': period_criterion.weight_decimal,
                'raw_values': {},
            }

        for vendor_score in period.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                criterion_matrix[score_line.criterion_id.id]['raw_values'][vendor_score.id] = score_line.raw_score

        for criterion_data in criterion_matrix.values():
            all_raw = list(criterion_data['raw_values'].values())
            criterion_data['max_raw'] = max(all_raw) if all_raw else 1
            criterion_data['min_raw'] = min(all_raw) if all_raw else 1

        for vendor_score in period.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                crit = criterion_matrix[score_line.criterion_id.id]
                raw = score_line.raw_score
                if crit['type'] == 'benefit':
                    normalized = raw / crit['max_raw'] if crit['max_raw'] else 0
                else:
                    normalized = crit['min_raw'] / raw if raw else 0
                weighted = normalized * crit['weight_decimal']
                score_line.write({
                    'normalized_score': normalized,
                    'weighted_score': weighted,
                })

        for vendor_score in period.vendor_score_ids:
            vendor_score.write({
                'final_score': sum(vendor_score.score_line_ids.mapped('weighted_score')),
            })

        ranked_scores = period.vendor_score_ids.sorted(
            key=lambda vs: vs.final_score, reverse=True,
        )
        for ranking, vendor_score in enumerate(ranked_scores, start=1):
            vendor_score.write({
                'rank': ranking,
                'is_recommended': ranking == 1,
            })

        period.write({'state': 'calculated'})
