# Copyright 2026 Deni Labs
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval



class ApprovalWorkflowConfig(models.Model):
    """Master configuration that binds an approval workflow to an Odoo model.

    One config = one workflow.  Multiple configs can target the same model
    as long as their *domain* filters are mutually exclusive (evaluated in
    *sequence* order — first match wins).
    """

    _name = "approval.workflow.config"
    _description = "Approval Workflow Configuration"
    _order = "sequence asc, name asc"

    name = fields.Char(
        string="Name",
        required=True,
        index=True,
        translate=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Lower sequences are evaluated first when multiple configs "
        "target the same model.",
    )
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
        help="The Odoo model this workflow applies to.",
    )
    model_name = fields.Char(
        related="model_id.model",
        store=True,
        readonly=True,
        string="Technical Model Name",
    )
    domain = fields.Char(
        string="Filter Domain",
        default="[]",
        help=(
            "Optional Odoo domain to restrict which records this workflow "
            "applies to.  Leave as '[]' (or empty) to match all records of "
            "the selected model.  Example: [('amount_total', '>=', 1000)]"
        ),
    )
    stage_ids = fields.One2many(
        comodel_name="approval.workflow.stage",
        inverse_name="config_id",
        string="Approval Stages",
        copy=True,
    )
    stage_count = fields.Integer(
        compute="_compute_stage_count",
        string="Stages",
        store=True,
    )
    gated_action_ids = fields.One2many(
        comodel_name="approval.gated.action",
        inverse_name="config_id",
        string="Gated Actions",
        copy=True,
        help=(
            "Define which button actions on the target model will be blocked "
            "until approval is granted. Each row maps a method name "
            "(e.g. 'action_confirm') to the approval states that trigger the block."
        ),
    )
    escalation_days = fields.Integer(
        string="Escalation After (Days)",
        default=7,
        help=(
            "Number of calendar days after which a still-pending approval "
            "request is considered overdue and the escalation user is notified."
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )
    note = fields.Html(string="Internal Notes")
    request_count = fields.Integer(
        compute="_compute_request_count",
        string="Requests",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("stage_ids")
    def _compute_stage_count(self):
        for config in self:
            config.stage_count = len(config.stage_ids)

    def _compute_request_count(self):
        Request = self.env["approval.request"]
        for config in self:
            config.request_count = Request.search_count(
                [("config_id", "=", config.id)]
            )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains("domain")
    def _check_domain(self):
        for config in self:
            if config.domain:
                try:
                    safe_eval(config.domain)
                except Exception as exc:
                    raise ValidationError(
                        _("Invalid domain expression: %s") % str(exc)
                    ) from exc

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_view_requests(self):
        """Smart button: open approval requests for this configuration."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Requests — %s") % self.name,
            "res_model": "approval.request",
            "view_mode": "kanban,list,form",
            "domain": [("config_id", "=", self.id)],
            "context": {"default_config_id": self.id},
        }

    def action_detect_actions(self):
        """Open the Detect Available Actions Wizard."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Detect Available Actions"),
            "res_model": "approval.detect.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"config_id": self.id},
        }

    @api.model
    def _apply_dynamic_patches(self):
        """Apply monkey patches for all active gated actions. Called on _register_hook and config updates."""
        try:
            self.env.cr.execute("SELECT id FROM approval_workflow_config WHERE active = true")
            active_ids = [r[0] for r in self.env.cr.fetchall()]
        except Exception:
            return

        if not active_ids:
            return

        configs = self.browse(active_ids)
        for config in configs:
            if not config.model_id:
                continue

            model_name = config.model_id.model
            ModelClass = self.env.registry.get(model_name)
            if not ModelClass:
                continue

            for action in config.gated_action_ids:
                method_name = action.method_name
                orig_method = getattr(ModelClass, method_name, None)
                
                if orig_method and callable(orig_method) and not getattr(orig_method, '_is_dynamic_gated', False):
                    
                    def make_wrapper(orig_fn, act_name, m_name):
                        def wrapper(record_self, *args, **kwargs):
                            # Zero-Code gate validation!
                            Config = record_self.env['approval.workflow.config'].sudo()
                            cfg = Config.search([('model_id.model', '=', m_name), ('active', '=', True)], limit=1)
                            if cfg:
                                for record in record_self:
                                    try:
                                        state = getattr(record, 'approval_state')
                                    except AttributeError:
                                        state = getattr(record, 'x_approval_state', 'draft')
                                    state = state or 'draft'
                                    
                                    gated = cfg.gated_action_ids.filtered(lambda a: a.method_name == act_name)
                                    if gated:
                                        blocked_states = [s.strip() for s in (gated[0].block_on_states or '').split(',')]
                                        if state in blocked_states:
                                            raise UserError(
                                                gated[0].error_message or 
                                                _("Aksi '%s' memerlukan persetujuan terlebih dahulu. "
                                                  "Gunakan tombol 'Submit for Approval'.") % gated[0].button_label
                                            )
                            return orig_fn(record_self, *args, **kwargs)
                        wrapper._is_dynamic_gated = True
                        return wrapper
                    
                    patched_fn = make_wrapper(orig_method, method_name, model_name)
                    setattr(ModelClass, method_name, patched_fn)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._apply_dynamic_patches()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._apply_dynamic_patches()
        return res

    @api.model
    def _register_hook(self):
        super()._register_hook()
        self._apply_dynamic_patches()

    def action_generate_dynamic_integration(self):
        """Zero-Code Integration Engine: Generate Fields & UI dynamically."""
        self.ensure_one()
        model_name = self.model_id.model
        ir_model = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
        
        # 1. Inject Field: x_approval_state
        state_field = self.env['ir.model.fields'].search([
            ('name', 'in', ['approval_state', 'x_approval_state']), 
            ('model_id', '=', ir_model.id)
        ])
        if not state_field:
            self.env['ir.model.fields'].create({
                'name': 'x_approval_state',
                'field_description': 'Approval Status',
                'model_id': ir_model.id,
                'ttype': 'selection',
                'selection': "[('draft', 'Draft'), ('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('returned', 'Returned')]",
                'copied': False,
            })
            
        # 2. Inject XML View
        # Sangat Penting: Ambil Base View yang sebenarnya (inherit_id = False) agar struktur utama ketemu.
        base_view = self.env['ir.ui.view'].search([
            ('model', '=', model_name), 
            ('type', '=', 'form'),
            ('inherit_id', '=', False)
        ], order='priority, id', limit=1)
        
        if base_view:
            dynamic_view_name = f"{model_name}.dynamic.approval.injection"
            existing_view = self.env['ir.ui.view'].search([('name', '=', dynamic_view_name)])
            
            # Cek kombinasi arch di form view untuk melihat apakah button_box ada
            import xml.etree.ElementTree as ET
            combined_arch = self.env[model_name].get_view(view_id=base_view.id, view_type='form')['arch']
            has_button_box = 'name="button_box"' in combined_arch
            
            button_box_xpath = """
                <xpath expr="//div[@name='button_box']" position="inside">
                    <button name="dl_approval_flow.action_dynamic_smart_button" type="action" class="oe_stat_button" icon="fa-tasks" invisible="x_approval_state in (False, 'draft')">
                        <div class="o_stat_info">
                            <span class="o_stat_text">Approvals</span>
                        </div>
                    </button>
                </xpath>
            """ if has_button_box else """
                <xpath expr="//sheet" position="before">
                    <div name="button_box" class="oe_button_box">
                        <button name="dl_approval_flow.action_dynamic_smart_button" type="action" class="oe_stat_button" icon="fa-tasks" invisible="x_approval_state in (False, 'draft')">
                            <div class="o_stat_info">
                                <span class="o_stat_text">Approvals</span>
                            </div>
                        </button>
                    </div>
                </xpath>
            """
            
            xml_arch = f"""
            <data>
                <xpath expr="//header" position="inside">
                    <field name="x_approval_state" invisible="1"/>
                    <button name="dl_approval_flow.action_dynamic_submit_wizard" 
                            type="action" 
                            string="Submit for Approval" 
                            class="btn-primary" 
                            context="{{'default_model_name': '{model_name}', 'default_res_id': id, 'default_config_id': {self.id}}}"
                            invisible="x_approval_state not in (False, 'draft', 'returned')"/>
                </xpath>
                {button_box_xpath}
                <xpath expr="//sheet" position="inside">
                    <widget name="web_ribbon" title="Pending Approval" bg_color="text-bg-warning" invisible="x_approval_state != 'pending_approval'"/>
                    <widget name="web_ribbon" title="Approved" bg_color="text-bg-success" invisible="x_approval_state != 'approved'"/>
                    <widget name="web_ribbon" title="Rejected" bg_color="text-bg-danger" invisible="x_approval_state != 'rejected'"/>
                    <widget name="web_ribbon" title="Returned" bg_color="text-bg-warning" invisible="x_approval_state != 'returned'"/>
                </xpath>
            </data>
            """

            try:
                if existing_view:
                    existing_view.write({'arch': xml_arch})
                else:
                    self.env['ir.ui.view'].create({
                        'name': dynamic_view_name,
                        'type': 'form',
                        'model': model_name,
                        'inherit_id': base_view.id,
                        'arch': xml_arch,
                    })
            except Exception as e:
                raise UserError(_("Peringatan UI: Layout XML Form (%s) tidak memiliki <header> atau <sheet> untuk injeksi UI. Pesan asli: %s") % (base_view.name, str(e)))



        # Signal web client to restart
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)
