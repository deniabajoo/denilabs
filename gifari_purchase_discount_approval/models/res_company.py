# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Purchase Discount Approval ──────────────────────────────────────
    purchase_disc_approval_enabled = fields.Boolean(
        string='Enable Purchase Discount Approval',
        default=False,
    )
    purchase_disc_approval_type = fields.Selection(
        selection=[
            ('percent', 'Discount Percentage (%)'),
            ('amount', 'Discount Amount (Nominal)'),
            ('both', 'Both (Either condition triggers)'),
        ],
        string='PO Approval Trigger',
        default='percent',
    )
    purchase_disc_approval_percent = fields.Float(
        string='Max Allowed PO Discount (%)',
        default=10.0,
    )
    purchase_disc_approval_amount = fields.Monetary(
        string='Max Allowed PO Discount Amount',
        currency_field='currency_id',
    )
    purchase_approval_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='res_company_purchase_approver_rel',
        column1='company_id',
        column2='user_id',
        string='Purchase Approval Users',
        domain=[('share', '=', False)],
        help='Users authorized to approve Purchase Orders with excessive discounts. '
             'Falls back to Purchase Manager group if empty.',
    )
