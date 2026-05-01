# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_disc_approval_enabled = fields.Boolean(
        related='company_id.purchase_disc_approval_enabled',
        readonly=False,
    )
    purchase_disc_approval_type = fields.Selection(
        related='company_id.purchase_disc_approval_type',
        readonly=False,
    )
    purchase_disc_approval_percent = fields.Float(
        related='company_id.purchase_disc_approval_percent',
        readonly=False,
    )
    purchase_disc_approval_amount = fields.Monetary(
        related='company_id.purchase_disc_approval_amount',
        readonly=False,
    )
    purchase_approval_user_ids = fields.Many2many(
        related='company_id.purchase_approval_user_ids',
        readonly=False,
    )
