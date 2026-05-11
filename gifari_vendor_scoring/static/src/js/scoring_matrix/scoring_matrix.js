/** @odoo-module **/

import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ScoringMatrixWidget extends Component {
    static template = "gifari_vendor_scoring.ScoringMatrix";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.matrixRef = useRef("matrixContainer");

        this.state = useState({
            criteria: [],
            vendors: [],
            totalCells: 0,
            filledCells: 0,
            loading: true,
            savingCells: {},
            periodState: "",
        });

        this.saveTimers = {};

        onWillStart(async () => {
            await this.loadMatrixData();
        });
    }

    get periodId() {
        return this.props.record.resId;
    }

    get progressPercent() {
        if (!this.state.totalCells) return 0;
        return Math.round((this.state.filledCells / this.state.totalCells) * 100);
    }

    get isReadonly() {
        return this.state.periodState !== "scoring";
    }

    async loadMatrixData() {
        this.state.loading = true;
        try {
            const matrixPayload = await this.orm.call(
                "scoring.period",
                "get_matrix_data",
                [this.periodId]
            );
            this.state.criteria = matrixPayload.criteria;
            this.state.vendors = matrixPayload.vendors;
            this.state.totalCells = matrixPayload.total_cells;
            this.state.filledCells = matrixPayload.filled_cells;
            this.state.periodState = matrixPayload.state;
        } catch (loadError) {
            this.notification.add(_t("Gagal memuat data matrix."), { type: "danger" });
            console.error("Matrix load error:", loadError);
        }
        this.state.loading = false;
    }

    getScoreValue(vendor, criterionId) {
        const lineData = vendor.score_lines[criterionId];
        return lineData ? lineData.raw_score : 0;
    }

    getLineId(vendor, criterionId) {
        const lineData = vendor.score_lines[criterionId];
        return lineData ? lineData.line_id : null;
    }

    isCellEmpty(vendor, criterionId) {
        return this.getScoreValue(vendor, criterionId) <= 0;
    }

    isCellSaving(lineId) {
        return !!this.state.savingCells[lineId];
    }

    getCellClass(vendor, criterionId) {
        const scoreValue = this.getScoreValue(vendor, criterionId);
        const lineId = this.getLineId(vendor, criterionId);
        const classes = ["scoring-matrix__cell-input"];
        if (scoreValue <= 0) {
            classes.push("scoring-matrix__cell-input--empty");
        }
        if (this.isCellSaving(lineId)) {
            classes.push("scoring-matrix__cell-input--saving");
        }
        return classes.join(" ");
    }

    onCellInput(event, vendor, criterion) {
        const inputElement = event.target;
        const lineId = this.getLineId(vendor, criterion.id);
        if (!lineId) return;

        const cellKey = `${lineId}`;
        if (this.saveTimers[cellKey]) {
            clearTimeout(this.saveTimers[cellKey]);
        }

        this.saveTimers[cellKey] = setTimeout(() => {
            this.saveScore(inputElement, vendor, criterion, lineId);
        }, 500);
    }

    onCellBlur(event, vendor, criterion) {
        const inputElement = event.target;
        const lineId = this.getLineId(vendor, criterion.id);
        if (!lineId) return;

        const cellKey = `${lineId}`;
        if (this.saveTimers[cellKey]) {
            clearTimeout(this.saveTimers[cellKey]);
        }
        this.saveScore(inputElement, vendor, criterion, lineId);
    }

    onCellKeydown(event, vendorIndex, criterionIndex) {
        const vendorCount = this.state.vendors.length;
        const criterionCount = this.state.criteria.length;

        let nextVendorIdx = vendorIndex;
        let nextCriterionIdx = criterionIndex;

        if (event.key === "Tab" && !event.shiftKey) {
            event.preventDefault();
            nextCriterionIdx++;
            if (nextCriterionIdx >= criterionCount) {
                nextCriterionIdx = 0;
                nextVendorIdx++;
            }
        } else if (event.key === "Tab" && event.shiftKey) {
            event.preventDefault();
            nextCriterionIdx--;
            if (nextCriterionIdx < 0) {
                nextCriterionIdx = criterionCount - 1;
                nextVendorIdx--;
            }
        } else if (event.key === "Enter") {
            event.preventDefault();
            nextVendorIdx++;
        } else if (event.key === "ArrowDown") {
            event.preventDefault();
            nextVendorIdx++;
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            nextVendorIdx--;
        } else if (event.key === "ArrowRight" && event.target.selectionStart === event.target.value.length) {
            event.preventDefault();
            nextCriterionIdx++;
        } else if (event.key === "ArrowLeft" && event.target.selectionStart === 0) {
            event.preventDefault();
            nextCriterionIdx--;
        } else {
            return;
        }

        if (nextVendorIdx >= 0 && nextVendorIdx < vendorCount &&
            nextCriterionIdx >= 0 && nextCriterionIdx < criterionCount) {
            const targetInput = this.matrixRef.el?.querySelector(
                `input[data-vendor-idx="${nextVendorIdx}"][data-criterion-idx="${nextCriterionIdx}"]`
            );
            if (targetInput) {
                targetInput.focus();
                targetInput.select();
            }
        }
    }

    async saveScore(inputElement, vendor, criterion, lineId) {
        const parsedScore = parseFloat(inputElement.value) || 0;

        if (criterion.type === "benefit" && parsedScore !== 0 && (parsedScore < 1 || parsedScore > 100)) {
            this.notification.add(
                _t("Skor kriteria '%s' (Benefit) harus antara 1-100.", criterion.name),
                { type: "warning" }
            );
            return;
        }
        if (criterion.type === "cost" && parsedScore < 0) {
            this.notification.add(
                _t("Skor kriteria '%s' (Cost) harus lebih dari 0.", criterion.name),
                { type: "warning" }
            );
            return;
        }

        const previousScore = this.getScoreValue(vendor, criterion.id);
        if (parsedScore === previousScore) return;

        this.state.savingCells[lineId] = true;

        try {
            await this.orm.call(
                "scoring.period",
                "update_matrix_score",
                [this.periodId, lineId, parsedScore]
            );

            const wasPreviouslyEmpty = previousScore <= 0;
            const isNowEmpty = parsedScore <= 0;

            vendor.score_lines[criterion.id].raw_score = parsedScore;

            if (wasPreviouslyEmpty && !isNowEmpty) {
                vendor.filled_count++;
                this.state.filledCells++;
            } else if (!wasPreviouslyEmpty && isNowEmpty) {
                vendor.filled_count--;
                this.state.filledCells--;
            }
        } catch (saveError) {
            this.notification.add(_t("Gagal menyimpan skor."), { type: "danger" });
            inputElement.value = previousScore || "";
        }

        delete this.state.savingCells[lineId];
    }

    getVendorProgress(vendor) {
        if (!vendor.total_criteria) return 0;
        return Math.round((vendor.filled_count / vendor.total_criteria) * 100);
    }
}

ScoringMatrixWidget.props = {
    record: { type: Object },
};

export const scoringMatrixWidget = {
    component: ScoringMatrixWidget,
};

registry.category("view_widgets").add("scoring_matrix", scoringMatrixWidget);
