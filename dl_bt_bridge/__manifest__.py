# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DL BT Bridge - Bluetooth Thermal Printer',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Direct Bluetooth thermal printing for Android POS via Intent Deep Links',
    'description': """
        Bypass IoT Box and browser printing to enable Android POS users
        to print receipts directly to Bluetooth thermal printers using
        RawBT or compatible Intent-based apps.

        Features:
        - Configuration toggles in POS Settings (Connected Devices section)
        - Support for 58mm (384px) and 80mm (576px) thermal paper
        - Multiple intent scheme support (RawBT, PrinterShare, POS BT Printer)
        - Automatic fallback to browser print on non-Android devices
        - Graceful error handling with user-facing dialogs

        Developed for PT Abajoo Transformasi Digital.
    """,
    'author': 'PT Abajoo Transformasi Digital',
    'website': 'https://abajoo.com',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'dl_bt_bridge/static/src/js/bt_utils.js',
            'dl_bt_bridge/static/src/js/bt_printer_service.js',
            'dl_bt_bridge/static/src/css/bt_receipt.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
