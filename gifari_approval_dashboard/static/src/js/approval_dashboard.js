/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class ApprovalDashboard extends Component {
    static template = "gifari_approval_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.rpc = rpc;
        this.action = useService("action");
        this.state = useState({
            loading: true,
            kpi: {},
            pending_sales: [],
            pending_purchases: [],
            recent_sale_logs: [],
            recent_purchase_logs: [],
            activeTab: "sales",
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/gifari/approval/dashboard/data", {});
            Object.assign(this.state, data, { loading: false });
        } catch (e) {
            console.error("Dashboard load error:", e);
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData();
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    openSaleOrder(orderId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPurchaseOrder(orderId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "purchase.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSaleQueue() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Discount Approval Queue",
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            domain: [["approval_state", "=", "pending"]],
            target: "current",
        });
    }

    openPurchaseQueue() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Amount Approval Queue",
            res_model: "purchase.order",
            views: [[false, "list"], [false, "form"]],
            domain: [["approval_state", "=", "pending"]],
            target: "current",
        });
    }

    getActionBadgeClass(action) {
        const map = {
            submit: "badge-info",
            resubmit: "badge-info",
            approve: "badge-success",
            counter_offer: "badge-success",
            reject: "badge-danger",
            cancel: "badge-secondary",
            reset: "badge-warning",
        };
        return map[action] || "badge-secondary";
    }

    getAgingClass(days) {
        if (days >= 3) return "aging-critical";
        if (days >= 1) return "aging-warning";
        return "aging-ok";
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("id-ID", {
            style: "decimal",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value || 0);
    }
}

registry.category("actions").add("gifari_approval_dashboard", ApprovalDashboard);
