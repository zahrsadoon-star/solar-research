# Recommendation: 5 studies to pilot in parallel (2026-10-21)

From 54 scored ideas (`IDEA_BANK.md`) and the literature check (`../literature/novelty_check.md`), related
ideas were merged into five studies. All five run on **one shared simulation core** (outage model, EMS variants,
battery degradation, economics, optimiser interface), so building it once serves every study.

Each study first gets a **pilot**: one small experiment with a go / no-go threshold. Only studies whose pilot
shows an effect large enough to publish move on to full experiments and a manuscript. Zaher decides each
study: approve, defer or cancel.

## S1 - Does outage foresight pay on a real intermittent grid? (main candidate)
Ideas 8, 11, 14, 5. Score of lead idea 4.40.
- **Question:** On measured Baghdad data, how much do predictive EMS strategies with a *learned* outage
  forecaster save versus Mode 0, blanket pre-charging and perfect foresight - and does the optimal system size change?
- **Method:** outage forecasters (logistic, RF, LightGBM; time-series CV); EMS variants (Mode 0, blanket
  pre-charge, forecast-based pre-charge, quantile-reserve, perfect foresight); re-optimise size for each; 30 seeds.
- **Novelty vs closest work:** Babu (2026) used synthetic regimes and an abstract predictability parameter; we
  test the same question with real data and real forecast error, and can confirm or contradict his conclusion.
- **Pilot go/no-go:** forecast-based EMS changes grid import, LPSP or cost by >= 10 % vs Mode 0 at equal size.
- **Data:** in hand (load, outage, generator). Weather from PVGIS / NASA POWER.

## S2 - Reliability vs battery lifetime under extreme heat (main candidate)
Ideas 21, 20, 22. Score 4.25.
- **Question:** Keeping batteries full for outage readiness (Mode 0 charges from grid below 80 % SOC) speeds up
  calendar ageing at Iraqi summer temperatures. What reserve-SOC policy and chemistry minimise lifetime cost
  at a given reliability?
- **Method:** semi-empirical ageing (calendar: SOC + temperature; cycle: rainflow DoD) for LFP / NMC / lead-acid;
  battery temperature from ambient + placement; sweep reserve SOC 40-100 %; multi-year simulation with fade.
- **Novelty:** degradation-aware sizing exists (Wu 2022; Sowe 2022) but not the outage-readiness vs ageing
  trade-off in extreme heat.
- **Pilot go/no-go:** optimal reserve SOC differs from 80 % and lifetime cost changes by >= 10 %.
- **Data:** ageing parameters from published, citable models (to be verified); temperatures from weather data.

## S3 - PV + battery + generator-ampere subscription in Iraq's dual-supply market (main candidate)
Ideas 30, 39, 6. Score 4.25.
- **Question:** What is the optimal mix of PV, battery and neighbourhood-generator ampere subscription for an Iraqi
  household, given the subscription's hard current cap and monthly per-ampere price?
- **Method:** amperes as an integer design variable; EMS that respects the cap and serves critical loads first;
  scenarios for per-ampere prices and grid availability; compare PV+battery only, amps only, and the hybrid.
- **Novelty:** Tahir (2024) used Spanish-adapted loads and treated generators as savings; Bou Gebrael (2026) is a
  game-theoretic Lebanon market model. Ampere subscription as a design variable on measured data was not found.
- **Pilot go/no-go:** hybrid lowers household annual cost by >= 10 % vs the best single option.
- **Data needed from Zaher:** typical per-ampere monthly prices (Baghdad / Nasiriyah, recent years) and common
  subscription sizes; otherwise published values with citation.

## S4 - How optimal are metaheuristic sizing results? (supporting)
Ideas 16, 15, 19. Score 3.60.
- **Question:** For sizing with hourly dispatch, how far are GNPSO, PSO, GA, NSGA-II, SHADE from the exact
  MILP optimum, and how stable are they over 30 runs?
- **Role:** gives S1-S3 a defensible optimiser choice; could stand alone if the gap is large. Novelty not yet checked.

## S5 - Irradiance model and weather-year sensitivity in an arid climate (supporting, quick)
Ideas 28, 29. Score 3.05.
- **Question:** Do the transposition model (isotropic vs HDKR vs Perez) and the weather year change the design?
- **Role:** fixes the thesis equations-vs-code discrepancy and sets the weather input for S1-S3.
  Likely a short paper (Q2) or a section, not a Q1 lead.

## Suggested order of work
1. Shared core (Codex tasks in parallel with the product track): outage record parser, EMS variants, ageing model,
   economics, optimiser interface, weather download + cache.
2. Pilots S5 -> S1 -> S2 -> S3 -> S4 (S5 first because it fixes the weather input for the others).
3. Report pilot results to Zaher -> he chooses which studies continue to full experiments and drafting.

Honest caveat: Q1 acceptance is never guaranteed. The pilots are there so we spend effort only where the data
shows a real, publishable effect.
