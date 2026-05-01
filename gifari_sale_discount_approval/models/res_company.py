# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Sale Discount Approval ──────────────────────────────────────────
    sale_disc_approval_enabled = fields.Boolean(
        string='Enable Sale Discount Approval',
        default=False,
    )
    sale_disc_approval_type = fields.Selection(
        selection=[
            ('percent', 'Discount Percentage (%)'),
            ('amount', 'Discount Amount (Nominal)'),
            ('both', 'Both (Either condition triggers)'),
        ],
        string='Approval Trigger',
        default='percent',
    )
    sale_disc_approval_percent = fields.Float(
        string='Max Allowed Discount (%)',
        default=20.0,
        help='Sales Orders with any line discount exceeding this percentage will require approval.',
    )
    sale_disc_approval_amount = fields.Monetary(
        string='Max Allowed Discount Amount',
        currency_field='currency_id',
        help='Sales Orders with total discount amount exceeding this value will require approval.',
    )
    sale_approval_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='res_company_sale_approver_rel',
        column1='company_id',
        column2='user_id',
        string='Sales Approval Users',
        domain=[('share', '=', False)],
        help='Users who are authorized to approve or reject Sales Orders pending discount approval. '
             'If empty, falls back to all users in the Sales Manager group.',
    )
