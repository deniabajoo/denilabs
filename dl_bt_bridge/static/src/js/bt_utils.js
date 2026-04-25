/** @odoo-module */

// =============================================================================
// BT Utils — Platform Detection & Intent Dispatch
// =============================================================================
// Utility functions for the DL BT Bridge module.
// Handles Android detection, paper width mapping, intent URI construction,
// and intent dispatch via hidden iframe.
// =============================================================================

/**
 * Detects if the current browser is running on an Android device.
 * Uses the modern userAgentData API (Chromium 93+) with a legacy UA
 * string fallback for older browsers and WebViews.
 *
 * @returns {boolean} True if running on Android
 */
export function isAndroidDevice() {
    // Modern API — available in Chrome/Edge 93+ on Android
    if (navigator.userAgentData?.platform) {
        return navigator.userAgentData.platform === 'Android';
    }
    // Legacy fallback — works everywhere including WebView
    return /android/i.test(navigator.userAgent);
}

/**
 * Returns the pixel width corresponding to a thermal paper size selection.
 *
 * Standard thermal printer DPI is 203 dpi:
 *   - 58mm paper ≈ 48mm printable area ≈ 384 dots
 *   - 80mm paper ≈ 72mm printable area ≈ 576 dots
 *
 * @param {'58mm' | '80mm'} paperSize - The selected paper size from pos.config
 * @returns {number} Width in pixels
 */
export function getPaperWidthPx(paperSize) {
    const PAPER_WIDTH_MAP = {
        '58mm': 384,
        '80mm': 576,
    };
    return PAPER_WIDTH_MAP[paperSize] || 384;
}

/**
 * Constructs the intent URI for the given scheme and base64 image data.
 *
 * Supported URI formats:
 *   - rawbt:                rawbt:base64,<DATA>
 *   - printershare:         printershare://print?base64=<DATA>
 *   - pos_bluetooth_printer: pos_bluetooth_printer://print?img=<DATA>
 *
 * @param {string} scheme - One of 'rawbt', 'printershare', 'pos_bluetooth_printer'
 * @param {string} base64Data - Base64-encoded PNG image data (WITHOUT the data URI prefix)
 * @returns {string} The complete intent URI ready for dispatch
 */
export function buildIntentUri(scheme, base64Data) {
    switch (scheme) {
        case 'rawbt':
            return `rawbt:base64,${base64Data}`;
        case 'printershare':
            return `printershare://print?base64=${base64Data}`;
        case 'pos_bluetooth_printer':
            return `pos_bluetooth_printer://print?img=${base64Data}`;
        default:
            // Default to RawBT format as it's the most common
            console.warn(`[BT Bridge] Unknown intent scheme "${scheme}", defaulting to rawbt`);
            return `rawbt:base64,${base64Data}`;
    }
}

/**
 * Dispatches a print intent by injecting a hidden iframe with the URI.
 *
 * Using an iframe (instead of window.location.href) prevents the POS session
 * from navigating away if the intent app is installed. If the app is NOT
 * installed, the iframe simply fails silently — no crash, no 404 page.
 *
 * The iframe is cleaned up after a 3-second timeout, which is sufficient
 * for the Android OS to hand off the intent to the receiving app.
 *
 * @param {string} uri - The fully constructed intent URI
 * @returns {Promise<boolean>} Resolves true after dispatch attempt completes
 */
export function dispatchIntent(uri) {
    return new Promise((resolve) => {
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = uri;
        document.body.appendChild(iframe);

        // Clean up after the OS has had time to process the intent
        setTimeout(() => {
            if (iframe.parentNode) {
                iframe.parentNode.removeChild(iframe);
            }
            resolve(true);
        }, 3000);
    });
}
