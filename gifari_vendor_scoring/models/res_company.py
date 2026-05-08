from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    vendor_scoring_evaluator_ids = fields.Many2many(
        comodel_name='res.users',
        relation='company_vendor_scoring_evaluator_rel',
        column1='company_id',
        column2='user_id',
        string="Evaluator",
        help="User yang berhak melakukan input skor pemasok.",
    )
    vendor_scoring_validator_ids = fields.Many2many(
        comodel_name='res.users',
        relation='company_vendor_scoring_validator_rel',
        column1='company_id',
        column2='user_id',
        string="Validator",
        help="User yang berhak memvalidasi hasil evaluasi.",
    )
    vendor_scoring_configurator_ids = fields.Many2many(
        comodel_name='res.users',
        relation='company_vendor_scoring_configurator_rel',
        column1='company_id',
        column2='user_id',
        string="Configurator",
        help="User yang berhak mengkonfigurasi kriteria dan bobot.",
    )
