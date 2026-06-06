from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    @api.constrains('line_ids')
    def _check_total_weight(self):
        for package in self:
            if not package.line_ids:
                continue
            total_weight = sum(package.line_ids.mapped('weight'))
            if abs(total_weight - 100.0) > 0.01:
                raise ValidationError(
                    "Total bobot kriteria pada paket '%s' harus tepat 100%%. "
                    "Saat ini: %.2f%%." % (package.name, total_weight)
                )
