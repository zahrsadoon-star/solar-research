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
