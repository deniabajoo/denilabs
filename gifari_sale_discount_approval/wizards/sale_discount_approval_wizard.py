# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleDiscountApprovalWizard(models.TransientModel):
    _name = 'sale.discount.approval.wizard'
    _description = 'Sale Discount Approval Wizard'

    # ── Context Fields ───────────────────────────────────

    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
    )
    level_id = fields.Many2one(
        'sale.discount.approval.level',
        string='Approval Level',
        readonly=True,
    )
    current_discount = fields.Float(
        string='Current Max Discount (%)',
        readonly=True,
        digits='Discount',
    )
    order_partner = fields.Char(
        related='order_id.partner_id.name',
        string='Customer',
    )
    order_amount = fields.Monetary(
        related='order_id.amount_total',
        string='Total Amount',
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

    # Counter-offer (Q3=A)
    use_counter_offer = fields.Boolean(
        string='Apply Counter-Offer',
        help="If checked, you can specify a lower discount percentage.",
    )
    counter_offer_percent = fields.Float(
        string='Approved Max Discount (%)',
        digits='Discount',
        help="Set the maximum discount you approve. "
             "All line discounts will be proportionally adjusted.",
    )

    # Rejection reason
    rejected_reason = fields.Text(
        string='Reason',
        help="Required when rejecting.",
    )

    # Notes
    notes = fields.Text(
        string='Additional Notes',
    )

    # ── Validation ───────────────────────────────────────

    @api.constrains('action', 'rejected_reason')
    def _check_rejection_reason(self):
        for wizard in self:
            if wizard.action == 'reject' and not wizard.rejected_reason:
                raise ValidationError(
                    _("Please provide a reason for rejection.")
                )

    @api.constrains('use_counter_offer', 'counter_offer_percent', 'current_discount')
    def _check_counter_offer(self):
        for wizard in self:
            if wizard.use_counter_offer:
                if wizard.counter_offer_percent <= 0:
                    raise ValidationError(
                        _("Counter-offer discount must be greater than 0%%.")
                    )
                if wizard.counter_offer_percent >= wizard.current_discount:
                    raise ValidationError(
                        _("Counter-offer discount (%(offer).2f%%) must be "
                          "lower than the current discount (%(current).2f%%).",
                          offer=wizard.counter_offer_percent,
                          current=wizard.current_discount)
                    )

    # ── Actions ──────────────────────────────────────────

    def action_confirm_wizard(self):
        """Execute the approve or reject action."""
        self.ensure_one()
        order = self.order_id

        if self.action == 'approve':
            counter = (
                self.counter_offer_percent
                if self.use_counter_offer else 0.0
            )
            order.action_approve_discount(
                notes=self.notes or '',
                counter_offer_percent=counter,
            )
        elif self.action == 'reject':
            order.action_reject_discount(
                reason=self.rejected_reason or '',
            )

        return {'type': 'ir.actions.act_window_close'}
