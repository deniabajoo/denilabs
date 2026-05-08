# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleDiscountApprovalLevel(models.Model):
    _name = 'sale.discount.approval.level'
    _description = 'Sale Discount Approval Level'
    _order = 'sequence, id'
    _check_company_auto = True

    # ── Core Fields ──────────────────────────────────────

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    sequence = fields.Integer(
        string='Level',
        default=10,
        help="Determines the order of approval levels. Lower = first.",
    )
    name = fields.Char(
        string='Level Name',
        required=True,
    )
    active = fields.Boolean(default=True)

    # ── Threshold Configuration ──────────────────────────

    min_discount = fields.Float(
        string='Min Discount (%)',
        required=True,
    )
    max_discount = fields.Float(
        string='Max Discount (%)',
        help="Leave 0 for unlimited (final level).",
    )

    # ── Approver Configuration ───────────────────────────

    approver_ids = fields.Many2many(
        'res.users',
        'sale_discount_approval_level_user_rel',
        'level_id', 'user_id',
        string='Approvers',
        required=True,
    )
    approval_mode = fields.Selection(
        [
            ('any_one', 'Any One Approver'),
            ('all_must', 'All Must Approve'),
        ],
        string='Approval Mode',
        default='any_one',
        required=True,
    )

    # ── NEW: SLA & Delegation ────────────────────────────

    sla_hours = fields.Float(
        string='SLA (Hours)',
        default=24.0,
        help="Batas waktu approval. Setelah melewati batas ini, "
             "sistem akan mengirim notifikasi eskalasi ke level berikutnya "
             "atau ke manager. Set 0 untuk non-aktif SLA.",
    )
    escalate_to_ids = fields.Many2many(
        'res.users',
        'sale_discount_level_escalate_user_rel',
        'level_id', 'user_id',
        string='Escalation Recipients',
        help="User yang diberitahu jika SLA terlewat. "
             "Biasanya atasan dari approver level ini.",
    )
    can_delegate = fields.Boolean(
        string='Allow Delegation',
        default=True,
        help="Jika aktif, approver di level ini dapat "
             "mendelegasikan approval ke user lain.",
    )
    send_email_notification = fields.Boolean(
        string='Send Email Notification',
        default=True,
        help="Kirim email ke approver selain in-app activity.",
    )

    # ── Constraints ──────────────────────────────────────

    @api.constrains('min_discount', 'max_discount')
    def _check_discount_range(self):
        for record in self:
            if record.min_discount < 0:
                raise ValidationError(
                    _("Min Discount cannot be negative.")
                )
            if record.max_discount and record.max_discount < record.min_discount:
                raise ValidationError(
                    _("Max Discount (%(max)s%%) must be >= Min Discount (%(min)s%%).",
                      max=record.max_discount, min=record.min_discount)
                )

    @api.constrains('approver_ids')
    def _check_approvers(self):
        for record in self:
            if not record.approver_ids:
                raise ValidationError(
                    _("At least one approver must be assigned to level '%(name)s'.",
                      name=record.name)
                )

    @api.constrains('sla_hours')
    def _check_sla_hours(self):
        for record in self:
            if record.sla_hours < 0:
                raise ValidationError(_("SLA hours cannot be negative."))

    # ── Automatic Security Group Granting ────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._sync_approver_group(records)
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'approver_ids' in vals:
            self._sync_approver_group(self)
        return res

    def _sync_approver_group(self, records):
        group_manager = self.env.ref(
            'gifari_sale_discount_approval.group_sale_approval_manager',
            raise_if_not_found=False,
        )
        if group_manager:
            for record in records:
                if record.approver_ids:
                    group_manager.sudo().write(
                        {'user_ids': [(4, u.id) for u in record.approver_ids]}
                    )
