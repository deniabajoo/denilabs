# -*- coding: utf-8 -*-
{
    'name': 'Gifari Sale Discount Approval',
    'version': '19.0.2.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Sales/Sales',
    'summary': 'Multi-level discount approval workflow with SLA, delegation & SPK integration',
    'description': """
        Enhancement v2.0.0:
        - SLA per approval level dengan auto-eskalasi via cron
        - Email template notifikasi approval & rejection
        - Delegasi approval ke user lain
        - Lock order line setelah approved (prevent discount editing)
        - Integrasi dengan modul SPK-SAW (rekomendasi diskon)
        - Improved counter-offer: proportional adjustment lebih akurat
    """,
    'depends': [
        'sale',
        'sale_stock',
        'sale_management',
        'mail',
    ],
    'data': [
        # Security (load first)
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        # Data
        'data/mail_activity_type.xml',
        'data/mail_template.xml',
        'data/ir_cron.xml',

        # Views
        'views/sale_discount_approval_level_views.xml',
        'views/sale_discount_approval_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_approval_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
