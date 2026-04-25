# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    bt_print_enabled = fields.Boolean(
        string="Mobile Bluetooth Print",
        default=False,
        help=(
            "Enable direct Bluetooth thermal printing for Android POS devices. "
            "Bypasses IoT Box and browser printing. Requires a compatible "
            "Android printing app (e.g., RawBT) installed on the device."
        ),
    )
    bt_intent_scheme = fields.Selection(
        selection=[
            ('rawbt', 'RawBT'),
            ('printershare', 'PrinterShare'),
            ('pos_bluetooth_printer', 'POS BT Printer'),
        ],
        string="Intent Scheme",
        default='rawbt',
        help="Select the Android app that handles Bluetooth print intents.",
    )
    bt_paper_size = fields.Selection(
        selection=[
            ('58mm', '58mm (384px)'),
            ('80mm', '80mm (576px)'),
        ],
        string="Paper Size",
        default='58mm',
        help=(
            "Thermal printer paper width. Determines the pixel width used "
            "when rendering the receipt image. 58mm = 384px, 80mm = 576px."
        ),
    )
