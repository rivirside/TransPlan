// Disclaimer modal on first visit
(function () {
  const STORAGE_KEY = 'transplan-disclaimer-seen';

  function initDisclaimerModal() {
    const hasSeenDisclaimer = localStorage.getItem(STORAGE_KEY);

    if (hasSeenDisclaimer) {
      return; // User has already seen it
    }

    // Create modal HTML
    const modalHTML = `
      <div id="disclaimer-modal" class="disclaimer-modal-overlay">
        <div class="disclaimer-modal">
          <div class="disclaimer-header">
            <h2>Important Disclaimer</h2>
            <button class="disclaimer-close" aria-label="Close disclaimer">&times;</button>
          </div>
          <div class="disclaimer-content">
            <p><strong>This tool is designed for research purposes</strong> to help inform policy decision-making in transplantation.</p>
            <p>While validation for clinical use is planned, <strong>this tool is not currently intended to inform medical or financial decisions.</strong></p>
            <p><strong>Nothing on this site should be construed as medical or financial advice.</strong></p>
            <p>This is an independent, open-source research project built on publicly available data. Use it to explore trends and inform discussion—not to replace conversations with your transplant team or financial advisors.</p>
          </div>
          <button class="disclaimer-confirm">I Understand</button>
        </div>
      </div>
    `;

    // Insert modal into DOM
    document.body.insertAdjacentHTML('afterbegin', modalHTML);

    // Get modal elements
    const overlay = document.getElementById('disclaimer-modal');
    const closeBtn = overlay.querySelector('.disclaimer-close');
    const confirmBtn = overlay.querySelector('.disclaimer-confirm');

    // Close handler
    function closeModal() {
      overlay.classList.add('dismiss');
      setTimeout(() => overlay.remove(), 300);
      localStorage.setItem(STORAGE_KEY, 'true');
    }

    closeBtn.addEventListener('click', closeModal);
    confirmBtn.addEventListener('click', closeModal);

    // Close on backdrop click (but not on modal itself)
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeModal();
      }
    });
  }

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDisclaimerModal);
  } else {
    initDisclaimerModal();
  }
})();
