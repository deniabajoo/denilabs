# -*- coding: utf-8 -*-
{
    'name': 'Gifari Purchase Approval',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Inventory/Purchase',
    'summary': 'Multi-level amount-based approval workflow for Purchase Orders',
    'description': """
        Extends standard Purchase Order approval to support N-level
        amount-based approval tiers.

        Features:
        - N-level approval based on amount_untaxed thresholds
        - Sequential approval flow (L1 → L2 → L3)
        - Bypass for PO from Purchase Agreements
        - Re-approval when approved PO is unlocked and edited
        - Full audit trail with approval logs
        - In-app activity notifications to approvers
        - Approval Queue menu
    """,
    'depends': [
        'purchase',
        'purchase_stock',
    ],
    'data': [
        # Security
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        # Data
        'data/mail_activity_type.xml',

        # Views
        'views/purchase_approval_level_views.xml',
        'views/purchase_approval_wizard_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_approval_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
