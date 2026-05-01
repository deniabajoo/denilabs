# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseDiscountApprovalWizard(models.TransientModel):
    _name = 'purchase.discount.approval.wizard'
    _description = 'Purchase Discount Approval Wizard'

    order_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    action = fields.Selection([('approve', 'Approve'), ('reject', 'Reject')],
                              required=True, default='approve')
    current_discount_percent = fields.Float(string='Current Max Discount (%)', readonly=True)
    current_discount_amount = fields.Monetary(string='Current Total Discount', readonly=True,
                                               currency_field='currency_id')
    currency_id = fields.Many2one(related='order_id.currency_id')
    partner_id = fields.Many2one(related='order_id.partner_id', string='Vendor')
    amount_total = fields.Monetary(related='order_id.amount_total', currency_field='currency_id')
    approval_notes = fields.Text(string='Approval Notes')
    rejected_reason = fields.Text(string='Rejection Reason')
    use_counter_offer = fields.Boolean(string='Apply Counter-Offer Discount')
    counter_offer_percent = fields.Float(string='Approved Max Discount (%)')
    counter_offer_amount = fields.Monetary(string='Approved Max Discount Amount',
                                            currency_field='currency_id')

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
            if (wizard.use_counter_offer
                    and wizard.counter_offer_percent >= wizard.current_discount_percent):
                raise UserError(_(
                    'Counter-offer (%(offer).1f%%) must be less than current discount (%(curr).1f%%).',
                    offer=wizard.counter_offer_percent,
                    curr=wizard.current_discount_percent,
                ))

    def action_confirm(self):
        self.ensure_one()
        order = self.order_id
        if self.action == 'approve':
            order.action_approve(
                notes=self.approval_notes,
                counter_percent=self.counter_offer_percent if self.use_counter_offer else None,
                counter_amount=self.counter_offer_amount if self.use_counter_offer else None,
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ PO Approved'),
                    'message': _('Purchase Order %s has been approved and confirmed.', order.name),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        else:
            order.action_reject(reason=self.rejected_reason)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ PO Rejected'),
                    'message': _('Purchase Order %s has been rejected.', order.name),
                    'type': 'danger',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
