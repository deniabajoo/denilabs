from odoo import fields, models


class ScoringPackage(models.Model):
    _name = 'scoring.package'
    _description = 'Paket Kriteria Evaluasi'

    name = fields.Char(
        string="Nama Paket",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name='scoring.package.line',
        inverse_name='package_id',
        string="Kriteria & Bobot",
        required=True,
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
