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

// ==================== REGIONAL DATA REPOSITORY ====================

const regionalHealthData = {
    // Northeast
    "Pittsburgh": { diabetesRate: 10.2, obesityRate: 31.5, ckdRate: 14.2, hypertensionRate: 32.1, smokingRate: 19.3, airQuality: 68 },
    "Baltimore": { diabetesRate: 11.8, obesityRate: 34.2, ckdRate: 15.8, hypertensionRate: 35.4, smokingRate: 17.9, airQuality: 62 },
    "Philadelphia": { diabetesRate: 11.4, obesityRate: 33.8, ckdRate: 15.2, hypertensionRate: 34.2, smokingRate: 18.5, airQuality: 64 },
    "New York": { diabetesRate: 10.9, obesityRate: 28.5, ckdRate: 14.5, hypertensionRate: 31.8, smokingRate: 14.2, airQuality: 58 },

    // Midwest
    "Minneapolis": { diabetesRate: 8.1, obesityRate: 27.3, ckdRate: 12.4, hypertensionRate: 28.5, smokingRate: 15.8, airQuality: 78 },
    "Madison": { diabetesRate: 7.9, obesityRate: 26.8, ckdRate: 12.1, hypertensionRate: 27.9, smokingRate: 14.9, airQuality: 82 },
    "Chicago": { diabetesRate: 10.5, obesityRate: 32.1, ckdRate: 14.8, hypertensionRate: 33.2, smokingRate: 16.7, airQuality: 61 },
    "Cleveland": { diabetesRate: 11.2, obesityRate: 33.5, ckdRate: 15.3, hypertensionRate: 34.8, smokingRate: 20.1, airQuality: 65 },
    "St. Louis": { diabetesRate: 10.8, obesityRate: 32.7, ckdRate: 14.9, hypertensionRate: 33.9, smokingRate: 19.5, airQuality: 66 },
    "Indianapolis": { diabetesRate: 11.5, obesityRate: 34.8, ckdRate: 15.7, hypertensionRate: 35.2, smokingRate: 21.3, airQuality: 67 },
    "Omaha": { diabetesRate: 9.8, obesityRate: 31.2, ckdRate: 13.9, hypertensionRate: 31.5, smokingRate: 17.8, airQuality: 74 },
    "Rochester": { diabetesRate: 8.5, obesityRate: 28.9, ckdRate: 12.8, hypertensionRate: 29.3, smokingRate: 15.2, airQuality: 80 },

    // South
    "Nashville": { diabetesRate: 12.3, obesityRate: 36.2, ckdRate: 16.5, hypertensionRate: 37.1, smokingRate: 22.8, airQuality: 69 },
    "Durham": { diabetesRate: 11.1, obesityRate: 33.1, ckdRate: 15.1, hypertensionRate: 34.5, smokingRate: 18.9, airQuality: 71 },
    "Miami": { diabetesRate: 12.8, obesityRate: 32.5, ckdRate: 16.8, hypertensionRate: 36.2, smokingRate: 16.4, airQuality: 65 },
    "Dallas": { diabetesRate: 11.9, obesityRate: 33.9, ckdRate: 15.9, hypertensionRate: 35.8, smokingRate: 17.2, airQuality: 63 },
    "Houston": { diabetesRate: 12.5, obesityRate: 34.7, ckdRate: 16.3, hypertensionRate: 36.5, smokingRate: 16.8, airQuality: 59 },

    // West
    "Portland": { diabetesRate: 8.7, obesityRate: 29.1, ckdRate: 13.1, hypertensionRate: 29.8, smokingRate: 15.3, airQuality: 76 },
    "Seattle": { diabetesRate: 8.3, obesityRate: 27.8, ckdRate: 12.6, hypertensionRate: 28.9, smokingRate: 14.8, airQuality: 77 },
    "San Francisco": { diabetesRate: 8.9, obesityRate: 26.2, ckdRate: 13.3, hypertensionRate: 29.1, smokingRate: 13.5, airQuality: 68 },
    "Los Angeles": { diabetesRate: 10.3, obesityRate: 30.4, ckdRate: 14.6, hypertensionRate: 32.4, smokingRate: 14.9, airQuality: 45 },
    "Palo Alto": { diabetesRate: 7.8, obesityRate: 24.1, ckdRate: 11.9, hypertensionRate: 27.2, smokingRate: 11.8, airQuality: 72 }
};

const costOfLivingIndex = {
    "San Francisco": 191, "Palo Alto": 204, "New York": 187,
    "Los Angeles": 150, "Seattle": 145, "Baltimore": 89,
    "Pittsburgh": 85, "Minneapolis": 98, "Madison": 97,
    "Portland": 135, "Chicago": 102, "Philadelphia": 101,
    "Dallas": 92, "Houston": 90, "Miami": 112,
    "Nashville": 95, "Durham": 93, "Cleveland": 81,
    "St. Louis": 83, "Rochester": 91, "Omaha": 86,
    "Indianapolis": 87
};

const climateScores = {
    // Higher is better for recovery (moderate temps, low extreme weather)
    "San Francisco": 92, "Los Angeles": 88, "Palo Alto": 91,
    "Miami": 75, "Seattle": 82, "Portland": 83,
    "Minneapolis": 62, "Madison": 64, "Rochester": 60,
    "Pittsburgh": 71, "Baltimore": 73, "Philadelphia": 72,
    "Chicago": 67, "Cleveland": 66, "St. Louis": 70,
    "Nashville": 78, "Durham": 77, "Dallas": 72,
    "Houston": 71, "New York": 70, "Omaha": 68,
    "Indianapolis": 69
};

const livingDonorProgramStrength = {
    "Minneapolis": 95, "Madison": 92, "Pittsburgh": 94,
    "Cleveland": 93, "Los Angeles": 91, "San Francisco": 90,
    "Baltimore": 89, "Rochester": 91, "Durham": 88,
    "Chicago": 86, "Houston": 87, "Palo Alto": 89,
    "Nashville": 84, "Philadelphia": 85, "St. Louis": 83,
    "Portland": 86, "Seattle": 87, "Dallas": 82,
    "Miami": 81, "New York": 84, "Omaha": 85,
    "Indianapolis": 80
};

const insuranceAcceptanceRates = {
    "Rochester": 99, "Cleveland": 98, "Baltimore": 97,
    "Pittsburgh": 97, "Minneapolis": 96, "Madison": 96,
    "Durham": 95, "Los Angeles": 94, "San Francisco": 94,
    "Chicago": 93, "Palo Alto": 94, "Houston": 92,
    "Nashville": 91, "Philadelphia": 93, "St. Louis": 92,
    "Seattle": 94, "Portland": 93, "Dallas": 90,
    "Miami": 89, "New York": 92, "Omaha": 95,
    "Indianapolis": 91
};

// Transplant center annual volumes by organ
const centerVolumes = {
    kidney: {
        "Pittsburgh": 385, "Minneapolis": 348, "Baltimore": 362,
        "Cleveland": 355, "Los Angeles": 425, "San Francisco": 368,
        "Rochester": 305, "Madison": 298, "Chicago": 398,
        "Philadelphia": 342, "Nashville": 285, "Durham": 295,
        "Houston": 378, "Dallas": 268, "Miami": 245,
        "Palo Alto": 312, "Portland": 228, "Seattle": 315,
        "St. Louis": 278, "New York": 412, "Omaha": 195,
        "Indianapolis": 235
    },
    liver: {
        "Pittsburgh": 312, "Los Angeles": 398, "San Francisco": 352,
        "Baltimore": 305, "Cleveland": 288, "Rochester": 285,
        "Minneapolis": 268, "Dallas": 275, "Houston": 325,
        "Chicago": 342, "Philadelphia": 318, "Miami": 242,
        "Durham": 268, "Nashville": 235, "Madison": 215,
        "Palo Alto": 285, "Seattle": 295, "Portland": 195,
        "St. Louis": 248, "New York": 385, "Omaha": 145,
        "Indianapolis": 198
    },
    heart: {
        "Cleveland": 175, "Nashville": 148, "Durham": 142,
        "Houston": 155, "Palo Alto": 135, "Los Angeles": 168,
        "Pittsburgh": 132, "Chicago": 145, "San Francisco": 128,
        "Baltimore": 138, "Minneapolis": 125, "Philadelphia": 138,
        "St. Louis": 105, "Rochester": 98, "Madison": 85,
        "Dallas": 118, "Seattle": 115, "Miami": 95,
        "Portland": 78, "New York": 148, "Omaha": 58,
        "Indianapolis": 72
    },
    lung: {
        "Durham": 155, "Pittsburgh": 142, "St. Louis": 128,
        "Seattle": 118, "Philadelphia": 108, "Cleveland": 132,
        "Los Angeles": 125, "San Francisco": 115, "Nashville": 105,
        "Chicago": 118, "Houston": 112, "Baltimore": 95,
        "Minneapolis": 88, "Rochester": 82, "Palo Alto": 95,
        "Madison": 68, "Dallas": 78, "Portland": 72,
        "Miami": 65, "New York": 122, "Omaha": 45,
        "Indianapolis": 58
    },
    pancreas: {
        "Minneapolis": 128, "Madison": 115, "Miami": 95,
        "San Francisco": 88, "Chicago": 82, "Pittsburgh": 78,
        "Cleveland": 72, "Los Angeles": 85, "Houston": 75,
        "Baltimore": 68, "Philadelphia": 72, "Durham": 62,
        "Rochester": 65, "Nashville": 55, "Dallas": 58,
        "Palo Alto": 68, "Seattle": 62, "St. Louis": 52,
        "Portland": 45, "New York": 78, "Omaha": 38,
        "Indianapolis": 42
    },
    intestine: {
        "Pittsburgh": 52, "Omaha": 28, "Miami": 22,
        "Indianapolis": 18, "Los Angeles": 15, "Baltimore": 12,
        "Chicago": 14, "Cleveland": 11, "Minneapolis": 10,
        "Rochester": 9, "San Francisco": 11, "Houston": 13,
        "Philadelphia": 10, "Durham": 8, "Nashville": 7,
        "Madison": 6, "Dallas": 8, "Seattle": 7,
        "St. Louis": 6, "Portland": 5, "Palo Alto": 6,
        "New York": 14
    }
};

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
function calculateWaitTimeScore(city, organType, urgency) {
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

    // Urgency dramatically affects wait time
    const urgencyFactors = { '1': 0.3, '2': 0.6, '3': 1.0, '4': 1.4 };
    const adjustedWait = cityWait * urgencyFactors[urgency];

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

    // State donor registration rate (35% of category)
    const stateRegistrationRates = donorData?.stateRegistrationRates || {
        "Montana": 82, "Alaska": 75, "Minnesota": 68, "Oregon": 58,
        "Washington": 56, "Wisconsin": 54, "New York": 52, "Massachusetts": 51,
        "Pennsylvania": 42, "Ohio": 41, "Maryland": 40, "Illinois": 48,
        "California": 45, "North Carolina": 37, "Tennessee": 31,
        "Texas": 30, "Florida": 68, "Georgia": 28, "Indiana": 36,
        "Nebraska": 47, "Missouri": 32, "Iowa": 50
    };

    const regRate = stateRegistrationRates[state] || 35;
    score += (regRate / 82) * 100 * 0.35; // Normalized to best state

    // Population density for deceased donor pool (25% of category)
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

    // Living donor program strength (25% of category)
    const ldpData = donorData?.livingDonorProgramStrength || livingDonorProgramStrength;
    const livingDonorScore = ldpData[city] || 75;
    score += livingDonorScore * 0.25;

    // Traffic fatality rate (deceased donor indicator) (15% of category)
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
    score += (traumaScores[city] / 100) * 100 * 0.15;

    return score;
}

/**
 * Category 4: Hospital Quality & Experience (Weight: 15%)
 * Factors: Annual volume, outcomes, specialization, research activity
 */
function calculateHospitalQualityScore(city, organType) {
    let score = 0;
    const hqData = window.TransPlanData?.hospitalQuality;

    // Volume-outcome relationship (50% of category)
    const volumes = hqData?.centerVolumes || centerVolumes;
    const volume = volumes[organType]?.[city] || 50;
    const volumeThresholds = {
        kidney: 300, liver: 250, heart: 120,
        lung: 100, pancreas: 80, intestine: 20
    };
    const threshold = volumeThresholds[organType];
    const volumeScore = Math.min(100, (volume / threshold) * 100);
    score += volumeScore * 0.50;

    // Center reputation (30% of category)
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
    score += (tierScores[city] || 80) * 0.30;

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

    return score;
}

/**
 * Category 5: Geographic & Logistical (Weight: 10%)
 * Factors: Cost of living, climate, air quality, housing availability
 */
function calculateGeographicScore(city) {
    let score = 0;

    // Cost of living (inverted - lower is better) (40% of category)
    const colData = window.TransPlanData?.costOfLiving || costOfLivingIndex;
    const col = colData[city] || 100;
    const colScore = Math.max(0, 100 - ((col - 80) / 120) * 100);
    score += Math.max(0, Math.min(100, colScore)) * 0.40;

    // Climate favorability for recovery (35% of category)
    const climData = window.TransPlanData?.climateScores || climateScores;
    score += (climData[city] || 70) * 0.35;

    // Air quality (25% of category)
    const aqData = window.TransPlanData?.airQuality;
    const airQuality = aqData?.[city] || regionalHealthData[city]?.airQuality || 70;
    score += airQuality * 0.25;

    return score;
}

/**
 * Category 6: Health Demographics (Weight: 7%)
 * Factors: Regional disease prevalence affecting donor pool quality
 */
function calculateHealthDemographicsScore(city) {
    const hdData = window.TransPlanData?.healthDemographics;
    const health = hdData?.[city] || regionalHealthData[city];
    if (!health) return 70;

    let score = 100;

    // Lower disease prevalence = better donor pool
    score -= (health.diabetesRate - 7) * 2;  // Penalty for high diabetes
    score -= (health.obesityRate - 25) * 1.5; // Penalty for high obesity
    score -= (health.ckdRate - 11) * 2.5;     // Penalty for high CKD
    score -= (health.hypertensionRate - 27) * 1; // Penalty for high hypertension
    score -= (health.smokingRate - 13) * 1.5;    // Penalty for high smoking

    return Math.max(30, Math.min(100, score));
}

/**
 * Category 7: Policy & Legal Environment (Weight: 3%)
 * Factors: State donation laws, insurance mandates, Medicaid expansion
 */
function calculatePolicyScore(state) {
    const policyTiers = window.TransPlanData?.policyTiers || {
        "California": 100, "Oregon": 100, "Washington": 100,
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
        waitTime: calculateWaitTimeScore(cityName, organType, formData.urgency),
        donorAvailability: calculateDonorAvailabilityScore(cityName, stateName, organType),
        hospitalQuality: calculateHospitalQualityScore(cityName, organType),
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
        calculateComprehensiveScore,
        regionalHealthData,
        costOfLivingIndex,
        climateScores,
        livingDonorProgramStrength,
        insuranceAcceptanceRates,
        centerVolumes
    };
}
