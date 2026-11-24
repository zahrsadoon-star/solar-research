# S1 dispatch experiment, version 2: answers to Reviewer 2 (M2, M3, M4, M5, M7, SHOULD-FIX 1/5/6)

Every number below is read from a CSV in `results/` written by `run_all.py`. The file and column are given in brackets.
Main labels and sizes: label `grid0` (outage = grid kWh == 0), sites BG (Baghdad) and KR (Karbala), April-December
2018 (6,600 h).

## How to run
```
/home/claude/venv/bin/python -m pytest -q        # 12 unit tests (hand-checked cases, energy balance, oracles, causality)
/home/claude/venv/bin/python run_all.py          # all CSVs and figures; --refit regenerates forecasts
/home/claude/venv/bin/python run_all.py --analyse-only   # re-analyse results/policy_points.csv
```
Runtime on this 2-core machine, shared with other jobs:
- Forecast regeneration: about 9.3 min (4 site x label sets, about 140 s each).
- Simulations, oracles and analysis: 818 s (`run_info.json`).
- A full `--refit` run of an earlier version of the grid (9 fewer no-forecast points per configuration) took 1,240 s.

## Files
| file | content |
|---|---|
| `common.py` | data loading (both labels, load = grid + generator), PV (src/pv/model.py, estimated timestamp offset), window |
| `simulator_v2.py` | simulator and policy builders |
| `forecasts_v2.py` | rolling-origin forecasts (pilot code imported), start-of-hour features, cache name hashed on config |
| `oracle_lp.py` | perfect-information LP (HiGHS via scipy) |
| `oracle_dp.py` | perfect-information DP restricted to the policies' action set |
| `frontier.py` | Pareto fronts, regret, oracle gap |
| `run_all.py` | pipeline, CSVs, figures |
| `test_simulator_v2.py` | unit tests |
| `results/policy_points.csv` | every simulated policy and oracle point (8,856 rows, all metrics) |
| `results/regret_points.csv` | every forecast-policy point with regret (step / interpolated, bracket width) and gaps to both oracles, per plane |
| `results/regret_summary.csv` | per configuration x plane x forecaster x family: counts, min/median regret, where |
| `results/oracle_gap_summary.csv` | per family front: min LPSP, gap to the DP and LP oracles |
| `results/headline.csv` | one row per site x label x size x plane, holding all numbers quoted below |
| `results/m3_unserved_split.csv`, `m3_longest_outages.csv` | M3 |
| `results/forecast_checks.csv` | Brier per model/label/k; difference from the v1 forecast cache |
| `results/pareto_{meansoc,hours80}_{grid0,gen}.png`, `regret_{meansoc,hours80}_grid0.png` | figures (200 dpi) |

## What changed relative to v1 (pilot/dispatch_value.py)
- **Topology made explicit (AC-coupled).**
  - PV: min(PV_DC, 10 kW) x 0.98.
  - Battery converter: also 0.98 in both directions. Charge stored = AC_in x 0.98 x 0.95; discharge AC = DC_out x 0.95 x 0.98.
  - Power limit: 0.5 C at the battery terminal.
  - Converter: 10 kW AC, shared with PV-to-load during discharge, as in v1.
  - Unchanged from v1: c_min 0.05 C, c_max 0.98 C, self-discharge 2e-5/h, initial SOC 0.515.
- **Losses counted separately.** PV clipped at the inverter (`pv_clipped_kwh`, DC) is reported apart from curtailment (`pv_curtailed_kwh`, AC surplus the battery could not take).
- **One SOC definition:** SOC = E / C everywhere. This includes Mode 0's 80 % test, which v1 computed as E / c_max.
- **Energy balance:** sources minus sinks minus storage change. The maximum |residual| over all 8,856 runs is 3.8e-10 kWh (`run_info.json`).
- **Information at decision time:**
  - The grid-charging decision in hour t uses the grid status of hour t (assumed observable at its start), SOC at the start of hour t, PV of hour t-1 (Mode 0's night test: AC PV of t-1 < 0.1 kW), and forecasts issued at the start of hour t.
  - The forecasts were **regenerated** with the pilot's method, with one change: `load_roll24` is shifted by 1 h. This was the only pilot feature that used information from the end of hour t; the test `test_forecast_features_known_at_start_of_hour` checks it.
  - risk_t = max_k P(outage at t+k), k = 1..6.
  - The final hour of the year has no target and gets risk 0. In the last 6 h the max runs over the available k.
  - The cached v1 forecasts are not used. For the `gen` label, the regenerated RF/Logistic risks differ from the v1 cache by a mean |Δp| of 0.0009-0.017; HourMarkov and Climatology are identical (`forecast_checks.csv`).
- **New outputs:** unserved energy is split into energy-limited (battery at c_min) and power-limited (0.5 C or converter limit) parts.

## Policy families (all at the same physical limits; PV surplus is always stored up to c_max)
| family | knob | grid |
|---|---|---|
| a1 SOC-trigger (as specified) | grid charges at 0.5 C while SOC < S (may overshoot S within the hour) | S 0.30-1.00 step 0.05 **+ 0.10-0.25 and 0.76-0.795** |
| a2 SOC-target | same, but stops at S | same |
| b Mode 0 | thesis 0.25 C / rate-matched 0.5 C at threshold 0.80; threshold sweep 0.30-0.95 at both rates | |
| c PV-only | none | |
| d Binary top-up | 0.5 C to c_max when risk_t > theta | theta 0.00-0.99 step 0.01 |
| e RiskTarget | target_t = S_low + (S_high - S_low) risk_t, stop at target | S_low 0.20-0.80 step 0.05; S_high 1.0 (specified) **and 0.9, 0.8** |

Forecasters used in d and e:
- RandomForest and Logistic: "learned".
- HourMarkov and Climatology: "statistical".
- PerfectBinary: risk = 1 if an outage really occurs in t+1..t+6. This has the same policy shape as the forecasters and is **not** an oracle.

Deviations from the task spec, and why (bold in the table above):
1. **SOC grid extended down to 0.10.** Without it the no-forecast (NF) front has a gap between PV-only and S = 0.30, and the step regret there was an artefact of that gap (-1.3 pp in a first run).
2. **Fine SOC grid at 0.76-0.795.** The cost "hours with SOC ≥ 80 %" is a step at 0.80. On the specified 0.05 grid the NF front jumps from S = 0.75 to S = 0.80, which crosses the step. RiskTarget with S_high = 0.8 stays just below the step by construction, so without this refinement the comparison favours forecasts. The headline columns `specgrid_*` repeat the comparison with the NF grid exactly as specified.
3. **S_high 0.9 and 0.8 added** to family e, so that the forecast families also have a variant that respects the 80 % step.
4. **A second oracle (DP) added.** Details under Oracles.

## Oracles
- **LP** (`oracle_lp.py`):
  - Objective: min unserved + lambda x sum_t SOC_t, lambda swept over 23 values.
  - Decisions: PV-to-battery, grid-to-battery (grid-on hours only), discharge (outage hours only, at most the net load), energy state.
  - PV serves load first, as in every policy.
  - The LP **may curtail PV voluntarily** to keep SOC low, which no policy can do. Its schedules are re-simulated with simulator_v2; the LP and re-simulated unserved energy agree in the tests.
  - A hinge variant (penalty on E above 0.8 C, 12 weights) gives perfect-information schedules for the hours ≥ 80 % plane. That curve is achievable, but it is **not** a proven bound for the step cost.
- **DP** (`oracle_dp.py`):
  - Perfect information with **the policies' action set**: PV surplus is always stored, and only the grid-charging amount is chosen.
  - Costs: unserved + w x SOC_t, or unserved + w x 1[SOC_t ≥ 0.8]. The step cost is optimised directly.
  - 201 SOC levels with linear interpolation of the value function; the schedule is re-simulated.
  - Discretisation error: some policy points lie up to 0.01 pp below the DP front (`learned_min_gap_DP_pp`).

## Regret definitions (frontier.py)
Regret is computed for each forecast-policy point at equal stress (mean SOC, or hours with SOC ≥ 80 %):
- **interp:** regret against the NF Pareto front, linearly interpolated **only between the two adjacent front points that bracket the stress**. The bracket width is reported in `interp_bracket_width` and `learned_bracket_width`.
- **step:** regret against the best NF point actually simulated at equal or lower stress. This version is more favourable to forecasts.
- **Outside the NF range:** below the least-stressed NF point, regret is undefined (NaN). Beyond the largest front x, the last front point is used.

Negative regret means the forecast policy beats every no-forecast policy.

## Findings (label grid0; the gen label gives the same picture: best regrets differ by at most 0.042 pp, see `headline.csv` rows with label = gen)

### 1. Reliability alone: no room for forecasts
Perfect foresight does not lower the minimum LPSP. The LP oracle's minimum LPSP equals the best no-forecast LPSP, which is "Blanket" (SOC-trigger S = 1.0), to 3 decimals in every configuration:

| config | min LPSP (Blanket = LP oracle) |
|---|---|
| BG 8/10.2 | 3.983 % |
| BG 5/10.2 | 4.736 % |
| BG 8/20.4 | 1.088 % |
| KR 8/10.2 | 1.725 % |
| KR 5/10.2 | 2.159 % |
| KR 8/20.4 | 0.475 % |

Source: `headline.csv` `nf_min_LPSP_pct`, `oracle_LP_min_LPSP_pct`. A battery kept full whenever the grid is on is already reliability-optimal. Forecast value can only appear as lower battery stress at equal LPSP.

### 2. Forecast families vs the best no-forecast policy (LPSP at equal stress)
Over all four forecasters, the best (most negative) interpolated regret per configuration is (`learned_min_regret_interp_pp`):

| | mean-SOC plane | hours ≥ 80 % plane |
|---|---|---|
| BG 8/10.2 | -0.114 pp | -0.123 pp |
| BG 5/10.2 | -0.208 pp | -0.232 pp |
| BG 8/20.4 | -0.024 pp | -0.019 pp |
| KR 8/10.2 | -0.188 pp | -0.076 pp |
| KR 5/10.2 | -0.151 pp | -0.050 pp |
| KR 8/20.4 | -0.008 pp | -0.005 pp |

Step regret (simulated NF points only, `learned_min_regret_step_pp`) is between -0.11 and -0.83 pp. The large values occur where the NF bracket is wide (KR 5/10.2: 2.3 mean-SOC points, 13 h).

- **Size of the best gain.** 0.23 pp of 19,504 kWh BG load is about 45 kWh over nine months. No significance test or bootstrap has been run, and each minimum is the best of about 556 swept points evaluated in sample, so these minima are optimistic.
- **Learned vs statistical, BG.** ML forecasters (RF, Logistic) compared with the best of NF **and** the HourMarkov/Climatology forecasters still gain -0.105 / -0.127 pp (8/10.2), -0.203 / -0.185 pp (5/10.2) and -0.051 / -0.037 pp (8/20.4) (`ml_min_regret_vs_nf_and_stat_pp`).
- **Learned vs statistical, KR.** The largest KR gains come from **HourMarkov/Climatology** risk inside the RiskTarget shape, i.e. a time-of-day charging schedule, not from forecast skill. ML adds at most 0.05 pp over that set in KR.
- **PerfectBinary** gains only -0.003 to -0.10 pp (`perfectbinary_min_regret_interp_pp`). Knowing exactly *whether* an outage occurs within 6 h does not help much in these policy shapes.

### 3. Stress at equal LPSP (the same fronts read horizontally)
This is the largest reduction in stress, at equal LPSP, of a learned/statistical point against the NF front (simulated NF points only; `learned_max_stress_saving_equal_LPSP`, `learned_stress_saving_rel_pct`, `learned_stress_saving_at_LPSP`):

| config | hours ≥ 80 % saved | at LPSP |
|---|---|---|
| BG 8/10.2 | 780 h (17 %) | 4.10 % |
| BG 5/10.2 | 934 h (22 %) | 4.87 % |
| BG 8/20.4 | 688 h (13 %) | 1.11 % |
| KR 8/10.2 | 407 h (7.2 %) | |
| KR 5/10.2 | 344 h (6.3 %) | |
| KR 8/20.4 | 252 h (4.1 %) | |

- **Mean-SOC reductions** are 1.9-4.7 SOC percentage points.
- **ML vs NF and statistical:** the same in BG, 218-407 h in KR (`ml_max_stress_saving_vs_nf_and_stat`).
- **Where these savings sit:** in the flat, high-reliability part of the fronts, where a 0.05-0.2 pp LPSP difference corresponds to hundreds of hours.
- **Grid sensitivity:** with the NF grid exactly as specified, KR shows 1,002-1,224 h instead (`specgrid_learned_max_stress_saving`). About two-thirds of that apparent KR benefit was the coarse 0.80 grid point, not the forecast.

### 4. What does NOT support forecast value
- **Low-stress half of the frontier.** Forecast fronts are mostly **worse** than the NF front:
  - The share of points on the joint learned/statistical envelope with negative regret is 38-66 % in BG and 7-55 % in KR (`learned_envelope_share_regret_lt0_pct`).
  - The worst envelope point is +0.8 to +3.8 pp LPSP behind NF (`learned_envelope_max_regret_interp_pp`).
  - Negative regret occurs only in the high-stress band, close to the NF minimum-LPSP point (`learned_envelope_x_range_regret_lt0`, e.g. BG 8/10.2: mean SOC 72.4-79.1 % vs NF minimum at 80.6 %).
  - In that region SOC-target / Mode 0 rules with a low target dominate every forecast rule tested. See `regret_meansoc_grid0.png`.
- **Size of the gains.** The best LPSP gains are ≤ 0.23 pp, untested for significance and selected in sample. Thresholds were not chosen ex ante (SHOULD-FIX 7 not addressed).
- **KR.** Gains are mostly reproduced by non-skilful forecasts (HourMarkov/Climatology). They reflect the time-varying-target policy shape.
- **20.4 kWh battery.** LPSP gains at both sites are ≤ 0.024 pp.
- **Charging rate.** Rate-matching Mode 0 (0.25 C -> 0.5 C at the same threshold) moves BG 8/10.2 from 5.54 % to 4.15 % LPSP; the thesis-rate point is at 4,206 h and the rate-matched point at 4,582 h (`policy_points.csv`). The charging rate alone is worth more LPSP than any forecast family's gain over the NF front.

### 5. Distance to the oracle
- **DP oracle (same action set, perfect information).** It reaches the minimum LPSP (within 0.005 pp) at much lower stress than any policy (`oracle_DP_x_at_min`, `nf_x_to_within_0p05_of_oracle`, `learned_x_to_within_0p05_of_oracle`):

  | config | DP mean SOC | NF mean SOC | best forecast mean SOC | DP hours ≥ 80 % | NF hours | best forecast hours |
  |---|---|---|---|---|---|---|
  | BG 8/10.2 | 63.5 % | 79.1 % | 76.4 % | 3,079 h | 4,648 h | 4,033 h |
  | KR 8/10.2 | 60.5 % | 90.8 % | 88.7 % | 3,067 h | 5,651 h | 5,417 h |

  NF and the best forecast are measured within 0.05 pp of the oracle LPSP.
- **At the DP oracle's own stress level:**
  - The best NF policy has LPSP 3.25-9.78 % against the oracle's 0.48-4.74 %, i.e. 2.2-7.6 pp worse.
  - Forecast policies are about as far away (3.33-10.58 %; `nf_LPSP_at_oracle_DP_x`, `learned_LPSP_at_oracle_DP_x`).
- **Summary of the gap.** Forecasts close only a small part of the oracle gap: in BG 8/10.2, 615 of the 1,569 hours between NF and the oracle (39 %); in KR 8/10.2, 234 of 2,584 h (9 %).
- **LP oracle (may also curtail PV).** It reaches the same minimum LPSP at mean SOC 8.9-19.1 % and 10-290 h above 80 % (`oracle_LP_x_at_min`). Most of the remaining distance is therefore about *what the battery is allowed to refuse* (PV storage), not about foresight of outages.

### 6. M3: why energy is unserved
Source: `m3_unserved_split.csv` and `m3_longest_outages.csv`.

- **BG thesis size (14.95 kWp / 30.6 kWh), Mode 0.**
  - 60.99 kWh unserved, 100 % energy-limited, all inside the 59 h outage starting 2018-05-28 13:00 (158.1 kWh of load).
  - Usable battery energy is 26.5 kWh AC; the maximum outage-hour load is 4.85 kWh against a 10 kW discharge limit.
  - PV clipped at the 10 kW inverter: 1,666 kWh.
  - The v1 claim "power limit, not energy" is therefore false: the shortfall is energy-limited by a few multi-day outages. The 10 longest BG outages are 19-59 h.
- **BG at 8/10.2 and 5/10.2.** All unserved energy is energy-limited for every policy.
- **KR.** The longest outage is 8 h, but outage-hour load reaches 15.1 kWh, above the 5 kW discharge limit of a 10.2 kWh battery.
  - With Blanket, 74 % (8/10.2), 65 % (5/10.2), 96 % (8/20.4) and 100 % (thesis size) of unserved energy is **power-limited**.
  - With PV-only it is 96-99 % energy-limited at the three study sizes (69 % at the thesis size).
  - So in KR, reliability under grid charging is limited by battery power, not energy or forecasting.

## Limitations
- **One year, one trajectory.** No bootstrap or significance tests. A 0.1 pp LPSP difference is about 20 kWh.
- **Regret minima are selected in sample** over dense knob grids. No ex-ante threshold choice.
- **Outage-hour load is suppressed demand**, capped by the generator subscription, so LPSP understates the requirement.
- **Labels are inferred from metered consumption.** The two labels differ in 4 (BG) and 14 (KR) hours, plus 1 KR hour; results are near-identical.
- **KR uses Baghdad 2018 weather** (about 80 km away).
- **PV model:** system_losses = 0; no soiling sensitivity (Reviewer SHOULD-FIX 8b).
- **Stress proxies, not an ageing model.** Mean SOC and hours ≥ 80 % are proxies; there is no calendar-ageing model.
- **Hours ≥ 80 % oracle.** The DP oracle optimises the step cost directly, but on a 201-level grid. The LP hinge curve is only an achievable set.
- **Forecasts use the pilot's features and models,** including the raw `month` feature (SHOULD-FIX 2) and the expanding climatology (M1); not re-tuned.
- **Grid status of hour t is assumed known at the start of hour t,** following the spec.
