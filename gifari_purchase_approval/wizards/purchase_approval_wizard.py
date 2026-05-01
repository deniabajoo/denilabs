# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseApprovalWizard(models.TransientModel):
    _name = 'purchase.approval.wizard'
    _description = 'Purchase Approval Wizard'

    # ── Context Fields ───────────────────────────────────

    order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
    )
    level_id = fields.Many2one(
        'purchase.approval.level',
        string='Approval Level',
        readonly=True,
    )
    order_partner = fields.Char(
        related='order_id.partner_id.name',
        string='Vendor',
    )
    order_amount = fields.Monetary(
        related='order_id.amount_untaxed',
        string='Amount (Untaxed)',
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
    )

    # ── Action Fields ────────────────────────────────────

    action = fields.Selection(
        [
            ('approve', 'Approve'),
            ('reject', 'Reject'),
        ],
        string='Action',
        required=True,
        default='approve',
    )
    rejected_reason = fields.Text(
        string='Reason',
        help="Required when rejecting.",
    )
    notes = fields.Text(string='Additional Notes')

    # ── Validation ───────────────────────────────────────

    @api.constrains('action', 'rejected_reason')
    def _check_rejection_reason(self):
        for wizard in self:
            if wizard.action == 'reject' and not wizard.rejected_reason:
                raise ValidationError(
                    _("Please provide a reason for rejection.")
                )

    # ── Actions ──────────────────────────────────────────

    def action_confirm_wizard(self):
        """Execute the approve or reject action."""
        self.ensure_one()
        order = self.order_id

        if self.action == 'approve':
            order.action_approve_purchase(notes=self.notes or '')
        elif self.action == 'reject':
            order.action_reject_purchase(reason=self.rejected_reason or '')

        return {'type': 'ir.actions.act_window_close'}
