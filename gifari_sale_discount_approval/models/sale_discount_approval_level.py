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
        help="e.g. 'Sales Supervisor', 'Sales Manager', 'Director'",
    )
    active = fields.Boolean(default=True)

    # ── Threshold Configuration ──────────────────────────

    min_discount = fields.Float(
        string='Min Discount (%)',
        required=True,
        help="Minimum discount percentage that triggers this level.",
    )
    max_discount = fields.Float(
        string='Max Discount (%)',
        help="Maximum discount this level can approve. "
             "Leave 0 for unlimited (final level).",
    )

    # ── Approver Configuration ───────────────────────────

    approver_ids = fields.Many2many(
        'res.users',
        'sale_discount_approval_level_user_rel',
        'level_id', 'user_id',
        string='Approvers',
        required=True,
        help="Users who can approve at this level.",
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
                    _("Max Discount (%(max)s%%) must be greater than or equal to "
                      "Min Discount (%(min)s%%).",
                      max=record.max_discount,
                      min=record.min_discount)
                )

    @api.constrains('approver_ids')
    def _check_approvers(self):
        for record in self:
            if not record.approver_ids:
                raise ValidationError(
                    _("At least one approver must be assigned to level '%(name)s'.",
                      name=record.name)
                )

    # ── Automatic Security Group Granting ────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        group_manager = self.env.ref('gifari_sale_discount_approval.group_sale_approval_manager', raise_if_not_found=False)
        if group_manager:
            for record in records:
                if record.approver_ids:
                    group_manager.sudo().write({'user_ids': [(4, user.id) for user in record.approver_ids]})
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'approver_ids' in vals:
            group_manager = self.env.ref('gifari_sale_discount_approval.group_sale_approval_manager', raise_if_not_found=False)
            if group_manager:
                for record in self:
                    if record.approver_ids:
                        group_manager.sudo().write({'user_ids': [(4, user.id) for user in record.approver_ids]})
        return res
