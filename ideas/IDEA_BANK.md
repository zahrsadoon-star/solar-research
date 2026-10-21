# Idea Bank (v1, 2026-10-21)

Baseline: MSc thesis - GNPSO sizing of a residential PV-battery system, Baghdad, real 8,760-h load with
~49 % grid unavailability (longest outage 59 h), Mode 0 EMS, RF outage + LSTM load forecasting.
Our unfair advantage: **measured** Iraqi household load + outage + generator data. Ideas that exploit
it score higher on novelty than ideas any group could run on synthetic data.

Scores 1-5 (5 = best). N = novelty after literature check, F = feasibility with data we have,
P = Q1 publishability, E = ease / speed, O = low overlap with the thesis.
Total = 0.30N + 0.25F + 0.25P + 0.10E + 0.10O (max 5.0). Novelty for the top ideas was checked against
the literature in `literature/novelty_check.md`; the rest are first-pass estimates.

## A. Grid-outage modelling and uncertainty
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 1 | Data-driven outage generator | Does a semi-Markov / hazard outage model fitted to Baghdad data change optimal sizing vs a single historical year? | 2 | 5 | 3 | 4 | 4 | 3.40 |
| 2 | Chance-constrained sizing | Cost of guaranteeing LPSP <= x % with 90/95/99 % confidence under outage uncertainty | 3 | 4 | 4 | 3 | 4 | 3.60 |
| 3 | Min-max regret robust sizing | How much does a regret-robust design cost vs the expected-value design? | 3 | 4 | 3 | 3 | 4 | 3.35 |
| 4 | Required autonomy hours | Outage-duration distribution (Weibull/lognormal) -> battery autonomy Iraqi homes really need | 2 | 5 | 2 | 5 | 3 | 3.15 |
| 5 | Scheduled vs random load-shedding | Can rotational (predictable) cuts be exploited to shrink storage vs random outages? | 4 | 4 | 4 | 3 | 4 | 3.90 |
| 6 | VoLL-based economic reliability | Optimal reliability level when unserved energy is priced at Iraqi generator/VoLL cost | 3 | 4 | 3 | 4 | 4 | 3.45 |
| 7 | Multi-year grid availability trends | Sizing robustness to year-to-year changes in national supply (2018-2025) | 3 | 2 | 3 | 3 | 4 | 2.85 |

## B. Forecasting and control
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 8 | Value of outage foresight on REAL data | With learned (imperfect) outage forecasts, how much do predictive EMS strategies save vs Mode 0, blanket pre-charging and perfect foresight? | 4 | 5 | 5 | 3 | 4 | 4.40 |
| 9 | MPC vs rule-based EMS under outages | Benefit of MPC with PV/load/outage forecasts over Mode 0 | 2 | 4 | 3 | 3 | 4 | 3.05 |
| 10 | Deep RL EMS (PPO/SAC) | Can RL beat MPC under heavy outages without explicit forecasts? | 3 | 3 | 4 | 2 | 5 | 3.35 |
| 11 | Probabilistic forecasting for reserve | Quantile / conformal outage-duration forecasts to set a dynamic SOC reserve | 4 | 4 | 4 | 3 | 5 | 4.00 |
| 12 | Honest forecaster benchmark | LSTM vs LightGBM vs Transformer vs naive for outage-period load, with proper time-series CV | 2 | 5 | 2 | 4 | 3 | 3.05 |
| 13 | Joint sizing + control (bi-level) | Does rule-based EMS lead to oversized batteries vs co-optimised control? | 3 | 4 | 4 | 2 | 4 | 3.50 |
| 14 | Forecast-aware sizing | How optimal battery size shifts with forecast accuracy | 3 | 4 | 4 | 3 | 5 | 3.70 |

## C. Optimisation methodology
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 15 | Rigorous metaheuristic benchmark | GNPSO vs NSGA-II, MOEA/D, SHADE, CMA-ES, GWO with 30 runs, hypervolume, Friedman tests | 2 | 5 | 3 | 4 | 3 | 3.30 |
| 16 | Exact MILP optimality gap | How far are metaheuristic designs from the true MILP optimum of sizing + dispatch? | 3 | 4 | 4 | 3 | 4 | 3.60 |
| 17 | Surrogate-assisted optimisation | Kriging/GP surrogate to cut evaluations 10x without losing optimality | 2 | 4 | 3 | 3 | 4 | 3.05 |
| 18 | Many-objective + MCDM | Cost, reliability, emissions, wear, grid dependence; TOPSIS/AHP decision | 2 | 4 | 3 | 3 | 4 | 3.05 |
| 19 | Fitness-landscape analysis | Why do GA-PSO hybrids help on this problem class? | 4 | 4 | 3 | 3 | 4 | 3.65 |

## D. Battery
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 20 | Heat-aware degradation sizing | Rainflow + temperature-dependent calendar ageing at Iraqi summer temperatures: impact on optimal size and LCE | 3 | 4 | 4 | 3 | 5 | 3.70 |
| 21 | Reliability vs lifetime trade-off of Mode 0 | Keeping SOC high for outage readiness accelerates calendar ageing: where is the optimum reserve policy? | 4 | 4 | 5 | 3 | 5 | 4.25 |
| 22 | Chemistry comparison | LFP vs NMC vs lead-acid vs sodium-ion for outage-heavy hot climates | 2 | 4 | 3 | 4 | 4 | 3.15 |
| 23 | Second-life EV batteries | Techno-economics of second-life packs for Iraqi homes | 3 | 3 | 3 | 3 | 5 | 3.20 |
| 24 | Battery placement and cooling | Indoor vs outdoor vs actively cooled installations: lifetime and energy cost | 3 | 3 | 3 | 3 | 5 | 3.20 |

## E. Climate and environment
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 25 | Soiling-aware sizing + cleaning schedule | Joint optimisation of PV size and cleaning interval under dust events | 3 | 3 | 3 | 3 | 5 | 3.20 |
| 26 | Hot-climate module tech | Bifacial/TOPCon vs mono-PERC temperature derating effects on sizing | 2 | 4 | 2 | 4 | 4 | 2.90 |
| 27 | Climate-change-robust sizing | CMIP6-morphed 2050 weather: does today's design survive? | 3 | 3 | 3 | 3 | 5 | 3.20 |
| 28 | Transposition model choice | Isotropic vs HDKR vs Perez in arid climates: effect on sizing and LPSP | 2 | 5 | 2 | 5 | 3 | 3.15 |
| 29 | Multi-year weather variability | TMY vs actual years 2005-2023 on reliability of the sized system | 2 | 4 | 3 | 4 | 4 | 3.15 |

## F. Iraq-specific socio-technical
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 30 | PV + battery + generator-amp co-optimisation | Optimal mix of PV, battery and neighbourhood-generator ampere subscription under the Iraqi dual-supply market, using measured data | 4 | 4 | 5 | 3 | 5 | 4.25 |
| 31 | Community vs individual storage | Shared neighbourhood battery vs per-home batteries under correlated outages | 3 | 3 | 4 | 3 | 5 | 3.45 |
| 32 | Replacing neighbourhood diesel generators | Community PV-battery microgrid replacing an NDG: cost, emissions, reliability | 2 | 3 | 4 | 3 | 5 | 3.15 |
| 33 | Policy scenarios | Net metering, subsidies, fuel-price reform: payback distribution across policies | 2 | 4 | 3 | 4 | 4 | 3.15 |
| 34 | Aggregated home batteries as grid support | Can coordinated home batteries reduce national load-shedding hours? | 4 | 2 | 4 | 2 | 5 | 3.40 |
| 35 | Affordability and equity | Budget-constrained designs across income levels | 3 | 3 | 3 | 4 | 5 | 3.30 |
| 36 | Iraq design atlas | Design maps for Basra, Mosul, Erbil, Nasiriyah, Baghdad with outage profiles | 2 | 3 | 3 | 3 | 4 | 2.80 |
| 37 | Financing models | PAYG / leasing effect on adoption economics | 2 | 3 | 2 | 4 | 5 | 2.75 |

## G. Load side
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 38 | AC demand response with thermal model | Pre-cooling and AC curtailment to shrink battery size in 50 C summers | 3 | 3 | 4 | 2 | 5 | 3.35 |
| 39 | Critical / non-critical load prioritisation | Tiered load shedding in EMS: cost of resilience per load tier | 3 | 4 | 4 | 3 | 5 | 3.70 |
| 40 | Bottom-up stochastic load synthesis | Appliance-level generator for homes without metered data, validated on our data | 3 | 3 | 3 | 3 | 5 | 3.20 |
| 41 | Electrification and load growth | Future-proof sizing with EVs / heat pumps | 2 | 3 | 3 | 3 | 5 | 2.90 |
| 42 | Thermal storage alternatives | Water heating / ice storage instead of electrochemical storage | 3 | 2 | 3 | 2 | 5 | 2.85 |

## H. System architecture
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 43 | DC- vs AC-coupled architecture | Losses and inverter limits change the optimal design? | 2 | 4 | 2 | 4 | 4 | 2.90 |
| 44 | DC/AC ratio and clipping | Optimal inverter sizing under outages and heat derating | 2 | 4 | 2 | 4 | 4 | 2.90 |
| 45 | PV-battery-small generator hybrid | Optimal private generator dispatch inside the home system | 2 | 4 | 3 | 3 | 4 | 3.05 |
| 46 | V2H for outage resilience | EV battery as home storage in Iraq | 2 | 2 | 3 | 3 | 5 | 2.65 |
| 47 | Hydrogen storage | Seasonal storage for Iraqi homes | 1 | 2 | 2 | 2 | 5 | 2.00 |

## I. Data / ML methodology
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 48 | Explainable surrogate sizing tool | ML surrogate trained on optimiser runs + SHAP: instant, explainable designs | 3 | 4 | 4 | 3 | 4 | 3.60 |
| 49 | Global sensitivity (Sobol) | Which uncertain inputs drive cost and reliability? | 2 | 5 | 3 | 4 | 4 | 3.40 |
| 50 | Transfer learning across households | Forecasting with little data via pre-trained models | 3 | 2 | 3 | 3 | 5 | 2.95 |
| 51 | Resilience metric suite | Survivable outage duration + critical-load survival instead of LPSP only | 2 | 5 | 3 | 4 | 4 | 3.40 |

## J. Validation and resources
| # | Idea | Research question | N | F | P | E | O | Total |
|---|---|---|---|---|---|---|---|---|
| 52 | Open tool vs HOMER Pro | Validation of an open-source sizing tool across scenarios (software paper) | 2 | 5 | 2 | 4 | 3 | 3.05 |
| 53 | Open dataset paper | Baghdad intermittent-grid household dataset (data paper; not Q1 track) | 3 | 5 | 1 | 5 | 4 | 3.30 |
| 54 | Reproducibility audit | Equations-vs-code audit of PV-battery sizing literature | 3 | 3 | 2 | 3 | 4 | 2.85 |

## Top of the ranking (before merging)
8 (4.40), 21 (4.25), 30 (4.25), 11 (4.00), 5 (3.90), 14 (3.70), 20 (3.70), 39 (3.70), 19 (3.65), 2 (3.60), 16 (3.60), 48 (3.60).
Related ideas are merged into candidate studies in `ideas/RECOMMENDATION.md`.
