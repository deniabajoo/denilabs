# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

from ..hooks.post_init_hook import generate_demo_data

_logger = logging.getLogger(__name__)

class GifariDemoDataWizard(models.TransientModel):
    _name = 'gifari.demo.data.wizard'
    _description = 'Generate Demo Data Wizard'

    month_count = fields.Integer(
        string='Months Back', 
        default=6, 
        help="Berapa bulan ke belakang data transaksi (SO/PO) akan di-generate?"
    )
    
    def action_generate_data(self):
        self.ensure_one()
        _logger.info("Manual generation of demo data triggered by user.")
        
        # Panggil fungsi utama generator dari post_init_hook
        generate_demo_data(self.env, check_demo_mode=False, months_back=self.month_count)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demo Data Generated',
                'message': f'Berhasil men-generate transaksi demo untuk {self.month_count} bulan ke belakang.',
                'sticky': False,
                'type': 'success',
            }
        }
