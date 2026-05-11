from odoo import api, fields, models

RANK_MEDAL_MAP = {1: '🥇', 2: '🥈', 3: '🥉'}


class VendorScore(models.Model):
    _name = 'vendor.score'
    _inherit = ['mail.thread']
    _description = 'Skor Pemasok per Periode'
    _order = 'rank, id'

    period_id = fields.Many2one(
        comodel_name='scoring.period',
        string="Periode Evaluasi",
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Pemasok",
        required=True,
        domain=[('supplier_rank', '>', 0)],
    )
    score_line_ids = fields.One2many(
        comodel_name='vendor.score.line',
        inverse_name='vendor_score_id',
        string="Detail Skor per Kriteria",
    )
    final_score = fields.Float(
        string="Skor Akhir (Vᵢ)",
        digits=(10, 4),
        tracking=True,
        help="Nilai preferensi SAW: Vᵢ = Σ(wⱼ × rᵢⱼ).",
    )
    rank = fields.Integer(
        string="Peringkat",
        default=0,
    )
    is_recommended = fields.Boolean(
        string="Direkomendasikan",
        default=False,
        help="Pemasok dengan peringkat tertinggi.",
    )
    company_id = fields.Many2one(
        related='period_id.company_id',
        string="Perusahaan",
        store=True,
    )
    period_state = fields.Selection(
        related='period_id.state',
        string="Status Periode",
    )
    rank_display = fields.Char(
        string="Peringkat",
        compute='_compute_rank_display',
    )

    _unique_period_partner = models.Constraint(
        'UNIQUE(period_id, partner_id)',
        'Pemasok hanya boleh dinilai sekali per periode evaluasi.',
    )

    @api.depends('rank')
    def _compute_rank_display(self):
        for vendor_score in self:
            if vendor_score.rank:
                medal = RANK_MEDAL_MAP.get(vendor_score.rank, '')
                vendor_score.rank_display = (
                    '%s #%d' % (medal, vendor_score.rank) if medal
                    else '#%d' % vendor_score.rank
                )
            else:
                vendor_score.rank_display = ''

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.period_id and not record.score_line_ids:
                lines = [
                    (0, 0, {'criterion_id': pc.criterion_id.id, 'raw_score': 0.0})
                    for pc in record.period_id.period_criterion_ids
                ]
                if lines:
                    record.score_line_ids = lines
        return records

    def action_open_score_detail(self):
        """Buka form detail skor pemasok dalam popup."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Skor: %s' % self.partner_id.name,
            'res_model': 'vendor.score',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('gifari_vendor_scoring.view_vendor_score_form').id,
            'target': 'new',
        }

    def get_radar_data(self):
        """RPC endpoint: return radar chart data for this vendor vs period average."""
        self.ensure_one()
        all_period_lines = self.env['vendor.score.line'].search_read(
            [('vendor_score_id.period_id', '=', self.period_id.id)],
            ['criterion_id', 'normalized_score'],
        )

        criterion_all_scores = {}
        for line_record in all_period_lines:
            crit_id = line_record['criterion_id'][0]
            criterion_all_scores.setdefault(crit_id, []).append(
                line_record['normalized_score']
            )

        labels = []
        vendor_normalized = []
        average_normalized = []

        for score_line in self.score_line_ids.sorted('criterion_id'):
            labels.append(score_line.criterion_id.name)
            vendor_normalized.append(round(score_line.normalized_score, 4))
            crit_scores = criterion_all_scores.get(score_line.criterion_id.id, [])
            average_normalized.append(
                round(sum(crit_scores) / len(crit_scores), 4) if crit_scores else 0
            )

        return {
            'labels': labels,
            'vendor_scores': vendor_normalized,
            'avg_scores': average_normalized,
            'vendor_name': self.partner_id.name,
        }
