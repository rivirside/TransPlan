// Mock data for transplant statistics by city and organ type
const cityData = {
    kidney: [
        {
            city: "Pittsburgh",
            state: "Pennsylvania",
            score: 94.2,
            waitTime: "1.8 years",
            donorRate: "High",
            matchRate: "87%",
            centersQuality: "Excellent",
            factors: [
                "Top-ranked transplant centers (UPMC)",
                "High regional donor registration (42%)",
                "Low diabetes prevalence in surrounding areas",
                "Strong regional donor recovery network",
                "Moderate cost of living enables transplant care access"
            ]
        },
        {
            city: "Minneapolis",
            state: "Minnesota",
            score: 91.7,
            waitTime: "2.1 years",
            donorRate: "Very High",
            matchRate: "84%",
            centersQuality: "Excellent",
            factors: [
                "Highest organ donor registration rate in US (68%)",
                "University of Minnesota transplant excellence",
                "Low obesity rates improve donor pool quality",
                "Strong public health infrastructure",
                "Active living donor programs"
            ]
        },
        {
            city: "Baltimore",
            state: "Maryland",
            score: 88.5,
            waitTime: "2.3 years",
            donorRate: "High",
            matchRate: "82%",
            centersQuality: "Excellent",
            factors: [
                "Johns Hopkins Hospital transplant leadership",
                "Regional organ sharing agreements",
                "Research-driven transplant protocols",
                "Diverse donor demographics improve matching",
                "Strong insurance acceptance rates"
            ]
        },
        {
            city: "Madison",
            state: "Wisconsin",
            score: 86.3,
            waitTime: "2.5 years",
            donorRate: "High",
            matchRate: "80%",
            centersQuality: "Very Good",
            factors: [
                "UW Health transplant program",
                "High regional health literacy",
                "Above-average living donor rates",
                "Low wait times for blood type O-",
                "Excellent post-transplant support infrastructure"
            ]
        },
        {
            city: "Portland",
            state: "Oregon",
            score: 83.9,
            waitTime: "2.8 years",
            donorRate: "High",
            matchRate: "79%",
            centersQuality: "Very Good",
            factors: [
                "OHSU transplant center expertise",
                "High organ donation awareness (58% registration)",
                "Healthier population reduces organ damage",
                "Strong living donor advocacy programs",
                "Pacific Northwest organ sharing network"
            ]
        }
    ],
    liver: [
        {
            city: "Los Angeles",
            state: "California",
            score: 92.8,
            waitTime: "0.9 years",
            donorRate: "Very High",
            matchRate: "85%",
            centersQuality: "Excellent",
            factors: [
                "UCLA and USC world-class liver programs",
                "Large population increases donor pool",
                "Advanced living donor liver transplant expertise",
                "High-volume centers improve outcomes",
                "Diverse blood type availability"
            ]
        },
        {
            city: "San Francisco",
            state: "California",
            score: 90.1,
            waitTime: "1.2 years",
            donorRate: "Very High",
            matchRate: "83%",
            centersQuality: "Excellent",
            factors: [
                "UCSF transplant innovation leader",
                "Shorter wait times due to MELD scoring",
                "Strong hepatology research programs",
                "Access to experimental treatments",
                "High insurance coverage rates"
            ]
        },
        {
            city: "Pittsburgh",
            state: "Pennsylvania",
            score: 88.4,
            waitTime: "1.4 years",
            donorRate: "High",
            matchRate: "81%",
            centersQuality: "Excellent",
            factors: [
                "UPMC pioneered liver transplantation",
                "High-volume center with excellent outcomes",
                "Research-driven protocol improvements",
                "Regional trauma centers increase donors",
                "Lower competition than major metro areas"
            ]
        },
        {
            city: "Dallas",
            state: "Texas",
            score: 86.7,
            waitTime: "1.6 years",
            donorRate: "High",
            matchRate: "79%",
            centersQuality: "Very Good",
            factors: [
                "Baylor University Medical Center excellence",
                "Lower wait times than national average",
                "Strong deceased donor program",
                "Growing living donor initiatives",
                "Affordable cost of living"
            ]
        },
        {
            city: "Rochester",
            state: "Minnesota",
            score: 84.2,
            waitTime: "1.8 years",
            donorRate: "High",
            matchRate: "78%",
            centersQuality: "Excellent",
            factors: [
                "Mayo Clinic transplant expertise",
                "Comprehensive pre and post-op care",
                "High success rates for complex cases",
                "Integrated healthcare system",
                "Strong focus on patient outcomes"
            ]
        }
    ],
    heart: [
        {
            city: "Cleveland",
            state: "Ohio",
            score: 93.5,
            waitTime: "4.2 months",
            donorRate: "High",
            matchRate: "81%",
            centersQuality: "Excellent",
            factors: [
                "Cleveland Clinic #1 in cardiac care",
                "Highest heart transplant volume in US",
                "Advanced mechanical support bridge programs",
                "Excellent survival outcomes",
                "Shorter wait times for Status 1 patients"
            ]
        },
        {
            city: "Nashville",
            state: "Tennessee",
            score: 89.8,
            waitTime: "5.1 months",
            donorRate: "High",
            matchRate: "78%",
            centersQuality: "Excellent",
            factors: [
                "Vanderbilt Heart transplant leadership",
                "Central location in organ sharing region",
                "Lower competition than coastal cities",
                "Strong deceased donor network",
                "Innovative preservation techniques"
            ]
        },
        {
            city: "Durham",
            state: "North Carolina",
            score: 87.3,
            waitTime: "5.8 months",
            donorRate: "High",
            matchRate: "76%",
            centersQuality: "Excellent",
            factors: [
                "Duke University Hospital cardiac excellence",
                "Research-driven transplant protocols",
                "High-quality donor organ assessment",
                "Strong VAD program for bridge therapy",
                "Excellent long-term survival rates"
            ]
        },
        {
            city: "Houston",
            state: "Texas",
            score: 85.1,
            waitTime: "6.3 months",
            donorRate: "Very High",
            matchRate: "75%",
            centersQuality: "Excellent",
            factors: [
                "Texas Heart Institute leadership",
                "Large donor pool from metro population",
                "Advanced mechanical circulatory support",
                "Multiple high-volume transplant centers",
                "Strong pediatric and adult programs"
            ]
        },
        {
            city: "Palo Alto",
            state: "California",
            score: 82.6,
            waitTime: "7.1 months",
            donorRate: "High",
            matchRate: "73%",
            centersQuality: "Excellent",
            factors: [
                "Stanford Hospital cardiac innovation",
                "Access to cutting-edge treatments",
                "Strong research and clinical integration",
                "Excellent post-transplant care",
                "High donor registration in Bay Area"
            ]
        }
    ],
    lung: [
        {
            city: "Durham",
            state: "North Carolina",
            score: 91.2,
            waitTime: "3.8 months",
            donorRate: "High",
            matchRate: "74%",
            centersQuality: "Excellent",
            factors: [
                "Duke performs most lung transplants in US",
                "Shortest median wait time nationally",
                "Advanced donor lung rehabilitation",
                "Strong pulmonary hypertension program",
                "Excellent bilateral lung transplant outcomes"
            ]
        },
        {
            city: "Pittsburgh",
            state: "Pennsylvania",
            score: 88.7,
            waitTime: "4.5 months",
            donorRate: "High",
            matchRate: "72%",
            centersQuality: "Excellent",
            factors: [
                "UPMC pioneered lung transplantation",
                "High-volume center improves expertise",
                "Strong COPD and IPF programs",
                "Regional organ sharing advantages",
                "Excellent patient selection protocols"
            ]
        },
        {
            city: "St. Louis",
            state: "Missouri",
            score: 86.4,
            waitTime: "5.2 months",
            donorRate: "High",
            matchRate: "70%",
            centersQuality: "Very Good",
            factors: [
                "Barnes-Jewish Hospital excellence",
                "Central US location for organ sharing",
                "Lower competition than coastal areas",
                "Strong cystic fibrosis program",
                "Good outcomes for complex cases"
            ]
        },
        {
            city: "Seattle",
            state: "Washington",
            score: 84.1,
            waitTime: "5.9 months",
            donorRate: "High",
            matchRate: "69%",
            centersQuality: "Very Good",
            factors: [
                "University of Washington Medical Center",
                "Pacific Northwest organ sharing network",
                "Strong living donor advocacy",
                "Innovative preservation techniques",
                "Comprehensive pulmonary rehabilitation"
            ]
        },
        {
            city: "Philadelphia",
            state: "Pennsylvania",
            score: 81.8,
            waitTime: "6.4 months",
            donorRate: "Moderate",
            matchRate: "68%",
            centersQuality: "Very Good",
            factors: [
                "Penn Medicine transplant expertise",
                "Multiple transplant centers in region",
                "Strong academic medical infrastructure",
                "Good insurance acceptance",
                "Established post-transplant support"
            ]
        }
    ],
    pancreas: [
        {
            city: "Minneapolis",
            state: "Minnesota",
            score: 92.4,
            waitTime: "1.4 years",
            donorRate: "Very High",
            matchRate: "76%",
            centersQuality: "Excellent",
            factors: [
                "University of Minnesota pioneered pancreas transplant",
                "Highest volume pancreas center globally",
                "Excellent diabetes management programs",
                "Strong simultaneous kidney-pancreas expertise",
                "Best outcomes for Type 1 diabetes patients"
            ]
        },
        {
            city: "Madison",
            state: "Wisconsin",
            score: 88.9,
            waitTime: "1.8 years",
            donorRate: "High",
            matchRate: "73%",
            centersQuality: "Excellent",
            factors: [
                "UW Health pancreas transplant leadership",
                "Strong islet cell transplant program",
                "Comprehensive diabetes care integration",
                "Lower wait times than national average",
                "High success rates for SPK transplants"
            ]
        },
        {
            city: "Miami",
            state: "Florida",
            score: 86.2,
            waitTime: "2.1 years",
            donorRate: "High",
            matchRate: "71%",
            centersQuality: "Very Good",
            factors: [
                "University of Miami diabetes research center",
                "Diverse donor pool improves matching",
                "Strong deceased donor program",
                "Innovative immunosuppression protocols",
                "Warm climate aids recovery"
            ]
        },
        {
            city: "San Francisco",
            state: "California",
            score: 83.7,
            waitTime: "2.5 years",
            donorRate: "High",
            matchRate: "69%",
            centersQuality: "Very Good",
            factors: [
                "UCSF pancreas transplant innovation",
                "Research-driven outcome improvements",
                "Strong living donor programs",
                "Access to clinical trials",
                "Excellent endocrinology integration"
            ]
        },
        {
            city: "Chicago",
            state: "Illinois",
            score: 81.3,
            waitTime: "2.8 years",
            donorRate: "Moderate",
            matchRate: "67%",
            centersQuality: "Very Good",
            factors: [
                "Northwestern Medicine expertise",
                "Multiple transplant centers provide options",
                "Large metro donor pool",
                "Strong insurance networks",
                "Comprehensive post-transplant care"
            ]
        }
    ],
    intestine: [
        {
            city: "Pittsburgh",
            state: "Pennsylvania",
            score: 94.8,
            waitTime: "8.2 months",
            donorRate: "High",
            matchRate: "65%",
            centersQuality: "Excellent",
            factors: [
                "UPMC performs most intestinal transplants globally",
                "Pioneered multivisceral transplantation",
                "Only center for some complex cases",
                "Excellent short bowel syndrome program",
                "Best survival rates for intestinal transplants"
            ]
        },
        {
            city: "Omaha",
            state: "Nebraska",
            score: 89.1,
            waitTime: "10.5 months",
            donorRate: "High",
            matchRate: "62%",
            centersQuality: "Excellent",
            factors: [
                "Nebraska Medicine intestinal transplant leader",
                "Strong pediatric intestinal program",
                "Central location in organ network",
                "Lower competition for organs",
                "Comprehensive rehabilitation programs"
            ]
        },
        {
            city: "Miami",
            state: "Florida",
            score: 85.6,
            waitTime: "12.1 months",
            donorRate: "Moderate",
            matchRate: "59%",
            centersQuality: "Very Good",
            factors: [
                "University of Miami intestinal expertise",
                "Strong multivisceral transplant program",
                "Diverse donor demographics",
                "Warm climate aids recovery",
                "Strong nutritional support teams"
            ]
        },
        {
            city: "Indianapolis",
            state: "Indiana",
            score: 82.3,
            waitTime: "13.8 months",
            donorRate: "Moderate",
            matchRate: "57%",
            centersQuality: "Very Good",
            factors: [
                "Indiana University Health intestinal program",
                "Good outcomes for complex cases",
                "Affordable cost of living",
                "Central Midwest location",
                "Strong post-transplant monitoring"
            ]
        },
        {
            city: "Los Angeles",
            state: "California",
            score: 79.7,
            waitTime: "15.2 months",
            donorRate: "Moderate",
            matchRate: "55%",
            centersQuality: "Good",
            factors: [
                "UCLA intestinal transplant program",
                "Large metro area donor pool",
                "Research hospital advantages",
                "Multiple transplant options in region",
                "Access to experimental treatments"
            ]
        }
    ]
};

// City coordinates for map markers
const cityCoordinates = {
    "Pittsburgh": [40.4406, -79.9959],
    "Minneapolis": [44.9778, -93.2650],
    "Baltimore": [39.2904, -76.6122],
    "Madison": [43.0731, -89.4012],
    "Portland": [45.5152, -122.6784],
    "Los Angeles": [34.0522, -118.2437],
    "San Francisco": [37.7749, -122.4194],
    "Dallas": [32.7767, -96.7970],
    "Rochester": [44.0121, -92.4802],
    "Cleveland": [41.4993, -81.6944],
    "Nashville": [36.1627, -86.7816],
    "Durham": [35.9940, -78.8986],
    "Houston": [29.7604, -95.3698],
    "Palo Alto": [37.4419, -122.1430],
    "St. Louis": [38.6270, -90.1994],
    "Seattle": [47.6062, -122.3321],
    "Philadelphia": [39.9526, -75.1652],
    "Miami": [25.7617, -80.1918],
    "Chicago": [41.8781, -87.6298],
    "Omaha": [41.2565, -95.9345],
    "Indianapolis": [39.7684, -86.1581]
};

// M3: Stored results for detail modal and comparison
let _currentResults = null;
let _currentSimResult = null;
let _currentFormData = null;
// M4: Equity analysis result
let _currentEquityResult = null;
// Submission guard to prevent concurrent form submissions (#66)
let _isSubmitting = false;

// M5: Expose results for export module
if (typeof window !== 'undefined') {
    window.TransPlanResults = {
        getResults: function() { return _currentResults; },
        getSimResult: function() { return _currentSimResult; },
        getFormData: function() { return _currentFormData; },
        getEquityResult: function() { return _currentEquityResult; }
    };
}

// ── Tier Config ──
var _tierConfig = null;

function fetchTierConfig() {
    var apiBase = window.TransPlanAPI ? window.TransPlanAPI.getBaseUrl() : '';
    return fetch(apiBase + '/tier')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            _tierConfig = data || _defaultWebTier();
            _applyTierCaps();
        })
        .catch(function() {
            _tierConfig = _defaultWebTier();
            _applyTierCaps();
        });
}

function _defaultWebTier() {
    return {
        name: 'web',
        caps: {
            max_iterations: 1000,
            allowed_inference_modes: ['monte_carlo', 'bayesian'],
            allowed_bbn_granularity: ['classic', 'state'],
            copula_theta_locked: true,
            elasticity_locked: true,
            max_equity_centers: 30,
            max_equity_iterations: 200,
            max_sensitivity_iterations: 500,
            max_whatif_iterations: 500,
            max_spatial_resolution: 30
        }
    };
}

function _applyTierCaps() {
    if (!_tierConfig) return;
    var caps = _tierConfig.caps;
    var badge = document.getElementById('tierBadge');
    if (badge) {
        badge.textContent = _tierConfig.name === 'local' ? 'Local' : 'Web';
        badge.className = 'tier-badge tier-' + _tierConfig.name;
    }
    // Iterations slider
    _capSlider('iterationsSlider', 'iterationsValue', caps.max_iterations);
    // BBN granularity dropdown
    _capSelect('bbnGranularity', caps.allowed_bbn_granularity);
    // Copula theta
    _lockControl('copulaThetaRow', caps.copula_theta_locked);
    // Elasticity
    _lockControl('elasticityRow', caps.elasticity_locked);
    // Equity
    _capSlider('equityCentersSlider', 'equityCentersValue', caps.max_equity_centers);
    _capSlider('equityIterSlider', 'equityIterValue', caps.max_equity_iterations);
}

function _capSlider(sliderId, valueId, maxVal) {
    var slider = document.getElementById(sliderId);
    if (!slider) return;
    slider.max = maxVal;
    if (parseInt(slider.value) > maxVal) slider.value = maxVal;
    var valueEl = document.getElementById(valueId);
    if (valueEl) valueEl.textContent = slider.value;
}

function _capSelect(selectId, allowedValues) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    Array.from(sel.options).forEach(function(opt) {
        if (allowedValues.indexOf(opt.value) === -1) {
            opt.disabled = true;
            if (opt.textContent.indexOf('(local only)') === -1) {
                opt.textContent += ' (local only)';
            }
        } else {
            opt.disabled = false;
        }
    });
    // If current value is not allowed, switch to last allowed
    if (allowedValues.indexOf(sel.value) === -1) {
        sel.value = allowedValues[allowedValues.length - 1];
    }
}

function _lockControl(rowId, locked) {
    var row = document.getElementById(rowId);
    if (!row) return;
    if (locked) {
        row.classList.add('tier-locked');
    } else {
        row.classList.remove('tier-locked');
    }
}

// Wire slider value displays
function _initAdvancedSliders() {
    var sliders = [
        ['iterationsSlider', 'iterationsValue', ''],
        ['copulaThetaSlider', 'copulaThetaValue', ''],
        ['elasticitySlider', 'elasticityValue', ''],
        ['donorMultSlider', 'donorMultValue', 'x'],
        ['waitMultSlider', 'waitMultValue', 'x'],
        ['equityCentersSlider', 'equityCentersValue', ''],
        ['equityIterSlider', 'equityIterValue', '']
    ];
    sliders.forEach(function(s) {
        var slider = document.getElementById(s[0]);
        var display = document.getElementById(s[1]);
        if (slider && display) {
            slider.addEventListener('input', function() {
                display.textContent = this.value + s[2];
            });
        }
    });
    // Show/hide BBN granularity row based on inference mode
    var inferenceSelect = document.getElementById('inferenceMode');
    if (inferenceSelect) {
        inferenceSelect.addEventListener('change', function() {
            var bbnRow = document.getElementById('bbnGranularityRow');
            if (bbnRow) {
                bbnRow.style.display = this.value === 'bayesian' ? '' : 'none';
            }
        });
    }
}

// Collect advanced simulation params from the panel
function _getAdvancedParams() {
    var params = {};
    var iterSlider = document.getElementById('iterationsSlider');
    if (iterSlider) params.iterations = parseInt(iterSlider.value);

    var bbnRow = document.getElementById('bbnGranularityRow');
    var bbnSelect = document.getElementById('bbnGranularity');
    if (bbnSelect && bbnRow && bbnRow.style.display !== 'none') {
        params.bbn_granularity = bbnSelect.value;
    }

    if (!_tierConfig || !_tierConfig.caps.copula_theta_locked) {
        var thetaSlider = document.getElementById('copulaThetaSlider');
        if (thetaSlider) params.copula_theta = parseFloat(thetaSlider.value);
    }

    if (!_tierConfig || !_tierConfig.caps.elasticity_locked) {
        var elastSlider = document.getElementById('elasticitySlider');
        if (elastSlider) params.elasticity = parseFloat(elastSlider.value);
    }

    var donorSlider = document.getElementById('donorMultSlider');
    if (donorSlider) params.donor_rate_multiplier = parseFloat(donorSlider.value);

    var waitSlider = document.getElementById('waitMultSlider');
    if (waitSlider) params.wait_time_multiplier = parseFloat(waitSlider.value);

    var eqCentersSlider = document.getElementById('equityCentersSlider');
    if (eqCentersSlider) params.max_equity_centers = parseInt(eqCentersSlider.value);

    var eqIterSlider = document.getElementById('equityIterSlider');
    if (eqIterSlider) params.equity_iterations = parseInt(eqIterSlider.value);

    return params;
}

// Map layers
let map;
let trafficHeatLayer;
let donorRegistrationHeatLayer;
let transplantCentersLayer;
let statePoliciesLayer;
let waitTimeGridLayer;
let diabetesLayer;
let obesityLayer;
let costOfLivingLayer;
let airQualityLayer;
let insuranceCoverageLayer;
let cityMarkersLayer;
let spatialHeatmapLayer;

// Pagination state
let _paginationPage = 0;
let _paginationPageSize = 20;
let _paginationFilterState = '';

// Initialize map
function initializeMap() {
    if (!window.TransPlanCDN?.leaflet || typeof L === 'undefined') {
        const mapEl = document.getElementById('map');
        if (mapEl) {
            const notice = document.createElement('div');
            notice.className = 'cdn-fallback-notice';
            const p = document.createElement('p');
            const strong = document.createElement('strong');
            strong.textContent = 'Map unavailable';
            p.appendChild(strong);
            p.appendChild(document.createTextNode(' \u2014 the mapping library could not be loaded. City rankings and scores are still displayed below.'));
            notice.appendChild(p);
            mapEl.replaceChildren(notice);
            mapEl.style.height = 'auto';
            mapEl.style.minHeight = '80px';
        }
        return;
    }

    // Create map centered on US
    map = L.map('map').setView([39.8283, -98.5795], 4);

    // Add base tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // Initialize layers
    trafficHeatLayer = L.layerGroup();
    donorRegistrationHeatLayer = L.layerGroup();
    transplantCentersLayer = L.layerGroup();
    statePoliciesLayer = L.layerGroup();
    waitTimeGridLayer = L.layerGroup();
    diabetesLayer = L.layerGroup();
    obesityLayer = L.layerGroup();
    costOfLivingLayer = L.layerGroup();
    airQualityLayer = L.layerGroup();
    insuranceCoverageLayer = L.layerGroup();
    spatialHeatmapLayer = L.layerGroup();
    cityMarkersLayer = L.layerGroup().addTo(map);

    // Create layer controls
    setupLayerControls();

    // Initialize default layers
    createTrafficAccidentHeatmap();
    createTransplantCentersLayer();
    setupSpatialHeatmapControls();
}

// Traffic accident fatalities data - combination of heatmap and state-level data
function createTrafficAccidentHeatmap() {
    trafficHeatLayer.clearLayers();

    // Major city accident hotspots for heatmap
    const accidentHotspots = [
        [34.0522, -118.2437, 0.9], // Los Angeles
        [29.7604, -95.3698, 0.85],  // Houston
        [33.4484, -112.0740, 0.82], // Phoenix
        [32.7767, -96.7970, 0.78],  // Dallas
        [25.7617, -80.1918, 0.8],   // Miami
        [39.7392, -104.9903, 0.72], // Denver
        [36.1699, -115.1398, 0.75], // Las Vegas
        [35.2271, -80.8431, 0.68],  // Charlotte
        [40.7128, -74.0060, 0.7],   // NYC
        [41.8781, -87.6298, 0.73],  // Chicago
        [30.2672, -97.7431, 0.65],  // Austin
        [33.7490, -84.3880, 0.71],  // Atlanta
        [37.3382, -121.8863, 0.68], // San Jose
        [39.2904, -76.6122, 0.6],   // Baltimore
        [39.9526, -75.1652, 0.65],  // Philadelphia
        [32.7157, -117.1611, 0.66], // San Diego
        [35.4676, -97.5164, 0.62],  // Oklahoma City
        [29.4241, -98.4936, 0.64],  // San Antonio
        [26.1224, -80.1373, 0.72],  // Fort Lauderdale
        [36.1627, -86.7816, 0.58],  // Nashville
        [39.0997, -94.5786, 0.6],   // Kansas City
        [27.9506, -82.4572, 0.67],  // Tampa
        [35.2226, -80.8431, 0.63],  // Charlotte
        [33.7490, -117.8877, 0.69]  // Riverside
    ];

    // Create heatmap layer (requires leaflet-heat plugin)
    if (!window.TransPlanCDN?.leafletHeat) {
        console.warn('leaflet-heat unavailable; skipping heatmap overlay.');
        return;
    }
    const heat = L.heatLayer(accidentHotspots, {
        radius: 50,
        blur: 40,
        maxZoom: 10,
        max: 1.0,
        gradient: {
            0.0: '#ffffb2',
            0.2: '#fed976',
            0.4: '#feb24c',
            0.6: '#fd8d3c',
            0.8: '#f03b20',
            1.0: '#bd0026'
        }
    }).addTo(trafficHeatLayer);

    // State-level fatality rates (per 100k population) - helps identify donor potential
    const stateFatalityRates = {
        "Mississippi": { rate: 23.1, fatalitiesPerYear: 683, color: "#bd0026" },
        "Wyoming": { rate: 22.3, fatalitiesPerYear: 129, color: "#bd0026" },
        "South Carolina": { rate: 21.8, fatalitiesPerYear: 1125, color: "#bd0026" },
        "Montana": { rate: 21.0, fatalitiesPerYear: 227, color: "#f03b20" },
        "Arkansas": { rate: 19.8, fatalitiesPerYear: 598, color: "#f03b20" },
        "Alabama": { rate: 19.2, fatalitiesPerYear: 944, color: "#f03b20" },
        "Louisiana": { rate: 18.6, fatalitiesPerYear: 864, color: "#f03b20" },
        "New Mexico": { rate: 18.4, fatalitiesPerYear: 386, color: "#f03b20" },
        "Kentucky": { rate: 17.3, fatalitiesPerYear: 775, color: "#fd8d3c" },
        "Oklahoma": { rate: 17.0, fatalitiesPerYear: 675, color: "#fd8d3c" },
        "Tennessee": { rate: 16.5, fatalitiesPerYear: 1135, color: "#fd8d3c" },
        "West Virginia": { rate: 16.3, fatalitiesPerYear: 293, color: "#fd8d3c" },
        "Florida": { rate: 15.7, fatalitiesPerYear: 3389, color: "#fd8d3c" },
        "Texas": { rate: 14.6, fatalitiesPerYear: 4290, color: "#feb24c" },
        "Arizona": { rate: 14.5, fatalitiesPerYear: 1057, color: "#feb24c" },
        "Georgia": { rate: 14.3, fatalitiesPerYear: 1540, color: "#feb24c" },
        "North Carolina": { rate: 14.0, fatalitiesPerYear: 1481, color: "#feb24c" },
        "Missouri": { rate: 13.8, fatalitiesPerYear: 849, color: "#feb24c" },
        "Nevada": { rate: 13.2, fatalitiesPerYear: 410, color: "#fed976" },
        "Indiana": { rate: 12.9, fatalitiesPerYear: 870, color: "#fed976" },
        "Kansas": { rate: 12.7, fatalitiesPerYear: 370, color: "#fed976" },
        "Idaho": { rate: 12.5, fatalitiesPerYear: 229, color: "#fed976" },
        "Ohio": { rate: 11.8, fatalitiesPerYear: 1377, color: "#fed976" },
        "California": { rate: 11.2, fatalitiesPerYear: 4407, color: "#ffffcc" },
        "Michigan": { rate: 11.1, fatalitiesPerYear: 1111, color: "#ffffcc" },
        "Virginia": { rate: 10.9, fatalitiesPerYear: 934, color: "#ffffcc" },
        "Pennsylvania": { rate: 10.8, fatalitiesPerYear: 1386, color: "#ffffcc" },
        "Wisconsin": { rate: 10.6, fatalitiesPerYear: 618, color: "#ffffcc" },
        "Illinois": { rate: 10.3, fatalitiesPerYear: 1299, color: "#f7fcb9" },
        "Colorado": { rate: 10.2, fatalitiesPerYear: 596, color: "#f7fcb9" },
        "Iowa": { rate: 10.1, fatalitiesPerYear: 319, color: "#f7fcb9" },
        "Oregon": { rate: 9.8, fatalitiesPerYear: 416, color: "#f7fcb9" },
        "Maryland": { rate: 9.2, fatalitiesPerYear: 558, color: "#f7fcb9" },
        "Washington": { rate: 8.9, fatalitiesPerYear: 682, color: "#e5f5e0" },
        "New Jersey": { rate: 8.1, fatalitiesPerYear: 723, color: "#e5f5e0" },
        "Connecticut": { rate: 7.8, fatalitiesPerYear: 279, color: "#e5f5e0" },
        "Minnesota": { rate: 7.5, fatalitiesPerYear: 423, color: "#e5f5e0" },
        "New York": { rate: 7.2, fatalitiesPerYear: 1398, color: "#c7e9c0" },
        "Massachusetts": { rate: 6.2, fatalitiesPerYear: 428, color: "#c7e9c0" },
        "Rhode Island": { rate: 5.8, fatalitiesPerYear: 61, color: "#a1d99b" }
    };

    // Add state overlay with semi-transparent fills
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const stateData = stateFatalityRates[stateName];

                    if (stateData) {
                        return {
                            fillColor: stateData.color,
                            weight: 1,
                            opacity: 0.4,
                            color: '#ffffff',
                            fillOpacity: 0.2
                        };
                    } else {
                        return {
                            fillColor: '#e5f5e0',
                            weight: 1,
                            opacity: 0.2,
                            color: '#cccccc',
                            fillOpacity: 0.1
                        };
                    }
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const stateData = stateFatalityRates[stateName];

                    if (stateData) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Traffic Fatality Rate: <strong style="color: #bd0026">${stateData.rate}</strong> per 100k<br>
                            Annual Fatalities: <strong>${stateData.fatalitiesPerYear}</strong><br>
                            <em style="font-size: 0.9em">One of several factors used in regional donor availability estimates</em>
                        `);
                    }

                    layer.on('mouseover', function() {
                        if (stateData) {
                            this.setStyle({
                                fillOpacity: 0.5,
                                weight: 2
                            });
                        }
                    });

                    layer.on('mouseout', function() {
                        this.setStyle({
                            fillOpacity: 0.2,
                            weight: 1
                        });
                    });
                }
            }).addTo(trafficHeatLayer);
        });

    // Add legend
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = `
            <h4>Traffic Fatalities</h4>
            <p style="font-size: 0.8em; margin-bottom: 8px;">Rate per 100k population</p>
            <div class="legend-item">
                <div class="legend-color" style="background: #bd0026;"></div>
                <span>&gt; 20 (Very High)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f03b20;"></div>
                <span>17-20 (High)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fd8d3c;"></div>
                <span>14-17 (Above Avg)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #feb24c;"></div>
                <span>12-14 (Average)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffffcc;"></div>
                <span>9-12 (Below Avg)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #c7e9c0;"></div>
                <span>&lt; 9 (Low)</span>
            </div>
        `;
        return div;
    };
    addLayerLegend('traffic', legend);
}

// Organ donor registration rates with state boundaries
function createDonorRegistrationHeatmap() {
    donorRegistrationHeatLayer.clearLayers();

    // Fetch US states GeoJSON
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            // State-by-state donor registration rates
            const donorRegistrationRates = {
                "Montana": { rate: 82, percentage: "82%" },
                "Alaska": { rate: 75, percentage: "75%" },
                "Minnesota": { rate: 68, percentage: "68%" },
                "Oregon": { rate: 58, percentage: "58%" },
                "Washington": { rate: 56, percentage: "56%" },
                "Wisconsin": { rate: 54, percentage: "54%" },
                "New York": { rate: 52, percentage: "52%" },
                "Massachusetts": { rate: 51, percentage: "51%" },
                "Iowa": { rate: 50, percentage: "50%" },
                "Colorado": { rate: 49, percentage: "49%" },
                "Illinois": { rate: 48, percentage: "48%" },
                "Nebraska": { rate: 47, percentage: "47%" },
                "California": { rate: 45, percentage: "45%" },
                "Connecticut": { rate: 44, percentage: "44%" },
                "Vermont": { rate: 44, percentage: "44%" },
                "Pennsylvania": { rate: 42, percentage: "42%" },
                "Ohio": { rate: 41, percentage: "41%" },
                "Maryland": { rate: 40, percentage: "40%" },
                "Michigan": { rate: 39, percentage: "39%" },
                "New Jersey": { rate: 38, percentage: "38%" },
                "North Carolina": { rate: 37, percentage: "37%" },
                "Indiana": { rate: 36, percentage: "36%" },
                "Virginia": { rate: 35, percentage: "35%" },
                "Arizona": { rate: 34, percentage: "34%" },
                "Nevada": { rate: 33, percentage: "33%" },
                "Missouri": { rate: 32, percentage: "32%" },
                "Tennessee": { rate: 31, percentage: "31%" },
                "Texas": { rate: 30, percentage: "30%" },
                "South Carolina": { rate: 29, percentage: "29%" },
                "Georgia": { rate: 28, percentage: "28%" },
                "Kentucky": { rate: 27, percentage: "27%" },
                "Florida": { rate: 26, percentage: "26%" },
                "Alabama": { rate: 25, percentage: "25%" },
                "Louisiana": { rate: 24, percentage: "24%" },
                "Arkansas": { rate: 24, percentage: "24%" },
                "Mississippi": { rate: 22, percentage: "22%" }
            };

            // Color scale function
            function getColorForRate(rate) {
                if (rate >= 65) return '#08306b';  // Very high (darkest blue)
                if (rate >= 55) return '#08519c';  // High
                if (rate >= 45) return '#2171b5';  // Above average
                if (rate >= 35) return '#4292c6';  // Average
                if (rate >= 28) return '#6baed6';  // Below average
                return '#9ecae1';                   // Low (lightest blue)
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const stateData = donorRegistrationRates[stateName];

                    if (stateData) {
                        return {
                            fillColor: getColorForRate(stateData.rate),
                            weight: 2,
                            opacity: 0.8,
                            color: '#ffffff',
                            fillOpacity: 0.7
                        };
                    } else {
                        return {
                            fillColor: '#d0d0d0',
                            weight: 1,
                            opacity: 0.5,
                            color: '#999999',
                            fillOpacity: 0.3
                        };
                    }
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const stateData = donorRegistrationRates[stateName];

                    if (stateData) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Donor Registration: <strong style="color: #2171b5; font-size: 1.2em">${stateData.percentage}</strong><br>
                            <em>of eligible adults registered as organ donors</em>
                        `);
                    } else {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            <em>Donor registration data not available</em>
                        `);
                    }

                    // Hover effects
                    layer.on('mouseover', function() {
                        this.setStyle({
                            fillOpacity: 0.9,
                            weight: 3,
                            color: '#ffff00'
                        });
                    });

                    layer.on('mouseout', function() {
                        const stateData = donorRegistrationRates[stateName];
                        this.setStyle({
                            fillOpacity: stateData ? 0.7 : 0.3,
                            weight: stateData ? 2 : 1,
                            color: stateData ? '#ffffff' : '#999999'
                        });
                    });
                }
            }).addTo(donorRegistrationHeatLayer);

            // Add legend
            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Donor Registration</h4>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #08306b;"></div>
                        <span>≥ 65% (Excellent)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #08519c;"></div>
                        <span>55-64% (High)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #2171b5;"></div>
                        <span>45-54% (Above Avg)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #4292c6;"></div>
                        <span>35-44% (Average)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #6baed6;"></div>
                        <span>28-34% (Below Avg)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #9ecae1;"></div>
                        <span>&lt; 28% (Low)</span>
                    </div>
                `;
                return div;
            };
            addLayerLegend('donorRegistration', legend);
        })
        .catch(error => {
            console.error('Error loading donor registration data:', error);
        });
}

// Transplant centers markers with enhanced visualization
function createTransplantCentersLayer() {
    transplantCentersLayer.clearLayers();

    // Try to fetch all ~248 centers from backend API, fall back to hardcoded
    _loadCentersForMap().then(centers => {
        _renderCenterMarkers(centers);
    });
}

async function _loadCentersForMap() {
    // Try backend first for all ~248 centers
    if (window.TransPlanAPI && window.TransPlanAPI.fetchCenters) {
        try {
            const result = await window.TransPlanAPI.fetchCenters({});
            if (result && result.centers && result.centers.length > 10) {
                return result.centers.map(c => ({
                    name: c.name || c.code || '',
                    city: c.city || '',
                    state: c.state_abbr || c.state || '',
                    coord: [c.lat, c.lon],
                    organs: c.organs || [],
                    organCount: c.organs ? c.organs.length : 0
                }));
            }
        } catch (e) { /* fall through */ }
    }

    // Fallback: hardcoded 24 centers
    return [
        { name: "UPMC", city: "Pittsburgh", state: "PA", coord: [40.4406, -79.9959], organCount: 6 },
        { name: "Mayo Clinic", city: "Rochester", state: "MN", coord: [44.0121, -92.4802], organCount: 6 },
        { name: "Cleveland Clinic", city: "Cleveland", state: "OH", coord: [41.4993, -81.6944], organCount: 6 },
        { name: "UCLA Medical Center", city: "Los Angeles", state: "CA", coord: [34.0522, -118.2437], organCount: 6 },
        { name: "Johns Hopkins", city: "Baltimore", state: "MD", coord: [39.2904, -76.6122], organCount: 6 },
        { name: "Duke University Hospital", city: "Durham", state: "NC", coord: [35.9940, -78.8986], organCount: 6 },
        { name: "UCSF Medical Center", city: "San Francisco", state: "CA", coord: [37.7749, -122.4194], organCount: 5 },
        { name: "Vanderbilt", city: "Nashville", state: "TN", coord: [36.1627, -86.7816], organCount: 4 },
        { name: "UW Health", city: "Madison", state: "WI", coord: [43.0731, -89.4012], organCount: 4 },
        { name: "University of Minnesota", city: "Minneapolis", state: "MN", coord: [44.9778, -93.2650], organCount: 4 },
        { name: "Northwestern Medicine", city: "Chicago", state: "IL", coord: [41.8781, -87.6298], organCount: 4 },
        { name: "Stanford Hospital", city: "Palo Alto", state: "CA", coord: [37.4419, -122.1430], organCount: 3 },
        { name: "Texas Heart Institute", city: "Houston", state: "TX", coord: [29.7604, -95.3698], organCount: 4 },
        { name: "Penn Medicine", city: "Philadelphia", state: "PA", coord: [39.9526, -75.1652], organCount: 5 },
        { name: "Baylor University Medical Center", city: "Dallas", state: "TX", coord: [32.7767, -96.7970], organCount: 3 },
        { name: "Nebraska Medicine", city: "Omaha", state: "NE", coord: [41.2565, -95.9345], organCount: 3 },
        { name: "University of Miami", city: "Miami", state: "FL", coord: [25.7617, -80.1918], organCount: 4 },
        { name: "Indiana University Health", city: "Indianapolis", state: "IN", coord: [39.7684, -86.1581], organCount: 3 },
        { name: "Barnes-Jewish Hospital", city: "St. Louis", state: "MO", coord: [38.6270, -90.1994], organCount: 5 },
        { name: "University of Washington", city: "Seattle", state: "WA", coord: [47.6062, -122.3321], organCount: 4 },
        { name: "Emory University Hospital", city: "Atlanta", state: "GA", coord: [33.7490, -84.3880], organCount: 4 },
        { name: "University of Colorado", city: "Denver", state: "CO", coord: [39.7392, -104.9903], organCount: 3 },
        { name: "NYU Langone", city: "New York", state: "NY", coord: [40.7128, -74.0060], organCount: 4 },
        { name: "Mount Sinai", city: "New York", state: "NY", coord: [40.7895, -73.9535], organCount: 3 }
    ];
}

function _renderCenterMarkers(centers) {
    transplantCentersLayer.clearLayers();

    // Use marker clustering if available (handles 248+ points), otherwise plain group
    const useCluster = window.TransPlanCDN && window.TransPlanCDN.leafletMarkerCluster;
    const group = useCluster ? L.markerClusterGroup({
        maxClusterRadius: 40,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        disableClusteringAtZoom: 8
    }) : L.layerGroup();

    centers.forEach(center => {
        if (!center.coord || center.coord[0] == null || center.coord[1] == null) return;

        const orgCount = center.organCount || 0;
        let size, color, borderColor;
        if (orgCount >= 5) {
            size = 14; color = '#e74c3c'; borderColor = '#c0392b';
        } else if (orgCount >= 3) {
            size = 10; color = '#3498db'; borderColor = '#2980b9';
        } else {
            size = 8; color = '#2ecc71'; borderColor = '#27ae60';
        }

        const markerDiv = document.createElement('div');
        markerDiv.style.cssText = 'background:' + color + ';width:' + size + 'px;height:' + size + 'px;border-radius:50%;border:2px solid ' + borderColor + ';box-shadow:0 2px 6px rgba(0,0,0,0.3);';

        const icon = L.divIcon({
            className: 'transplant-center-marker',
            html: markerDiv.outerHTML,
            iconSize: [size + 4, size + 4]
        });

        // Build popup safely using DOM
        const popupDiv = document.createElement('div');
        popupDiv.style.minWidth = '160px';
        const nameEl = document.createElement('strong');
        nameEl.textContent = center.name;
        const locEl = document.createElement('em');
        locEl.textContent = center.city + ', ' + center.state;
        popupDiv.appendChild(nameEl);
        popupDiv.appendChild(document.createElement('br'));
        popupDiv.appendChild(locEl);
        if (center.organs && center.organs.length > 0) {
            popupDiv.appendChild(document.createElement('br'));
            const progLabel = document.createElement('strong');
            progLabel.textContent = 'Programs: ';
            popupDiv.appendChild(progLabel);
            popupDiv.appendChild(document.createTextNode(center.organs.join(', ')));
        }

        L.marker(center.coord, { icon: icon })
            .bindPopup(popupDiv)
            .addTo(group);
    });

    group.addTo(transplantCentersLayer);

    // Update legend using DOM methods
    const legend = L.control({ position: 'topright' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend');
        const title = document.createElement('h4');
        title.textContent = 'Transplant Centers (' + centers.length + ')';
        div.appendChild(title);

        const items = [
            { size: 14, bg: '#e74c3c', border: '#c0392b', text: '5-6 organ programs' },
            { size: 10, bg: '#3498db', border: '#2980b9', text: '3-4 organ programs' },
            { size: 8, bg: '#2ecc71', border: '#27ae60', text: '1-2 organ programs' }
        ];
        items.forEach(item => {
            const row = document.createElement('div');
            row.className = 'legend-item';
            const dot = document.createElement('div');
            dot.style.cssText = 'width:' + item.size + 'px;height:' + item.size + 'px;background:' + item.bg + ';border:2px solid ' + item.border + ';border-radius:50%;';
            const label = document.createElement('span');
            label.textContent = item.text;
            row.appendChild(dot);
            row.appendChild(label);
            div.appendChild(row);
        });
        return div;
    };
    addLayerLegend('transplantCenters', legend);
}

// State policies overlay with color-coded boundaries
function createStatePoliciesLayer() {
    statePoliciesLayer.clearLayers();

    // Fetch US states GeoJSON and apply policies
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            // State policy mapping
            const statePolicyColors = {
                "California": { color: "#2ecc71", policy: "Opt-out donor registry (donor by default)", level: "opt-out" },
                "Oregon": { color: "#2ecc71", policy: "Opt-out donor registry", level: "opt-out" },
                "Washington": { color: "#2ecc71", policy: "Opt-out donor registry", level: "opt-out" },
                "Minnesota": { color: "#27ae60", policy: "Strong opt-in registry with DMV enrollment", level: "strong" },
                "New York": { color: "#27ae60", policy: "Enhanced opt-in at DMV", level: "strong" },
                "Illinois": { color: "#27ae60", policy: "First person consent law", level: "strong" },
                "Wisconsin": { color: "#27ae60", policy: "Strong DMV enrollment", level: "strong" },
                "Texas": { color: "#f39c12", policy: "Traditional opt-in", level: "standard" },
                "Florida": { color: "#f39c12", policy: "Traditional opt-in", level: "standard" },
                "Pennsylvania": { color: "#27ae60", policy: "Enhanced consent mechanisms", level: "strong" },
                "Ohio": { color: "#27ae60", policy: "Strong DMV program", level: "strong" },
                "North Carolina": { color: "#27ae60", policy: "First person consent", level: "strong" },
                "Tennessee": { color: "#f39c12", policy: "Standard opt-in", level: "standard" },
                "Nebraska": { color: "#27ae60", policy: "Strong awareness programs", level: "strong" },
                "Indiana": { color: "#f39c12", policy: "Standard opt-in", level: "standard" },
                "Massachusetts": { color: "#27ae60", policy: "Enhanced opt-in", level: "strong" },
                "Colorado": { color: "#27ae60", policy: "Strong DMV program", level: "strong" },
                "Maryland": { color: "#27ae60", policy: "Enhanced consent", level: "strong" },
                "Georgia": { color: "#f39c12", policy: "Standard opt-in", level: "standard" },
                "Arizona": { color: "#f39c12", policy: "Standard opt-in", level: "standard" }
            };

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const statePolicy = statePolicyColors[stateName];

                    if (statePolicy) {
                        return {
                            fillColor: statePolicy.color,
                            weight: 2,
                            opacity: 0.8,
                            color: statePolicy.color,
                            fillOpacity: 0.3
                        };
                    } else {
                        // Default for states without specific policy data
                        return {
                            fillColor: '#95a5a6',
                            weight: 1,
                            opacity: 0.5,
                            color: '#7f8c8d',
                            fillOpacity: 0.1
                        };
                    }
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const statePolicy = statePolicyColors[stateName];

                    if (statePolicy) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            <em>${statePolicy.policy}</em>
                        `);
                    } else {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            <em>No specific policy data</em>
                        `);
                    }

                    // Hover effects
                    layer.on('mouseover', function() {
                        this.setStyle({
                            fillOpacity: 0.5,
                            weight: 3
                        });
                    });

                    layer.on('mouseout', function() {
                        const statePolicy = statePolicyColors[stateName];
                        this.setStyle({
                            fillOpacity: statePolicy ? 0.3 : 0.1,
                            weight: statePolicy ? 2 : 1
                        });
                    });
                }
            }).addTo(statePoliciesLayer);

            // Add legend
            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Donation Policies</h4>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #2ecc71;"></div>
                        <span>Opt-out registry</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #27ae60;"></div>
                        <span>Strong opt-in</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #f39c12;"></div>
                        <span>Standard opt-in</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #95a5a6;"></div>
                        <span>No data</span>
                    </div>
                `;
                return div;
            };
            addLayerLegend('statePolicies', legend);
        })
        .catch(error => {
            console.error('Error loading state boundaries:', error);
        });
}

// Regional wait time grid overlay
function createWaitTimeGridLayer() {
    waitTimeGridLayer.clearLayers();

    // Fetch US states GeoJSON and group into UNOS regions
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            // UNOS region mapping (11 regions)
            const unosRegions = {
                "Region 1": {
                    states: ["Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Vermont"],
                    waitTime: "2.8 years",
                    color: "#ffc107",
                    name: "New England"
                },
                "Region 2": {
                    states: ["Delaware", "District of Columbia", "Maryland", "New Jersey", "Pennsylvania", "West Virginia"],
                    waitTime: "3.2 years",
                    color: "#ff9800",
                    name: "Mid-Atlantic"
                },
                "Region 3": {
                    states: ["Alabama", "Arkansas", "Georgia", "Louisiana", "Mississippi", "Puerto Rico"],
                    waitTime: "2.6 years",
                    color: "#ffeb3b",
                    name: "Deep South"
                },
                "Region 4": {
                    states: ["Oklahoma", "Texas"],
                    waitTime: "2.4 years",
                    color: "#8bc34a",
                    name: "Texas/Oklahoma"
                },
                "Region 5": {
                    states: ["Arizona", "California", "Nevada", "New Mexico", "Utah"],
                    waitTime: "3.8 years",
                    color: "#f44336",
                    name: "Southwest"
                },
                "Region 6": {
                    states: ["Alaska", "Hawaii", "Idaho", "Montana", "Oregon", "Washington"],
                    waitTime: "2.2 years",
                    color: "#4caf50",
                    name: "Pacific Northwest"
                },
                "Region 7": {
                    states: ["Illinois", "Minnesota", "North Dakota", "South Dakota", "Wisconsin"],
                    waitTime: "2.1 years",
                    color: "#4caf50",
                    name: "Upper Midwest"
                },
                "Region 8": {
                    states: ["Colorado", "Iowa", "Kansas", "Missouri", "Nebraska", "Wyoming"],
                    waitTime: "2.5 years",
                    color: "#8bc34a",
                    name: "Central Plains"
                },
                "Region 9": {
                    states: ["New York", "Vermont"],
                    waitTime: "3.4 years",
                    color: "#ff9800",
                    name: "New York"
                },
                "Region 10": {
                    states: ["Indiana", "Michigan", "Ohio"],
                    waitTime: "2.7 years",
                    color: "#ffeb3b",
                    name: "Great Lakes"
                },
                "Region 11": {
                    states: ["Kentucky", "North Carolina", "South Carolina", "Tennessee", "Virginia"],
                    waitTime: "2.9 years",
                    color: "#ffc107",
                    name: "Southeast"
                }
            };

            // Create a mapping of state to region
            const stateToRegion = {};
            Object.entries(unosRegions).forEach(([regionKey, regionData]) => {
                regionData.states.forEach(state => {
                    stateToRegion[state] = { key: regionKey, data: regionData };
                });
            });

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const region = stateToRegion[stateName];

                    if (region) {
                        return {
                            fillColor: region.data.color,
                            weight: 2,
                            opacity: 0.6,
                            color: '#333',
                            fillOpacity: 0.25
                        };
                    } else {
                        return {
                            fillColor: '#cccccc',
                            weight: 1,
                            opacity: 0.3,
                            color: '#999',
                            fillOpacity: 0.1
                        };
                    }
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const region = stateToRegion[stateName];

                    if (region) {
                        layer.bindPopup(`
                            <strong>${region.key}: ${region.data.name}</strong><br>
                            State: ${stateName}<br>
                            Avg Wait Time (Kidney): <strong>${region.data.waitTime}</strong>
                        `);
                    }

                    // Hover effects
                    layer.on('mouseover', function() {
                        this.setStyle({
                            fillOpacity: 0.5,
                            weight: 3
                        });
                    });

                    layer.on('mouseout', function() {
                        this.setStyle({
                            fillOpacity: 0.25,
                            weight: 2
                        });
                    });
                }
            }).addTo(waitTimeGridLayer);

            // Add legend
            const legend = L.control({ position: 'bottomleft' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>UNOS Wait Times</h4>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #4caf50;"></div>
                        <span>&lt; 2.3 years (Best)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #8bc34a;"></div>
                        <span>2.3 - 2.7 years</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #ffc107;"></div>
                        <span>2.7 - 3.0 years</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #ff9800;"></div>
                        <span>3.0 - 3.5 years</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #f44336;"></div>
                        <span>&gt; 3.5 years (Worst)</span>
                    </div>
                `;
                return div;
            };
            addLayerLegend('waitTimeGrid', legend);
        })
        .catch(error => {
            console.error('Error loading UNOS regions:', error);
        });
}

// Diabetes prevalence heatmap layer
function createDiabetesLayer() {
    diabetesLayer.clearLayers();

    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            const diabetesRates = {
                "West Virginia": 13.8, "Mississippi": 13.6, "Alabama": 13.5, "Arkansas": 12.9,
                "Louisiana": 12.8, "Tennessee": 12.7, "Kentucky": 12.6, "South Carolina": 12.4,
                "Oklahoma": 12.2, "Georgia": 11.9, "Texas": 11.7, "North Carolina": 11.5,
                "Florida": 11.3, "Indiana": 11.2, "Ohio": 10.9, "Missouri": 10.8,
                "Michigan": 10.7, "Kansas": 10.3, "Arizona": 10.2, "Nevada": 10.1,
                "Pennsylvania": 10.0, "Illinois": 9.8, "New York": 9.6, "Wisconsin": 9.2,
                "Iowa": 9.1, "California": 9.0, "Oregon": 8.9, "Washington": 8.7,
                "Minnesota": 8.3, "Colorado": 7.9, "Massachusetts": 7.8, "Vermont": 7.5
            };

            function getColorForDiabetes(rate) {
                if (rate >= 13) return '#a50f15';
                if (rate >= 12) return '#de2d26';
                if (rate >= 11) return '#fb6a4a';
                if (rate >= 10) return '#fc9272';
                if (rate >= 9) return '#fcbba1';
                return '#fee5d9';
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const rate = diabetesRates[stateName];
                    if (rate) {
                        return {
                            fillColor: getColorForDiabetes(rate),
                            weight: 2,
                            opacity: 0.7,
                            color: '#fff',
                            fillOpacity: 0.6
                        };
                    }
                    return { fillColor: '#f0f0f0', weight: 1, opacity: 0.3, fillOpacity: 0.2 };
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const rate = diabetesRates[stateName];
                    if (rate) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Diabetes Prevalence: <strong style="color: #a50f15">${rate}%</strong><br>
                            <em>High rates reduce donor kidney quality</em>
                        `);
                    }
                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.8, weight: 3 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.6, weight: 2 }));
                }
            }).addTo(diabetesLayer);

            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Diabetes Prevalence</h4>
                    <div class="legend-item"><div class="legend-color" style="background: #a50f15;"></div><span>≥ 13% (Highest)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #de2d26;"></div><span>12-13%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fb6a4a;"></div><span>11-12%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fc9272;"></div><span>10-11%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fcbba1;"></div><span>9-10%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fee5d9;"></div><span>&lt; 9% (Lowest)</span></div>
                `;
                return div;
            };
            addLayerLegend('diabetes', legend);
        });
}

// Obesity rates layer
function createObesityLayer() {
    obesityLayer.clearLayers();

    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            const obesityRates = {
                "West Virginia": 39.1, "Mississippi": 38.8, "Arkansas": 37.4, "Kentucky": 36.5,
                "Tennessee": 36.2, "Alabama": 36.0, "Louisiana": 35.9, "Oklahoma": 35.4,
                "Indiana": 34.8, "South Carolina": 34.4, "Kansas": 34.2, "Missouri": 34.0,
                "Ohio": 33.8, "Michigan": 33.3, "Georgia": 33.0, "North Carolina": 32.8,
                "Texas": 32.4, "Iowa": 32.1, "Illinois": 31.9, "Nebraska": 31.6,
                "Pennsylvania": 31.4, "Wisconsin": 31.2, "Florida": 30.8, "Arizona": 30.4,
                "New York": 30.0, "California": 29.5, "Washington": 29.2, "Oregon": 29.1,
                "Minnesota": 28.6, "Massachusetts": 27.8, "Vermont": 27.3, "Colorado": 24.2
            };

            function getColorForObesity(rate) {
                if (rate >= 37) return '#7a0177';
                if (rate >= 34) return '#c51b8a';
                if (rate >= 31) return '#f768a1';
                if (rate >= 29) return '#fa9fb5';
                return '#fcc5c0';
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const rate = obesityRates[stateName];
                    if (rate) {
                        return {
                            fillColor: getColorForObesity(rate),
                            weight: 2,
                            opacity: 0.7,
                            color: '#fff',
                            fillOpacity: 0.6
                        };
                    }
                    return { fillColor: '#f0f0f0', weight: 1, opacity: 0.3, fillOpacity: 0.2 };
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const rate = obesityRates[stateName];
                    if (rate) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Obesity Rate: <strong style="color: #7a0177">${rate}%</strong><br>
                            <em>Affects donor organ quality and surgical outcomes</em>
                        `);
                    }
                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.8, weight: 3 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.6, weight: 2 }));
                }
            }).addTo(obesityLayer);

            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Obesity Rates</h4>
                    <div class="legend-item"><div class="legend-color" style="background: #7a0177;"></div><span>≥ 37% (Highest)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #c51b8a;"></div><span>34-37%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #f768a1;"></div><span>31-34%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fa9fb5;"></div><span>29-31%</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fcc5c0;"></div><span>&lt; 29% (Lowest)</span></div>
                `;
                return div;
            };
            addLayerLegend('obesity', legend);
        });
}

// Cost of living layer
function createCostOfLivingLayer() {
    costOfLivingLayer.clearLayers();

    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            const costIndices = {
                "Hawaii": 193, "California": 151, "New York": 139, "Massachusetts": 131,
                "Alaska": 128, "Maryland": 129, "Washington": 118, "New Jersey": 120,
                "Oregon": 115, "Connecticut": 116, "Colorado": 105, "Rhode Island": 110,
                "Vermont": 108, "New Hampshire": 109, "Illinois": 100, "Virginia": 103,
                "Pennsylvania": 99, "Florida": 99, "Arizona": 98, "Minnesota": 96,
                "Georgia": 91, "Texas": 91, "Nevada": 104, "North Carolina": 94,
                "Utah": 97, "Wisconsin": 96, "Michigan": 89, "Ohio": 88,
                "Indiana": 89, "Tennessee": 89, "Missouri": 88, "South Carolina": 92,
                "Louisiana": 91, "Alabama": 88, "Kentucky": 87, "Oklahoma": 86,
                "Kansas": 87, "Iowa": 88, "Arkansas": 85, "Mississippi": 84,
                "West Virginia": 84, "Nebraska": 89, "South Dakota": 93, "North Dakota": 96
            };

            function getColorForCOL(index) {
                if (index >= 140) return '#8c2d04';
                if (index >= 120) return '#d94801';
                if (index >= 100) return '#f16913';
                if (index >= 90) return '#fdae6b';
                return '#feedde';
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const index = costIndices[stateName];
                    if (index) {
                        return {
                            fillColor: getColorForCOL(index),
                            weight: 2,
                            opacity: 0.7,
                            color: '#fff',
                            fillOpacity: 0.6
                        };
                    }
                    return { fillColor: '#f0f0f0', weight: 1, opacity: 0.3, fillOpacity: 0.2 };
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const index = costIndices[stateName];
                    if (index) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Cost of Living Index: <strong style="color: #8c2d04">${index}</strong><br>
                            <em>(100 = US average)</em><br>
                            Lower costs aid relocation and post-transplant care
                        `);
                    }
                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.8, weight: 3 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.6, weight: 2 }));
                }
            }).addTo(costOfLivingLayer);

            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Cost of Living</h4>
                    <div class="legend-item"><div class="legend-color" style="background: #8c2d04;"></div><span>≥ 140 (Very High)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #d94801;"></div><span>120-139 (High)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #f16913;"></div><span>100-119 (Above Avg)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #fdae6b;"></div><span>90-99 (Below Avg)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #feedde;"></div><span>&lt; 90 (Low)</span></div>
                `;
                return div;
            };
            addLayerLegend('costOfLiving', legend);
        });
}

// Air quality layer
function createAirQualityLayer() {
    airQualityLayer.clearLayers();

    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            const airQualityScores = {
                "Hawaii": 95, "Vermont": 93, "New Hampshire": 92, "Maine": 91, "Alaska": 90,
                "Wyoming": 89, "Montana": 88, "South Dakota": 87, "North Dakota": 86, "Iowa": 85,
                "Minnesota": 84, "Wisconsin": 83, "Nebraska": 82, "Oregon": 80, "Washington": 79,
                "Idaho": 78, "Colorado": 77, "New Mexico": 76, "Kansas": 75, "Oklahoma": 74,
                "Missouri": 72, "Arkansas": 71, "Massachusetts": 70, "Rhode Island": 69, "Connecticut": 68,
                "Virginia": 67, "North Carolina": 66, "Tennessee": 65, "Kentucky": 64, "Michigan": 63,
                "Illinois": 61, "Indiana": 60, "Ohio": 59, "Pennsylvania": 58, "New York": 57,
                "Maryland": 56, "Delaware": 55, "New Jersey": 54, "Texas": 53, "Louisiana": 52,
                "Georgia": 51, "Alabama": 50, "Arizona": 48, "Nevada": 47, "California": 45
            };

            function getColorForAir(score) {
                if (score >= 85) return '#006d2c';
                if (score >= 75) return '#31a354';
                if (score >= 65) return '#74c476';
                if (score >= 55) return '#bae4b3';
                return '#edf8e9';
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const score = airQualityScores[stateName];
                    if (score) {
                        return {
                            fillColor: getColorForAir(score),
                            weight: 2,
                            opacity: 0.7,
                            color: '#fff',
                            fillOpacity: 0.6
                        };
                    }
                    return { fillColor: '#f0f0f0', weight: 1, opacity: 0.3, fillOpacity: 0.2 };
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const score = airQualityScores[stateName];
                    if (score) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Air Quality Score: <strong style="color: #006d2c">${score}/100</strong><br>
                            <em>Critical for lung recipients and post-transplant recovery</em>
                        `);
                    }
                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.8, weight: 3 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.6, weight: 2 }));
                }
            }).addTo(airQualityLayer);

            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Air Quality</h4>
                    <div class="legend-item"><div class="legend-color" style="background: #006d2c;"></div><span>≥ 85 (Excellent)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #31a354;"></div><span>75-84 (Good)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #74c476;"></div><span>65-74 (Moderate)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #bae4b3;"></div><span>55-64 (Fair)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #edf8e9;"></div><span>&lt; 55 (Poor)</span></div>
                `;
                return div;
            };
            addLayerLegend('airQuality', legend);
        });
}

// Insurance coverage layer
function createInsuranceCoverageLayer() {
    insuranceCoverageLayer.clearLayers();

    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
        .then(response => response.json())
        .then(data => {
            const insuranceRates = {
                "Massachusetts": 97.5, "Hawaii": 96.3, "Vermont": 95.9, "Rhode Island": 95.1,
                "Connecticut": 94.8, "Minnesota": 94.3, "Iowa": 93.7, "Wisconsin": 93.4,
                "New York": 93.1, "New Hampshire": 92.8, "Pennsylvania": 92.5, "Ohio": 92.0,
                "Michigan": 91.8, "Maryland": 91.5, "Washington": 91.2, "Delaware": 91.0,
                "New Jersey": 90.7, "California": 90.4, "Oregon": 90.1, "Illinois": 89.8,
                "Colorado": 89.5, "Virginia": 89.2, "Kentucky": 89.0, "Indiana": 88.5,
                "North Dakota": 88.2, "South Dakota": 88.0, "Missouri": 87.5, "Tennessee": 87.2,
                "Nebraska": 87.0, "Kansas": 86.8, "North Carolina": 86.5, "Georgia": 85.8,
                "Arizona": 85.5, "Louisiana": 85.2, "Alabama": 85.0, "Florida": 84.5,
                "South Carolina": 84.2, "Nevada": 84.0, "Mississippi": 83.5, "Oklahoma": 83.2,
                "Texas": 82.5, "Alaska": 82.0
            };

            function getColorForInsurance(rate) {
                if (rate >= 95) return '#084594';
                if (rate >= 90) return '#2171b5';
                if (rate >= 85) return '#4292c6';
                if (rate >= 82) return '#6baed6';
                return '#9ecae1';
            }

            L.geoJSON(data, {
                style: function(feature) {
                    const stateName = feature.properties.name;
                    const rate = insuranceRates[stateName];
                    if (rate) {
                        return {
                            fillColor: getColorForInsurance(rate),
                            weight: 2,
                            opacity: 0.7,
                            color: '#fff',
                            fillOpacity: 0.6
                        };
                    }
                    return { fillColor: '#f0f0f0', weight: 1, opacity: 0.3, fillOpacity: 0.2 };
                },
                onEachFeature: function(feature, layer) {
                    const stateName = feature.properties.name;
                    const rate = insuranceRates[stateName];
                    if (rate) {
                        layer.bindPopup(`
                            <strong>${stateName}</strong><br>
                            Insurance Coverage: <strong style="color: #084594">${rate}%</strong><br>
                            <em>Population with health insurance</em><br>
                            Higher coverage = better post-transplant support
                        `);
                    }
                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.8, weight: 3 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.6, weight: 2 }));
                }
            }).addTo(insuranceCoverageLayer);

            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function() {
                const div = L.DomUtil.create('div', 'map-legend');
                div.innerHTML = `
                    <h4>Insurance Coverage</h4>
                    <div class="legend-item"><div class="legend-color" style="background: #084594;"></div><span>≥ 95% (Excellent)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #2171b5;"></div><span>90-94% (Very Good)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #4292c6;"></div><span>85-89% (Good)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #6baed6;"></div><span>82-84% (Fair)</span></div>
                    <div class="legend-item"><div class="legend-color" style="background: #9ecae1;"></div><span>&lt; 82% (Low)</span></div>
                `;
                return div;
            };
            addLayerLegend('insurance', legend);
        });
}

// Legend management — prevents duplicate legends when toggling layers
const layerLegends = {};
function addLayerLegend(layerName, legend) {
    if (layerLegends[layerName]) {
        map.removeControl(layerLegends[layerName]);
    }
    layerLegends[layerName] = legend;
    legend.addTo(map);
}
function removeLayerLegend(layerName) {
    if (layerLegends[layerName]) {
        map.removeControl(layerLegends[layerName]);
        // Keep reference in registry so it can be restored on toggle-on
    }
}
function showLayerLegend(layerName) {
    if (layerLegends[layerName]) {
        layerLegends[layerName].addTo(map);
    }
}

// Setup layer toggle controls
function setupLayerControls() {
    document.getElementById('trafficAccidentsLayer').addEventListener('change', function() {
        if (this.checked) {
            trafficHeatLayer.addTo(map);
            showLayerLegend('traffic');
        } else {
            map.removeLayer(trafficHeatLayer);
            removeLayerLegend('traffic');
        }
    });

    document.getElementById('donorRegistrationLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!donorRegistrationHeatLayer.getLayers().length) {
                createDonorRegistrationHeatmap();
            } else {
                showLayerLegend('donorRegistration');
            }
            donorRegistrationHeatLayer.addTo(map);
        } else {
            map.removeLayer(donorRegistrationHeatLayer);
            removeLayerLegend('donorRegistration');
        }
    });

    document.getElementById('transplantCentersLayer').addEventListener('change', function() {
        if (this.checked) {
            transplantCentersLayer.addTo(map);
            showLayerLegend('transplantCenters');
        } else {
            map.removeLayer(transplantCentersLayer);
            removeLayerLegend('transplantCenters');
        }
    });

    document.getElementById('statePoliciesLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!statePoliciesLayer.getLayers().length) {
                createStatePoliciesLayer();
            } else {
                showLayerLegend('statePolicies');
            }
            statePoliciesLayer.addTo(map);
        } else {
            map.removeLayer(statePoliciesLayer);
            removeLayerLegend('statePolicies');
        }
    });

    document.getElementById('waitTimeGridLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!waitTimeGridLayer.getLayers().length) {
                createWaitTimeGridLayer();
            } else {
                showLayerLegend('waitTimeGrid');
            }
            waitTimeGridLayer.addTo(map);
        } else {
            map.removeLayer(waitTimeGridLayer);
            removeLayerLegend('waitTimeGrid');
        }
    });

    document.getElementById('diabetesLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!diabetesLayer.getLayers().length) {
                createDiabetesLayer();
            } else {
                showLayerLegend('diabetes');
            }
            diabetesLayer.addTo(map);
        } else {
            map.removeLayer(diabetesLayer);
            removeLayerLegend('diabetes');
        }
    });

    document.getElementById('obesityLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!obesityLayer.getLayers().length) {
                createObesityLayer();
            } else {
                showLayerLegend('obesity');
            }
            obesityLayer.addTo(map);
        } else {
            map.removeLayer(obesityLayer);
            removeLayerLegend('obesity');
        }
    });

    document.getElementById('costOfLivingLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!costOfLivingLayer.getLayers().length) {
                createCostOfLivingLayer();
            } else {
                showLayerLegend('costOfLiving');
            }
            costOfLivingLayer.addTo(map);
        } else {
            map.removeLayer(costOfLivingLayer);
            removeLayerLegend('costOfLiving');
        }
    });

    document.getElementById('airQualityLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!airQualityLayer.getLayers().length) {
                createAirQualityLayer();
            } else {
                showLayerLegend('airQuality');
            }
            airQualityLayer.addTo(map);
        } else {
            map.removeLayer(airQualityLayer);
            removeLayerLegend('airQuality');
        }
    });

    document.getElementById('insuranceCoverageLayer').addEventListener('change', function() {
        if (this.checked) {
            if (!insuranceCoverageLayer.getLayers().length) {
                createInsuranceCoverageLayer();
            } else {
                showLayerLegend('insurance');
            }
            insuranceCoverageLayer.addTo(map);
        } else {
            map.removeLayer(insuranceCoverageLayer);
            removeLayerLegend('insurance');
        }
    });

    // Add default layers
    trafficHeatLayer.addTo(map);
    transplantCentersLayer.addTo(map);
}

// Phase 6B: Spatial heatmap overlay (fetches grid from backend)
function setupSpatialHeatmapControls() {
    var checkbox = document.getElementById('spatialHeatmapLayer');
    var select = document.getElementById('spatialHeatmapSelect');
    if (!checkbox || !select) return;

    checkbox.addEventListener('change', function() {
        select.disabled = !this.checked;
        if (this.checked) {
            loadSpatialHeatmap(select.value);
        } else {
            spatialHeatmapLayer.clearLayers();
            map.removeLayer(spatialHeatmapLayer);
        }
    });

    select.addEventListener('change', function() {
        if (checkbox.checked) {
            loadSpatialHeatmap(this.value);
        }
    });
}

async function loadSpatialHeatmap(layerName) {
    if (!window.TransPlanCDN || !window.TransPlanCDN.leafletHeat) return;

    spatialHeatmapLayer.clearLayers();

    var base = window.TransPlanBackend || '';
    try {
        var url = base + '/spatial-grid?layer=' + encodeURIComponent(layerName) + '&resolution=35';
        var response = await fetch(url, { signal: AbortSignal.timeout(10000) });
        if (!response.ok) return;
        var data = await response.json();
        if (!data.points || data.points.length === 0) return;

        var heat = L.heatLayer(data.points, {
            radius: 25,
            blur: 20,
            maxZoom: 10,
            max: 1.0,
            gradient: { 0.0: '#313695', 0.25: '#4575b4', 0.5: '#fee090', 0.75: '#f46d43', 1.0: '#a50026' }
        });
        heat.addTo(spatialHeatmapLayer);
        spatialHeatmapLayer.addTo(map);
    } catch (e) {
        console.warn('Spatial heatmap unavailable:', e.message);
    }
}

// Update map with ranked cities
function updateMapWithResults(cities, homeCenterCity) {
    cityMarkersLayer.clearLayers();

    cities.forEach((city, index) => {
        const rank = index + 1;
        // Use coordinates from result data (248-center scoring), fall back to hardcoded (#145)
        const coord = (city.lat && city.lon) ? [city.lat, city.lon]
            : cityCoordinates[city.city] || null;
        const isHome = homeCenterCity && city.city === homeCenterCity;

        if (coord) {
            const colors = ['#ffd700', '#c0c0c0', '#cd7f32', '#667eea', '#9b59b6'];
            const color = isHome ? '#1D9E5C' : colors[Math.min(rank - 1, 4)];
            const size = isHome ? 38 : 32;
            const label = isHome ? 'H' : rank;
            const border = isHome ? '3px solid #115C38' : '3px solid white';

            const icon = L.divIcon({
                className: 'city-rank-marker',
                html: `<div style="
                    background: ${color};
                    color: white;
                    width: ${size}px;
                    height: ${size}px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: ${isHome ? '16px' : '14px'};
                    border: ${border};
                    box-shadow: 0 3px 10px rgba(0,0,0,0.4);
                ">${label}</div>`,
                iconSize: [size + 6, size + 6]
            });

            const popupPrefix = isHome ? '<strong>Reference Center</strong><br>' : '';
            L.marker(coord, { icon: icon, zIndexOffset: isHome ? 1000 : 0 })
                .bindPopup(`
                    ${popupPrefix}
                    <strong>#${rank} ${city.city}</strong><br>
                    ${city.state}<br>
                    Location Score: <strong>${city.personalizedScore.toFixed(1)}</strong><br>
                    Wait Time: ${city.waitTime}
                `)
                .addTo(cityMarkersLayer);
        }
    });
}

// Blood type compatibility affects matching rates
const bloodTypeMultipliers = {
    'O-': 0.85,  // Universal donor, but can only receive O-
    'O+': 0.92,
    'A-': 0.95,
    'A+': 1.02,
    'B-': 0.88,
    'B+': 0.96,
    'AB-': 0.98,
    'AB+': 1.08   // Universal recipient
};

// Age affects prioritization and outcomes
function getAgeMultiplier(age) {
    if (age < 18) return 1.15;  // Pediatric priority
    if (age < 50) return 1.05;
    if (age < 65) return 1.0;
    if (age < 75) return 0.92;
    return 0.85;
}

// Sex can affect organ size matching
const sexMultipliers = {
    'male': 1.0,
    'female': 0.98
};

// Medical urgency dramatically affects wait time
const urgencyMultipliers = {
    '1': 1.5,   // Critical
    '2': 1.2,   // High
    '3': 1.0,   // Active
    '4': 0.7    // Inactive
};

// City-to-state mapping for dynamic scoring across all 22 cities
const cityStateMap = {
    "Pittsburgh": "Pennsylvania", "Baltimore": "Maryland", "Philadelphia": "Pennsylvania",
    "New York": "New York", "Minneapolis": "Minnesota", "Madison": "Wisconsin",
    "Chicago": "Illinois", "Cleveland": "Ohio", "St. Louis": "Missouri",
    "Indianapolis": "Indiana", "Omaha": "Nebraska", "Rochester": "Minnesota",
    "Nashville": "Tennessee", "Durham": "North Carolina", "Miami": "Florida",
    "Dallas": "Texas", "Houston": "Texas", "Portland": "Oregon",
    "Seattle": "Washington", "San Francisco": "California", "Los Angeles": "California",
    "Palo Alto": "California"
};

// State abbreviations for Home Center dropdown display
const stateAbbreviations = {
    "Pennsylvania": "PA", "Maryland": "MD", "New York": "NY",
    "Minnesota": "MN", "Wisconsin": "WI", "Illinois": "IL",
    "Ohio": "OH", "Missouri": "MO", "Indiana": "IN",
    "Nebraska": "NE", "Tennessee": "TN", "North Carolina": "NC",
    "Florida": "FL", "Texas": "TX", "Oregon": "OR",
    "Washington": "WA", "California": "CA"
};

// Populate Home Center dropdown — tries API first, falls back to hardcoded cityStateMap
(async function populateHomeCenterDropdown() {
    const select = document.getElementById('homeCenter');
    if (!select) return;

    function populate(entries) {
        entries
            .sort((a, b) => (a.name || a.city || '').localeCompare(b.name || b.city || ''))
            .forEach((entry) => {
                const option = document.createElement('option');
                const name = entry.name || entry.city || '';
                const state = entry.state_abbr || stateAbbreviations[entry.state] || entry.state || '';
                const code = entry.code || '';
                option.value = code || name;
                option.textContent = name + (state ? ', ' + state : '') + (code ? ' (' + code + ')' : '');
                select.appendChild(option);
            });
    }

    // Try dynamic loading from backend API — fetch ALL centers (#148, #203)
    if (window.TransPlanAPI && window.TransPlanAPI.fetchCenters) {
        try {
            const data = await window.TransPlanAPI.fetchCenters({});
            if (data && data.cities && data.cities.length > 0) {
                populate(data.cities);
                return;
            }
        } catch (e) { /* fall through */ }
    }

    // Fallback: use hardcoded cityStateMap
    populate(
        Object.entries(cityStateMap).map(([city, state]) => ({ city, state }))
    );
})();

document.getElementById('transplantForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Prevent concurrent submissions (#66)
    if (_isSubmitting) return;
    _isSubmitting = true;
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {

    const formData = {
        organ: document.getElementById('organ').value,
        bloodType: document.getElementById('bloodType').value,
        age: parseInt(document.getElementById('age').value),
        sex: document.getElementById('sex').value,
        urgency: document.getElementById('urgency').value,
        weight: document.getElementById('weight').value,
        height: document.getElementById('height').value,
        insurance: document.getElementById('insurance').value,
        cpra: parseInt(document.getElementById('cpra')?.value) || 0,
        meld: parseInt(document.getElementById('meld')?.value) || 0,
        las: parseFloat(document.getElementById('las')?.value) || 0,
        homeCenter: document.getElementById('homeCenter')?.value || '',
        patientLocation: document.getElementById('patientLocation')?.value || '',
        adjustForCauseOfDeath: document.getElementById('adjustCauseOfDeath')?.checked || false,
        useCopula: document.getElementById('useCopula')?.checked || false,
        inferenceMode: document.getElementById('inferenceMode')?.value || 'monte_carlo',
        weights: window.TransPlanWeights?.getWeights() || null
    };

    // Show loading spinner
    const spinner = document.getElementById('simulationSpinner');
    if (spinner) spinner.style.display = 'flex';

    // Load data before calculating
    if (typeof loadAllData === 'function' && !window.TransPlanData?._loaded) {
        await loadAllData();
    }

    // Phase 6A: Geocode patient location if provided
    if (formData.patientLocation) {
        var geo = await _geocodeLocation(formData.patientLocation);
        if (geo) {
            formData.patientLat = geo.lat;
            formData.patientLon = geo.lon;
            var helpEl = document.getElementById('patientLocationHelp');
            if (helpEl) helpEl.textContent = 'Location found: ' + geo.display;
        }
    }

    // Phase 1: Calculate deterministic scores (tries backend API, falls back to local)
    _paginationPage = 0; // Reset pagination on new submission
    await calculateResults(formData);

    // Phase 2: Call backend for simulation (Monte Carlo or Bayesian)
    var advancedParams = typeof _getAdvancedParams === 'function' ? _getAdvancedParams() : {};
    let simResult = null;
    let equityResult = null;
    if (window.TransPlanAPI) {
        simResult = await window.TransPlanAPI.simulate(formData, formData.inferenceMode, advancedParams);
        // M4: Run equity analysis in parallel with the spinner still visible
        if (simResult) {
            equityResult = await window.TransPlanAPI.equityAnalysis(
                formData,
                advancedParams.equity_iterations || undefined
            );
        }
    }

    // Hide spinner
    if (spinner) spinner.style.display = 'none';

    // Render probability view (or show unavailable notice)
    renderProbabilityView(simResult, formData);

    // M4: Render equity view
    renderEquityView(equityResult);

    // Set up tab toggle state
    initResultsTabs(simResult !== null, equityResult !== null);

    } finally {
        _isSubmitting = false;
        if (submitBtn) submitBtn.disabled = false;
    }
});

// --- Organ-specific conditional field visibility ---
document.getElementById('organ').addEventListener('change', function() {
    const selectedOrgan = this.value;
    document.querySelectorAll('.conditional-field').forEach(field => {
        const targetOrgan = field.getAttribute('data-organ');
        field.style.display = (targetOrgan === selectedOrgan) ? '' : 'none';
    });
    // Reset hidden field values when switching organs
    if (selectedOrgan !== 'kidney') document.getElementById('cpra').value = 0;
    if (selectedOrgan !== 'liver') document.getElementById('meld').value = '';
    if (selectedOrgan !== 'lung') document.getElementById('las').value = '';
    // Update cPRA output display
    document.getElementById('cpra-output').textContent = document.getElementById('cpra').value + '%';
});

// Live update for cPRA slider output
document.getElementById('cpra').addEventListener('input', function() {
    document.getElementById('cpra-output').textContent = this.value + '%';
});

// Derive display metrics from algorithm data instead of relying on mock entries
function deriveDisplayMetrics(cityName, stateName, organType, formData, breakdown) {
    const urgency = typeof formData === 'object' ? formData.urgency : formData;

    // --- Wait Time — uses shared constants from algorithm.js (#72, #73) ---
    const cityWaitTimeFactors = (window.TransPlanData && window.TransPlanData.cityWaitTimeFactors) || {};
    const cityFactors = cityWaitTimeFactors[cityName] || {};
    const base = BASE_WAIT_TIMES[organType] || BASE_WAIT_TIMES.kidney;
    const avgWait = (base.min + base.max) / 2;
    const cityFactor = cityFactors[organType] || 1.0;
    const cityWait = avgWait * cityFactor;

    const waitMultiplier = calculateWaitTimeMultiplier(organType, formData);

    const waitYears = Math.round(cityWait * waitMultiplier * 10) / 10;
    const waitMonths = Math.round(waitYears * 12);
    const waitTime = waitYears < 1
        ? `${Math.max(1, waitMonths)} ${waitMonths === 1 ? 'month' : 'months'}`
        : `${waitYears} ${waitYears === 1 ? 'year' : 'years'}`;

    // --- Donor Rate (from donor availability score) ---
    const donorScore = breakdown?.donorAvailability || 50;
    const donorRate = donorScore >= 80 ? 'Very High' :
                      donorScore >= 65 ? 'High' :
                      donorScore >= 50 ? 'Moderate' :
                      donorScore >= 35 ? 'Low' : 'Very Low';

    // --- Match Probability (derived from medical compatibility + donor scores) ---
    const medScore = breakdown?.medicalCompatibility || 50;
    const matchPct = Math.round(60 + (medScore + donorScore) / 200 * 35);
    const matchRate = matchPct + '%';

    // --- Center Quality (from hospital quality score) ---
    const hospScore = breakdown?.hospitalQuality || 50;
    const centersQuality = hospScore >= 90 ? 'Excellent' :
                           hospScore >= 75 ? 'Very Good' :
                           hospScore >= 60 ? 'Good' : 'Fair';

    // --- City-specific factors (generated from scoring data) ---
    const factors = generateCityFactors(cityName, stateName, organType, breakdown);

    return { waitTime, donorRate, matchRate, centersQuality, factors };
}

// Generate meaningful per-city factors based on actual scoring data
function generateCityFactors(cityName, stateName, organType, breakdown) {
    const factors = [];

    // Hospital quality factor
    const hospScore = breakdown?.hospitalQuality || 0;
    if (hospScore >= 90) {
        factors.push(`Top-tier transplant center with high annual ${organType} volume`);
    } else if (hospScore >= 75) {
        factors.push(`Well-established ${organType} transplant program`);
    } else {
        factors.push(`Growing ${organType} transplant program`);
    }

    // Wait time factor
    const waitScore = breakdown?.waitTime || 0;
    if (waitScore >= 75) {
        factors.push('Shorter than average wait times in this region');
    } else if (waitScore >= 50) {
        factors.push('Moderate regional wait times');
    } else {
        factors.push('Higher competition may extend wait times');
    }

    // Donor availability factor
    const donorScore = breakdown?.donorAvailability || 0;
    if (donorScore >= 70) {
        factors.push(`Strong donor registration rates in ${stateName}`);
    } else if (donorScore >= 50) {
        factors.push('Moderate regional donor availability');
    } else {
        factors.push('Lower donor registration in this region');
    }

    // Geographic factor
    const geoScore = breakdown?.geographic || 0;
    if (geoScore >= 70) {
        factors.push('Favorable cost of living and recovery climate');
    } else if (geoScore >= 50) {
        factors.push('Moderate cost of living in metro area');
    } else {
        factors.push('Higher cost of living — plan for additional expenses');
    }

    // Health demographics factor
    const healthScore = breakdown?.healthDemographics || 0;
    if (healthScore >= 70) {
        factors.push('Healthy regional population supports quality donor pool');
    } else {
        factors.push('Regional health factors may affect donor pool quality');
    }

    return factors;
}

async function calculateResults(formData) {
    const organ = formData.organ;

    // Try backend scoring API first (248 centers)
    if (window.TransPlanAPI && window.TransPlanAPI.scoreAll) {
        try {
            const result = await window.TransPlanAPI.scoreAll(formData);
            if (result && result.centers && result.centers.length > 0) {
                const cities = result.centers.map(function(c) {
                    return {
                        city: c.name,
                        state: c.state,
                        stateAbbr: c.state_abbr,
                        centerCode: c.code,
                        lat: c.lat,
                        lon: c.lon,
                        score: c.total,
                        personalizedScore: c.total,
                        scoreBreakdown: c.breakdown,
                        waitTime: null,
                        donorRate: null,
                        matchRate: null,
                        centersQuality: null,
                        factors: []
                    };
                });
                displayResults(cities, formData);
                return;
            }
        } catch (err) {
            console.warn('Backend scoring failed, falling back to local scoring:', err.message);
        }
    }

    // Fallback: local scoring for 22 cities
    if (typeof calculateComprehensiveScore === 'function') {
        const cities = Object.entries(cityStateMap).map(([cityName, stateName]) => {
            const result = calculateComprehensiveScore(formData, cityName, stateName, organ, formData.weights);
            const metrics = deriveDisplayMetrics(cityName, stateName, organ, formData, result.breakdown);
            return {
                city: cityName,
                state: stateName,
                score: result.total,
                personalizedScore: result.total,
                scoreBreakdown: result.breakdown,
                waitTime: metrics.waitTime,
                donorRate: metrics.donorRate,
                matchRate: metrics.matchRate,
                centersQuality: metrics.centersQuality,
                factors: metrics.factors
            };
        });

        cities.sort((a, b) => b.personalizedScore - a.personalizedScore);
        displayResults(cities, formData);
    }
}

function displayResults(cities, formData) {
    _currentResults = cities;
    _currentFormData = formData;

    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');

    resultsContainer.innerHTML = '';

    // Reset comparison checkboxes
    _clearCompareSelection();

    // Show urgency warning for Status 1 (critical) patients
    let warningEl = document.getElementById('urgency-warning');
    if (!warningEl) {
        warningEl = document.createElement('div');
        warningEl.id = 'urgency-warning';
        warningEl.className = 'urgency-warning';
        warningEl.setAttribute('role', 'alert');
        resultsSection.insertBefore(warningEl, resultsSection.querySelector('.map-section'));
    }
    if (formData.urgency === '1') {
        warningEl.innerHTML = '<strong>Important:</strong> Status 1 (critical) patients are typically too medically urgent for relocation planning. These results may not be actionable in this situation. Discuss any decisions with the transplant team immediately.';
        warningEl.style.display = 'block';
    } else {
        warningEl.style.display = 'none';
    }

    // Dynamic results intro (#193)
    const introEl = document.querySelector('.results-intro');
    if (introEl) {
        const organNames = { kidney: 'kidney', liver: 'liver', heart: 'heart', lung: 'lung', pancreas: 'pancreas', intestine: 'intestine' };
        const organLabel = organNames[formData.organ] || formData.organ;
        const urgencyLabels = { '1': 'Status 1 (critical)', '2': 'Status 2 (high priority)', '3': 'Status 3 (active)', '4': 'Status 4 (inactive)' };
        const urgencyLabel = urgencyLabels[formData.urgency] || '';
        introEl.textContent = `Results for a ${organLabel} transplant candidate, blood type ${formData.bloodType}, age ${formData.age}, ${urgencyLabel}. Cities ranked by location suitability score based on regional data trends.`;
    }

    // Find home center for comparison (null if not selected)
    const homeCenter = formData.homeCenter
        ? cities.find(c => c.city === formData.homeCenter)
        : null;

    // Initialize map if not already done
    if (!map) {
        resultsSection.style.display = 'block';
        setTimeout(() => {
            initializeMap();
            updateMapWithResults(cities, formData.homeCenter);
        }, 100);
    } else {
        updateMapWithResults(cities, formData.homeCenter);
    }

    // Apply state filter if active
    let filtered = cities;
    if (_paginationFilterState) {
        filtered = cities.filter(c => c.state === _paginationFilterState);
    }

    // Pagination
    const pageSize = _paginationPageSize === 'all' ? filtered.length : parseInt(_paginationPageSize, 10);
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    if (_paginationPage >= totalPages) _paginationPage = totalPages - 1;
    const start = _paginationPage * pageSize;
    const paged = filtered.slice(start, start + pageSize);

    paged.forEach((city, index) => {
        const rank = start + index + 1;
        const card = createCityCard(city, rank, formData, homeCenter);
        resultsContainer.appendChild(card);
    });

    // Update pagination controls
    _updatePaginationControls(filtered.length, totalPages, cities);

    // ── Table view (#204) ────────────────────────────────────────────
    _renderResultsTable(filtered, formData, homeCenter);
    _renderResultsSummary(cities, formData);

    resultsSection.style.display = 'block';
    // Hide empty state when results appear
    var emptyState = document.getElementById('emptyState');
    if (emptyState) emptyState.style.display = 'none';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Render comparison bar chart
    setTimeout(() => {
        if (window.TransPlanCharts) {
            window.TransPlanCharts.createComparisonChart(cities);
        }
    }, 200);
}

function _updatePaginationControls(filteredCount, totalPages, allCities) {
    var controls = document.getElementById('resultsControls');
    if (!controls) return;

    // Show controls if more than 10 results
    controls.style.display = allCities.length > 10 ? 'flex' : 'none';

    // Update page info
    var pageInfo = document.getElementById('resultsPageInfo');
    if (pageInfo) {
        pageInfo.textContent = 'Page ' + (_paginationPage + 1) + '/' + totalPages +
            ' (' + filteredCount + ' results)';
    }

    // Enable/disable buttons
    var prevBtn = document.getElementById('resultsPrev');
    var nextBtn = document.getElementById('resultsNext');
    if (prevBtn) prevBtn.disabled = _paginationPage <= 0;
    if (nextBtn) nextBtn.disabled = _paginationPage >= totalPages - 1;

    // Populate state filter dropdown (once)
    var stateSelect = document.getElementById('resultsFilterState');
    if (stateSelect && stateSelect.options.length <= 1) {
        var states = [];
        allCities.forEach(function(c) {
            if (c.state && states.indexOf(c.state) === -1) states.push(c.state);
        });
        states.sort();
        states.forEach(function(s) {
            var opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            stateSelect.appendChild(opt);
        });
    }
}

// Set up pagination event handlers (called once on DOMContentLoaded)
function _initPaginationHandlers() {
    var prevBtn = document.getElementById('resultsPrev');
    var nextBtn = document.getElementById('resultsNext');
    var pageSizeSelect = document.getElementById('resultsPageSize');
    var stateFilter = document.getElementById('resultsFilterState');

    if (prevBtn) prevBtn.addEventListener('click', function() {
        if (_paginationPage > 0) {
            _paginationPage--;
            if (_currentResults && _currentFormData) displayResults(_currentResults, _currentFormData);
        }
    });
    if (nextBtn) nextBtn.addEventListener('click', function() {
        _paginationPage++;
        if (_currentResults && _currentFormData) displayResults(_currentResults, _currentFormData);
    });
    if (pageSizeSelect) pageSizeSelect.addEventListener('change', function() {
        _paginationPageSize = this.value;
        _paginationPage = 0;
        if (_currentResults && _currentFormData) displayResults(_currentResults, _currentFormData);
    });
    if (stateFilter) stateFilter.addEventListener('change', function() {
        _paginationFilterState = this.value;
        _paginationPage = 0;
        if (_currentResults && _currentFormData) displayResults(_currentResults, _currentFormData);
    });

    // Collapse/expand results cards (#153)
    var collapseBtn = document.getElementById('collapseResultsBtn');
    if (collapseBtn) collapseBtn.addEventListener('click', function() {
        var container = document.getElementById('resultsContainer');
        if (!container) return;
        var collapsed = container.classList.toggle('collapsed');
        collapseBtn.textContent = collapsed ? 'Expand ▼' : 'Collapse ▲';
    });
}

// Phase 6A: Geocode a location string using Nominatim
async function _geocodeLocation(query) {
    try {
        var url = 'https://nominatim.openstreetmap.org/search?q=' +
            encodeURIComponent(query + ', USA') +
            '&format=json&limit=1&countrycodes=us';
        var response = await fetch(url, {
            headers: { 'User-Agent': 'TransPlan/1.0' },
            signal: AbortSignal.timeout(5000)
        });
        var data = await response.json();
        if (data && data.length > 0) {
            return {
                lat: parseFloat(data[0].lat),
                lon: parseFloat(data[0].lon),
                display: data[0].display_name.split(',').slice(0, 2).join(',')
            };
        }
    } catch (e) {
        console.warn('Geocoding failed:', e.message);
    }
    return null;
}

// Haversine distance in miles
function _haversineMiles(lat1, lon1, lat2, lon2) {
    var R = 3959; // Earth radius in miles
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function createCityCard(city, rank, formData, homeCenter) {
    const card = document.createElement('div');
    card.className = `city-card rank-${rank}`;
    const radarId = `radar-chart-${rank}`;

    const isHome = homeCenter && city.city === homeCenter.city;
    if (isHome) card.classList.add('home-center');

    // Build comparison badge HTML (all values derived from internal scoring, not user input)
    let comparisonHtml = '';
    if (isHome) {
        comparisonHtml = '<div class="comparison-badge comparison-home">Reference Center</div>';
    } else if (homeCenter) {
        const delta = city.personalizedScore - homeCenter.personalizedScore;
        const sign = delta >= 0 ? '+' : '';
        const cls = delta >= 0 ? 'comparison-positive' : 'comparison-negative';
        comparisonHtml = `<div class="comparison-badge ${cls}">${sign}${delta.toFixed(1)} pts</div>`;
    }

    const scoreClass = city.personalizedScore >= 90 ? 'good' :
                       city.personalizedScore >= 80 ? 'moderate' : 'poor';

    // Note: innerHTML values are all derived from internal algorithm data (city names,
    // computed scores, static strings), not from user-supplied or external content.
    card.style.cursor = 'pointer';
    card.dataset.city = city.city;

    card.innerHTML = `
        <div class="city-header">
            <div class="city-info">
                <h3>${city.city}</h3>
                <p class="state">${city.state}</p>
            </div>
            <div class="city-header-right">
                <label class="compare-check" onclick="event.stopPropagation()" title="Add to comparison">
                    <input type="checkbox" data-city="${city.city}" data-panel="scores" onchange="updateCompareBar()">
                    Compare
                </label>
                ${comparisonHtml}
                <div class="rank-badge">Rank #${rank}</div>
            </div>
        </div>

        <div class="score">
            <div class="score-label">Location Suitability Score</div>
            <div class="score-value">${city.personalizedScore.toFixed(1)}/100</div>
        </div>

        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Estimated Wait Time</div>
                <div class="metric-value ${getWaitTimeClass(formData.organ, city.waitTime)}">${city.waitTime}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Donor Availability</div>
                <div class="metric-value ${getDonorClass(city.donorRate)}">${city.donorRate}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Compatibility Index</div>
                <div class="metric-value ${getMatchClass(city.matchRate)}">${city.matchRate}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Center Quality</div>
                <div class="metric-value good">${city.centersQuality}</div>
            </div>
            ${formData.patientLat ? (() => {
                const cityCoord = cityCoordinates[city.city];
                if (!cityCoord) return '';
                const dist = Math.round(_haversineMiles(formData.patientLat, formData.patientLon, cityCoord[0], cityCoord[1]));
                const cls = dist < 200 ? 'good' : dist < 500 ? 'moderate' : 'poor';
                return '<div class="metric"><div class="metric-label">Distance</div><div class="metric-value ' + cls + '">' + dist + ' mi</div></div>';
            })() : ''}
        </div>

        ${city.scoreBreakdown ? `
        <div class="radar-chart-container">
            <h4>Score Breakdown</h4>
            ${window.TransPlanCDN && window.TransPlanCDN.chartjs
                ? `<canvas id="${radarId}"></canvas>`
                : `<div class="chart-fallback">${Object.entries(city.scoreBreakdown).map(([k, v]) => k.replace(/([A-Z])/g, ' $1').trim() + ': ' + (typeof v === 'number' ? v.toFixed(0) : v)).join(' / ')}</div>`}
        </div>
        ` : ''}

        <div class="factors">
            <h4>Why This Location?</h4>
            <ul>
                ${city.factors.map(factor => `<li>${factor}</li>`).join('')}
            </ul>
        </div>
    `;

    card.addEventListener('click', function(e) {
        if (e.target.closest('.compare-check')) return;
        openCityDetail(city.city);
    });

    // Render radar chart after card is in DOM (skip if Chart.js unavailable #199)
    if (city.scoreBreakdown && window.TransPlanCDN && window.TransPlanCDN.chartjs) {
        setTimeout(() => {
            if (window.TransPlanCharts) {
                window.TransPlanCharts.createRadarChart(radarId, city.scoreBreakdown, city.city);
            }
        }, 0);
    }

    return card;
}

function getWaitTimeClass(organ, waitTime) {
    // Parse wait time string
    const value = parseFloat(waitTime);

    if (organ === 'kidney' || organ === 'pancreas') {
        return value < 2 ? 'good' : value < 3 ? 'moderate' : 'poor';
    } else if (organ === 'liver') {
        return value < 1.5 ? 'good' : value < 2 ? 'moderate' : 'poor';
    } else if (organ === 'heart' || organ === 'lung') {
        return value < 6 ? 'good' : value < 12 ? 'moderate' : 'poor';
    }
    return 'moderate';
}

function getDonorClass(rate) {
    if (rate === 'Very High') return 'good';
    if (rate === 'High') return 'good';
    if (rate === 'Moderate') return 'moderate';
    return 'poor';
}

function getMatchClass(rate) {
    const value = parseInt(rate);
    return value >= 80 ? 'good' : value >= 70 ? 'moderate' : 'poor';
}

// ── Results Table (#204) ────────────────────────────────────────────────────

/** Current sort state for the results table */
var _tableSortKey = 'rank';
var _tableSortAsc = true;

/**
 * Render the summary card above the table.
 */
function _renderResultsSummary(cities, formData) {
    var el = document.getElementById('resultsSummary');
    if (!el || !cities || cities.length === 0) { if (el) el.style.display = 'none'; return; }

    var top = cities[0];
    var worst = cities[cities.length - 1];
    var range = top.personalizedScore.toFixed(1) + ' \u2013 ' + worst.personalizedScore.toFixed(1);

    // Pick a key differentiator from the top city
    var diff = '';
    if (top.donorRate === 'Very High') diff = 'Very high donor availability';
    else if (parseFloat(top.waitTime) <= 1) diff = 'Very short wait time';
    else if (top.centersQuality === 'Excellent') diff = 'Excellent center quality';
    else diff = top.factors && top.factors[0] ? top.factors[0] : '';

    // Note: all values are derived from internal scoring data, not user input
    el.textContent = '';
    var span1 = document.createElement('span');
    span1.className = 'summary-top-city';
    span1.textContent = '#1 ' + top.city + ', ' + top.state;
    el.appendChild(span1);

    var span2 = document.createElement('span');
    span2.className = 'summary-score';
    span2.textContent = top.personalizedScore.toFixed(1) + '/100';
    el.appendChild(span2);

    if (diff) {
        var span3 = document.createElement('span');
        span3.className = 'summary-detail';
        span3.textContent = diff;
        el.appendChild(span3);
    }

    var span4 = document.createElement('span');
    span4.className = 'summary-detail';
    span4.textContent = 'Score range: ' + range + ' (' + cities.length + ' programs)';
    el.appendChild(span4);

    el.style.display = '';
}

/**
 * Render (or re-render) the results table body.
 * @param {Array} cities - filtered city list
 * @param {Object} formData
 * @param {Object|null} homeCenter
 */
function _renderResultsTable(cities, formData, homeCenter) {
    var tbody = document.getElementById('resultsTableBody');
    if (!tbody) return;
    tbody.textContent = '';

    var hasDistance = !!formData.patientLat;
    var distHeader = document.getElementById('distanceHeader');
    if (distHeader) distHeader.style.display = hasDistance ? '' : 'none';

    // Sort a working copy
    var sorted = cities.slice();
    _sortResultsArray(sorted, _tableSortKey, _tableSortAsc, formData);

    // Update header sort indicators
    _updateSortIndicators();

    sorted.forEach(function(city) {
        var originalRank = cities.indexOf(city) + 1;
        var tr = document.createElement('tr');
        var isHome = homeCenter && city.city === homeCenter.city;
        if (isHome) tr.className = 'home-row';

        var scoreClass = city.personalizedScore >= 90 ? 'good' :
                         city.personalizedScore >= 80 ? 'moderate' : 'poor';

        // Rank cell
        var tdRank = document.createElement('td');
        tdRank.className = 'rank-cell' + (originalRank <= 3 ? ' rank-' + originalRank : '');
        tdRank.textContent = originalRank;
        tr.appendChild(tdRank);

        // City cell
        var tdCity = document.createElement('td');
        tdCity.className = 'city-cell';
        tdCity.textContent = city.city;
        var stateSpan = document.createElement('span');
        stateSpan.className = 'city-state';
        stateSpan.textContent = city.state;
        tdCity.appendChild(stateSpan);
        if (isHome) {
            var refLabel = document.createElement('small');
            refLabel.style.cssText = 'color:var(--color-primary);font-weight:400;margin-left:4px';
            refLabel.textContent = '(ref)';
            tdCity.appendChild(refLabel);
        }
        tr.appendChild(tdCity);

        // Score cell
        var tdScore = document.createElement('td');
        tdScore.className = 'score-cell metric-cell ' + scoreClass;
        tdScore.textContent = city.personalizedScore.toFixed(1);
        tr.appendChild(tdScore);

        // Wait Time cell
        var tdWait = document.createElement('td');
        tdWait.className = 'metric-cell ' + getWaitTimeClass(formData.organ, city.waitTime);
        tdWait.textContent = city.waitTime;
        tr.appendChild(tdWait);

        // Donor Availability cell
        var tdDonor = document.createElement('td');
        tdDonor.className = 'metric-cell ' + getDonorClass(city.donorRate);
        tdDonor.textContent = city.donorRate;
        tr.appendChild(tdDonor);

        // Center Quality cell
        var tdQuality = document.createElement('td');
        tdQuality.className = 'metric-cell';
        tdQuality.textContent = city.centersQuality;
        tr.appendChild(tdQuality);

        // Distance cell (conditional)
        if (hasDistance) {
            var tdDist = document.createElement('td');
            tdDist.className = 'metric-cell';
            var coord = cityCoordinates[city.city];
            if (coord) {
                var dist = Math.round(_haversineMiles(formData.patientLat, formData.patientLon, coord[0], coord[1]));
                var distClass = dist < 200 ? 'good' : dist < 500 ? 'moderate' : 'poor';
                tdDist.className += ' ' + distClass;
                tdDist.textContent = dist + ' mi';
            } else {
                tdDist.textContent = '\u2014';
            }
            tr.appendChild(tdDist);
        }

        // Details button cell
        var tdBtn = document.createElement('td');
        var btn = document.createElement('button');
        btn.className = 'detail-btn';
        btn.dataset.city = city.city;
        btn.textContent = 'Details';
        tdBtn.appendChild(btn);
        tr.appendChild(tdBtn);

        // Row click -> open detail modal
        tr.addEventListener('click', function() {
            openCityDetail(city.city);
        });

        tbody.appendChild(tr);
    });
}

/**
 * Parse a wait time string like "1.8 years" or "4.2 months" into a
 * numeric value in months for correct sorting.
 */
function _parseWaitTimeMonths(str) {
    if (!str) return Infinity;
    var num = parseFloat(str);
    if (isNaN(num)) return Infinity;
    var lower = str.toLowerCase();
    if (lower.indexOf('year') !== -1) return num * 12;
    if (lower.indexOf('week') !== -1) return num / 4.345;
    if (lower.indexOf('day') !== -1) return num / 30.44;
    // Default: assume months
    return num;
}

/**
 * Sort the results array in-place by the given key.
 */
function _sortResultsArray(arr, key, asc, formData) {
    arr.sort(function(a, b) {
        var va, vb;
        switch (key) {
            case 'rank':
            case 'score':
                va = a.personalizedScore; vb = b.personalizedScore;
                // Default sort for rank is descending (highest score = rank 1)
                return key === 'rank'
                    ? (asc ? vb - va : va - vb)
                    : (asc ? va - vb : vb - va);
            case 'city':
                va = a.city.toLowerCase(); vb = b.city.toLowerCase();
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            case 'waitTime':
                va = _parseWaitTimeMonths(a.waitTime);
                vb = _parseWaitTimeMonths(b.waitTime);
                return asc ? va - vb : vb - va;
            case 'donorRate':
                var donorOrder = { 'Very High': 4, 'High': 3, 'Moderate': 2, 'Low': 1 };
                va = donorOrder[a.donorRate] || 0; vb = donorOrder[b.donorRate] || 0;
                return asc ? va - vb : vb - va;
            case 'centersQuality':
                var qualOrder = { 'Excellent': 4, 'Very Good': 3, 'Good': 2, 'Fair': 1 };
                va = qualOrder[a.centersQuality] || 0; vb = qualOrder[b.centersQuality] || 0;
                return asc ? va - vb : vb - va;
            case 'distance':
                if (!formData || !formData.patientLat) return 0;
                var ca = cityCoordinates[a.city], cb = cityCoordinates[b.city];
                va = ca ? _haversineMiles(formData.patientLat, formData.patientLon, ca[0], ca[1]) : 99999;
                vb = cb ? _haversineMiles(formData.patientLat, formData.patientLon, cb[0], cb[1]) : 99999;
                return asc ? va - vb : vb - va;
            default:
                return 0;
        }
    });
}

/**
 * Update sort arrow indicators on table headers.
 */
function _updateSortIndicators() {
    var ths = document.querySelectorAll('.results-table thead th[data-sort]');
    ths.forEach(function(th) {
        var key = th.getAttribute('data-sort');
        var arrow = th.querySelector('.sort-arrow');
        if (!arrow) {
            arrow = document.createElement('span');
            arrow.className = 'sort-arrow';
            th.appendChild(arrow);
        }
        if (key === _tableSortKey) {
            th.classList.add('sort-active');
            arrow.textContent = _tableSortAsc ? ' \u25B2' : ' \u25BC';
        } else {
            th.classList.remove('sort-active');
            arrow.textContent = ' \u25B2';
        }
    });
}

/**
 * Initialize click handlers on table headers for sorting.
 * Called once on DOMContentLoaded.
 */
function _initTableSortHandlers() {
    var table = document.getElementById('resultsTable');
    if (!table) return;
    table.querySelector('thead').addEventListener('click', function(e) {
        var th = e.target.closest('th[data-sort]');
        if (!th) return;
        var key = th.getAttribute('data-sort');
        if (_tableSortKey === key) {
            _tableSortAsc = !_tableSortAsc;
        } else {
            _tableSortKey = key;
            // Default ascending for most, descending for score/rank
            _tableSortAsc = (key === 'score' || key === 'rank') ? true : true;
        }
        // Re-render table with current results
        if (_currentResults && _currentFormData) {
            var homeCenter = _currentFormData.homeCenter
                ? _currentResults.find(function(c) { return c.city === _currentFormData.homeCenter; })
                : null;
            var filtered = _currentResults;
            if (_paginationFilterState) {
                filtered = _currentResults.filter(function(c) { return c.state === _paginationFilterState; });
            }
            _renderResultsTable(filtered, _currentFormData, homeCenter);
        }
    });
}

// ── Phase 2: Probability View ──────────────────────────────────────────────

/**
 * Initialize results tab toggle behavior (3 tabs: Scores, Probabilities, Equity).
 * @param {boolean} simulationAvailable - Whether Phase 2 results exist
 * @param {boolean} equityAvailable - Whether M4 equity results exist
 */
function initResultsTabs(simulationAvailable, equityAvailable) {
    const tabScores = document.getElementById('tab-scores');
    const tabProbs = document.getElementById('tab-probabilities');
    const tabEquity = document.getElementById('tab-equity');
    const panelScores = document.getElementById('panel-scores');
    const panelProbs = document.getElementById('panel-probabilities');
    const panelEquity = document.getElementById('panel-equity');
    const unavailableBanner = document.getElementById('simulation-unavailable');

    if (!tabScores || !tabProbs) return;

    if (!simulationAvailable) {
        tabProbs.disabled = true;
        tabProbs.title = 'Backend not running';
        if (unavailableBanner) unavailableBanner.style.display = 'block';
    } else {
        tabProbs.disabled = false;
        tabProbs.title = '';
        if (unavailableBanner) unavailableBanner.style.display = 'none';
    }

    // M4: Equity tab state
    if (tabEquity) {
        if (!equityAvailable) {
            tabEquity.disabled = true;
            tabEquity.title = simulationAvailable ? 'Equity analysis unavailable' : 'Backend not running';
        } else {
            tabEquity.disabled = false;
            tabEquity.title = '';
        }
    }

    // Helper to activate a single tab
    function activateTab(activeTab, activePanel) {
        var allTabs = [newTabScores, newTabProbs, newTabEquity].filter(Boolean);
        var allPanels = [panelScores, panelProbs, panelEquity].filter(Boolean);
        allTabs.forEach(function (t) {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
        });
        allPanels.forEach(function (p) { p.style.display = 'none'; });
        activeTab.classList.add('active');
        activeTab.setAttribute('aria-selected', 'true');
        activePanel.style.display = '';
    }

    // Remove old listeners by cloning
    const newTabScores = tabScores.cloneNode(true);
    const newTabProbs = tabProbs.cloneNode(true);
    tabScores.parentNode.replaceChild(newTabScores, tabScores);
    tabProbs.parentNode.replaceChild(newTabProbs, tabProbs);

    var newTabEquity = null;
    if (tabEquity) {
        newTabEquity = tabEquity.cloneNode(true);
        tabEquity.parentNode.replaceChild(newTabEquity, tabEquity);
    }

    newTabScores.addEventListener('click', function () {
        activateTab(newTabScores, panelScores);
    });

    newTabProbs.addEventListener('click', function () {
        if (newTabProbs.disabled) return;
        activateTab(newTabProbs, panelProbs);
    });

    if (newTabEquity) {
        newTabEquity.addEventListener('click', function () {
            if (newTabEquity.disabled) return;
            activateTab(newTabEquity, panelEquity);
        });
    }
}

/**
 * Render the probability view from simulation results.
 * @param {Object|null} simResult - SimulationResult from backend, or null
 * @param {Object} [formData] - Form data for sensitivity analysis
 */
function renderProbabilityView(simResult, formData) {
    _currentSimResult = simResult;
    if (formData) _currentFormData = formData;

    const container = document.getElementById('probabilityContainer');
    if (!container) return;
    container.textContent = '';

    // Hide tornado chart until sensitivity results arrive
    var tornadoSectionEl = document.getElementById('tornadoSection');
    if (tornadoSectionEl) tornadoSectionEl.style.display = 'none';

    if (!simResult || !simResult.cities) return;

    // Simulation metadata with inference mode badge
    const meta = document.createElement('div');
    meta.className = 'simulation-meta';
    var isBayesian = simResult.inference_mode === 'bayesian';
    var isMCMC = simResult.inference_mode === 'mcmc';
    if (isBayesian) {
        meta.innerHTML = '<span class="inference-badge inference-badge--bayesian">Bayesian Network</span> ' +
            'Exact inference in ' + simResult.elapsed_seconds.toFixed(2) + 's';
    } else if (isMCMC) {
        meta.innerHTML = '<span class="inference-badge inference-badge--mcmc">MCMC Hierarchical</span> ' +
            simResult.iterations.toLocaleString() + ' posterior draws in ' + simResult.elapsed_seconds.toFixed(2) + 's';
    } else {
        meta.innerHTML = '<span class="inference-badge inference-badge--mc">Monte Carlo</span> ' +
            simResult.iterations.toLocaleString() + ' iterations in ' + simResult.elapsed_seconds.toFixed(2) + 's';
    }
    container.appendChild(meta);

    // Find home center for comparison (null if not selected)
    var homeCenterCity = formData && formData.homeCenter
        ? simResult.cities.find(function (c) { return c.city === formData.homeCenter; })
        : null;

    // Create probability cards for each city
    simResult.cities.forEach(function (city, index) {
        const card = createProbabilityCard(city, index + 1, homeCenterCity);
        container.appendChild(card);
    });

    // Render charts
    setTimeout(function () {
        if (window.TransPlanProbCharts) {
            window.TransPlanProbCharts.destroyAll();
            window.TransPlanProbCharts.renderCDFChart('cdfChart', simResult.cities, 5, formData && formData.homeCenter);
            window.TransPlanProbCharts.renderCompetingRisksChart('competingRisksChart', simResult.cities, 10);
        }

        // Sensitivity analysis — async, uses top-ranked city, shown when ready
        var tornadoSection = document.getElementById('tornadoSection');
        if (window.TransPlanAPI && window.TransPlanAPI.sensitivity && formData && tornadoSection) {
            var topCity = (simResult.cities[0] && simResult.cities[0].city) || 'Nashville';
            window.TransPlanAPI.sensitivity(formData, topCity, 300).then(function (sensitivityResult) {
                if (sensitivityResult && window.TransPlanProbCharts) {
                    tornadoSection.style.display = '';
                    // Adjust canvas height based on number of parameters
                    var container = document.querySelector('.chart-container--tornado');
                    if (container) {
                        var nParams = (sensitivityResult.impacts || []).length;
                        container.style.height = Math.max(160, nParams * 60 + 80) + 'px';
                    }
                    window.TransPlanProbCharts.renderTornadoChart('tornadoChart', sensitivityResult);
                }
            });
        }

        // What-If scenario sliders — show section and populate city dropdown
        _initWhatIfSliders(simResult, formData);
        // Phase 4 M4: Policy scenario selector
        _initPolicyScenarios(simResult, formData);
        // Travel subsidy analysis (#141)
        _initTravelSubsidy(simResult, formData);
    }, 200);
}


/**
 * Initialize the what-if scenario sliders section.
 * Populates the city dropdown from simulation results and wires event handlers.
 */
function _initWhatIfSliders(simResult, formData) {
    var section = document.getElementById('whatIfSection');
    if (!section || !window.TransPlanAPI || !window.TransPlanAPI.whatIf) return;
    if (!simResult || !simResult.cities) return;

    section.style.display = '';

    // Populate city dropdown from simulation results
    var citySelect = document.getElementById('whatIfCity');
    if (citySelect && citySelect.options.length <= 1) {
        simResult.cities.forEach(function (c) {
            var opt = document.createElement('option');
            opt.value = c.city;
            opt.textContent = c.city + ', ' + c.state;
            citySelect.appendChild(opt);
        });
    }

    // Wire slider value displays
    var donorSlider = document.getElementById('whatIfDonorRate');
    var donorValue = document.getElementById('whatIfDonorRateValue');
    var waitSlider = document.getElementById('whatIfWaitTime');
    var waitValue = document.getElementById('whatIfWaitTimeValue');

    if (donorSlider) {
        donorSlider.oninput = function () {
            donorValue.textContent = parseFloat(this.value).toFixed(1) + '\u00d7';
        };
    }
    if (waitSlider) {
        waitSlider.oninput = function () {
            waitValue.textContent = parseFloat(this.value).toFixed(1) + '\u00d7';
        };
    }

    // Wire run button
    var runBtn = document.getElementById('whatIfRunBtn');
    if (runBtn) {
        runBtn.onclick = function () {
            _runWhatIfAnalysis(simResult, formData);
        };
    }
}


/**
 * Initialize the policy scenario selector (Phase 4 M4).
 * Fetches available scenarios from the backend and wires the UI.
 */
function _initPolicyScenarios(simResult, formData) {
    var section = document.getElementById('policyScenarioSection');
    if (!section || !window.TransPlanAPI || !window.TransPlanAPI.policyScenarios) return;
    if (!simResult || !simResult.cities) return;

    var scenarioSelect = document.getElementById('policyScenarioSelect');
    var citySelect = document.getElementById('policyScenarioCity');
    var runBtn = document.getElementById('policyScenarioRunBtn');
    var infoDiv = document.getElementById('policyScenarioInfo');
    var descEl = document.getElementById('policyScenarioDesc');
    var refsEl = document.getElementById('policyScenarioRefs');
    var caveatsEl = document.getElementById('policyScenarioCaveats');

    if (!scenarioSelect) return;

    // Populate city dropdown
    if (citySelect && citySelect.options.length <= 1) {
        simResult.cities.forEach(function (c) {
            var opt = document.createElement('option');
            opt.value = c.city;
            opt.textContent = c.city + ', ' + c.state;
            citySelect.appendChild(opt);
        });
    }

    // Fetch scenarios filtered by current organ
    var organ = formData && formData.organ ? formData.organ : null;
    var _scenarioCache = [];

    window.TransPlanAPI.policyScenarios(organ).then(function (scenarios) {
        if (!scenarios || !scenarios.length) {
            section.style.display = 'none';
            return;
        }
        _scenarioCache = scenarios;

        // Clear and populate scenario dropdown
        scenarioSelect.textContent = '';
        var defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = 'Select a policy scenario\u2026';
        scenarioSelect.appendChild(defaultOpt);

        scenarios.forEach(function (s) {
            var opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.name;
            scenarioSelect.appendChild(opt);
        });
    });

    // Show scenario info on selection change
    scenarioSelect.onchange = function () {
        var selectedId = scenarioSelect.value;
        if (!selectedId) {
            if (infoDiv) infoDiv.style.display = 'none';
            if (runBtn) runBtn.disabled = true;
            return;
        }

        var scenario = _scenarioCache.find(function (s) { return s.id === selectedId; });
        if (!scenario) return;

        if (descEl) descEl.textContent = scenario.description;
        if (refsEl) {
            refsEl.textContent = '';
            (scenario.references || []).forEach(function (ref) {
                var li = document.createElement('li');
                li.textContent = ref;
                refsEl.appendChild(li);
            });
        }
        if (caveatsEl) {
            caveatsEl.textContent = '';
            (scenario.caveats || []).forEach(function (caveat) {
                var li = document.createElement('li');
                li.textContent = caveat;
                caveatsEl.appendChild(li);
            });
        }
        if (infoDiv) infoDiv.style.display = '';
        if (runBtn) runBtn.disabled = false;
    };

    // Wire run button
    if (runBtn) {
        runBtn.onclick = function () {
            _runPolicyScenario(simResult, formData);
        };
    }
}

/**
 * Execute a policy scenario analysis.
 */
function _runPolicyScenario(simResult, formData) {
    var scenarioSelect = document.getElementById('policyScenarioSelect');
    var citySelect = document.getElementById('policyScenarioCity');
    var runBtn = document.getElementById('policyScenarioRunBtn');
    var resultsDiv = document.getElementById('policyScenarioResults');

    if (!scenarioSelect || !scenarioSelect.value || !formData) return;

    var scenarioId = scenarioSelect.value;
    var city = citySelect && citySelect.value
        ? citySelect.value
        : (simResult.cities[0] && simResult.cities[0].city) || 'Nashville';

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Running scenario\u2026';
    }

    window.TransPlanAPI.policyScenario(formData, scenarioId, city, 500).then(function (result) {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = 'Run Policy Scenario';
        }

        if (!result) {
            if (resultsDiv) {
                while (resultsDiv.firstChild) resultsDiv.removeChild(resultsDiv.firstChild);
                var errMsg = _el('div', 'what-if-error');
                errMsg.textContent = 'Scenario could not be run. This may happen if the selected '
                    + 'policy scenario does not apply to the chosen organ type.';
                resultsDiv.appendChild(errMsg);
            }
            return;
        }
        if (!resultsDiv) return;

        // Render using the same grid as what-if results
        _renderWhatIfResults(resultsDiv, result);

        // Add scenario-specific header
        var header = _el('div', 'policy-scenario-result-header');
        header.textContent = result.scenario
            ? result.scenario.name + ' \u2014 ' + result.city
            : city;
        resultsDiv.insertBefore(header, resultsDiv.firstChild);

        // Show effective multipliers
        var multInfo = _el('div', 'what-if-meta');
        multInfo.textContent = 'Effective multipliers for ' + result.city + ': '
            + 'donor ' + (result.donor_rate_multiplier || 1.0).toFixed(2) + '\u00d7, '
            + 'wait ' + (result.wait_time_multiplier || 1.0).toFixed(2) + '\u00d7';
        resultsDiv.insertBefore(multInfo, resultsDiv.children[1]);
    });
}


/**
 * Initialize the travel subsidy analysis section (#141).
 */
function _initTravelSubsidy(simResult, formData) {
    var section = document.getElementById('travelSubsidySection');
    if (!section || !window.TransPlanAPI || !window.TransPlanAPI.travelSubsidyAnalysis) {
        if (section) section.style.display = 'none';
        return;
    }
    if (!simResult || !simResult.cities) {
        if (section) section.style.display = 'none';
        return;
    }

    var runBtn = document.getElementById('travelSubsidyRunBtn');
    if (!runBtn) return;

    runBtn.onclick = function () {
        _runTravelSubsidyAnalysis(formData);
    };
}


/**
 * Execute travel subsidy multi-price-point comparison (#141).
 */
function _runTravelSubsidyAnalysis(formData) {
    var runBtn = document.getElementById('travelSubsidyRunBtn');
    var spinner = document.getElementById('travelSubsidySpinner');
    var resultsDiv = document.getElementById('travelSubsidyResults');
    var tableDiv = document.getElementById('travelSubsidyTable');
    var cityDetailDiv = document.getElementById('travelSubsidyCityDetail');
    var disclaimersDiv = document.getElementById('travelSubsidyDisclaimers');

    if (!formData) return;

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Analyzing 4 price points\u2026';
    }
    if (spinner) spinner.style.display = '';

    window.TransPlanAPI.travelSubsidyAnalysis(formData, [], 500).then(function (result) {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = 'Run Subsidy Comparison';
        }
        if (spinner) spinner.style.display = 'none';

        if (!result || !result.tiers || !result.tiers.length) {
            if (tableDiv) {
                tableDiv.textContent = '';
                var errMsg = _el('div', 'what-if-error');
                errMsg.textContent = 'Travel subsidy analysis could not be completed. Ensure the backend is running.';
                tableDiv.appendChild(errMsg);
            }
            if (resultsDiv) resultsDiv.style.display = '';
            return;
        }

        // Render results
        if (resultsDiv) resultsDiv.style.display = '';

        // --- Summary comparison table ---
        if (tableDiv) {
            tableDiv.textContent = '';

            var heading = _el('h5', '');
            heading.textContent = 'System-Wide Impact by Subsidy Amount';
            tableDiv.appendChild(heading);

            var table = _el('table', 'travel-subsidy-summary-table');
            var thead = _el('thead', '');
            var headerRow = _el('tr', '');
            ['Subsidy', 'Avg P(Tx \u2264 24mo)', 'With Subsidy', '\u0394 P24', 'Avg Wait', 'With Subsidy'].forEach(function (h) {
                var th = _el('th', '');
                th.textContent = h;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            var tbody = _el('tbody', '');
            result.tiers.forEach(function (tier) {
                var row = _el('tr', '');

                var labelCell = _el('td', 'subsidy-label');
                labelCell.textContent = tier.label;
                row.appendChild(labelCell);

                var baseP24Cell = _el('td', '');
                baseP24Cell.textContent = (tier.system_avg_baseline_p24 * 100).toFixed(1) + '%';
                row.appendChild(baseP24Cell);

                var adjP24Cell = _el('td', '');
                adjP24Cell.textContent = (tier.system_avg_adjusted_p24 * 100).toFixed(1) + '%';
                row.appendChild(adjP24Cell);

                var deltaCell = _el('td', tier.system_delta_p24 > 0 ? 'delta-positive' : 'delta-neutral');
                deltaCell.textContent = (tier.system_delta_p24 > 0 ? '+' : '') + (tier.system_delta_p24 * 100).toFixed(2) + ' pp';
                row.appendChild(deltaCell);

                var baseWaitCell = _el('td', '');
                baseWaitCell.textContent = tier.system_avg_baseline_wait.toFixed(1) + ' mo';
                row.appendChild(baseWaitCell);

                var adjWaitCell = _el('td', '');
                adjWaitCell.textContent = tier.system_avg_adjusted_wait.toFixed(1) + ' mo';
                row.appendChild(adjWaitCell);

                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            tableDiv.appendChild(table);

            // Marginal efficiency note
            if (result.tiers.length >= 2) {
                var firstDelta = result.tiers[0].system_delta_p24;
                var lastDelta = result.tiers[result.tiers.length - 1].system_delta_p24;
                var firstAmount = result.tiers[0].subsidy_amount;
                var lastAmount = result.tiers[result.tiers.length - 1].subsidy_amount;
                if (lastDelta > 0 && firstDelta > 0) {
                    var efficiency = (firstDelta / firstAmount) / (lastDelta / lastAmount);
                    var note = _el('p', 'travel-subsidy-note');
                    note.textContent = result.tiers[0].label + ' is '
                        + efficiency.toFixed(1) + '\u00d7 more cost-efficient per dollar than '
                        + result.tiers[result.tiers.length - 1].label
                        + ' (diminishing returns).';
                    tableDiv.appendChild(note);
                }
            }
        }

        // --- Per-city detail (top 5 most improved + bottom 5) ---
        if (cityDetailDiv && result.tiers.length > 0) {
            cityDetailDiv.textContent = '';
            // Use the $20K tier as the reference for city-level detail
            var refTier = result.tiers.find(function (t) { return t.subsidy_amount === 20000; })
                || result.tiers[result.tiers.length - 1];

            var cityHeading = _el('h5', '');
            cityHeading.textContent = 'Per-City Impact (' + refTier.label + ' Subsidy)';
            cityDetailDiv.appendChild(cityHeading);

            var sorted = refTier.cities.slice().sort(function (a, b) {
                return b.delta_p24 - a.delta_p24;
            });

            var cityTable = _el('table', 'travel-subsidy-city-table');
            var cThead = _el('thead', '');
            var cHeaderRow = _el('tr', '');
            ['City', 'Baseline P24', 'With Subsidy', '\u0394 P24', 'Wait \u0394'].forEach(function (h) {
                var th = _el('th', '');
                th.textContent = h;
                cHeaderRow.appendChild(th);
            });
            cThead.appendChild(cHeaderRow);
            cityTable.appendChild(cThead);

            var cTbody = _el('tbody', '');
            sorted.forEach(function (c) {
                var row = _el('tr', '');

                var cityCell = _el('td', '');
                cityCell.textContent = c.city + ', ' + c.state;
                row.appendChild(cityCell);

                var bCell = _el('td', '');
                bCell.textContent = (c.baseline_p24 * 100).toFixed(1) + '%';
                row.appendChild(bCell);

                var aCell = _el('td', '');
                aCell.textContent = (c.adjusted_p24 * 100).toFixed(1) + '%';
                row.appendChild(aCell);

                var dCell = _el('td', c.delta_p24 > 0 ? 'delta-positive' : 'delta-neutral');
                dCell.textContent = (c.delta_p24 > 0 ? '+' : '') + (c.delta_p24 * 100).toFixed(2) + ' pp';
                row.appendChild(dCell);

                var wCell = _el('td', '');
                var waitDelta = c.adjusted_median_wait - c.baseline_median_wait;
                wCell.textContent = (waitDelta < 0 ? '' : '+') + waitDelta.toFixed(1) + ' mo';
                row.appendChild(wCell);

                cTbody.appendChild(row);
            });
            cityTable.appendChild(cTbody);
            cityDetailDiv.appendChild(cityTable);
        }

        // --- Disclaimers ---
        if (disclaimersDiv && result.disclaimers) {
            disclaimersDiv.textContent = '';
            var dHeading = _el('h5', '');
            dHeading.textContent = 'Disclaimers';
            disclaimersDiv.appendChild(dHeading);
            result.disclaimers.forEach(function (d) {
                var p = _el('p', 'disclaimer-text');
                p.textContent = d;
                disclaimersDiv.appendChild(p);
            });
        }
    });
}


/**
 * Execute what-if analysis: call backend with slider values, render results.
 */
function _runWhatIfAnalysis(simResult, formData) {
    var donorSlider = document.getElementById('whatIfDonorRate');
    var waitSlider = document.getElementById('whatIfWaitTime');
    var citySelect = document.getElementById('whatIfCity');
    var runBtn = document.getElementById('whatIfRunBtn');
    var resultsDiv = document.getElementById('whatIfResults');

    if (!donorSlider || !waitSlider || !formData) return;

    var donorMult = parseFloat(donorSlider.value);
    var waitMult = parseFloat(waitSlider.value);
    var city = citySelect && citySelect.value
        ? citySelect.value
        : (simResult.cities[0] && simResult.cities[0].city) || 'Nashville';

    // Disable button during request
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Running simulation\u2026';
    }

    window.TransPlanAPI.whatIf(formData, city, donorMult, waitMult, 500).then(function (result) {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = 'Run What-If Simulation';
        }

        if (!result || !resultsDiv) return;
        _renderWhatIfResults(resultsDiv, result);
    });
}


/**
 * Render what-if results into the results container using safe DOM methods.
 */
function _renderWhatIfResults(container, result) {
    container.style.display = '';
    container.textContent = '';

    var grid = _el('div', 'what-if-result-grid');

    // Baseline p24
    var baselineMetric = _el('div', 'what-if-metric');
    baselineMetric.appendChild(_el('div', 'what-if-metric-label', 'Baseline'));
    baselineMetric.appendChild(_el('div', 'what-if-metric-value', (result.baseline_p24 * 100).toFixed(1) + '%'));
    var baseCi = _el('div', 'what-if-meta');
    baseCi.textContent = '95% CI: ' + (result.baseline_ci_95[0] * 100).toFixed(1) + '–' + (result.baseline_ci_95[1] * 100).toFixed(1) + '%';
    baselineMetric.appendChild(baseCi);
    grid.appendChild(baselineMetric);

    // Adjusted p24
    var adjustedMetric = _el('div', 'what-if-metric');
    adjustedMetric.appendChild(_el('div', 'what-if-metric-label', 'Adjusted'));
    adjustedMetric.appendChild(_el('div', 'what-if-metric-value', (result.adjusted_p24 * 100).toFixed(1) + '%'));
    var adjCi = _el('div', 'what-if-meta');
    adjCi.textContent = '95% CI: ' + (result.adjusted_ci_95[0] * 100).toFixed(1) + '–' + (result.adjusted_ci_95[1] * 100).toFixed(1) + '%';
    adjustedMetric.appendChild(adjCi);
    grid.appendChild(adjustedMetric);

    // Delta
    var deltaMetric = _el('div', 'what-if-metric');
    deltaMetric.appendChild(_el('div', 'what-if-metric-label', 'Change'));
    var deltaVal = result.delta_p24 * 100;
    var deltaSign = deltaVal > 0 ? '+' : '';
    var deltaEl = _el('div', 'what-if-metric-value', deltaSign + deltaVal.toFixed(1) + ' pp');
    deltaMetric.appendChild(deltaEl);
    var deltaClass = deltaVal > 0.05 ? 'positive' : deltaVal < -0.05 ? 'negative' : 'neutral';
    var deltaLabel = _el('div', 'what-if-metric-delta ' + deltaClass);
    deltaLabel.textContent = deltaVal > 0.05 ? 'Improved' : deltaVal < -0.05 ? 'Worsened' : 'No significant change';
    deltaMetric.appendChild(deltaLabel);
    grid.appendChild(deltaMetric);

    container.appendChild(grid);

    // Median wait comparison
    var waitGrid = _el('div', 'what-if-result-grid');
    waitGrid.style.marginTop = 'var(--space-3)';

    var baseWait = _el('div', 'what-if-metric');
    baseWait.appendChild(_el('div', 'what-if-metric-label', 'Baseline Median Wait'));
    baseWait.appendChild(_el('div', 'what-if-metric-value', result.baseline_median_wait.toFixed(1) + ' mo'));
    waitGrid.appendChild(baseWait);

    var adjWait = _el('div', 'what-if-metric');
    adjWait.appendChild(_el('div', 'what-if-metric-label', 'Adjusted Median Wait'));
    adjWait.appendChild(_el('div', 'what-if-metric-value', result.adjusted_median_wait.toFixed(1) + ' mo'));
    waitGrid.appendChild(adjWait);

    var waitDelta = _el('div', 'what-if-metric');
    waitDelta.appendChild(_el('div', 'what-if-metric-label', 'Wait Change'));
    var waitDiff = result.adjusted_median_wait - result.baseline_median_wait;
    var waitSign = waitDiff > 0 ? '+' : '';
    waitDelta.appendChild(_el('div', 'what-if-metric-value', waitSign + waitDiff.toFixed(1) + ' mo'));
    // For wait: negative is good (shorter wait)
    var waitClass = waitDiff < -0.1 ? 'positive' : waitDiff > 0.1 ? 'negative' : 'neutral';
    var waitLabel = _el('div', 'what-if-metric-delta ' + waitClass);
    waitLabel.textContent = waitDiff < -0.1 ? 'Shorter wait' : waitDiff > 0.1 ? 'Longer wait' : 'No significant change';
    waitDelta.appendChild(waitLabel);
    waitGrid.appendChild(waitDelta);

    container.appendChild(waitGrid);

    // Metadata
    var meta = _el('div', 'what-if-meta');
    meta.textContent = result.city + ' · ' + result.iterations.toLocaleString() + ' iterations · ' +
        'Donor ' + result.donor_rate_multiplier.toFixed(1) + '\u00d7 · Wait ' +
        result.wait_time_multiplier.toFixed(1) + '\u00d7 · ' + result.elapsed_seconds.toFixed(2) + 's';
    container.appendChild(meta);
}

/**
 * Helper: create a text element.
 */
function _el(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
}

/**
 * Create a probability city card element using safe DOM methods.
 */
function createProbabilityCard(city, rank, homeCenter) {
    const card = _el('div', 'prob-card');
    card.style.cursor = 'pointer';
    card.dataset.city = city.city;

    if (rank <= 3) card.classList.add('rank-' + rank);

    const isHome = homeCenter && city.city === homeCenter.city;
    if (isHome) card.classList.add('home-center');

    const ci = city.confidence_interval_95 || [0, 0];

    // Header
    const header = _el('div', 'prob-card-header');
    const info = _el('div');
    info.appendChild(_el('h3', null, city.city));
    info.appendChild(_el('span', 'state', city.state));
    header.appendChild(info);

    const headerRight = _el('div', 'city-header-right');
    const compareLabel = _el('label', 'compare-check');
    compareLabel.title = 'Add to comparison';
    compareLabel.onclick = function(e) { e.stopPropagation(); };
    const compareInput = document.createElement('input');
    compareInput.type = 'checkbox';
    compareInput.dataset.city = city.city;
    compareInput.dataset.panel = 'probs';
    compareInput.onchange = updateCompareBar;
    compareLabel.appendChild(compareInput);
    compareLabel.appendChild(document.createTextNode(' Compare'));
    headerRight.appendChild(compareLabel);
    headerRight.appendChild(_el('span', 'prob-card-rank', '#' + rank));
    header.appendChild(headerRight);
    card.appendChild(header);

    card.addEventListener('click', function(e) {
        if (e.target.closest('.compare-check')) return;
        openCityDetail(city.city);
    });

    // Comparison indicator
    if (homeCenter) {
        const compDiv = _el('div', 'comparison-indicator');
        if (isHome) {
            compDiv.classList.add('comparison-home');
            compDiv.textContent = 'Reference Center';
        } else {
            const delta = city.p_transplant_24mo - homeCenter.p_transplant_24mo;
            const pctDelta = (delta * 100).toFixed(1);
            const sign = delta >= 0 ? '+' : '';
            compDiv.classList.add(delta >= 0 ? 'comparison-positive' : 'comparison-negative');
            compDiv.textContent = sign + pctDelta + '% vs. home';
        }
        card.appendChild(compDiv);
    }

    // Probability metrics grid
    const metrics = _el('div', 'prob-metrics');
    const timepoints = [
        ['6 months', city.p_transplant_6mo],
        ['12 months', city.p_transplant_12mo],
        ['24 months', city.p_transplant_24mo],
        ['36 months', city.p_transplant_36mo]
    ];
    timepoints.forEach(function (tp) {
        const m = _el('div', 'prob-metric');
        m.appendChild(_el('div', 'prob-metric-label', tp[0]));
        m.appendChild(_el('div', 'prob-metric-value ' + probClass(tp[1]), formatPct(tp[1])));
        metrics.appendChild(m);
    });

    // Median wait
    const medianMetric = _el('div', 'prob-metric');
    medianMetric.appendChild(_el('div', 'prob-metric-label', 'Median Wait'));
    medianMetric.appendChild(_el('div', 'prob-metric-value', city.median_wait_months.toFixed(1) + ' mo'));
    metrics.appendChild(medianMetric);

    card.appendChild(metrics);

    // CI text — BBN is deterministic, so label as "Uncertainty band" (#54)
    var ciLabel = (_currentSimResult && _currentSimResult.inference_mode === 'bayesian')
        ? 'Uncertainty band' : '95% CI';
    card.appendChild(_el('div', 'prob-ci',
        ciLabel + ' at 24 mo: ' + formatPct(ci[0]) + ' \u2013 ' + formatPct(ci[1])));

    // Competing risks bar
    if (city.competing_risks) {
        card.appendChild(buildRiskBar(city.competing_risks));
    }

    // Post-transplant outcomes (Phase 4 M2)
    if (city.outcomes) {
        card.appendChild(buildOutcomesSection(city.outcomes));
    }

    // Historical trend badge (Phase 4 M3)
    if (city.trends && city.trends.overall_direction && city.trends.overall_direction !== 'insufficient_data') {
        card.appendChild(buildTrendBadge(city.trends));
    }

    return card;
}

function buildRiskBar(cr) {
    const wrapper = document.createDocumentFragment();
    const bar = _el('div', 'prob-risks');
    const segments = [
        [cr.p_transplant_24mo || 0, '#27ae60'],
        [cr.p_still_waiting_24mo || 0, '#bdc3c7'],
        [cr.p_delisting_24mo || 0, '#f39c12'],
        [cr.p_mortality_24mo || 0, '#e74c3c']
    ];
    segments.forEach(function (s) {
        const seg = _el('div', 'prob-risk-segment');
        seg.style.width = (s[0] * 100) + '%';
        seg.style.background = s[1];
        bar.appendChild(seg);
    });
    wrapper.appendChild(bar);

    const legend = _el('div', 'prob-risk-legend');
    const labels = [
        ['risk-transplant', 'Transplanted', cr.p_transplant_24mo || 0],
        ['risk-waiting', 'Waiting', cr.p_still_waiting_24mo || 0],
        ['risk-delisted', 'Delisted', cr.p_delisting_24mo || 0],
        ['risk-mortality', 'Mortality', cr.p_mortality_24mo || 0]
    ];
    labels.forEach(function (l) {
        legend.appendChild(_el('span', l[0], l[1] + ' ' + formatPct(l[2])));
    });
    wrapper.appendChild(legend);

    return wrapper;
}

function buildOutcomesSection(outcomes) {
    var section = _el('div', 'prob-outcomes');

    // Graft survival row
    if (outcomes.graft_survival_1yr != null) {
        var gsPct = (outcomes.graft_survival_1yr * 100).toFixed(1);
        var natGs = outcomes.national_graft_survival_1yr
            ? (outcomes.national_graft_survival_1yr * 100).toFixed(1) : null;
        var gsRow = _el('div', 'outcome-row');
        gsRow.appendChild(_el('span', 'outcome-label', '1yr Graft Survival'));
        var gsVal = _el('span', 'outcome-value');
        gsVal.textContent = gsPct + '%';
        if (natGs) {
            gsVal.classList.add(parseFloat(gsPct) >= parseFloat(natGs) ? 'outcome-good' : 'outcome-warn');
            gsVal.title = 'National avg: ' + natGs + '%';
        }
        gsRow.appendChild(gsVal);
        section.appendChild(gsRow);
    }

    // Compound success
    if (outcomes.compound_success != null) {
        var csRow = _el('div', 'outcome-row outcome-compound');
        csRow.appendChild(_el('span', 'outcome-label', 'Overall Success'));
        var csVal = _el('span', 'outcome-value ' + probClass(outcomes.compound_success));
        csVal.textContent = (outcomes.compound_success * 100).toFixed(1) + '%';
        csVal.title = 'P(transplant within 24mo) \u00D7 P(1yr graft survival)';
        csRow.appendChild(csVal);
        section.appendChild(csRow);
    }

    // Performance badge
    if (outcomes.performance_rating && outcomes.performance_rating !== 'insufficient_data') {
        var badge = _el('span', 'performance-badge performance-' + outcomes.performance_rating.replace(/_/g, '-'));
        var badgeLabels = {
            'better_than_expected': 'Above Expected',
            'as_expected': 'As Expected',
            'worse_than_expected': 'Below Expected'
        };
        badge.textContent = badgeLabels[outcomes.performance_rating] || outcomes.performance_rating;
        section.appendChild(badge);
    }

    return section;
}

function buildTrendBadge(trends) {
    var badge = _el('div', 'trend-badge trend-' + trends.overall_direction);
    var arrows = { improving: '\u2191', stable: '\u2192', declining: '\u2193' };
    var labels = { improving: 'Improving', stable: 'Stable', declining: 'Declining' };
    var dir = trends.overall_direction;
    badge.textContent = (arrows[dir] || '') + ' ' + (labels[dir] || dir) + ' (historical trend)';

    // Tooltip with detail
    var details = [];
    if (trends.wait_time_trend && trends.wait_time_trend.direction !== 'insufficient_data') {
        details.push('Wait time: ' + trends.wait_time_trend.direction);
    }
    if (trends.volume_trend && trends.volume_trend.direction !== 'insufficient_data') {
        details.push('Volume: ' + trends.volume_trend.direction);
    }
    if (trends.graft_survival_trend && trends.graft_survival_trend.direction !== 'insufficient_data') {
        details.push('Graft survival: ' + trends.graft_survival_trend.direction);
    }
    if (details.length) badge.title = details.join('\n');

    return badge;
}

function formatPct(v) {
    return (v * 100).toFixed(1) + '%';
}

function probClass(v) {
    if (v >= 0.5) return 'high';
    if (v >= 0.2) return 'mid';
    return 'low';
}

// ==================== M4: Equity Analysis View ====================

/**
 * Render the equity analysis view from backend results.
 * @param {Object|null} equityResult - EquityAnalysisResult from backend, or null
 */
function renderEquityView(equityResult) {
    _currentEquityResult = equityResult;

    var container = document.getElementById('equityContainer');
    var disclaimersEl = document.getElementById('equityDisclaimers');
    if (!container) return;
    container.textContent = '';

    // Destroy old charts
    if (window.TransPlanEquityCharts) {
        window.TransPlanEquityCharts.destroyAll();
    }

    if (!equityResult || !equityResult.cities) return;

    // --- Summary card ---
    var summary = _el('div', 'equity-summary-card');

    // Gini badge
    var giniBadge = _el('div', 'equity-gini-badge');
    var giniVal = equityResult.overall_gini;
    var giniLevel = giniVal < 0.15 ? 'low' : giniVal < 0.30 ? 'mid' : 'high';
    giniBadge.classList.add(giniLevel);
    giniBadge.innerHTML = '<span class="gini-label">Overall Gini</span><span class="gini-value">' +
        giniVal.toFixed(4) + '</span><span class="gini-level">' +
        (giniLevel === 'low' ? 'Low Inequality' : giniLevel === 'mid' ? 'Moderate Inequality' : 'High Inequality') + '</span>';
    summary.appendChild(giniBadge);

    // Stats
    var stats = _el('div', 'equity-stats');
    stats.innerHTML =
        '<div class="equity-stat"><span class="stat-value">' + equityResult.profiles_simulated + '</span><span class="stat-label">Profiles Simulated</span></div>' +
        '<div class="equity-stat"><span class="stat-value">' + equityResult.cities.length + '</span><span class="stat-label">Cities Analyzed</span></div>' +
        '<div class="equity-stat"><span class="stat-value">' + equityResult.iterations_per_profile + '</span><span class="stat-label">Iterations/Profile</span></div>' +
        '<div class="equity-stat"><span class="stat-value">' + equityResult.elapsed_seconds.toFixed(1) + 's</span><span class="stat-label">Compute Time</span></div>';
    summary.appendChild(stats);

    container.appendChild(summary);

    // --- City equity table ---
    var tableSection = _el('div', 'equity-table-section');
    var tableTitle = _el('h3', '', 'City Equity Rankings');
    tableSection.appendChild(tableTitle);

    var table = document.createElement('table');
    table.className = 'equity-city-table';

    // Header
    var thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>Rank</th><th>City</th><th>State</th><th>Gini</th><th>Best P24</th><th>Worst P24</th><th>Range</th></tr>';
    table.appendChild(thead);

    // Body
    var tbody = document.createElement('tbody');
    equityResult.cities.forEach(function (city, idx) {
        var tr = document.createElement('tr');
        var gLevel = city.gini_coefficient < 0.15 ? 'low' : city.gini_coefficient < 0.30 ? 'mid' : 'high';
        tr.innerHTML =
            '<td>' + (idx + 1) + '</td>' +
            '<td><strong>' + city.city + '</strong></td>' +
            '<td>' + city.state + '</td>' +
            '<td class="gini-cell ' + gLevel + '">' + city.gini_coefficient.toFixed(4) + '</td>' +
            '<td>' + (city.p24_range[1] * 100).toFixed(1) + '%</td>' +
            '<td>' + (city.p24_range[0] * 100).toFixed(1) + '%</td>' +
            '<td>' + ((city.p24_range[1] - city.p24_range[0]) * 100).toFixed(1) + ' pp</td>';
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableSection.appendChild(table);
    container.appendChild(tableSection);

    // --- Render charts (use first city's dimension data for detail charts) ---
    // Use overall averages across all cities for the disparity charts
    var allBloodType = _aggregateDimension(equityResult.cities, 'blood_type');
    var allAge = _aggregateDimension(equityResult.cities, 'age_bracket');

    if (window.TransPlanEquityCharts) {
        window.TransPlanEquityCharts.renderBloodTypeDisparityChart('equityBloodTypeChart', allBloodType);
        window.TransPlanEquityCharts.renderAgeDisparityChart('equityAgeChart', allAge);
        window.TransPlanEquityCharts.renderGiniByCity('equityGiniChart', equityResult.cities);
    }

    // --- Disclaimers ---
    if (disclaimersEl && equityResult.disclaimers && equityResult.disclaimers.length) {
        disclaimersEl.innerHTML = '<h3>Important Limitations</h3>';
        var ul = document.createElement('ul');
        equityResult.disclaimers.forEach(function (text) {
            var li = document.createElement('li');
            li.textContent = text;
            ul.appendChild(li);
        });
        disclaimersEl.appendChild(ul);
    }
}

/**
 * Aggregate dimension disparity data across all cities (average p24 and median_wait per value).
 */
function _aggregateDimension(cities, dimKey) {
    var sums = {};   // value -> { p24Sum, waitSum, count }
    cities.forEach(function (city) {
        var entries = city.dimension_disparities[dimKey] || [];
        entries.forEach(function (entry) {
            if (!sums[entry.value]) {
                sums[entry.value] = { p24Sum: 0, waitSum: 0, count: 0 };
            }
            sums[entry.value].p24Sum += entry.p24;
            sums[entry.value].waitSum += entry.median_wait;
            sums[entry.value].count += 1;
        });
    });
    var result = [];
    Object.keys(sums).sort().forEach(function (val) {
        var s = sums[val];
        result.push({
            value: val,
            p24: s.p24Sum / s.count,
            median_wait: s.waitSum / s.count
        });
    });
    return result;
}

// ==================== M3: City Detail Modal ====================

// CATEGORY_LABELS is already declared in algorithm.js (loaded before script.js)

// Issue #69: Read current weights from TransPlanWeights (respects user customization).
// Falls back to DEFAULT_WEIGHTS from algorithm.js if TransPlanWeights not available.
function _getCurrentWeightsInt() {
    var tw = window.TransPlanWeights;
    if (tw) {
        var custom = tw.getWeights();
        if (custom) {
            var result = {};
            CATEGORY_KEYS.forEach(function(k) { result[k] = Math.round(custom[k] * 100); });
            return result;
        }
    }
    var result = {};
    CATEGORY_KEYS.forEach(function(k) { result[k] = Math.round(DEFAULT_WEIGHTS[k] * 100); });
    return result;
}

function openCityDetail(cityName) {
    var city = _currentResults ? _currentResults.find(function(c) { return c.city === cityName; }) : null;
    var simCity = _currentSimResult && _currentSimResult.cities
        ? _currentSimResult.cities.find(function(c) { return c.city === cityName; })
        : null;
    if (!city && !simCity) return;

    var modal = document.getElementById('cityDetailModal');
    var nameEl = document.getElementById('modal-city-name');
    var stateEl = document.getElementById('modal-state-name');
    var body = document.getElementById('modal-body');

    nameEl.textContent = city ? city.city : simCity.city;
    stateEl.textContent = city ? city.state : simCity.state;
    body.innerHTML = '';

    // Rank info
    if (city) {
        var rank = _currentResults.indexOf(city) + 1;
        var overallDiv = document.createElement('div');
        overallDiv.className = 'modal-overall-score';
        overallDiv.innerHTML = '<span class="score-big">' + city.personalizedScore.toFixed(1) + '</span>' +
            '<span class="score-label">/100 &mdash; Rank #' + rank + '</span>';
        body.appendChild(overallDiv);
    }

    // Home center comparison
    if (city && _currentFormData && _currentFormData.homeCenter) {
        var homeCity = _currentResults.find(function(c) { return c.city === _currentFormData.homeCenter; });
        if (homeCity && homeCity.city !== city.city) {
            var delta = city.personalizedScore - homeCity.personalizedScore;
            var compDiv = document.createElement('div');
            compDiv.className = 'comparison-badge ' + (delta >= 0 ? 'comparison-positive' : 'comparison-negative');
            compDiv.style.display = 'inline-block';
            compDiv.style.marginBottom = 'var(--space-4)';
            compDiv.textContent = (delta >= 0 ? '+' : '') + delta.toFixed(1) + ' pts vs. ' + homeCity.city;
            body.appendChild(compDiv);
        }
    }

    // Score breakdown table
    if (city && city.scoreBreakdown) {
        var section = _modalSection('Score Breakdown');
        var table = document.createElement('table');
        table.className = 'modal-score-table';
        table.innerHTML = '<thead><tr><th>Category</th><th class="num">Score</th><th class="num">Weight</th><th class="num">Contribution</th><th class="modal-score-bar-cell">Visual</th></tr></thead>';
        var tbody = document.createElement('tbody');
        var currentWeights = _getCurrentWeightsInt();
        var keys = Object.keys(CATEGORY_LABELS);
        keys.forEach(function(key) {
            var raw = city.scoreBreakdown[key] || 0;
            var weight = currentWeights[key] || 0;
            var contribution = (raw * weight / 100).toFixed(1);
            var tr = document.createElement('tr');
            tr.innerHTML = '<td class="cat-name">' + CATEGORY_LABELS[key] + '</td>' +
                '<td class="num">' + raw.toFixed(1) + '</td>' +
                '<td class="num">' + weight + '%</td>' +
                '<td class="num">' + contribution + '</td>' +
                '<td class="modal-score-bar-cell"><div class="modal-score-bar"><div class="modal-score-bar-fill" style="width:' + raw + '%"></div></div></td>';
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        section.appendChild(table);
        body.appendChild(section);
    }

    // Key factors
    if (city && city.factors && city.factors.length > 0) {
        var factorsSection = _modalSection('Key Factors');
        var ul = document.createElement('ul');
        ul.className = 'modal-factors';
        city.factors.forEach(function(f) {
            var li = document.createElement('li');
            li.textContent = f;
            ul.appendChild(li);
        });
        factorsSection.appendChild(ul);
        body.appendChild(factorsSection);
    }

    // Radar chart
    if (city && city.scoreBreakdown && window.TransPlanCharts) {
        var radarSection = _modalSection('Score Profile');
        var canvas = document.createElement('canvas');
        canvas.id = 'modal-radar-chart';
        canvas.style.maxHeight = '300px';
        radarSection.appendChild(canvas);
        body.appendChild(radarSection);
        setTimeout(function() {
            window.TransPlanCharts.createRadarChart('modal-radar-chart', city.scoreBreakdown, city.city);
        }, 50);
    }

    // Phase 2 probabilities
    if (simCity) {
        var probSection = _modalSection('Transplant Probabilities');
        var grid = document.createElement('div');
        grid.className = 'modal-prob-grid';
        var timepoints = [
            ['6 months', simCity.p_transplant_6mo],
            ['12 months', simCity.p_transplant_12mo],
            ['24 months', simCity.p_transplant_24mo],
            ['36 months', simCity.p_transplant_36mo]
        ];
        timepoints.forEach(function(tp) {
            var item = document.createElement('div');
            item.className = 'modal-prob-item';
            item.innerHTML = '<div class="label">' + tp[0] + '</div>' +
                '<div class="value ' + probClass(tp[1]) + '">' + formatPct(tp[1]) + '</div>';
            grid.appendChild(item);
        });
        // Median wait
        var medianItem = document.createElement('div');
        medianItem.className = 'modal-prob-item';
        medianItem.innerHTML = '<div class="label">Median Wait</div>' +
            '<div class="value">' + simCity.median_wait_months.toFixed(1) + ' mo</div>';
        grid.appendChild(medianItem);
        probSection.appendChild(grid);

        // CI / Uncertainty band — BBN is deterministic (#54)
        var ci = simCity.confidence_interval_95 || [0, 0];
        var modalCiLabel = (_currentSimResult && _currentSimResult.inference_mode === 'bayesian')
            ? 'Uncertainty band' : '95% CI';
        var ciDiv = document.createElement('div');
        ciDiv.style.marginTop = 'var(--space-3)';
        ciDiv.style.fontSize = 'var(--fs-sm)';
        ciDiv.style.color = 'var(--text-3)';
        ciDiv.textContent = modalCiLabel + ' at 24 mo: ' + formatPct(ci[0]) + ' \u2013 ' + formatPct(ci[1]);
        probSection.appendChild(ciDiv);

        body.appendChild(probSection);

        // Competing risks
        if (simCity.competing_risks) {
            var riskSection = _modalSection('24-Month Waitlist Outcomes');
            riskSection.appendChild(buildRiskBar(simCity.competing_risks));
            body.appendChild(riskSection);
        }

        // Post-transplant outcomes (Phase 4 M2)
        if (simCity.outcomes) {
            var outcomeSection = _modalSection('Post-Transplant Outlook');
            var oc = simCity.outcomes;

            var outcomeGrid = _el('div', 'outcome-grid');
            var items = [];
            if (oc.graft_survival_1yr != null) {
                items.push(['1yr Graft Survival', (oc.graft_survival_1yr * 100).toFixed(1) + '%',
                    oc.national_graft_survival_1yr ? 'National: ' + (oc.national_graft_survival_1yr * 100).toFixed(1) + '%' : '']);
            }
            if (oc.patient_survival_1yr != null) {
                items.push(['1yr Patient Survival', (oc.patient_survival_1yr * 100).toFixed(1) + '%',
                    oc.national_patient_survival_1yr ? 'National: ' + (oc.national_patient_survival_1yr * 100).toFixed(1) + '%' : '']);
            }
            if (oc.graft_hr_1yr != null) {
                var hrText = oc.graft_hr_1yr.toFixed(3);
                if (oc.graft_hr_1yr_ci) {
                    hrText += ' (' + oc.graft_hr_1yr_ci[0].toFixed(3) + '\u2013' + oc.graft_hr_1yr_ci[1].toFixed(3) + ')';
                }
                items.push(['Hazard Ratio (1yr)', hrText, 'Lower is better; <1.0 = above expected']);
            }
            if (oc.compound_success != null) {
                items.push(['Overall Success', (oc.compound_success * 100).toFixed(1) + '%',
                    'P(transplant 24mo) \u00D7 P(1yr graft survival)']);
            }
            if (oc.n_1yr != null) {
                items.push(['Cohort Size', String(oc.n_1yr) + ' patients', '']);
            }

            items.forEach(function(item) {
                var cell = _el('div', 'outcome-grid-cell');
                cell.appendChild(_el('div', 'outcome-grid-label', item[0]));
                cell.appendChild(_el('div', 'outcome-grid-value', item[1]));
                if (item[2]) cell.appendChild(_el('div', 'outcome-grid-note', item[2]));
                outcomeGrid.appendChild(cell);
            });
            outcomeSection.appendChild(outcomeGrid);

            // Performance badge
            if (oc.performance_rating && oc.performance_rating !== 'insufficient_data') {
                var badge = _el('div', 'performance-badge performance-' + oc.performance_rating.replace(/_/g, '-'));
                var labels = { 'better_than_expected': 'Above Expected', 'as_expected': 'As Expected', 'worse_than_expected': 'Below Expected' };
                badge.textContent = 'SRTR Rating: ' + (labels[oc.performance_rating] || oc.performance_rating);
                outcomeSection.appendChild(badge);
            }

            // Disclaimer
            var disc = _el('div', 'outcome-disclaimer');
            disc.textContent = 'These are risk-adjusted center-level averages from SRTR, not individual predictions. Actual outcomes depend on many clinical factors.';
            outcomeSection.appendChild(disc);

            body.appendChild(outcomeSection);
        }

        // Historical trends with sparkline charts (Phase 4 M3)
        if (simCity.trends && simCity.trends.sparklines) {
            var trendSection = _modalSection('Historical Trends');

            // Overall trend badge in modal
            if (simCity.trends.overall_direction && simCity.trends.overall_direction !== 'insufficient_data') {
                trendSection.appendChild(buildTrendBadge(simCity.trends));
            }

            // Sparkline grid
            var sparkGrid = _el('div', 'trend-sparklines');
            var sparklines = simCity.trends.sparklines;
            var national = simCity.trends.national || {};

            var sparkConfigs = [
                { key: 'wait_time', label: 'Wait Time (months)', trendKey: 'wait_time_trend', unit: ' mo', lower_is_better: true },
                { key: 'volume', label: 'Transplant Volume', trendKey: 'volume_trend', unit: '', lower_is_better: false },
                { key: 'graft_survival', label: 'Graft Survival 1yr (%)', trendKey: 'graft_survival_trend', unit: '%', lower_is_better: false },
            ];

            sparkConfigs.forEach(function(cfg) {
                var values = sparklines[cfg.key];
                if (!values || !values.some(function(v) { return v != null; })) return;

                var cell = _el('div', 'sparkline-cell');
                cell.appendChild(_el('h4', null, cfg.label));

                // Canvas for Chart.js sparkline
                var canvasWrap = _el('div', 'sparkline-canvas-wrapper');
                var canvas = document.createElement('canvas');
                canvas.id = 'sparkline-' + cfg.key;
                canvasWrap.appendChild(canvas);
                cell.appendChild(canvasWrap);

                // Direction indicator
                var metricTrend = simCity.trends[cfg.trendKey];
                if (metricTrend && metricTrend.direction !== 'insufficient_data') {
                    var dirSpan = _el('div', 'sparkline-direction');
                    var arrows = { improving: '\u2191', stable: '\u2192', declining: '\u2193' };
                    var colors = { improving: 'var(--success-700)', stable: 'var(--text-muted)', declining: 'var(--warning-700)' };
                    dirSpan.textContent = (arrows[metricTrend.direction] || '') + ' ' + metricTrend.direction;
                    dirSpan.style.color = colors[metricTrend.direction] || '';
                    if (metricTrend.change_per_year != null) {
                        var sign = metricTrend.change_per_year >= 0 ? '+' : '';
                        dirSpan.textContent += ' (' + sign + metricTrend.change_per_year + cfg.unit + '/yr)';
                    }
                    cell.appendChild(dirSpan);
                }

                sparkGrid.appendChild(cell);

                // Render sparkline after DOM insertion
                setTimeout(function() {
                    _renderSparkline(canvas, sparklines.years, values, national[cfg.key], cfg.lower_is_better);
                }, 50);
            });

            trendSection.appendChild(sparkGrid);

            // Trend disclaimer
            var tDisc = _el('div', 'outcome-disclaimer');
            tDisc.textContent = 'Trends are based on multi-year SRTR data. Statistical significance tested via linear regression (p < 0.10). Past trends do not predict future performance.';
            trendSection.appendChild(tDisc);

            body.appendChild(trendSection);
        }
    }

    // Show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    modal.querySelector('.city-modal-close').focus();
}

function _modalSection(title) {
    var section = document.createElement('div');
    section.className = 'modal-section';
    var h3 = document.createElement('h3');
    h3.textContent = title;
    section.appendChild(h3);
    return section;
}

// Track sparkline Chart.js instances for cleanup
var _sparklineCharts = [];

function _renderSparkline(canvas, years, values, nationalValues, lowerIsBetter) {
    if (typeof Chart === 'undefined') return;

    // Filter data for Chart.js (replace nulls with NaN for gaps)
    var data = values.map(function(v) { return v != null ? v : NaN; });

    var datasets = [{
        data: data,
        borderColor: 'var(--accent, #4361ee)',
        backgroundColor: 'rgba(67, 97, 238, 0.08)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 3,
        spanGaps: true,
    }];

    // National reference line (dashed)
    if (nationalValues && nationalValues.length === years.length) {
        var natData = nationalValues.map(function(v) { return v != null ? v : NaN; });
        datasets.push({
            data: natData,
            borderColor: 'rgba(128, 128, 128, 0.5)',
            borderWidth: 1,
            borderDash: [4, 3],
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            spanGaps: true,
        });
    }

    var chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: years.map(String),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(ctx) {
                            var val = ctx.parsed.y;
                            return ctx.datasetIndex === 0 ? 'Center: ' + val : 'National: ' + val;
                        }
                    }
                },
            },
            scales: {
                x: { display: false },
                y: { display: false },
            },
            elements: {
                point: { radius: 0 },
                line: { borderWidth: 2 },
            },
            animation: { duration: 300 },
        },
    });

    _sparklineCharts.push(chart);
}

function closeCityDetail() {
    var modal = document.getElementById('cityDetailModal');
    modal.style.display = 'none';
    document.body.style.overflow = '';
    // Destroy radar chart if any
    if (window.TransPlanCharts && window.TransPlanCharts.destroyChart) {
        window.TransPlanCharts.destroyChart('modal-radar-chart');
    }
    // Destroy sparkline charts
    _sparklineCharts.forEach(function(c) { try { c.destroy(); } catch(e) {} });
    _sparklineCharts = [];
}

function closeCompareModal() {
    var modal = document.getElementById('cityCompareModal');
    modal.style.display = 'none';
    document.body.style.overflow = '';
}

// Close modals on backdrop click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('city-modal-backdrop')) {
        var modal = e.target.closest('.city-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }
});

// Close modals on ESC key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var detail = document.getElementById('cityDetailModal');
        var compare = document.getElementById('cityCompareModal');
        if (compare && compare.style.display !== 'none') {
            closeCompareModal();
        } else if (detail && detail.style.display !== 'none') {
            closeCityDetail();
        }
    }
});

// Close button handlers
document.addEventListener('DOMContentLoaded', function() {
    var detailClose = document.querySelector('#cityDetailModal .city-modal-close');
    if (detailClose) detailClose.addEventListener('click', closeCityDetail);
    var compareClose = document.querySelector('#cityCompareModal .city-modal-close');
    if (compareClose) compareClose.addEventListener('click', closeCompareModal);

    // Compare bar buttons
    var compareBtn = document.getElementById('compareBtn');
    if (compareBtn) compareBtn.addEventListener('click', openCityComparison);
    var clearBtn = document.getElementById('compareClear');
    if (clearBtn) clearBtn.addEventListener('click', _clearCompareSelection);

    // Phase 6B: Pagination event handlers
    _initPaginationHandlers();

    // #204: Results table sort handlers
    _initTableSortHandlers();

    // Tier system: fetch caps and wire advanced sliders
    fetchTierConfig();
    _initAdvancedSliders();

    // Wire weight slider re-scoring (Phase 4 M1)
    // When weights change, re-calculate Phase 1 scores instantly (no backend call)
    if (window.TransPlanWeights) {
        window.TransPlanWeights.onReScore(function() {
            if (!_currentFormData) return;
            // Update weights in stored form data and re-run scoring
            _currentFormData.weights = window.TransPlanWeights.getWeights();
            calculateResults(_currentFormData);
            // Update methodology donut chart to reflect new weights
            if (window.TransPlanCharts?.updateWeightsDonut) {
                window.TransPlanCharts.updateWeightsDonut();
            }
        });
    }
});

// ==================== M3: Side-by-Side Comparison ====================

function updateCompareBar() {
    var checked = document.querySelectorAll('.compare-check input:checked');
    var bar = document.getElementById('compareBar');
    var countEl = document.getElementById('compareCount');
    var btn = document.getElementById('compareBtn');
    if (!bar) return;

    var count = checked.length;
    bar.style.display = count >= 1 ? 'flex' : 'none';
    countEl.textContent = count + ' selected';
    btn.disabled = count < 2;

    // Disable unchecked boxes when 3 already selected
    var allBoxes = document.querySelectorAll('.compare-check input');
    allBoxes.forEach(function(box) {
        if (!box.checked) {
            box.disabled = count >= 3;
            box.closest('.compare-check').title = count >= 3 ? 'Maximum 3 cities' : 'Add to comparison';
        }
    });
}

function _clearCompareSelection() {
    var allBoxes = document.querySelectorAll('.compare-check input');
    allBoxes.forEach(function(box) {
        box.checked = false;
        box.disabled = false;
    });
    var bar = document.getElementById('compareBar');
    if (bar) bar.style.display = 'none';
}

function openCityComparison() {
    var checked = document.querySelectorAll('.compare-check input:checked');
    var cityNames = [];
    checked.forEach(function(box) { cityNames.push(box.dataset.city); });
    if (cityNames.length < 2) return;

    // Gather data for selected cities
    var cities = cityNames.map(function(name) {
        var phase1 = _currentResults ? _currentResults.find(function(c) { return c.city === name; }) : null;
        var phase2 = _currentSimResult && _currentSimResult.cities
            ? _currentSimResult.cities.find(function(c) { return c.city === name; })
            : null;
        return { name: name, phase1: phase1, phase2: phase2 };
    });

    var modal = document.getElementById('cityCompareModal');
    var body = document.getElementById('compare-body');
    body.innerHTML = '';

    var table = document.createElement('table');
    table.className = 'compare-table';

    // Header row
    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    headerRow.appendChild(_th('Metric'));
    cities.forEach(function(c) {
        var th = _th(c.name);
        var stateText = c.phase1 ? c.phase1.state : (c.phase2 ? c.phase2.state : '');
        th.innerHTML = c.name + '<br><small style="font-weight:normal;color:var(--text-3)">' + stateText + '</small>';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');

    // Phase 1 scores
    if (cities[0].phase1) {
        tbody.appendChild(_sectionRow('Location Scores', cities.length + 1));
        _addCompareRow(tbody, 'Overall Score', cities.map(function(c) {
            return c.phase1 ? c.phase1.personalizedScore.toFixed(1) : '—';
        }), 'max');

        var compareWeights = _getCurrentWeightsInt();
        var catKeys = Object.keys(CATEGORY_LABELS);
        catKeys.forEach(function(key) {
            _addCompareRow(tbody, CATEGORY_LABELS[key] + ' (' + compareWeights[key] + '%)', cities.map(function(c) {
                if (!c.phase1 || !c.phase1.scoreBreakdown) return '—';
                return c.phase1.scoreBreakdown[key] ? c.phase1.scoreBreakdown[key].toFixed(1) : '—';
            }), 'max');
        });
    }

    // Phase 2 probabilities
    if (cities.some(function(c) { return c.phase2; })) {
        tbody.appendChild(_sectionRow('Simulation Probabilities', cities.length + 1));
        _addCompareRow(tbody, 'P(transplant 6 mo)', cities.map(function(c) {
            return c.phase2 ? formatPct(c.phase2.p_transplant_6mo) : '—';
        }), 'max');
        _addCompareRow(tbody, 'P(transplant 12 mo)', cities.map(function(c) {
            return c.phase2 ? formatPct(c.phase2.p_transplant_12mo) : '—';
        }), 'max');
        _addCompareRow(tbody, 'P(transplant 24 mo)', cities.map(function(c) {
            return c.phase2 ? formatPct(c.phase2.p_transplant_24mo) : '—';
        }), 'max');
        _addCompareRow(tbody, 'P(transplant 36 mo)', cities.map(function(c) {
            return c.phase2 ? formatPct(c.phase2.p_transplant_36mo) : '—';
        }), 'max');
        _addCompareRow(tbody, 'Median Wait', cities.map(function(c) {
            return c.phase2 ? c.phase2.median_wait_months.toFixed(1) + ' mo' : '—';
        }), 'min');

        // Competing risks
        if (cities.some(function(c) { return c.phase2 && c.phase2.competing_risks; })) {
            _addCompareRow(tbody, 'P(mortality 24 mo)', cities.map(function(c) {
                return c.phase2 && c.phase2.competing_risks ? formatPct(c.phase2.competing_risks.p_mortality_24mo || 0) : '—';
            }), 'min');
            _addCompareRow(tbody, 'P(delisting 24 mo)', cities.map(function(c) {
                return c.phase2 && c.phase2.competing_risks ? formatPct(c.phase2.competing_risks.p_delisting_24mo || 0) : '—';
            }), 'min');
        }

        // Post-transplant outcomes
        if (cities.some(function(c) { return c.phase2 && c.phase2.outcomes; })) {
            tbody.appendChild(_sectionRow('Post-Transplant Outcomes', cities.length + 1));
            _addCompareRow(tbody, '1yr Graft Survival', cities.map(function(c) {
                return c.phase2 && c.phase2.outcomes && c.phase2.outcomes.graft_survival_1yr != null
                    ? (c.phase2.outcomes.graft_survival_1yr * 100).toFixed(1) + '%' : '—';
            }), 'max');
            _addCompareRow(tbody, 'Overall Success', cities.map(function(c) {
                return c.phase2 && c.phase2.outcomes && c.phase2.outcomes.compound_success != null
                    ? (c.phase2.outcomes.compound_success * 100).toFixed(1) + '%' : '—';
            }), 'max');
        }

        // Historical trends (Phase 4 M3)
        if (cities.some(function(c) { return c.phase2 && c.phase2.trends && c.phase2.trends.overall_direction; })) {
            tbody.appendChild(_sectionRow('Historical Trends', cities.length + 1));
            _addCompareRow(tbody, 'Overall Trend', cities.map(function(c) {
                if (!c.phase2 || !c.phase2.trends) return '—';
                var dir = c.phase2.trends.overall_direction;
                var arrows = { improving: '\u2191 Improving', stable: '\u2192 Stable', declining: '\u2193 Declining' };
                return arrows[dir] || dir || '—';
            }), null);
            _addCompareRow(tbody, 'Wait Time Trend', cities.map(function(c) {
                if (!c.phase2 || !c.phase2.trends || !c.phase2.trends.wait_time_trend) return '—';
                return c.phase2.trends.wait_time_trend.direction || '—';
            }), null);
            _addCompareRow(tbody, 'Volume Trend', cities.map(function(c) {
                if (!c.phase2 || !c.phase2.trends || !c.phase2.trends.volume_trend) return '—';
                return c.phase2.trends.volume_trend.direction || '—';
            }), null);
            _addCompareRow(tbody, 'Graft Survival Trend', cities.map(function(c) {
                if (!c.phase2 || !c.phase2.trends || !c.phase2.trends.graft_survival_trend) return '—';
                return c.phase2.trends.graft_survival_trend.direction || '—';
            }), null);
        }
    }

    table.appendChild(tbody);
    body.appendChild(table);

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function _th(text) {
    var th = document.createElement('th');
    th.textContent = text;
    return th;
}

function _sectionRow(label, colspan) {
    var tr = document.createElement('tr');
    tr.className = 'section-row';
    var td = document.createElement('td');
    td.colSpan = colspan;
    td.textContent = label;
    tr.appendChild(td);
    return tr;
}

function _addCompareRow(tbody, label, values, bestDirection) {
    var tr = document.createElement('tr');
    var labelTd = document.createElement('td');
    labelTd.textContent = label;
    tr.appendChild(labelTd);

    // Find best value index
    var numericValues = values.map(function(v) {
        return parseFloat(v) || 0;
    });
    var bestIdx = -1;
    if (values.some(function(v) { return v !== '—'; })) {
        if (bestDirection === 'max') {
            bestIdx = numericValues.indexOf(Math.max.apply(null, numericValues));
        } else {
            // For 'min', find lowest non-zero
            var filtered = numericValues.map(function(v, i) { return values[i] === '—' ? Infinity : v; });
            bestIdx = filtered.indexOf(Math.min.apply(null, filtered));
        }
    }

    values.forEach(function(val, i) {
        var td = document.createElement('td');
        td.className = 'num';
        td.textContent = val;
        if (i === bestIdx && val !== '—' && values.filter(function(v) { return v !== '—'; }).length > 1) {
            td.classList.add('compare-best');
        }
        tr.appendChild(td);
    });
    tbody.appendChild(tr);
}

// Export for unit tests (Node.js / Jest)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        _parseWaitTimeMonths: _parseWaitTimeMonths,
        _sortResultsArray: _sortResultsArray
    };
}
