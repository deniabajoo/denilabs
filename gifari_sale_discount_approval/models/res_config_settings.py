# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Sale Discount Approval ──────────────────────────────────────────
    sale_disc_approval_enabled = fields.Boolean(
        related='company_id.sale_disc_approval_enabled',
        readonly=False,
        string='Enable Discount Approval Workflow',
    )
    sale_disc_approval_type = fields.Selection(
        related='company_id.sale_disc_approval_type',
        readonly=False,
        string='Approval Trigger',
    )
    sale_disc_approval_percent = fields.Float(
        related='company_id.sale_disc_approval_percent',
        readonly=False,
        string='Max Allowed Discount (%)',
    )
    sale_disc_approval_amount = fields.Monetary(
        related='company_id.sale_disc_approval_amount',
        readonly=False,
        string='Max Allowed Discount Amount',
    )
    sale_approval_user_ids = fields.Many2many(
        related='company_id.sale_approval_user_ids',
        readonly=False,
        string='Sales Approval Users',
    )
