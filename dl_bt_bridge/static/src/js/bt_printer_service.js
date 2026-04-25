/** @odoo-module */

// =============================================================================
// BT Printer Service — PosPrinterService Patch
// =============================================================================
// Patches the registered POS "printer" service (PosPrinterService) to intercept
// receipt printing and route it through Android Bluetooth intents when:
//   1. bt_print_enabled is true in pos.config
//   2. The device is detected as Android
//
// On non-Android devices or when BT printing is disabled, the patch is
// transparent — all calls pass through to super unchanged.
//
// This module strictly handles customer-facing receipts. Kitchen/preparation
// ticket printing (which uses pos.printer / BasePrinter) is NOT intercepted.
// =============================================================================

import { PosPrinterService } from "@point_of_sale/app/services/pos_printer_service";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    isAndroidDevice,
    getPaperWidthPx,
    buildIntentUri,
    dispatchIntent,
} from "@dl_bt_bridge/js/bt_utils";
import { toCanvas } from "@point_of_sale/app/utils/html-to-image";
import { waitImages } from "@point_of_sale/utils";

const BT_LOG_PREFIX = "[BT Bridge]";

patch(PosPrinterService.prototype, {

    // =========================================================================
    // Private Helpers
    // =========================================================================

    /**
     * Determine whether Bluetooth printing should be active for the current
     * request. Both the config toggle AND Android platform must be true.
     *
     * @returns {boolean}
     */
    _isBtPrintActive() {
        const config = this.hardware_proxy?.pos?.config;
        if (!config) {
            return false;
        }
        return Boolean(config.bt_print_enabled) && isAndroidDevice();
    },

    /**
     * Read BT configuration values from pos.config.
     *
     * @returns {{ scheme: string, paperWidthPx: number }}
     */
    _getBtConfig() {
        const config = this.hardware_proxy.pos.config;
        return {
            scheme: config.bt_intent_scheme || "rawbt",
            paperWidthPx: getPaperWidthPx(config.bt_paper_size || "58mm"),
        };
    },

    /**
     * Render an HTML element to a base64 PNG string at the configured
     * paper width. The element is temporarily mounted in Odoo's off-screen
     * `.render-container` for accurate layout calculation.
     *
     * @param {HTMLElement} el - The receipt DOM element
     * @param {number} paperWidthPx - Target width in pixels
     * @returns {Promise<string>} Base64-encoded PNG (without data URI prefix)
     */
    async _renderToBtImage(el, paperWidthPx) {
        // Force thermal paper width constraints on the element
        el.style.width = `${paperWidthPx}px`;
        el.style.maxWidth = `${paperWidthPx}px`;
        el.style.minWidth = `${paperWidthPx}px`;
        el.style.overflow = "hidden";
        el.style.backgroundColor = "#ffffff";

        // Mount in the off-screen render container (same approach as
        // Odoo's htmlToCanvas in render_service.js)
        const container = document.querySelector(".render-container");
        if (!container) {
            throw new Error("Render container (.render-container) not found in DOM");
        }

        const elClone = el.cloneNode(true);
        container.textContent = "";
        container.appendChild(elClone);

        // Allow the browser to compute layout
        await new Promise((resolve) => requestAnimationFrame(resolve));
        await waitImages(elClone);

        // Render to canvas using Odoo's bundled html-to-image
        const canvas = await toCanvas(elClone, {
            backgroundColor: "#ffffff",
            height: Math.ceil(elClone.scrollHeight),
            width: paperWidthPx,
            pixelRatio: 1,
        });

        // Extract base64 PNG
        const dataUrl = canvas.toDataURL("image/png");
        return dataUrl.replace("data:image/png;base64,", "");
    },

    // =========================================================================
    // Patched Public Methods
    // =========================================================================

    /**
     * Override: Main print entry point.
     *
     * When BT printing is active:
     *   1. Render the OWL component to HTML via this.renderer.toHtml()
     *   2. Wait for embedded images to load
     *   3. Render to a constrained-width canvas → base64 PNG
     *   4. Dispatch the Android intent URI
     *
     * On failure, shows an AlertDialog offering browser print fallback.
     *
     * @param {Component} component - OWL component class (e.g., OrderReceipt)
     * @param {Object} props - Component props
     * @param {Object} [options={}] - Print options
     * @returns {Promise<Object>} Print result with { successful: boolean }
     */
    async print(component, props, options = {}) {
        if (!this._isBtPrintActive()) {
            return await super.print(...arguments);
        }

        console.info(`${BT_LOG_PREFIX} Bluetooth print path activated`);
        this.state.isPrinting = true;

        try {
            // Step 1: Render OWL component to HTML element
            const el = await this.renderer.toHtml(component, props);

            // Step 2: Wait for images (logos, barcodes, QR codes)
            try {
                await waitImages(el);
            } catch (e) {
                console.warn(`${BT_LOG_PREFIX} Some images could not be loaded:`, e);
            }

            // Step 3 & 4: Render to image and dispatch
            const { scheme, paperWidthPx } = this._getBtConfig();
            console.info(
                `${BT_LOG_PREFIX} Rendering receipt at ${paperWidthPx}px width, scheme: ${scheme}`
            );

            const base64Data = await this._renderToBtImage(el, paperWidthPx);
            const uri = buildIntentUri(scheme, base64Data);

            console.info(
                `${BT_LOG_PREFIX} Dispatching intent (${scheme}), payload size: ${
                    Math.round(base64Data.length / 1024)
                } KB`
            );

            await dispatchIntent(uri);

            console.info(`${BT_LOG_PREFIX} Intent dispatched successfully`);
            return { successful: true };
        } catch (error) {
            console.error(`${BT_LOG_PREFIX} Bluetooth print failed:`, error);

            // Show user-friendly error with browser print fallback
            this.dialog.add(AlertDialog, {
                title: _t("Bluetooth Print Failed"),
                body: _t(
                    "Could not send receipt to the Bluetooth printer. " +
                    "Please ensure the printing app (e.g., RawBT) is installed " +
                    "and a Bluetooth printer is paired.\n\n" +
                    "The receipt will be printed via the browser instead."
                ),
            });

            // Attempt browser print as ultimate fallback
            try {
                return super.printWeb(
                    await this.renderer.toHtml(component, props)
                );
            } catch {
                return { successful: false };
            }
        } finally {
            this.state.isPrinting = false;
        }
    },

    /**
     * Override: printHtml is called when a pre-rendered HTML element needs
     * to be printed (e.g., from BasePrinter.printReceipt flow).
     *
     * When BT is active, we intercept and render the element as an image
     * instead of sending it to IoT Box / proxy.
     *
     * @param {HTMLElement} el - Pre-rendered receipt HTML element
     * @param {Object} [options={}] - Print options
     * @returns {Promise<Object>} Print result
     */
    async printHtml(el, options = {}) {
        if (!this._isBtPrintActive()) {
            return await super.printHtml(...arguments);
        }

        console.info(`${BT_LOG_PREFIX} printHtml intercepted for BT printing`);

        try {
            const { scheme, paperWidthPx } = this._getBtConfig();
            const base64Data = await this._renderToBtImage(el, paperWidthPx);
            const uri = buildIntentUri(scheme, base64Data);

            await dispatchIntent(uri);
            return { successful: true };
        } catch (error) {
            console.error(`${BT_LOG_PREFIX} printHtml BT failed:`, error);
            // Fall through to standard printHtml
            return await super.printHtml(...arguments);
        }
    },
});
