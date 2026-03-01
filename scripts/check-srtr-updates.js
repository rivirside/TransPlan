#!/usr/bin/env node
/**
 * Check SRTR website for new biannual reports.
 * Creates a GitHub Issue if new reports are detected.
 * Source: srtr.org
 * Auth: None (GITHUB_TOKEN for issue creation)
 */

const { fetchWithRetry, updateMetadata, reportError } = require('./utils');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SRTR_URL = 'https://www.srtr.org/reports/program-specific-reports/';
const META_PATH = path.join(__dirname, '..', 'data', 'metadata.json');

async function checkSRTR() {
    console.log('Checking SRTR for new reports...');

    try {
        const response = await fetchWithRetry(SRTR_URL);
        const html = await response.text();

        // Hash the page content to detect changes
        const currentHash = crypto.createHash('sha256').update(html).digest('hex');

        // Read stored hash
        let metadata = {};
        try {
            metadata = JSON.parse(fs.readFileSync(META_PATH, 'utf-8'));
        } catch {
            metadata = { srtrReportHash: null };
        }

        const previousHash = metadata.srtrReportHash;

        if (previousHash && previousHash !== currentHash) {
            console.log('SRTR reports page has changed! New reports may be available.');

            // Create GitHub Issue if running in Actions
            if (process.env.GITHUB_TOKEN && process.env.GITHUB_REPOSITORY) {
                await createGitHubIssue();
            } else {
                console.log('Not running in GitHub Actions. Skipping issue creation.');
            }
        } else if (!previousHash) {
            console.log('First run - storing baseline hash.');
        } else {
            console.log('No changes detected on SRTR reports page.');
        }

        // Update stored hash
        metadata.srtrReportHash = currentHash;
        fs.writeFileSync(META_PATH, JSON.stringify(metadata, null, 2) + '\n');
        updateMetadata('srtr-reports', 'SRTR Website Check');

    } catch (err) {
        reportError('SRTR Check', err);
    }
}

async function createGitHubIssue() {
    const token = process.env.GITHUB_TOKEN;
    const repo = process.env.GITHUB_REPOSITORY;

    if (!token || !repo) return;

    const title = '[Manual Update] New SRTR reports available';

    // Check for existing open issue with same title
    try {
        const searchUrl = `https://api.github.com/repos/${repo}/issues?state=open&labels=data-pipeline`;
        const searchResponse = await fetchWithRetry(searchUrl, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });
        const existingIssues = await searchResponse.json();
        const duplicate = existingIssues.find(i => i.title === title);
        if (duplicate) {
            console.log(`Issue already exists: #${duplicate.number}. Skipping.`);
            return;
        }
    } catch {
        // Continue with creation if search fails
    }

    const body = `## New SRTR Reports Detected

The SRTR program-specific reports page has been updated. New biannual data may be available.

### Action Items
- [ ] Visit [SRTR Reports](https://www.srtr.org/reports/program-specific-reports/)
- [ ] Download updated center volume and outcome data
- [ ] Update \`data/manual/srtr-reports.json\` with new volumes
- [ ] Update \`data/hospital-quality.json\` centerReputation scores if needed
- [ ] Update specializations list if centers have changed focus areas
- [ ] Verify all 22 cities have current data
- [ ] Commit and push updates

*This issue was automatically created by the SRTR check workflow.*`;

    try {
        const createUrl = `https://api.github.com/repos/${repo}/issues`;
        await fetchWithRetry(createUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                body,
                labels: ['data-pipeline', 'manual-update']
            })
        });
        console.log('GitHub Issue created successfully.');
    } catch (err) {
        console.error(`Failed to create GitHub Issue: ${err.message}`);
    }
}

checkSRTR().catch(err => {
    reportError('SRTR Check', err);
    process.exit(1);
});
