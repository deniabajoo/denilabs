# -*- coding: utf-8 -*-
"""
Post-init hook for gifari_demo_data.

Generates 6 months of realistic transactional demo data:
- Purchase Orders (to build stock)
- Sales Orders (consuming stock with discount variations)
- Various approval statuses (approved, pending, rejected)
- Backdated timestamps for realism
"""
import logging
import random
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Reproducible randomness
random.seed(42)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

MONTHS_BACK = 6

# Discount tiers for sales (probability weights)
DISCOUNT_TIERS = [
    (0.0, 0.45),    # 45% chance: no discount → no approval
    (5.0, 0.15),    # 15% chance: 5% disc → no approval
    (12.0, 0.12),   # 12% chance: 12% disc → L1
    (15.0, 0.08),   # 8% chance: 15% disc → L1
    (22.0, 0.07),   # 7% chance: 22% disc → L2
    (28.0, 0.05),   # 5% chance: 28% disc → L2
    (38.0, 0.04),   # 4% chance: 38% disc → L3
    (45.0, 0.04),   # 4% chance: 45% disc → L3
]

# Amount tiers for purchases (min amount → probability weight)
PO_AMOUNT_PROFILES = [
    ('small', 0.35),      # < 5M → no approval
    ('medium', 0.30),     # 5M-50M → L1
    ('large', 0.20),      # 50M-200M → L2
    ('enterprise', 0.15), # > 200M → L3
]

SO_PER_MONTH_RANGE = (30, 60)
PO_PER_MONTH_RANGE = (15, 30)


def post_init_hook(env):
    """Main entry point — generate demo transactions."""
    generate_demo_data(env, check_demo_mode=True, months_back=MONTHS_BACK)

def generate_demo_data(env, check_demo_mode=True, months_back=6):
    """Core logic to generate demo data."""
    _logger.info("═══ gifari_demo_data: Starting demo data generation ═══")

    if check_demo_mode:
        cr = env.cr
        cr.execute("""
            SELECT demo FROM ir_module_module WHERE name = 'gifari_demo_data'
        """)
        result = cr.fetchone()
        if not result or not result[0]:
            _logger.info("Demo mode not active — skipping transaction generation.")
            return

    company = env['res.company'].browse(1)
    
    # Update Company Name and Currency to IDR
    idr_currency = env.ref('base.IDR')
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

    # Gather references
    refs = _gather_references(env)
    if not refs:
        _logger.warning("Could not gather all references — aborting.")
        return

    today = fields.Date.today()

    for month_offset in range(months_back, 0, -1):
        month_start = today - relativedelta(months=month_offset, day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        _logger.info("Generating data for: %s", month_start.strftime('%B %Y'))

        is_last_month = (month_offset == 1)

        # Phase 1: Purchase Orders (build stock first)
        _generate_purchase_orders(env, refs, company, month_start, month_end, is_last_month)

        # Phase 2: Sales Orders
        _generate_sale_orders(env, refs, company, month_start, month_end, is_last_month)

    # Phase 3: Backdate create_date for realism
    _backdate_records(env)

    _logger.info("═══ gifari_demo_data: Demo data generation COMPLETE ═══")


def _gather_references(env):
    """Collect all XML IDs needed for generation."""
    module = 'gifari_demo_data'
    try:
        refs = {
            # Users
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
            # Partners
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

        # Products — all from this module
        all_products = env['product.product'].search([
            ('product_tmpl_id.default_code', '!=', False),
            ('product_tmpl_id.default_code', 'like', '%-%'),
        ])
        # Filter to our demo products by code prefix
        demo_codes = [
            'STL-', 'CMT-', 'PIP-', 'HVY-', 'ELC-',
            'K3-', 'CHM-', 'FWK-', 'FIN-', 'CON-',
        ]
        refs['products'] = all_products.filtered(
            lambda p: any(p.default_code and p.default_code.startswith(c) for c in demo_codes)
        )

        if not refs['products']:
            _logger.warning("No demo products found!")
            return None

        _logger.info(
            "References gathered: %d customers, %d vendors, %d products",
            len(refs['customers']), len(refs['vendors']), len(refs['products']),
        )
        return refs

    except Exception as e:
        _logger.error("Error gathering references: %s", e)
        return None


# ══════════════════════════════════════════════════════
# PURCHASE ORDER GENERATION
# ══════════════════════════════════════════════════════

def _generate_purchase_orders(env, refs, company, month_start, month_end, is_last_month):
    """Generate POs for one month."""
    count = random.randint(*PO_PER_MONTH_RANGE)
    products = list(refs['products'])
    vendors = list(refs['vendors'])
    purchase_staff = refs['purchase_staff']

    for i in range(count):
        vendor = random.choice(vendors)
        staff = random.choice(purchase_staff)
        order_date = _random_date(month_start, month_end)

        # Determine amount profile
        profile = _weighted_choice(PO_AMOUNT_PROFILES)

        # Pick products and quantities to match target amount
        lines_data = _build_po_lines(products, profile)

        po_vals = {
            'partner_id': vendor.id,
            'company_id': company.id,
            'date_order': order_date,
            'user_id': staff.id,
            'order_line': [(0, 0, line) for line in lines_data],
        }

        po = env['purchase.order'].sudo().create(po_vals)
        _logger.debug("Created PO %s (%s) — amount: %s", po.name, profile, po.amount_untaxed)

        # Decide fate
        if is_last_month and i >= count - 3:
            # Last month: leave some pending/rejected
            _process_po_approval(env, refs, po, fate='pending' if i % 2 == 0 else 'rejected')
        elif profile == 'small':
            # No approval needed — confirm directly
            po.with_user(staff).button_confirm()
        else:
            # Needs approval — confirm triggers workflow
            po.with_user(staff).button_confirm()
            if po.approval_state == 'pending':
                _process_po_approval(env, refs, po, fate='approved')
        
        # Complete stock movements for confirmed POs
        if po.state == 'purchase':
            for picking in po.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()


def _build_po_lines(products, profile):
    """Build PO lines to match a target amount profile."""
    if profile == 'small':
        target = random.randint(500_000, 4_500_000)
    elif profile == 'medium':
        target = random.randint(5_000_000, 45_000_000)
    elif profile == 'large':
        target = random.randint(50_000_000, 190_000_000)
    else:  # enterprise
        target = random.randint(200_000_000, 500_000_000)

    lines = []
    remaining = target
    num_lines = random.randint(2, 8)
    selected = random.sample(products, min(num_lines, len(products)))

    for prod in selected:
        if remaining <= 0:
            break
        price = prod.standard_price or 100000
        max_qty = max(1, int(remaining / price))
        qty = random.randint(1, min(max_qty, 50))
        lines.append({
            'product_id': prod.id,
            'product_qty': qty,
            'price_unit': price,
            'name': prod.name,
            'product_uom_id': prod.uom_id.id,
        })
        remaining -= price * qty

    return lines if lines else [{
        'product_id': products[0].id,
        'product_qty': 1,
        'price_unit': products[0].standard_price or 100000,
        'name': products[0].name,
        'product_uom_id': products[0].uom_id.id,
    }]


def _process_po_approval(env, refs, po, fate='approved'):
    """Process approval workflow for a PO."""
    if po.approval_state != 'pending':
        return

    if fate == 'rejected':
        approver = po.current_approval_level_id.approver_ids[:1]
        if approver:
            po.with_user(approver).action_reject_purchase(
                reason=random.choice([
                    "Harga terlalu tinggi, minta re-negosiasi dengan vendor.",
                    "Budget proyek belum disetujui manajemen.",
                    "Vendor belum terverifikasi oleh departemen QC.",
                    "Spesifikasi material tidak sesuai kebutuhan proyek.",
                ])
            )
        return

    if fate == 'pending':
        # Leave as pending — don't approve
        return

    # fate == 'approved' — walk through all levels
    max_iterations = 10
    iteration = 0
    while po.approval_state == 'pending' and iteration < max_iterations:
        iteration += 1
        level = po.current_approval_level_id
        if not level:
            break
        for approver in level.approver_ids:
            if po.approval_state != 'pending':
                break
            try:
                po.with_user(approver).action_approve_purchase(
                    notes=random.choice([
                        "Approved. Harga sesuai market.",
                        "OK, lanjutkan procurement.",
                        "Disetujui sesuai kebutuhan proyek.",
                        "Approved.",
                    ])
                )
            except Exception as e:
                _logger.debug("Approval skip: %s", e)
                break


# ══════════════════════════════════════════════════════
# SALES ORDER GENERATION
# ══════════════════════════════════════════════════════

def _generate_sale_orders(env, refs, company, month_start, month_end, is_last_month):
    """Generate SOs for one month."""
    count = random.randint(*SO_PER_MONTH_RANGE)
    products = list(refs['products'])
    customers = list(refs['customers'])
    sales_staff = refs['sales_staff']

    for i in range(count):
        customer = random.choice(customers)
        staff = random.choice(sales_staff)
        order_date = _random_date(month_start, month_end)

        # Pick discount tier
        if is_last_month and i >= count - 5:
            # Force high discount for the dashboard demo records
            disc_pct = random.uniform(15.0, 45.0)
        else:
            disc_pct = _weighted_choice_value(DISCOUNT_TIERS)

        # Build SO lines
        num_lines = random.randint(1, 6)
        selected = random.sample(products, min(num_lines, len(products)))
        lines_data = []
        for prod in selected:
            qty = random.randint(1, 30)
            lines_data.append({
                'product_id': prod.id,
                'product_uom_qty': qty,
                'price_unit': prod.list_price or 100000,
                'discount': disc_pct,
                'name': prod.name,
            })

        so_vals = {
            'partner_id': customer.id,
            'company_id': company.id,
            'date_order': order_date,
            'user_id': staff.id,
            'order_line': [(0, 0, line) for line in lines_data],
        }

        so = env['sale.order'].sudo().create(so_vals)
        _logger.debug("Created SO %s — discount: %.1f%%", so.name, disc_pct)

        # Decide fate
        if is_last_month and i >= count - 5:
            # Last month: leave some in various states
            if i % 3 == 0:
                # Leave as draft
                continue
            elif i % 3 == 1:
                # Submit and leave pending
                so.with_user(staff).action_confirm()
            else:
                # Submit and reject
                so.with_user(staff).action_confirm()
                if so.approval_state == 'pending':
                    _process_so_approval(env, refs, so, fate='rejected')
        else:
            # Normal flow: confirm
            so.with_user(staff).action_confirm()
            if so.approval_state == 'pending':
                # 85% approved, 15% rejected for historical months
                fate = 'approved' if random.random() < 0.85 else 'rejected'
                _process_so_approval(env, refs, so, fate=fate)

        # Complete stock movements for confirmed SOs
        if so.state == 'sale':
            for picking in so.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()


def _process_so_approval(env, refs, so, fate='approved'):
    """Process approval workflow for an SO."""
    if so.approval_state != 'pending':
        return

    if fate == 'rejected':
        approver = so.current_approval_level_id.approver_ids[:1]
        if approver:
            so.with_user(approver).action_reject_discount(
                reason=random.choice([
                    "Diskon terlalu besar, margin terlalu tipis.",
                    "Tidak sesuai kebijakan harga untuk customer ini.",
                    "Perlu negosiasi ulang dengan customer.",
                    "Harga sudah di bawah HPP, mohon revisi.",
                    "Approval ditolak, customer belum memenuhi syarat diskon.",
                ])
            )
        return

    if fate == 'pending':
        return

    # fate == 'approved'
    max_iterations = 10
    iteration = 0
    while so.approval_state == 'pending' and iteration < max_iterations:
        iteration += 1
        level = so.current_approval_level_id
        if not level:
            break

        # Randomly decide: approve or counter-offer (10% chance)
        use_counter = random.random() < 0.10 and so.effective_max_discount > 15

        for approver in level.approver_ids:
            if so.approval_state != 'pending':
                break
            try:
                if use_counter:
                    counter_pct = so.effective_max_discount * random.uniform(0.6, 0.9)
                    so.with_user(approver).action_approve_discount(
                        notes="Counter-offer: diskon disesuaikan.",
                        counter_offer_percent=counter_pct,
                    )
                else:
                    so.with_user(approver).action_approve_discount(
                        notes=random.choice([
                            "Approved. Margin masih aman.",
                            "OK, harga wajar untuk volume ini.",
                            "Disetujui untuk proyek strategis.",
                            "Approved.",
                        ])
                    )
            except Exception as e:
                _logger.debug("SO approval skip: %s", e)
                break


# ══════════════════════════════════════════════════════
# BACKDATE HELPER
# ══════════════════════════════════════════════════════

def _backdate_records(env):
    """Update create_date on generated records to match date_order."""
    cr = env.cr
    _logger.info("Backdating SO create_date...")
    cr.execute("""
        UPDATE sale_order
        SET create_date = date_order
        WHERE create_date::date = CURRENT_DATE
          AND date_order < CURRENT_DATE
    """)

    _logger.info("Backdating PO create_date...")
    cr.execute("""
        UPDATE purchase_order
        SET create_date = date_order
        WHERE create_date::date = CURRENT_DATE
          AND date_order < CURRENT_DATE
    """)

    _logger.info("Backdating approval logs...")
    cr.execute("""
        UPDATE sale_discount_approval_log
        SET create_date = timestamp
        WHERE create_date::date = CURRENT_DATE
          AND timestamp < CURRENT_DATE::timestamp
    """)
    cr.execute("""
        UPDATE purchase_approval_log
        SET create_date = timestamp
        WHERE create_date::date = CURRENT_DATE
          AND timestamp < CURRENT_DATE::timestamp
    """)
    _logger.info("Backdating complete.")


# ══════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════

def _random_date(start, end):
    """Return a random date between start and end (inclusive)."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))


def _weighted_choice(choices):
    """Pick a value from [(value, weight), ...] based on weights."""
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def _weighted_choice_value(choices):
    """Pick a numeric value from [(value, weight), ...] with slight randomization."""
    base = _weighted_choice(choices)
    # Add slight variance ±2%
    return round(base + random.uniform(-2, 2), 1) if base > 0 else 0.0
