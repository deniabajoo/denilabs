# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ── Approval State (separate from native `state`) ────

    approval_state = fields.Selection(
        [
            ('none', 'No Approval Needed'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        default='none',
        copy=False,
        tracking=True,
        index=True,
    )
    current_approval_level_id = fields.Many2one(
        'purchase.approval.level',
        string='Current Approval Level',
        copy=False,
        tracking=True,
    )
    submitted_by = fields.Many2one(
        'res.users',
        string='Submitted By',
        copy=False,
    )

    # ── Approval Log ─────────────────────────────────────

    approval_log_ids = fields.One2many(
        'purchase.approval.log',
        'order_id',
        string='Approval History',
    )

    # ── Aging ────────────────────────────────────────────

    days_pending = fields.Integer(
        string='Days Pending',
        compute='_compute_days_pending',
    )

    # ── Helper Booleans ──────────────────────────────────

    is_current_user_approver = fields.Boolean(
        compute='_compute_is_current_user_approver',
    )
    show_approval_banner = fields.Boolean(
        compute='_compute_show_approval_banner',
    )
    requires_multi_approval = fields.Boolean(
        string='Requires Multi-Level Approval',
        compute='_compute_requires_multi_approval',
    )

    # ── Track original amount for re-approval (Q10=A) ────

    approved_amount_untaxed = fields.Monetary(
        string='Approved Amount',
        copy=False,
        currency_field='currency_id',
        help="The untaxed amount at the time of last approval.",
    )

    # ══════════════════════════════════════════════════════
    # COMPUTE METHODS
    # ══════════════════════════════════════════════════════

    def _compute_days_pending(self):
        now = fields.Datetime.now()
        for order in self:
            if order.approval_state == 'pending' and order.approval_log_ids:
                submit_log = order.approval_log_ids.filtered(
                    lambda l: l.action in ('submit', 'resubmit', 'reset')
                ).sorted('create_date', reverse=True)[:1]
                if submit_log:
                    delta = now - submit_log.timestamp
                    order.days_pending = delta.days
                else:
                    order.days_pending = 0
            else:
                order.days_pending = 0

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
            order.show_approval_banner = order.approval_state in (
                'pending', 'approved', 'rejected'
            )

    def _compute_requires_multi_approval(self):
        for order in self:
            if not order.company_id.purchase_approval_enabled:
                order.requires_multi_approval = False
                continue
            required_level = order._get_required_approval_level()
            order.requires_multi_approval = bool(required_level)

    # ══════════════════════════════════════════════════════
    # APPROVAL LEVEL RESOLUTION
    # ══════════════════════════════════════════════════════

    def _get_approval_levels(self):
        """Return all active approval levels for the company, sorted."""
        self.ensure_one()
        return self.env['purchase.approval.level'].search(
            [
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
            ],
            order='sequence, id',
        )

    def _get_required_approval_level(self):
        """Determine which approval level is needed based on amount_untaxed (Q7=A)."""
        self.ensure_one()
        levels = self._get_approval_levels()
        if not levels:
            return self.env['purchase.approval.level']

        required_level = self.env['purchase.approval.level']
        for level in levels:
            if self.amount_untaxed >= level.min_amount:
                required_level = level
        return required_level

    def _get_first_approval_level(self):
        """Return the first (lowest sequence) approval level."""
        self.ensure_one()
        levels = self._get_approval_levels()
        return levels[:1] if levels else self.env['purchase.approval.level']

    def _get_next_approval_level(self):
        """Return the next level after the current one."""
        self.ensure_one()
        if not self.current_approval_level_id:
            return self._get_first_approval_level()

        levels = self._get_approval_levels()
        current_seq = self.current_approval_level_id.sequence
        current_id = self.current_approval_level_id.id
        for level in levels:
            if (level.sequence > current_seq or
                    (level.sequence == current_seq and level.id > current_id)):
                return level
        return self.env['purchase.approval.level']

    def _needs_multi_approval(self):
        """Check if this PO needs multi-level approval."""
        self.ensure_one()
        company = self.company_id
        if not company.purchase_approval_enabled:
            return False

        # Q9=A: Bypass for PO from Purchase Agreements
        if self.origin and 'purchase.requisition' in str(
            self.env['purchase.order.line'].search([
                ('order_id', '=', self.id)
            ]).mapped('requisition_line_id')
        ):
            _logger.info(
                "PO %s originates from Purchase Agreement — bypassing "
                "multi-level approval.", self.name
            )
            return False

        required_level = self._get_required_approval_level()
        return bool(required_level)

    # ══════════════════════════════════════════════════════
    # OVERRIDE: _approval_allowed & button_confirm
    # ══════════════════════════════════════════════════════

    def _approval_allowed(self):
        """Override standard approval check to integrate multi-level.

        Standard logic (line 1249-1258):
          - one_step: always True
          - two_step + amount < threshold: True
          - two_step + amount >= threshold: only purchase_manager

        Our extension: if multi-level is enabled AND a level matches,
        we take over. Otherwise fall back to standard.
        """
        self.ensure_one()

        # If our custom approval already approved it, allow
        if self.approval_state == 'approved':
            return True

        # If multi-level is enabled and needed, block standard approval
        if self._needs_multi_approval():
            return False

        # Fallback to standard Odoo logic
        return super()._approval_allowed()

    def button_confirm(self):
        """Override to intercept with multi-level approval."""
        for order in self:
            # If already approved via our workflow, proceed
            if order.approval_state == 'approved':
                continue

            if order.approval_state == 'pending':
                raise UserError(
                    _("Purchase Order '%s' is pending approval. "
                      "Please wait for approval before confirming.",
                      order.name)
                )

            if order.approval_state == 'rejected':
                raise UserError(
                    _("Purchase Order '%s' has been rejected. "
                      "Please adjust and re-submit.",
                      order.name)
                )

            # Check multi-level approval
            if order._needs_multi_approval():
                order._submit_for_approval()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Approval Required"),
                        'message': _(
                            "This order amount (%(amount)s) exceeds the "
                            "threshold. It has been submitted for approval "
                            "to %(level)s.",
                            amount=order.amount_untaxed,
                            level=order.current_approval_level_id.name,
                        ),
                        'type': 'warning',
                        'sticky': True,
                        'next': {'type': 'ir.actions.act_window_close'},
                    },
                }

        # If we reach here, proceed with standard flow
        return super().button_confirm()

    # ══════════════════════════════════════════════════════
    # RE-APPROVAL ON UNLOCK+EDIT (Q10=A)
    # ══════════════════════════════════════════════════════

    def write(self, vals):
        """Track amount changes on approved POs for re-approval."""
        res = super().write(vals)
        for order in self:
            if (order.approval_state == 'approved'
                    and order.approved_amount_untaxed
                    and order.state in ('draft', 'sent', 'to approve')):
                # Check if amount changed significantly
                if abs(order.amount_untaxed - order.approved_amount_untaxed) > 0.01:
                    order._trigger_re_approval()
        return res

    def _trigger_re_approval(self):
        """Reset approval state when approved PO amount changes."""
        self.ensure_one()
        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id if self.current_approval_level_id else False,
            'user_id': self.env.user.id,
            'action': 'reset',
            'order_amount': self.amount_untaxed,
            'notes': _(
                "Amount changed from %(old)s to %(new)s. Re-approval required.",
                old=self.approved_amount_untaxed,
                new=self.amount_untaxed,
            ),
            'ip_address': ip_address,
        })

        self.approval_state = 'none'
        self.current_approval_level_id = False
        self.approved_amount_untaxed = 0.0

        self.message_post(
            body=_(
                "⚠️ <b>Re-approval Required</b><br/>"
                "Order amount was changed after approval. "
                "Please re-confirm to trigger approval workflow."
            ),
            subtype_xmlid='mail.mt_note',
        )

    # ══════════════════════════════════════════════════════
    # APPROVAL WORKFLOW ACTIONS
    # ══════════════════════════════════════════════════════

    def _submit_for_approval(self):
        """Submit the PO for approval at the first required level."""
        self.ensure_one()
        first_level = self._get_first_approval_level()
        if not first_level:
            return

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.write({
            'approval_state': 'pending',
            'current_approval_level_id': first_level.id,
            'submitted_by': self.env.user.id,
        })

        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': first_level.id,
            'user_id': self.env.user.id,
            'action': 'submit',
            'order_amount': self.amount_untaxed,
            'notes': _(
                "Submitted for approval. Amount (untaxed): %(amount)s",
                amount=self.amount_untaxed,
            ),
            'ip_address': ip_address,
        })

        self._create_approval_activities(first_level)

        self.message_post(
            body=Markup(_(
                "🔔 <b>Amount Approval Required</b><br/>"
                "Amount (untaxed): <b>%(amount)s</b><br/>"
                "Assigned to: <b>%(level)s</b> (%(approvers)s)",
                amount=self.amount_untaxed,
                level=first_level.name,
                approvers=', '.join(first_level.approver_ids.mapped('name')),
            )),
            subtype_xmlid='mail.mt_note',
        )

    def _create_approval_activities(self, level):
        """Create mail.activity for each approver."""
        self.ensure_one()
        activity_type = self.env.ref(
            'gifari_purchase_approval.mail_activity_type_purchase_approval',
            raise_if_not_found=False,
        )
        if not activity_type:
            return

        for approver in level.approver_ids:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=approver.id,
                summary=_(
                    "Approve PO %(order)s — %(amount)s (%(level)s)",
                    order=self.name,
                    amount=self.amount_untaxed,
                    level=level.name,
                ),
                note=_(
                    "Purchase Order <b>%(order)s</b> requires your approval.<br/>"
                    "Vendor: %(partner)s<br/>"
                    "Amount (untaxed): %(amount)s",
                    order=self.name,
                    partner=self.partner_id.name,
                    amount=self.amount_untaxed,
                ),
            )

    def _clear_approval_activities(self, user_id=None):
        """Remove pending approval activities for this order.
        If user_id is provided, only remove activity for that user.
        """
        activity_type = self.env.ref(
            'gifari_purchase_approval.mail_activity_type_purchase_approval',
            raise_if_not_found=False
        )
        if activity_type:
            domain = [('activity_type_id', '=', activity_type.id)]
            if user_id:
                domain.append(('user_id', '=', user_id))
            self.activity_ids.filtered_domain(domain).unlink()

    def action_approve_purchase(self, notes=''):
        """Called by the wizard to approve the current level."""
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(
                _("You are not authorized to approve this order at the current level.")
            )

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        current_level = self.current_approval_level_id
        required_level = self._get_required_approval_level()

        # Log approval
        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': current_level.id,
            'user_id': self.env.user.id,
            'action': 'approve',
            'order_amount': self.amount_untaxed,
            'notes': notes,
            'ip_address': ip_address,
        })

        # Mode Check: All Must Approve?
        is_level_completed = True
        if current_level.approval_mode == 'all_must':
            # Count distinct approvers who have already signed off
            approvals = self.env['purchase.approval.log'].search([
                ('order_id', '=', self.id),
                ('level_id', '=', current_level.id),
                ('action', '=', 'approve'),
            ])
            approved_user_ids = approvals.mapped('user_id').ids
            required_user_ids = current_level.approver_ids.ids
            if not all(uid in approved_user_ids for uid in required_user_ids):
                is_level_completed = False

        if not is_level_completed:
            # Level not yet completed, just clear current user's activity
            self._clear_approval_activities(user_id=self.env.user.id)
            remaining_users = current_level.approver_ids.filtered(lambda u: u.id not in approved_user_ids)
            self.message_post(
                body=Markup(_(
                    "✅ <b>Approved by %(user)s</b> at level <b>%(level)s</b>.<br/>"
                    "Status: <b>Waiting for others</b> (%(remaining)s)",
                    user=self.env.user.name,
                    level=current_level.name,
                    remaining=', '.join(remaining_users.mapped('name')),
                )),
                subtype_xmlid='mail.mt_note',
            )
            return True

        # If level is completed, proceed to next or final
        self._clear_approval_activities() # Clear all for this level
        next_level = self._get_next_approval_level()
        if (next_level and
                current_level != required_level and
                next_level.sequence <= required_level.sequence):
            self.write({
                'current_approval_level_id': next_level.id,
            })
            self._create_approval_activities(next_level)
            self.message_post(
                body=Markup(_(
                    "✅ <b>Approved by %(user)s</b> at level "
                    "<b>%(level)s</b>.<br/>"
                    "Advancing to next level: <b>%(next)s</b>",
                    user=self.env.user.name,
                    level=current_level.name,
                    next=next_level.name,
                )),
                subtype_xmlid='mail.mt_note',
            )
        else:
            # Final approval
            self.write({
                'approval_state': 'approved',
                'approved_amount_untaxed': self.amount_untaxed,
            })
            self.message_post(
                body=Markup(_(
                    "✅ <b>Final Approval by %(user)s</b> at level "
                    "<b>%(level)s</b>.<br/>"
                    "Order is approved and will be confirmed.",
                    user=self.env.user.name,
                    level=current_level.name,
                )),
                subtype_xmlid='mail.mt_note',
            )
            # Auto-confirm: call standard flow
            super(PurchaseOrder, self).button_confirm()

    def action_reject_purchase(self, reason=''):
        """Called by the wizard to reject."""
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(
                _("You are not authorized to reject this order.")
            )

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id,
            'action': 'reject',
            'order_amount': self.amount_untaxed,
            'notes': reason,
            'ip_address': ip_address,
        })

        self._clear_approval_activities()

        self.write({
            'approval_state': 'rejected',
        })

        self.message_post(
            body=Markup(_(
                "❌ <b>Rejected by %(user)s</b> at level <b>%(level)s</b>.<br/>"
                "Reason: %(reason)s",
                user=self.env.user.name,
                level=self.current_approval_level_id.name,
                reason=reason or _('No reason provided'),
            )),
            subtype_xmlid='mail.mt_note',
        )

        # Notify submitter
        if self.submitted_by:
            activity_type = self.env.ref(
                'gifari_purchase_approval.mail_activity_type_purchase_approval',
                raise_if_not_found=False,
            )
            if activity_type:
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=self.submitted_by.id,
                    summary=_("PO REJECTED — %s", self.name),
                    note=_(
                        "Your PO <b>%(order)s</b> was rejected by %(user)s.<br/>"
                        "Reason: %(reason)s",
                        order=self.name,
                        user=self.env.user.name,
                        reason=reason or _('No reason provided'),
                    ),
                )

    def action_resubmit_approval(self):
        """Re-submit after rejection (Q2=A)."""
        self.ensure_one()
        if self.approval_state != 'rejected':
            raise UserError(_("Only rejected orders can be re-submitted."))

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        first_level = self._get_first_approval_level()
        if not first_level:
            raise UserError(_("No approval levels configured."))

        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': first_level.id,
            'user_id': self.env.user.id,
            'action': 'resubmit',
            'order_amount': self.amount_untaxed,
            'notes': _("Re-submitted for approval."),
            'ip_address': ip_address,
        })

        self.write({
            'approval_state': 'pending',
            'current_approval_level_id': first_level.id,
            'submitted_by': self.env.user.id,
        })

        self._create_approval_activities(first_level)

        self.message_post(
            body=Markup(_(
                "🔄 <b>Re-submitted for approval</b> by %(user)s.<br/>"
                "Assigned to: <b>%(level)s</b>",
                user=self.env.user.name,
                level=first_level.name,
            )),
            subtype_xmlid='mail.mt_note',
        )

    def action_cancel_approval(self):
        """Cancel a pending approval."""
        self.ensure_one()
        if self.approval_state not in ('pending', 'rejected'):
            raise UserError(
                _("Can only cancel pending or rejected approval requests.")
            )

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.env['purchase.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id,
            'action': 'cancel',
            'order_amount': self.amount_untaxed,
            'notes': _("Approval request cancelled."),
            'ip_address': ip_address,
        })

        self._clear_approval_activities()

        self.write({
            'approval_state': 'none',
            'current_approval_level_id': False,
            'submitted_by': False,
        })

    def action_open_approval_wizard(self):
        """Open the approval wizard."""
        self.ensure_one()
        return {
            'name': _("Purchase Approval"),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_level_id': self.current_approval_level_id.id,
            },
        }

    # ══════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════

