# TransPlan: Software Requirements Specification (SRS) and Development Roadmap

**Version 1.2 (Merged and Clinical-Focused Draft)**  
**Prepared by:** 🇦🇶 rivir yona (@rivirside)  
**Date:** March 02, 2026  
**Project Type:** Open-source patient-facing clinical decision support software (CDSS) for transplant center optimization and relocation modeling  
**Scope:** Probabilistic forecasting, center comparisons, relocation scenarios, and equity analysis in organ transplantation, with a path to FDA validation as Software as a Medical Device (SaMD)  
**Disclaimer:** In its initial open-source form, TransPlan is educational and exploratory. It does not provide medical advice or guarantees. For eventual clinical use, it will undergo rigorous validation to support informed patient decisions in consultation with transplant professionals. All outputs emphasize consultation with licensed providers.

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) merges and expands on prior drafts to outline the functional, non-functional, architectural, governance, ethical, regulatory, and sustainability requirements for TransPlan—a patient-facing CDSS designed to help users explore transplant center options, including relocation scenarios for improved probabilities of success. Using public datasets (e.g., SRTR, UNOS, CDC), the tool generates personalized probabilistic estimates (e.g., time-to-transplant distributions via Monte Carlo simulations) and ranked lists of states/areas/centers.

Primary goals:
- Empower patients to evaluate geographic and center-based options (e.g., "If relocating to State X, your simulated P(transplant <2 years) increases by Y%").
- Facilitate research and policy simulations.
- Promote equity by highlighting disparities and barriers.
- Evolve from open-source educational tool to FDA-cleared SaMD (likely Class II via 510(k) pathway), providing evidence-based insights for clinical discussions.

TransPlan is intended for:
- Patients/families exploring listing/multiple listing/relocation options.
- Clinicians as a supplemental decision aid.
- Researchers for system-level modeling.

It is **not** intended for:
- Direct clinical recommendations without provider oversight.
- Handling PHI or real-time data until validated.
- Commodifying allocation (e.g., no "gaming" framing).

This document serves as a blueprint for development, GitHub docs, grant proposals (e.g., NIH SBIR, HRSA), and FDA pre-submissions.

### 1.2 Scope
TransPlan will provide:
- Web-based dashboard for user inputs, simulations, and ranked relocation outputs.
- Probabilistic engines for wait times, outcomes, and scenarios.
- Equity-focused analyses and visualizations.
- Open-source code for community contributions.
- Exportable reports for clinical/research use.
- Path to FDA clearance: Validation studies up to RCT demonstrating improved decision quality/safety.

Out of Scope (initially):
- EHR integration (post-FDA).
- Mobile app (focus on responsive web/PWA).
- International data (US-focused first).

### 1.3 Definitions and Acronyms
- **cPRA**: Calculated Panel Reactive Antibody.
- **MELD**: Model for End-Stage Liver Disease.
- **LAS**: Lung Allocation Score.
- **SRTR**: Scientific Registry of Transplant Recipients.
- **UNOS/OPTN**: United Network for Organ Sharing/Organ Procurement and Transplantation Network.
- **Monte Carlo Simulation**: Stochastic method for probability distributions.
- **SaMD**: Software as a Medical Device (FDA term).
- **CDSS**: Clinical Decision Support Software.
- **PHI**: Protected Health Information (HIPAA).
- **RCT**: Randomized Controlled Trial.
- **510(k)**: FDA premarket notification pathway for substantial equivalence.

### 1.4 References
- SRTR Public Datasets: srtr.org (tools like Kidney Waiting Times Calculator provide baselines but lack relocation simulations).
- UNOS Policies: unos.org.
- OPTN Ethics: optn.transplant.hrsa.gov (emphasizes equity in allocation).
- FDA CDSS Guidance (2022, updated): Criteria for non-device vs. SaMD; requires studies for validation (e.g., RCTs for efficacy).
- IPDAS Standards: ipdas.ohri.ca (for decision aids).
- Examples: iChoose Kidney (similar wait-time tool, not FDA-cleared); IDx-DR (AI diagnostic via 510(k)).

### 1.5 Assumptions and Dependencies
- Public datasets remain accessible (e.g., SRTR quarterly).
- Users consult providers; tool includes prompts.
- Phoenix, AZ location enables local pilots (e.g., Mayo Clinic Phoenix).
- FDA classification: Likely device CDSS (patient-facing probabilistic insights); aim for 510(k) with predicates like SRTR tools.

---

## 2. System Overview
TransPlan is a modular platform with a focus on patient relocation modeling for transplant probabilities.

### 2.1 High-Level Architecture
- **Frontend**: Interactive UI for inputs/outputs (e.g., ranked relocation lists).
- **Backend**: Python engine for simulations.
- **Data Layer**: Local/static files for SRTR data.
- **Deployment**: Docker for local/offline; cloud for web (e.g., AWS).
- **Integration**: Public APIs (SRTR); no user data outbound.

### 2.2 User Roles
- **Patient/User**: Inputs profile, views ranked probabilities/relocations.
- **Clinician**: Uses in consultations (post-FDA).
- **Researcher**: Configures advanced scenarios.
- **Contributor**: Submits PRs.
- **Maintainer**: Manages releases/validation.

### 2.3 Use Cases
- **UC-1: Relocation Simulation**: User inputs profile; views ranked states/areas by P(success), with visuals.
- **UC-2: Center Comparison**: Drill-down to centers in top areas.
- **UC-3: Clinical Export**: Generate report for provider discussion.
- **UC-4: Research Scenario**: Toggle policies for system impacts.

---

## 3. Functional Requirements
Each includes priority, acceptance criteria, dependencies. Emphasize relocation flow.

### 3.1 User Profile Input Module
**FR-1: Input Collection** (High)  
Support organ, age, blood type, cPRA, MELD/LAS, comorbidities, current ZIP/state, relocation prefs (e.g., max distance).  
*Acceptance*: Validates; defaults aggregates.  
*Dependencies*: Pydantic.

**FR-2: Input Validation** (High)  
Real-time checks; errors (e.g., invalid MELD).  
*Acceptance*: 100% test coverage.

### 3.2 Scoring and Modeling Engine
**FR-3: Multi-Factor Scoring** (High)  
Scores (0–100) across categories; personalized for profile.  
*Acceptance*: Reproducible; example calculations.

**FR-4: Configurable Weights** (Medium)  
Editable for research; locked for patient use.  
*Acceptance*: Changes audited.

**FR-5: Monte Carlo Simulation** (High)  
1,000+ iterations for distributions; adjust for relocation.  
*Acceptance*: <5s; matches SRTR benchmarks.

**FR-6: Competing Risks** (High)  
P(transplant) vs. mortality/delisting; relocation variants.  
*Acceptance*: Validated retrospectively.

**FR-7: Probability Outputs** (High)  
P(transplant ≤X months) with CIs; ranked by boost vs. current.  
*Acceptance*: Visual curves.

### 3.3 Relocation and Policy Features
**FR-8: Relocation Modeling** (High)  
Rank states/DSAs/centers by probability; integrate costs (housing/travel APIs).  
*Acceptance*: Table with ranks, boosts, notes (e.g., barriers).

**FR-9: Policy Toggles** (Medium)  
Simulate donor rates/sharing; impact on probabilities.  
*Acceptance*: Side-by-side comparisons.

### 3.4 Equity Analysis
**FR-10: Stratification** (High)  
By demographics/SES; flag disparities in relocations.  
*Acceptance*: Gini/Theil indices.

**FR-11: Equity Metrics** (High)  
Alerts for high-inequity scenarios.  
*Acceptance*: Integrated reports.

### 3.5 Visualization and Outputs
**FR-12: Ranked Display** (High)  
Sortable tables/maps for relocations.  
*Acceptance*: Interactive.

**FR-13: Mapping** (Medium)  
US heatmaps for probabilities.  
*Acceptance*: Tooltips.

**FR-14: Curves** (High)  
D3.js for distributions.  
*Acceptance*: Exportable.

### 3.6 Data and API
**FR-15: Data Docs** (High)  
Metadata/citations.  
*Acceptance*: UI footer.

**FR-16: Versioning** (High)  
Git for data/models.  
*Acceptance*: Outputs reference versions.

**FR-17: Ingestion** (Medium)  
Quarterly SRTR pulls.  
*Acceptance*: CI/CD.

**FR-18: API** (Medium)  
For research; rate-limited.  
*Acceptance*: Swagger.

**FR-19: Formats** (Medium)  
CSV/JSON/PDF.  
*Acceptance*: Validated.

**FR-20: Reports** (High)  
PDF with disclaimers/sources.  
*Acceptance*: Watermarked.

---

## 4. Non-Functional Requirements
### 4.1 Transparency
Document assumptions; explainable outputs (Criterion 4 for FDA Non-Device).

### 4.2 Reproducibility
Seeds for RNG; containerized.

### 4.3 Performance
<5s sims; scalable.

### 4.4 Security/Privacy
Local processing; no PHI (align with HIPAA/FDA).

### 4.5 Accessibility
WCAG 2.1 AA; multilingual.

### 4.6 Reliability
99% uptime; backups.

### 4.7 Ethical Constraints
Disclaimers; bias audits; no "gaming" language.

### 4.8 Usability
Wizard UI; tutorials.

### 4.9 Regulatory (New)
- FDA QMS (21 CFR 820); risk management (ISO 14971).
- Validation: Studies for safety/efficacy.
- Classification: Seek Q-sub for Non-Device; else 510(k) with predicates (e.g., SRTR tools).

---

## 5. Architecture Requirements
- **Backend**: FastAPI/Python; NumPy/SciPy/PyMC/Lifelines.
- **Frontend**: Next.js/React; D3/Leaflet.
- **Data**: PostgreSQL/Git LFS.
- **Interfaces**: Responsive; API versioning.
- **Deployment**: GitHub Actions; Vercel/AWS.
- **Workflow & Jobs**: Celery/RQ/Temporal worker tier for Monte Carlo runs plus Dagster/Prefect pipelines for scheduled ingests and validations.
- **Schema Management**: Typed domain models (SQLModel/Pydantic) with Alembic migrations and seeded fixtures to guarantee reproducibility.
- **Infrastructure**: Terraform/Pulumi modules for cloud resources, centralized logging/metrics (OpenTelemetry, Loki/Prometheus), and automated compliance checks.
- **Frontend Tooling**: TypeScript-first Next.js setup with shared design system (e.g., Radix/Chakra theme), WCAG-compliant components, localization pipeline, and end-to-end tests (Playwright).

### 5.1 Deployment Pathways
To handle potential PHI while preserving an open-source path, TransPlan supports two deployment modes:

1. **Local/Offline Mode (default educational build)**  
   - Runs entirely in-browser or via a desktop/PWA package.  
   - Fetches only public datasets; never transmits user-entered health history to a server.  
   - Saves optional exports locally so patients can choose whether to share with clinicians.  
   - Requires deterministic bundles (no remote logging) and a documented threat model, but remains outside HIPAA scope because no identifiers leave the device.

2. **HIPAA-Compliant Cloud Mode (clinical pilots)**  
   - Hosted with signed BAAs (e.g., AWS HITRUST, Aptible, hospital-owned infra).  
   - Enforces encryption in transit/at rest, strict IAM, audit logging, backups, breach notification, and QMS-aligned change control.  
   - Separates PHI services (profile intake, report storage) from de-identified modeling services via message queues or data clean rooms.  
   - Requires deployment automation (Terraform/Pulumi), security scanning, and documentation for FDA submissions.

The roadmap should keep both modes buildable from the same codebase by using feature flags/environment configs: community builds default to offline processing, while BAA-backed instances enable server persistence and integrations once compliance controls are in place.

---

## 6. Governance Requirements
- PR process; Code of Conduct.
- Releases: Quarterly.
- Decision: Maintainer + community.

---

## 7. Documentation Requirements
- README/ROADMAP/CONTRIBUTING.
- Tech docs: Jupyter for models.
- User guides: Ethical/FDA paths.

---

## 8. Donation & Sustainability Requirements
- GitHub Sponsors/Patreon.
- Transparency: Annual reports.
- No paywalls; grants for validation.

---

## 9. Testing Requirements
- Unit/Integration: 80% coverage (Pytest).
- Usability: Beta testing.
- Validation: Retrospective (Brier <0.2); bias audits.
- Clinical: Per FDA (e.g., RCTs for outcomes).

---

## 10. Risk Assessment
- Ethical: Disparities—mitigate with audits.
- Regulatory: Reclassification—early FDA dialogue.
- Technical: Data staleness—auto-updates.
- Adoption: Outreach via @rivirside; local (Mayo Phoenix).

---

## 11. Future Enhancements
- EHR integration (post-FDA).
- ML for advanced risks.
- International expansion.

---

## 12. Success Criteria
- Adoption: 1k+ stars; 100+ users.
- Validation: RCT publication; FDA clearance.
- Impact: Improved patient decisions; equity insights.

---

## 13. Development Roadmap
Phased, 3–5 years total (part-time; accelerate with grants). Phoenix location aids pilots (e.g., Mayo Clinic).

### Phase 1: MVP Development & Internal Validation (Months 1–6)
- Focus: Core inputs, scoring, basic relocation ranking.
- Milestones: v1.0 on transplan.org; internal tests.
- Effort: 200–400 hours; $5k.
- FDA: Document QMS.

### Phase 2: Probabilistic & Relocation Enhancements (Months 7–12)
- Focus: Monte Carlo; ranked probabilities.
- Milestones: v2.0; retrospective validation.
- Effort: 300–500 hours; $10k–20k (stats consult).
- FDA: Risk analysis.

### Phase 3: Equity, Usability, & Observational Studies (Months 13–24)
- Focus: Stratification; pilots.
- Milestones: Usability study (n=50); observational (n=100).
- Effort: 400–600 hours; $50k–100k (IRB/grants).
- FDA: Q-submission for classification.

### Phase 4: Advanced Features & RCT (Months 25–36)
- Focus: Policy sims; full relocation modeling.
- Milestones: RCT (n=200–500); publications.
- Effort: 500+ hours; $200k+ (NIH grants).
- FDA: 510(k) submission with evidence.

### Phase 5: FDA Clearance & Scaling (Months 37+)
- Focus: Iterations; integrations.
- Milestones: Clearance; endorsements (e.g., OPTN).
- Effort: Ongoing; community/funding-driven.
- Success: Widespread clinical use.

**Contingencies**: Delays—fallback to educational mode. Review quarterly.

If needed, format for GitHub, add diagrams, or refine based on Phoenix resources!
