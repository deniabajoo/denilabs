# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ── Approval State Fields ───────────────────────────────────────────
    approval_state = fields.Selection(
        selection=[
            ('pending', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval State',
        copy=False,
        tracking=True,
        index=True,
    )
    approval_user_id = fields.Many2one(
        'res.users', string='Approved/Rejected By', copy=False, readonly=True, tracking=True,
    )
    approval_date = fields.Datetime(string='Approval Date', copy=False, readonly=True)
    approval_notes = fields.Text(string='Approval Notes', copy=False)
    rejected_reason = fields.Text(string='Rejection Reason', copy=False, readonly=True)
    approved_max_discount_percent = fields.Float(
        string='Approved Max Discount (%)', copy=False, readonly=True,
    )
    approved_max_discount_amount = fields.Monetary(
        string='Approved Max Discount Amount', copy=False, readonly=True,
    )

    # ── Computed Discount Metrics ───────────────────────────────────────
    max_discount_percent = fields.Float(
        string='Max Line Discount (%)',
        compute='_compute_discount_metrics',
        store=True,
        digits=(16, 2),
    )
    total_discount_amount = fields.Monetary(
        string='Total Discount Amount',
        compute='_compute_discount_metrics',
        store=True,
    )
    needs_approval = fields.Boolean(
        string='Needs Approval',
        compute='_compute_needs_approval',
        store=True,
    )
    is_current_user_approver = fields.Boolean(
        compute='_compute_is_current_user_approver',
    )

    # ── COMPUTE METHODS ─────────────────────────────────────────────────

    @api.depends(
        'order_line.discount', 'order_line.discount_amount',
        'order_line.price_unit', 'order_line.product_qty', 'order_line.display_type',
    )
    def _compute_discount_metrics(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            if lines:
                order.max_discount_percent = max(lines.mapped('discount') or [0.0])
                # Use stored discount_amount (which may be manually overridden)
                order.total_discount_amount = sum(lines.mapped('discount_amount') or [0.0])
            else:
                order.max_discount_percent = 0.0
                order.total_discount_amount = 0.0

    @api.depends(
        'max_discount_percent', 'total_discount_amount',
        'company_id.purchase_disc_approval_enabled',
        'company_id.purchase_disc_approval_type',
        'company_id.purchase_disc_approval_percent',
        'company_id.purchase_disc_approval_amount',
    )
    def _compute_needs_approval(self):
        for order in self:
            company = order.company_id
            if not company.purchase_disc_approval_enabled:
                order.needs_approval = False
                continue

            approval_type = company.purchase_disc_approval_type
            triggered = False

            if approval_type in ('percent', 'both'):
                if order.max_discount_percent > company.purchase_disc_approval_percent:
                    triggered = True

            if approval_type in ('amount', 'both'):
                if order.total_discount_amount > company.purchase_disc_approval_amount:
                    triggered = True

            order.needs_approval = triggered

    @api.depends('company_id.purchase_approval_user_ids')
    def _compute_is_current_user_approver(self):
        for order in self:
            order.is_current_user_approver = self.env.user in order._get_approval_users()

    # ── HELPER METHODS ──────────────────────────────────────────────────

    def _get_approval_users(self):
        self.ensure_one()
        approvers = self.company_id.purchase_approval_user_ids
        if not approvers:
            approvers = self.env.ref(
                'purchase.group_purchase_manager', raise_if_not_found=False
            )
            if approvers:
                approvers = approvers.users
        return approvers

    def _check_is_approver(self):
        self.ensure_one()
        if self.env.user not in self._get_approval_users() and not self.env.su:
            raise AccessError(_(
                'You are not authorized to approve or reject this Purchase Order.\n'
                'Please contact your Purchasing Manager.'
            ))

    # ── OVERRIDE button_confirm ─────────────────────────────────────────

    def button_confirm(self):
        """Intercept PO confirmation to enforce discount approval workflow."""
        for order in self:
            if order.needs_approval and order.approval_state != 'approved':
                order._request_discount_approval()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Approval Required'),
                        'message': _(
                            'Purchase Order %(name)s submitted for approval. '
                            'Max discount: %(pct).1f%% / %(amount)s.',
                            name=order.name,
                            pct=order.max_discount_percent,
                            amount=order.currency_id.symbol + '{:,.0f}'.format(order.total_discount_amount),
                        ),
                        'type': 'warning',
                        'sticky': True,
                    },
                }
        return super().button_confirm()

    # ── APPROVAL WORKFLOW METHODS ───────────────────────────────────────

    def _request_discount_approval(self):
        self.ensure_one()
        self.write({
            'approval_state': 'pending',
            'approval_user_id': False,
            'approval_date': False,
            'rejected_reason': False,
        })
        approvers = self._get_approval_users()

        for approver in approvers:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=_('PO Discount Approval Required — %s', self.name),
                note=_(
                    'Purchase Order <b>%(name)s</b> from <b>%(vendor)s</b> requires approval.<br/>'
                    'Max Discount: <b>%(pct).1f%%</b> | Total Discount: <b>%(amount)s</b>',
                    name=self.name,
                    vendor=self.partner_id.name,
                    pct=self.max_discount_percent,
                    amount=self.currency_id.symbol + '{:,.0f}'.format(self.total_discount_amount),
                ),
                user_id=approver.id,
            )

        self.message_post(
            body=_(
                '<b>Discount Approval Requested</b><br/>'
                'Max Discount: <b>%(pct).1f%%</b> | Amount: <b>%(amount)s</b><br/>'
                'Submitted by: %(user)s',
                pct=self.max_discount_percent,
                amount=self.currency_id.symbol + '{:,.0f}'.format(self.total_discount_amount),
                user=self.env.user.name,
            ),
            subtype_xmlid='mail.mt_note',
        )

        template = self.env.ref(
            'gifari_purchase_discount_approval.mail_template_purchase_approval_request',
            raise_if_not_found=False,
        )
        if template:
            for approver in approvers:
                template.with_context(
                    approver_name=approver.name,
                    lang=approver.lang or self.env.lang,
                ).send_mail(
                    self.id,
                    email_values={'email_to': approver.email, 'email_cc': ''},
                    force_send=True,
                )

    def action_open_approve_wizard(self):
        self._check_is_approver()
        if self.approval_state != 'pending':
            raise UserError(_('This Purchase Order is not pending approval.'))
        return {
            'name': _('Approve Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.discount.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_action': 'approve',
                'default_current_discount_percent': self.max_discount_percent,
                'default_current_discount_amount': self.total_discount_amount,
            },
        }

    def action_open_reject_wizard(self):
        self._check_is_approver()
        if self.approval_state != 'pending':
            raise UserError(_('This Purchase Order is not pending approval.'))
        return {
            'name': _('Reject Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.discount.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_action': 'reject',
                'default_current_discount_percent': self.max_discount_percent,
                'default_current_discount_amount': self.total_discount_amount,
            },
        }

    def action_approve(self, notes=None, counter_percent=None, counter_amount=None):
        self.ensure_one()
        self._check_is_approver()

        vals = {
            'approval_state': 'approved',
            'approval_user_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
            'approval_notes': notes,
        }

        if counter_percent is not None and counter_percent > 0:
            vals['approved_max_discount_percent'] = counter_percent
            for line in self.order_line.filtered(
                lambda l: not l.display_type and l.discount > counter_percent
            ):
                line.discount = counter_percent

        if counter_amount is not None and counter_amount > 0:
            vals['approved_max_discount_amount'] = counter_amount

        self.write(vals)

        self.activity_feedback(
            act_type_xmlids=['mail.mail_activity_data_todo'],
            feedback=_('Approved by %s', self.env.user.name),
        )

        self.message_post(
            body=_(
                '<b>✅ Purchase Order Approved</b><br/>'
                'Approved by: <b>%(user)s</b><br/>'
                '%(counter)s%(notes)s',
                user=self.env.user.name,
                counter=(
                    _('Counter-offer: Max Discount capped to <b>%(pct).1f%%</b><br/>', pct=counter_percent)
                    if counter_percent else ''
                ),
                notes=(_('Notes: %(n)s', n=notes) if notes else ''),
            ),
            subtype_xmlid='mail.mt_note',
        )

        template = self.env.ref(
            'gifari_purchase_discount_approval.mail_template_purchase_approval_result',
            raise_if_not_found=False,
        )
        if template and self.user_id and self.user_id.email:
            template.with_context(
                approval_result='approved',
                approver_name=self.env.user.name,
                lang=self.user_id.lang or self.env.lang,
            ).send_mail(self.id, force_send=True)

        return super(PurchaseOrder, self).button_confirm()

    def action_reject(self, reason=None):
        self.ensure_one()
        self._check_is_approver()

        self.write({
            'approval_state': 'rejected',
            'approval_user_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
            'rejected_reason': reason,
        })

        self.activity_feedback(
            act_type_xmlids=['mail.mail_activity_data_todo'],
            feedback=_('Rejected by %s: %s', self.env.user.name, reason or ''),
        )

        self.message_post(
            body=_(
                '<b>❌ Purchase Order Rejected</b><br/>'
                'Rejected by: <b>%(user)s</b><br/>'
                'Reason: %(reason)s',
                user=self.env.user.name,
                reason=reason or _('(No reason provided)'),
            ),
            subtype_xmlid='mail.mt_note',
        )

        template = self.env.ref(
            'gifari_purchase_discount_approval.mail_template_purchase_approval_result',
            raise_if_not_found=False,
        )
        if template and self.user_id and self.user_id.email:
            template.with_context(
                approval_result='rejected',
                approver_name=self.env.user.name,
                rejection_reason=reason or '',
                lang=self.user_id.lang or self.env.lang,
            ).send_mail(self.id, force_send=True)

    def action_reset_approval(self):
        self.ensure_one()
        self.write({
            'approval_state': False,
            'approval_user_id': False,
            'approval_date': False,
            'rejected_reason': False,
            'approved_max_discount_percent': 0.0,
            'approved_max_discount_amount': 0.0,
        })
        self.message_post(
            body=_('<b>Approval Reset</b> — PO returned to draft for revision.'),
            subtype_xmlid='mail.mt_note',
        )
