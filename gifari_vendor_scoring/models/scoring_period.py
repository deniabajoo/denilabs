from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ScoringPeriod(models.Model):
    _name = 'scoring.period'
    _description = 'Periode Evaluasi Pemasok'
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string="Nama Periode",
        required=True,
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
    )
    validator_id = fields.Many2one(
        comodel_name='res.users',
        string="Validator",
    )
    validation_date = fields.Datetime(
        string="Tanggal Validasi",
    )
    vendor_score_ids = fields.One2many(
        comodel_name='vendor.score',
        inverse_name='period_id',
        string="Skor Pemasok",
    )
    criterion_ids = fields.Many2many(
        comodel_name='scoring.criterion',
        string="Kriteria Evaluasi",
        help="Kriteria yang digunakan pada periode evaluasi ini.",
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
    )
    is_weight_valid = fields.Boolean(
        string="Bobot Valid",
        compute='_compute_total_weight',
    )

    _constraints = [
        models.Constraint(
            'check(date_to >= date_from)',
            'Tanggal akhir harus lebih besar atau sama dengan tanggal mulai.',
        ),
    ]

    @api.depends('vendor_score_ids')
    def _compute_vendor_count(self):
        for period in self:
            period.vendor_count = len(period.vendor_score_ids)

    @api.depends('criterion_ids.weight')
    def _compute_total_weight(self):
        for period in self:
            period.total_weight = sum(period.criterion_ids.mapped('weight'))
            period.is_weight_valid = abs(period.total_weight - 100.0) < 0.01

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for period in self:
            if period.date_to < period.date_from:
                raise ValidationError(
                    "Tanggal akhir harus lebih besar atau sama dengan tanggal mulai."
                )

    def action_start_scoring(self):
        """Mulai proses penilaian: generate vendor score lines."""
        self.ensure_one()
        if not self.criterion_ids:
            raise UserError(
                "Silakan pilih minimal satu kriteria evaluasi sebelum memulai penilaian."
            )
        if not self.is_weight_valid:
            raise UserError(
                "Total bobot kriteria harus tepat 100%%. Saat ini: %.2f%%." % self.total_weight
            )

        active_vendors = self.env['res.partner'].search([
            ('supplier_rank', '>', 0),
            ('company_id', 'in', [self.company_id.id, False]),
        ])
        if not active_vendors:
            raise UserError("Tidak ditemukan pemasok aktif di sistem.")

        existing_vendor_ids = self.vendor_score_ids.mapped('partner_id').ids
        new_vendor_scores = []

        for vendor in active_vendors:
            if vendor.id in existing_vendor_ids:
                continue
            score_lines = []
            for criterion in self.criterion_ids:
                score_lines.append((0, 0, {
                    'criterion_id': criterion.id,
                    'raw_score': 0.0,
                }))
            new_vendor_scores.append((0, 0, {
                'partner_id': vendor.id,
                'score_line_ids': score_lines,
            }))

        if new_vendor_scores:
            self.write({'vendor_score_ids': new_vendor_scores})

        self.write({'state': 'scoring'})

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
        for criterion in self.criterion_ids:
            criterion_raw_scores[criterion.id] = {
                'type': criterion.criterion_type,
                'weight': criterion.weight_decimal,
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

    def action_validate(self):
        """Validasi hasil evaluasi oleh manager."""
        self.ensure_one()
        self.write({
            'state': 'validated',
            'validator_id': self.env.user.id,
            'validation_date': fields.Datetime.now(),
        })

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
