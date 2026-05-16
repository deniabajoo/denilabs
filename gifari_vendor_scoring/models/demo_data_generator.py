import random
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember',
}

COMPANY_INFO = {
    'name': 'PT Indonesia Pondasi Raya Tbk',
    'street': 'Jl. Raya Cilegon KM. 3',
    'street2': 'Kelurahan Ramanuju, Kecamatan Purwakarta',
    'city': 'Cilegon',
    'zip': '42435',
    'phone': '(0254) 391811',
    'email': 'info@indopora.com',
    'website': 'https://www.indopora.com',
    'vat': '01.061.634.0-402.000',
    'company_registry': '8120209832068',
}

VENDOR_MASTER = [
    {
        'name': 'PT Krakatau Steel (Persero) Tbk',
        'street': 'Jl. Industri No. 5',
        'street2': 'Kawasan Industri Krakatau',
        'city': 'Cilegon',
        'zip': '42435',
        'phone': '(0254) 391111',
        'email': 'procurement@krakatusteel.co.id',
        'website': 'https://www.krakatusteel.com',
        'vat': '01.000.059.1-402.000',
    },
    {
        'name': 'PT Semen Indonesia (Persero) Tbk',
        'street': 'Jl. Veteran No. 10',
        'street2': 'Kec. Kebomas',
        'city': 'Gresik',
        'zip': '61122',
        'phone': '(031) 3981732',
        'email': 'sales@semenindonesia.com',
        'website': 'https://www.semenindonesia.com',
        'vat': '01.000.602.1-512.000',
    },
    {
        'name': 'PT United Tractors Tbk',
        'street': 'Jl. Raya Bekasi Km. 22',
        'street2': 'Cakung, Jakarta Timur',
        'city': 'Jakarta Timur',
        'zip': '13910',
        'phone': '(021) 24579999',
        'email': 'parts@unitedtractors.com',
        'website': 'https://www.unitedtractors.com',
        'vat': '01.308.566.5-007.000',
    },
    {
        'name': 'PT Pionirbeton Industri',
        'street': 'Jl. Raya Serpong Km. 8',
        'street2': 'Kec. Serpong, Tangerang Selatan',
        'city': 'Tangerang Selatan',
        'zip': '15310',
        'phone': '(021) 53122888',
        'email': 'order@pionirbeton.co.id',
        'website': 'https://www.pionirbeton.co.id',
        'vat': '02.192.345.8-411.000',
    },
    {
        'name': 'PT Pertamina Patra Niaga',
        'street': 'Jl. Yos Sudarso No. 32-34',
        'street2': 'Tanjung Priok',
        'city': 'Jakarta Utara',
        'zip': '14320',
        'phone': '(021) 4301515',
        'email': 'industrial@patraniaga.com',
        'website': 'https://www.patraniaga.pertamina.com',
        'vat': '01.061.833.0-007.000',
    },
]

# Profil kepribadian skor vendor — menghasilkan variasi ranking yang realistis
# C1=Kualitas, C2=Harga (cost), C3=Ketepatan Waktu, C4=Kapasitas/Stok, C5=Layanan
VENDOR_SCORE_PROFILES = [
    # Krakatau Steel: kualitas baja sangat tinggi, harga premium, kapasitas besar
    {'C1': (85, 95), 'C2': (3500, 4500), 'C3': (75, 88), 'C4': (85, 95), 'C5': (78, 90)},
    # Semen Indonesia: performa stabil, harga kompetitif, kapasitas tinggi
    {'C1': (80, 92), 'C2': (3000, 4000), 'C3': (80, 92), 'C4': (88, 95), 'C5': (75, 88)},
    # United Tractors: layanan after-sales unggulan, harga paling mahal
    {'C1': (78, 90), 'C2': (4000, 5000), 'C3': (82, 95), 'C4': (75, 85), 'C5': (85, 95)},
    # Pionirbeton: delivery tercepat, kapasitas terbatas
    {'C1': (75, 88), 'C2': (3200, 4200), 'C3': (85, 95), 'C4': (70, 82), 'C5': (80, 90)},
    # Pertamina Patra Niaga: harga paling bersaing, layanan rata-rata
    {'C1': (78, 88), 'C2': (2800, 3800), 'C3': (78, 90), 'C4': (78, 88), 'C5': (72, 85)},
]

DEMO_USERS = [
    {
        'name': 'Budi Santoso',
        'login': 'evaluator_demo',
        'password': 'evaluator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_evaluator',
    },
    {
        'name': 'Siti Rahayu',
        'login': 'validator_demo',
        'password': 'validator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_validator',
    },
    {
        'name': 'Ahmad Hidayat',
        'login': 'configurator_demo',
        'password': 'configurator_demo',
        'group_xml_id': 'gifari_vendor_scoring.group_vendor_scoring_configurator',
    },
]


class ScoringPeriodDemoGenerator(models.Model):
    _inherit = 'scoring.period'

    @api.model
    def generate_demo_data(self):
        """Entry point: generate 12 monthly evaluation periods with realistic scores."""
        existing_demo = self.search([
            ('name', 'like', 'Evaluasi Vendor - %'),
        ], limit=1)
        if existing_demo:
            raise UserError(
                "Demo data sudah pernah di-generate. "
                "Hapus periode evaluasi yang ada terlebih dahulu jika ingin generate ulang."
            )

        demo_users = self._ensure_demo_users()
        self._setup_company_info()
        vendors = self._ensure_demo_vendors()
        package = self.env.ref(
            'gifari_vendor_scoring.package_default_5c',
            raise_if_not_found=False,
        )
        if not package or not package.line_ids:
            raise UserError(
                "Paket Kriteria default tidak ditemukan atau kosong. "
                "Pastikan modul terinstall dengan benar."
            )

        generated_period_ids = self._generate_monthly_periods(
            vendors, package, demo_users,
        )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Demo Data - Periode Evaluasi',
            'res_model': 'scoring.period',
            'view_mode': 'list,form',
            'domain': [('id', 'in', generated_period_ids)],
            'target': 'current',
        }

    @api.model
    def _setup_company_info(self):
        """Set the current company's identity to PT Indopora."""
        company = self.env.company
        indonesia = self.env['res.country'].search([
            ('code', '=', 'ID'),
        ], limit=1)
        update_vals = {
            'name': COMPANY_INFO['name'],
            'street': COMPANY_INFO['street'],
            'street2': COMPANY_INFO['street2'],
            'city': COMPANY_INFO['city'],
            'zip': COMPANY_INFO['zip'],
            'phone': COMPANY_INFO['phone'],
            'email': COMPANY_INFO['email'],
            'website': COMPANY_INFO['website'],
            'vat': COMPANY_INFO['vat'],
            'company_registry': COMPANY_INFO['company_registry'],
        }
        if indonesia:
            update_vals['country_id'] = indonesia.id
        company.write(update_vals)
        # Partner record juga diupdate agar konsisten di header laporan
        company.partner_id.write(update_vals)

    @api.model
    def _ensure_demo_vendors(self):
        """Find or create the 5 construction vendor partners."""
        partner_model = self.env['res.partner']
        vendor_records = partner_model
        for vendor_def in VENDOR_MASTER:
            existing = partner_model.search([
                ('name', '=', vendor_def['name']),
            ], limit=1)
            if existing:
                vendor_records |= existing
            else:
                vendor_records |= partner_model.create({
                    **vendor_def,
                    'supplier_rank': 1,
                    'company_type': 'company',
                })
        return vendor_records

    @api.model
    def _ensure_demo_users(self):
        """Find or create 3 demo users with Evaluator, Validator, Configurator roles."""
        user_model = self.env['res.users'].with_context(no_reset_password=True)
        created_users = {}
        for user_def in DEMO_USERS:
            existing = user_model.search([
                ('login', '=', user_def['login']),
            ], limit=1)
            if existing:
                created_users[user_def['login']] = existing
            else:
                group = self.env.ref(user_def['group_xml_id'])
                new_user = user_model.create({
                    'name': user_def['name'],
                    'login': user_def['login'],
                    'password': user_def['password'],
                    'group_ids': [(4, group.id)],
                })
                created_users[user_def['login']] = new_user
        return created_users

    @api.model
    def _generate_monthly_periods(self, vendors, package, demo_users):
        """Create 12 monthly periods, fill scores, calculate SAW, validate historical."""
        today = date.today()
        current_month_start = today.replace(day=1)
        generated_ids = []

        for month_offset in range(11, -1, -1):
            period_start = current_month_start - relativedelta(months=month_offset)
            period_end = period_start + relativedelta(months=1, days=-1)
            month_label = INDONESIAN_MONTHS[period_start.month]
            period_name = "Evaluasi Vendor - %s %d" % (month_label, period_start.year)

            period_criteria_vals = [
                (0, 0, {
                    'criterion_id': pkg_line.criterion_id.id,
                    'weight': pkg_line.weight,
                })
                for pkg_line in package.line_ids
            ]

            evaluator = demo_users['evaluator_demo']
            validator = demo_users['validator_demo']

            period = self.create({
                'name': period_name,
                'date_from': period_start,
                'date_to': period_end,
                'package_id': package.id,
                'evaluator_id': evaluator.id,
                'state': 'draft',
                'period_criterion_ids': period_criteria_vals,
                'partner_ids': [(6, 0, vendors.ids)],
            })

            self._create_vendor_scores(period, vendors, package)
            self._calculate_saw_silent(period)

            # 11 bulan lalu → Tervalidasi, bulan ini → tetap Scoring
            if month_offset > 0:
                period.write({
                    'state': 'validated',
                    'validator_id': validator.id,
                    'validation_date': fields.Datetime.from_string(
                        '%s 17:00:00' % period_end
                    ),
                })
            else:
                period.write({'state': 'scoring'})

            generated_ids.append(period.id)

        return generated_ids

    @api.model
    def _create_vendor_scores(self, period, vendors, package):
        """Create vendor.score + vendor.score.line records with randomized raw scores."""
        score_model = self.env['vendor.score']
        vendor_list = list(vendors)

        score_vals_batch = []
        for vendor_index, vendor in enumerate(vendor_list):
            profile = VENDOR_SCORE_PROFILES[vendor_index]
            score_line_vals = []
            for pkg_line in package.line_ids:
                criterion_code = pkg_line.criterion_id.code
                score_range = profile.get(criterion_code, (70, 90))
                if pkg_line.criterion_type == 'cost':
                    raw = round(random.uniform(score_range[0], score_range[1]), 2)
                else:
                    raw = float(random.randint(score_range[0], score_range[1]))
                score_line_vals.append((0, 0, {
                    'criterion_id': pkg_line.criterion_id.id,
                    'raw_score': raw,
                }))

            score_vals_batch.append({
                'period_id': period.id,
                'partner_id': vendor.id,
                'score_line_ids': score_line_vals,
            })

        score_model.create(score_vals_batch)

    @api.model
    def _calculate_saw_silent(self, period):
        """Replicate SAW calculation without sending emails or creating activities."""
        criterion_matrix = {}
        for period_criterion in period.period_criterion_ids:
            criterion_matrix[period_criterion.criterion_id.id] = {
                'type': period_criterion.criterion_type,
                'weight_decimal': period_criterion.weight_decimal,
                'raw_values': {},
            }

        for vendor_score in period.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                criterion_matrix[score_line.criterion_id.id]['raw_values'][vendor_score.id] = score_line.raw_score

        for criterion_data in criterion_matrix.values():
            all_raw = list(criterion_data['raw_values'].values())
            criterion_data['max_raw'] = max(all_raw) if all_raw else 1
            criterion_data['min_raw'] = min(all_raw) if all_raw else 1

        for vendor_score in period.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                crit = criterion_matrix[score_line.criterion_id.id]
                raw = score_line.raw_score
                if crit['type'] == 'benefit':
                    normalized = raw / crit['max_raw'] if crit['max_raw'] else 0
                else:
                    normalized = crit['min_raw'] / raw if raw else 0
                weighted = normalized * crit['weight_decimal']
                score_line.write({
                    'normalized_score': normalized,
                    'weighted_score': weighted,
                })

        for vendor_score in period.vendor_score_ids:
            vendor_score.write({
                'final_score': sum(vendor_score.score_line_ids.mapped('weighted_score')),
            })

        ranked_scores = period.vendor_score_ids.sorted(
            key=lambda vs: vs.final_score, reverse=True,
        )
        for ranking, vendor_score in enumerate(ranked_scores, start=1):
            vendor_score.write({
                'rank': ranking,
                'is_recommended': ranking == 1,
            })

        period.write({'state': 'calculated'})
