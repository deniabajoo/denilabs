# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleDiscountApprovalLog(models.Model):
    _name = 'sale.discount.approval.log'
    _description = 'Sale Discount Approval Log'
    _order = 'create_date desc'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, index=True,
    )
    order_id = fields.Many2one(
        'sale.order', required=True, ondelete='cascade', index=True,
    )
    level_id = fields.Many2one(
        'sale.discount.approval.level', ondelete='set null',
    )
    user_id = fields.Many2one(
        'res.users', required=True,
        default=lambda self: self.env.user,
    )
    action = fields.Selection(
        [
            ('submit',        'Submitted for Approval'),
            ('approve',       'Approved'),
            ('reject',        'Rejected'),
            ('counter_offer', 'Counter-Offer Applied'),
            ('resubmit',      'Re-submitted'),
            ('cancel',        'Cancelled'),
            ('escalate',      'Escalated (SLA Breach)'),
            ('delegate',      'Delegated to Another User'),
        ],
        string='Action',
        required=True,
    )
    notes = fields.Text(string='Notes / Reason')
    old_max_discount = fields.Float(digits='Discount')
    new_max_discount = fields.Float(digits='Discount')

    delegated_to_id = fields.Many2one(
        'res.users',
        string='Delegated To',
        help="Diisi jika action = delegate.",
    )

    ip_address = fields.Char(string='IP Address')
    timestamp = fields.Datetime(
        default=fields.Datetime.now, required=True,
    )

    @api.depends('user_id', 'action', 'level_id')
    def _compute_display_name(self):
        for record in self:
            level_name = record.level_id.name or ''
            action_label = dict(
                record._fields['action'].selection
            ).get(record.action, '')
            record.display_name = (
                f"{record.user_id.name} — {action_label}"
                f"{(' (' + level_name + ')') if level_name else ''}"
            )
