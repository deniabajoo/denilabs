# -*- coding: utf-8 -*-
{
    'name': 'Gifari Product Discount Recommendation (SPK-SAW)',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Sales/Sales',
    'summary': 'Sistem Pendukung Keputusan rekomendasi diskon produk berbasis SAW',
    'description': """
        Modul SPK menggunakan metode Simple Additive Weighting (SAW) untuk:
        - Menghitung skor produk berdasarkan 4 kriteria
        - Menghasilkan rekomendasi diskon optimal per produk
        - Menampilkan rekomendasi pada Sales Order Line
        - Cron job harian untuk recalculate scoring
        - Integrasi dengan modul gifari_sale_discount_approval
    """,
    'depends': [
        'sale',
        'sale_stock',
        'sale_management',
        'stock',
        'account',
        'gifari_sale_discount_approval',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/spk_saw_criterion_data.xml',
        'data/ir_cron.xml',
        'views/spk_saw_criterion_views.xml',
        'views/spk_saw_product_score_views.xml',
        'views/sale_order_line_views.xml',
        'views/spk_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
