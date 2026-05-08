# -*- coding: utf-8 -*-
"""SAW Product Score model and engine."""
import logging
from datetime import timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SpkSawProductScore(models.Model):
    _name = 'spk.saw.product.score'
    _description = 'SPK SAW Product Score'
    _order = 'saw_score desc, id'
    _check_company_auto = True
    _rec_name = 'product_id'

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id', store=True, index=True)
    categ_id = fields.Many2one(
        related='product_id.categ_id', store=True, string='Product Category')

    raw_stock_age = fields.Float(string='Stock Age (days)', digits=(10, 2))
    raw_overstocking_ratio = fields.Float(string='Overstocking Ratio', digits=(10, 4))
    raw_margin_safety = fields.Float(string='Margin Safety (%)', digits=(10, 2))
    raw_demand_trend = fields.Float(string='Demand Trend (units/day)', digits=(10, 4))

    norm_stock_age = fields.Float(digits=(6, 4))
    norm_overstocking_ratio = fields.Float(digits=(6, 4))
    norm_margin_safety = fields.Float(digits=(6, 4))
    norm_demand_trend = fields.Float(digits=(6, 4))

    saw_score = fields.Float(string='SAW Score', digits=(6, 4))

    recommendation_level = fields.Selection(
        [('none', 'Tidak Direkomendasikan'), ('low', 'Diskon Rendah (1-10%)'),
         ('medium', 'Diskon Sedang (11-20%)'), ('high', 'Diskon Agresif (21-30%)')],
        string='Rekomendasi Level', compute='_compute_recommendation', store=True)
    recommended_discount_percent = fields.Float(
        string='Recommended Discount (%)', compute='_compute_recommendation',
        store=True, digits='Discount')
    recommendation_rationale = fields.Text(string='Rationale')

    last_computed = fields.Datetime(string='Last Computed')
    computation_period_days = fields.Integer(default=90)

    _sql_constraints = [
        ('unique_product_company', 'UNIQUE(product_id, company_id)',
         'Setiap produk hanya boleh memiliki satu baris score per perusahaan.'),
    ]

    @api.depends('saw_score')
    def _compute_recommendation(self):
        for rec in self:
            score = rec.saw_score
            if score >= 0.80:
                rec.recommendation_level = 'high'
                rec.recommended_discount_percent = 25.0
            elif score >= 0.60:
                rec.recommendation_level = 'medium'
                rec.recommended_discount_percent = 15.0
            elif score >= 0.40:
                rec.recommendation_level = 'low'
                rec.recommended_discount_percent = 7.0
            else:
                rec.recommendation_level = 'none'
                rec.recommended_discount_percent = 0.0

    @api.model
    def _cron_compute_saw_scores(self):
        companies = self.env['res.company'].search([])
        for company in companies:
            self.with_context(company_id=company.id)._compute_all_scores(company)

    @api.model
    def _compute_all_scores(self, company=None):
        if company is None:
            company = self.env.company
        criteria = self.env['spk.saw.criterion'].search([
            ('company_id', '=', company.id), ('active', '=', True)], order='sequence')
        if not criteria:
            _logger.warning("No SAW criteria for company %s", company.name)
            return

        total_weight = sum(criteria.mapped('weight'))
        if abs(total_weight - 100.0) > 0.01:
            _logger.warning("SAW weights sum to %.2f%% for %s. Normalizing.",
                            total_weight, company.name)

        products = self.env['product.product'].search([
            ('type', 'in', ['consu', 'product']),
            ('active', '=', True), ('sale_ok', '=', True)])
        if not products:
            return

        period_days = 90
        date_from = fields.Date.today() - timedelta(days=period_days)

        raw_data = {}
        for product in products:
            raw_data[product.id] = self._collect_raw_data(product, company, date_from, period_days)

        normalized_data = self._normalize(raw_data, criteria)

        scores = {}
        weight_sum = sum(criteria.mapped('weight'))
        for prod_id, norm_vals in normalized_data.items():
            saw_score = 0.0
            for criterion in criteria:
                w = criterion.weight / weight_sum
                v = norm_vals.get(criterion.code, 0.0)
                saw_score += w * v
            scores[prod_id] = saw_score

        now = fields.Datetime.now()
        for product in products:
            pid = product.id
            score = scores.get(pid, 0.0)
            raw = raw_data.get(pid, {})
            norms = normalized_data.get(pid, {})
            rationale = self._build_rationale(product, raw, score)

            existing = self.search([
                ('product_id', '=', pid), ('company_id', '=', company.id)], limit=1)

            vals = {
                'product_id': pid, 'company_id': company.id,
                'raw_stock_age': raw.get('stock_age', 0.0),
                'raw_overstocking_ratio': raw.get('overstocking_ratio', 0.0),
                'raw_margin_safety': raw.get('margin_safety', 0.0),
                'raw_demand_trend': raw.get('demand_trend', 0.0),
                'norm_stock_age': norms.get('stock_age', 0.0),
                'norm_overstocking_ratio': norms.get('overstocking_ratio', 0.0),
                'norm_margin_safety': norms.get('margin_safety', 0.0),
                'norm_demand_trend': norms.get('demand_trend', 0.0),
                'saw_score': round(score, 4),
                'recommendation_rationale': rationale,
                'last_computed': now,
                'computation_period_days': period_days,
            }
            if existing:
                existing.write(vals)
            else:
                self.create(vals)

        _logger.info("SAW scoring selesai: %d produk untuk %s", len(products), company.name)

    def _collect_raw_data(self, product, company, date_from, period_days):
        result = {}
        on_hand = product.qty_available
        demand_qty = self._get_demand_qty(product, date_from)
        daily_demand = demand_qty / period_days if period_days > 0 else 0

        if daily_demand > 0:
            stock_age = on_hand / daily_demand
        elif on_hand > 0:
            stock_age = period_days * 2
        else:
            stock_age = 0.0
        result['stock_age'] = round(stock_age, 2)

        monthly_demand = daily_demand * 30
        if monthly_demand > 0:
            overstocking_ratio = on_hand / monthly_demand
        elif on_hand > 0:
            overstocking_ratio = 10.0
        else:
            overstocking_ratio = 0.0
        result['overstocking_ratio'] = round(overstocking_ratio, 4)

        list_price = product.lst_price or 0.0
        standard_price = product.standard_price or 0.0
        if list_price > 0 and list_price > standard_price:
            margin_safety = (list_price - standard_price) / list_price * 100.0
        else:
            margin_safety = 0.0
        result['margin_safety'] = round(margin_safety, 2)
        result['demand_trend'] = round(daily_demand, 4)
        return result

    def _get_demand_qty(self, product, date_from):
        sol_data = self.env['sale.order.line'].read_group(
            domain=[
                ('product_id', '=', product.id),
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.date_order', '>=', fields.Datetime.to_datetime(date_from)),
            ],
            fields=['product_uom_qty:sum'],
            groupby=[])
        if sol_data:
            return sol_data[0].get('product_uom_qty', 0.0) or 0.0
        return 0.0

    def _normalize(self, raw_data, criteria):
        values_by_code = {
            c.code: [raw_data[pid].get(c.code, 0.0) for pid in raw_data]
            for c in criteria}
        normalized = {pid: {} for pid in raw_data}
        for criterion in criteria:
            code = criterion.code
            vals = values_by_code.get(code, [])
            ctype = criterion.criterion_type
            max_val = max(vals) if vals else 0.0
            min_val = min(vals) if vals else 0.0
            for prod_id, raw in raw_data.items():
                x = raw.get(code, 0.0)
                if ctype == 'benefit':
                    norm = (x / max_val) if max_val > 0 else 0.0
                else:
                    norm = (min_val / x) if x > 0 else 0.0
                normalized[prod_id][code] = round(max(0.0, min(1.0, norm)), 4)
        return normalized

    def _build_rationale(self, product, raw, score):
        parts = []
        stock_age = raw.get('stock_age', 0)
        overstocking = raw.get('overstocking_ratio', 0)
        margin = raw.get('margin_safety', 0)
        demand = raw.get('demand_trend', 0)
        if stock_age > 60:
            parts.append(f"Stok menua {stock_age:.0f} hari")
        if overstocking > 2.0:
            parts.append(f"Overstocking {overstocking:.1f}x")
        if margin < 20:
            parts.append(f"Margin terbatas {margin:.1f}%")
        if demand < 0.1:
            parts.append("Slow-moving item")
        elif demand > 1.0:
            parts.append(f"Demand aktif {demand:.2f} unit/hari")
        if score >= 0.8:
            parts.insert(0, "⚡ PRIORITAS TINGGI")
        elif score >= 0.6:
            parts.insert(0, "✅ Direkomendasikan")
        elif score >= 0.4:
            parts.insert(0, "🔵 Pertimbangkan diskon ringan")
        else:
            parts.insert(0, "❌ Tidak perlu diskon saat ini")
        return ". ".join(parts) + f". (SAW Score: {score:.4f})"
