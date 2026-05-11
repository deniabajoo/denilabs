from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScoringPeriodCriterion(models.Model):
    _name = 'scoring.period.criterion'
    _description = 'Kriteria Periode Evaluasi'
    _order = 'period_id, sequence, id'

    period_id = fields.Many2one(
        comodel_name='scoring.period',
        string="Periode",
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
    weight_decimal = fields.Float(
        string="Bobot Desimal",
        compute='_compute_weight_decimal',
        store=True,
    )

    @api.depends('weight')
    def _compute_weight_decimal(self):
        for record in self:
            record.weight_decimal = record.weight / 100.0

    @api.constrains('weight')
    def _check_weight_range(self):
        for record in self:
            if record.weight <= 0 or record.weight > 100:
                raise ValidationError(
                    "Bobot kriteria '%s' harus antara 0.01 dan 100." % record.criterion_id.name
                )
