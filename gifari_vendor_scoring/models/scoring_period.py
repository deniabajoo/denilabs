from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


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

    @api.model
    def get_dashboard_data(self):
        """RPC endpoint: return structured dashboard data for OWL component."""
        company_id = self.env.company.id

        latest_validated = self.search([
            ('state', '=', 'validated'),
            ('company_id', '=', company_id),
        ], order='date_to desc', limit=1)

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
            for vendor_score in latest_validated.vendor_score_ids.sorted('rank'):
                weighted_per_criterion = {}
                for score_line in vendor_score.score_line_ids:
                    weighted_per_criterion[score_line.criterion_id.name] = score_line.weighted_score

                vendor_entry = {
                    'rank': vendor_score.rank,
                    'partner_name': vendor_score.partner_id.name,
                    'final_score': vendor_score.final_score,
                    'is_recommended': vendor_score.is_recommended,
                    'rank_display': vendor_score.rank_display,
                    'criteria_scores': weighted_per_criterion,
                }
                comparison_chart_vendors.append(vendor_entry)
                if vendor_score.rank <= 5:
                    top_vendors.append(vendor_entry)

        validated_periods = self.search([
            ('state', '=', 'validated'),
            ('company_id', '=', company_id),
        ], order='date_from asc', limit=8)

        period_trend = []
        for period in validated_periods:
            all_final_scores = period.vendor_score_ids.mapped('final_score')
            top_vendor_score = period.vendor_score_ids.filtered(lambda vs: vs.rank == 1)[:1]
            period_trend.append({
                'name': period.name,
                'top_score': top_vendor_score.final_score if top_vendor_score else 0,
                'avg_score': round(
                    sum(all_final_scores) / len(all_final_scores), 4
                ) if all_final_scores else 0,
                'vendor_count': len(period.vendor_score_ids),
            })

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
            },
            'top_vendors': top_vendors,
            'period_trend': period_trend,
            'comparison_data': comparison_chart_vendors,
            'criteria_names': criteria_names,
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
