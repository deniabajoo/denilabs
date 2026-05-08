# -*- coding: utf-8 -*-
"""Extend sale.order.line untuk menampilkan rekomendasi SPK-SAW."""
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrderLineSpk(models.Model):
    _inherit = 'sale.order.line'

    spk_score_id = fields.Many2one(
        'spk.saw.product.score', string='SPK Score',
        compute='_compute_spk_recommendation', store=True)
    spk_recommended_discount = fields.Float(
        string='SPK Recommended Discount (%)',
        compute='_compute_spk_recommendation', store=True, digits='Discount')
    spk_recommendation_level = fields.Selection(
        related='spk_score_id.recommendation_level', string='SPK Level', store=True)
    spk_saw_score = fields.Float(
        related='spk_score_id.saw_score', string='SAW Score', store=True, digits=(4, 4))
    spk_rationale = fields.Text(
        related='spk_score_id.recommendation_rationale', string='SPK Rationale')
    discount_variance_state = fields.Selection(
        [('no_rec', 'No Recommendation'), ('aligned', 'Aligned with SPK'),
         ('over', 'Over SPK Recommendation'), ('under', 'Under SPK Recommendation')],
        string='Discount vs SPK', compute='_compute_discount_variance', store=True)

    @api.depends('product_id', 'order_id.company_id')
    def _compute_spk_recommendation(self):
        for line in self:
            if not line.product_id or line.display_type:
                line.spk_score_id = False
                line.spk_recommended_discount = 0.0
                continue
            score = self.env['spk.saw.product.score'].search([
                ('product_id', '=', line.product_id.id),
                ('company_id', '=', line.order_id.company_id.id),
            ], limit=1)
            line.spk_score_id = score.id if score else False
            line.spk_recommended_discount = score.recommended_discount_percent if score else 0.0

    @api.depends('discount', 'spk_recommended_discount', 'spk_score_id')
    def _compute_discount_variance(self):
        for line in self:
            if not line.spk_score_id or line.display_type:
                line.discount_variance_state = 'no_rec'
                continue
            rec_disc = line.spk_recommended_discount
            user_disc = line.discount
            tolerance = 2.0
            if rec_disc == 0.0:
                line.discount_variance_state = 'no_rec'
            elif abs(user_disc - rec_disc) <= tolerance:
                line.discount_variance_state = 'aligned'
            elif user_disc > rec_disc:
                line.discount_variance_state = 'over'
            else:
                line.discount_variance_state = 'under'
