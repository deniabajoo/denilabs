# -*- coding: utf-8 -*-
{
    'name': 'Gifari Approval Dashboard',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'website': 'https://www.indopora.co.id',
    'category': 'Sales/Sales',
    'summary': 'Centralized OWL dashboard for monitoring Sale & Purchase approvals',
    'description': """
        Unified dashboard for monitoring all pending approvals
        from Sale Discount Approval and Purchase Amount Approval modules.

        Features:
        - KPI cards: Total Pending, Approved Today, Rejected Today
        - Pending approval lists with aging indicators
        - Quick approve/reject via modal
        - Navigation links to respective approval queues
    """,
    'depends': [
        'gifari_sale_discount_approval',
        'gifari_purchase_approval',
    ],
    'data': [
        'views/dashboard_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gifari_approval_dashboard/static/src/css/approval_dashboard.css',
            'gifari_approval_dashboard/static/src/xml/approval_dashboard.xml',
            'gifari_approval_dashboard/static/src/js/approval_dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
