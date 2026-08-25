/**
 * scoring-constants.js — canonical scoring category constants (frontend copy).
 *
 * The authoritative scoring engine is backend/services/scoring.py; the
 * no-build-step architecture needs these three constants client-side for the
 * weight-slider UI (weight-config.js). Parity with scoring.py is enforced by
 * backend/tests/test_constants_parity.py.
 *
 * History: extracted from algorithm.js when the legacy client-side scorer was
 * retired (#293) — scoring runs exclusively through POST /score since the
 * Phase 2 rebuild.
 */

const DEFAULT_WEIGHTS = {
    medicalCompatibility: 0.25,
    waitTime: 0.20,
    donorAvailability: 0.18,
    hospitalQuality: 0.15,
    geographic: 0.10,
    healthDemographics: 0.07,
    policy: 0.03,
    socioeconomic: 0.02
};

// Category display labels (used by the weight UI)
const CATEGORY_LABELS = {
    medicalCompatibility: 'Medical Compatibility',
    waitTime: 'Wait Time',
    donorAvailability: 'Donor Availability',
    hospitalQuality: 'Hospital Quality',
    geographic: 'Geographic',
    healthDemographics: 'Health Demographics',
    policy: 'Policy',
    socioeconomic: 'Socioeconomic'
};

// Ordered list of category keys (canonical order for serialization)
const CATEGORY_KEYS = Object.keys(DEFAULT_WEIGHTS);

// Export for unit tests
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DEFAULT_WEIGHTS, CATEGORY_LABELS, CATEGORY_KEYS };
}
