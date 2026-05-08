# -*- coding: utf-8 -*-
{
    'name': 'Gifari Demo Data — PT Indopora',
    'version': '19.0.2.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Hidden/Tools',
    'summary': 'Generates 6-month demo data for approval + SPK-SAW discount recommendation',
    'description': """
        Demo data generator v2.0 untuk PT Indopora.

        Creates:
        - Company, users, customers, vendors
        - 50+ construction products with IDR pricing
        - 3-level discount approval (with SLA, delegation, escalation)
        - SAW criteria + product scoring
        - 6 months of SO transactions with varied approval states
        - Stock movements → aging & overstocking scenarios
        - SPK-SAW scores otomatis dihitung setelah generation
    """,
    'depends': [
        'gifari_sale_discount_approval',
        'gifari_product_discount_recommendation',
        'gifari_purchase_approval',
        'gifari_approval_dashboard',
        'l10n_id',
        'stock',
        'account',
        'sale_management',
        'purchase_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_company.xml',
        'data/res_partner.xml',
        'data/res_users.xml',
        'data/product_category.xml',
        'data/product_template.xml',
        'data/approval_levels.xml',
        'wizard/demo_data_wizard_views.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
