{
    'name': 'Vendor Scoring - SAW Method',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Vendor Management',
    'summary': 'Evaluasi & perangkingan pemasok menggunakan metode Simple Additive Weighting (SAW)',
    'description': """
Vendor Scoring - SAW Method
============================
Custom module evaluasi pemasok menggunakan metode Simple Additive Weighting (SAW)
yang terintegrasi dengan modul Purchase pada Odoo 19 Community.

Fitur Utama:
- Konfigurasi kriteria evaluasi dinamis (benefit/cost)
- Input skor pemasok skala 1-10
- Normalisasi matriks keputusan otomatis
- Perhitungan nilai preferensi (Vᵢ = Σ wⱼ × rᵢⱼ)
- Perangkingan pemasok otomatis
- Laporan PDF hasil evaluasi
- Hak akses konfigurabel via Settings
    """,
    'author': 'Ikhwanudin Gifari',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['purchase', 'web', 'mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/default_criteria.xml',
        'data/mail_templates.xml',
        'data/ir_cron_data.xml',
        'views/scoring_criterion_views.xml',
        'views/scoring_package_views.xml',
        'views/scoring_period_views.xml',
        'views/dashboard_action.xml',
        'views/res_partner_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/res_config_settings_views.xml',
        'views/vendor_scoring_menu.xml',
        'reports/scoring_report_action.xml',
        'reports/scoring_report_template.xml',
        'data/demo_data_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gifari_vendor_scoring/static/src/js/scoring_matrix/scoring_matrix.js',
            'gifari_vendor_scoring/static/src/js/scoring_matrix/scoring_matrix.xml',
            'gifari_vendor_scoring/static/src/js/scoring_matrix/scoring_matrix.scss',
            'gifari_vendor_scoring/static/src/js/dashboard/vendor_scoring_dashboard.js',
            'gifari_vendor_scoring/static/src/js/dashboard/vendor_scoring_dashboard.xml',
            'gifari_vendor_scoring/static/src/js/dashboard/vendor_scoring_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
}
