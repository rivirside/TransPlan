/**
 * site-chrome.js — Shared nav & footer for all transplant.today pages.
 *
 * Injects nav into #nav-placeholder, footer into #footer-placeholder.
 * Footer variant is read from data-footer-variant attribute (default | simulator | advocacy).
 * Dispatches 'nav-ready' event after injection so dark-mode.js can find .nav-links.
 *
 * Runs immediately (not on DOMContentLoaded) — loaded at end of <body>.
 */
(function () {
  'use strict';

  // --------------- NAV ---------------
  var navHTML =
    '<nav class="site-nav" aria-label="Site navigation">' +
      '<div class="nav-inner">' +
        '<a href="/" class="nav-brand">' +
          '<span class="nav-brand-icon" aria-hidden="true">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>' +
          '</span>' +
          '<span class="nav-brand-text">transplant.today</span>' +
        '</a>' +
        '<button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>' +
        '<div class="nav-links">' +
          '<a href="simulator.html" class="nav-link">Simulator</a>' +
          '<div class="nav-dropdown">' +
            '<button class="nav-link nav-dropdown-trigger" aria-expanded="false" aria-haspopup="true">Resources <span class="dropdown-arrow" aria-hidden="true">&#9662;</span></button>' +
            '<div class="nav-dropdown-menu" role="menu">' +
              '<a href="find-centers.html" class="nav-dropdown-item" role="menuitem">Find My Centers</a>' +
              '<a href="wait-estimator.html" class="nav-dropdown-item" role="menuitem">Wait Estimator</a>' +
              '<a href="centers.html" class="nav-dropdown-item" role="menuitem">Center Explorer</a>' +
              '<a href="compare.html" class="nav-dropdown-item" role="menuitem">Compare Centers</a>' +
              '<a href="organ-guides.html" class="nav-dropdown-item" role="menuitem">Organ Guides</a>' +
              '<a href="education.html" class="nav-dropdown-item" role="menuitem">Education</a>' +
              '<a href="support.html" class="nav-dropdown-item" role="menuitem">Patient Support</a>' +
              '<a href="advocacy.html" class="nav-dropdown-item" role="menuitem">Give Back</a>' +
              '<a href="faq.html" class="nav-dropdown-item" role="menuitem">FAQ</a>' +
              '<a href="checklist.html" class="nav-dropdown-item" role="menuitem">Checklist</a>' +
            '</div>' +
          '</div>' +
          '<a href="data.html" class="nav-link nav-link-accent">Data</a>' +
          '<a href="docs-site/build/" class="nav-link" target="_blank" rel="noopener">Docs</a>' +
        '</div>' +
      '</div>' +
    '</nav>';

  // --------------- FOOTER DISCLAIMER VARIANTS ---------------
  var disclaimers = {
    default:
      '<h3>Disclaimer</h3>' +
      '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not a medical device, does not provide medical advice, and cannot predict individual transplant outcomes.</p>' +
      '<p><strong>Scores are relative comparisons</strong> based on publicly available regional statistics. They are not clinical assessments.</p>' +
      '<p><strong>Always consult your transplant team</strong> and healthcare providers before making any decisions about where to list for a transplant.</p>',

    simulator:
      '<h3>Disclaimer</h3>' +
      '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not a medical device, does not provide medical advice, and cannot predict individual transplant outcomes.</p>' +
      '<p><strong>What this tool cannot account for:</strong> HLA typing and crossmatch compatibility, specific disease etiology and comorbidities, your current functional status, individual OPO performance, or your relationship with specific transplant programs. While optional inputs for cPRA, MELD, and LAS adjust scoring, they are rough approximations and do not replace clinical allocation models.</p>' +
      '<p><strong>Scores are relative comparisons</strong> based on publicly available regional statistics. They are not clinical assessments. A city scoring 85/100 does not mean you have an 85% chance of a successful transplant there.</p>' +
      '<p><strong>Some data is estimated or manually curated</strong> and may not reflect current conditions. Wait time estimates are derived from regional averages and may not match your individual circumstances.</p>' +
      '<p><strong>Always consult your transplant team</strong> and healthcare providers before making any decisions about where to list for a transplant. Your medical team has access to your complete clinical picture, which this tool does not.</p>',

    advocacy:
      '<h3>Disclaimer</h3>' +
      '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not affiliated with any of the organizations listed on this page. Links are provided for informational purposes.</p>' +
      '<p><strong>Always verify information</strong> directly with the organization before taking action.</p>'
  };

  // --------------- FOOTER LINKS VARIANTS ---------------
  var footerLinks = {
    default:
      '<a href="simulator.html">Simulator</a>' +
      '<a href="docs-site/build/" target="_blank" rel="noopener">Documentation</a>',

    simulator:
      '<a href="/">Home</a>' +
      '<a href="docs-site/build/" target="_blank" rel="noopener">Documentation</a>'
  };

  function buildFooter(variant) {
    var disc = disclaimers[variant] || disclaimers['default'];
    var links = footerLinks[variant] || footerLinks['default'];
    return (
      '<footer id="disclaimer-full" class="site-footer">' +
        '<div class="footer-inner">' +
          '<div class="footer-disclaimer">' + disc + '</div>' +
          '<div class="footer-meta">' +
            '<div class="footer-links">' + links + '</div>' +
            '<p class="footer-copy">transplant.today is under active development. Not affiliated with UNOS, OPTN, or any transplant center.</p>' +
            '<p class="footer-copy">Contact: <a href="mailto:tomer@arizona.edu">tomer@arizona.edu</a></p>' +
          '</div>' +
        '</div>' +
      '</footer>'
    );
  }

  // --------------- ACTIVE LINK DETECTION ---------------
  function markActiveLink(navEl) {
    var path = window.location.pathname;
    // Normalize: strip leading slash, handle index
    var page = path.replace(/^\//, '').replace(/^TransPlan\//, '') || 'index.html';
    if (page === '' || page === '/') page = 'index.html';

    // Map of nav-link hrefs to their normalized page
    var navLinks = navEl.querySelectorAll('.nav-link[href]');
    navLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href === '#' || link.classList.contains('nav-dropdown-trigger')) return;
      if (href === '/' && (page === 'index.html' || page === '')) {
        link.classList.add('nav-link--active');
      } else if (href !== '/' && page === href) {
        link.classList.add('nav-link--active');
      }
    });

    // Dropdown items
    var dropdownItems = navEl.querySelectorAll('.nav-dropdown-item[href]');
    dropdownItems.forEach(function (item) {
      var href = item.getAttribute('href');
      if (page === href) {
        item.classList.add('active');
      }
    });
  }

  // --------------- INJECT ---------------
  var navPlaceholder = document.getElementById('nav-placeholder');
  if (navPlaceholder) {
    navPlaceholder.outerHTML = navHTML;
    markActiveLink(document.querySelector('.site-nav'));
  }

  var footerPlaceholder = document.getElementById('footer-placeholder');
  if (footerPlaceholder) {
    var variant = footerPlaceholder.getAttribute('data-footer-variant') || 'default';
    footerPlaceholder.outerHTML = buildFooter(variant);
  }

  // Dispatch event so dark-mode.js can find .nav-links
  document.dispatchEvent(new Event('nav-ready'));
})();
