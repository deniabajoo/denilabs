# -*- coding: utf-8 -*-
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class ApprovalDashboardController(http.Controller):

    @http.route('/gifari/approval/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, **kw):
        """Return all dashboard data in a single RPC call."""
        env = request.env
        today_start = fields.Date.today()

        # ── Sale Approval KPIs ───────────────────────────
        sale_pending = env['sale.order'].sudo().search_count([
            ('approval_state', '=', 'pending'),
            ('company_id', 'in', env.companies.ids),
        ])
        sale_approved_today = env['sale.discount.approval.log'].sudo().search_count([
            ('action', '=', 'approve'),
            ('company_id', 'in', env.companies.ids),
            ('timestamp', '>=', fields.Datetime.to_string(
                fields.Datetime.start_of(fields.Datetime.now(), 'day')
            )),
        ])
        sale_rejected_today = env['sale.discount.approval.log'].sudo().search_count([
            ('action', '=', 'reject'),
            ('company_id', 'in', env.companies.ids),
            ('timestamp', '>=', fields.Datetime.to_string(
                fields.Datetime.start_of(fields.Datetime.now(), 'day')
            )),
        ])

        # ── Purchase Approval KPIs ───────────────────────
        purchase_pending = env['purchase.order'].sudo().search_count([
            ('approval_state', '=', 'pending'),
            ('company_id', 'in', env.companies.ids),
        ])
        purchase_approved_today = env['purchase.approval.log'].sudo().search_count([
            ('action', '=', 'approve'),
            ('company_id', 'in', env.companies.ids),
            ('timestamp', '>=', fields.Datetime.to_string(
                fields.Datetime.start_of(fields.Datetime.now(), 'day')
            )),
        ])
        purchase_rejected_today = env['purchase.approval.log'].sudo().search_count([
            ('action', '=', 'reject'),
            ('company_id', 'in', env.companies.ids),
            ('timestamp', '>=', fields.Datetime.to_string(
                fields.Datetime.start_of(fields.Datetime.now(), 'day')
            )),
        ])

        # ── Pending Sale Orders (list) ───────────────────
        pending_sales = env['sale.order'].sudo().search_read(
            [('approval_state', '=', 'pending'), ('company_id', 'in', env.companies.ids)],
            fields=[
                'name', 'partner_id', 'amount_total',
                'effective_max_discount', 'current_approval_level_id',
                'days_pending', 'submitted_by', 'user_id',
                'currency_id',
            ],
            order='id desc',
            limit=50,
        )

        # ── Pending Purchase Orders (list) ───────────────
        pending_purchases = env['purchase.order'].sudo().search_read(
            [('approval_state', '=', 'pending'), ('company_id', 'in', env.companies.ids)],
            fields=[
                'name', 'partner_id', 'amount_untaxed',
                'amount_total', 'current_approval_level_id',
                'days_pending', 'submitted_by', 'user_id',
                'currency_id',
            ],
            order='id desc',
            limit=50,
        )

        # ── Recent Activity Log ──────────────────────────
        recent_sale_logs = env['sale.discount.approval.log'].sudo().search_read(
            [('company_id', 'in', env.companies.ids)],
            fields=[
                'order_id', 'user_id', 'action', 'timestamp',
                'level_id', 'notes',
            ],
            order='create_date desc',
            limit=10,
        )
        recent_purchase_logs = env['purchase.approval.log'].sudo().search_read(
            [('company_id', 'in', env.companies.ids)],
            fields=[
                'order_id', 'user_id', 'action', 'timestamp',
                'level_id', 'notes',
            ],
            order='create_date desc',
            limit=10,
        )

        return {
            'kpi': {
                'sale_pending': sale_pending,
                'sale_approved_today': sale_approved_today,
                'sale_rejected_today': sale_rejected_today,
                'purchase_pending': purchase_pending,
                'purchase_approved_today': purchase_approved_today,
                'purchase_rejected_today': purchase_rejected_today,
                'total_pending': sale_pending + purchase_pending,
                'total_approved_today': sale_approved_today + purchase_approved_today,
                'total_rejected_today': sale_rejected_today + purchase_rejected_today,
            },
            'pending_sales': pending_sales,
            'pending_purchases': pending_purchases,
            'recent_sale_logs': recent_sale_logs,
            'recent_purchase_logs': recent_purchase_logs,
        }
