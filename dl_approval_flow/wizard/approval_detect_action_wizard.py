# Copyright 2026 Deni Labs
from lxml import etree

from odoo import _, api, fields, models


class ApprovalDetectActionWizard(models.TransientModel):
    _name = "approval.detect.action.wizard"
    _description = "Detect Available Actions Wizard"

    config_id = fields.Many2one(
        "approval.workflow.config",
        string="Workflow Configuration",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        related="config_id.model_id",
        string="Target Model",
    )
    line_ids = fields.One2many(
        "approval.detect.action.wizard.line",
        "wizard_id",
        string="Available Actions",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "config_id" not in self.env.context:
            return res

        config_id = self.env.context.get("config_id")
        config = self.env["approval.workflow.config"].browse(config_id)
        if not config or not config.model_id:
            return res

        res["config_id"] = config.id
        existing_methods = config.gated_action_ids.mapped("method_name")
        methods = {}

        try:
            # Get the parsed Form View
            view_info = self.env[config.model_id.model].get_view(view_type="form")
            arch = etree.fromstring(view_info["arch"])
            
            # Find all object-type buttons
            for btn in arch.xpath("//button[@type='object']"):
                method_name = btn.get("name")
                if not method_name or method_name in existing_methods:
                    continue
                if method_name in methods:
                    continue
                
                label = btn.get("string") or method_name
                methods[method_name] = label
        except Exception:
            pass 

        lines = []
        for m_name, m_label in methods.items():
            lines.append(
                (
                    0,
                    0,
                    {
                        "method_name": m_name,
                        "button_label": m_label,
                        "is_selected": False,
                    },
                )
            )

        res["line_ids"] = lines
        return res

    def action_add_selected(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        
        for line in selected_lines:
            self.env["approval.gated.action"].create(
                {
                    "config_id": self.config_id.id,
                    "method_name": line.method_name,
                    "button_label": line.button_label,
                }
            )
        
        return {"type": "ir.actions.act_window_close"}


class ApprovalDetectActionWizardLine(models.TransientModel):
    _name = "approval.detect.action.wizard.line"
    _description = "Detect Available Actions Wizard Line"

    wizard_id = fields.Many2one(
        "approval.detect.action.wizard",
        required=True,
        ondelete="cascade",
    )
    is_selected = fields.Boolean(string="Select")
    method_name = fields.Char(string="Method Name")
    button_label = fields.Char(string="Button Label")

