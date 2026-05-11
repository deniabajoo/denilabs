from odoo import api, fields, models


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    vs_latest_score = fields.Float(
        string="Skor Evaluasi Terakhir",
        compute='_compute_vendor_latest_score',
        digits=(10, 4),
        help="Skor evaluasi vendor terbaru dari metode SAW.",
    )
    vs_latest_rank_display = fields.Char(
        string="Ranking Terakhir",
        compute='_compute_vendor_latest_score',
    )
    vs_latest_period_id = fields.Many2one(
        comodel_name='scoring.period',
        string="Periode Evaluasi",
        compute='_compute_vendor_latest_score',
    )

    @api.depends('partner_id')
    def _compute_vendor_latest_score(self):
        """Ambil skor dan ranking terbaru dari pemasok."""
        if not self.ids:
            # Prevent operations on empty datasets
            for record in self:
                record.vs_latest_score = 0.0
                record.vs_latest_rank_display = False
                record.vs_latest_period_id = False
            return

        partner_ids = self.mapped('partner_id').ids
        if not partner_ids:
            for record in self:
                record.vs_latest_score = 0.0
                record.vs_latest_rank_display = False
                record.vs_latest_period_id = False
            return

        # Fetch the latest validated score for each partner (N+1 prevention via search_read with order/limit logic or mapped grouping)
        # However, search_read doesn't support grouping with limit. Let's fetch all validated scores for these partners, ordered by date descending.
        domain = [
            ('partner_id', 'in', partner_ids),
            ('period_id.state', '=', 'validated'),
        ]
        
        # Using search to get the records, order by period end date desc
        latest_scores = self.env['vendor.score'].search(domain, order='create_date desc')
        
        # Get only the latest per partner
        score_by_partner = {}
        for score in latest_scores:
            if score.partner_id.id not in score_by_partner:
                score_by_partner[score.partner_id.id] = score

        for record in self:
            partner_id = record.partner_id.id
            if partner_id in score_by_partner:
                score_rec = score_by_partner[partner_id]
                record.vs_latest_score = score_rec.final_score
                record.vs_latest_rank_display = score_rec.rank_display
                record.vs_latest_period_id = score_rec.period_id.id
            else:
                record.vs_latest_score = 0.0
                record.vs_latest_rank_display = False
                record.vs_latest_period_id = False
