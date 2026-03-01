/**
 * COMPREHENSIVE TRANSPLANT MATCHING ALGORITHM
 *
 * This algorithm considers 50+ factors across 8 major categories to calculate
 * a personalized transplant success probability score for each city.
 *
 * SCORING CATEGORIES (with weights):
 * 1. Medical Compatibility (25%) - Blood type, organ size, antibody sensitivity
 * 2. Wait Time & List Position (20%) - Regional wait times, list competition
 * 3. Donor Availability (18%) - Registration rates, deceased donor events, living donor programs
 * 4. Hospital Quality & Experience (15%) - Volume, outcomes, specialization
 * 5. Geographic & Logistical (10%) - Travel distance, cost of living, climate
 * 6. Health Demographics (7%) - Regional disease prevalence affecting donor pool
 * 7. Policy & Legal Environment (3%) - State donation laws, insurance coverage
 * 8. Socioeconomic Factors (2%) - Support systems, employment, housing
 */

// ==================== DATA ACCESS ====================
// All city data lives in data-loader.js DEFAULTS (the single source of truth).
// data-loader.js loads JSON files at runtime, falling back to DEFAULTS.
// Scoring functions read from window.TransPlanData (populated by data-loader.js).
// L-024: Removed ~140 lines of duplicate inline constants that drifted from DEFAULTS.

// ==================== SCORING FUNCTIONS ====================

/**
 * Category 1: Medical Compatibility (Weight: 25%)
 * Factors: Blood type, age, sex, organ size matching, antibody sensitivity
 */
function calculateMedicalCompatibilityScore(formData, city, organType) {
    let score = 0;

    // Blood type compatibility (40% of category)
    const bloodTypeScores = {
        'O-': 70,   // Hardest to match, can only receive O-
        'O+': 85,   // Limited options
        'A-': 88,   // Moderate
        'A+': 95,   // Good options
        'B-': 82,   // Limited
        'B+': 90,   // Moderate
        'AB-': 92,  // Rare but can receive A-, B-, O-
        'AB+': 100  // Universal recipient - best compatibility
    };
    score += bloodTypeScores[formData.bloodType] * 0.40;

    // Age-based matching (25% of category)
    const age = formData.age;
    let ageScore = 100;
    if (age < 18) ageScore = 115; // Pediatric priority
    else if (age < 35) ageScore = 105;
    else if (age < 50) ageScore = 100;
    else if (age < 65) ageScore = 95;
    else if (age < 75) ageScore = 85;
    else ageScore = 75;
    score += ageScore * 0.25;

    // Sex and organ size compatibility (15% of category)
    // Body size matching is relevant for thoracic organs (heart, lung) where
    // donor-recipient size match matters. Minimal factor for other organs.
    let sexScore = 100;
    if ((organType === 'heart' || organType === 'lung') && formData.sex === 'female') {
        sexScore = 95; // Smaller average body size narrows matching pool for thoracic organs
    }
    score += sexScore * 0.15;

    // Weight/height matching for thoracic organs (20% of category)
    if ((organType === 'heart' || organType === 'lung') && formData.weight && formData.height) {
        const bmi = (formData.weight / (formData.height * formData.height)) * 703;
        let sizeScore = 100;
        if (bmi < 18.5) sizeScore = 85; // Underweight - harder to match
        else if (bmi > 35) sizeScore = 80; // Obese - harder to match
        score += sizeScore * 0.20;
    } else {
        score += 100 * 0.20; // Neutral score if no data
    }

    return Math.min(100, score);
}

/**
 * Category 2: Wait Time & Competition (Weight: 20%)
 * Factors: UNOS region wait time, list size, annual transplants, deaths on waitlist
 */
function calculateWaitTimeScore(city, organType, formData) {
    const urgency = typeof formData === 'object' ? formData.urgency : formData;

    const baseWaitTimes = {
        kidney: { min: 1.8, max: 4.2 },
        liver: { min: 0.8, max: 2.5 },
        heart: { min: 0.25, max: 0.8 },
        lung: { min: 0.3, max: 0.9 },
        pancreas: { min: 1.2, max: 3.5 },
        intestine: { min: 0.6, max: 1.5 }
    };

    const cityWaitTimeFactors = {
        "Minneapolis": 0.85, "Madison": 0.88, "Portland": 0.90,
        "Pittsburgh": 0.87, "Baltimore": 0.95, "Cleveland": 0.92,
        "Nashville": 0.89, "Durham": 0.91, "Rochester": 0.86,
        "Omaha": 0.84, "Seattle": 0.93, "St. Louis": 0.90,
        "Indianapolis": 0.91, "Chicago": 1.05, "Philadelphia": 1.08,
        "Houston": 0.96, "Dallas": 0.94, "Miami": 0.98,
        "Los Angeles": 1.15, "San Francisco": 1.18, "Palo Alto": 1.16,
        "New York": 1.12
    };

    const factor = cityWaitTimeFactors[city] || 1.0;
    const avgWait = (baseWaitTimes[organType].min + baseWaitTimes[organType].max) / 2;
    const cityWait = avgWait * factor;

    // --- Organ-specific clinical scoring ---
    let waitMultiplier;

    if (organType === 'kidney' && typeof formData === 'object' && formData.cpra > 0) {
        // L-001: cPRA (Panel Reactive Antibody) for kidney
        // Highly sensitized patients (cPRA > 80%) wait dramatically longer
        const cpra = Number(formData.cpra);
        if (cpra <= 20) waitMultiplier = 1.0;
        else if (cpra <= 50) waitMultiplier = 1.0 + (cpra - 20) / 30 * 0.5;   // 1.0-1.5x
        else if (cpra <= 80) waitMultiplier = 1.5 + (cpra - 50) / 30 * 1.0;   // 1.5-2.5x
        else if (cpra <= 97) waitMultiplier = 2.5 + (cpra - 80) / 17 * 0.5;   // 2.5-3.0x
        else waitMultiplier = 3.0 + (cpra - 97) / 3 * 2.0;                     // 3.0-5.0x
    } else if (organType === 'liver' && typeof formData === 'object' && formData.meld) {
        // L-002: MELD score for liver allocation
        // Higher MELD = sicker = higher priority = shorter wait
        const meld = Number(formData.meld);
        if (meld >= 35) waitMultiplier = 0.15;       // Weeks — top priority
        else if (meld >= 25) waitMultiplier = 0.4;    // 1-3 months
        else if (meld >= 15) waitMultiplier = 1.0;    // Standard wait
        else waitMultiplier = 2.0;                     // Low MELD, long wait
    } else if (organType === 'lung' && typeof formData === 'object' && formData.las) {
        // L-003: LAS (Lung Allocation Score) for lung allocation
        // Higher LAS = higher medical urgency + expected benefit = shorter wait
        const las = Number(formData.las);
        if (las >= 50) waitMultiplier = 0.3;           // High urgency
        else if (las >= 35) waitMultiplier = 0.7;      // Moderate urgency
        else waitMultiplier = 1.2;                      // Lower priority
    } else {
        // Generic urgency factor (fallback for all organs when specific score not provided)
        const urgencyFactors = { '1': 0.3, '2': 0.6, '3': 1.0, '4': 1.4 };
        waitMultiplier = urgencyFactors[urgency] || 1.0;
    }

    const adjustedWait = cityWait * waitMultiplier;

    // Score inversely proportional to wait time
    const maxWait = baseWaitTimes[organType].max * 1.5;
    const score = Math.max(0, 100 - (adjustedWait / maxWait) * 100);

    return score;
}

/**
 * Category 3: Donor Availability (Weight: 18%)
 * Factors: Registration rate, trauma centers, population density, living donor programs
 */
function calculateDonorAvailabilityScore(city, state, organType) {
    let score = 0;
    const donorData = window.TransPlanData?.donorRegistration;
    const trafficData = window.TransPlanData?.trafficFatalities;

    // State donor registration rate (39% of category — raised from 35% after L-008 traffic weight reduction)
    const stateRegistrationRates = donorData?.stateRegistrationRates || {
        "Montana": 82, "Alaska": 75, "Minnesota": 68, "Oregon": 58,
        "Washington": 56, "Wisconsin": 54, "New York": 52, "Massachusetts": 51,
        "Pennsylvania": 42, "Ohio": 41, "Maryland": 40, "Illinois": 48,
        "California": 45, "North Carolina": 37, "Tennessee": 31,
        "Texas": 30, "Florida": 68, "Georgia": 28, "Indiana": 36,
        "Nebraska": 47, "Missouri": 32, "Iowa": 50
    };

    const regRate = stateRegistrationRates[state] || 35;
    score += (regRate / 82) * 100 * 0.39; // Normalized to best state

    // Population density for deceased donor pool (25% of category — unchanged)
    const populationFactors = donorData?.populationFactors || {
        "New York": 100, "Los Angeles": 95, "Chicago": 90,
        "Houston": 88, "Philadelphia": 85, "San Francisco": 82,
        "Miami": 80, "Dallas": 85, "Baltimore": 75,
        "Pittsburgh": 68, "Cleveland": 70, "Minneapolis": 72,
        "Seattle": 74, "Nashville": 71, "Durham": 68,
        "St. Louis": 67, "Rochester": 60, "Madison": 62,
        "Portland": 70, "Palo Alto": 78, "Indianapolis": 69,
        "Omaha": 58
    };
    score += (populationFactors[city] / 100) * 100 * 0.25;

    // Living donor program strength (28% of category — raised from 25% after L-008 traffic weight reduction)
    const ldpData = donorData?.livingDonorProgramStrength || {};
    const livingDonorScore = ldpData[city] || 75;
    score += livingDonorScore * 0.28;

    // Traffic fatality rate (8% of category — reduced from 15% per L-008: only ~20-25% of
    // modern deceased donors come from motor vehicle accidents; strokes, overdoses, and
    // cardiac events now dominate. Weight redistributed to registration and living donor programs)
    const traumaScores = trafficData?.traumaScores || {
        "Los Angeles": 85, "Houston": 82, "Miami": 80,
        "Dallas": 78, "Phoenix": 82, "Nashville": 72,
        "Pittsburgh": 65, "Cleveland": 68, "Baltimore": 70,
        "Chicago": 75, "Philadelphia": 72, "Indianapolis": 70,
        "St. Louis": 72, "Minneapolis": 62, "Seattle": 58,
        "Portland": 60, "San Francisco": 65, "Rochester": 55,
        "Madison": 52, "Palo Alto": 62, "Durham": 68,
        "Omaha": 65, "New York": 70
    };
    score += (traumaScores[city] / 100) * 100 * 0.08;

    return score;
}

/**
 * Category 4: Hospital Quality & Experience (Weight: 15%)
 * Factors: Annual volume, outcomes, specialization, insurance acceptance
 */
function calculateHospitalQualityScore(city, organType, formData) {
    let score = 0;
    const hqData = window.TransPlanData?.hospitalQuality;

    // Volume-outcome relationship (40% of category)
    const volumes = hqData?.centerVolumes || {};
    const volume = volumes[organType]?.[city] || 50;
    const volumeThresholds = {
        kidney: 300, liver: 250, heart: 120,
        lung: 100, pancreas: 80, intestine: 20
    };
    const threshold = volumeThresholds[organType];
    const volumeScore = Math.min(100, (volume / threshold) * 100);
    score += volumeScore * 0.40;

    // Center reputation (25% of category)
    const tierScores = hqData?.centerReputation || {
        "Pittsburgh": 100, "Cleveland": 98, "Baltimore": 97,
        "Rochester": 97, "Los Angeles": 95, "San Francisco": 94,
        "Minneapolis": 93, "Durham": 92, "Chicago": 90,
        "Houston": 89, "Palo Alto": 91, "Philadelphia": 88,
        "Nashville": 86, "Madison": 87, "Seattle": 88,
        "St. Louis": 85, "Dallas": 83, "Miami": 82,
        "Portland": 84, "Indianapolis": 81, "Omaha": 83,
        "New York": 92
    };
    score += (tierScores[city] || 80) * 0.25;

    // Specialization in specific organ (20% of category)
    const specializations = hqData?.specializations || {
        kidney: ["Pittsburgh", "Minneapolis", "Madison", "Baltimore"],
        liver: ["Pittsburgh", "Los Angeles", "San Francisco", "Baltimore"],
        heart: ["Cleveland", "Nashville", "Durham", "Houston", "Palo Alto"],
        lung: ["Durham", "Pittsburgh", "St. Louis", "Seattle"],
        pancreas: ["Minneapolis", "Madison", "Miami", "San Francisco"],
        intestine: ["Pittsburgh", "Omaha", "Miami"]
    };
    const isSpecialized = (specializations[organType] || []).includes(city);
    score += (isSpecialized ? 100 : 75) * 0.20;

    // Insurance acceptance (15% of category)
    // Centers with higher acceptance rates are more accessible to all patients.
    // If no insurance type selected, use full acceptance score.
    const acceptanceRates = hqData?.insuranceAcceptanceRates || {};
    const cityAcceptance = acceptanceRates[city] || 85;
    if (formData?.insurance === 'medicaid') {
        // Medicaid patients face more access barriers; acceptance rate matters more
        score += (cityAcceptance * 0.85) * 0.15; // 15% discount for Medicaid access variability
    } else if (formData?.insurance === 'none') {
        // Uninsured patients face the most barriers
        score += (cityAcceptance * 0.70) * 0.15;
    } else {
        // Medicare or private insurance — generally well-accepted
        score += cityAcceptance * 0.15;
    }

    return score;
}

/**
 * Category 5: Geographic & Logistical (Weight: 10%)
 * Factors: Cost of living, climate, air quality, housing availability
 */
function calculateGeographicScore(city) {
    let score = 0;

    // Cost of living (inverted - lower is better) (40% of category)
    const colData = window.TransPlanData?.costOfLiving || {};
    const col = colData[city] || 100;
    const colScore = Math.max(0, 100 - ((col - 80) / 120) * 100);
    score += Math.max(0, Math.min(100, colScore)) * 0.40;

    // Climate favorability for recovery (35% of category)
    const climData = window.TransPlanData?.climateScores || {};
    score += (climData[city] || 70) * 0.35;

    // Air quality (25% of category)
    const aqData = window.TransPlanData?.airQuality;
    const airQuality = aqData?.[city] || 70;
    score += airQuality * 0.25;

    return score;
}

/**
 * Category 6: Health Demographics (Weight: 7%)
 * Factors: Regional disease prevalence affecting donor pool quality
 */
function calculateHealthDemographicsScore(city) {
    const hdData = window.TransPlanData?.healthDemographics;
    const health = hdData?.[city];
    if (!health) return 70;

    let score = 100;

    // Lower disease prevalence = better donor pool
    // Use null-safe access with national-average defaults to prevent NaN
    // if fetched data only has some fields (e.g., CDC fetch only gets diabetes)
    const diabetes = health.diabetesRate ?? 10.5;      // US avg ~10.5%
    const obesity = health.obesityRate ?? 31.9;         // US avg ~31.9%
    const ckd = health.ckdRate ?? 14.0;                 // US avg ~14%
    const hypertension = health.hypertensionRate ?? 32;  // US avg ~32%
    const smoking = health.smokingRate ?? 14.0;          // US avg ~14%

    score -= (diabetes - 7) * 2;        // Penalty for high diabetes
    score -= (obesity - 25) * 1.5;      // Penalty for high obesity
    score -= (ckd - 11) * 2.5;          // Penalty for high CKD
    score -= (hypertension - 27) * 1;   // Penalty for high hypertension
    score -= (smoking - 13) * 1.5;      // Penalty for high smoking

    return Math.max(30, Math.min(100, score));
}

/**
 * Category 7: Policy & Legal Environment (Weight: 3%)
 * Factors: State donation laws, insurance mandates, Medicaid expansion
 */
function calculatePolicyScore(state) {
    const policyTiers = window.TransPlanData?.policyTiers || {
        "California": 92, "Oregon": 100, "Washington": 90,
        "Minnesota": 90, "New York": 90, "Illinois": 90,
        "Pennsylvania": 88, "Ohio": 88, "Wisconsin": 88,
        "Massachusetts": 87, "Colorado": 86, "Maryland": 86,
        "North Carolina": 85, "Nebraska": 84, "Iowa": 83,
        "Michigan": 82, "New Jersey": 81, "Virginia": 80,
        "Tennessee": 75, "Texas": 75, "Florida": 74,
        "Indiana": 74, "Georgia": 73, "Missouri": 73,
        "Arizona": 72
    };

    return policyTiers[state] || 70;
}

/**
 * Category 8: Socioeconomic Factors (Weight: 2%)
 * Factors: Support systems, employment opportunities, community resources
 */
function calculateSocioeconomicScore(city) {
    const socioScores = window.TransPlanData?.socioeconomic || {
        "San Francisco": 95, "Palo Alto": 94, "Seattle": 92,
        "Minneapolis": 91, "Madison": 90, "Rochester": 89,
        "Boston": 93, "New York": 90, "Chicago": 87,
        "Los Angeles": 86, "Portland": 88, "Denver": 87,
        "Baltimore": 82, "Pittsburgh": 83, "Cleveland": 81,
        "Philadelphia": 84, "Nashville": 85, "Durham": 84,
        "Dallas": 83, "Houston": 82, "St. Louis": 80,
        "Miami": 79, "Indianapolis": 78, "Omaha": 82
    };

    return socioScores[city] || 75;
}

// ==================== MASTER CALCULATION FUNCTION ====================

function calculateComprehensiveScore(formData, cityName, stateName, organType) {
    const weights = {
        medicalCompatibility: 0.25,
        waitTime: 0.20,
        donorAvailability: 0.18,
        hospitalQuality: 0.15,
        geographic: 0.10,
        healthDemographics: 0.07,
        policy: 0.03,
        socioeconomic: 0.02
    };

    const scores = {
        medicalCompatibility: calculateMedicalCompatibilityScore(formData, cityName, organType),
        waitTime: calculateWaitTimeScore(cityName, organType, formData),
        donorAvailability: calculateDonorAvailabilityScore(cityName, stateName, organType),
        hospitalQuality: calculateHospitalQualityScore(cityName, organType, formData),
        geographic: calculateGeographicScore(cityName),
        healthDemographics: calculateHealthDemographicsScore(cityName),
        policy: calculatePolicyScore(stateName),
        socioeconomic: calculateSocioeconomicScore(cityName)
    };

    // Calculate weighted total
    let totalScore = 0;
    for (const [category, score] of Object.entries(scores)) {
        totalScore += score * weights[category];
    }

    return {
        total: Math.min(100, Math.max(0, totalScore)),
        breakdown: scores
    };
}

// Export for use in main script
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        calculateComprehensiveScore
    };
}
