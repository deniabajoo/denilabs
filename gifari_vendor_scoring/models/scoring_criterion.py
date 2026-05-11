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

    description = fields.Text(
        string="Panduan Penilaian",
        help="Penjelasan cara menilai kriteria ini (skala 1-100).",
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


    _unique_code_company = models.Constraint(
        'UNIQUE(code, company_id)',
        'Kode kriteria harus unik per perusahaan.',
    )

