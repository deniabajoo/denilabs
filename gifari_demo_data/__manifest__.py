# -*- coding: utf-8 -*-
{
    'name': 'Gifari Demo Data — PT Indopora',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Hidden/Tools',
    'summary': 'Generates 6-month realistic demo data for PT Indopora approval system',
    'description': """
        Demo data generator for the PT Indopora Approval System.

        Creates:
        - 50+ construction products with IDR pricing
        - 20+ customers and 15+ vendors
        - 3-level approval configurations (Sale + Purchase)
        - 6 months of SO and PO transactions
        - Varied approval statuses (approved, pending, rejected)
        - Stock movements, deliveries, and invoices
        - Realistic approval audit logs

        IMPORTANT: Only loads when Odoo is started with demo data enabled.
    """,
    'depends': [
        'gifari_sale_discount_approval',
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
        # Master data — always loaded
        'data/res_company.xml',
        'data/res_partner.xml',
        'data/res_users.xml',
        'data/product_category.xml',
        'data/product_template.xml',
        'data/approval_levels.xml',
        'wizard/demo_data_wizard_views.xml',
    ],
    'demo': [
        # Transaction data — demo mode only
        # Handled by post_init_hook instead of XML
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
