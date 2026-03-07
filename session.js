/**
 * Session management for local TransPlan instance.
 * Only activates when running on localhost via start.command.
 * Reads .transplan-session.json for backend port, shows "End Session" button.
 */
(function () {
  'use strict';

  var isLocal = window.location.hostname === 'localhost' ||
                window.location.hostname === '127.0.0.1';
  if (!isLocal) return;

  var session = null;

  // Fetch session config written by start.command
  fetch('/.transplan-session.json')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data || !data.backendPort) return;
      session = data;
      // Expose backend URL globally (used by M6 API client later)
      window.TransPlanBackend = 'http://localhost:' + data.backendPort;
      createSessionUI();
    })
    .catch(function () { /* no session file — not launched via start.command */ });

  function createSessionUI() {
    var bar = document.createElement('div');
    bar.className = 'transplan-session-bar';

    var status = document.createElement('span');
    status.className = 'session-status';
    status.textContent = 'Local session active';
    status.title = 'Backend :' + session.backendPort +
                   ' | Frontend :' + session.frontendPort;

    var btn = document.createElement('button');
    btn.className = 'session-end-btn';
    btn.textContent = 'End Session';
    btn.onclick = endSession;

    bar.appendChild(status);
    bar.appendChild(btn);
    document.body.appendChild(bar);
  }

  function endSession() {
    if (!confirm('End the TransPlan session? This will stop the local servers.')) {
      return;
    }

    var btn = document.querySelector('.session-end-btn');
    if (btn) {
      btn.textContent = 'Stopping...';
      btn.disabled = true;
    }

    fetch(window.TransPlanBackend + '/shutdown', { method: 'POST' })
      .then(function () {
        var bar = document.querySelector('.transplan-session-bar');
        if (bar) {
          bar.querySelector('.session-status').textContent = 'Session ended';
          bar.querySelector('.session-end-btn').textContent = 'Stopped';
        }
      })
      .catch(function () {
        // Backend may already be gone — that's fine
        var bar = document.querySelector('.transplan-session-bar');
        if (bar) {
          bar.querySelector('.session-status').textContent = 'Session ended';
          bar.querySelector('.session-end-btn').textContent = 'Stopped';
        }
      });
  }
})();
