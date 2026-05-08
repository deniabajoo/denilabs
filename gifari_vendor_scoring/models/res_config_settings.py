from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_scoring_evaluator_ids = fields.Many2many(
        related='company_id.vendor_scoring_evaluator_ids',
        readonly=False,
        string="Evaluator (Input Skor)",
    )
    vendor_scoring_validator_ids = fields.Many2many(
        related='company_id.vendor_scoring_validator_ids',
        readonly=False,
        string="Validator (Review Hasil)",
    )
    vendor_scoring_configurator_ids = fields.Many2many(
        related='company_id.vendor_scoring_configurator_ids',
        readonly=False,
        string="Configurator (Kelola Kriteria)",
    )

    @api.model
    def get_values(self):
        settings = super().get_values()
        company = self.env.company
        settings.update({
            'vendor_scoring_evaluator_ids': [(6, 0, company.vendor_scoring_evaluator_ids.ids)],
            'vendor_scoring_validator_ids': [(6, 0, company.vendor_scoring_validator_ids.ids)],
            'vendor_scoring_configurator_ids': [(6, 0, company.vendor_scoring_configurator_ids.ids)],
        })
        return settings

    def set_values(self):
        super().set_values()
        company = self.env.company
        evaluator_group = self.env.ref(
            'gifari_vendor_scoring.group_vendor_scoring_evaluator', raise_if_not_found=False
        )
        validator_group = self.env.ref(
            'gifari_vendor_scoring.group_vendor_scoring_validator', raise_if_not_found=False
        )
        configurator_group = self.env.ref(
            'gifari_vendor_scoring.group_vendor_scoring_configurator', raise_if_not_found=False
        )

        if evaluator_group:
            self._sync_group_members(
                evaluator_group,
                company.vendor_scoring_evaluator_ids,
                self.vendor_scoring_evaluator_ids,
            )
        if validator_group:
            self._sync_group_members(
                validator_group,
                company.vendor_scoring_validator_ids,
                self.vendor_scoring_validator_ids,
            )
        if configurator_group:
            self._sync_group_members(
                configurator_group,
                company.vendor_scoring_configurator_ids,
                self.vendor_scoring_configurator_ids,
            )

    @api.private
    def _sync_group_members(self, group, old_users, new_users):
        """Sync security group membership with Settings user selection."""
        removed_users = old_users - new_users
        added_users = new_users - old_users

        for removed_user in removed_users:
            removed_user.sudo().write({'groups_id': [(3, group.id)]})
        for added_user in added_users:
            added_user.sudo().write({'groups_id': [(4, group.id)]})
