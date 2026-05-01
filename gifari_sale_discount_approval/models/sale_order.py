# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
        'sale.discount.approval.level',
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
        'sale.discount.approval.log',
        'order_id',
        string='Approval History',
    )

    # ── Computed Discount Metrics ────────────────────────

    max_line_discount = fields.Float(
        string='Max Line Discount (%)',
        compute='_compute_discount_metrics',
        store=True,
        digits='Discount',
    )
    global_discount_percent = fields.Float(
        string='Global Discount (%)',
        compute='_compute_discount_metrics',
        store=True,
        digits='Discount',
    )
    effective_max_discount = fields.Float(
        string='Effective Max Discount (%)',
        compute='_compute_discount_metrics',
        store=True,
        digits='Discount',
        help="The higher of max line discount and global discount (OR logic).",
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

    # ══════════════════════════════════════════════════════
    # COMPUTE METHODS
    # ══════════════════════════════════════════════════════

    @api.depends(
        'order_line.discount',
        'order_line.price_unit',
        'order_line.product_uom_qty',
        'amount_undiscounted',
        'amount_untaxed',
    )
    def _compute_discount_metrics(self):
        for order in self:
            # Per-line max discount
            discounts = [
                line.discount
                for line in order.order_line
                if not line.display_type and line.discount > 0
            ]
            order.max_line_discount = max(discounts) if discounts else 0.0

            # Global discount = (undiscounted - untaxed) / undiscounted * 100
            if order.amount_undiscounted:
                diff = order.amount_undiscounted - order.amount_untaxed
                order.global_discount_percent = (
                    (diff / order.amount_undiscounted) * 100.0
                    if diff > 0 else 0.0
                )
            else:
                order.global_discount_percent = 0.0

            # Effective = max of both (OR logic per Q1=C)
            order.effective_max_discount = max(
                order.max_line_discount,
                order.global_discount_percent,
            )

    def _compute_days_pending(self):
        now = fields.Datetime.now()
        for order in self:
            if order.approval_state == 'pending' and order.approval_log_ids:
                submit_log = order.approval_log_ids.filtered(
                    lambda l: l.action in ('submit', 'resubmit')
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

    # ══════════════════════════════════════════════════════
    # APPROVAL LEVEL RESOLUTION
    # ══════════════════════════════════════════════════════

    def _get_approval_levels(self):
        """Return all active approval levels for the company, sorted."""
        self.ensure_one()
        return self.env['sale.discount.approval.level'].search(
            [
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
            ],
            order='sequence, id',
        )

    def _get_required_approval_level(self):
        """Determine which approval level is needed based on effective_max_discount.

        Returns the HIGHEST level that the discount falls into.
        Sequential: we need to go through ALL levels up to and including
        the one whose range contains our discount.
        """
        self.ensure_one()
        levels = self._get_approval_levels()
        if not levels:
            return self.env['sale.discount.approval.level']

        required_level = self.env['sale.discount.approval.level']
        for level in levels:
            if self.effective_max_discount >= level.min_discount:
                required_level = level
        return required_level

    def _get_first_approval_level(self):
        """Return the first (lowest sequence) approval level."""
        self.ensure_one()
        levels = self._get_approval_levels()
        return levels[:1] if levels else self.env['sale.discount.approval.level']

    def _get_next_approval_level(self):
        """Return the next level after the current one, or empty if final."""
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
        return self.env['sale.discount.approval.level']

    def _needs_approval(self):
        """Check if this SO needs discount approval."""
        self.ensure_one()
        company = self.company_id
        if not company.sale_disc_approval_enabled:
            return False

        required_level = self._get_required_approval_level()
        return bool(required_level)

    # ══════════════════════════════════════════════════════
    # ACTION CONFIRM OVERRIDE
    # ══════════════════════════════════════════════════════

    def action_confirm(self):
        """Override to intercept confirmation when discount exceeds threshold."""
        for order in self:
            # Skip if already approved or no approval needed
            if order.approval_state == 'approved':
                continue
            if order.approval_state == 'pending':
                raise UserError(
                    _("Sales Order '%s' is pending approval. "
                      "Please wait for approval before confirming.",
                      order.name)
                )
            if order.approval_state == 'rejected':
                raise UserError(
                    _("Sales Order '%s' has been rejected. "
                      "Please adjust the discount and re-submit.",
                      order.name)
                )
            # Check if approval is needed
            if order._needs_approval():
                order._submit_for_approval()
                # Return action to show the user a notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Approval Required"),
                        'message': _(
                            "This order has a discount of %(disc).2f%% which "
                            "exceeds the threshold. It has been submitted for "
                            "approval to %(level)s.",
                            disc=order.effective_max_discount,
                            level=order.current_approval_level_id.name,
                        ),
                        'type': 'warning',
                        'sticky': True,
                        'next': {'type': 'ir.actions.act_window_close'},
                    },
                }

        # If we reach here, all orders are either approved or don't need approval
        return super().action_confirm()

    # ══════════════════════════════════════════════════════
    # APPROVAL WORKFLOW ACTIONS
    # ══════════════════════════════════════════════════════

    def _submit_for_approval(self):
        """Submit the SO for approval at the first required level."""
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

        # Create audit log
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': first_level.id,
            'user_id': self.env.user.id,
            'action': 'submit',
            'old_max_discount': self.effective_max_discount,
            'notes': _(
                "Submitted for approval. Max line discount: %(line).2f%%, "
                "Global discount: %(global).2f%%",
                line=self.max_line_discount,
                **{'global': self.global_discount_percent},
            ),
            'ip_address': ip_address,
        })

        # Create activities for approvers
        self._create_approval_activities(first_level)

        # Log in chatter
        self.message_post(
            body=Markup(_(
                "🔔 <b>Discount Approval Required</b><br/>"
                "Max line discount: <b>%(line).2f%%</b><br/>"
                "Global discount: <b>%(glob).2f%%</b><br/>"
                "Assigned to: <b>%(level)s</b> (%(approvers)s)",
                line=self.max_line_discount,
                glob=self.global_discount_percent,
                level=first_level.name,
                approvers=', '.join(first_level.approver_ids.mapped('name')),
            )),
            subtype_xmlid='mail.mt_note',
        )

    def _create_approval_activities(self, level):
        """Create mail.activity for each approver in the level."""
        self.ensure_one()
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False,
        )
        if not activity_type:
            return

        for approver in level.approver_ids:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=approver.id,
                summary=_(
                    "Approve discount %(disc).2f%% on %(order)s (%(level)s)",
                    disc=self.effective_max_discount,
                    order=self.name,
                    level=level.name,
                ),
                note=_(
                    "Sales Order <b>%(order)s</b> requires your approval.<br/>"
                    "Customer: %(partner)s<br/>"
                    "Max Discount: %(disc).2f%%<br/>"
                    "Amount: %(amount)s",
                    order=self.name,
                    partner=self.partner_id.name,
                    disc=self.effective_max_discount,
                    amount=self.amount_total,
                ),
            )

    def _clear_approval_activities(self, user_id=None):
        """Remove pending approval activities for this order.
        If user_id is provided, only remove activity for that user.
        """
        activity_type = self.env.ref(
            'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
            raise_if_not_found=False
        )
        if activity_type:
            domain = [('activity_type_id', '=', activity_type.id)]
            if user_id:
                domain.append(('user_id', '=', user_id))
            self.activity_ids.filtered_domain(domain).unlink()

    def action_approve_discount(self, notes='', counter_offer_percent=0.0):
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

        # Handle counter-offer
        action = 'approve'
        new_discount = self.effective_max_discount
        if counter_offer_percent and counter_offer_percent < self.effective_max_discount:
            action = 'counter_offer'
            new_discount = counter_offer_percent
            self._apply_counter_offer(counter_offer_percent)

        # Log approval
        self.env['sale.discount.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': current_level.id,
            'user_id': self.env.user.id,
            'action': action,
            'old_max_discount': self.effective_max_discount,
            'new_max_discount': new_discount if action == 'counter_offer' else 0.0,
            'notes': notes,
            'ip_address': ip_address,
        })

        # Mode Check: All Must Approve?
        is_level_completed = True
        if current_level.approval_mode == 'all_must':
            # Count distinct approvers who have already signed off (approve or counter_offer)
            approvals = self.env['sale.discount.approval.log'].search([
                ('order_id', '=', self.id),
                ('level_id', '=', current_level.id),
                ('action', 'in', ('approve', 'counter_offer')),
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
                    "✅ <b>Approved by %(user)s</b> at level <b>%(level)s</b>.%(counter)s<br/>"
                    "Status: <b>Waiting for others</b> (%(remaining)s)",
                    user=self.env.user.name,
                    level=current_level.name,
                    counter=(
                        _(" Counter-offer: %(pct).2f%%.", pct=counter_offer_percent)
                        if action == 'counter_offer' else ''
                    ),
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
            # Advance to next level
            self.write({
                'current_approval_level_id': next_level.id,
            })
            self._create_approval_activities(next_level)
            self.message_post(
                body=Markup(_(
                    "✅ <b>Approved by %(user)s</b> at level <b>%(level)s</b>."
                    "%(counter)s<br/>"
                    "Advancing to next level: <b>%(next)s</b>",
                    user=self.env.user.name,
                    level=current_level.name,
                    counter=(
                        _(" Counter-offer: %(pct).2f%%.", pct=counter_offer_percent)
                        if action == 'counter_offer' else ''
                    ),
                    next=next_level.name,
                )),
                subtype_xmlid='mail.mt_note',
            )
        else:
            # Final approval — proceed to confirm
            self.write({
                'approval_state': 'approved',
            })
            self.message_post(
                body=Markup(_(
                    "✅ <b>Final Approval by %(user)s</b> at level "
                    "<b>%(level)s</b>.%(counter)s<br/>"
                    "Order is now approved and will be confirmed.",
                    user=self.env.user.name,
                    level=current_level.name,
                    counter=(
                        _(" Counter-offer: %(pct).2f%%.", pct=counter_offer_percent)
                        if action == 'counter_offer' else ''
                    ),
                )),
                subtype_xmlid='mail.mt_note',
            )
            # Auto-confirm after final approval
            super(SaleOrder, self).action_confirm()

    def action_reject_discount(self, reason=''):
        """Called by the wizard to reject."""
        self.ensure_one()
        if not self.is_current_user_approver:
            raise AccessError(
                _("You are not authorized to reject this order at the current level.")
            )

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.env['sale.discount.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id,
            'action': 'reject',
            'old_max_discount': self.effective_max_discount,
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

        # Notify submitter via activity
        if self.submitted_by:
            activity_type = self.env.ref(
                'gifari_sale_discount_approval.mail_activity_type_sale_discount_approval',
                raise_if_not_found=False,
            )
            if activity_type:
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=self.submitted_by.id,
                    summary=_("Discount REJECTED on %s", self.name),
                    note=_(
                        "Your discount request on <b>%(order)s</b> was rejected "
                        "by %(user)s.<br/>Reason: %(reason)s",
                        order=self.name,
                        user=self.env.user.name,
                        reason=reason or _('No reason provided'),
                    ),
                )

    def action_resubmit_approval(self):
        """Allow salesperson to re-submit after rejection (Q2=A)."""
        self.ensure_one()
        if self.approval_state != 'rejected':
            raise UserError(_("Only rejected orders can be re-submitted."))

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        first_level = self._get_first_approval_level()
        if not first_level:
            raise UserError(_("No approval levels configured."))

        self.env['sale.discount.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': first_level.id,
            'user_id': self.env.user.id,
            'action': 'resubmit',
            'old_max_discount': self.effective_max_discount,
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
        """Cancel a pending approval and return to draft."""
        self.ensure_one()
        if self.approval_state not in ('pending', 'rejected'):
            raise UserError(
                _("Can only cancel pending or rejected approval requests.")
            )

        ip_address = ''
        if request:
            ip_address = request.httprequest.remote_addr or ''

        self.env['sale.discount.approval.log'].create({
            'order_id': self.id,
            'company_id': self.company_id.id,
            'level_id': self.current_approval_level_id.id,
            'user_id': self.env.user.id,
            'action': 'cancel',
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
        """Open the approval wizard for current user."""
        self.ensure_one()
        return {
            'name': _("Discount Approval"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.discount.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_level_id': self.current_approval_level_id.id,
                'default_current_discount': self.effective_max_discount,
            },
        }

    # ══════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════

    def _apply_counter_offer(self, new_discount_percent):
        """Apply counter-offer: reduce all line discounts proportionally."""
        self.ensure_one()
        if self.max_line_discount <= 0:
            return

        ratio = new_discount_percent / self.max_line_discount
        for line in self.order_line:
            if not line.display_type and line.discount > 0:
                line.discount = line.discount * ratio
