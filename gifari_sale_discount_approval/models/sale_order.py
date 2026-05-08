# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approval_state = fields.Selection(
        [('none', 'No Approval Needed'), ('pending', 'Pending Approval'),
         ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='Approval Status', default='none', copy=False, tracking=True, index=True,
    )
    current_approval_level_id = fields.Many2one(
        'sale.discount.approval.level', string='Current Approval Level', copy=False, tracking=True,
    )
    submitted_by = fields.Many2one('res.users', string='Submitted By', copy=False)
    approval_log_ids = fields.One2many('sale.discount.approval.log', 'order_id', string='Approval History')

    max_line_discount = fields.Float(compute='_compute_discount_metrics', store=True, digits='Discount')
    global_discount_percent = fields.Float(compute='_compute_discount_metrics', store=True, digits='Discount')
    effective_max_discount = fields.Float(compute='_compute_discount_metrics', store=True, digits='Discount')

    approval_deadline = fields.Datetime(string='Approval Deadline', copy=False)
    is_sla_breached = fields.Boolean(compute='_compute_is_sla_breached', store=False)
    discount_locked = fields.Boolean(default=False, copy=False)
    days_pending = fields.Integer(compute='_compute_days_pending')
    is_current_user_approver = fields.Boolean(compute='_compute_is_current_user_approver')
    show_approval_banner = fields.Boolean(compute='_compute_show_approval_banner')

    @api.depends('order_line.discount', 'order_line.price_unit',
                 'order_line.product_uom_qty', 'amount_undiscounted', 'amount_untaxed')
    def _compute_discount_metrics(self):
        for order in self:
            discounts = [l.discount for l in order.order_line if not l.display_type and l.discount > 0]
            order.max_line_discount = max(discounts) if discounts else 0.0
            if order.amount_undiscounted:
                diff = order.amount_undiscounted - order.amount_untaxed
                order.global_discount_percent = (diff / order.amount_undiscounted) * 100.0 if diff > 0 else 0.0
            else:
                order.global_discount_percent = 0.0
            order.effective_max_discount = max(order.max_line_discount, order.global_discount_percent)

    def _compute_days_pending(self):
        now = fields.Datetime.now()
        for order in self:
            if order.approval_state == 'pending' and order.approval_log_ids:
                submit_log = order.approval_log_ids.filtered(
                    lambda l: l.action in ('submit', 'resubmit')
                ).sorted('create_date', reverse=True)[:1]
                order.days_pending = (now - submit_log.timestamp).days if submit_log else 0
            else:
                order.days_pending = 0

    @api.depends('approval_deadline')
    def _compute_is_sla_breached(self):
        now = fields.Datetime.now()
        for order in self:
            order.is_sla_breached = (
                order.approval_state == 'pending'
                and order.approval_deadline
                and now > order.approval_deadline
            )

    @api.depends('current_approval_level_id.approver_ids')
    @api.depends_context('uid')
    def _compute_is_current_user_approver(self):
        for order in self:
            order.is_current_user_approver = (
                order.approval_state == 'pending'
                and order.current_approval_level_id
                and self.env.user in order.current_approval_level_id.approver_ids
            )

    @api.depends('approval_state')
    def _compute_show_approval_banner(self):
        for order in self:
            order.show_approval_banner = order.approval_state in ('pending', 'approved', 'rejected')

    def _get_approval_levels(self):
        self.ensure_one()
        return self.env['sale.discount.approval.level'].search(
            [('company_id', '=', self.company_id.id), ('active', '=', True)], order='sequence, id')

    def _get_required_approval_level(self):
        self.ensure_one()
        levels = self._get_approval_levels()
        required_level = self.env['sale.discount.approval.level']
        for level in levels:
            if self.effective_max_discount >= level.min_discount:
                required_level = level
        return required_level

    def _get_first_approval_level(self):
        self.ensure_one()
        levels = self._get_approval_levels()
        return levels[:1] if levels else self.env['sale.discount.approval.level']

    def _get_next_approval_level(self):
        self.ensure_one()
        if not self.current_approval_level_id:
            return self._get_first_approval_level()
        levels = self._get_approval_levels()
        current_seq = self.current_approval_level_id.sequence
        current_id = self.current_approval_level_id.id
        for level in levels:
            if level.sequence > current_seq or (level.sequence == current_seq and level.id > current_id):
                return level
        return self.env['sale.discount.approval.level']

    def _needs_approval(self):
        self.ensure_one()
        if not self.company_id.sale_disc_approval_enabled:
            return False
        return bool(self._get_required_approval_level())

    def _lock_discount(self):
        self.ensure_one()
        self.write({'discount_locked': True})

    def _unlock_discount(self):
        self.ensure_one()
        self.write({'discount_locked': False})

    def action_draft(self):
        res = super().action_draft()
        self.filtered(lambda o: o.discount_locked)._unlock_discount()
        return res

    def _compute_deadline(self, level):
        if level.sla_hours and level.sla_hours > 0:
            return fields.Datetime.now() + timedelta(hours=level.sla_hours)
        return False

    def action_confirm(self):
        for order in self:
            if order.approval_state == 'approved':
                continue
            if order.approval_state == 'pending':
                raise UserError(_("Sales Order '%s' sedang menunggu approval.", order.name))
            if order.approval_state == 'rejected':
                raise UserError(_("Sales Order '%s' telah ditolak. Sesuaikan diskon dan submit ulang.", order.name))
            if order._needs_approval():
                order._submit_for_approval()
                return {
                    'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {
                        'title': _("Approval Required"),
                        'message': _("Order memiliki diskon %(disc).2f%% melebihi threshold. Dikirim ke %(level)s.",
                                     disc=order.effective_max_discount,
                                     level=order.current_approval_level_id.name),
                        'type': 'warning', 'sticky': True,
                        'next': {'type': 'ir.actions.act_window_close'},
                    },
                }
        return super().action_confirm()

    def _get_ip_address(self):
        try:
            if request:
                return request.httprequest.remote_addr or ''
        except RuntimeError:
            pass
        return ''

    def _submit_for_approval(self):
        self.ensure_one()
        first_level = self._get_first_approval_level()
        if not first_level:
            return
        ip_address = self._get_ip_address()
        deadline = self._compute_deadline(first_level)
        self.write({
            'approval_state': 'pending', 'current_approval_level_id': first_level.id,
            'submitted_by': self.env.user.id, 'approval_deadline': deadline,
        })
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': first_level.id, 'user_id': self.env.user.id, 'action': 'submit',
            'old_max_discount': self.effective_max_discount,
            'notes': _("Submitted. Max line: %(line).2f%%, Global: %(glob).2f%%",
                        line=self.max_line_discount, **{'glob': self.global_discount_percent}),
            'ip_address': ip_address,
        })
        self._create_approval_activities(first_level)
        if first_level.send_email_notification:
            self._send_approval_email(first_level)
        self.message_post(
            body=Markup(_(
                "🔔 <b>Discount Approval Required</b><br/>"
                "Max line discount: <b>%(line).2f%%</b><br/>"
                "Global discount: <b>%(glob).2f%%</b><br/>"
                "Assigned to: <b>%(level)s</b> (%(approvers)s)<br/>"
                "Deadline: <b>%(deadline)s</b>",
                line=self.max_line_discount, glob=self.global_discount_percent,
                level=first_level.name,
                approvers=', '.join(first_level.approver_ids.mapped('name')),
                deadline=deadline.strftime('%d/%m/%Y %H:%M') if deadline else 'N/A',
            )), subtype_xmlid='mail.mt_note')

    def _send_approval_email(self, level):
        self.ensure_one()
        template = self.env.ref(
            'gifari_sale_discount_approval.email_template_discount_approval_request',
            raise_if_not_found=False)
        if not template:
            return
        for approver in level.approver_ids:
            template.with_context(
                approver_name=approver.name, approver_email=approver.email, level_name=level.name,
            ).send_mail(self.id, force_send=True, email_values={'email_to': approver.email})

    def _send_rejection_email(self, reason):
        self.ensure_one()
        template = self.env.ref(
            'gifari_sale_discount_approval.email_template_discount_approval_rejected',
            raise_if_not_found=False)
        if not template or not self.submitted_by:
            return
        template.with_context(rejection_reason=reason).send_mail(
            self.id, force_send=True, email_values={'email_to': self.submitted_by.email})

    def _create_approval_activities(self, level):
        self.ensure_one()
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False)
        if not activity_type:
            return
        deadline_date = self.approval_deadline.date() if self.approval_deadline else fields.Date.today()
        for approver in level.approver_ids:
            self.activity_schedule(
                activity_type_id=activity_type.id, user_id=approver.id, date_deadline=deadline_date,
                summary=_("Approve discount %(disc).2f%% on %(order)s (%(level)s)",
                           disc=self.effective_max_discount, order=self.name, level=level.name),
                note=_("Sales Order <b>%(order)s</b> membutuhkan approval Anda.<br/>"
                        "Customer: %(partner)s<br/>Max Discount: %(disc).2f%%<br/>"
                        "Total: %(amount)s<br/>Deadline: %(deadline)s",
                        order=self.name, partner=self.partner_id.name,
                        disc=self.effective_max_discount, amount=self.amount_total,
                        deadline=self.approval_deadline.strftime('%d/%m/%Y %H:%M') if self.approval_deadline else 'N/A'))

    def _clear_approval_activities(self, user_id=None):
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False)
        if activity_type:
            domain = [('activity_type_id', '=', activity_type.id)]
            if user_id:
                domain.append(('user_id', '=', user_id))
            self.activity_ids.filtered_domain(domain).unlink()

    def action_approve_discount(self, notes='', counter_offer_percent=0.0):
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(_("Anda tidak memiliki otorisasi untuk approve order ini."))
        ip_address = self._get_ip_address()
        current_level = self.current_approval_level_id
        required_level = self._get_required_approval_level()
        action = 'approve'
        new_discount = self.effective_max_discount
        if counter_offer_percent and counter_offer_percent < self.effective_max_discount:
            action = 'counter_offer'
            new_discount = counter_offer_percent
            self._apply_counter_offer(counter_offer_percent)
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': current_level.id, 'user_id': self.env.user.id, 'action': action,
            'old_max_discount': self.effective_max_discount,
            'new_max_discount': new_discount if action == 'counter_offer' else 0.0,
            'notes': notes, 'ip_address': ip_address,
        })
        is_level_completed = True
        approved_user_ids = []
        if current_level.approval_mode == 'all_must':
            approvals = self.env['sale.discount.approval.log'].search([
                ('order_id', '=', self.id), ('level_id', '=', current_level.id),
                ('action', 'in', ('approve', 'counter_offer'))])
            approved_user_ids = approvals.mapped('user_id').ids
            required_user_ids = current_level.approver_ids.ids
            if not all(uid in approved_user_ids for uid in required_user_ids):
                is_level_completed = False
        if not is_level_completed:
            self._clear_approval_activities(user_id=self.env.user.id)
            remaining = current_level.approver_ids.filtered(lambda u: u.id not in approved_user_ids)
            self.message_post(body=Markup(_(
                "✅ <b>Approved by %(user)s</b> at level <b>%(level)s</b>.<br/>"
                "Menunggu: <b>%(remaining)s</b>",
                user=self.env.user.name, level=current_level.name,
                remaining=', '.join(remaining.mapped('name')))),
                subtype_xmlid='mail.mt_note')
            return True
        self._clear_approval_activities()
        next_level = self._get_next_approval_level()
        if (next_level and current_level != required_level
                and next_level.sequence <= required_level.sequence):
            deadline = self._compute_deadline(next_level)
            self.write({'current_approval_level_id': next_level.id, 'approval_deadline': deadline})
            self._create_approval_activities(next_level)
            if next_level.send_email_notification:
                self._send_approval_email(next_level)
            self.message_post(body=Markup(_(
                "✅ <b>Approved by %(user)s</b> at level <b>%(level)s</b>.<br/>"
                "Advancing to: <b>%(next)s</b>",
                user=self.env.user.name, level=current_level.name, next=next_level.name)),
                subtype_xmlid='mail.mt_note')
        else:
            self.write({'approval_state': 'approved', 'approval_deadline': False})
            self._lock_discount()
            self.message_post(body=Markup(_(
                "✅ <b>Final Approval by %(user)s</b> at <b>%(level)s</b>.<br/>"
                "Order dikonfirmasi otomatis.",
                user=self.env.user.name, level=current_level.name)),
                subtype_xmlid='mail.mt_note')
            super(SaleOrder, self).action_confirm()

    def action_reject_discount(self, reason=''):
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(_("Anda tidak memiliki otorisasi untuk reject order ini."))
        ip_address = self._get_ip_address()
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id, 'action': 'reject',
            'old_max_discount': self.effective_max_discount,
            'notes': reason, 'ip_address': ip_address,
        })
        self._clear_approval_activities()
        self.write({'approval_state': 'rejected', 'approval_deadline': False})
        self.message_post(body=Markup(_(
            "❌ <b>Rejected by %(user)s</b> at <b>%(level)s</b>.<br/>Reason: %(reason)s",
            user=self.env.user.name, level=self.current_approval_level_id.name,
            reason=reason or _('No reason provided'))),
            subtype_xmlid='mail.mt_note')
        self._send_rejection_email(reason)
        if self.submitted_by:
            activity_type = self.env.ref(
                'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
                raise_if_not_found=False)
            if activity_type:
                self.activity_schedule(
                    activity_type_id=activity_type.id, user_id=self.submitted_by.id,
                    summary=_("Discount DITOLAK pada %s", self.name),
                    note=_("Permintaan diskon pada <b>%(order)s</b> ditolak oleh %(user)s.<br/>"
                            "Alasan: %(reason)s", order=self.name, user=self.env.user.name,
                            reason=reason or _('No reason provided')))

    def action_delegate_approval(self, delegate_to_user_id, notes=''):
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(_("Anda tidak dapat mendelegasikan approval ini."))
        current_level = self.current_approval_level_id
        if not current_level.can_delegate:
            raise UserError(_("Level '%(level)s' tidak mengizinkan delegasi.", level=current_level.name))
        delegate_user = self.env['res.users'].browse(delegate_to_user_id)
        if not delegate_user.exists():
            raise UserError(_("User untuk delegasi tidak ditemukan."))
        ip_address = self._get_ip_address()
        current_level.sudo().write({'approver_ids': [(4, delegate_user.id)]})
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': current_level.id, 'user_id': self.env.user.id,
            'action': 'delegate', 'delegated_to_id': delegate_user.id,
            'notes': notes or _("Delegated to %(name)s", name=delegate_user.name),
            'ip_address': ip_address,
        })
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False)
        if activity_type:
            self.activity_schedule(
                activity_type_id=activity_type.id, user_id=delegate_user.id,
                summary=_("[DELEGATED] Approve discount %(disc).2f%% on %(order)s",
                           disc=self.effective_max_discount, order=self.name),
                note=_("Approval didelegasikan oleh <b>%(delegator)s</b> kepada Anda.<br/>"
                        "Sales Order: <b>%(order)s</b><br/>Max Discount: %(disc).2f%%",
                        delegator=self.env.user.name, order=self.name, disc=self.effective_max_discount))
        self.message_post(body=Markup(_(
            "🔄 <b>Approval didelegasikan</b> oleh %(delegator)s ke <b>%(delegate)s</b>.",
            delegator=self.env.user.name, delegate=delegate_user.name)),
            subtype_xmlid='mail.mt_note')

    def action_resubmit_approval(self):
        self.ensure_one()
        if self.approval_state != 'rejected':
            raise UserError(_("Hanya order yang ditolak yang bisa di-resubmit."))
        ip_address = self._get_ip_address()
        first_level = self._get_first_approval_level()
        if not first_level:
            raise UserError(_("Tidak ada approval level yang terkonfigurasi."))
        deadline = self._compute_deadline(first_level)
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': first_level.id, 'user_id': self.env.user.id,
            'action': 'resubmit', 'old_max_discount': self.effective_max_discount,
            'notes': _("Re-submitted for approval."), 'ip_address': ip_address,
        })
        self.write({
            'approval_state': 'pending', 'current_approval_level_id': first_level.id,
            'submitted_by': self.env.user.id, 'approval_deadline': deadline,
        })
        self._create_approval_activities(first_level)
        if first_level.send_email_notification:
            self._send_approval_email(first_level)
        self.message_post(body=Markup(_(
            "🔄 <b>Re-submitted</b> oleh %(user)s.<br/>Assigned to: <b>%(level)s</b><br/>"
            "Deadline: <b>%(deadline)s</b>",
            user=self.env.user.name, level=first_level.name,
            deadline=deadline.strftime('%d/%m/%Y %H:%M') if deadline else 'N/A')),
            subtype_xmlid='mail.mt_note')

    def action_cancel_approval(self):
        self.ensure_one()
        if self.approval_state not in ('pending', 'rejected'):
            raise UserError(_("Hanya approval pending/rejected yang bisa dibatalkan."))
        ip_address = self._get_ip_address()
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id, 'action': 'cancel',
            'notes': _("Approval request cancelled."), 'ip_address': ip_address,
        })
        self._clear_approval_activities()
        self.write({
            'approval_state': 'none', 'current_approval_level_id': False,
            'submitted_by': False, 'approval_deadline': False,
        })

    def action_open_approval_wizard(self):
        self.ensure_one()
        return {
            'name': _("Discount Approval"), 'type': 'ir.actions.act_window',
            'res_model': 'sale.discount.approval.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_level_id': self.current_approval_level_id.id,
                'default_current_discount': self.effective_max_discount,
                'default_can_delegate': self.current_approval_level_id.can_delegate,
            },
        }

    @api.model
    def _cron_check_approval_sla(self):
        now = fields.Datetime.now()
        breached_orders = self.search([
            ('approval_state', '=', 'pending'), ('approval_deadline', '<', now)])
        for order in breached_orders:
            order._action_escalate_sla_breach()

    def _action_escalate_sla_breach(self):
        self.ensure_one()
        current_level = self.current_approval_level_id
        if not current_level:
            return
        escalation_users = current_level.escalate_to_ids
        if not escalation_users:
            _logger.warning("SLA breach on %s but no escalation recipients on level %s",
                            self.name, current_level.name)
            return
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id, 'company_id': self.company_id.id,
            'level_id': current_level.id,
            'user_id': self.env.ref('base.user_root').id, 'action': 'escalate',
            'notes': _("SLA %(sla)s jam terlewat. Eskalasi ke: %(users)s",
                        sla=current_level.sla_hours,
                        users=', '.join(escalation_users.mapped('name'))),
        })
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False)
        if activity_type:
            for user in escalation_users:
                self.activity_schedule(
                    activity_type_id=activity_type.id, user_id=user.id,
                    summary=_("⚠️ SLA BREACH: Approval belum dilakukan pada %s", self.name),
                    note=_("Sales Order <b>%(order)s</b> belum diapprove oleh <b>%(level)s</b>.<br/>"
                            "Deadline: %(deadline)s<br/>Mohon tindak lanjut segera.",
                            order=self.name, level=current_level.name,
                            deadline=self.approval_deadline.strftime('%d/%m/%Y %H:%M')))
        self.message_post(body=Markup(_(
            "⚠️ <b>SLA BREACH</b>: Approval belum dilakukan pada <b>%(level)s</b>.<br/>"
            "Notifikasi eskalasi dikirim ke: %(users)s",
            level=current_level.name, users=', '.join(escalation_users.mapped('name')))),
            subtype_xmlid='mail.mt_note')

    def _apply_counter_offer(self, new_discount_percent):
        self.ensure_one()
        if self.effective_max_discount <= 0:
            return
        ratio = new_discount_percent / self.effective_max_discount
        for line in self.order_line:
            if not line.display_type and line.discount > 0:
                line.discount = round(line.discount * ratio, 2)
