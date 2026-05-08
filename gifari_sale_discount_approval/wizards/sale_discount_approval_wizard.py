# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleDiscountApprovalWizard(models.TransientModel):
    _name = 'sale.discount.approval.wizard'
    _description = 'Sale Discount Approval Wizard'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    level_id = fields.Many2one('sale.discount.approval.level', readonly=True)
    current_discount = fields.Float(readonly=True, digits='Discount')
    order_partner = fields.Char(related='order_id.partner_id.name')
    order_amount = fields.Monetary(related='order_id.amount_total')
    currency_id = fields.Many2one(related='order_id.currency_id')
    can_delegate = fields.Boolean(default=True)

    action = fields.Selection(
        [('approve', 'Approve'), ('reject', 'Reject'), ('delegate', 'Delegate')],
        string='Action', required=True, default='approve',
    )

    use_counter_offer = fields.Boolean(string='Apply Counter-Offer')
    counter_offer_percent = fields.Float(digits='Discount')
    rejected_reason = fields.Text(string='Reason')
    notes = fields.Text(string='Additional Notes')

    delegate_user_id = fields.Many2one(
        'res.users', string='Delegate To',
        domain=[('share', '=', False)],
    )
    delegate_notes = fields.Text(string='Delegation Notes')

    @api.constrains('action', 'rejected_reason')
    def _check_rejection_reason(self):
        for wizard in self:
            if wizard.action == 'reject' and not wizard.rejected_reason:
                raise ValidationError(_("Harap isi alasan penolakan."))

    @api.constrains('use_counter_offer', 'counter_offer_percent', 'current_discount')
    def _check_counter_offer(self):
        for wizard in self:
            if wizard.use_counter_offer:
                if wizard.counter_offer_percent <= 0:
                    raise ValidationError(_("Counter-offer discount harus > 0%."))
                if wizard.counter_offer_percent >= wizard.current_discount:
                    raise ValidationError(_(
                        "Counter-offer (%(offer).2f%%) harus lebih rendah dari diskon saat ini (%(current).2f%%).",
                        offer=wizard.counter_offer_percent, current=wizard.current_discount))

    @api.constrains('action', 'delegate_user_id')
    def _check_delegation(self):
        for wizard in self:
            if wizard.action == 'delegate' and not wizard.delegate_user_id:
                raise ValidationError(_("Pilih user untuk delegasi approval."))

    @api.onchange('action')
    def _onchange_action(self):
        if self.action != 'delegate':
            self.delegate_user_id = False
            self.delegate_notes = False
        if self.action != 'approve':
            self.use_counter_offer = False
            self.counter_offer_percent = 0.0

    def action_confirm_wizard(self):
        self.ensure_one()
        order = self.order_id
        if self.action == 'approve':
            counter = self.counter_offer_percent if self.use_counter_offer else 0.0
            order.action_approve_discount(notes=self.notes or '', counter_offer_percent=counter)
        elif self.action == 'reject':
            order.action_reject_discount(reason=self.rejected_reason or '')
        elif self.action == 'delegate':
            if not self.delegate_user_id:
                raise UserError(_("Pilih user untuk delegasi."))
            order.action_delegate_approval(
                delegate_to_user_id=self.delegate_user_id.id,
                notes=self.delegate_notes or '')
        return {'type': 'ir.actions.act_window_close'}
