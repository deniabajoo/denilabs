# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Purchase Approval Configuration ──────────────────

    purchase_approval_enabled = fields.Boolean(
        string='Enable Purchase Amount Approval',
        default=False,
        help="When enabled, Purchase Orders with amounts exceeding "
             "configured thresholds will require multi-level approval.",
    )
