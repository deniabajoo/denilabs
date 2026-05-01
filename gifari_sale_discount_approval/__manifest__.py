# -*- coding: utf-8 -*-
{
    'name': 'Gifari Sale Discount Approval',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Sales/Sales',
    'summary': 'Multi-level discount approval workflow for Sales Orders',
    'description': """
        Adds configurable multi-level approval workflow for Sales Order discounts.

        Features:
        - N-level approval based on discount percentage thresholds
        - Per-line and global discount checking (OR logic)
        - Sequential approval flow (L1 → L2 → L3)
        - Counter-offer support (approver can modify discount)
        - Full audit trail with approval logs
        - Stock availability warning on SO lines
        - Cross-module notification when goods received in warehouse
        - In-app activity notifications to approvers
        - Approval Queue menu
    """,
    'depends': [
        'sale',
        'sale_stock',
        'sale_management',
    ],
    'data': [
        # Security (load first)
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        # Data
        'data/mail_activity_type.xml',

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
