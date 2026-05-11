/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const CHART_COLORS = [
    "#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626",
    "#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
];

export class VendorScoringDashboard extends Component {
    static template = "gifari_vendor_scoring.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.comparisonRef = useRef("comparisonCanvas");
        this.trendRef = useRef("trendCanvas");

        this.chartInstances = [];

        this.state = useState({
            loading: true,
            active_period: null,
            latest_period: null,
            kpis: {},
            top_vendors: [],
            period_trend: [],
            comparison_data: [],
            criteria_names: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadDashboardData() {
        try {
            const dashboardPayload = await this.orm.call(
                "scoring.period", "get_dashboard_data", []
            );
            Object.assign(this.state, dashboardPayload);
        } catch (loadError) {
            console.error("Dashboard load error:", loadError);
        }
        this.state.loading = false;
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
                        borderColor: "#7c3aed",
                        backgroundColor: "rgba(124, 58, 237, 0.1)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: "#7c3aed",
                    },
                    {
                        label: _t("Rata-rata"),
                        data: this.state.period_trend.map((period) => period.avg_score),
                        borderColor: "#9ca3af",
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointBackgroundColor: "#9ca3af",
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
