from odoo import api, fields, models
from odoo.exceptions import ValidationError


class VendorScoreLine(models.Model):
    _name = 'vendor.score.line'
    _description = 'Detail Skor Pemasok per Kriteria'
    _order = 'criterion_id'

    vendor_score_id = fields.Many2one(
        comodel_name='vendor.score',
        string="Skor Pemasok",
        required=True,
        ondelete='cascade',
    )
    criterion_id = fields.Many2one(
        comodel_name='scoring.criterion',
        string="Kriteria",
        required=True,
    )
    raw_score = fields.Float(
        string="Skor Mentah (1-10)",
        digits=(10, 2),
        help="Nilai penilaian mentah pada skala 1-10.",
    )
    normalized_score = fields.Float(
        string="Skor Normalisasi (rᵢⱼ)",
        digits=(10, 4),
        help="Benefit: xᵢⱼ/max(xⱼ). Cost: min(xⱼ)/xᵢⱼ.",
    )
    weighted_score = fields.Float(
        string="Skor Terbobot (wⱼ×rᵢⱼ)",
        digits=(10, 4),
        help="Hasil perkalian bobot kriteria dengan skor normalisasi.",
    )
    criterion_type = fields.Selection(
        related='criterion_id.criterion_type',
        string="Tipe Kriteria",
    )
    criterion_weight = fields.Float(
        related='criterion_id.weight',
        string="Bobot (%)",
    )

    @api.constrains('raw_score')
    def _check_raw_score_range(self):
        for line in self:
            if line.raw_score and (line.raw_score < 1.0 or line.raw_score > 10.0):
                raise ValidationError(
                    "Skor untuk kriteria '%s' harus antara 1 dan 10. "
                    "Nilai yang dimasukkan: %.2f." % (
                        line.criterion_id.name,
                        line.raw_score,
                    )
                )
