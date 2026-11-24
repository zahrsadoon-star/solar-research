# S1 pilot report - outage forecasting, Baghdad and Karbala houses (2026-10-21)

Script: `pilot_s1.py` (seed 42). All numbers below come from `results/summary.csv`, `results/fold_scores.csv`,
`results/leakage_check.csv` and `results/data_quality.json`. Figure: `results/pilot_skill.png`.

## Data
| | Baghdad (BG) | Karbala (KR) |
|---|---|---|
| Outage share of hours | 49.4 % | 13.9 % |
| Outage events | 1,064 | 1,030 |
| Mean / max duration | 4.06 h / 59 h | 1.18 h / 8 h |
| Hours with no grid and no generator energy | 4 | 14 |

**Label definition (limitation):** an hour is an outage when the generator supplied energy. In BG the workbook's
"Outage (1/0)" column equals `generator > 0` in all 8,760 hours, so the label is inferred from consumption, not from a
utility outage log. The two sites show different regimes: long, irregular cuts in Baghdad; short, frequent cuts in
Karbala.

## Protocol
Rolling-origin monthly CV: train on all earlier months (>= 3), test on each month April-December (9 folds), with an
embargo so no training target falls inside the test month. Horizons 1, 3, 6, 12, 24 h. Brier skill is relative to
climatology P(outage | hour, month). Models: persistence, climatology, hour-of-day Markov chain, logistic regression,
random forest, LightGBM (untuned, same features for all ML models). Temperature tested as an ablation for BG.

## Results (Brier skill vs climatology, mean of 9 folds)
| Site | Model | 1 h | 3 h | 6 h | 12 h | 24 h |
|---|---|---|---|---|---|---|
| BG | Random forest | 0.504 | 0.400 | 0.356 | 0.338 | 0.349 |
| BG | LightGBM | 0.490 | 0.393 | 0.342 | 0.302 | 0.286 |
| BG | Logistic | 0.435 | 0.387 | 0.340 | 0.328 | 0.348 |
| BG | Hour-Markov | 0.227 | 0.049 | 0.010 | -0.002 | -0.002 |
| KR | Random forest | 0.511 | 0.475 | 0.410 | 0.350 | 0.277 |
| KR | LightGBM | 0.477 | 0.447 | 0.382 | 0.323 | 0.251 |
| KR | Logistic | 0.500 | 0.450 | 0.410 | 0.329 | 0.269 |
| KR | Hour-Markov | -0.031 | 0.002 | 0.003 | 0.002 | 0.002 |

- Random forest beat the hour-Markov chain and climatology in **27 of 27** fold-horizon cases (h = 1-6 h) at both sites.
- The Markov chain - the outage model used in recent weak-grid dispatch work - is no better than climatology beyond
  1-3 h at either site.
- Persistence is worse than climatology at almost every horizon because outages are short relative to the horizons.
- **Temperature did not help** (BG random forest skill 0.493 with vs 0.504 without at 1 h); reported as a negative
  ablation, not hidden.
- **Leakage:** a random 80/20 split (the thesis's approach) inflates LightGBM ROC-AUC from 0.868 to 0.936 (BG, 1 h)
  and from 0.746 to 0.884 (BG, 24 h); KR 24 h: 0.720 -> 0.895.

## Go / no-go
- Criterion 1 (>= 10 % Brier skill over climatology at 1-6 h): **met at both sites by a wide margin.**
- Criterion 2 (forecast-based dispatch changes LPSP or grid import by >= 10 % vs Mode 0): **not tested yet** - needs
  the corrected PV model and the battery simulator (next work package).
- Recommendation: **GO** for the full study.

## Caveats before any claim
One year per site; labels inferred from generator use; untuned models; no significance tests yet (Friedman/Nemenyi and
Diebold-Mariano are planned); KR uses no weather because the NASA series is for Baghdad.

## Implications for the full study
1. The headline is not "ML forecasts outages" but: **learned models carry real skill that the Markov model used in
   dispatch studies misses, and random splits overstate it** - both shown on two Iraqi sites with different regimes.
2. Simple models (logistic) are close to random forest - the full benchmark must test whether deep and foundation
   models add anything beyond them.
3. Next: tuned 20+ model benchmark with statistics, then dispatch value with the corrected PV model.

---

# Criterion 2 - dispatch value of the forecasts (added 2026-10-22)

Scripts: `dispatch_value.py` (size sweep, `results/dispatch_value_{BG,KR}.csv`) and `pareto.py`
(`results/pareto_{BG,KR}.csv`, `results/pareto.png`). Corrected PV model (`src/pv/model.py`, 2018 weather);
out-of-sample forecasts, April-December; KR uses Baghdad weather as a proxy.

## 1. The thesis system is oversized once the PV model is corrected
With 15 kWp / 30.6 kWh / 10 kW, Baghdad April-December: PV 21,700 kWh vs load 19,504 kWh, and LPSP is already 0.35 %
with **no grid charging at all** (Mode 0: 0.29 %). The remaining ~57 kWh unserved is a power limit, not energy. The
thesis sizing must be redone with the corrected model (product track), and forecast value cannot show at this size.

## 2. Charging policy matters more than forecasting (size sweep)
Allowing the grid to keep the battery topped up (Blanket) instead of the thesis rule (Mode 0: night-time only,
below 80 % SOC, 0.25 C) cuts unserved energy by 5-67 % (BG) and 5-73 % (KR) across the sizes tested. A random-forest
trigger reaches 98-100 % of Blanket's reliability gain in BG with ~1-3 % less grid charging; perfect 6-h foresight is
no better. With outages ~54 % of hours in BG, "an outage within 6 h" is almost always true, so a forecast has little
room to change the decision. This agrees with Babu (2026, *Results in Engineering*): grid-charging permission, not
foresight, drives the benefit.

## 3. Where forecast skill does turn into value: reliability vs. battery stress
If time at high state of charge is treated as a cost (calendar ageing; see study S2), the trigger threshold traces a
frontier between LPSP and hours with SOC >= 80 % (8 kWp, 10.2 kWh):

| Site | LPSP at the same high-SOC hours as Mode 0 | Mode 0 |
|---|---|---|
| BG | Logistic 3.96 %, Random forest 4.07 %, Markov 6.61 %, Climatology 6.59 % | 5.33 % |
| KR | Logistic 2.62 %, Random forest 3.23 %, Markov 4.04 %, Climatology 4.16 % | 2.70 % |

- Learned forecasters dominate the Markov chain and climatology across the middle of the frontier at both sites
  (e.g. BG: ~4 % vs ~6.6 % LPSP at equal battery stress).
- At the corners (no grid charging, or always charging) every strategy converges - forecasts only matter for the
  trade-off in between.
- In BG, a learned trigger with a 0.3 pp LPSP penalty spends 15-19 % fewer hours at high SOC than Blanket.
- Perfect foresight is a single point here (binary risk), close to Blanket; it is not an upper bound on this frontier.

## Verdict on criterion 2
Met as written (forecast-triggered dispatch changes unserved energy by > 10 % vs Mode 0), **but most of that effect
comes from the charging policy, not the forecast**. The defensible claim is narrower: forecast skill buys a better
reliability / battery-stress trade-off than a Markov model or climatology. Keep S1 GO with this framing:
"skill is not value - outage forecasts matter on the reliability-ageing frontier, not for reliability alone."

## Limitations of this part
Single-year simulation; no battery ageing model yet (high-SOC hours is only a proxy); untuned thresholds and models;
6-h look-ahead only; KR weather proxy; no economics (Iraqi grid vs generator tariffs to be sourced and cited).
