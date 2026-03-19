---
sidebar_position: 1
---

# FAQ

## General

### What is TransPlan?

TransPlan is a patient-facing clinical decision support tool that helps transplant patients explore which US cities might offer better transplant outcomes for their specific clinical profile. It scores 22 cities across 8 categories and models transplant probability distributions using Monte Carlo simulation.

### Is TransPlan medical advice?

**No.** TransPlan is for educational purposes only. It uses population-level statistical models that cannot predict individual outcomes. Always discuss your options with your transplant coordinator and medical team before making any decisions about relocation, multi-listing, or center selection.

### Is my data stored anywhere?

No. TransPlan does not collect, store, or transmit any patient data. The simulation runs locally on your machine, and nothing is sent to a remote server.

### How often is the data updated?

API-sourced data (air quality, hospital quality, cost of living, health demographics) is updated weekly via GitHub Actions. SRTR data (wait time distributions, competing risks) is updated biannually when SRTR publishes new Program-Specific Reports. Manually curated data (climate scores, policy tiers, socioeconomic scores) is updated as needed.

---

## Transplant Terminology

### What is cPRA?

**Calculated Panel Reactive Antibody** is a measure of how sensitized a kidney transplant candidate is to potential donors. It ranges from 0 to 100%. At 0%, the patient is not sensitized and will accept most donors. At 80% or above, the patient is highly sensitized and needs a rare compatible donor, which significantly extends wait time. At 99% or above, very few compatible donors exist.

High cPRA dramatically increases wait time for kidney transplants.

### What is MELD score?

**Model for End-Stage Liver Disease** is a score from 6 to 40 measuring the severity of chronic liver disease, used to prioritize liver allocation. Scores of 6 to 14 indicate the lowest urgency. Scores of 15 to 24 indicate moderate urgency and trigger expedited allocation. Scores of 25 to 35 indicate high urgency with significant 6-month mortality risk. Scores above 35 trigger emergency allocation priority.

Higher MELD means shorter expected wait time because allocation priority increases, but also higher mortality risk while waiting.

### What is LAS?

**Lung Allocation Score** is a score from 0 to 100 that prioritizes lung transplant candidates based on their medical urgency and expected post-transplant benefit. Higher LAS means higher priority and shorter expected wait.

### What is a competing risk?

A competing risk is an event that prevents the primary outcome from occurring. For transplant patients, the possible outcomes are receiving a transplant (the desired outcome), dying while waiting (a competing event), or being delisted due to a clinical change (another competing event).

Because these events compete with each other, calculating their probabilities correctly requires competing risks analysis rather than standard survival analysis. TransPlan ensures all four outcomes (transplant, mortality, delisting, and still waiting) sum to 100%.

### What does "OPO" mean?

**Organ Procurement Organization** is a nonprofit organization designated by HRSA to coordinate organ donation within a geographic region. OPOs are responsible for recovering organs from deceased donors, coordinating with transplant centers, and promoting organ donation in their community.

---

## Technical

### Why does Phase 2 sometimes not show up?

Phase 2 (Monte Carlo simulation) and equity analysis require the local Python backend to be running. If you are using TransPlan directly via `simulator.html` without the launcher, the backend will not be available. Use `TransPlan.app` or `start.command` to launch the full stack.

### Why are the confidence intervals sometimes wide?

Wide 95% confidence intervals indicate high uncertainty. This usually happens because the blood type is rare (few historical SRTR observations), the cPRA is very high (a sparse region of the model), or the organ type has low volume at that city.

### Can I use TransPlan for multiple listing?

Multiple listing (being listed at multiple transplant centers simultaneously) is permitted under UNOS policy. TransPlan can help you identify which additional cities might offer better wait time prospects, but the actual decision to pursue multiple listing must involve your transplant team and considers many factors not modeled here, such as travel logistics and insurance coverage at other centers.

### How do I run TransPlan without internet?

Phase 1 (scoring) works entirely offline. Data is pre-loaded as JSON files in the repo. Phase 2 (simulation) requires the local backend but no internet connection. The data files are committed to the repository and load from `localhost`.

### What's the difference between Phase 1 and Phase 2?

Phase 1 is a deterministic scoring engine that runs instantly in the browser, producing relative rankings from 0 to 100 with no uncertainty quantification and no backend requirement. Phase 2 is a probabilistic simulation engine that runs in roughly 100ms on the backend, producing probability estimates at each time horizon with 95% confidence intervals. Phase 2 requires the Python backend to be running.

### What is the Home Center feature?

The Home Center dropdown lets you select your current transplant listing center (city). When set, the results show comparison badges on each city card indicating the score or probability difference compared to your home center. A green "H" marker appears on the map. This helps answer the question: "Would I benefit from relisting at a different center?"

### What is the COD multiplier?

The **Cause of Death (COD) multiplier** adjusts donor availability estimates based on regional cause-of-death patterns. Different regions have different proportions of motor vehicle accidents, strokes, and other causes of death that produce transplantable organs for specific organ types. Enabling this toggle applies these regional differences to the simulation. It is based on published recovery rate data and CDC WONDER state-level statistics.

### What is the Equity Analysis tab?

The equity analysis evaluates fairness across a 48-profile demographic matrix (8 blood types by 3 age brackets by 2 sexes). For each city, it computes a Gini coefficient measuring outcome equality and shows charts comparing disparities by blood type and age bracket. Race, ethnicity, and insurance status are deliberately not modeled.

---

## Limitations

For a complete list of known data quality issues and model limitations, see [Limitations](/about/limitations).

The most important limitations to be aware of are that data is 6 to 18 months old because SRTR publishes biannually, that city-level models average across multiple centers so individual center variation is not captured, that clinical status changes over time (rising MELD, changing cPRA) are not modeled, that OPO geographic boundaries are not modeled so results are city-level only, and that the equity analysis does not include race/ethnicity or insurance status by design.
