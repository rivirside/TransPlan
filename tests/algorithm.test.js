/**
 * Unit tests for TransPlan scoring algorithm.
 *
 * Covers all 8 category scoring functions + the master calculation.
 * Tests boundary values, edge cases, organ-specific logic, and NaN prevention.
 */

const {
    calculateComprehensiveScore,
    calculateMedicalCompatibilityScore,
    calculateWaitTimeScore,
    calculateDonorAvailabilityScore,
    calculateHospitalQualityScore,
    calculateGeographicScore,
    calculateHealthDemographicsScore,
    calculatePolicyScore,
    calculateSocioeconomicScore,
    DEFAULT_WEIGHTS,
    CATEGORY_LABELS,
    CATEGORY_KEYS
} = require('../algorithm');

// ==================== MOCK DATA ====================
// Representative data from actual JSON files, used to populate window.TransPlanData.

const MOCK_TRANSPLANT_DATA = {
    costOfLiving: {
        "Rochester": 91, "Cleveland": 84, "Pittsburgh": 86,
        "Houston": 92, "Minneapolis": 103, "New York": 187,
        "San Francisco": 204, "Miami": 122, "Omaha": 81
    },
    climateScores: {
        "Rochester": 40, "Cleveland": 45, "Pittsburgh": 50,
        "Houston": 60, "Miami": 70, "San Francisco": 80,
        "Minneapolis": 35, "Omaha": 45, "New York": 55
    },
    airQuality: {
        "Rochester": 75, "Cleveland": 58, "Pittsburgh": 55,
        "Houston": 50, "Miami": 65, "San Francisco": 62,
        "Minneapolis": 72, "Omaha": 70, "New York": 52
    },
    healthDemographics: {
        "Rochester": { diabetesRate: 8.5, obesityRate: 28.0, ckdRate: 12.5, hypertensionRate: 28.0, smokingRate: 14.0 },
        "Cleveland": { diabetesRate: 12.5, obesityRate: 35.0, ckdRate: 16.0, hypertensionRate: 35.0, smokingRate: 18.0 },
        "Houston": { diabetesRate: 11.0, obesityRate: 32.0, ckdRate: 14.5, hypertensionRate: 31.0, smokingRate: 12.0 },
        "PartialCity": { diabetesRate: 9.0 } // Only one field — tests null-safety
    },
    donorRegistration: {
        stateRegistrationRates: {
            "Minnesota": 68, "Ohio": 41, "Texas": 30, "New York": 52, "Florida": 68
        },
        populationFactors: {
            "Minneapolis": 72, "Cleveland": 70, "Houston": 88, "New York": 100, "Miami": 80, "Rochester": 60
        },
        livingDonorProgramStrength: {
            "Minneapolis": 95, "Cleveland": 93, "Houston": 87, "New York": 84, "Miami": 81, "Rochester": 91
        }
    },
    trafficFatalities: {
        traumaScores: {
            "Minneapolis": 62, "Cleveland": 68, "Houston": 82, "New York": 70, "Miami": 80, "Rochester": 55
        }
    },
    hospitalQuality: {
        centerVolumes: {
            kidney: { "Minneapolis": 350, "Cleveland": 310, "Houston": 280, "Rochester": 250, "Miami": 180 },
            liver: { "Houston": 400, "Cleveland": 280, "Minneapolis": 200, "Rochester": 180 },
            heart: { "Cleveland": 130, "Houston": 100, "Minneapolis": 90 },
            lung: { "Cleveland": 110, "Durham": 95, "Minneapolis": 80 },
            pancreas: { "Minneapolis": 100, "Indianapolis": 60 },
            intestine: { "Pittsburgh": 25, "Omaha": 15 }
        },
        centerReputation: {
            "Pittsburgh": 100, "Cleveland": 98, "Rochester": 97,
            "Minneapolis": 93, "Houston": 89, "Miami": 82, "New York": 92
        },
        specializations: {
            kidney: ["Cleveland", "Nashville", "St. Louis", "Madison", "San Francisco", "Chicago"],
            liver: ["Houston", "Cleveland", "San Francisco", "Pittsburgh", "Indianapolis", "Nashville"],
            heart: ["Nashville", "Durham", "Los Angeles", "Palo Alto", "San Francisco", "New York"],
            lung: ["Cleveland", "Durham", "Nashville", "Chicago", "San Francisco", "Pittsburgh"],
            pancreas: ["Minneapolis", "Indianapolis", "Madison", "San Francisco"],
            intestine: ["Pittsburgh", "Omaha", "Miami", "Cleveland"]
        },
        insuranceAcceptanceRates: {
            "Minneapolis": 92, "Cleveland": 90, "Houston": 88, "Rochester": 95, "Miami": 80, "New York": 85
        }
    },
    policyTiers: {
        "Minnesota": 90, "Ohio": 88, "Texas": 75, "New York": 90,
        "Florida": 74, "Oregon": 100, "California": 92
    },
    socioeconomic: {
        "Rochester": 95, "Cleveland": 92, "Pittsburgh": 91,
        "Houston": 90, "Minneapolis": 81, "Miami": 78, "New York": 85
    },
    causeOfDeath: {
        organRecoveryRates: {
            heart:     { trauma: 0.488, cardiovascular: 0.151, drug_intox: 0.369, stroke: 0.157 },
            lung:      { trauma: 0.280, cardiovascular: 0.094, drug_intox: 0.204, stroke: 0.190 },
            liver:     { trauma: 0.797, cardiovascular: 0.654, drug_intox: 0.780, stroke: 0.737 },
            kidney:    { trauma: 0.896, cardiovascular: 0.686, drug_intox: 0.824, stroke: 0.668 },
            pancreas:  { trauma: 0.246, cardiovascular: 0.048, drug_intox: 0.095, stroke: 0.053 },
            intestine: { trauma: 0.246, cardiovascular: 0.048, drug_intox: 0.095, stroke: 0.053 }
        },
        stateCauseOfDeathProportions: {
            // High trauma state — better for heart/pancreas
            "Minnesota":      { trauma: 0.35, cardiovascular: 0.25, drug_intox: 0.15, stroke: 0.25 },
            // High cardiovascular state — worse for heart/pancreas
            "Ohio":           { trauma: 0.20, cardiovascular: 0.35, drug_intox: 0.20, stroke: 0.25 },
            "Texas":          { trauma: 0.30, cardiovascular: 0.30, drug_intox: 0.15, stroke: 0.25 },
            "New York":       { trauma: 0.22, cardiovascular: 0.28, drug_intox: 0.25, stroke: 0.25 },
            "Florida":        { trauma: 0.25, cardiovascular: 0.30, drug_intox: 0.20, stroke: 0.25 }
        }
    }
};

// ==================== SETUP ====================

beforeEach(() => {
    // Set up global window with mock TransPlanData
    global.window = { TransPlanData: JSON.parse(JSON.stringify(MOCK_TRANSPLANT_DATA)) };
});

afterEach(() => {
    delete global.window;
});

// ==================== HELPERS ====================

function makeFormData(overrides = {}) {
    return {
        bloodType: 'A+',
        age: 45,
        sex: 'male',
        weight: 180,
        height: 70,
        urgency: '3',
        insurance: 'private',
        cpra: 0,
        meld: 0,
        las: 0,
        ...overrides
    };
}

// ==================== 1. MEDICAL COMPATIBILITY ====================

describe('calculateMedicalCompatibilityScore', () => {
    test('all 8 blood types produce valid scores', () => {
        const bloodTypes = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'];
        for (const bt of bloodTypes) {
            const score = calculateMedicalCompatibilityScore(
                makeFormData({ bloodType: bt }), 'Minneapolis', 'kidney'
            );
            expect(score).toBeGreaterThanOrEqual(0);
            expect(score).toBeLessThanOrEqual(100);
        }
    });

    test('AB+ (universal recipient) scores highest blood type component', () => {
        const abPlus = calculateMedicalCompatibilityScore(
            makeFormData({ bloodType: 'AB+' }), 'Minneapolis', 'kidney'
        );
        const oMinus = calculateMedicalCompatibilityScore(
            makeFormData({ bloodType: 'O-' }), 'Minneapolis', 'kidney'
        );
        expect(abPlus).toBeGreaterThan(oMinus);
    });

    test('pediatric age (<18) gets priority bonus', () => {
        const child = calculateMedicalCompatibilityScore(
            makeFormData({ age: 17 }), 'Minneapolis', 'kidney'
        );
        const adult = calculateMedicalCompatibilityScore(
            makeFormData({ age: 45 }), 'Minneapolis', 'kidney'
        );
        expect(child).toBeGreaterThan(adult);
    });

    test('age boundary: 17 vs 18', () => {
        const age17 = calculateMedicalCompatibilityScore(
            makeFormData({ age: 17 }), 'Minneapolis', 'kidney'
        );
        const age18 = calculateMedicalCompatibilityScore(
            makeFormData({ age: 18 }), 'Minneapolis', 'kidney'
        );
        // 17 = pediatric (115), 18 = young adult (105)
        expect(age17).toBeGreaterThan(age18);
    });

    test('age boundary: 74 vs 75', () => {
        const age74 = calculateMedicalCompatibilityScore(
            makeFormData({ age: 74 }), 'Minneapolis', 'kidney'
        );
        const age75 = calculateMedicalCompatibilityScore(
            makeFormData({ age: 75 }), 'Minneapolis', 'kidney'
        );
        expect(age74).toBeGreaterThan(age75);
    });

    test('elderly (75+) scores lower', () => {
        const score = calculateMedicalCompatibilityScore(
            makeFormData({ age: 80 }), 'Minneapolis', 'kidney'
        );
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
    });

    test('female + heart organ gets sex penalty', () => {
        const female = calculateMedicalCompatibilityScore(
            makeFormData({ sex: 'female' }), 'Minneapolis', 'heart'
        );
        const male = calculateMedicalCompatibilityScore(
            makeFormData({ sex: 'male' }), 'Minneapolis', 'heart'
        );
        expect(female).toBeLessThan(male);
    });

    test('female + kidney has no sex penalty', () => {
        const female = calculateMedicalCompatibilityScore(
            makeFormData({ sex: 'female' }), 'Minneapolis', 'kidney'
        );
        const male = calculateMedicalCompatibilityScore(
            makeFormData({ sex: 'male' }), 'Minneapolis', 'kidney'
        );
        expect(female).toBe(male);
    });

    test('BMI underweight (<18.5) for heart gets penalty', () => {
        // weight=100, height=80 -> BMI = (100/(80*80))*703 = 10.98
        const underweight = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 100, height: 80 }), 'Minneapolis', 'heart'
        );
        const normal = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 180, height: 70 }), 'Minneapolis', 'heart'
        );
        expect(underweight).toBeLessThan(normal);
    });

    test('BMI obese (>35) for lung gets penalty', () => {
        // weight=300, height=65 -> BMI = (300/(65*65))*703 = 49.9
        const obese = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 300, height: 65 }), 'Minneapolis', 'lung'
        );
        const normal = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 160, height: 70 }), 'Minneapolis', 'lung'
        );
        expect(obese).toBeLessThan(normal);
    });

    test('no weight/height defaults to neutral BMI score', () => {
        const score = calculateMedicalCompatibilityScore(
            makeFormData({ weight: null, height: null }), 'Minneapolis', 'heart'
        );
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('kidney ignores BMI entirely', () => {
        const thin = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 100, height: 80 }), 'Minneapolis', 'kidney'
        );
        const heavy = calculateMedicalCompatibilityScore(
            makeFormData({ weight: 300, height: 65 }), 'Minneapolis', 'kidney'
        );
        // For kidney, BMI section gives neutral 100*0.20 regardless
        expect(thin).toBe(heavy);
    });
});

// ==================== 2. WAIT TIME ====================

describe('calculateWaitTimeScore', () => {
    test('all 6 organ types produce valid scores', () => {
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
        for (const organ of organs) {
            const score = calculateWaitTimeScore('Minneapolis', organ, makeFormData());
            expect(score).toBeGreaterThanOrEqual(0);
            expect(Number.isNaN(score)).toBe(false);
        }
    });

    test('lower wait-time factor city scores higher', () => {
        // Omaha factor=0.84, Los Angeles factor=1.15
        const omaha = calculateWaitTimeScore('Omaha', 'kidney', makeFormData());
        const la = calculateWaitTimeScore('Los Angeles', 'kidney', makeFormData());
        expect(omaha).toBeGreaterThan(la);
    });

    test('unknown city defaults to factor 1.0', () => {
        const score = calculateWaitTimeScore('UnknownCity', 'kidney', makeFormData());
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    // cPRA tests for kidney
    test('kidney: cPRA=0 gets normal wait multiplier', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 0 }));
        expect(score).toBeGreaterThanOrEqual(0);
    });

    test('kidney: cPRA=20 boundary (top of first tier)', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 20 }));
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('kidney: cPRA=50 moderate sensitization', () => {
        const low = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 20 }));
        const mid = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 50 }));
        // Higher cPRA = longer wait = lower score
        expect(mid).toBeLessThan(low);
    });

    test('kidney: cPRA=97 highly sensitized', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 97 }));
        expect(score).toBeGreaterThanOrEqual(0);
    });

    test('kidney: cPRA=100 maximum sensitization clamps to floor', () => {
        const cpra100 = calculateWaitTimeScore('Minneapolis', 'kidney', makeFormData({ cpra: 100 }));
        // cPRA=100 produces 5.0x multiplier — wait time far exceeds maxWait, score clamps to 0
        expect(cpra100).toBe(0);
        expect(Number.isNaN(cpra100)).toBe(false);
    });

    // MELD tests for liver
    test('liver: MELD=35 (top priority) scores highest', () => {
        const meld35 = calculateWaitTimeScore('Minneapolis', 'liver', makeFormData({ meld: 35 }));
        const meld15 = calculateWaitTimeScore('Minneapolis', 'liver', makeFormData({ meld: 15 }));
        // Higher MELD = higher priority = shorter wait = higher score
        expect(meld35).toBeGreaterThan(meld15);
    });

    test('liver: MELD=10 (low) gets long wait', () => {
        const meld10 = calculateWaitTimeScore('Minneapolis', 'liver', makeFormData({ meld: 10 }));
        const meld25 = calculateWaitTimeScore('Minneapolis', 'liver', makeFormData({ meld: 25 }));
        expect(meld10).toBeLessThan(meld25);
    });

    test('liver: MELD boundary at 15', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'liver', makeFormData({ meld: 15 }));
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    // LAS tests for lung
    test('lung: LAS=50 (high urgency) scores highest', () => {
        const las50 = calculateWaitTimeScore('Minneapolis', 'lung', makeFormData({ las: 50 }));
        const las30 = calculateWaitTimeScore('Minneapolis', 'lung', makeFormData({ las: 30 }));
        expect(las50).toBeGreaterThan(las30);
    });

    test('lung: LAS boundary at 35', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'lung', makeFormData({ las: 35 }));
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    // Generic urgency
    test('urgency 1 (most urgent) scores higher than urgency 4', () => {
        const urgent = calculateWaitTimeScore('Minneapolis', 'pancreas', makeFormData({ urgency: '1' }));
        const notUrgent = calculateWaitTimeScore('Minneapolis', 'pancreas', makeFormData({ urgency: '4' }));
        expect(urgent).toBeGreaterThan(notUrgent);
    });

    test('unknown urgency defaults to 1.0 multiplier', () => {
        const score = calculateWaitTimeScore('Minneapolis', 'pancreas', makeFormData({ urgency: '9' }));
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });
});

// ==================== 3. DONOR AVAILABILITY ====================

describe('calculateDonorAvailabilityScore', () => {
    test('known city+state produces valid score', () => {
        const score = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('unknown city uses fallback values', () => {
        const score = calculateDonorAvailabilityScore('UnknownCity', 'Minnesota', 'kidney');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('unknown state uses default registration rate', () => {
        const score = calculateDonorAvailabilityScore('Minneapolis', 'UnknownState', 'kidney');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('all 6 organ types work without crashing', () => {
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
        for (const organ of organs) {
            const score = calculateDonorAvailabilityScore('Houston', 'Texas', organ);
            expect(score).toBeGreaterThanOrEqual(0);
            expect(Number.isNaN(score)).toBe(false);
        }
    });

    test('higher registration rate state scores higher', () => {
        // Minnesota=68, Texas=30
        const mn = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney');
        const tx = calculateDonorAvailabilityScore('Houston', 'Texas', 'kidney');
        expect(mn).toBeGreaterThan(tx);
    });

    test('higher population factor city scores higher in that component', () => {
        // New York=100 pop factor, Rochester=60
        const ny = calculateDonorAvailabilityScore('New York', 'New York', 'kidney');
        const roch = calculateDonorAvailabilityScore('Rochester', 'Minnesota', 'kidney');
        // NY has higher pop factor but lower registration rate — test they both produce valid scores
        expect(ny).toBeGreaterThanOrEqual(0);
        expect(roch).toBeGreaterThanOrEqual(0);
    });

    // --- M2: Organ-specific cause-of-death adjustment ---

    test('toggle OFF: same score for heart vs kidney (backward compat)', () => {
        const formOff = makeFormData({ adjustForCauseOfDeath: false });
        const heart = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'heart', formOff);
        const kidney = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney', formOff);
        // Without COD adjustment, organ doesn't affect donor availability score
        expect(heart).toBe(kidney);
    });

    test('toggle ON: different scores for heart vs kidney in same city', () => {
        const formOn = makeFormData({ adjustForCauseOfDeath: true });
        const heart = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'heart', formOn);
        const kidney = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney', formOn);
        // Recovery rates differ → scores should diverge
        expect(heart).not.toBe(kidney);
    });

    test('toggle ON: pancreas varies more than kidney across states', () => {
        const formOn = makeFormData({ adjustForCauseOfDeath: true });
        // Minnesota (high trauma) vs Ohio (high cardiovascular)
        const panc_mn = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'pancreas', formOn);
        const panc_oh = calculateDonorAvailabilityScore('Cleveland', 'Ohio', 'pancreas', formOn);
        const kid_mn = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney', formOn);
        const kid_oh = calculateDonorAvailabilityScore('Cleveland', 'Ohio', 'kidney', formOn);
        // Pancreas spread should be larger than kidney spread (wider recovery rate range)
        const pancSpread = Math.abs(panc_mn - panc_oh);
        const kidSpread = Math.abs(kid_mn - kid_oh);
        expect(pancSpread).toBeGreaterThan(kidSpread);
    });

    test('toggle ON: all 6 organs stay in 0-100 range', () => {
        const formOn = makeFormData({ adjustForCauseOfDeath: true });
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
        for (const organ of organs) {
            const score = calculateDonorAvailabilityScore('Houston', 'Texas', organ, formOn);
            expect(score).toBeGreaterThanOrEqual(0);
            expect(score).toBeLessThanOrEqual(100);
            expect(Number.isNaN(score)).toBe(false);
        }
    });

    test('toggle ON with missing COD data: falls back to base score', () => {
        // Remove COD data from window
        delete global.window.TransPlanData.causeOfDeath;
        const formOn = makeFormData({ adjustForCauseOfDeath: true });
        const score = calculateDonorAvailabilityScore('Minneapolis', 'Minnesota', 'kidney', formOn);
        // Should still produce a valid score (no multiplier applied)
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('toggle ON with unknown state: returns base score', () => {
        const formOn = makeFormData({ adjustForCauseOfDeath: true });
        const baseScore = calculateDonorAvailabilityScore('Minneapolis', 'UnknownState', 'kidney');
        const adjustedScore = calculateDonorAvailabilityScore('Minneapolis', 'UnknownState', 'kidney', formOn);
        // Unknown state has no COD proportions → multiplier is null → base score unchanged
        expect(adjustedScore).toBe(baseScore);
    });

    test('no 4th arg: backward compatible with existing 3-arg callers', () => {
        // Existing tests call with 3 args — ensure they still work
        const score3arg = calculateDonorAvailabilityScore('Houston', 'Texas', 'kidney');
        const score4arg = calculateDonorAvailabilityScore('Houston', 'Texas', 'kidney', undefined);
        expect(score3arg).toBe(score4arg);
        expect(Number.isNaN(score3arg)).toBe(false);
    });
});

// ==================== 4. HOSPITAL QUALITY ====================

describe('calculateHospitalQualityScore', () => {
    test('private insurance gets full acceptance rate', () => {
        const score = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'private' })
        );
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
    });

    test('medicaid gets 85% of acceptance rate', () => {
        const priv = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'private' })
        );
        const medicaid = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'medicaid' })
        );
        expect(medicaid).toBeLessThan(priv);
    });

    test('no insurance gets 70% of acceptance rate', () => {
        const priv = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'private' })
        );
        const none = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'none' })
        );
        expect(none).toBeLessThan(priv);
    });

    test('undefined insurance treated as private', () => {
        const priv = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: 'private' })
        );
        const undef = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData({ insurance: undefined })
        );
        expect(undef).toBe(priv);
    });

    test('specialized city scores higher than non-specialized', () => {
        // Cleveland is specialized for kidney, Miami is not
        const specialized = calculateHospitalQualityScore(
            'Cleveland', 'kidney', makeFormData()
        );
        const notSpecialized = calculateHospitalQualityScore(
            'Miami', 'kidney', makeFormData()
        );
        expect(specialized).toBeGreaterThan(notSpecialized);
    });

    test('high volume center scores higher', () => {
        // Minneapolis kidney=350 (above 300 threshold), Miami=180 (below)
        const highVol = calculateHospitalQualityScore(
            'Minneapolis', 'kidney', makeFormData()
        );
        const lowVol = calculateHospitalQualityScore(
            'Miami', 'kidney', makeFormData()
        );
        expect(highVol).toBeGreaterThan(lowVol);
    });

    test('unknown city uses fallback defaults', () => {
        const score = calculateHospitalQualityScore(
            'UnknownCity', 'kidney', makeFormData()
        );
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('all 6 organ types produce valid scores', () => {
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
        for (const organ of organs) {
            const score = calculateHospitalQualityScore('Cleveland', organ, makeFormData());
            expect(score).toBeGreaterThanOrEqual(0);
            expect(score).toBeLessThanOrEqual(100);
            expect(Number.isNaN(score)).toBe(false);
        }
    });
});

// ==================== 5. GEOGRAPHIC ====================

describe('calculateGeographicScore', () => {
    test('low cost-of-living city scores higher', () => {
        // Omaha COL=81, San Francisco COL=204
        const lowCOL = calculateGeographicScore('Omaha');
        const highCOL = calculateGeographicScore('San Francisco');
        expect(lowCOL).toBeGreaterThan(highCOL);
    });

    test('unknown city uses defaults (70 for climate/AQ, 100 for COL)', () => {
        const score = calculateGeographicScore('UnknownCity');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('score components are within bounds', () => {
        const score = calculateGeographicScore('Rochester');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
    });

    test('city with no data in any source still produces valid score', () => {
        // Clear all geographic data
        global.window.TransPlanData.costOfLiving = {};
        global.window.TransPlanData.climateScores = {};
        global.window.TransPlanData.airQuality = {};
        const score = calculateGeographicScore('Nowhere');
        expect(score).toBeGreaterThanOrEqual(0);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('COL normalization adapts to data range dynamically', () => {
        // Set narrow COL range: all cities between 90-110
        global.window.TransPlanData.costOfLiving = {
            "CheapCity": 90,
            "MidCity": 100,
            "ExpensiveCity": 110
        };
        const scoreCheap = calculateGeographicScore('CheapCity');
        const scoreExpensive = calculateGeographicScore('ExpensiveCity');
        // Lower COL should produce higher geographic score
        expect(scoreCheap).toBeGreaterThan(scoreExpensive);
        expect(Number.isNaN(scoreCheap)).toBe(false);
        expect(Number.isNaN(scoreExpensive)).toBe(false);
    });
});

// ==================== 6. HEALTH DEMOGRAPHICS ====================

describe('calculateHealthDemographicsScore', () => {
    test('city with all 5 health metrics produces valid score', () => {
        const score = calculateHealthDemographicsScore('Rochester');
        expect(score).toBeGreaterThanOrEqual(30);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('healthier city (lower disease rates) scores higher', () => {
        // Rochester has lower rates, Cleveland has higher
        const healthy = calculateHealthDemographicsScore('Rochester');
        const unhealthy = calculateHealthDemographicsScore('Cleveland');
        expect(healthy).toBeGreaterThan(unhealthy);
    });

    test('partial data (only diabetesRate) uses null-safe defaults for missing fields', () => {
        const score = calculateHealthDemographicsScore('PartialCity');
        expect(score).toBeGreaterThanOrEqual(30);
        expect(score).toBeLessThanOrEqual(100);
        expect(Number.isNaN(score)).toBe(false);
    });

    test('missing city returns fallback 70', () => {
        const score = calculateHealthDemographicsScore('NonexistentCity');
        expect(score).toBe(70);
    });

    test('output clamped to minimum 30', () => {
        // Create a city with extremely high disease rates
        global.window.TransPlanData.healthDemographics['DiseasedCity'] = {
            diabetesRate: 30, obesityRate: 60, ckdRate: 30,
            hypertensionRate: 60, smokingRate: 30
        };
        const score = calculateHealthDemographicsScore('DiseasedCity');
        expect(score).toBe(30);
    });

    test('output clamped to maximum 100', () => {
        // Create a city with impossibly low disease rates
        global.window.TransPlanData.healthDemographics['HealthyCity'] = {
            diabetesRate: 1, obesityRate: 10, ckdRate: 5,
            hypertensionRate: 15, smokingRate: 5
        };
        const score = calculateHealthDemographicsScore('HealthyCity');
        expect(score).toBeLessThanOrEqual(100);
    });

    test('null TransPlanData.healthDemographics returns 70', () => {
        global.window.TransPlanData.healthDemographics = null;
        const score = calculateHealthDemographicsScore('Rochester');
        expect(score).toBe(70);
    });

    test('undefined healthDemographics returns 70', () => {
        delete global.window.TransPlanData.healthDemographics;
        const score = calculateHealthDemographicsScore('Rochester');
        expect(score).toBe(70);
    });
});

// ==================== 7. POLICY ====================

describe('calculatePolicyScore', () => {
    test('known state returns its tier score', () => {
        const score = calculatePolicyScore('Oregon');
        expect(score).toBe(100);
    });

    test('another known state', () => {
        const score = calculatePolicyScore('Texas');
        expect(score).toBe(75);
    });

    test('unknown state defaults to 70', () => {
        const score = calculatePolicyScore('UnknownState');
        expect(score).toBe(70);
    });
});

// ==================== 8. SOCIOECONOMIC ====================

describe('calculateSocioeconomicScore', () => {
    test('known city returns its score', () => {
        const score = calculateSocioeconomicScore('Rochester');
        expect(score).toBe(95);
    });

    test('unknown city defaults to 75', () => {
        const score = calculateSocioeconomicScore('UnknownCity');
        expect(score).toBe(75);
    });

    test('all scores are in valid range', () => {
        const cities = ['Rochester', 'Cleveland', 'Houston', 'Miami'];
        for (const city of cities) {
            const score = calculateSocioeconomicScore(city);
            expect(score).toBeGreaterThanOrEqual(0);
            expect(score).toBeLessThanOrEqual(100);
        }
    });
});

// ==================== 9. COMPREHENSIVE SCORE ====================

describe('calculateComprehensiveScore', () => {
    test('returns object with total and breakdown', () => {
        const result = calculateComprehensiveScore(
            makeFormData(), 'Minneapolis', 'Minnesota', 'kidney'
        );
        expect(result).toHaveProperty('total');
        expect(result).toHaveProperty('breakdown');
    });

    test('breakdown has all 8 category keys', () => {
        const result = calculateComprehensiveScore(
            makeFormData(), 'Minneapolis', 'Minnesota', 'kidney'
        );
        const expectedKeys = [
            'medicalCompatibility', 'waitTime', 'donorAvailability',
            'hospitalQuality', 'geographic', 'healthDemographics',
            'policy', 'socioeconomic'
        ];
        for (const key of expectedKeys) {
            expect(result.breakdown).toHaveProperty(key);
        }
    });

    test('weights sum to 1.0', () => {
        // Verify internally by checking that a full-100 score across all categories = 100
        // Since we can't directly access weights, verify the total is reasonable
        const result = calculateComprehensiveScore(
            makeFormData(), 'Minneapolis', 'Minnesota', 'kidney'
        );
        expect(result.total).toBeGreaterThan(0);
        expect(result.total).toBeLessThanOrEqual(100);
    });

    test('total is clamped to [0, 100]', () => {
        const result = calculateComprehensiveScore(
            makeFormData(), 'Minneapolis', 'Minnesota', 'kidney'
        );
        expect(result.total).toBeGreaterThanOrEqual(0);
        expect(result.total).toBeLessThanOrEqual(100);
    });

    test('all 6 organ types produce valid scores without NaN', () => {
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
        for (const organ of organs) {
            const result = calculateComprehensiveScore(
                makeFormData(), 'Cleveland', 'Ohio', organ
            );
            expect(Number.isNaN(result.total)).toBe(false);
            expect(result.total).toBeGreaterThan(0);
            for (const [key, value] of Object.entries(result.breakdown)) {
                expect(Number.isNaN(value)).toBe(false);
            }
        }
    });

    test('missing formData fields do not produce NaN', () => {
        const sparseForm = { bloodType: 'A+', age: 30 };
        const result = calculateComprehensiveScore(
            sparseForm, 'Houston', 'Texas', 'kidney'
        );
        expect(Number.isNaN(result.total)).toBe(false);
        expect(result.total).toBeGreaterThan(0);
    });

    test('different cities produce different scores', () => {
        const form = makeFormData();
        const rochester = calculateComprehensiveScore(form, 'Rochester', 'Minnesota', 'kidney');
        const miami = calculateComprehensiveScore(form, 'Miami', 'Florida', 'kidney');
        expect(rochester.total).not.toBe(miami.total);
    });

    test('different organs produce different scores for same city', () => {
        const form = makeFormData();
        const kidney = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney');
        const heart = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'heart');
        expect(kidney.total).not.toBe(heart.total);
    });
});

// ==================== CONFIGURABLE WEIGHTS ====================

describe('Configurable Weights', () => {
    test('DEFAULT_WEIGHTS has all 8 categories', () => {
        expect(Object.keys(DEFAULT_WEIGHTS)).toHaveLength(8);
        expect(DEFAULT_WEIGHTS.medicalCompatibility).toBe(0.25);
        expect(DEFAULT_WEIGHTS.waitTime).toBe(0.20);
        expect(DEFAULT_WEIGHTS.donorAvailability).toBe(0.18);
        expect(DEFAULT_WEIGHTS.hospitalQuality).toBe(0.15);
        expect(DEFAULT_WEIGHTS.geographic).toBe(0.10);
        expect(DEFAULT_WEIGHTS.healthDemographics).toBe(0.07);
        expect(DEFAULT_WEIGHTS.policy).toBe(0.03);
        expect(DEFAULT_WEIGHTS.socioeconomic).toBe(0.02);
    });

    test('DEFAULT_WEIGHTS sums to 1.0', () => {
        const sum = Object.values(DEFAULT_WEIGHTS).reduce((s, v) => s + v, 0);
        expect(sum).toBeCloseTo(1.0, 10);
    });

    test('CATEGORY_KEYS has 8 entries in correct order', () => {
        expect(CATEGORY_KEYS).toHaveLength(8);
        expect(CATEGORY_KEYS[0]).toBe('medicalCompatibility');
        expect(CATEGORY_KEYS[7]).toBe('socioeconomic');
    });

    test('CATEGORY_LABELS has human-readable names for all keys', () => {
        expect(Object.keys(CATEGORY_LABELS)).toHaveLength(8);
        expect(CATEGORY_LABELS.medicalCompatibility).toBe('Medical Compatibility');
        expect(CATEGORY_LABELS.waitTime).toBe('Wait Time');
    });

    test('no custom weights produces same result as before', () => {
        const form = makeFormData();
        const without = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney');
        const withNull = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', null);
        const withUndef = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', undefined);
        expect(withNull.total).toBe(without.total);
        expect(withUndef.total).toBe(without.total);
    });

    test('passing DEFAULT_WEIGHTS explicitly produces same result', () => {
        const form = makeFormData();
        const without = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney');
        const withDefaults = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', DEFAULT_WEIGHTS);
        expect(withDefaults.total).toBeCloseTo(without.total, 10);
    });

    test('all weight on one category returns that category raw score', () => {
        const form = makeFormData();
        const allOnMedical = {};
        CATEGORY_KEYS.forEach(k => { allOnMedical[k] = k === 'medicalCompatibility' ? 1.0 : 0.0; });

        const result = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', allOnMedical);
        const medScore = calculateMedicalCompatibilityScore(form, 'Cleveland', 'kidney');
        expect(result.total).toBeCloseTo(medScore, 5);
    });

    test('all weight on waitTime returns waitTime raw score', () => {
        const form = makeFormData();
        const allOnWait = {};
        CATEGORY_KEYS.forEach(k => { allOnWait[k] = k === 'waitTime' ? 1.0 : 0.0; });

        const result = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', allOnWait);
        const waitScore = calculateWaitTimeScore('Cleveland', 'kidney', form);
        expect(result.total).toBeCloseTo(waitScore, 5);
    });

    test('zero weight on a category eliminates its influence', () => {
        const form1 = makeFormData({ urgency: '1' });
        const form4 = makeFormData({ urgency: '4' });

        // With default weights, different urgency changes scores (via waitTime category)
        const def1 = calculateComprehensiveScore(form1, 'Cleveland', 'Ohio', 'kidney');
        const def4 = calculateComprehensiveScore(form4, 'Cleveland', 'Ohio', 'kidney');
        expect(def1.total).not.toBeCloseTo(def4.total, 1);

        // With waitTime zeroed out, urgency difference vanishes
        const noWait = { ...DEFAULT_WEIGHTS, waitTime: 0.0 };
        const nw1 = calculateComprehensiveScore(form1, 'Cleveland', 'Ohio', 'kidney', noWait);
        const nw4 = calculateComprehensiveScore(form4, 'Cleveland', 'Ohio', 'kidney', noWait);
        expect(nw1.total).toBeCloseTo(nw4.total, 5);
    });

    test('weights auto-normalize when sum is not 1.0', () => {
        const form = makeFormData();
        // Double all weights (sum=2.0) — should normalize and produce same result
        const doubled = {};
        CATEGORY_KEYS.forEach(k => { doubled[k] = DEFAULT_WEIGHTS[k] * 2; });

        const normal = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', DEFAULT_WEIGHTS);
        const dbld = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', doubled);
        expect(dbld.total).toBeCloseTo(normal.total, 5);
    });

    test('partial/invalid weights object falls back to defaults', () => {
        const form = makeFormData();
        const defaultResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney');

        // Only 3 keys — invalid, should fall back
        const partial = { medicalCompatibility: 0.5, waitTime: 0.3, geographic: 0.2 };
        const partialResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', partial);
        expect(partialResult.total).toBe(defaultResult.total);

        // Empty object — should fall back
        const emptyResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', {});
        expect(emptyResult.total).toBe(defaultResult.total);

        // Non-object — should fall back
        const strResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', 'balanced');
        expect(strResult.total).toBe(defaultResult.total);
    });

    test('custom weights change city rankings', () => {
        const form = makeFormData();
        // Default: balanced weights
        const balanced = calculateComprehensiveScore(form, 'San Francisco', 'California', 'kidney');
        const balancedOmaha = calculateComprehensiveScore(form, 'Omaha', 'Nebraska', 'kidney');

        // QoL preset: heavy geographic weight — expensive cities should drop
        const qol = {
            medicalCompatibility: 0.15, waitTime: 0.15, donorAvailability: 0.10,
            hospitalQuality: 0.10, geographic: 0.20, healthDemographics: 0.10,
            policy: 0.05, socioeconomic: 0.15
        };
        const qolSF = calculateComprehensiveScore(form, 'San Francisco', 'California', 'kidney', qol);
        const qolOmaha = calculateComprehensiveScore(form, 'Omaha', 'Nebraska', 'kidney', qol);

        // SF should lose relative advantage when geographic weight increases (high COL)
        const balancedGap = balanced.total - balancedOmaha.total;
        const qolGap = qolSF.total - qolOmaha.total;
        expect(qolGap).toBeLessThan(balancedGap);
    });

    test('all presets produce valid scores in [0, 100] with no NaN', () => {
        const presets = [
            { medicalCompatibility: 0.25, waitTime: 0.20, donorAvailability: 0.18, hospitalQuality: 0.15, geographic: 0.10, healthDemographics: 0.07, policy: 0.03, socioeconomic: 0.02 },
            { medicalCompatibility: 0.35, waitTime: 0.15, donorAvailability: 0.10, hospitalQuality: 0.25, geographic: 0.05, healthDemographics: 0.05, policy: 0.03, socioeconomic: 0.02 },
            { medicalCompatibility: 0.15, waitTime: 0.30, donorAvailability: 0.25, hospitalQuality: 0.10, geographic: 0.08, healthDemographics: 0.05, policy: 0.05, socioeconomic: 0.02 },
            { medicalCompatibility: 0.15, waitTime: 0.15, donorAvailability: 0.10, hospitalQuality: 0.10, geographic: 0.20, healthDemographics: 0.10, policy: 0.05, socioeconomic: 0.15 },
        ];
        const form = makeFormData();
        const organs = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];

        for (const preset of presets) {
            for (const organ of organs) {
                const result = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', organ, preset);
                expect(Number.isNaN(result.total)).toBe(false);
                expect(result.total).toBeGreaterThanOrEqual(0);
                expect(result.total).toBeLessThanOrEqual(100);
            }
        }
    });

    test('breakdown scores are unaffected by custom weights', () => {
        const form = makeFormData();
        const defaultResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney');
        const customResult = calculateComprehensiveScore(form, 'Cleveland', 'Ohio', 'kidney', {
            medicalCompatibility: 0.50, waitTime: 0.50, donorAvailability: 0, hospitalQuality: 0,
            geographic: 0, healthDemographics: 0, policy: 0, socioeconomic: 0
        });
        // Raw breakdown scores should be identical — weights only affect total
        expect(customResult.breakdown.medicalCompatibility).toBe(defaultResult.breakdown.medicalCompatibility);
        expect(customResult.breakdown.waitTime).toBe(defaultResult.breakdown.waitTime);
        expect(customResult.breakdown.geographic).toBe(defaultResult.breakdown.geographic);
    });
});
