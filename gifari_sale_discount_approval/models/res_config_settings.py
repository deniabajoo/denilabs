# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Sale Discount Approval ─────────────────────────

    sale_disc_approval_enabled = fields.Boolean(
        related='company_id.sale_disc_approval_enabled',
        readonly=False,
    )
    sale_disc_check_mode = fields.Selection(
        related='company_id.sale_disc_check_mode',
        readonly=False,
    )
