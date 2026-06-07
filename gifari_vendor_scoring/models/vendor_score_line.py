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
        ondelete='cascade',
    )
    raw_score = fields.Float(
        string="Skor Mentah (1-100)",
        digits=(10, 2),
        help="Nilai penilaian mentah pada skala 1-100.",
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
        string="Bobot (%)",
        compute='_compute_criterion_weight',
    )

    @api.depends('vendor_score_id.period_id.period_criterion_ids.weight', 'criterion_id')
    def _compute_criterion_weight(self):
        for line in self:
            if not line.vendor_score_id.period_id or not line.criterion_id:
                line.criterion_weight = 0.0
                continue
            period_criterion = line.vendor_score_id.period_id.period_criterion_ids.filtered(
                lambda pc: pc.criterion_id.id == line.criterion_id.id
            )
            line.criterion_weight = period_criterion.weight if period_criterion else 0.0

    @api.constrains('raw_score')
    def _check_raw_score_range(self):
        # Skala seragam 1-100 untuk Benefit maupun Cost. Arah "baik" ditentukan
        # saat normalisasi SAW: Benefit → nilai lebih tinggi lebih baik (x/maks),
        # Cost → nilai lebih rendah lebih baik (min/x).
        for line in self:
            if not line.raw_score:
                continue
            if line.raw_score < 1.0 or line.raw_score > 100.0:
                direction = (
                    "nilai lebih rendah berarti lebih baik"
                    if line.criterion_type == 'cost'
                    else "nilai lebih tinggi berarti lebih baik"
                )
                criterion_label = 'Cost' if line.criterion_type == 'cost' else 'Benefit'
                raise ValidationError(
                    "Skor untuk kriteria '%s' (%s) harus antara 1 dan 100 — %s. "
                    "Nilai yang dimasukkan: %.2f." % (
                        line.criterion_id.name,
                        criterion_label,
                        direction,
                        line.raw_score,
                    )
                )
