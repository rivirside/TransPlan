/**
 * Extracted from faq.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
// Open the targeted FAQ entry when arriving at (or clicking to) a #fragment.
    // Anchors point at the <details> element itself, which browsers do not auto-expand.
    (function() {
        'use strict';
        function openFromHash() {
            var hash = window.location.hash;
            if (!hash || hash.length < 2) return;
            var el = document.getElementById(hash.slice(1));
            if (!el || el.tagName.toLowerCase() !== 'details') return;
            el.open = true;
            el.scrollIntoView({ block: 'start' });
        }
        window.addEventListener('hashchange', openFromHash);
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', openFromHash);
        } else {
            openFromHash();
        }
    })();
