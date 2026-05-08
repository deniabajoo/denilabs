from odoo import fields, models


class VendorScore(models.Model):
    _name = 'vendor.score'
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

    _constraints = [
        models.Constraint(
            'unique(period_id, partner_id)',
            'Pemasok hanya boleh dinilai sekali per periode evaluasi.',
        ),
    ]

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
