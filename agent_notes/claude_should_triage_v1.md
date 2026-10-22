# SHOULD-item triage and fresh consistency read: S1 protocol v1.0-rc (Claude, Reviewer-2 / methodologist)

Date: 2026-10-22 (for the day-2 freeze on 23 Oct). Object: `method/S1_protocol.md` v1.0-rc as of git `db12b22` (399 lines;
line numbers below refer to that version). Inputs read: the protocol; `agent_notes/claude_reviewer2_protocol_v1rc.md`
(v1rc check, items S1-S10); `agent_notes/claude_reviewer2_protocol.md` (v0.9 review); `agent_notes/claude_statistician_protocol.md`;
`DECISIONS.md`; `method/S1_ageing_model.md`; `results/S1/eda/summary.json`; the Read Me sheet of
`data/raw/BG18760_with_analysis.xlsx`; the sheet layout of `data/raw/BG1-8760.xlsx` and `data/raw/KR-8760.xlsx`.
No file other than this one was edited.
(Lead note: written by a cloud Claude agent; the cloud push was refused (403), so the lead copied this file to the PC repo verbatim.)

New numbers in this note, and how they were obtained (nothing else is new):
- BG primary-label counts (4,328 outage hours, 1,067 events, 4 hours with grid==0 and gen==0, 0 hours with grid>0 and gen>0):
  my own recount with pandas from the `Hourly Data` sheet of `data/raw/BG18760_with_analysis.xlsx` (events = maximal runs
  of `grid_kwh == 0`). They must be reproduced by the WP1 script, not copied.
- Nemenyi CD check: `scipy.stats.studentized_range.ppf(0.95, k, 1e6)/sqrt(2) * sqrt(k(k+1)/(6*9))` gives 12.69 (k = 25),
  13.26 (k = 26), 13.83 (k = 27). The protocol's "about 12.7" for BG k = 25 is correct.
- Test 8 check: on `data/raw/nasa_power_baghdad_2018_hourly_local.csv` the mean GHI is 0.0 at local hours 0-4 and peaks at
  hour 11 (708 W/m2; hour 12: 698). Test 8 as written will pass.
- Source-file facts used in I1: `BG1-8760.xlsx` Sheet1 has 745 full datetimes (1 Jan 00:00 to 1 Feb 00:00), after which
  the cells are time-only `00:00`; Sheet2 has 745 rows covering January only; `KR-8760.xlsx` has 8,760 rows x 2 columns with
  no header and no timestamps. The Read Me of the analysis workbook states that the timestamps are reconstructed from row
  order and that 731 of 745 January rows match Sheet2 at zero offset. I have not re-run that offset check myself.

---

## 1. Triage of the open SHOULD items

Status of the v1rc SHOULD list (S1-S10 in `claude_reviewer2_protocol_v1rc.md`, section 4) against v1.0-rc:
already applied by the lead: S4 (episode bootstrap, line 378-379), S8 (G2 Holm, line 257), S9-ii (near-oracle O1,
lines 355-358), S9-iii (headline pooled May-Dec, line 364), S10-i ((b)/(c) scoring, line 36), S10-ii (static-climatology (b)
smoothing, line 109). S2 is covered in substance by line 364-365 ("Policy changes ... are `[LEAD]` decisions").
The table lists every item that is still open, fully or in part.

| # | Item | Verdict | One-line reason |
|---|---|---|---|
| T1 | S1 primary-label counts in §0 | **APPLY** | The headline label has no counts in the protocol; the counts are now known and test 19 can check them. |
| T2 | S2 `[LEAD]` tag on the 9.3 objective | **REJECT (already covered)** | Lines 364-365 already tag the objective and primary-pair changes as `[LEAD]` with reasons; a second tag adds nothing. |
| T3 | S3 lambda grid definition | **APPLY (modified)** | "Spanning the slopes" cannot be coded; log spacing also fails if a slope is 0, so a fallback is needed. |
| T4 | S5 R_t meaning (residual sentence) | **APPLY** | Line 35 fixes the scale; one sentence makes the 1-h offset explicit for whoever codes the KM median and MAE. |
| T5 | S6 trailing-climatology denominator | **APPLY** | Line 112 divides by (W + 1); line 40 says denominator = available days. Two coders would differ (KR may have gaps). |
| T6 | S7 seed-rule pooling | **APPLY (extended)** | "Pooled inner-validation Brier" does not say pooled over what, when n is decided, or which settings the max runs over. |
| T7 | S9-i virtual-time ageing and initial state | **APPLY (modified)** | Needed, but S9-i's "initial Q_loss = 0" is wrong for a sqrt-time model; see I5. Use a positive initial state. |
| T8 | S9-iv grid charging only with realised grid supply | **APPLY** | Physical rule that the simulator must implement and that no section states. |
| T9 | S10-iii FM target (b) needs every k-step forecast | **APPLY** | Line 132 `prod_k` is undefined in k; FMs must output k = 1..h, not only the 5 horizons. |
| T10 | S10-iv calendar flag use (main vs sensitivity) | **APPLY** | Line 92 creates `holiday_uncertain` but does not say whether the main run uses it; ad hoc holidays can postdate the origin. |
| T11 | S10-v "every evaluation seed" vs deterministic models | **APPLY** | Line 65 conflicts in wording with line 179 (deterministic models: 1 run). |
| T12 | v0.9 review A.3: minimum-detectable-effect / power remark | **DEFER-TO-SENSITIVITY** | A pre-data MDE needs the SD of d_t, which is unknown; report achieved CI half-widths per horizon instead, never post-hoc power. |

APPLY count: **10** (T1, T3-T11).

### Exact replacement text (old text quoted verbatim from v1.0-rc)

**T1 - §0, line 17.**
Old: `  WP1 EDA (label S-gen): 4,324 outage hours, 1,064 events, outage share 0.494, mean event 4.06 h.`
New: `  WP1 EDA (label S-gen): 4,324 outage hours, 1,064 events, outage share 0.494, mean event 4.06 h. Primary label
  (grid==0), Reviewer-2 recount: 4,328 outage hours, 1,067 events (the 4 extra hours have grid==0 and gen==0; no hour has
  both > 0); the WP1 script writes its own counts to data_audit.csv before the hash, and those counts govern.`

**T3 - §9.3, line 344.**
Old: ``spanning the slopes of the no-forecast front computed on Jan-Mar (training months only) `[JC]`. Secondary stress planes,``
New: ``between the smallest and largest finite positive |dLPSP_pp / dA| over adjacent points of the N2 Pareto front (LPSP_pp
vs A), simulated on Jan-Mar with realised outages, no forecasts and the 9.1 initial state (training months only); if fewer
than two such slopes exist, the same on Jan-Apr `[JC]`. Secondary stress planes,``

**T4 - §0, line 36.**
Old: `  use this R_t scale. Targets (b) and (c) are scored`
New: `  use this R_t scale (for an event of length D seen at elapsed run length e, including row t: R_t = D - e + 1, i.e.
  R_t - 1 further outage hours follow the origin). Targets (b) and (c) are scored`

**T5 - §3 B.4, line 112.**
Old: `+ 0.5) / (W + 1)`
New: `+ 0.5) / (n_avail + 1)` and append to the same bullet, after `all three reported.` on line 113:
`The sum runs over the n_avail of the W days whose label is observed (n_avail = W without missing hours); (b) likewise.`

**T6 - §5, line 182.**
Old: `SD10 = seed SD of pooled **inner-validation** Brier over seeds 1-10, taken as the maximum over that model's`
New: `SD10 = seed SD of **inner-validation** Brier over seeds 1-10 (each seed's Brier pooled over the inner-validation
  origins of all 9 folds; n is decided once, after seeds 1-10 have run on all folds, and seeds 11..n then run on all
  folds and settings; the 1.4 random-draw seeds 0-4 are a separate namespace), taken as the maximum over that model's`
And line 183, old: `(target, horizon) cells `[LEAD]``
New: `(site, weather setting, target, horizon) cells under the primary label `[LEAD]``

**T7 - §9.1 line 324, §9.3 after line 341, §9.5 line 363.**
(a) Old (9.1): `initial SOC 0.5 on 1 Apr, battery state carried across`
New: `initial SOC 0.5 and initial ageing state (9.3) on 1 Apr, battery state (SOC and the virtual ageing times) carried across`
(b) 9.3, insert after `if not verifiable, a stated assumption with a +/-50 % sensitivity.` (line 341):
`A is accumulated hour by hour with the virtual-time form (Eqs. 5.15/5.17 and 5.26/5.28 as copied in
method/S1_ageing_model.md), so it is path-dependent and not additive across months. Initial state: Q_cal,0 and the cycle
virtual FEC from an assumed pack age (value fixed in method/S1_ageing_model.md before its hash) `[JC]`; never 0, because the
sqrt-time model has an infinite rate at t = 0 and would front-load ageing into April and break the O1 linearisation.`
(c) Old (9.5): `SOC 0.5 and zero ageing.`
New: `SOC 0.5 and the 9.1 initial ageing state.`

**T8 - §9.4, line 349.**
Old: `- N2 SOC-target, no forecast: grid-charge at rate c whenever SOC < S; S in {0.30, 0.35, ..., 1.00}, c in {0.25, 0.5} C;`
New: `- N2 SOC-target, no forecast: grid-charge at rate c whenever SOC < S; S in {0.30, 0.35, ..., 1.00}, c in {0.25, 0.5} C
  (in every family, grid charging happens only in rows with realised grid supply; this is simulator physics, not a forecast);`

**T9 - §3 FMs, line 132.**
Old: `` target (b) via `1 - prod_k(1 - p_{t+k})` ``
New: `` target (b) via `1 - prod_{k=1}^{h}(1 - p_{t+k})`, where p_{t+k} is the k-step forecast from origin t for every
k = 1..h (not only the 5 horizons), ``

**T10 - §2 Calendar, line 92-93.**
Old: ``the day gets a separate `holiday_uncertain` flag instead of `holiday` `[JC]`;``
New: ``the day gets a separate `holiday_uncertain` flag instead of `holiday` `[JC]`; the main run uses `holiday` only, a
  sensitivity run adds `holiday_uncertain` (ad hoc declarations can postdate the origin, a look-ahead risk);``

**T11 - §1.2, line 65.**
Old: `for every evaluation seed, and its`
New: `for every evaluation seed (one run for deterministic models, section 5), and its`

**T12 (deferred) - suggested sensitivity line for §6.3, not required for the freeze:**
`Achieved precision: per horizon, the 95 % CI half-width of dBS(C_ML - C_B) is reported next to the G1 margin 0.005; no
post-hoc power is computed.`

---

## 2. Fresh read of v1.0-rc: remaining inconsistencies

Severity: **[B]** = blocks the freeze (a test that cannot be implemented, a contradiction that changes code, or a missing
setting that changes a confirmatory or go/no-go result); **[S]** = should be fixed in the same edit pass (text only);
**[N]** = note, no protocol edit strictly needed.

### I1 [B] Test 18 cannot be implemented as written (§0 lines 26-27, §8 lines 305-306, §10 line 397)
- Test 18 must "fail on a 1-h shift" by checking "the workbook's documented timestamps and the start/end times in
  Outage Events". No source carries interval semantics:
  - BG Sheet1 has explicit datetimes for January only (745 rows); later cells are time-only `00:00`. The analysis
    workbook's Read Me says the annual timestamps are reconstructed from row order. `results/S1/eda/summary.json` records
    7,682 time-only clock disagreements, so these cells cannot serve as a check.
  - "Outage Events" is derived from the same reconstructed row clock, so a check against it is circular.
  - `KR-8760.xlsx` has no timestamps and no header row at all.
- What can be tested is row alignment, not hour-beginning vs hour-ending. The assumption is leakage-safe: if rows were
  hour-ending, every label is known 1 h earlier than assumed, so forecasts are conservative. It is not harmless for the
  PV/load alignment in 9.1 or for W1 weather alignment.
- Fix, test 18. Old: `18. `test_label_hour_convention`: label rows are hour-beginning (checked against the workbook's documented timestamps`
  and `    and the start/end times in "Outage Events"); fails on a 1-h shift.`
  New: `18. `test_label_row_alignment`: the BG row index reproduces the explicit January timestamps of BG1-8760.xlsx
  Sheet2 at offset 0, with strictly more matches than at any offset in [-5, +5] (match count logged; the workbook Read Me
  reports 731 of 745); the KR workbook is read with header=None and has exactly 8,760 rows. Hour-beginning semantics are an
  assumption [JC], not tested (no source states them); they are leakage-conservative for labels, and the 9.1 PV/load
  alignment inherits them (stated limitation).`
- §0 line 26-27, old: `verified for the label workbooks by test 18 before the hash.` New: `row alignment checked by test 18
  before the hash; the interval semantics are assumed [JC] (see test 18).`
- §10 line 397, old: `Test 18 (hour convention) must pass` New: `Test 18 (row alignment) must pass`

### I2 [B] Tuning study key omits site, weather setting and label (§4 lines 143-147)
- A study is keyed by (model, target, horizon, re-tuning point). It is not stated whether W1, W2, KR-native and the S-gen
  re-run get their own studies or reuse W0/BG/primary hyper-parameters. That changes G2 (W1 vs W0), G4 (KR-native) and
  the S-gen G1 repeat, and the compute budget.
- Fix, line 144. Old: `one study per\n  (model, target, horizon, re-tuning point)` (line break after "study per").
  New: `one study per (site, weather setting, model, target, horizon, re-tuning point); the S-gen re-run reuses the
  primary-label hyper-parameters [JC] (labels differ in 4 BG hours)`. If compute forbids per-weather studies, the
  alternative is to state that W1/W2 reuse W0 hyper-parameters `[JC]` and flag G2 as conservative for weather models.
  The lead must pick one before the hash.

### I3 [B] Tuning objective for target (c) undefined (§4)
- Line 146 gives the objective only for multi-output deep models (Brier). Weibull AFT and Cox are tuned (search space line
  164), but Brier does not apply to target (c). G3 selects by inner-validation MAE (line 261). The convergence flag
  (line 158) is in Brier units.
- Fix, append to the first §4 bullet (after `Study name <-> seed mapping logged.`, line 147): `Objective: inner-validation
  Brier for targets (a)/(b); inner-validation MAE on uncensored origins (R_t scale) for target (c). The convergence flag for
  target (c) uses a relative improvement threshold set by the lead [JC; value to be fixed before the hash].` I do not
  propose a number; none is sourced.

### I4 [B for RQ3 only] Ageing temperature and source disagree between 9.3 and `method/S1_ageing_model.md`
- 9.3 line 336: "fixed cell temperature of 30 degC `[JC]`". The ageing note §5.1 uses 25 C (Arrhenius factor = 1),
  with a 35 C sensitivity.
- 9.3 line 340: cycle part "proportional to energy throughput, coefficient from ... (Naumann et al. 2020)". The ageing note
  says S-b (2020) full text was not read. Its parameters come from the 2018 dissertation, Table 5.3, and the cycle model
  is sqrt(FEC) with virtual FEC, which is not proportional to throughput.
- This does not block the forecasting hash, because the ageing file is a day-8 addendum. But the protocol is the
  controlling text, so the two must agree before day 8.
- Fix, line 336. Old: `at a fixed cell temperature of 30 degC `[JC]`` New: `at a fixed cell temperature T_cell [JC]
  (value fixed in method/S1_ageing_model.md; the lead chooses 25 C or 30 C and the other values are a sensitivity)`.
- Fix, line 340-341. Old: `- **cycle part:** proportional to energy throughput, coefficient from the same source family (Naumann et al. 2020) or,`
  New: `- **cycle part:** Naumann cycle model (form of Naumann et al. 2020, parameters from Naumann 2018 Table 5.3 as copied
  in method/S1_ageing_model.md; a throughput-linear proxy is allowed inside optimisers only, with the gap reported) or,`

### I5 [B for RQ3 only] Initial ageing state contradicts the ageing note
- 9.5 line 363: selection re-simulations start "at ... zero ageing". 9.1 gives no initial ageing state for the main run.
- The ageing note §5.2 says Q_cal must start > 0, because the sqrt-time model has an infinite rate at t = 0. With zero
  start, A is dominated by the first hours of April, and the O1 linearisation at the first month's virtual time
  is undefined.
- Fix: T7 above.

### I6 [S] "Best NF" contains a forecast-driven family (§9.4-9.7)
- N4 is "family F fed the C_B probability", so it uses a forecast. Yet 9.5 line 366 lists it among the "no-forecast
  families". G5 "F(C_ML) beats best NF" therefore tests learned-model value over the best non-ML policy, which is
  arguably the right question, but the label misdescribes it.
- Fix, line 366. Old: `The family winner among no-forecast families {N0, N1, N1r, N2, N3, N4} ("best NF")`
  New: `The family winner among the non-ML families {N0, N1, N1r, N2, N3, N4} ("best NF"; N4 uses the baseline forecast
  C_B, so G5 measures the value of a learned forecaster over the best non-ML policy; the best of N0-N3 is also reported)`

### I7 [S] F family grid incomplete (§9.4 lines 352-354)
- The charge rate c of F (and of N4, O2) is not given, and S_lo <= S_hi is not required.
- Fix, line 353. Old: `origin t; S_lo and S_hi on the N2 grid,` New: `origin t; S_lo <= S_hi on the N2 grid, c in {0.25, 0.5} C
  as in N2,`

### I8 [S] Seed-level composite undefined (§5 lines 185-187)
- "for each Q1 comparison the share of seeds with single-run dBS < 0 and the DM range over seeds" requires a seed-s
  version of C_ML. C_ML can pick a deterministic model in one fold and stochastic models with different n in others.
- Fix, append to line 187 (after `Selection in 6.2 uses seed-mean inner-validation Brier.`): `The seed-s composite
  (s = 1..10, which every stochastic model has) uses seed s of the model selected in each fold, and the single run where
  that model is deterministic; selection itself is not repeated per seed.`

### I9 [S] Fragile flag mixes adjusted and unadjusted quantities (§6.3 line 229)
- Old: `- **Fragile:** DM p-value and bootstrap CI disagree at 0.05,`
- New: `- **Fragile:** the unadjusted DM p-value and the 95 % bootstrap CI disagree at 0.05,`
- Without this, Holm-adjusted p vs an unadjusted CI disagree by construction.

### I10 [S] G2 does not state site, target and label (§7 lines 257-260)
- Old: `- **G2 weather value** (named secondary family, Holm over 5 horizons): composite C_all`
- New: `- **G2 weather value** (named secondary family, Holm over 5 horizons; BG, target (a), primary label): composite C_all`

### I11 [S] G3 criterion ambiguous (§7 lines 261-262)
- It does not say which statistic's CI must exclude 0, or on which origins.
- Old: `C-index >= 0.60 and MAE >= 10 % below the\n  training-KM conditional median, event-cluster CI excluding 0.`
  New: `pooled test C-index >= 0.60 and MAE >= 10 % below the training-KM conditional median, with the event-cluster 95 %
  CI of dMAE (model - KM) entirely below 0; all origins with y_t = 1 and uncensored R_t (event-start origins reported
  alongside).`

### I12 [S] G4 overall outcome only partly defined (§7 lines 266-268)
- PASS overall is defined. FAIL and inconclusive overall are not.
- Fix, after `and at least two are assessable.` (line 267; the sentence starts on line 266) add: `G4 fails if it
  FAILs at any assessable horizon; otherwise it is inconclusive (including when fewer than two horizons are assessable).`

### I13 [S] Baseline fit scope vs inner-validation predictions (§3 lines 108, 115)
- "over all training origins (fit once per fold)" and "fit on the full training window" (Markov) read as if inner-validation
  predictions came from the full-window fit. That would put validation labels inside the fit. Section 1.2 implies the
  inner-train fit, but the baseline bullets contradict it.
- Fix, line 104. Old: `All baselines are per-origin functions `f(history <= t, h)`, not per-fold fitted tables, unless stated.`
  New: `... unless stated. "Training window" in this section means the inner-train window when producing inner-validation
  predictions and the full training window when producing test predictions (1.2).`

### I14 [S] Test 4(a) does not cover Markov tables (§8 line 286)
- Markov-1/2 and semi-Markov are per-fold fitted tables, but only static climatology is checked for test-month
  perturbation.
- Old: `(a) static climatology for fold k is unchanged` New: `(a) static climatology, Markov-1/2 and semi-Markov
  transition/hazard tables for fold k are unchanged`

### I15 [S] Search-space gaps (§4 table lines 168, 171)
- The TCN row says "receptive field covers lookback", but the TCN lookback is never defined.
- The boosting early-stopping metric is not stated. The library default is log-loss, not Brier.
- Fix, line 171: append `; lookback as LSTM` to the TCN cell.
- Fix, line 168: change `early stop 100` to `early stop 100 on inner-validation Brier`.

### I16 [S] Disclosure: the evaluation data are not unseen (header / §7)
- The pilot already evaluated models on the same 2018 months (`DECISIONS.md` 2026-10-21: pilot GO). WP1 inspected the
  full year (`summary.json` limitation: "later evaluation months are not wholly unseen").
- Several `[JC]` values were set with that knowledge: the G1 5 % rationale from the pilot trailing-14d Brier ~0.17, H = 6,
  and the 720-h regime feature.
- This is not a harness leak, but the confirmatory family is pre-registered on data the team has already looked at. The
  protocol should say so, or a reader will.
- Fix, §7 Reporting bullet (line 271), after `a NO-GO is a primary finding;` insert: `the protocol was written after the
  pilot and WP1 EDA had used the same 2018 data, so Q1/G1-G5 are pre-specified but not on unseen data, and every paper
  states this;`

### I17 [S] Dispatch read-scope wording (§1.2 lines 68-69)
- Old: `may read inner-validation predictions and test-fold predictions whose` (line 68) + `origin lies before the first
  hour of month m` (start of line 69)
- New: `may read inner-validation and test-fold predictions, in both cases only those whose origin lies before the first
  hour of month m`
- Test 20 already enforces the strict reading; the text should match it.

### I18 [N] Minor items (no blocking effect)
- **Pre-series lags.** Lags and 720-h shares at early-January origins reach before 2018-01-01. Treat those hours as
  missing hours under §0 (state it in the YAML).
- **BCa under block resampling** (§6.3 line 227, §6.5, G4). State how the acceleration is estimated, e.g. a
  delete-one-block jackknife. If the implementation cannot do this, use percentile CIs and record a deviation. I have not
  verified what `arch` supports here.
- **Test 14 settings.** Default hyper-parameters, seed 1, one fold suffice; otherwise test 14 needs a full tuning run.
  Say which.
- **Layout** (§7 line 274). The prediction file key needs site, weather setting and label in addition to
  model x target x horizon x fold x seed.
- **PV losses.** `src/pv/model.py` defaults to `system_losses = 0.0`. The 0.14 of §9.1 must be set explicitly in the
  frozen YAML.
- **Pre-hash deliverables still missing** in the repo at `db12b22`: `config/S1_frozen.yaml` and
  `data/calendar/iraq_2018.csv`. No KR NASA POWER file is committed, so KR is W0-only unless one is added before the
  hash (as §2 already says).
- **Fixed-b polynomial** (line 217). It stays sensitivity-only until the primary source is checked. I did not verify the
  coefficients.

Checked and consistent (no action): the fold table and the 6,600 test origins; the inner-validation purge example
(line 56-57); the TC indices (k0 = 1 for h <= 24; the (b) windows end <= t); the rota-naive (a)/(b) indices; the model
count (BG 27, KR 28, k = 25 for the target-(a) ranking); CD 12.7; test 8 on the committed weather file; the G1 rationale
arithmetic (5 % of ~0.17 = 0.0085 > 0.005); the dispatch decision timing (row t+1 uses origin <= t; 1 Apr 00:00 fallback).

---

## 3. Final verdict: **FREEZE_AFTER_EDITS**

All edits are text-only; no experiment is needed before the hash.
- Must be in the hashed v1.0: T1, T3-T11, I1-I3, I6-I17.
- I4/I5 (with T7) must be in the protocol text now, because the protocol controls the day-8 ageing addendum.
- The lead must make two choices before hashing:
  - I2: per-weather tuning studies vs reuse of W0 hyper-parameters.
  - I3: the target-(c) convergence threshold.
- The §10 deliverables are still open: the YAML, the calendar file, and test 18 in its rewritten form.
