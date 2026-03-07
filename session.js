/**
 * Session management for local TransPlan instance.
 * Only activates on localhost. Uses same-origin /health check
 * to detect if backend is running. Shows "End Session" bar.
 */
(function () {
  'use strict';

  var isLocal = window.location.hostname === 'localhost' ||
                window.location.hostname === '127.0.0.1';
  if (!isLocal) return;

  // Check if backend is reachable (same-origin)
  fetch('/health')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data || data.status !== 'ok') return;
      createSessionUI();
    })
    .catch(function () { /* no backend — static-only server */ });

  function createSessionUI() {
    var bar = document.createElement('div');
    bar.className = 'transplan-session-bar';

    var status = document.createElement('span');
    status.className = 'session-status';
    status.textContent = 'Local session active';

    var btn = document.createElement('button');
    btn.className = 'session-end-btn';
    btn.textContent = 'End Session';
    btn.onclick = endSession;

    bar.appendChild(status);
    bar.appendChild(btn);
    document.body.appendChild(bar);
  }

  function endSession() {
    if (!confirm('End the TransPlan session? This will stop the local server.')) {
      return;
    }

    var btn = document.querySelector('.session-end-btn');
    if (btn) {
      btn.textContent = 'Stopping...';
      btn.disabled = true;
    }

    fetch('/shutdown', { method: 'POST' })
      .then(function () {
        updateStatus('Session ended', 'Stopped');
      })
      .catch(function () {
        updateStatus('Session ended', 'Stopped');
      });
  }

  function updateStatus(statusText, btnText) {
    var statusEl = document.querySelector('.session-status');
    var btnEl = document.querySelector('.session-end-btn');
    if (statusEl) statusEl.textContent = statusText;
    if (btnEl) btnEl.textContent = btnText;
  }
})();
