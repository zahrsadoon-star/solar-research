# S1 related work - arXiv scan via alphaXiv (2026-10-21)

Saved in Zaher's alphaXiv library, folder "S1 Grid-outage forecasting (Baghdad)".
arXiv IDs are verified identifiers; journal versions (if any) still to check before citing.

## Closest to S1
- **Essus, Vatsavai, Rachunok (2026), "Data Leakage Inflates Generalizability of Power Outage Prediction Models"**,
  arXiv:2608.24665. US East Coast 2018-2023, weather-driven outages. Random train/test splits give strong scores that
  are inflated by spatial and temporal autocorrelation; under spatial/temporal/event hold-outs models often fail to beat
  a null baseline. -> Directly supports our point that the thesis's random 20 %-per-month split leaks, and warns that
  climatology / persistence baselines must be taken seriously.
- **Enyam, Koepele, Asare, Wallington, Lygeros (2026), "Scenario-Based Stochastic MPC for Energy Hubs with EV Fleets
  Under Persistent Grid Outages"**, arXiv:2604.18268. Ghana campus hub; outages from a 2-state continuous-time Markov
  chain whose rates come from **resident surveys**; stochastic MPC within 0.39 % of perfect-forecast cost, while an
  outage-unaware MPC is no better than rule-based control. -> Shows outage awareness pays, but uses only a simple
  Markov model with survey-estimated rates.
- **(2026) "Transfer Learning with Conformalized Quantile Regression for Solar PV Forecasting Under
  Load-Shedding-Driven Data Scarcity"**, arXiv:2609.26959 (Bangladesh). Load shedding as a data problem for PV
  forecasting, not as the forecast target.

## Context (different outage type)
- OutageDiT generative outage scenarios, arXiv:2609.01896; spatio-temporal conformal prediction for outage data,
  arXiv:2411.17099; GNN outage prediction, arXiv:2604.04916; tropical-cyclone outages, arXiv:2512.06644 - all
  **weather/extreme-event outages at county/tract level**, not chronic supply-deficit load shedding at a household.
- Decision-focused learning for battery scheduling under PV/load uncertainty, arXiv:2610.14782 (forecast quality vs
  decision quality - relevant to RQ3).

## Evaluation methodology
- Time-series validation trade-offs (sufficiency / coverage / causality), arXiv:2609.29530.
- Leakage in time-series foundation-model evaluation, arXiv:2510.13654.
- Conformal prediction for time series - methods and benchmark, arXiv:2601.18509.
- TFB fair forecasting benchmark, arXiv:2403.20150.

## What this changes in S1
1. **Gap is sharper:** arXiv outage-prediction work targets weather-driven, region-level outages. Forecasting
   **chronic, supply-deficit load shedding at household level from a measured record** is not covered; the closest
   dispatch study (Enyam 2026) uses a Markov chain with survey rates.
2. **New central question for RQ3:** do learned ML/DL forecasters add dispatch value **beyond a fitted Markov chain**?
   The Markov/CTMC model becomes a headline baseline, alongside persistence and climatology.
3. Leakage: report random-split vs rolling-origin scores side by side (motivated by Essus 2026).
4. Add a probabilistic layer (conformal / calibrated probabilities) since dispatch needs P(outage), not 0/1.
