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

// M5: Expose results for export module
window.TransPlanResults = {
    getResults: function() { return _currentResults; },
    getSimResult: function() { return _currentSimResult; },
    getFormData: function() { return _currentFormData; },
    getEquityResult: function() { return _currentEquityResult; }
};

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

// Initialize map
function initializeMap() {
    if (!window.TransPlanCDN?.leaflet) {
        const mapEl = document.getElementById('map');
        if (mapEl) {
            const notice = document.createElement('div');
            notice.className = 'cdn-fallback-notice';
            const p = document.createElement('p');
            const strong = document.createElement('strong');
            strong.textContent = 'Map unavailable';
            p.appendChild(strong);
            p.appendChild(document.createTextNode(' \u2014 the mapping library could not be loaded. Your city rankings and scores are still displayed below.'));
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
    cityMarkersLayer = L.layerGroup().addTo(map);

    // Create layer controls
    setupLayerControls();

    // Initialize default layers
    createTrafficAccidentHeatmap();
    createTransplantCentersLayer();
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

    const transplantCenters = [
        // Tier 1: Very High Volume Centers
        { name: "UPMC", city: "Pittsburgh", state: "PA", coord: [40.4406, -79.9959], volume: "Very High", annualTransplants: 450, specialties: "All organs, pioneered liver & intestine" },
        { name: "Mayo Clinic", city: "Rochester", state: "MN", coord: [44.0121, -92.4802], volume: "Very High", annualTransplants: 420, specialties: "All organs, integrated care" },
        { name: "Cleveland Clinic", city: "Cleveland", state: "OH", coord: [41.4993, -81.6944], volume: "Very High", annualTransplants: 465, specialties: "Heart leader, all organs" },
        { name: "UCLA Medical Center", city: "Los Angeles", state: "CA", coord: [34.0522, -118.2437], volume: "Very High", annualTransplants: 438, specialties: "Liver, kidney, multi-organ" },
        { name: "Johns Hopkins", city: "Baltimore", state: "MD", coord: [39.2904, -76.6122], volume: "Very High", annualTransplants: 425, specialties: "All organs, research leader" },
        { name: "Duke University Hospital", city: "Durham", state: "NC", coord: [35.9940, -78.8986], volume: "Very High", annualTransplants: 410, specialties: "Lung leader, heart, all organs" },

        // Tier 2: High Volume Centers
        { name: "UCSF Medical Center", city: "San Francisco", state: "CA", coord: [37.7749, -122.4194], volume: "High", annualTransplants: 385, specialties: "Liver excellence, all organs" },
        { name: "Vanderbilt", city: "Nashville", state: "TN", coord: [36.1627, -86.7816], volume: "High", annualTransplants: 360, specialties: "Heart, lung, kidney" },
        { name: "UW Health", city: "Madison", state: "WI", coord: [43.0731, -89.4012], volume: "High", annualTransplants: 345, specialties: "Kidney, pancreas leader" },
        { name: "University of Minnesota", city: "Minneapolis", state: "MN", coord: [44.9778, -93.2650], volume: "High", annualTransplants: 370, specialties: "Pancreas pioneer, kidney" },
        { name: "Northwestern Medicine", city: "Chicago", state: "IL", coord: [41.8781, -87.6298], volume: "High", annualTransplants: 355, specialties: "Kidney, liver, pancreas" },
        { name: "Stanford Hospital", city: "Palo Alto", state: "CA", coord: [37.4419, -122.1430], volume: "High", annualTransplants: 340, specialties: "Heart, lung, innovation" },
        { name: "Texas Heart Institute", city: "Houston", state: "TX", coord: [29.7604, -95.3698], volume: "High", annualTransplants: 368, specialties: "Heart leader, multi-organ" },
        { name: "Penn Medicine", city: "Philadelphia", state: "PA", coord: [39.9526, -75.1652], volume: "High", annualTransplants: 350, specialties: "All organs, research" },

        // Tier 3: Moderate Volume Centers
        { name: "Baylor University Medical Center", city: "Dallas", state: "TX", coord: [32.7767, -96.7970], volume: "Moderate", annualTransplants: 285, specialties: "Liver, kidney" },
        { name: "Nebraska Medicine", city: "Omaha", state: "NE", coord: [41.2565, -95.9345], volume: "Moderate", annualTransplants: 240, specialties: "Intestine, multi-organ" },
        { name: "University of Miami", city: "Miami", state: "FL", coord: [25.7617, -80.1918], volume: "Moderate", annualTransplants: 265, specialties: "Kidney, pancreas, liver" },
        { name: "Indiana University Health", city: "Indianapolis", state: "IN", coord: [39.7684, -86.1581], volume: "Moderate", annualTransplants: 255, specialties: "Kidney, liver" },
        { name: "Barnes-Jewish Hospital", city: "St. Louis", state: "MO", coord: [38.6270, -90.1994], volume: "High", annualTransplants: 335, specialties: "Lung, all organs" },
        { name: "University of Washington", city: "Seattle", state: "WA", coord: [47.6062, -122.3321], volume: "High", annualTransplants: 330, specialties: "Lung, kidney, liver" },
        { name: "Emory University Hospital", city: "Atlanta", state: "GA", coord: [33.7490, -84.3880], volume: "High", annualTransplants: 315, specialties: "Liver, kidney, heart" },
        { name: "University of Colorado", city: "Denver", state: "CO", coord: [39.7392, -104.9903], volume: "Moderate", annualTransplants: 290, specialties: "Kidney, liver, lung" },
        { name: "NYU Langone", city: "New York", state: "NY", coord: [40.7128, -74.0060], volume: "High", annualTransplants: 340, specialties: "Liver, kidney, heart" },
        { name: "Mount Sinai", city: "New York", state: "NY", coord: [40.7895, -73.9535], volume: "High", annualTransplants: 325, specialties: "Liver excellence, kidney" }
    ];

    transplantCenters.forEach(center => {
        // Size and color based on volume
        let size, color, borderColor;
        if (center.volume === "Very High") {
            size = 18;
            color = '#e74c3c';
            borderColor = '#c0392b';
        } else if (center.volume === "High") {
            size = 14;
            color = '#3498db';
            borderColor = '#2980b9';
        } else {
            size = 10;
            color = '#2ecc71';
            borderColor = '#27ae60';
        }

        const icon = L.divIcon({
            className: 'transplant-center-marker',
            html: `<div style="
                background: ${color};
                width: ${size}px;
                height: ${size}px;
                border-radius: 50%;
                border: 3px solid ${borderColor};
                box-shadow: 0 3px 8px rgba(0,0,0,0.4);
                position: relative;
            ">
                <div style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: ${size - 6}px;
                    height: ${size - 6}px;
                    background: white;
                    border-radius: 50%;
                    opacity: 0.3;
                "></div>
            </div>`,
            iconSize: [size + 6, size + 6]
        });

        L.marker(center.coord, { icon: icon })
            .bindPopup(`
                <div style="min-width: 200px;">
                    <strong style="font-size: 1.1em; color: ${color};">${center.name}</strong><br>
                    <em>${center.city}, ${center.state}</em><br>
                    <hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;">
                    <strong>Volume:</strong> ${center.volume}<br>
                    <strong>Annual Transplants:</strong> ~${center.annualTransplants}<br>
                    <strong>Specialties:</strong><br>
                    <em style="font-size: 0.9em;">${center.specialties}</em>
                </div>
            `)
            .addTo(transplantCentersLayer);
    });

    // Add legend
    const legend = L.control({ position: 'topright' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = `
            <h4>Transplant Centers</h4>
            <div class="legend-item">
                <div style="width: 18px; height: 18px; background: #e74c3c; border: 2px solid #c0392b; border-radius: 50%;"></div>
                <span>Very High Volume (&gt;400/yr)</span>
            </div>
            <div class="legend-item">
                <div style="width: 14px; height: 14px; background: #3498db; border: 2px solid #2980b9; border-radius: 50%;"></div>
                <span>High Volume (300-400/yr)</span>
            </div>
            <div class="legend-item">
                <div style="width: 10px; height: 10px; background: #2ecc71; border: 2px solid #27ae60; border-radius: 50%;"></div>
                <span>Moderate Volume (&lt;300/yr)</span>
            </div>
        `;
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

// Update map with ranked cities
function updateMapWithResults(cities, homeCenterCity) {
    cityMarkersLayer.clearLayers();

    cities.forEach((city, index) => {
        const rank = index + 1;
        const coord = cityCoordinates[city.city];
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

            const popupPrefix = isHome ? '<strong>Your Center</strong><br>' : '';
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

// Populate Home Center dropdown from cityStateMap
(function populateHomeCenterDropdown() {
    const select = document.getElementById('homeCenter');
    if (!select) return;
    Object.entries(cityStateMap)
        .sort(([a], [b]) => a.localeCompare(b))
        .forEach(([city, state]) => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city + ', ' + (stateAbbreviations[state] || state);
            select.appendChild(option);
        });
})();

document.getElementById('transplantForm').addEventListener('submit', async function(e) {
    e.preventDefault();

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
        las: parseInt(document.getElementById('las')?.value) || 0,
        homeCenter: document.getElementById('homeCenter')?.value || '',
        adjustForCauseOfDeath: document.getElementById('adjustCauseOfDeath')?.checked || false,
        weights: window.TransPlanWeights?.getWeights() || null
    };

    // Show loading spinner
    const spinner = document.getElementById('simulationSpinner');
    if (spinner) spinner.style.display = 'flex';

    // Load data before calculating
    if (typeof loadAllData === 'function' && !window.TransPlanData?._loaded) {
        await loadAllData();
    }

    // Phase 1: Calculate deterministic scores
    calculateResults(formData);

    // Phase 2: Call backend for Monte Carlo simulation
    let simResult = null;
    let equityResult = null;
    if (window.TransPlanAPI) {
        simResult = await window.TransPlanAPI.simulate(formData);
        // M4: Run equity analysis in parallel with the spinner still visible
        if (simResult) {
            equityResult = await window.TransPlanAPI.equityAnalysis(formData);
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

    // --- Wait Time (derived from algorithm's wait time factors) ---
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
    const base = baseWaitTimes[organType] || baseWaitTimes.kidney;
    const avgWait = (base.min + base.max) / 2;
    const cityFactor = cityWaitTimeFactors[cityName] || 1.0;
    const cityWait = avgWait * cityFactor;

    // Organ-specific wait multiplier (mirrors algorithm.js logic)
    let waitMultiplier;
    if (organType === 'kidney' && typeof formData === 'object' && formData.cpra > 0) {
        const cpra = Number(formData.cpra);
        if (cpra <= 20) waitMultiplier = 1.0;
        else if (cpra <= 50) waitMultiplier = 1.0 + (cpra - 20) / 30 * 0.5;
        else if (cpra <= 80) waitMultiplier = 1.5 + (cpra - 50) / 30 * 1.0;
        else if (cpra <= 97) waitMultiplier = 2.5 + (cpra - 80) / 17 * 0.5;
        else waitMultiplier = 3.0 + (cpra - 97) / 3 * 2.0;
    } else if (organType === 'liver' && typeof formData === 'object' && formData.meld) {
        const meld = Number(formData.meld);
        if (meld >= 35) waitMultiplier = 0.15;
        else if (meld >= 25) waitMultiplier = 0.4;
        else if (meld >= 15) waitMultiplier = 1.0;
        else waitMultiplier = 2.0;
    } else if (organType === 'lung' && typeof formData === 'object' && formData.las) {
        const las = Number(formData.las);
        if (las >= 50) waitMultiplier = 0.3;
        else if (las >= 35) waitMultiplier = 0.7;
        else waitMultiplier = 1.2;
    } else {
        const urgencyFactors = { '1': 0.3, '2': 0.6, '3': 1.0, '4': 1.4 };
        waitMultiplier = urgencyFactors[urgency] || 1.0;
    }

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

function calculateResults(formData) {
    const organ = formData.organ;

    // Use comprehensive algorithm to dynamically score all cities
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
    } else {
        // Fallback to mock data with simple multipliers
        const cities = JSON.parse(JSON.stringify(cityData[organ]));
        const bloodMultiplier = bloodTypeMultipliers[formData.bloodType];
        const ageMultiplier = getAgeMultiplier(formData.age);
        const sexMultiplier = sexMultipliers[formData.sex];
        const urgencyMultiplier = urgencyMultipliers[formData.urgency];

        cities.forEach(city => {
            const baseScore = city.score;
            city.personalizedScore = baseScore * bloodMultiplier * ageMultiplier * sexMultiplier * urgencyMultiplier;
            city.personalizedScore = Math.min(100, city.personalizedScore);
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
        warningEl.innerHTML = '<strong>Important:</strong> Status 1 (critical) patients are typically too medically urgent for relocation planning. These results may not be actionable for your situation. Please discuss any decisions with your transplant team immediately.';
        warningEl.style.display = 'block';
    } else {
        warningEl.style.display = 'none';
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

    cities.forEach((city, index) => {
        const rank = index + 1;
        const card = createCityCard(city, rank, formData, homeCenter);
        resultsContainer.appendChild(card);
    });

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Render comparison bar chart
    setTimeout(() => {
        if (window.TransPlanCharts) {
            window.TransPlanCharts.createComparisonChart(cities);
        }
    }, 200);
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
        comparisonHtml = '<div class="comparison-badge comparison-home">Your Center</div>';
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
        </div>

        ${city.scoreBreakdown ? `
        <div class="radar-chart-container">
            <h4>Score Breakdown</h4>
            <canvas id="${radarId}"></canvas>
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

    // Render radar chart after card is in DOM
    if (city.scoreBreakdown) {
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
    const unit = waitTime.includes('month') ? 'months' : 'years';

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

    // Simulation metadata
    const meta = document.createElement('div');
    meta.className = 'simulation-meta';
    meta.textContent = 'Monte Carlo simulation: ' + simResult.iterations.toLocaleString() +
        ' iterations in ' + simResult.elapsed_seconds.toFixed(2) + 's';
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
            compDiv.textContent = 'Your Center';
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

    // CI text
    card.appendChild(_el('div', 'prob-ci',
        '95% CI at 24 mo: ' + formatPct(ci[0]) + ' \u2013 ' + formatPct(ci[1])));

    // Competing risks bar
    if (city.competing_risks) {
        card.appendChild(buildRiskBar(city.competing_risks));
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

const CATEGORY_WEIGHTS = {
    medicalCompatibility: 25,
    waitTime: 20,
    donorAvailability: 18,
    hospitalQuality: 15,
    geographic: 10,
    healthDemographics: 7,
    policy: 3,
    socioeconomic: 2
};

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
        var keys = Object.keys(CATEGORY_LABELS);
        keys.forEach(function(key) {
            var raw = city.scoreBreakdown[key] || 0;
            var weight = CATEGORY_WEIGHTS[key] || 0;
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

        // 95% CI
        var ci = simCity.confidence_interval_95 || [0, 0];
        var ciDiv = document.createElement('div');
        ciDiv.style.marginTop = 'var(--space-3)';
        ciDiv.style.fontSize = 'var(--fs-sm)';
        ciDiv.style.color = 'var(--text-3)';
        ciDiv.textContent = '95% CI at 24 mo: ' + formatPct(ci[0]) + ' \u2013 ' + formatPct(ci[1]);
        probSection.appendChild(ciDiv);

        body.appendChild(probSection);

        // Competing risks
        if (simCity.competing_risks) {
            var riskSection = _modalSection('24-Month Waitlist Outcomes');
            riskSection.appendChild(buildRiskBar(simCity.competing_risks));
            body.appendChild(riskSection);
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

function closeCityDetail() {
    var modal = document.getElementById('cityDetailModal');
    modal.style.display = 'none';
    document.body.style.overflow = '';
    // Destroy radar chart if any
    if (window.TransPlanCharts && window.TransPlanCharts.destroyChart) {
        window.TransPlanCharts.destroyChart('modal-radar-chart');
    }
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

        var catKeys = Object.keys(CATEGORY_LABELS);
        catKeys.forEach(function(key) {
            _addCompareRow(tbody, CATEGORY_LABELS[key] + ' (' + CATEGORY_WEIGHTS[key] + '%)', cities.map(function(c) {
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
