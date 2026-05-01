# -*- coding: utf-8 -*-
import logging
from odoo import models, _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Override to notify salesperson when goods are received."""
        res = super().button_validate()
        self._notify_sales_stock_received()
        return res

    def _notify_sales_stock_received(self):
        """Find active SO lines waiting for received products and notify."""
        for picking in self:
            # Only for incoming pickings (receipts)
            if picking.picking_type_code != 'incoming':
                continue

            received_products = picking.move_ids.filtered(
                lambda m: m.state == 'done'
            ).mapped('product_id')

            if not received_products:
                continue

            # Find active SO lines (draft/sent) needing these products (Q11=A)
            waiting_lines = self.env['sale.order.line'].search([
                ('product_id', 'in', received_products.ids),
                ('order_id.state', 'in', ['draft', 'sent']),
                ('needs_purchase', '=', True),
            ])

            if not waiting_lines:
                continue

            # Group by SO to avoid duplicate activities
            orders = waiting_lines.mapped('order_id')
            activity_type = self.env.ref(
                'gifari_sale_discount_approval.mail_activity_type_stock_received_notice',
                raise_if_not_found=False,
            )
            if not activity_type:
                continue

            for order in orders:
                affected_lines = waiting_lines.filtered(
                    lambda l: l.order_id == order
                )
                product_names = ', '.join(
                    affected_lines.mapped('product_id.name')
                )
                # Create activity for salesperson (Q13=A: deep link)
                order.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=order.user_id.id or order.create_uid.id,
                    summary=_(
                        "Stock received for %s", order.name
                    ),
                    note=_(
                        "Good news! The following products have been received "
                        "in warehouse:<br/><b>%(products)s</b><br/>"
                        "Sales Order <a href='/odoo/sales/%(order_id)s'>"
                        "%(order_name)s</a> can now proceed.",
                        products=product_names,
                        order_id=order.id,
                        order_name=order.name,
                    ),
                )

                _logger.info(
                    "Stock received notification sent to %s for SO %s "
                    "(products: %s)",
                    order.user_id.name or order.create_uid.name,
                    order.name,
                    product_names,
                )
