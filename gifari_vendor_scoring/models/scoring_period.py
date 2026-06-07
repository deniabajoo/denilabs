from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# Band kualitatif untuk skor akhir SAW (final_score ∈ [0, 1]).
# Membantu pengambil keputusan membaca skor 4-desimal sebagai "kelas" cepat.
# Urut menurun: ambang pertama yang terpenuhi dipakai.
SCORE_BANDS = [
    (0.85, 'Sangat Baik', 'success'),
    (0.70, 'Baik', 'primary'),
    (0.55, 'Cukup', 'warning'),
    (0.0, 'Kurang', 'danger'),
]


def _saw_score_band(final_score):
    """Kembalikan band kualitatif {label, tone} untuk satu skor akhir SAW."""
    for threshold, label, tone in SCORE_BANDS:
        if final_score >= threshold:
            return {'label': label, 'tone': tone}
    return {'label': 'Kurang', 'tone': 'danger'}


class ScoringPeriod(models.Model):
    _name = 'scoring.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Periode Evaluasi Pemasok'
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string="Nama Periode",
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        string="Tanggal Mulai",
        required=True,
    )
    date_to = fields.Date(
        string="Tanggal Akhir",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('scoring', 'Penilaian'),
            ('calculated', 'Terhitung'),
            ('validated', 'Tervalidasi'),
            ('cancelled', 'Dibatalkan'),
        ],
        string="Status",
        default='draft',
        required=True,
        tracking=True,
    )
    evaluator_id = fields.Many2one(
        comodel_name='res.users',
        string="Evaluator",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    validator_id = fields.Many2one(
        comodel_name='res.users',
        string="Validator",
        tracking=True,
    )
    validation_date = fields.Datetime(
        string="Tanggal Validasi",
    )
    vendor_score_ids = fields.One2many(
        comodel_name='vendor.score',
        inverse_name='period_id',
        string="Skor Pemasok",
    )
    package_id = fields.Many2one(
        comodel_name='scoring.package',
        string="Paket Kriteria",
        help="Pilih paket untuk otomatis memuat kriteria dan membagi bobot.",
    )
    period_criterion_ids = fields.One2many(
        comodel_name='scoring.period.criterion',
        inverse_name='period_id',
        string="Kriteria Evaluasi",
        help="Kriteria yang digunakan pada periode evaluasi ini berserta bobotnya.",
    )
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='scoring_period_partner_rel',
        column1='period_id',
        column2='partner_id',
        string="Pemasok yang Dievaluasi",
        domain=[('supplier_rank', '>', 0)],
        help="Pilih pemasok yang akan dievaluasi pada periode ini.",
    )
    notes = fields.Html(
        string="Catatan",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Perusahaan",
        default=lambda self: self.env.company,
        required=True,
    )
    vendor_count = fields.Integer(
        string="Jumlah Pemasok",
        compute='_compute_vendor_count',
    )
    criterion_count = fields.Integer(
        string="Jumlah Kriteria",
        compute='_compute_setup_counts',
    )
    partner_selected_count = fields.Integer(
        string="Jumlah Pemasok Dipilih",
        compute='_compute_setup_counts',
    )
    is_ready_to_start = fields.Boolean(
        string="Siap Dinilai",
        compute='_compute_is_ready_to_start',
        help="Benar jika tanggal terisi, bobot kriteria 100%, dan minimal 2 pemasok dipilih.",
    )
    total_weight = fields.Float(
        string="Total Bobot (%)",
        compute='_compute_total_weight',
        store=True,
    )
    is_weight_valid = fields.Boolean(
        string="Bobot Valid",
        compute='_compute_total_weight',
        store=True,
    )
    score_filled_count = fields.Integer(
        string="Skor Terisi",
        compute='_compute_scoring_progress',
    )
    score_total_count = fields.Integer(
        string="Total Skor",
        compute='_compute_scoring_progress',
    )
    scoring_progress_percent = fields.Float(
        string="Progress Penilaian (%)",
        compute='_compute_scoring_progress',
    )
    top_score_value = fields.Float(
        string="Skor Tertinggi",
        compute='_compute_top_vendor',
        digits=(10, 4),
    )
    top_vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string="Vendor Terbaik",
        compute='_compute_top_vendor',
    )
    top_vendor_name = fields.Char(
        string="Nama Vendor Terbaik",
        compute='_compute_top_vendor',
    )

    _check_date_range = models.Constraint(
        'CHECK(date_to >= date_from)',
        'Tanggal akhir harus lebih besar atau sama dengan tanggal mulai.',
    )

    @api.depends('vendor_score_ids')
    def _compute_vendor_count(self):
        for period in self:
            period.vendor_count = len(period.vendor_score_ids)

    @api.depends('period_criterion_ids', 'partner_ids')
    def _compute_setup_counts(self):
        for period in self:
            period.criterion_count = len(period.period_criterion_ids)
            period.partner_selected_count = len(period.partner_ids)

    @api.depends('date_from', 'date_to', 'is_weight_valid', 'partner_ids')
    def _compute_is_ready_to_start(self):
        for period in self:
            period.is_ready_to_start = bool(
                period.date_from
                and period.date_to
                and period.is_weight_valid
                and len(period.partner_ids) >= 2
            )

    @api.onchange('package_id')
    def _onchange_package_id(self):
        if not self.package_id:
            return
            
        # Hapus kriteria yang ada
        self.period_criterion_ids = [(5, 0, 0)]
        
        lines = self.package_id.line_ids
        if not lines:
            return
            
        # Buat baris kriteria baru dari paket
        new_lines = []
        for line in lines:
            new_lines.append((0, 0, {
                'criterion_id': line.criterion_id.id,
                'weight': line.weight,
            }))
        self.period_criterion_ids = new_lines

    @api.depends('period_criterion_ids.weight')
    def _compute_total_weight(self):
        for period in self:
            period.total_weight = sum(period.period_criterion_ids.mapped('weight'))
            period.is_weight_valid = abs(period.total_weight - 100.0) < 0.01

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for period in self:
            if period.date_to < period.date_from:
                raise ValidationError(
                    "Tanggal akhir harus lebih besar atau sama dengan tanggal mulai."
                )

    @api.constrains('period_criterion_ids')
    def _check_total_weight(self):
        for period in self:
            if period.period_criterion_ids and not period.is_weight_valid:
                raise ValidationError(
                    "Total bobot kriteria harus tepat 100%%. Saat ini: %.2f%%."
                    % period.total_weight
                )

    @api.depends('vendor_score_ids.score_line_ids.raw_score')
    def _compute_scoring_progress(self):
        for period in self:
            all_score_lines = period.vendor_score_ids.score_line_ids
            period.score_total_count = len(all_score_lines)
            period.score_filled_count = len(
                all_score_lines.filtered(lambda line: line.raw_score > 0)
            )
            period.scoring_progress_percent = (
                (period.score_filled_count / period.score_total_count * 100)
                if period.score_total_count else 0.0
            )

    @api.depends('vendor_score_ids.rank', 'vendor_score_ids.final_score', 'vendor_score_ids.partner_id')
    def _compute_top_vendor(self):
        for period in self:
            top_vendor_score = period.vendor_score_ids.filtered(lambda vs: vs.rank == 1)[:1]
            period.top_score_value = top_vendor_score.final_score if top_vendor_score else 0.0
            period.top_vendor_id = top_vendor_score.partner_id if top_vendor_score else False
            period.top_vendor_name = top_vendor_score.partner_id.name if top_vendor_score else ''

    def _reload_form_view(self):
        """Buka ulang record ini di form view.

        Tujuannya mereset 'memory' tab notebook di sisi klien sehingga
        atribut autofocus pada <page> kembali berlaku — mis. setelah
        'Mulai Penilaian' tab default menjadi Matrix Penilaian (bukan
        tab terakhir yang dilihat, Catatan).
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_start_scoring(self):
        """Mulai proses penilaian: generate vendor score lines dari partner_ids."""
        self.ensure_one()
        if not self.period_criterion_ids:
            raise UserError(
                "Silakan pilih minimal satu kriteria evaluasi sebelum memulai penilaian."
            )
        if not self.is_weight_valid:
            raise UserError(
                "Total bobot kriteria harus tepat 100%%. Saat ini: %.2f%%." % self.total_weight
            )
        if not self.partner_ids:
            raise UserError(
                "Silakan pilih minimal satu pemasok yang akan dievaluasi."
            )

        # Hapus skor vendor yang tidak ada lagi di pilihan partner_ids
        vendors_to_remove = self.vendor_score_ids.filtered(lambda vs: vs.partner_id.id not in self.partner_ids.ids)
        if vendors_to_remove:
            vendors_to_remove.unlink()

        existing_vendor_ids = self.vendor_score_ids.mapped('partner_id').ids
        new_vendor_scores = []

        for vendor in self.partner_ids:
            if vendor.id in existing_vendor_ids:
                continue
            score_lines = [(0, 0, {'criterion_id': c.criterion_id.id, 'raw_score': 0.0})
                           for c in self.period_criterion_ids]
            new_vendor_scores.append((0, 0, {
                'partner_id': vendor.id,
                'score_line_ids': score_lines,
            }))

        if new_vendor_scores:
            self.write({'vendor_score_ids': new_vendor_scores})

        self.write({'state': 'scoring'})

        self._schedule_activity_scoring()
        self._send_mail_template('gifari_vendor_scoring.mail_template_period_started')

        return self._reload_form_view()

    def action_calculate_saw(self):
        """Kalkulasi SAW: Normalisasi → Pembobotan → Perangkingan."""
        self.ensure_one()
        if not self.vendor_score_ids:
            raise UserError("Tidak ada pemasok yang dinilai.")
        if len(self.vendor_score_ids) < 2:
            raise UserError("Minimal 2 pemasok diperlukan untuk perbandingan.")

        # Validasi: semua skor harus terisi (> 0)
        for vendor_score in self.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                if score_line.raw_score <= 0:
                    raise UserError(
                        "Skor untuk pemasok '%s' pada kriteria '%s' belum diisi." % (
                            vendor_score.partner_id.name,
                            score_line.criterion_id.name,
                        )
                    )

        # Langkah 1 & 2: Kumpulkan matriks keputusan per kriteria
        criterion_raw_scores = {}
        for period_criterion in self.period_criterion_ids:
            criterion_raw_scores[period_criterion.criterion_id.id] = {
                'type': period_criterion.criterion_type,
                'weight': period_criterion.weight_decimal,
                'scores': {},
            }

        for vendor_score in self.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                criterion_raw_scores[score_line.criterion_id.id]['scores'][vendor_score.id] = score_line.raw_score

        # Langkah 3: Hitung max dan min per kriteria, lalu normalisasi
        for criterion_id, criterion_data in criterion_raw_scores.items():
            scores = criterion_data['scores'].values()
            criterion_data['max_score'] = max(scores)
            criterion_data['min_score'] = min(scores)

        # Update normalized_score dan weighted_score untuk setiap score line
        for vendor_score in self.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                criterion_data = criterion_raw_scores[score_line.criterion_id.id]
                raw = score_line.raw_score

                if criterion_data['type'] == 'benefit':
                    max_val = criterion_data['max_score']
                    normalized = raw / max_val if max_val else 0.0
                else:
                    min_val = criterion_data['min_score']
                    normalized = min_val / raw if raw else 0.0

                weighted = normalized * criterion_data['weight']

                score_line.write({
                    'normalized_score': normalized,
                    'weighted_score': weighted,
                })

        # Langkah 4: Hitung final_score (Vᵢ) per pemasok
        for vendor_score in self.vendor_score_ids:
            final_score = sum(vendor_score.score_line_ids.mapped('weighted_score'))
            vendor_score.write({'final_score': final_score})

        # Langkah 5: Perangkingan
        sorted_scores = self.vendor_score_ids.sorted(key=lambda vs: vs.final_score, reverse=True)
        for ranking, vendor_score in enumerate(sorted_scores, start=1):
            vendor_score.write({
                'rank': ranking,
                'is_recommended': ranking == 1,
            })

        self.write({'state': 'calculated'})

        self._schedule_activity_validation()
        self._send_mail_template('gifari_vendor_scoring.mail_template_period_calculated')

        return self._reload_form_view()

    def action_validate(self):
        """Validasi hasil evaluasi oleh manager."""
        self.ensure_one()
        self.write({
            'state': 'validated',
            'validator_id': self.env.user.id,
            'validation_date': fields.Datetime.now(),
        })

        self.activity_ids.action_done()
        self._send_mail_template('gifari_vendor_scoring.mail_template_period_validated')

    def action_back_to_scoring(self):
        """Kembali ke tahap penilaian untuk revisi skor."""
        self.ensure_one()
        self.write({'state': 'scoring'})
        return self._reload_form_view()

    def action_cancel(self):
        """Batalkan periode evaluasi."""
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reset ke draft."""
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_view_vendor_scores(self):
        """Buka list skor pemasok untuk periode ini."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Skor Pemasok — %s' % self.name,
            'res_model': 'vendor.score',
            'view_mode': 'list,form',
            'domain': [('period_id', '=', self.id)],
            'context': {'default_period_id': self.id},
        }

    def action_view_top_vendor(self):
        """Buka detail skor vendor dengan rank tertinggi."""
        self.ensure_one()
        top_vendor_score = self.vendor_score_ids.filtered(lambda vs: vs.rank == 1)[:1]
        if not top_vendor_score:
            raise UserError("Belum ada hasil perangkingan.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Skor: %s' % top_vendor_score.partner_id.name,
            'res_model': 'vendor.score',
            'res_id': top_vendor_score.id,
            'view_mode': 'form',
            'view_id': self.env.ref('gifari_vendor_scoring.view_vendor_score_form').id,
            'target': 'new',
        }

    def get_matrix_data(self):
        """RPC endpoint: return structured matrix data for OWL component."""
        self.ensure_one()
        criteria = []
        for period_criterion in self.period_criterion_ids.sorted('sequence'):
            criteria.append({
                'id': period_criterion.criterion_id.id,
                'name': period_criterion.criterion_id.name,
                'code': period_criterion.criterion_id.code,
                'type': period_criterion.criterion_type,
                'weight': period_criterion.weight,
            })

        vendors = []
        for vendor_score in self.vendor_score_ids.sorted('partner_id'):
            score_lines = {}
            filled_count = 0
            for score_line in vendor_score.score_line_ids:
                score_lines[score_line.criterion_id.id] = {
                    'line_id': score_line.id,
                    'raw_score': score_line.raw_score,
                }
                if score_line.raw_score > 0:
                    filled_count += 1
            vendors.append({
                'vendor_score_id': vendor_score.id,
                'partner_id': vendor_score.partner_id.id,
                'partner_name': vendor_score.partner_id.name,
                'score_lines': score_lines,
                'filled_count': filled_count,
                'total_criteria': len(criteria),
            })

        total_cells = len(vendors) * len(criteria)
        filled_cells = sum(vendor['filled_count'] for vendor in vendors)

        return {
            'period_id': self.id,
            'period_name': self.name,
            'state': self.state,
            'criteria': criteria,
            'vendors': vendors,
            'total_cells': total_cells,
            'filled_cells': filled_cells,
        }

    def update_matrix_score(self, score_line_id, new_score):
        """RPC endpoint: update a single score cell from matrix component."""
        self.ensure_one()
        if self.state != 'scoring':
            raise UserError("Skor hanya bisa diubah saat status Penilaian.")

        score_line = self.env['vendor.score.line'].browse(score_line_id)
        if not score_line.exists():
            raise UserError("Baris skor tidak ditemukan.")
        if score_line.vendor_score_id.period_id.id != self.id:
            raise UserError("Baris skor tidak termasuk dalam periode ini.")

        score_line.write({'raw_score': new_score})
        return {'success': True, 'line_id': score_line_id, 'new_score': new_score}

    def bulk_fill_empty_scores(self, value):
        """RPC endpoint: isi semua sel kosong dengan satu nilai (input cepat).

        Hanya mengisi sel yang masih kosong (raw_score <= 0). Skala seragam
        1-100 untuk semua tipe kriteria (Benefit & Cost) — arah "baik"
        ditentukan saat normalisasi SAW (Cost: nilai lebih rendah lebih baik).
        Mengembalikan jumlah sel terisi.
        """
        self.ensure_one()
        if self.state != 'scoring':
            raise UserError("Skor hanya bisa diisi saat status Penilaian.")

        parsed_value = float(value or 0)
        if not (1.0 <= parsed_value <= 100.0):
            return {'filled_count': 0}

        filled_count = 0
        for vendor_score in self.vendor_score_ids:
            for score_line in vendor_score.score_line_ids:
                if score_line.raw_score > 0:
                    continue
                score_line.raw_score = parsed_value
                filled_count += 1

        return {'filled_count': filled_count}

    @api.model
    def get_dashboard_data(self, options=None):
        """RPC endpoint: return structured dashboard data for OWL component.

        options (optional dict):
            - focus_period_id: id periode tervalidasi yang dijadikan fokus
              leaderboard/perbandingan/radar. Bila tidak ada, pakai yang terbaru.
        """
        options = options or {}
        company_id = self.env.company.id

        available_periods = self.search([
            ('state', '=', 'validated'),
            ('company_id', '=', company_id),
        ], order='date_to desc')

        focus_period_id = options.get('focus_period_id')
        latest_validated = self.browse()
        if focus_period_id:
            latest_validated = available_periods.filtered(
                lambda period: period.id == focus_period_id
            )[:1]
        if not latest_validated:
            latest_validated = available_periods[:1]

        # Periode aktif: Prioritaskan yang sedang proses penilaian/kalkulasi, 
        # jika tidak ada, ambil periode tervalidasi yang masih berjalan (date_to >= hari ini)
        active_scoring = self.search([
            ('state', 'in', ('scoring', 'calculated')),
            ('company_id', '=', company_id),
        ], order='date_from desc', limit=1)

        if not active_scoring:
            today = fields.Date.context_today(self)
            active_scoring = self.search([
                ('state', '=', 'validated'),
                ('company_id', '=', company_id),
                ('date_from', '<=', today),
                ('date_to', '>=', today),
            ], order='date_from desc', limit=1)

        # Fallback terakhir jika tetap tidak ada, ambil periode non-draft terbaru
        if not active_scoring:
            active_scoring = self.search([
                ('state', 'not in', ('draft', 'cancelled')),
                ('company_id', '=', company_id),
            ], order='date_from desc', limit=1)

        total_periods = self.search_count([
            ('company_id', '=', company_id),
            ('state', '=', 'validated'),
        ])

        top_vendors = []
        comparison_chart_vendors = []
        criteria_names = []

        if latest_validated:
            criteria_names = [
                c.criterion_id.name for c in latest_validated.period_criterion_ids.sorted('sequence')
            ]

            # Peta peringkat dari periode tervalidasi sebelumnya (untuk indikator
            # pergerakan naik/turun per vendor di leaderboard).
            previous_validated = available_periods.filtered(
                lambda period: period.id != latest_validated.id
                and period.date_to < latest_validated.date_to
            )[:1]
            previous_rank_by_partner = {
                vendor_score.partner_id.id: vendor_score.rank
                for vendor_score in previous_validated.vendor_score_ids
            } if previous_validated else {}

            sorted_vendor_scores = latest_validated.vendor_score_ids.sorted('rank')
            top_final_score = sorted_vendor_scores[:1].final_score if sorted_vendor_scores else 0.0

            for vendor_score in sorted_vendor_scores:
                weighted_per_criterion = {}
                for score_line in vendor_score.score_line_ids:
                    weighted_per_criterion[score_line.criterion_id.name] = score_line.weighted_score

                previous_rank = previous_rank_by_partner.get(vendor_score.partner_id.id)
                rank_movement = (
                    None if previous_rank is None
                    else previous_rank - vendor_score.rank  # + naik, - turun, 0 tetap
                )

                vendor_entry = {
                    'vendor_score_id': vendor_score.id,
                    'partner_id': vendor_score.partner_id.id,
                    'rank': vendor_score.rank,
                    'partner_name': vendor_score.partner_id.name,
                    'final_score': vendor_score.final_score,
                    'is_recommended': vendor_score.is_recommended,
                    'rank_display': vendor_score.rank_display,
                    'criteria_scores': weighted_per_criterion,
                    'delta_to_top': round(top_final_score - vendor_score.final_score, 4),
                    'score_band': _saw_score_band(vendor_score.final_score),
                    'rank_movement': rank_movement,
                    'has_previous': previous_rank is not None,
                }
                comparison_chart_vendors.append(vendor_entry)
                if vendor_score.rank <= 5:
                    top_vendors.append(vendor_entry)

        # Keunggulan pemenang vs runner-up: sinyal kepercayaan keputusan.
        # Margin tipis = perlu kehati-hatian; margin lebar = pemenang jelas.
        winner_margin = 0.0
        winner_margin_percent = 0.0
        runner_up_name = ''
        if len(comparison_chart_vendors) >= 2:
            winner_entry = comparison_chart_vendors[0]
            runner_up_entry = comparison_chart_vendors[1]
            winner_margin = round(winner_entry['final_score'] - runner_up_entry['final_score'], 4)
            winner_margin_percent = round(
                winner_margin / winner_entry['final_score'] * 100, 1
            ) if winner_entry['final_score'] else 0.0
            runner_up_name = runner_up_entry['partner_name']

        # Alasan rekomendasi: di berapa kriteria pemenang punya skor terbobot
        # tertinggi (termasuk seri). Memberi justifikasi singkat di dashboard.
        recommendation_reason = ''
        top_vendor_band = None
        if comparison_chart_vendors and criteria_names:
            winner_entry = comparison_chart_vendors[0]
            top_vendor_band = winner_entry['score_band']
            winning_criteria = []
            for criterion_name in criteria_names:
                best_weighted = max(
                    vendor_entry['criteria_scores'].get(criterion_name, 0.0)
                    for vendor_entry in comparison_chart_vendors
                )
                winner_weighted = winner_entry['criteria_scores'].get(criterion_name, 0.0)
                if best_weighted > 0 and winner_weighted >= best_weighted:
                    winning_criteria.append(criterion_name)
            if winning_criteria:
                leading_criteria = ', '.join(winning_criteria[:2])
                recommendation_reason = (
                    "Unggul di %d dari %d kriteria (mis. %s)."
                    % (len(winning_criteria), len(criteria_names), leading_criteria)
                )
            else:
                recommendation_reason = "Skor akhir tertinggi pada periode ini."

        return {
            'active_period': {
                'id': active_scoring.id,
                'name': active_scoring.name,
                'progress_percent': active_scoring.scoring_progress_percent,
                'vendor_count': active_scoring.vendor_count,
            } if active_scoring else None,
            'latest_period': {
                'id': latest_validated.id,
                'name': latest_validated.name,
            } if latest_validated else None,
            'kpis': {
                'total_periods': total_periods,
                'top_vendor_name': top_vendors[0]['partner_name'] if top_vendors else '-',
                'top_vendor_score': top_vendors[0]['final_score'] if top_vendors else 0,
                'top_vendor_band': top_vendor_band,
                'winner_margin': winner_margin,
                'winner_margin_percent': winner_margin_percent,
                'runner_up_name': runner_up_name,
                'recommendation_reason': recommendation_reason,
                'vendor_evaluated_count': len(comparison_chart_vendors),
            },
            'top_vendors': top_vendors,
            'comparison_data': comparison_chart_vendors,
            'criteria_names': criteria_names,
            'available_periods': [
                {'id': period.id, 'name': period.name}
                for period in available_periods
            ],
            'focus_period_id': latest_validated.id if latest_validated else None,
        }

    # ------------------------------------------------------
    # WORKFLOW & COLLABORATION HELPERS
    # ------------------------------------------------------

    def _schedule_activity_scoring(self):
        self.ensure_one()
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary="Input Skor Vendor: %s" % self.name,
            note="Harap lengkapi skor evaluasi vendor untuk periode ini.",
            user_id=self.evaluator_id.id,
            date_deadline=self.date_to,
        )

    def _schedule_activity_validation(self):
        self.ensure_one()
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary="Validasi Hasil Evaluasi: %s" % self.name,
            note="Harap tinjau dan validasi hasil perhitungan SAW.",
            user_id=self.validator_id.id if self.validator_id else self.env.user.id,
            date_deadline=fields.Date.context_today(self) + timedelta(days=2),
        )

    def _send_mail_template(self, template_xml_id):
        self.ensure_one()
        template = self.env.ref(template_xml_id, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _cron_remind_scoring(self):
        """Cron: Ingatkan evaluator jika deadline (date_to) < 3 hari dan status masih 'scoring'."""
        deadline = fields.Date.context_today(self) + timedelta(days=3)
        periods = self.search([
            ('state', '=', 'scoring'),
            ('date_to', '<=', deadline),
        ])
        for period in periods:
            period._send_mail_template('gifari_vendor_scoring.mail_template_scoring_reminder')
