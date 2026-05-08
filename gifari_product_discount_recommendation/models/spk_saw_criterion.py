# -*- coding: utf-8 -*-
"""
Model Kriteria SAW.
SAW Formula:
    Benefit: r_ij = x_ij / max(x_j)
    Cost:    r_ij = min(x_j) / x_ij
    V_i = SUM(w_j * r_ij)
"""
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SpkSawCriterion(models.Model):
    _name = 'spk.saw.criterion'
    _description = 'SPK SAW Criterion'
    _order = 'sequence, id'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Criterion Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    criterion_type = fields.Selection(
        [('benefit', 'Benefit (Higher = Better)'),
         ('cost', 'Cost (Lower = Better)')],
        string='Criterion Type', required=True, default='benefit',
    )
    weight = fields.Float(
        string='Weight (%)', required=True, default=25.0, digits=(6, 2),
    )

    score_threshold_recommend = fields.Float(
        string='Recommend Threshold', default=0.6, digits=(4, 2),
    )
    score_threshold_high = fields.Float(
        string='High Priority Threshold', default=0.8, digits=(4, 2),
    )

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0 or rec.weight > 100:
                raise ValidationError(_("Weight harus antara 0 dan 100%."))

    @api.constrains('code')
    def _check_code(self):
        valid_codes = {'stock_age', 'overstocking_ratio', 'margin_safety', 'demand_trend'}
        for rec in self:
            if rec.code not in valid_codes:
                raise ValidationError(
                    _("Code '%(code)s' tidak dikenali. Pilih dari: %(valid)s",
                      code=rec.code, valid=', '.join(sorted(valid_codes))))

    @api.model
    def get_total_weight(self, company_id=None):
        domain = [('active', '=', True)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        return sum(self.search(domain).mapped('weight'))
