# -*- coding: utf-8 -*-
{
    'name': 'Gifari Purchase Discount Approval',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Purchase',
    'summary': 'Approval workflow for Purchase Orders exceeding discount thresholds',
    'description': """
        Adds a configurable discount approval workflow to Purchase Orders.
        When a PO's discount exceeds the configured threshold (% or amount),
        the order is blocked and requires approval from designated Purchasing Managers.

        Features:
        - Configurable approval trigger: by discount % and/or discount amount
        - Discount amount field on PO lines (computed from % + manual override)
        - Configurable list of approvers per company
        - Counter-offer: approver can propose a lower discount
        - Email + in-app notifications
        - Dedicated 'Approval Queue' menu for purchasing managers
        - Full chatter audit trail
    """,
    'depends': ['purchase', 'gifari_sale_discount_approval'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_discount_approval_wizard_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_approval_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
