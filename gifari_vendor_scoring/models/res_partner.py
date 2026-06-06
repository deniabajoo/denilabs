from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_category = fields.Selection(
        selection=[
            ('baja', 'Baja & Struktur'),
            ('beton', 'Beton & Material'),
            ('alat_berat', 'Alat Berat'),
            ('bbm_kimia', 'BBM & Kimia'),
            ('logistik', 'Logistik'),
            ('other', 'Lainnya'),
        ],
        string="Kategori Vendor",
        help="Bidang pengadaan vendor, dipakai untuk mengelompokkan pemasok pada evaluasi.",
    )
    vendor_score_count = fields.Integer(
        string="Jumlah Evaluasi",
        compute='_compute_vendor_score_count',
    )

    def _compute_vendor_score_count(self):
        score_counts = self.env['vendor.score'].search_read(
            [
                ('partner_id', 'in', self.ids),
                ('period_id.state', '=', 'validated'),
            ],
            ['partner_id'],
        )
        count_per_partner = {}
        for score_record in score_counts:
            partner_id = score_record['partner_id'][0]
            count_per_partner[partner_id] = count_per_partner.get(partner_id, 0) + 1

        for partner in self:
            partner.vendor_score_count = count_per_partner.get(partner.id, 0)

    def action_view_vendor_scores(self):
        """Buka riwayat skor vendor ini."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Riwayat Skor: %s' % self.name,
            'res_model': 'vendor.score',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('period_id.state', '=', 'validated'),
            ],
            'context': {'default_partner_id': self.id},
        }
