from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScoringPackageLine(models.Model):
    _name = 'scoring.package.line'
    _description = 'Baris Paket Kriteria'
    _order = 'package_id, sequence, id'

    package_id = fields.Many2one(
        comodel_name='scoring.package',
        string="Paket",
        required=True,
        ondelete='cascade',
    )
    criterion_id = fields.Many2one(
        comodel_name='scoring.criterion',
        string="Kriteria",
        required=True,
        ondelete='cascade',
    )
    criterion_type = fields.Selection(
        related='criterion_id.criterion_type',
        string="Tipe",
        readonly=True,
    )
    sequence = fields.Integer(
        related='criterion_id.sequence',
        string="Urutan",
        store=True,
    )
    weight = fields.Float(
        string="Bobot (%)",
        required=True,
        default=0.0,
    )

    @api.constrains('weight')
    def _check_weight_range(self):
        for line in self:
            if line.weight <= 0 or line.weight > 100:
                raise ValidationError(
                    "Bobot kriteria '%s' harus antara 0.01 dan 100." % line.criterion_id.name
                )
