/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Gifari Approval Dashboard — PT Indopora
 * OWL Component for monitoring Sales & Purchase discount approval workflows
 */
class GifariApprovalDashboard extends Component {
    static template = "gifari_approval_dashboard.ApprovalDashboard";

    setup() {
        this.actionService = useService("action");
        this.notificationService = useService("notification");

        this.state = useState({
            loading: false,
            moduleFilter: "all",
            dateRange: "7",
            kpi: {
                so_pending: 0,
                po_pending: 0,
                approved_today: 0,
                rejected_today: 0,
                total_pending: 0,
            },
            trend: {
                labels: [],
                so_approved: [],
                po_approved: [],
                so_rejected: [],
                po_rejected: [],
            },
            pendingList: [],
            userName: "",
            currentDate: this._formatDate(new Date()),
            modal: {
                visible: false,
                action: "approve",
                item: null,
                notes: "",
                reason: "",
            },
        });

        this.chart = null;

        onMounted(() => {
            this.loadData();
        });

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        });
    }

    _formatDate(date) {
        return date.toLocaleDateString("id-ID", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    async loadData() {
        if (this.state.loading) return;
        this.state.loading = true;

        try {
            const data = await rpc("/gifari/approval/dashboard/data", {
                date_range: this.state.dateRange,
                module_filter: this.state.moduleFilter,
            });

            this.state.kpi = data.kpi || {};
            this.state.trend = data.trend || {};
            this.state.pendingList = data.pending_list || [];
            this.state.userName = data.user?.name || "";
            this.state.currentDate = this._formatDate(new Date());

            // Render chart after data loads
            this._renderChart();
        } catch (error) {
            this.notificationService.add(
                "Failed to load dashboard data. Please try again.",
                { type: "danger" }
            );
            console.error("Dashboard load error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    _renderChart() {
        const canvas = document.getElementById("gadTrendChart");
        if (!canvas) return;

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        // Check if Chart.js is available (it's bundled with Odoo)
        if (typeof Chart === "undefined") {
            console.warn("Chart.js not available");
            return;
        }

        const trend = this.state.trend;
        if (!trend.labels || !trend.labels.length) return;

        this.chart = new Chart(canvas, {
            type: "bar",
            data: {
                labels: trend.labels,
                datasets: [
                    {
                        label: "SO Approved",
                        data: trend.so_approved || [],
                        backgroundColor: "rgba(99,102,241,0.7)",
                        borderColor: "#6366f1",
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                    {
                        label: "PO Approved",
                        data: trend.po_approved || [],
                        backgroundColor: "rgba(139,92,246,0.7)",
                        borderColor: "#8b5cf6",
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                    {
                        label: "SO Rejected",
                        data: trend.so_rejected || [],
                        backgroundColor: "rgba(239,68,68,0.5)",
                        borderColor: "#ef4444",
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                    {
                        label: "PO Rejected",
                        data: trend.po_rejected || [],
                        backgroundColor: "rgba(239,68,68,0.3)",
                        borderColor: "#ef4444",
                        borderWidth: 1,
                        borderRadius: 4,
                        borderDash: [4, 4],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: "#94a3b8",
                            font: { size: 11 },
                            boxWidth: 12,
                        },
                    },
                    tooltip: {
                        backgroundColor: "#1e293b",
                        borderColor: "#334155",
                        borderWidth: 1,
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#64748b", font: { size: 10 } },
                        grid: { color: "#1e293b" },
                    },
                    y: {
                        ticks: {
                            color: "#64748b",
                            font: { size: 10 },
                            stepSize: 1,
                        },
                        grid: { color: "#253047" },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    setFilter(filter) {
        this.state.moduleFilter = filter;
        this.loadData();
    }

    onDateRangeChange(ev) {
        this.state.dateRange = ev.target.value;
        this.loadData();
    }

    navigateTo(docType) {
        if (docType === "sale") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Sales Approval Queue",
                res_model: "sale.order",
                view_mode: "list,form",
                domain: [["approval_state", "=", "pending"]],
                views: [[false, "list"], [false, "form"]],
            });
        } else if (docType === "purchase") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Purchase Approval Queue",
                res_model: "purchase.order",
                view_mode: "list,form",
                domain: [["approval_state", "=", "pending"]],
                views: [[false, "list"], [false, "form"]],
            });
        }
    }

    openRecord(item) {
        const model = item.type === "SO" ? "sale.order" : "purchase.order";
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: item.id,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    openQuickAction(item, action) {
        this.state.modal = {
            visible: true,
            action: action,
            item: item,
            notes: "",
            reason: "",
        };
    }

    closeModal() {
        this.state.modal.visible = false;
    }

    async confirmQuickAction() {
        const modal = this.state.modal;
        const item = modal.item;

        if (modal.action === "reject" && !modal.reason.trim()) {
            this.notificationService.add("Please provide a rejection reason.", {
                type: "warning",
            });
            return;
        }

        try {
            const result = await rpc("/gifari/approval/quick_action", {
                doc_type: item.type === "SO" ? "sale" : "purchase",
                doc_id: item.id,
                action: modal.action,
                notes: modal.notes || "",
                reason: modal.reason || "",
            });

            if (result.success) {
                this.notificationService.add(
                    `${item.name} has been ${modal.action}d successfully.`,
                    { type: modal.action === "approve" ? "success" : "info" }
                );
                this.closeModal();
                await this.loadData();
            } else {
                this.notificationService.add(
                    `Error: ${result.error || "Action failed."}`,
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notificationService.add("An unexpected error occurred.", {
                type: "danger",
            });
            console.error("Quick action error:", error);
        }
    }
}

// Register as Odoo client action
registry.category("actions").add(
    "gifari_approval_dashboard",
    GifariApprovalDashboard
);
