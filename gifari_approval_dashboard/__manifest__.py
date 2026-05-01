# -*- coding: utf-8 -*-
{
    'name': 'Gifari Approval Dashboard',
    'version': '19.0.1.0.0',
    'author': 'Ikhwanudin Gifari — PT Indopora',
    'category': 'Extra Tools',
    'summary': 'Interactive dashboard to monitor Sales & Purchase discount approval workflows',
    'depends': [
        'gifari_sale_discount_approval',
        'gifari_purchase_discount_approval',
        'web',
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
    'license': 'LGPL-3',
}
