# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ── Stock Availability Enhancement ───────────────────

    stock_status = fields.Selection(
        [
            ('available', 'In Stock'),
            ('partial', 'Partial Stock'),
            ('unavailable', 'Out of Stock'),
        ],
        string='Stock Status',
        compute='_compute_stock_status',
        store=True,
    )
    needs_purchase = fields.Boolean(
        string='Needs Purchase',
        compute='_compute_stock_status',
        store=True,
        help="True if available stock is insufficient for this line.",
    )

    @api.depends('free_qty_today', 'product_uom_qty', 'product_id')
    def _compute_stock_status(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.stock_status = False
                line.needs_purchase = False
                continue

            if not hasattr(line, 'free_qty_today'):
                # sale_stock not computing this field
                line.stock_status = False
                line.needs_purchase = False
                continue

            free_qty = line.free_qty_today or 0.0
            required = line.product_uom_qty or 0.0

            if free_qty >= required:
                line.stock_status = 'available'
                line.needs_purchase = False
            elif free_qty > 0:
                line.stock_status = 'partial'
                line.needs_purchase = True
            else:
                line.stock_status = 'unavailable'
                line.needs_purchase = True
