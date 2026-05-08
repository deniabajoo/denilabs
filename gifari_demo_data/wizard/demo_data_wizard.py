# -*- coding: utf-8 -*-
from odoo import models, fields, _
import logging

from ..hooks.post_init_hook import generate_demo_data

_logger = logging.getLogger(__name__)


class GifariDemoDataWizard(models.TransientModel):
    _name = 'gifari.demo.data.wizard'
    _description = 'Generate Demo Data Wizard'

    month_count = fields.Integer(
        string='Months Back', default=6,
        help="Berapa bulan ke belakang data transaksi akan di-generate?")
    generate_so = fields.Boolean(string='Generate Sales Orders', default=True)
    generate_po = fields.Boolean(string='Generate Purchase Orders', default=True)
    generate_spk_scores = fields.Boolean(
        string='Generate SPK-SAW Scores', default=True,
        help="Hitung SAW scoring otomatis setelah transaksi di-generate.")
    generate_delegation_samples = fields.Boolean(
        string='Generate Delegation Samples', default=True,
        help="Generate beberapa contoh SO dengan status delegasi.")
    generate_sla_breach_samples = fields.Boolean(
        string='Generate SLA Breach Samples', default=True,
        help="Generate SO pending yang sudah melewati SLA deadline.")

    def action_generate_data(self):
        self.ensure_one()
        _logger.info("Manual demo data generation triggered.")
        generate_demo_data(
            self.env,
            check_demo_mode=False,
            months_back=self.month_count,
            generate_so=self.generate_so,
            generate_po=self.generate_po,
            generate_spk=self.generate_spk_scores,
            generate_delegation=self.generate_delegation_samples,
            generate_sla_breach=self.generate_sla_breach_samples,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Demo Data Generated ✅"),
                'message': _(
                    "Berhasil men-generate data demo untuk %(months)s bulan ke belakang "
                    "(SO, PO, Approval, SPK-SAW).",
                    months=self.month_count),
                'sticky': False, 'type': 'success',
            },
        }
