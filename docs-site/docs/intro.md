---
sidebar_position: 1
---

# Introduction

TransPlan is a patient-facing clinical decision support tool that helps transplant patients identify the best US cities for their specific organ transplant needs.

## What TransPlan Does

TransPlan analyzes **50+ factors across 8 weighted categories** and scores 22 major US transplant markets. Enter your organ type, blood type, clinical scores, and urgency, and TransPlan produces suitability scores for each city (Phase 1 deterministic), transplant probability estimates at 6, 12, 24, and 36 months (Phase 2 probabilistic), a competing risks breakdown showing the probability of transplant vs. mortality vs. delisting vs. still waiting, and CDF curves showing cumulative probability over time.

## Two Modes of Analysis

### Phase 1: Deterministic Scoring

A rule-based weighted scoring engine that ranks cities by suitability. Fast, transparent, reproducible. Covers all 8 categories including policy, socioeconomic factors, and hospital quality.

### Phase 2: Monte Carlo Simulation

A probabilistic engine running 1,000 simulations per city using log-normal wait time distributions parameterized from SRTR data. Outputs probability distributions with 95% confidence intervals. Also models competing risks (mortality and delisting) using exponential survival models.

## Disclaimer

:::warning Educational Use Only
TransPlan is for educational purposes only. It does not provide medical advice. All outputs should be discussed with your transplant team. Simulated probabilities are estimates based on population-level data and may not reflect your individual clinical situation.
:::

## 22 Covered Cities

Atlanta, Austin, Baltimore, Boston, Charlotte, Chicago, Cleveland, Dallas, Denver, Detroit, Houston, Los Angeles, Miami, Minneapolis, Nashville, New York, Philadelphia, Phoenix, Pittsburgh, Portland, San Francisco, Seattle.

## Quick Navigation

New users should start with [Quick Start](/getting-started/quick-start). To run the app locally, see [Local Setup](/getting-started/local-setup). For the underlying math, read [Scoring Methodology](/theory/scoring-methodology) or [Monte Carlo Simulation](/theory/monte-carlo). To build on or integrate with TransPlan, see the [API Reference](/api-reference/simulate).
