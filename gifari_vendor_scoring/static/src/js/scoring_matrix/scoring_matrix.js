/** @odoo-module **/

import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
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
            bulkValue: "",
            bulkBusy: false,
        });

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

    /**
     * Aturan rentang skor: skala seragam 1-100 untuk Benefit maupun Cost.
     * Nilai 0/kosong dianggap "belum diisi" (bukan invalid). Arah "baik"
     * ditentukan saat normalisasi SAW (Cost: nilai lebih rendah lebih baik),
     * bukan saat input. Mengembalikan true bila valid.
     */
    isScoreInRange(scoreValue) {
        if (scoreValue === 0) {
            return true; // kosong/belum diisi
        }
        return scoreValue >= 1 && scoreValue <= 100;
    }

    /**
     * Border merah dikelola secara imperatif (DOM langsung), BUKAN lewat
     * reactive state. Sebabnya: OWL meng-compile <input t-att-value> sebagai
     * property dan memaksa set ulang `input.value` pada setiap re-render,
     * sehingga me-render ulang saat user mengetik akan mengembalikan nilai sel
     * ke nilai tersimpan (membuat sel tidak bisa diubah).
     */
    _setCellValidity(inputElement, isValid) {
        inputElement.classList.toggle("scoring-matrix__cell-input--invalid", !isValid);
    }

    getCellClass(vendor, criterionId) {
        const scoreValue = this.getScoreValue(vendor, criterionId);
        const lineId = this.getLineId(vendor, criterionId);
        const classes = ["scoring-matrix__cell-input", "vs-num"];
        if (scoreValue <= 0) {
            classes.push("scoring-matrix__cell-input--empty");
        }
        if (this.isCellSaving(lineId)) {
            classes.push("scoring-matrix__cell-input--saving");
        }
        return classes.join(" ");
    }

    /**
     * Nilai acuan SAW per kriteria (live, mengikuti skor yang sudah diisi):
     *  - Benefit → nilai MAKS (penyebut normalisasi: rᵢⱼ = xᵢⱼ / max).
     *  - Cost    → nilai MIN  (pembilang normalisasi: rᵢⱼ = min / xᵢⱼ).
     * Mengembalikan nilai acuan beserta nama vendor pemiliknya, atau null
     * jika belum ada skor terisi pada kolom kriteria tersebut.
     */
    getCriterionReference(criterion) {
        const isBenefit = criterion.type === "benefit";
        let best = null;
        for (const vendor of this.state.vendors) {
            const scoreValue = this.getScoreValue(vendor, criterion.id);
            if (scoreValue <= 0) {
                continue;
            }
            if (
                best === null ||
                (isBenefit ? scoreValue > best.value : scoreValue < best.value)
            ) {
                best = { value: scoreValue, vendorName: vendor.partner_name };
            }
        }
        if (best === null) {
            return null;
        }
        return {
            label: isBenefit ? _t("Maks") : _t("Min"),
            value: best.value,
            vendorName: best.vendorName,
        };
    }

    onCellInput(event, vendor, criterion) {
        const inputElement = event.target;
        const lineId = this.getLineId(vendor, criterion.id);
        if (!lineId) return;

        // Validasi rentang langsung (border merah) saat mengetik — imperatif,
        // tanpa menyentuh reactive state agar tidak memicu re-render.
        // Penyimpanan dilakukan saat blur/navigasi, bukan saat mengetik, supaya
        // re-render (yang memaksa set ulang input.value di OWL) tidak mereset
        // angka yang sedang diketik.
        const typedValue = parseFloat(inputElement.value) || 0;
        this._setCellValidity(inputElement, this.isScoreInRange(typedValue));
    }

    onCellBlur(event, vendor, criterion) {
        const inputElement = event.target;
        const lineId = this.getLineId(vendor, criterion.id);
        if (!lineId) return;
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

        if (!this.isScoreInRange(parsedScore)) {
            this._setCellValidity(inputElement, false);
            const rangeMessage =
                criterion.type === "benefit"
                    ? _t("Skor kriteria '%s' (Benefit) harus antara 1-100 (lebih tinggi lebih baik).", criterion.name)
                    : _t("Skor kriteria '%s' (Cost) harus antara 1-100 (lebih rendah lebih baik).", criterion.name);
            this.notification.add(rangeMessage, { type: "warning" });
            return;
        }
        this._setCellValidity(inputElement, true);

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

    async bulkFillEmpty() {
        const bulkValue = parseFloat(this.state.bulkValue) || 0;
        if (bulkValue <= 0) {
            this.notification.add(_t("Masukkan nilai lebih dari 0 untuk diisi cepat."), {
                type: "warning",
            });
            return;
        }

        this.state.bulkBusy = true;
        try {
            const result = await this.orm.call(
                "scoring.period",
                "bulk_fill_empty_scores",
                [this.periodId, bulkValue]
            );
            const filledCount = result.filled_count || 0;
            await this.loadMatrixData();
            if (filledCount > 0) {
                this.notification.add(
                    _t("%s sel kosong terisi dengan nilai %s.", filledCount, bulkValue),
                    { type: "success" }
                );
            } else {
                this.notification.add(
                    _t("Tidak ada sel yang terisi (nilai tidak valid untuk tipe kriteria, atau semua sel sudah terisi)."),
                    { type: "info" }
                );
            }
        } catch (bulkError) {
            this.notification.add(_t("Gagal mengisi sel secara massal."), { type: "danger" });
            console.error("Bulk fill error:", bulkError);
        }
        this.state.bulkBusy = false;
    }
}

ScoringMatrixWidget.props = {
    ...standardWidgetProps,
};

export const scoringMatrixWidget = {
    component: ScoringMatrixWidget,
};

registry.category("view_widgets").add("scoring_matrix", scoringMatrixWidget);
