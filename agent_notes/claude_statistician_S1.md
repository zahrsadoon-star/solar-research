# S1 pilot - statistical robustness review (Claude, statistician role, 2026-10-22)

Scope: tests whether the claims in `studies/S1_outage_forecasting/pilot/REPORT.md` hold up statistically. No
existing file was edited. All outputs are in `studies/S1_outage_forecasting/robustness/`, and
`robustness/run_all.py` regenerates them (~95 min from scratch on 2 cores; results are cached in `robustness/cache/`).
The pilot code is imported, not copied: `pilot_s1.evaluate_site` / `ml_models` (seed monkeypatched),
`dispatch_value.simulate` / `rolling_forecasts`. `pareto.py` is **not** imported because it runs and overwrites
`pilot/results/` at import time. Its settings (8 kWp, 10.2 kWh, theta 0.05..0.95) are restated in `robustness/common.py`.

Reproduction checks (all passed):
- The seed-42 rerun matches `pilot/results/fold_scores.csv` (540 rows, max |dBrier| = 1.1e-16).
- The new H = 12 forecasts reproduce the cached k = 1..6 columns (max diff 4e-16).
- The frontier interpolation reproduces the REPORT table exactly (BG RF 4.07, Log 3.96, Markov 6.61, Clim 6.59 %; KR 3.23, 2.62, 4.04, 4.16 %).

## 1. Seed robustness (Task 1): `seed_skill_summary.csv`, `seed_rf_wins_h1to6.csv`
Brier skill vs climatology uses the pilot definition: 1 - mean fold Brier / mean fold climatology Brier. Seeds 0-9 (10 seeds) were used.

| Site | Model | 1 h | 3 h | 6 h | 12 h | 24 h |
|---|---|---|---|---|---|---|
| BG | RF | 0.504 ± 0.001 | 0.402 ± 0.001 | 0.354 ± 0.001 | 0.338 ± 0.002 | 0.350 ± 0.001 |
| BG | LightGBM | 0.491 ± 0.003 | 0.395 ± 0.002 | 0.342 ± 0.003 | 0.305 ± 0.003 | 0.286 ± 0.003 |
| KR | RF | 0.511 ± 0.002 | 0.475 ± 0.001 | 0.410 ± 0.001 | 0.349 ± 0.001 | 0.274 ± 0.001 |
| KR | LightGBM | 0.479 ± 0.003 | 0.448 ± 0.005 | 0.379 ± 0.002 | 0.323 ± 0.003 | 0.250 ± 0.004 |

Seed sd is ≤ 0.005 everywhere. Every pilot (seed-42) value lies inside the 10-seed min-max range or within 0.003 of it.
"RF beats HourMarkov and climatology in 27/27 folds (h = 1-6)" holds for **all 10 seeds at both sites**.

## 2. Significance (Task 2): `friedman.csv`, `posthoc_pairwise.csv`, `friedman_ranks.png`, `diebold_mariano*.csv`
- **Friedman test** (6 models, 45 month × horizon blocks):
  - BG: χ² = 173.8, p < 1e-30.
  - KR: χ² = 169.2, p < 1e-30.
  - Per horizon (9 independent months), p < 1e-5 in all 10 cases.
- **Mean ranks** (Nemenyi CD = 1.12):
  - BG: RF 1.51, Logistic 2.18, LightGBM 2.42, HourMarkov 4.67, Climatology 4.89, Persistence 5.33.
  - KR: RF 1.87, Logistic 2.00, LightGBM 2.33, HourMarkov 4.44, Climatology 4.76, Persistence 5.60.
- **Learned vs baselines:** every learned model vs HourMarkov or climatology is significant at both sites (Nemenyi p < 1e-4; Wilcoxon-Holm p < 1e-4).
- **Learned vs learned is NOT significant by Nemenyi.**
  - RF vs Logistic: BG Nemenyi p = 0.54, but Wilcoxon-Holm p = 0.014 (RF better in 31/45 folds). KR: Holm p = 0.33.
  - RF vs LightGBM: BG Holm p = 1e-4 (RF better). KR: Holm p = 0.29.
  - Per horizon (9 blocks), no learned-vs-learned difference is significant. Power is low there: the smallest Holm-adjusted p with n = 9 is about 0.06.
- **Climatology vs HourMarkov:**
  - BG: Markov is slightly better overall (Holm p = 0.013). This is driven by h = 1, where Markov wins 9/9 months (Holm p = 0.059).
  - KR: no difference (Holm p = 0.33).
- **Diebold-Mariano** on hourly squared error, RF (seed 42) minus HourMarkov, Newey-West HAC with lag h-1 and the HLN correction:
  - BG h = 1: DM = -27.6. BG h = 6: DM = -21.2.
  - KR h = 1: DM = -27.5. KR h = 6: DM = -23.1.
  - All p < 1e-90.
  - Lag h-1 understates the autocorrelation of hourly outage losses. With lag 168, |DM| is still 7.3-15.1 (p < 1e-12).
  - Across seeds 0-9 the DM range is ±0.2.
- **DM, RF vs Logistic:**
  - BG h = 1: DM = -10.1 (lag 0) and -6.2 (lag 168), so significant.
  - BG h = 6: p = 0.027 at lag 5 but p = 0.28 at lag 168, so not robust.
  - KR: not significant at h = 1 (p ≥ 0.19) or h = 6 (p ≥ 0.93).
- **Caveat:** the 45 Friedman blocks are not independent (the 5 horizons share test months). The per-horizon tests and the DM tests are the conservative checks, and they give the same answer for learned vs baselines.

## 3. Dispatch uncertainty (Task 3): `bootstrap_dispatch_ci.csv`, `bootstrap_replicates_*.csv`, `bootstrap_dispatch.png`
Method: exact week-block bootstrap, with re-simulation.
- April-December is cut into 40 blocks of 168 h; 1,000 replicates.
- Each replicate draws 40 blocks with replacement, concatenates load, grid status, PV and stored risk, and re-runs `simulate` for Mode 0 and the full theta frontier of RF, Logistic and HourMarkov.
- Statistic: LPSP at Mode 0's high-SOC hours (difference in percentage points, pp).
- Limitations: the battery state carries across block joins, and the forecasts are not re-trained, so the CI is conditional on the fitted models. Climatology was left out of the bootstrap to save compute; its point estimate is close to HourMarkov's.
- A fast approximation (summing per-block contributions of one true-series run) gives CIs within about 0.1-0.15 pp of the exact ones. It is used only for Task 4.

| Comparison (pp of LPSP) | BG point [95 % CI] | KR point [95 % CI] |
|---|---|---|
| RF - HourMarkov | -2.53 [-3.51, -1.55] | **-0.81 [-1.85, +0.04]** (97 % of reps < 0) |
| Logistic - HourMarkov | -2.65 [-3.68, -1.64] | -1.42 [-2.44, -0.37] |
| **Mode 0 - HourMarkov** | **-1.28 [-2.26, -0.55]** | **-1.35 [-2.22, -0.41]** |
| RF - Mode 0 | -1.26 [-1.63, -0.66] | **+0.54 [-0.17, +1.23]** |
| Logistic - Mode 0 | -1.37 [-1.72, -0.81] | -0.07 [-0.46, +0.38] |
| RF - Logistic | +0.11 [-0.01, +0.45] | +0.61 [+0.06, +1.24] |

Seed sensitivity of the RF forecasts (`dispatch_rf_seed_sensitivity.csv`, seeds 42, 0, 1, 2): BG 4.07-4.10 %, KR 3.17-3.35 %. The KR value stays worse than Mode 0's 2.70 % for every seed.

## 4. Sensitivity to look-ahead H and battery size (Task 4): `sensitivity_points.csv`, `sensitivity_ci.csv`, `sensitivity_frontiers_{BG,KR}.png`
Setup: 8 kWp; H = 3, 6, 12 h; batteries of 5.1, 10.2 and 20.4 kWh; approximate bootstrap with 1,000 replicates. The H = 12 forecasts were newly computed with `dispatch_value.rolling_forecasts` (H = 12, seed 42).

**Learned vs HourMarkov:**
- BG: in all 9 configurations both learned models beat HourMarkov, with CIs excluding 0. The size of the gain is -0.8 to -2.8 pp.
- KR, Logistic: beats HourMarkov in 8/9 configurations. The exception is H = 3, 20.4 kWh (CI [-1.92, +0.07]).
- KR, RF: the CI includes 0 in 4/9 configurations (10.2 and 20.4 kWh at H = 3 and 6).

**Learned vs Mode 0**, the thesis rule with no forecast:
- BG, 5.1 and 10.2 kWh: learned is better by 1.1-1.4 pp (CIs exclude 0) for every H.
- BG, 20.4 kWh: no difference (point -0.15 to +0.01 pp; CIs about ±0.3).
- KR: Logistic is never significantly different from Mode 0 (points -0.07 to +0.31 pp). RF is worse than Mode 0 in every configuration (+0.46 to +0.69 pp; significant at 20.4 kWh for all H).

**Mode 0 vs HourMarkov:** Mode 0 itself beats the HourMarkov frontier in 16/18 configurations. The exception is BG 5.1 and 10.2 kWh at H = 12, where the CI touches 0.

**Effect of H:** H barely changes the learned forecasters (BG RF 4.07-4.21 %). It changes HourMarkov more, and in KR it does not change the ranking.

**Theta-grid check** (`theta_grid_check.csv`): HourMarkov and climatology risks take only 400 and 96 distinct values, so their frontiers on the 0.05 grid are coarse. A 99-quantile grid moves every value by ≤ 0.14 pp, and HourMarkov gets slightly worse (BG 6.69, KR 4.18 %). The coarse grid does not handicap the Markov baseline.

## Verdict on REPORT.md claims
**Survive:**
1. **Learned models have large, real skill over climatology at 1-24 h** (≥ 10 % criterion: the lowest skill is 0.25 at KR 24 h, and the 1-6 h values are 0.34-0.51). This is seed-stable (sd ≤ 0.005), Friedman p < 1e-30, and DM |t| ≥ 7 even with a 168-h HAC lag.
2. **RF beats HourMarkov and climatology in 27/27 folds (h = 1-6), both sites.** This holds for all 10 seeds.
3. **The Markov chain is no better than climatology beyond 1-3 h.** This is consistent: no difference at h ≥ 3. In BG, Markov is better at h = 1 (skill 0.227).
4. **"Simple models (logistic) are close to RF"** survives, and is stronger than stated. Nemenyi cannot separate RF, Logistic and LightGBM at either site. In KR, RF and Logistic are statistically indistinguishable (DM p ≥ 0.19). In BG, RF has a small edge (Wilcoxon-Holm p = 0.014; DM significant at h = 1 only).
5. **BG dispatch:** learned triggers give lower LPSP at equal high-SOC hours than HourMarkov (-2.5 pp [-3.5, -1.5]) **and than Mode 0** (-1.3 pp [-1.6, -0.7]). This is robust to H, and to battery size at 5.1 and 10.2 kWh.

**Do not survive, or need rewording:**
6. **"Learned forecasters dominate the Markov chain and climatology at both sites"** is only partly true. In KR, RF vs HourMarkov is not significant at 95 % in the base case ([-1.85, +0.04]) or in 4/9 sensitivity configurations. Only Logistic is consistently better.
7. **The Markov comparison is a weak benchmark.** Mode 0, which uses no forecast, already beats the HourMarkov-triggered frontier by 1.3 pp at both sites (CIs exclude 0). So "learned beats Markov" mainly shows that a Markov-triggered top-up is a poor rule. It is not evidence that forecasts add value over the thesis rule.
8. **KR:** forecast-triggered dispatch does **not** beat Mode 0 at equal battery stress. Logistic gives -0.07 pp [-0.46, +0.38]; RF gives +0.54 pp [-0.17, +1.23], which is worse and significantly worse at 20.4 kWh. **The "forecast skill buys a better reliability/ageing trade-off" verdict holds for BG only, not for KR.**
9. **Skill ordering ≠ value ordering.** RF has the better Brier score but a worse dispatch result than Logistic in KR (+0.61 pp [+0.06, +1.24]). Ranking forecasters by Brier score does not predict their dispatch value.
10. **BG with a large battery (20.4 kWh):** no forecast benefit over Mode 0 at any H.

**Not tested here** (point estimates only, no CI):
- "15-19 % fewer high-SOC hours than Blanket at a 0.3 pp penalty."
- "98-100 % of Blanket's gain."
- "Charging policy cuts unserved energy by 5-73 %."
- The temperature ablation and the leakage AUC inflation (single seed, no test).

## Recommended framing
- **Forecasting result:** strong and statistically solid. It can be headlined.
- **Dispatch result:** state it as "in Baghdad, learned outage forecasts cut LPSP by about 1.3 pp (95 % CI 0.7-1.6) relative to the thesis rule at equal high-SOC exposure, for batteries ≤ 10 kWh; in Karbala (short, frequent outages) they add nothing over the thesis rule."
- **Drop Markov as the main dispatch comparator, or add Mode 0 as the main reference in every frontier table.**
- All of this rests on one year and 40 weekly blocks per site. The CIs are conditional on the fitted forecast models and on the simulator.
