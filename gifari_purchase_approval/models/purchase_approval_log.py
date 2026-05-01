# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PurchaseApprovalLog(models.Model):
    _name = 'purchase.approval.log'
    _description = 'Purchase Approval Log'
    _order = 'create_date desc'
    _check_company_auto = True

    # ── Relations ────────────────────────────────────────

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    level_id = fields.Many2one(
        'purchase.approval.level',
        string='Approval Level',
        ondelete='set null',
    )

    # ── Action Details ───────────────────────────────────

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
    )
    action = fields.Selection(
        [
            ('submit', 'Submitted for Approval'),
            ('approve', 'Approved'),
            ('reject', 'Rejected'),
            ('resubmit', 'Re-submitted'),
            ('cancel', 'Cancelled'),
            ('reset', 'Reset (Re-approval Required)'),
        ],
        string='Action',
        required=True,
    )
    notes = fields.Text(string='Notes / Reason')

    # ── Amount Tracking ──────────────────────────────────

    order_amount = fields.Monetary(
        string='Order Amount (Untaxed)',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='order_id.currency_id',
    )

    # ── Audit Fields ─────────────────────────────────────

    ip_address = fields.Char(string='IP Address')
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
    )

    # ── Display ──────────────────────────────────────────

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
