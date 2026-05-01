# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Sale Discount Approval Configuration ─────────────

    sale_disc_approval_enabled = fields.Boolean(
        string='Enable Sale Discount Approval',
        default=False,
        help="When enabled, Sales Orders with discounts exceeding "
             "configured thresholds will require approval.",
    )
    sale_disc_check_mode = fields.Selection(
        [
            ('per_line', 'Per-Line Discount'),
            ('global', 'Global Discount'),
            ('both', 'Both (OR Logic)'),
        ],
        string='Discount Check Mode',
        default='both',
        help="Per-Line: check max discount on any single line.\n"
             "Global: check overall discount percentage.\n"
             "Both: trigger if EITHER exceeds threshold (OR logic).",
    )
