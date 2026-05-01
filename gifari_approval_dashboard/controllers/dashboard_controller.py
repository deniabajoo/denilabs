# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class GifariApprovalDashboardController(http.Controller):

    @http.route('/gifari/approval/dashboard/data', auth='user', type='json', methods=['POST'])
    def get_dashboard_data(self, date_range='7', module_filter='all', **kw):
        """
        Return aggregated approval data for the dashboard.
        :param date_range: Number of days to look back (string: '7', '30', '90')
        :param module_filter: 'all', 'sale', or 'purchase'
        """
        env = request.env
        days = int(date_range)
        date_from = fields.Datetime.now() - timedelta(days=days)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)

        result = {}

        # ── KPI Counts ──────────────────────────────────────────────────
        so_pending = po_pending = 0
        so_approved_today = po_approved_today = 0
        so_rejected_today = po_rejected_today = 0

        if module_filter in ('all', 'sale'):
            SaleOrder = env['sale.order']
            so_pending = SaleOrder.search_count([('approval_state', '=', 'pending')])
            so_approved_today = SaleOrder.search_count([
                ('approval_state', '=', 'approved'),
                ('approval_date', '>=', today_start),
            ])
            so_rejected_today = SaleOrder.search_count([
                ('approval_state', '=', 'rejected'),
                ('approval_date', '>=', today_start),
            ])

        if module_filter in ('all', 'purchase'):
            PO = env['purchase.order']
            po_pending = PO.search_count([('approval_state', '=', 'pending')])
            po_approved_today = PO.search_count([
                ('approval_state', '=', 'approved'),
                ('approval_date', '>=', today_start),
            ])
            po_rejected_today = PO.search_count([
                ('approval_state', '=', 'rejected'),
                ('approval_date', '>=', today_start),
            ])

        result['kpi'] = {
            'so_pending': so_pending,
            'po_pending': po_pending,
            'approved_today': so_approved_today + po_approved_today,
            'rejected_today': so_rejected_today + po_rejected_today,
            'total_pending': so_pending + po_pending,
        }

        # ── Trend Data (last N days) ────────────────────────────────────
        trend_labels = []
        trend_so_approved = []
        trend_po_approved = []
        trend_so_rejected = []
        trend_po_rejected = []

        for i in range(days - 1, -1, -1):
            day = datetime.utcnow().replace(hour=0, minute=0, second=0) - timedelta(days=i)
            day_end = day + timedelta(days=1)
            label = day.strftime('%d %b')
            trend_labels.append(label)

            if module_filter in ('all', 'sale'):
                so_app = env['sale.order'].search_count([
                    ('approval_state', '=', 'approved'),
                    ('approval_date', '>=', day),
                    ('approval_date', '<', day_end),
                ])
                so_rej = env['sale.order'].search_count([
                    ('approval_state', '=', 'rejected'),
                    ('approval_date', '>=', day),
                    ('approval_date', '<', day_end),
                ])
            else:
                so_app = so_rej = 0

            if module_filter in ('all', 'purchase'):
                po_app = env['purchase.order'].search_count([
                    ('approval_state', '=', 'approved'),
                    ('approval_date', '>=', day),
                    ('approval_date', '<', day_end),
                ])
                po_rej = env['purchase.order'].search_count([
                    ('approval_state', '=', 'rejected'),
                    ('approval_date', '>=', day),
                    ('approval_date', '<', day_end),
                ])
            else:
                po_app = po_rej = 0

            trend_so_approved.append(so_app)
            trend_po_approved.append(po_app)
            trend_so_rejected.append(so_rej)
            trend_po_rejected.append(po_rej)

        result['trend'] = {
            'labels': trend_labels,
            'so_approved': trend_so_approved,
            'po_approved': trend_po_approved,
            'so_rejected': trend_so_rejected,
            'po_rejected': trend_po_rejected,
        }

        # ── Top Discount Requests (pending, ranked by total_discount_amount) ──
        top_list = []

        if module_filter in ('all', 'sale'):
            so_pending_records = env['sale.order'].search(
                [('approval_state', '=', 'pending')],
                order='total_discount_amount desc',
                limit=10,
            )
            for order in so_pending_records:
                age_hours = (datetime.utcnow() - order.write_date).total_seconds() / 3600 if order.write_date else 0
                top_list.append({
                    'type': 'SO',
                    'id': order.id,
                    'name': order.name,
                    'partner': order.partner_id.name,
                    'salesperson': order.user_id.name or '',
                    'max_discount_percent': order.max_discount_percent,
                    'total_discount_amount': order.total_discount_amount,
                    'amount_total': order.amount_total,
                    'currency_symbol': order.currency_id.symbol,
                    'age_hours': round(age_hours, 1),
                    'write_date': order.write_date.strftime('%Y-%m-%d %H:%M') if order.write_date else '',
                })

        if module_filter in ('all', 'purchase'):
            po_pending_records = env['purchase.order'].search(
                [('approval_state', '=', 'pending')],
                order='total_discount_amount desc',
                limit=10,
            )
            for order in po_pending_records:
                age_hours = (datetime.utcnow() - order.write_date).total_seconds() / 3600 if order.write_date else 0
                top_list.append({
                    'type': 'PO',
                    'id': order.id,
                    'name': order.name,
                    'partner': order.partner_id.name,
                    'salesperson': order.user_id.name or '',
                    'max_discount_percent': order.max_discount_percent,
                    'total_discount_amount': order.total_discount_amount,
                    'amount_total': order.amount_total,
                    'currency_symbol': order.currency_id.symbol,
                    'age_hours': round(age_hours, 1),
                    'write_date': order.write_date.strftime('%Y-%m-%d %H:%M') if order.write_date else '',
                })

        # Sort combined list by discount amount descending
        top_list.sort(key=lambda x: x['total_discount_amount'], reverse=True)
        result['pending_list'] = top_list[:15]

        # Current user info
        result['user'] = {
            'name': request.env.user.name,
            'is_sale_approver': request.env.user in request.env.company.sale_approval_user_ids or
                                request.env.user.has_group('sales_team.group_sale_manager'),
            'is_purchase_approver': request.env.user in request.env.company.purchase_approval_user_ids or
                                    request.env.user.has_group('purchase.group_purchase_manager'),
        }

        return result

    @http.route('/gifari/approval/quick_action', auth='user', type='json', methods=['POST'])
    def quick_action(self, doc_type, doc_id, action, notes='', reason=''):
        """
        Quick approve/reject from dashboard.
        :param doc_type: 'sale' or 'purchase'
        :param doc_id: ID of the order
        :param action: 'approve' or 'reject'
        :param notes: Approval notes
        :param reason: Rejection reason
        """
        env = request.env
        try:
            if doc_type == 'sale':
                order = env['sale.order'].browse(int(doc_id))
                if action == 'approve':
                    order.action_approve(notes=notes)
                else:
                    order.action_reject(reason=reason)
            elif doc_type == 'purchase':
                order = env['purchase.order'].browse(int(doc_id))
                if action == 'approve':
                    order.action_approve(notes=notes)
                else:
                    order.action_reject(reason=reason)
            return {'success': True, 'message': f'Order {action}d successfully.'}
        except Exception as e:
            _logger.exception('Quick approval action failed: %s', str(e))
            return {'success': False, 'error': str(e)}
