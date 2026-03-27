# Copyright 2026 Deni Labs
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = ["sale.order", "approval.mixin"]

    # ------------------------------------------------------------------
    # Gated actions — delegate to the configurable gate mechanism
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Gate 'Confirm' if configured in the approval workflow."""
        self._check_approval_gate("action_confirm")
        return super().action_confirm()

    def action_cancel(self):
        """Gate 'Cancel' if configured in the approval workflow."""
        self._check_approval_gate("action_cancel")
        return super().action_cancel()

    def action_draft(self):
        """Reset approval state when order is moved back to quotation."""
        result = super().action_draft()
        self.filtered(lambda o: o.approval_state != "draft").write(
            {"approval_state": "draft"}
        )
        return result
