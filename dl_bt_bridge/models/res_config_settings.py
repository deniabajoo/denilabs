# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_bt_print_enabled = fields.Boolean(
        related='pos_config_id.bt_print_enabled',
        readonly=False,
    )
    pos_bt_intent_scheme = fields.Selection(
        related='pos_config_id.bt_intent_scheme',
        readonly=False,
    )
    pos_bt_paper_size = fields.Selection(
        related='pos_config_id.bt_paper_size',
        readonly=False,
    )
