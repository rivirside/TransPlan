/**
 * Donation/support banner — dismissible, localStorage-persisted.
 * Include this script on any page to show a bottom banner asking for support.
 */
(function() {
    'use strict';
    var STORAGE_KEY = 'transplan-donation-dismissed';
    var DISMISS_DAYS = 30; // Re-show after 30 days

    // Banner disabled — return immediately
    return;

    // Check if dismissed
    try {
        var dismissed = localStorage.getItem(STORAGE_KEY);
        if (dismissed) {
            var dismissedAt = parseInt(dismissed, 10);
            if (Date.now() - dismissedAt < DISMISS_DAYS * 86400000) return;
        }
    } catch (e) {}

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createBanner);
    } else {
        createBanner();
    }

    function createBanner() {
        var banner = document.createElement('div');
        banner.id = 'donation-banner';
        banner.setAttribute('role', 'complementary');
        banner.setAttribute('aria-label', 'Support transplant.today');

        // Styles
        var style = document.createElement('style');
        style.textContent = [
            '#donation-banner {',
            '  position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;',
            '  background: var(--surface, #fff); border-top: 1px solid var(--border, #e5e7eb);',
            '  box-shadow: 0 -2px 12px rgba(0,0,0,0.08); padding: 0.85rem 1.25rem;',
            '  display: flex; align-items: center; justify-content: center; gap: 1rem; flex-wrap: wrap;',
            '  font-size: 0.88rem; color: var(--text-2, #374151);',
            '  animation: slideUp 0.3s ease;',
            '}',
            '@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }',
            '#donation-banner .banner-text { flex: 0 1 auto; text-align: center; }',
            '#donation-banner .banner-text strong { color: var(--text-1, #111); }',
            '#donation-banner .banner-buttons { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; }',
            '#donation-banner .banner-btn {',
            '  padding: 0.4rem 0.85rem; border-radius: 6px; font-size: 0.82rem; font-weight: 500;',
            '  text-decoration: none; white-space: nowrap; transition: all 0.15s;',
            '}',
            '#donation-banner .btn-gh { background: #24292e; color: #fff; }',
            '#donation-banner .btn-gh:hover { background: #444d56; }',
            '#donation-banner .btn-bmc { background: #FFDD00; color: #000; }',
            '#donation-banner .btn-bmc:hover { background: #e6c700; }',
            '#donation-banner .btn-kofi { background: #FF5E5B; color: #fff; }',
            '#donation-banner .btn-kofi:hover { background: #e54542; }',
            '#donation-banner .banner-close {',
            '  background: none; border: none; color: var(--text-muted, #9ca3af);',
            '  font-size: 1.2rem; cursor: pointer; padding: 0.25rem 0.5rem; line-height: 1;',
            '  flex-shrink: 0;',
            '}',
            '#donation-banner .banner-close:hover { color: var(--text-1, #111); }',
            '@media (max-width: 768px) {',
            '  #donation-banner { display: none !important; }',
            '}',
        ].join('\n');
        document.head.appendChild(style);

        // Text
        var text = document.createElement('div');
        text.className = 'banner-text';
        var strong = document.createElement('strong');
        strong.textContent = 'transplant.today is free and open-source.';
        text.appendChild(strong);
        text.appendChild(document.createTextNode(' Help us keep it running. Every dollar supports development, data updates, and hosting.'));
        banner.appendChild(text);

        // Buttons
        var buttons = document.createElement('div');
        buttons.className = 'banner-buttons';

        var ghBtn = document.createElement('a');
        ghBtn.className = 'banner-btn btn-gh';
        ghBtn.href = 'https://github.com/sponsors/rivirside';
        ghBtn.target = '_blank';
        ghBtn.rel = 'noopener noreferrer';
        ghBtn.textContent = 'GitHub Sponsors';
        buttons.appendChild(ghBtn);

        var bmcBtn = document.createElement('a');
        bmcBtn.className = 'banner-btn btn-bmc';
        bmcBtn.href = 'https://buymeacoffee.com/transplantmatch';
        bmcBtn.target = '_blank';
        bmcBtn.rel = 'noopener noreferrer';
        bmcBtn.textContent = 'Buy Me a Coffee';
        buttons.appendChild(bmcBtn);

        var kofiBtn = document.createElement('a');
        kofiBtn.className = 'banner-btn btn-kofi';
        kofiBtn.href = 'https://ko-fi.com/rivir';
        kofiBtn.target = '_blank';
        kofiBtn.rel = 'noopener noreferrer';
        kofiBtn.textContent = 'Ko-fi';
        buttons.appendChild(kofiBtn);

        banner.appendChild(buttons);

        // Close button
        var close = document.createElement('button');
        close.className = 'banner-close';
        close.setAttribute('aria-label', 'Dismiss donation banner');
        close.textContent = '\u2715';
        close.addEventListener('click', function() {
            banner.remove();
            try { localStorage.setItem(STORAGE_KEY, String(Date.now())); } catch (e) {}
        });
        banner.appendChild(close);

        document.body.appendChild(banner);
    }
})();
