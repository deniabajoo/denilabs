# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ── Discount Amount (D3 + D1) ───────────────────────────────────────
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_discount_amount',
        store=True,
        readonly=False,
        currency_field='currency_id',
        help='Computed from Discount % × Unit Price × Quantity. '
             'Can be manually overridden if vendor provides a fixed nominal discount.',
    )

    @api.depends('price_unit', 'product_qty', 'discount', 'display_type')
    def _compute_discount_amount(self):
        """Compute discount amount from discount %. Result is editable."""
        for line in self:
            if line.display_type:
                line.discount_amount = 0.0
            else:
                line.discount_amount = line.price_unit * line.product_qty * (line.discount / 100.0)

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        """When user manually enters a discount amount, back-compute the discount %."""
        for line in self:
            if not line.display_type:
                base = line.price_unit * line.product_qty
                if base > 0 and line.discount_amount >= 0:
                    line.discount = (line.discount_amount / base) * 100.0
