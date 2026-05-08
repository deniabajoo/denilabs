# -*- coding: utf-8 -*-
"""Wizard untuk menjalankan SAW scoring secara manual."""
import logging
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class SpkRunScoringWizard(models.TransientModel):
    _name = 'spk.run.scoring.wizard'
    _description = 'SPK: Run SAW Scoring Now'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    product_category_id = fields.Many2one(
        'product.category', string='Filter by Category')
    period_days = fields.Integer(string='Analysis Period (days)', default=90)
    info = fields.Text(
        string='Info', readonly=True,
        default='Klik "Run SAW Scoring" untuk menghitung ulang skor SPK semua produk.\n'
                'Proses ini mungkin memakan waktu beberapa detik.')

    def action_run_scoring(self):
        self.ensure_one()
        self.env['spk.saw.product.score']._compute_all_scores(self.company_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("SAW Scoring Selesai"),
                'message': _("Scoring SPK-SAW berhasil dihitung ulang untuk %(company)s.",
                             company=self.company_id.name),
                'type': 'success', 'sticky': False,
            },
        }
