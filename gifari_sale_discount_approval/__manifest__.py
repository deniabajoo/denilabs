# -*- coding: utf-8 -*-
{
    'name': 'Gifari Sale Discount Approval',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Sales/Sales',
    'summary': 'Approval workflow for Sales Orders exceeding discount thresholds',
    'description': """
        Adds a configurable discount approval workflow to Sales Orders.
        When a quotation's discount exceeds the configured threshold (% or amount),
        the order is blocked and requires approval from designated managers
        before it can be confirmed.

        Features:
        - Configurable approval trigger: by discount % and/or discount amount
        - Configurable list of approvers per company
        - Counter-offer: approver can propose a lower discount
        - Email + in-app notifications for pending/approved/rejected
        - Dedicated 'Approval Queue' menu for managers
        - Full chatter audit trail
    """,
    'depends': ['sale_management'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/res_config_settings_views.xml',
        'views/sale_discount_approval_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/sale_approval_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
