# -*- coding: utf-8 -*-
"""
Post-init hook for gifari_demo_data v2.0.

Generates 6 months of realistic transactional demo data including:
- Purchase Orders (build stock + aging)
- Sales Orders (discount variations + approval workflow)
- Delegation & SLA breach samples
- SPK-SAW scoring computation
"""
import logging
import random
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, api, SUPERUSER_ID

_logger = logging.getLogger(__name__)
random.seed(42)

MONTHS_BACK = 6

DISCOUNT_TIERS = [
    (0.0, 0.45), (5.0, 0.15), (12.0, 0.12), (15.0, 0.08),
    (22.0, 0.07), (28.0, 0.05), (38.0, 0.04), (45.0, 0.04),
]
PO_AMOUNT_PROFILES = [
    ('small', 0.35), ('medium', 0.30), ('large', 0.20), ('enterprise', 0.15),
]
SO_PER_MONTH_RANGE = (30, 60)
PO_PER_MONTH_RANGE = (15, 30)


def post_init_hook(env):
    generate_demo_data(env, check_demo_mode=True, months_back=MONTHS_BACK)


def generate_demo_data(env, check_demo_mode=True, months_back=6,
                       generate_so=True, generate_po=True,
                       generate_spk=True, generate_delegation=True,
                       generate_sla_breach=True):
    _logger.info("═══ gifari_demo_data v2.0: Starting demo data generation ═══")

    if check_demo_mode:
        cr = env.cr
        cr.execute("SELECT demo FROM ir_module_module WHERE name = 'gifari_demo_data'")
        result = cr.fetchone()
        if not result or not result[0]:
            _logger.info("Demo mode not active — skipping.")
            return

    company = env['res.company'].browse(1)
    _setup_company_currency(env, company)

    refs = _gather_references(env)
    if not refs:
        _logger.warning("Could not gather references — aborting.")
        return

    today = fields.Date.today()

    for month_offset in range(months_back, 0, -1):
        month_start = today - relativedelta(months=month_offset, day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        _logger.info("Generating data for: %s", month_start.strftime('%B %Y'))
        is_last_month = (month_offset == 1)

        if generate_po:
            _generate_purchase_orders(env, refs, company, month_start, month_end, is_last_month)
        if generate_so:
            _generate_sale_orders(env, refs, company, month_start, month_end, is_last_month)

    if generate_delegation and generate_so:
        _generate_delegation_samples(env, refs, company, today)

    if generate_sla_breach and generate_so:
        _generate_sla_breach_samples(env, refs, company, today)

    _backdate_records(env)

    if generate_spk:
        _compute_spk_scores(env, company)

    _logger.info("═══ gifari_demo_data v2.0: Demo data generation COMPLETE ═══")


def _setup_company_currency(env, company):
    idr_currency = env.ref('base.IDR', raise_if_not_found=False)
    if idr_currency and not idr_currency.active:
        idr_currency.active = True
    company.write({
        'name': 'PT Indopora',
        'street': 'Jl. Sudirman Kav. 50',
        'city': 'Jakarta Selatan',
        'phone': '021-5551234',
        'email': 'info@indopora.co.id',
        'website': 'www.indopora.co.id',
        'currency_id': idr_currency.id if idr_currency else company.currency_id.id,
    })


def _gather_references(env):
    module = 'gifari_demo_data'
    try:
        refs = {
            'sales_staff': [
                env.ref(f'{module}.demo_sales_staff_1'),
                env.ref(f'{module}.demo_sales_staff_2'),
                env.ref(f'{module}.demo_sales_staff_3'),
            ],
            'sales_manager': env.ref(f'{module}.demo_sales_manager'),
            'sales_director': env.ref(f'{module}.demo_sales_director'),
            'purchase_staff': [
                env.ref(f'{module}.demo_purchase_staff_1'),
                env.ref(f'{module}.demo_purchase_staff_2'),
            ],
            'purchase_manager': env.ref(f'{module}.demo_purchase_manager'),
            'finance_director': env.ref(f'{module}.demo_finance_director'),
            'customers': env['res.partner'].search([
                ('customer_rank', '>', 0),
                ('id', 'in', [
                    env.ref(f'{module}.partner_customer_{i:02d}').id
                    for i in range(1, 26)
                ]),
            ]),
            'vendors': env['res.partner'].search([
                ('supplier_rank', '>', 0),
                ('id', 'in', [
                    env.ref(f'{module}.partner_vendor_{i:02d}').id
                    for i in range(1, 19)
                ]),
            ]),
        }
        demo_codes = ['STL-', 'CMT-', 'PIP-', 'HVY-', 'ELC-',
                       'K3-', 'CHM-', 'FWK-', 'FIN-', 'CON-']
        all_products = env['product.product'].search([
            ('product_tmpl_id.default_code', '!=', False),
            ('product_tmpl_id.default_code', 'like', '%-%'),
        ])
        refs['products'] = all_products.filtered(
            lambda p: any(p.default_code and p.default_code.startswith(c) for c in demo_codes))
        if not refs['products']:
            _logger.warning("No demo products found!")
            return None
        _logger.info("References: %d customers, %d vendors, %d products",
                     len(refs['customers']), len(refs['vendors']), len(refs['products']))
        return refs
    except Exception as e:
        _logger.error("Error gathering references: %s", e)
        return None


# ══════════════════════════════════════════════════════
# PURCHASE ORDER GENERATION
# ══════════════════════════════════════════════════════

def _generate_purchase_orders(env, refs, company, month_start, month_end, is_last_month):
    count = random.randint(*PO_PER_MONTH_RANGE)
    products = list(refs['products'])
    vendors = list(refs['vendors'])
    purchase_staff = refs['purchase_staff']

    for i in range(count):
        vendor = random.choice(vendors)
        staff = random.choice(purchase_staff)
        order_date = _random_date(month_start, month_end)
        profile = _weighted_choice(PO_AMOUNT_PROFILES)
        lines_data = _build_po_lines(products, profile)

        po = env['purchase.order'].sudo().create({
            'partner_id': vendor.id, 'company_id': company.id,
            'date_order': order_date, 'user_id': staff.id,
            'order_line': [(0, 0, l) for l in lines_data],
        })

        if is_last_month and i >= count - 3:
            _process_po_approval(env, refs, po, fate='pending' if i % 2 == 0 else 'rejected')
        elif profile == 'small':
            po.with_user(staff).button_confirm()
        else:
            po.with_user(staff).button_confirm()
            if po.approval_state == 'pending':
                _process_po_approval(env, refs, po, fate='approved')

        if po.state == 'purchase':
            for picking in po.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()


def _build_po_lines(products, profile):
    targets = {'small': (500_000, 4_500_000), 'medium': (5_000_000, 45_000_000),
               'large': (50_000_000, 190_000_000), 'enterprise': (200_000_000, 500_000_000)}
    target = random.randint(*targets.get(profile, (500_000, 4_500_000)))
    lines = []
    remaining = target
    selected = random.sample(products, min(random.randint(2, 8), len(products)))
    for prod in selected:
        if remaining <= 0:
            break
        price = prod.standard_price or 100000
        qty = random.randint(1, min(max(1, int(remaining / price)), 50))
        lines.append({
            'product_id': prod.id, 'product_qty': qty, 'price_unit': price,
            'name': prod.name, 'product_uom_id': prod.uom_id.id,
        })
        remaining -= price * qty
    return lines or [{'product_id': products[0].id, 'product_qty': 1,
                      'price_unit': products[0].standard_price or 100000,
                      'name': products[0].name, 'product_uom_id': products[0].uom_id.id}]


def _process_po_approval(env, refs, po, fate='approved'):
    if po.approval_state != 'pending':
        return
    if fate == 'rejected':
        approver = po.current_approval_level_id.approver_ids[:1]
        if approver:
            po.with_user(approver).action_reject_purchase(
                reason=random.choice([
                    "Harga terlalu tinggi, minta re-negosiasi.",
                    "Budget proyek belum disetujui.", "Vendor belum terverifikasi QC.",
                ]))
        return
    if fate == 'pending':
        return
    max_iter = 10
    it = 0
    while po.approval_state == 'pending' and it < max_iter:
        it += 1
        level = po.current_approval_level_id
        if not level:
            break
        for approver in level.approver_ids:
            if po.approval_state != 'pending':
                break
            try:
                po.with_user(approver).action_approve_purchase(notes="Approved.")
            except Exception:
                break


# ══════════════════════════════════════════════════════
# SALES ORDER GENERATION
# ══════════════════════════════════════════════════════

def _generate_sale_orders(env, refs, company, month_start, month_end, is_last_month):
    count = random.randint(*SO_PER_MONTH_RANGE)
    products = list(refs['products'])
    customers = list(refs['customers'])
    sales_staff = refs['sales_staff']

    for i in range(count):
        customer = random.choice(customers)
        staff = random.choice(sales_staff)
        order_date = _random_date(month_start, month_end)

        if is_last_month and i >= count - 5:
            disc_pct = random.uniform(15.0, 45.0)
        else:
            disc_pct = _weighted_choice_value(DISCOUNT_TIERS)

        selected = random.sample(products, min(random.randint(1, 6), len(products)))
        lines_data = [{'product_id': p.id, 'product_uom_qty': random.randint(1, 30),
                        'price_unit': p.list_price or 100000, 'discount': disc_pct,
                        'name': p.name} for p in selected]

        so = env['sale.order'].sudo().create({
            'partner_id': customer.id, 'company_id': company.id,
            'date_order': order_date, 'user_id': staff.id,
            'order_line': [(0, 0, l) for l in lines_data],
        })

        if is_last_month and i >= count - 5:
            if i % 3 == 0:
                continue
            elif i % 3 == 1:
                so.with_user(staff).action_confirm()
            else:
                so.with_user(staff).action_confirm()
                if so.approval_state == 'pending':
                    _process_so_approval(env, refs, so, fate='rejected')
        else:
            so.with_user(staff).action_confirm()
            if so.approval_state == 'pending':
                fate = 'approved' if random.random() < 0.85 else 'rejected'
                _process_so_approval(env, refs, so, fate=fate)

        if so.state == 'sale':
            for picking in so.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()


def _process_so_approval(env, refs, so, fate='approved'):
    if so.approval_state != 'pending':
        return
    if fate == 'rejected':
        approver = so.current_approval_level_id.approver_ids[:1]
        if approver:
            so.with_user(approver).action_reject_discount(
                reason=random.choice([
                    "Diskon terlalu besar, margin tipis.",
                    "Tidak sesuai kebijakan harga.", "Harga di bawah HPP.",
                ]))
        return
    if fate == 'pending':
        return
    max_iter = 10
    it = 0
    while so.approval_state == 'pending' and it < max_iter:
        it += 1
        level = so.current_approval_level_id
        if not level:
            break
        use_counter = random.random() < 0.10 and so.effective_max_discount > 15
        for approver in level.approver_ids:
            if so.approval_state != 'pending':
                break
            try:
                if use_counter:
                    counter_pct = so.effective_max_discount * random.uniform(0.6, 0.9)
                    so.with_user(approver).action_approve_discount(
                        notes="Counter-offer: diskon disesuaikan.", counter_offer_percent=counter_pct)
                else:
                    so.with_user(approver).action_approve_discount(
                        notes=random.choice(["Approved. Margin aman.", "OK, harga wajar.", "Approved."]))
            except Exception:
                break


# ══════════════════════════════════════════════════════
# DELEGATION SAMPLES
# ══════════════════════════════════════════════════════

def _generate_delegation_samples(env, refs, company, today):
    """Generate 3 SO with delegation workflow for demo."""
    _logger.info("Generating delegation sample SOs...")
    products = list(refs['products'])
    customers = list(refs['customers'])
    sales_staff = refs['sales_staff']
    manager = refs['sales_manager']
    director = refs['sales_director']

    delegation_scenarios = [
        {'disc': 15.0, 'delegator': manager, 'delegate_to': director,
         'notes': 'Saya sedang dinas luar, tolong di-handle.'},
        {'disc': 22.0, 'delegator': director, 'delegate_to': manager,
         'notes': 'Saya sedang cuti, mohon dibantu approve.'},
        {'disc': 18.0, 'delegator': manager, 'delegate_to': sales_staff[0],
         'notes': 'Delegasi ke senior staff untuk review.'},
    ]

    for scenario in delegation_scenarios:
        try:
            staff = random.choice(sales_staff)
            selected = random.sample(products, min(3, len(products)))
            lines = [{'product_id': p.id, 'product_uom_qty': random.randint(2, 10),
                       'price_unit': p.list_price or 100000, 'discount': scenario['disc'],
                       'name': p.name} for p in selected]

            so = env['sale.order'].sudo().create({
                'partner_id': random.choice(customers).id, 'company_id': company.id,
                'date_order': today - timedelta(days=random.randint(1, 5)),
                'user_id': staff.id,
                'order_line': [(0, 0, l) for l in lines],
            })
            so.with_user(staff).action_confirm()

            if so.approval_state == 'pending':
                level = so.current_approval_level_id
                if level and level.can_delegate:
                    delegator = scenario['delegator']
                    if delegator in level.approver_ids:
                        so.with_user(delegator).action_delegate_approval(
                            delegate_to_user_id=scenario['delegate_to'].id,
                            notes=scenario['notes'])
                        _logger.info("Delegation sample: %s → delegated by %s to %s",
                                     so.name, delegator.name, scenario['delegate_to'].name)
        except Exception as e:
            _logger.warning("Delegation sample error: %s", e)


# ══════════════════════════════════════════════════════
# SLA BREACH SAMPLES
# ══════════════════════════════════════════════════════

def _generate_sla_breach_samples(env, refs, company, today):
    """Generate 2 SO with expired SLA deadlines for demo."""
    _logger.info("Generating SLA breach sample SOs...")
    products = list(refs['products'])
    customers = list(refs['customers'])
    sales_staff = refs['sales_staff']

    breach_scenarios = [
        {'disc': 25.0, 'days_ago': 3, 'label': 'SLA breach 3 hari lalu'},
        {'disc': 40.0, 'days_ago': 5, 'label': 'SLA breach 5 hari lalu'},
    ]

    for scenario in breach_scenarios:
        try:
            staff = random.choice(sales_staff)
            selected = random.sample(products, min(4, len(products)))
            lines = [{'product_id': p.id, 'product_uom_qty': random.randint(3, 15),
                       'price_unit': p.list_price or 100000, 'discount': scenario['disc'],
                       'name': p.name} for p in selected]

            order_date = today - timedelta(days=scenario['days_ago'])
            so = env['sale.order'].sudo().create({
                'partner_id': random.choice(customers).id, 'company_id': company.id,
                'date_order': order_date, 'user_id': staff.id,
                'order_line': [(0, 0, l) for l in lines],
            })
            so.with_user(staff).action_confirm()

            if so.approval_state == 'pending' and so.approval_deadline:
                expired_deadline = fields.Datetime.now() - timedelta(hours=scenario['days_ago'] * 24)
                so.sudo().write({'approval_deadline': expired_deadline})
                _logger.info("SLA breach sample: %s — deadline set to %s (%s)",
                             so.name, expired_deadline, scenario['label'])
        except Exception as e:
            _logger.warning("SLA breach sample error: %s", e)


# ══════════════════════════════════════════════════════
# SPK-SAW SCORING
# ══════════════════════════════════════════════════════

def _compute_spk_scores(env, company):
    """Trigger SAW scoring computation after all data is generated."""
    _logger.info("Computing SPK-SAW scores for all products...")
    try:
        SpkScore = env['spk.saw.product.score']
        SpkScore._compute_all_scores(company)
        count = SpkScore.search_count([('company_id', '=', company.id)])
        _logger.info("SPK-SAW scoring complete: %d product scores generated.", count)
    except Exception as e:
        _logger.error("SPK-SAW scoring error: %s", e)


# ══════════════════════════════════════════════════════
# BACKDATE & UTILITY
# ══════════════════════════════════════════════════════

def _backdate_records(env):
    cr = env.cr
    _logger.info("Backdating records...")
    cr.execute("""
        UPDATE sale_order SET create_date = date_order
        WHERE create_date::date = CURRENT_DATE AND date_order < CURRENT_DATE
    """)
    cr.execute("""
        UPDATE purchase_order SET create_date = date_order
        WHERE create_date::date = CURRENT_DATE AND date_order < CURRENT_DATE
    """)
    cr.execute("""
        UPDATE sale_discount_approval_log SET create_date = timestamp
        WHERE create_date::date = CURRENT_DATE AND timestamp < CURRENT_DATE::timestamp
    """)
    try:
        cr.execute("""
            UPDATE purchase_approval_log SET create_date = timestamp
            WHERE create_date::date = CURRENT_DATE AND timestamp < CURRENT_DATE::timestamp
        """)
    except Exception:
        pass
    _logger.info("Backdating complete.")


def _random_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))


def _weighted_choice(choices):
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def _weighted_choice_value(choices):
    base = _weighted_choice(choices)
    return round(base + random.uniform(-2, 2), 1) if base > 0 else 0.0
