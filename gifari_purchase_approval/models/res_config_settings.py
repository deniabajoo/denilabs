# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Purchase Approval ────────────────────────────────

    purchase_approval_enabled = fields.Boolean(
        related='company_id.purchase_approval_enabled',
        readonly=False,
    )
