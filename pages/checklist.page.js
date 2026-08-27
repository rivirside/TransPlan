/**
 * Extracted from checklist.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function() {
        'use strict';
        var STORAGE_KEY = 'transplan-checklist';

        var phases = [
            {
                title: 'Pre-Evaluation',
                items: [
                    'Get referral from your doctor to a transplant center',
                    'Research transplant centers using transplant.today',
                    'Schedule evaluation appointment(s)',
                    'Gather medical records (labs, imaging, surgical history)',
                    'Review insurance coverage and financial assistance options',
                    'Arrange transportation and lodging if center is out of town',
                ]
            },
            {
                title: 'Evaluation & Listing',
                items: [
                    'Complete transplant center evaluation (blood work, imaging, consultations)',
                    'Meet with transplant surgeon, nephrologist/hepatologist, and coordinator',
                    'Complete psychosocial evaluation',
                    'Discuss organ-specific scoring (cPRA, MELD, LAS) with your team',
                    'Understand the waitlist process and expected timeline',
                    'Get officially listed on the UNOS waitlist',
                    'Consider multiple listing at a second center',
                ]
            },
            {
                title: 'Waiting Period',
                items: [
                    'Keep all follow-up appointments with your transplant team',
                    'Stay reachable 24/7 (keep phone charged, inform center of travel)',
                    'Maintain your health (diet, exercise, medications)',
                    'Complete required periodic testing (blood work, updates)',
                    'Notify center of any health changes immediately',
                    'Keep a packed hospital bag ready',
                    'Arrange caregiver and support system for post-transplant',
                    'Explore peer support groups and counseling resources',
                ]
            },
            {
                title: 'Transplant Surgery',
                items: [
                    'Respond immediately when called for an organ offer',
                    'Follow pre-surgery fasting and medication instructions',
                    'Bring ID, insurance cards, and medication list to the hospital',
                    'Designate a healthcare proxy / power of attorney',
                    'Notify your caregiver and support network',
                ]
            },
            {
                title: 'Recovery & Long-Term',
                items: [
                    'Follow post-transplant medication schedule exactly (immunosuppressants)',
                    'Attend all post-transplant clinic visits',
                    'Learn signs of rejection and when to seek emergency care',
                    'Follow dietary restrictions recommended by your team',
                    'Gradually resume physical activity as approved by your doctor',
                    'Schedule regular lab work and biopsies as directed',
                    'Maintain sun protection (increased skin cancer risk with immunosuppression)',
                    'Connect with post-transplant peer support community',
                ]
            }
        ];

        var savedState = {};
        try { savedState = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch (e) {}

        var content = document.getElementById('checklist-content');
        var progressFill = document.getElementById('progress-fill');
        var progressLabel = document.getElementById('progress-label');
        var totalItems = 0;
        var allCheckboxes = [];

        phases.forEach(function(phase, pi) {
            var section = document.createElement('div');
            section.className = 'phase';

            var header = document.createElement('div');
            header.className = 'phase-header';
            var num = document.createElement('span');
            num.className = 'phase-number';
            num.textContent = String(pi + 1);
            header.appendChild(num);
            var title = document.createElement('span');
            title.className = 'phase-title';
            title.textContent = phase.title;
            header.appendChild(title);
            section.appendChild(header);

            var items = document.createElement('div');
            items.className = 'checklist-items';

            phase.items.forEach(function(text, ii) {
                var key = 'p' + pi + '_i' + ii;
                totalItems++;
                var row = document.createElement('div');
                row.className = 'checklist-item';
                if (savedState[key]) row.classList.add('checked');

                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.id = key;
                cb.checked = !!savedState[key];
                allCheckboxes.push(cb);

                var lbl = document.createElement('label');
                lbl.setAttribute('for', key);
                lbl.textContent = text;

                cb.addEventListener('change', function() {
                    savedState[key] = cb.checked;
                    row.classList.toggle('checked', cb.checked);
                    save();
                    updateProgress();
                });

                row.appendChild(cb);
                row.appendChild(lbl);
                items.appendChild(row);
            });

            section.appendChild(items);
            content.appendChild(section);
        });

        function save() {
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(savedState)); } catch (e) {}
        }

        function updateProgress() {
            var checked = allCheckboxes.filter(function(cb) { return cb.checked; }).length;
            var pct = totalItems > 0 ? Math.round((checked / totalItems) * 100) : 0;
            progressFill.style.width = pct + '%';
            progressLabel.textContent = checked + ' of ' + totalItems + ' completed (' + pct + '%)';
        }

        updateProgress();

        document.getElementById('print-btn').addEventListener('click', function() { window.print(); });
        document.getElementById('reset-btn').addEventListener('click', function() {
            if (!confirm('Reset all checklist progress? This cannot be undone.')) return;
            savedState = {};
            save();
            allCheckboxes.forEach(function(cb) {
                cb.checked = false;
                cb.closest('.checklist-item').classList.remove('checked');
            });
            updateProgress();
        });
    })();
