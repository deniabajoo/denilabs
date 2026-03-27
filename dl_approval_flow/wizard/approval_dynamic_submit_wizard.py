# Copyright 2026 Deni Labs
from odoo import _, fields, models
from odoo.exceptions import UserError


class ApprovalDynamicSubmitWizard(models.TransientModel):
    _name = "approval.dynamic.submit.wizard"
    _description = "Dynamic Zero-Code Submit Wizard"

    model_name = fields.Char(string="Model", required=True)
    res_id = fields.Integer(string="Record ID", required=True)
    config_id = fields.Many2one("approval.workflow.config", string="Config", required=True)
    
    def action_confirm_submit(self):
        """Universal submit trigger for models without Python integration."""
        self.ensure_one()
        
        # 1. Fetch record
        record = self.env[self.model_name].browse(self.res_id)
        if not record.exists():
            raise UserError(_("Record not found."))
            
        # 2. Check if there's already an ongoing request
        existing_req = self.env["approval.request"].search([
            ("res_model", "=", self.model_name),
            ("res_id", "=", self.res_id),
            ("state", "=", "pending_approval")
        ])
        if existing_req:
            raise UserError(_("Ada request persetujuan yang sedang berjalan untuk dokumen ini."))
            
        # 3. Prevent submitting if already approved
        state_field = f"x_approval_state_{self.config_id.id}"
        if not hasattr(record, state_field):
            state_field = "approval_state" if hasattr(record, "approval_state") else "x_approval_state"
            
        if getattr(record, state_field, "draft") not in ("draft", "returned", False):
            raise UserError(_("Dokumen ini tidak dalam status Draft atau Returned (untuk workflow ini), sehingga tidak bisa disubmit."))

        # 4. Create Approval Request
        Request = self.env["approval.request"].sudo()
        Request.create({
            "config_id": self.config_id.id,
            "res_model": self.model_name,
            "res_id": self.res_id,
            "requester_id": self.env.user.id,
        })
        
        # 5. Update custom field back to pending
        if hasattr(record, state_field) and state_field.startswith("x_"):
            record.write({state_field: "pending_approval"})
            
        return {"type": "ir.actions.act_window_close"}
