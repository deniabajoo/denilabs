/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Data-Dense Dashboard palette: corporate navy/blue + amber highlight.
const CHART_COLORS = [
    "#1E40AF", "#3B82F6", "#0EA5E9", "#0D9488", "#F59E0B",
    "#6366F1", "#2563EB", "#06B6D4", "#10B981", "#D97706",
];
const COLOR_PRIMARY = "#1E40AF";
const COLOR_MUTED = "#94A3B8";
const CHART_FONT_FAMILY =
    "'Fira Sans', 'Segoe UI', system-ui, -apple-system, sans-serif";

export class VendorScoringDashboard extends Component {
    static template = "gifari_vendor_scoring.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.comparisonRef = useRef("comparisonCanvas");
        this.trendRef = useRef("trendCanvas");
        this.radarRef = useRef("radarCanvas");

        this.chartInstances = [];
        this.chartsAvailable = false;

        this.state = useState({
            loading: true,
            active_period: null,
            latest_period: null,
            kpis: {},
            top_vendors: [],
            period_trend: [],
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
    }

    async onFocusPeriodChange(changeEvent) {
        const selectedPeriodId = parseInt(changeEvent.target.value, 10);
        this.state.loading = true;
        await this.loadDashboardData({ focus_period_id: selectedPeriodId });
        this.renderCharts();
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
        this.renderRadarChart();
        this.renderTrendChart();
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

    renderRadarChart() {
        const canvas = this.radarRef.el;
        if (!canvas || !this.state.comparison_data.length || !this.state.criteria_names.length) {
            return;
        }

        // Profil multi-kriteria untuk maksimum 3 vendor teratas.
        const topVendors = this.state.comparison_data.slice(0, 3);
        const datasets = topVendors.map((vendor, vendorIdx) => {
            const baseColor = CHART_COLORS[vendorIdx % CHART_COLORS.length];
            return {
                label: vendor.partner_name,
                data: this.state.criteria_names.map(
                    (criterionName) => vendor.criteria_scores[criterionName] || 0
                ),
                borderColor: baseColor,
                backgroundColor: `${baseColor}33`,
                borderWidth: 2,
                pointBackgroundColor: baseColor,
                pointRadius: 3,
            };
        });

        const chartInstance = new Chart(canvas, {
            type: "radar",
            data: { labels: this.state.criteria_names, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: _t("Profil Kriteria Top 3 Vendor"), font: { size: 14 } },
                    legend: { position: "bottom", labels: { boxWidth: 12, padding: 10 } },
                },
                scales: {
                    r: { beginAtZero: true, ticks: { backdropColor: "transparent" } },
                },
            },
        });
        this.chartInstances.push(chartInstance);
    }

    renderTrendChart() {
        const canvas = this.trendRef.el;
        if (!canvas || !this.state.period_trend.length) return;

        const periodLabels = this.state.period_trend.map((period) => period.name);

        const chartInstance = new Chart(canvas, {
            type: "line",
            data: {
                labels: periodLabels,
                datasets: [
                    {
                        label: _t("Skor Tertinggi"),
                        data: this.state.period_trend.map((period) => period.top_score),
                        borderColor: COLOR_PRIMARY,
                        backgroundColor: "rgba(30, 64, 175, 0.1)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: COLOR_PRIMARY,
                    },
                    {
                        label: _t("Rata-rata"),
                        data: this.state.period_trend.map((period) => period.avg_score),
                        borderColor: COLOR_MUTED,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointBackgroundColor: COLOR_MUTED,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: _t("Trend Skor Antar Periode"), font: { size: 14 } },
                    legend: { position: "bottom", labels: { boxWidth: 12 } },
                },
                scales: {
                    y: { beginAtZero: true, max: 1, title: { display: true, text: "Final Score" } },
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
}

registry.category("actions").add("vendor_scoring_dashboard", VendorScoringDashboard);
