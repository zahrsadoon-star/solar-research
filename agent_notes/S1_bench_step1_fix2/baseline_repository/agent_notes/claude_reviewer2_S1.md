# Reviewer 2 - S1 pilot (outage forecasting + dispatch value), BG and KR, 2018

Reviewer: Claude (acting as Reviewer 2), 2026-10-22. No existing file was edited. All reproductions below were run
with `/home/claude/venv/bin/python` against the committed code, `results/*.csv` and the cached `*.pkl` forecasts.
Line numbers are those of the current files.

## Summary verdict: **MAJOR_REVISION**

The engineering is careful in several places. The rolling-origin protocol has a correct embargo. HourMarkov is fitted only
on data before the test month. The simulator's energy balance closes exactly (residual about 1e-12 kWh). The PV
timestamp offset holds up on a fine grid. The PV azimuth and timezone fixes are correct.

Two of the paper's central claims do not survive stronger baselines, though:

1. **The Criterion-1 "skill" is measured against a near-trivial reference.** The "climatology P(outage | hour, month)" never
   sees the test month, so it collapses to an expanding-window hour-of-day mean. Its Brier score is 0.251 for BG, which is
   a coin flip. A parameter-free 14-day trailing hour-of-day climatology already has Brier skill 0.31 on the same scale.
   Measured against that baseline, BG random forest skill is 0.28 (1 h), 0.13 (3 h), **0.06 (6 h)** and 0.05 (24 h).
   **Criterion 1 (>= 10 % at 1-6 h) fails at 6 h for BG.** KR still passes (0.43 / 0.39 / 0.31).
2. **The Criterion-2 "reliability vs battery-stress frontier" result is overturned by a no-forecast rule.** The rule is:
   top up from the grid at 0.5 C whenever SOC < S, with S swept. It dominates every forecaster across almost the whole
   frontier at both sites. The forecasters were only compared with other forecasters (Markov, climatology) and with fixed
   corner policies, never with a no-forecast policy family of the same shape.

There are also several factual errors in REPORT.md: the "power limit" claim, a wrong percentage range, a 0.3 pp vs 0.5 pp
mix-up, and a table that no script produces. The label also has no independent ground truth: the "National Status" sheet
is derived from `grid > 0`.

---

## MUST-FIX

### M1. Climatology reference is mis-specified and too weak; Brier skill is inflated (pilot_s1.py:90-106, 163-164, 206-210)
**Why.** `Climatology.fit` is given training rows whose targets are all before the test month (embargo, line 158). So
`(hr, test_month)` is **never** in `self.table`, and the `by_hour` fallback is always used. Check: for July, h = 3,
`any((h,7) in table)` returns `False`. The baseline is therefore an expanding-window hour-of-day mean, not the
P(outage | hour, month) described in REPORT.md:22 and the docstring. Outage share in BG swings between 0.12 (Mar) and
0.80 (Jul) and back to 0.15 (Oct). A stale expanding mean is a weak reference, and every "skill vs climatology" number
inherits that weakness. The ML features `roll_168` and `month` capture the regime level that the reference lacks.

**Reproduction** (trailing W-day hour-of-day mean, built only from `o[t+h-24k] <= t`; skill on the same scale as REPORT.md):
```
BG h1  trail14d 0.313 | RF 0.504 | RF skill vs trail14d 0.278
BG h3  trail14d 0.314 | RF 0.400 | RF vs trail14d 0.127
BG h6  trail14d 0.314 | RF 0.356 | RF vs trail14d 0.062   <- below the 10 % go/no-go bar
BG h24 trail14d 0.315 | RF 0.349 | RF vs trail14d 0.049
KR h1  trail14d 0.146 | RF 0.511 | RF vs trail14d 0.427
KR h6  trail14d 0.146 | RF 0.410 | RF vs trail14d 0.310
KR h24 trail14d 0.147 | RF 0.277 | RF vs trail14d 0.152
```
Code (scratchpad `baselines.py`), essence:
```python
lagged = sum(o.shift(24*k - h) for k in range(k0, k0+W)) / W   # k0 = ceil(h/24); uses only o at or before t
```
**Fix.** Add (a) a trailing-window (7/14/28 d) hour-of-day climatology, (b) the seasonal-naive baseline that the PLAN
promises (missing from the pilot), and (c) a recency-weighted Markov chain (fitted on the last N days). Report skill
against the **strongest** baseline. Rename the current one "expanding hour-of-day climatology". Re-evaluate Criterion 1:
for BG it currently fails at 6 h.

### M2. Dispatch frontier lacks a no-forecast policy family; Section 3's claim is overturned (dispatch_value.py:95-100; REPORT.md:84-98)
**Why.** The frontier compares only forecast-triggered top-ups (0.5 C) with each other. Its no-forecast references are
single fixed points: PV-only, Mode 0 at 0.25 C at night, and Blanket. "Hours with SOC >= 80 %" is a step-function cost, so a
rule that simply holds SOC just below 80 % avoids that cost while keeping most of the energy in reserve. No forecast is
needed for that.

**Reproduction.** Same simulator, copied verbatim. The only change is that Blanket becomes "Blanket while SOC < S"
(scratchpad `noforecast.py`). Setting: 8 kWp, 10.2 kWh, Apr-Dec.
```
BG (S, high-SOC h, LPSP no-forecast, RF LPSP at same h, Logistic LPSP at same h)
 (0.5, 3631, 4.15, 5.11, 5.67)
 (0.6, 4001, 4.02, 4.33, 4.01)
 (0.7, 4268, 4.01, 4.04, 3.91)
 (0.8, 4711, 3.92, 3.86, 3.86)
KR
 (0.4, 3623, 2.32, 5.06, 4.55)
 (0.5, 4054, 2.16, 4.36, 3.58)
 (0.6, 4816, 1.77, 3.03, 2.52)
 (0.7, 5302, 1.74, 2.21, 2.09)
```
The no-forecast rule dominates RF everywhere below about 4,700 h (BG) and about 5,800 h (KR). Logistic is ahead by at
most about 0.1 pp in a narrow BG band. Even the trivial rate-matched Mode 0 (same rule, 0.5 C instead of 0.25 C) gives
BG 3.95 % at 4,505 h, versus RF 3.88 % at 4,503 h. Most of the "learned forecasts beat Mode 0" gap in the table at
REPORT.md:90-91 comes from the C-rate, not the forecast.

**Fix.** (1) Add no-forecast policy families swept over their own knob: SOC target S, C-rate, night window. (2) Compare
the forecast families against the best of them at equal cost. (3) Replace the step proxy with a smooth ageing cost (mean
SOC, or an SOC-weighted calendar-ageing model, e.g. Arrhenius/SOC-dependent; cite properly), or use a forecast-dependent
SOC *target* rather than a binary trigger. (4) Only then claim forecast value.

### M3. Section 1 claim "the remaining unserved energy is a power limit, not energy" is false (REPORT.md:73)
**Reproduction** (instrumented copy of `simulate`, identical outputs to `dv.simulate`):
```
30.6 kWh / 14.95 kWp  Mode0   unserved 57.448  energy_limited 57.448  power_limited 0
max load during BG outage hours: 4.85 kWh (inverter 10 kW, 0.5C = 15.3 kW)
longest Apr-Dec outage: 59 h, 158.1 kWh (from 05-28 13:00)
```
All unserved energy happens when the battery is at c_min, during multi-day outages. **Fix:** rewrite as "energy-limited by a
few multi-day outages (59 h, 158 kWh) that no 30.6 kWh battery can bridge". The "oversized" conclusion still holds with
14 % system losses (LPSP PV-only 0.42 %, Mode 0 0.34 %), so say that too.

### M4. Numbers in REPORT.md that are wrong or not produced by any script (AGENTS.md rule 3)
| Location | Report says | Results say |
|---|---|---|
| REPORT.md:78 | Blanket cuts unserved vs Mode 0 by "5-67 % (BG)" | BG 0.0-66.5 % (11.1-66.5 % excluding the thesis size, where both are 57.45 kWh); KR 0.0-73.3 % |
| REPORT.md:97 | "learned trigger with a **0.3 pp** penalty: 15-19 % fewer high-SOC hours than Blanket" | 0.3 pp: Logistic 17.4 %, **RF 12.7 %**. The 15-19 % range is the **0.5 pp** criterion printed by pareto.py:52-63 (RF 15.4 %, Logistic 19.0 %) |
| REPORT.md:88-91 | "LPSP at the same high-SOC hours as Mode 0" table | No script computes it. I reproduced it only by `np.interp` on pareto_*.csv (BG 3.96/4.07/6.61/6.59, KR 2.62/3.23/4.04/4.16). For KR Markov/Climatology the interpolation crosses an unsampled gap (theta 0.15 -> 0.25 jumps from 5,522 to 3,431 h), so those two values are a chord, not an operating point |
| REPORT.md:93 | "learned forecasters dominate ... at both sites" | KR: at Mode 0's stress level RF (3.23 %) is **worse than Mode 0 itself** (2.70 %). Not stated |
| REPORT.md:79 | RF "~1-3 % less grid charging" | theta 0.5: 0.6-4.1 % less (95.9-99.4 % of Blanket) |

**Fix:** generate every report number in a script that writes a CSV, including the interpolation and its method. Use a
denser theta grid (or the distinct probability values) so no point is interpolated across a gap.

### M5. Label has no independent ground truth; generator-use is not grid status (pilot_s1.py:46; REPORT.md:14-17; PLAN.md "cross-checked")
**Why/evidence.**
```
BG: NatStatus==1  <=>  grid>0 in 8760/8760 h  (National Status sheet is derived from grid energy, not a utility log)
crosstab NatStatus x (gen>0):  [[4, 4324], [4432, 0]]
KR: grid==0 in 1229 h, gen>0 in 1216 h, grid==0 & gen==0 in 14 h, both>0 in 1 h
KR: 65.4 % of outage hours fall on odd clock hours; outage starts by hour: [9,56,11,54,15,46,40,72,...]
```
The PLAN's cross-check against "National Status" is circular. In KR, the strong odd/even clock-hour alternation is either a
real 2-hour rota (in which case a rota/phase baseline is needed) or a data-processing artefact (for example a half-hour
shift during aggregation). This must be resolved against Al-Shamri (2019) before KR is used as a second regime. The label
also conflates "grid off" with "the household chose or was able to run the generator". Night-time cuts when the neighbourhood
generator is off are labelled "grid on" (0). The 4 (BG) and 14 (KR) grid=0 & gen=0 hours are labelled 0 even though grid
energy is zero.

**Fix.** Define outage = `grid_kwh == 0` (this matches gen>0 except for the 4/14 hours) and run a sensitivity with both
labels. Report the odd/even analysis and explain it. State in the abstract that the labels are inferred from metered
consumption. In the dispatch part, note that outage-hour load = generator energy, which is **capped by the generator
subscription** (BG p99 4.2 kWh vs 22.4 kWh max overall). Simulated LPSP therefore uses suppressed demand and understates
the battery requirement.

### M6. Random-split "leakage" comparison is confounded as designed, but the claim survives (pilot_s1.py:179-192, 213-214; REPORT.md:43-44)
*Downgraded after my check: the fix is to add the controls, not to change the conclusion.*

**Why.** The random 80/20 split differs from the rolling origin in three ways at once. It tests on Jan-Dec rather than
Apr-Dec. Its training set is about 2-3 times larger. It also contains future months, which carry information about the
seasonal regime. As written, the gap cannot be attributed to neighbouring-hour leakage.

**Decomposition** (LightGBM, same features; scratchpad `leak.py`):
```
                 rolling-origin | blocked month CV, future months allowed, 7-d embargo | random 80/20 scored on Apr-Dec rows
BG h1            0.868          | 0.879                                               | 0.934
BG h24           0.746          | 0.764                                               | 0.880
KR h1            0.829          | 0.846                                               | 0.931
KR h24           0.720          | 0.730                                               | 0.889
```
Future-regime information and the larger training set add only about 0.01-0.02 AUC. Most of the inflation (0.06-0.16) is
temporal adjacency, so the report's direction **and** most of its magnitude are supported. **Fix:** put these two control
columns in leakage_check.csv and REPORT.md so the attribution is shown rather than asserted.

### M7. "Perfect" is not an upper bound; it is a binary trigger at the same rule (dispatch_value.py:132, 99-100; REPORT.md:80, 98)
`perfect = max(o[t+1:t+7])`. With BG Apr-Dec outage share at about 54 %, this is almost always 1, so "Perfect" approximates
Blanket. It is not "no better than RF" in any meaningful sense, and it cannot bound the frontier (the report admits as much
at :98, but :80 still uses it as evidence that "foresight is no better"). **Fix:** compute a real oracle. Use a DP/MILP over
SOC with full knowledge of outages and PV that minimises unserved energy + lambda * ageing cost, swept over lambda. That
gives the true frontier, and each policy's regret relative to it is the quantity to report.

---

## SHOULD-FIX

1. **Decision-time alignment in dispatch** (dispatch_value.py:133 with features at pilot_s1.py:66-78). risk[t] uses
   features "at t" (`state` = full-hour label of hour t, `roll_*` include s[t], `load_roll24` includes load[t]), but the
   grid top-up happens *during* hour t. That is information from the end of the hour used at its start. Test: origin t-1
   (k = 2..6) vs origin t (k = 1..5), same target window. LPSP changes are mostly <= 0.1 pp, but up to +0.43 pp for KR RF at
   theta 0.7 (3.44 -> 3.87). Use the forecast issued at t-1, or document the convention. In the same area, `load_roll24` /
   `temp_max24` include hour t; fine for an end-of-hour issuance, but state the issuance time explicitly.
2. **`month` as a raw integer feature** (pilot_s1.py:76). The test month is always outside the training range. Logistic
   extrapolates its month coefficient linearly; trees treat it as "the latest month". With regime reversals (Sep 0.67 ->
   Oct 0.15) this is unprincipled. Drop it, or use a cyclic day-of-year encoding, and run an ablation.
3. **Risk aggregation** (dispatch_value.py:133). `max_k P(outage at t+k)` is not P(any outage in (t, t+H]), which the PLAN
   lists as a target. Train that target directly; it is also what a calibrated dispatch rule needs.
4. **Markov baseline is a straw man for h >= 3** (pilot_s1.py:109-132). A first-order chain forgets the run length, so by
   construction it decays to the hour-of-day marginal within a few steps. The fair statistical competitor is a semi-Markov /
   duration-dependent hazard model (the Weibull/Cox model is in the PLAN), or a 2nd-order chain conditioned on run length.
   Without it, "learned models carry skill the Markov model misses" (REPORT.md:57-58) is mostly "run length matters".
5. **Simulator details** (dispatch_value.py:73-116). Energy balance verified (residual ~0 kWh, all strategies). Initial SOC
   (0.05 / 0.515 / 0.98) changes nothing because April starts on the grid; a Jan-Mar warm-up is therefore unnecessary, but
   say so. Remaining points:
   - (a) PV is clipped at 10 kW AC before charging (line 85), i.e. AC-coupled, yet battery discharge has no inverter
     efficiency (line 106) and grid charging has no charger efficiency. Make the topology explicit and apply efficiencies
     consistently.
   - (b) Clipped PV (1,666 kWh Apr-Dec at the thesis size) is not counted in `pv_curtailed_kwh`.
   - (c) SOC is defined two ways: Mode 0 compares `e/c_max < 0.8` (line 93), so the threshold is 78.4 % of nameplate,
     while the reported metric uses `e/cap >= 0.8` (line 111). Use one definition.
   - (d) Mode 0 differs from Blanket/FC in both trigger *and* C-rate (0.25 vs 0.5 C), which confounds "policy vs forecast".
     Add rate-matched variants.
   - (e) REPORT.md:72 compares the 21,700 kWh DC PV with load; after clipping and inverter loss it is 19,633 kWh.
6. **Stale cache** (dispatch_value.py:123-128). `forecasts_*_h6.pkl` is reused if present and is git-ignored, so results are
   not reproducible from a clean clone without retraining, and they will silently go stale if `features()` changes. Hash
   the feature/model config into the cache name, or regenerate in CI. (The Climatology part of the current cache does match
   the code: max |diff| = 0.)
7. **Threshold selection.** Sweeping theta on the test period and comparing frontiers at equal x is a legitimate
   ROC-style comparison. However, (i) only operating points that can be chosen ex ante are deployable, and (ii) models with
   different calibration land at different places, so "LPSP at Mode 0's stress" picks a different theta for each model
   after the fact. Add a nested choice of theta (on the preceding month's forecasts, or a calibrated cost threshold
   theta* = c_ageing / (c_ageing + c_unserved)) and report the realised point next to the frontier.
8. **PV model** (src/pv/model.py).
   - Azimuth (180 = S) and timezone handling are correct. The NASA request starts 2017-12-31 UTC, so local 2018-01-01
     00:00 is covered.
   - The +30 min offset is robust. Fine-grid RMSE vs Ineichen clear-sky on clear days is minimal at +30 (26.2 W/m², versus
     30.2 at +40 and 33.0 at +20), and an interval-mean clear-sky model also gives +30. The GHI centroid is at label hour
     11.52, so 12.02 h after the offset, vs solar noon of about 12:03.
   - Remaining issues: (a) `erbs` receives true zenith (line 109) while transposition uses apparent zenith (line 119); use
     one. (b) `system_losses = 0` (line 53) with no soiling in a dusty climate. Default to about 0.14, or run the
     sensitivity in the dispatch study. Yield 1,869 -> 1,607 kWh/kWp. (c) The NOCT model ignores wind, and NOCT/gamma are
     still unverified against the Hi-MO X10 datasheet. (d) NASA POWER GHI is a satellite/reanalysis product (coarse grid,
     dust-aerosol bias). Validate against a ground station or ERA5, or at least cite its known bias in the region.
     (e) `estimate_timestamp_offset` only tests {-30, 0, +30}; widen the grid and report the RMSE curve.
9. **KR weather proxy.** KR PV uses Baghdad 2018 weather (about 80 km). This is acceptable for a pilot, but download the
   NASA POWER series for (32.6136, 44.0430). It is a one-line change and removes a limitation.

## Statistical weaknesses (must be addressed before any manuscript claim)
- One year per site, nine monthly folds that are serially dependent and non-stationary (BG outage share 0.12-0.80), and
  no CIs or tests. The "27 of 27" count is not a test: the 27 cases share 9 folds, and the horizons are highly correlated.
- Required: (a) per-hour losses saved to disk (`preds_all` is computed but discarded at pilot_s1.py:176, 201);
  (b) Diebold-Mariano on Brier loss with a HAC variance (lag >= h) for key pairs, against the *strongest* baseline from
  M1; (c) moving-block bootstrap (block = 1-7 days) CIs for Brier skill and for the dispatch metrics (LPSP, high-SOC
  hours); (d) report fold-wise dispersion, not only means; (e) Friedman/Nemenyi only after (b)-(c), with the caveat that
  9 dependent folds give low power.
- Dispatch results are a single trajectory. Bootstrap outage weeks, or resample days within month, to get a distribution
  of LPSP differences; a 0.1 pp difference on about 19,500 kWh is about 20 kWh and almost certainly not significant.
- Models are untuned (acceptable for a pilot). Note that RF vs Logistic differ by small amounts (RF better in 32/45,
  29/45 and 28/45 fold-horizons), so "RF is best" needs a test.

## Claims that are currently overstated
1. "Criterion 1 met at both sites by a wide margin" (REPORT.md:47): only against a coin-flip reference. BG fails at 6 h
   against a trailing climatology (M1).
2. "Learned models carry real skill that the Markov model used in dispatch studies misses" (REPORT.md:57): the Markov
   chain is first-order and fitted on an expanding window, so it is weak by construction. Compare with a duration-aware
   model (SHOULD-4).
3. "Random splits overstate it" (REPORT.md:43-44, 58): **supported** by my decomposition (M6). Most of the gap is
   temporal adjacency, but the report should show the controls instead of asserting it.
4. "Forecast skill buys a better reliability / battery-stress trade-off than a Markov model or climatology"
   (REPORT.md:102-104), and the headline "outage forecasts matter on the reliability-ageing frontier": a no-forecast SOC
   target rule dominates (M2). As it stands, the defensible statement is the opposite: *on this proxy, a simple SOC cap
   captures the trade-off without any forecast*.
5. "Criterion 2 met as written" (REPORT.md:101): the >10 % change vs Mode 0 comes from charging permission and C-rate, not
   the forecast (the report half-admits this). With rate-matched Mode 0 the forecast adds <= 0.1 pp in BG. Criterion 2,
   read as "forecast value", is **not met**.
6. "The remaining ~57 kWh unserved is a power limit" (REPORT.md:73): false (M3).
7. "Perfect 6-h foresight is no better" (REPORT.md:80): "Perfect" is not an oracle (M7).
8. "Two sites with different regimes" (REPORT.md:16-17, 58): KR's regime may partly be an aggregation artefact (odd-hour
   pattern, M5); unverified.

## What I would accept for a revised pilot
- Criterion 1 recomputed against the strongest of {trailing climatology, seasonal-naive, recency Markov, semi-Markov},
  with DM tests and block-bootstrap CIs.
- Criterion 2 recomputed against no-forecast policy families on a smooth ageing cost, with a DP oracle frontier and an
  ex-ante threshold choice.
- Every number in REPORT.md traceable to a CSV written by a script.
- Label sensitivity (grid==0 vs gen>0) and an explanation of the KR odd-hour pattern.
- If, after this, the forecast value is still about 0, report it as a negative result. "Household outage forecasts have
  measurable skill but little dispatch value beyond a SOC-target rule" is itself publishable, provided it is shown with an
  oracle and proper statistics.
