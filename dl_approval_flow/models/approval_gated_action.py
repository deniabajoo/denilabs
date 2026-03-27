# Copyright 2026 Deni Labs
from odoo import _, api, fields, models


class ApprovalGatedAction(models.Model):
    """Defines which Python method (button action) on a model is gated
    behind approval. One record per method per workflow configuration.

    When ``approval_state`` of the document is in ``block_on_states`` and
    the config's ``_check_approval_gate(method_name)`` is called, a
    :class:`~odoo.exceptions.UserError` is raised preventing the action.
    """

    _name = "approval.gated.action"
    _description = "Approval Gated Action"
    _order = "config_id, sequence asc"

    config_id = fields.Many2one(
        comodel_name="approval.workflow.config",
        string="Workflow Configuration",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    method_name = fields.Char(
        string="Method Name",
        required=True,
        help=(
            "The exact Python method name to gate, e.g. 'action_confirm', "
            "'action_cancel', 'button_confirm'.  This must match the method "
            "defined on the model chosen in the workflow configuration."
        ),
    )
    button_label = fields.Char(
        string="Button Label",
        help=(
            "Human-readable label shown in error messages, "
            "e.g. 'Confirm', 'Cancel'.  Defaults to method_name if blank."
        ),
    )
    block_on_states = fields.Char(
        string="Block On Approval States",
        default="draft,returned,pending_approval,rejected",
        required=True,
        help=(
            "Comma-separated approval states in which this action is blocked. "
            "Allowed values: draft, returned, pending_approval, rejected, approved.\n"
            "Default blocks everything except 'approved'."
        ),
    )
    error_message = fields.Char(
        string="Custom Error Message",
        help=(
            "Optional custom message shown when the action is blocked. "
            "Leave empty to use the default message."
        ),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_blocked_states(self):
        """Return the list of blocked approval states as a Python list."""
        self.ensure_one()
        return [s.strip() for s in (self.block_on_states or "").split(",") if s.strip()]

    def _get_display_label(self):
        """Return a display label for this gate (button_label or method_name)."""
        self.ensure_one()
        return self.button_label or self.method_name
