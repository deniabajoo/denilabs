/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Data-Dense Dashboard palette: corporate navy/blue + amber highlight.
const CHART_COLORS = [
    "#1E40AF", "#3B82F6", "#0EA5E9", "#0D9488", "#F59E0B",
    "#6366F1", "#2563EB", "#06B6D4", "#10B981", "#D97706",
];
const CHART_FONT_FAMILY =
    "'Fira Sans', 'Segoe UI', system-ui, -apple-system, sans-serif";

export class VendorScoringDashboard extends Component {
    static template = "gifari_vendor_scoring.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.comparisonRef = useRef("comparisonCanvas");

        this.chartInstances = [];
        this.chartsAvailable = false;
        // Ditandai true setiap data dimuat ulang; chart digambar di onPatched
        // setelah DOM (canvas) benar-benar ter-render — bukan langsung setelah
        // toggle loading, yang patch-nya masih asinkron.
        this.chartsDirty = false;

        this.state = useState({
            loading: true,
            active_period: null,
            latest_period: null,
            kpis: {},
            top_vendors: [],
            comparison_data: [],
            criteria_names: [],
            available_periods: [],
            focus_period_id: null,
        });

        onWillStart(async () => {
            // Chart.js ships in a lazy Odoo bundle; load it before the first
            // render so the global `Chart` constructor is available.
            try {
                await loadBundle("web.chartjs_lib");
                this.chartsAvailable = typeof Chart !== "undefined";
                if (this.chartsAvailable) {
                    Chart.defaults.font.family = CHART_FONT_FAMILY;
                    Chart.defaults.color = "#475569";
                }
            } catch (chartLibError) {
                console.error("Chart.js bundle failed to load:", chartLibError);
            }
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
            this.chartsDirty = false;
        });

        // Setelah setiap re-render (mis. ganti periode fokus), gambar ulang chart
        // hanya bila data baru dimuat DAN canvas sudah ada di DOM.
        onPatched(() => {
            if (this.chartsDirty && this.comparisonRef.el) {
                this.chartsDirty = false;
                this.renderCharts();
            }
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadDashboardData(options = {}) {
        try {
            const dashboardPayload = await this.orm.call(
                "scoring.period", "get_dashboard_data", [options]
            );
            Object.assign(this.state, dashboardPayload);
        } catch (loadError) {
            console.error("Dashboard load error:", loadError);
        }
        this.state.loading = false;
        // Tandai perlu gambar ulang; eksekusi nyata di onPatched (DOM siap).
        this.chartsDirty = true;
    }

    async onFocusPeriodChange(changeEvent) {
        const selectedPeriodId = parseInt(changeEvent.target.value, 10);
        this.state.loading = true;
        await this.loadDashboardData({ focus_period_id: selectedPeriodId });
        // renderCharts dipicu oleh onPatched setelah canvas kembali ter-render.
    }

    destroyCharts() {
        for (const chartInstance of this.chartInstances) {
            chartInstance.destroy();
        }
        this.chartInstances = [];
    }

    renderCharts() {
        if (typeof Chart === "undefined") return;
        this.destroyCharts();
        this.renderComparisonChart();
    }

    renderComparisonChart() {
        const canvas = this.comparisonRef.el;
        if (!canvas || !this.state.comparison_data.length) return;

        const vendorLabels = this.state.comparison_data.map((vendor) => vendor.partner_name);
        const datasets = this.state.criteria_names.map((criterionName, criterionIdx) => ({
            label: criterionName,
            data: this.state.comparison_data.map(
                (vendor) => vendor.criteria_scores[criterionName] || 0
            ),
            backgroundColor: CHART_COLORS[criterionIdx % CHART_COLORS.length],
            borderWidth: 0,
            borderRadius: 2,
        }));

        const chartInstance = new Chart(canvas, {
            type: "bar",
            data: { labels: vendorLabels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: _t("Perbandingan Skor Terbobot per Vendor"), font: { size: 14 } },
                    legend: { position: "bottom", labels: { boxWidth: 12, padding: 10 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(4)}`,
                        },
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, beginAtZero: true, title: { display: true, text: "Skor Terbobot" } },
                },
            },
        });
        this.chartInstances.push(chartInstance);
    }

    openPeriod(periodId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "scoring.period",
            res_id: periodId,
            views: [[false, "form"]],
        });
    }

    openPeriodList() {
        this.action.doAction("gifari_vendor_scoring.action_scoring_period");
    }

    // Drill-down: buka rincian skor satu vendor (popup) langsung dari leaderboard
    // sehingga pengambil keputusan bisa melihat "kenapa" tanpa pindah menu.
    openVendorScore(vendorScoreId) {
        if (!vendorScoreId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "vendor.score",
            res_id: vendorScoreId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    // Info pergerakan peringkat vendor vs periode tervalidasi sebelumnya.
    rankMovementInfo(vendor) {
        if (!vendor.has_previous) {
            return { icon: "fa-star-o", cls: "text-info", text: _t("Baru") };
        }
        const movement = vendor.rank_movement;
        if (movement > 0) {
            return { icon: "fa-arrow-up", cls: "text-success", text: `+${movement}` };
        }
        if (movement < 0) {
            return { icon: "fa-arrow-down", cls: "text-danger", text: `${movement}` };
        }
        return { icon: "fa-minus", cls: "text-muted", text: _t("Tetap") };
    }
}

registry.category("actions").add("vendor_scoring_dashboard", VendorScoringDashboard);
