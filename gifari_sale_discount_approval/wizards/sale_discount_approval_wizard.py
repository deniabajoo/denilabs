# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleDiscountApprovalWizard(models.TransientModel):
    _name = 'sale.discount.approval.wizard'
    _description = 'Sale Discount Approval Wizard'

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
    )
    action = fields.Selection(
        selection=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
        ],
        string='Action',
        required=True,
        default='approve',
    )
    # Read-only info fields for context
    current_discount_percent = fields.Float(
        string='Current Max Discount (%)',
        readonly=True,
    )
    current_discount_amount = fields.Monetary(
        string='Current Total Discount Amount',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        string='Currency',
    )
    partner_id = fields.Many2one(
        related='order_id.partner_id',
        string='Customer',
    )
    amount_total = fields.Monetary(
        related='order_id.amount_total',
        string='Order Total',
        currency_field='currency_id',
    )

    # Approval
    approval_notes = fields.Text(
        string='Approval Notes',
        help='Optional notes to attach to the approval decision.',
    )

    # Rejection
    rejected_reason = fields.Text(
        string='Rejection Reason',
        help='Mandatory reason if rejecting the order.',
    )

    # Counter-offer (only for approve action)
    use_counter_offer = fields.Boolean(
        string='Apply Counter-Offer Discount',
        help='If enabled, the system will cap all line discounts to the approved values below.',
    )
    counter_offer_percent = fields.Float(
        string='Approved Max Discount (%)',
        help='All order lines with discount exceeding this value will be reduced to this level.',
    )
    counter_offer_amount = fields.Monetary(
        string='Approved Max Discount Amount',
        currency_field='currency_id',
        help='Record the approved maximum discount amount for reference.',
    )

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == 'reject':
            self.use_counter_offer = False

    @api.constrains('action', 'rejected_reason')
    def _check_rejection_reason(self):
        for wizard in self:
            if wizard.action == 'reject' and not wizard.rejected_reason:
                raise UserError(_('Please provide a reason for rejection.'))

    @api.constrains('use_counter_offer', 'counter_offer_percent', 'current_discount_percent')
    def _check_counter_offer(self):
        for wizard in self:
            if wizard.use_counter_offer and wizard.counter_offer_percent <= 0:
                raise UserError(_('Counter-offer discount percentage must be greater than 0.'))
            if wizard.use_counter_offer and wizard.counter_offer_percent >= wizard.current_discount_percent:
                raise UserError(_(
                    'Counter-offer discount (%(offer).1f%%) must be less than the '
                    'current requested discount (%(current).1f%%).',
                    offer=wizard.counter_offer_percent,
                    current=wizard.current_discount_percent,
                ))

    def action_confirm(self):
        """Execute the approval or rejection."""
        self.ensure_one()
        order = self.order_id

        if self.action == 'approve':
            counter_percent = self.counter_offer_percent if self.use_counter_offer else None
            counter_amount = self.counter_offer_amount if self.use_counter_offer else None
            order.action_approve(
                notes=self.approval_notes,
                counter_percent=counter_percent,
                counter_amount=counter_amount,
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Order Approved'),
                    'message': _('Sales Order %s has been approved and confirmed.', order.name),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        elif self.action == 'reject':
            order.action_reject(reason=self.rejected_reason)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Order Rejected'),
                    'message': _('Sales Order %s has been rejected.', order.name),
                    'type': 'danger',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
