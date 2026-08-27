/**
 * Extracted from index.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
// Methods accordion — auto-close on open
    (function() {
      document.querySelectorAll('.acc-trigger').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var item = btn.closest('.acc-item');
          var body = item.querySelector('.acc-body');
          var isOpen = btn.getAttribute('aria-expanded') === 'true';
          document.querySelectorAll('.acc-item').forEach(function(i) {
            i.querySelector('.acc-trigger').setAttribute('aria-expanded', 'false');
            i.querySelector('.acc-body').hidden = true;
          });
          if (!isOpen) {
            btn.setAttribute('aria-expanded', 'true');
            body.hidden = false;
          }
        });
      });
    })();
