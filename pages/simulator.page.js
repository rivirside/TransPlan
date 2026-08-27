/**
 * Extracted from simulator.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
window.TransPlanCDN = {
            leaflet: typeof L !== 'undefined' && typeof L.map === 'function',
            chartjs: typeof Chart !== 'undefined'
        };
