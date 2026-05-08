from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScoringCriterion(models.Model):
    _name = 'scoring.criterion'
    _description = 'Kriteria Evaluasi Pemasok'
    _order = 'sequence, id'

    name = fields.Char(
        string="Nama Kriteria",
        required=True,
    )
    code = fields.Char(
        string="Kode",
        required=True,
    )
    criterion_type = fields.Selection(
        selection=[
            ('benefit', 'Benefit (Semakin Besar Semakin Baik)'),
            ('cost', 'Cost (Semakin Kecil Semakin Baik)'),
        ],
        string="Tipe Kriteria",
        required=True,
        default='benefit',
    )
    weight = fields.Float(
        string="Bobot (%)",
        required=True,
        help="Bobot kepentingan kriteria dalam persen. Total bobot semua kriteria aktif harus 100%.",
    )
    description = fields.Text(
        string="Panduan Penilaian",
        help="Penjelasan cara menilai kriteria ini (skala 1-10).",
    )
    sequence = fields.Integer(
        string="Urutan",
        default=10,
    )
    active = fields.Boolean(
        string="Aktif",
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Perusahaan",
        default=lambda self: self.env.company,
        required=True,
    )
    weight_decimal = fields.Float(
        string="Bobot Desimal",
        compute='_compute_weight_decimal',
        store=True,
        help="Bobot dalam desimal (0-1) untuk kalkulasi SAW.",
    )

    _constraints = [
        models.Constraint(
            'unique(code, company_id)',
            'Kode kriteria harus unik per perusahaan.',
        ),
    ]

    @api.depends('weight')
    def _compute_weight_decimal(self):
        for criterion in self:
            criterion.weight_decimal = criterion.weight / 100.0

    @api.constrains('weight')
    def _check_weight_range(self):
        for criterion in self:
            if criterion.weight <= 0 or criterion.weight > 100:
                raise ValidationError(
                    "Bobot kriteria '%s' harus antara 0.01 dan 100." % criterion.name
                )
