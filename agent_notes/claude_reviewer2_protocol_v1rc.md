# Reviewer 2 (independent consistency check) - S1 protocol v1.0-rc

Reviewer: Claude (Reviewer 2, consistency checker), 2026-10-22. Object: `method/S1_protocol.md` v1.0-rc (369 lines).
Checked against `agent_notes/claude_reviewer2_protocol.md` (R2, v0.9 review), `agent_notes/claude_statistician_protocol.md`
(ST, "Exact settings to freeze") and `literature/S1_protocol_v1_refs.md`. No existing file was edited, no git was run.
The only new numbers are the Nemenyi CDs in E7, computed with `scipy.stats.studentized_range` (alpha 0.05, df = 1e6, N = 9).

## 1. Verdict: **HASH_AFTER_MINOR_EDITS**

Every R2 MUST item and every ST setting is either present or changed with a `[LEAD]`/`[JC]` reason that I judge sound.
The exceptions are two silent changes (dispatch objective and primary pair, see 2.3) and one missing ST sub-item.
However, the rc has **one real leakage path** and several contradictions that would be fixed differently in code:
- **E1 (leakage):** inner-validation origins near the end of the inner-validation month have label times in the
  **test month**. Example: fold 1, origin Mar 31 23:00, h = 24, label Apr 1 23:00. Nothing in 1.1/1.2 or tests 1/20
  excludes them, and these predictions drive selection, C_B, thresholds and the seed rule.
- **E2:** section 9.5 selects dispatch parameters on *test-month* forecasts of months < m, while 1.2 and test 20 say
  dispatch parameters read **only** `predictions/innerval/`.
- **E3:** `config/S1_frozen.yaml` is hashed on day 2, but the timing-run caps are "added to the YAML" later. That
  breaks the hash.
- **E4:** dispatch does not state the site, the weather setting, or which target/horizon C_ML and C_B are selected on.
  The F rule `S(t) ... p_t` is off by one hour in notation.
- **E5:** G4 does not say whether "at h in {1, 6, 24}" means all or any of the three horizons, does not give the pass
  rule relative to the CI, and does not say which BG model is transferred.

All of these are text edits; no experiment is needed before the hash. MUST edits are in section 4.

## 2. Traceability

### 2.1 R2 MUST items (v0.9 review, sections B and C)
| Item | Where in v1.0-rc | Status |
|---|---|---|
| C0.1 / N1 label primary + S-gen | §0 Label primary/sensitivity, label_disagreement.csv, test 19 | Present. Primary = grid==0 `[LEAD]`, sound. EDA counts in §0 are S-gen (labelled); primary counts not given (SHOULD S1) |
| C0.2 / L1 / L2 hour convention, zero latency | §0 Hour convention; test 18 | Present |
| C0.3 / N11 R_t | §0 Target (c); test 9 | Present; meaning of R_t on the hour grid needs one sentence (E6, SHOULD) |
| C0.4 / L6 missing fallbacks | §0 Missing hours | Present; TC formula denominator contradicts it (E8) |
| C1.1 / N6b inner-val on every fold | §1.2 | Present; end-of-month label leakage (E1, MUST) |
| C1.2 / M6 random-split controls | §1.4 | Present |
| C2.1 static climatology wording | §3 B.3 "Reporting reference only (6.1)" | CHANGED wording: now reads as if static climatology were not a C_B candidate (E9, MUST) |
| C3.1 / N3 / N3b / N4 / N5 baselines | §3 B.1-B.9 | Present; rota-naive target (b) undefined (E10, MUST) |
| C3.2 / N10 model list | §3 enumerated list | Present (BG 27, KR 28). The count includes 2 duration-only models, so 6.4 "k = 27" is wrong (E7) |
| C4.1 / N7 horizon group / budget | §4 | Present |
| C4.2 / N8 wall-clock cap | §4 (rule frozen) | Present as a rule (option R2 allowed); YAML/hash timing conflict (E3, MUST) |
| C5.1 / N9 seeds | §5 | CHANGED to the ST precision rule `[LEAD]`. Sound, but SD10 pooling is underspecified (E11, SHOULD) |
| C6.1 / N6 strongest baseline | §6.1 | Present |
| C6.2 / N12 Q1 sidedness | §6.2 | CHANGED one-sided -> two-sided `[LEAD]` (ST). Sound: G1 adds sign and magnitude |
| C6.3 / N12 exploratory family | §6.3 last bullet | CHANGED to no p-values `[LEAD]` (ST). Sound |
| C6.5 / N2 KR parity | §6.5 | Present |
| C7.1 / N15 G1 | §7 G1 | Present (+ ST CI condition) |
| C7.2 / N16 G2-G4 | §7 | Present; G2 Holm role and G4 rule ambiguous (E5, E12) |
| C8.1 / L3 test 4 | §8 test 4 | Present |
| C8.2 tests 18-21 | §8 | Present (+22) |
| D1 dispatch | §9 + ageing addendum (day 8) | Present; E2, E4, E13 |
| L4 / L5 / L7 (SHOULD) | §1.2, §8 test 13 | Present |
| N13 / N14 / N17 (SHOULD) | §6.1, §6.3, header | Present |

### 2.2 ST "Exact settings to freeze": forecast inference and seeds/tuning
| ST line | v1.0-rc | Status |
|---|---|---|
| primary_metric | 6.1 | Present |
| loss_differential | 6.3 | Present |
| confirmatory_family | 6.2 | Present |
| q1_simple_pool | B (§3) | Present (superset: + RM, semi-Markov; static climatology membership ambiguous, E9) |
| multiplicity Holm two-sided; WY optional | 6.2 | Present |
| exploratory_comparisons | 6.3 | Present |
| dm_variance, dm_hac_lag | 6.3 | Present; L_block defined only for Q1 comparisons (E14, MUST) |
| dm_reference fixed-b primary | 6.3 | CHANGED: t_{T-1} primary, fixed-b sensitivity `[LEAD]`. Sound: the polynomial is from a secondary source (refs §2) |
| dm_hln, dm_sensitivity | 6.3 | Present |
| bootstrap_type, block_length_rule, block_length_sensitivity, B, seed, ci_method | 6.3 | Present |
| fragile_flag | 6.3 | Present (uses the t-reference DM, consistent with the change) |
| g1_add | 7 G1 | Present |
| duration_bootstrap | 6.3 | Present |
| friedman_nemenyi | 6.4 | Present; k and CD wrong (E7) |
| acf_report | 6.3 | Present |
| seeds_stochastic_models | 5 | CHANGED: SD10 on inner-val `[LEAD]` (sound); deep cap 20 `[JC]` (acceptable, cap hits reported with SE) |
| evaluation_seeds, deterministic, fm_sampling, seed_reporting | 5, 3 | Present |
| optuna_sampler, trials, pruner, objective, convergence, cap, determinism | 4, 5 | Present |

### 2.3 ST "Exact settings to freeze": dispatch
| ST line | v1.0-rc | Status |
|---|---|---|
| primary_objective J = LPSP + lambda*stress (SOC>=80 %, mean SOC) | 9.3: J = LPSP_pp + lambda*A (ageing); stress planes secondary | CHANGED **without a `[LEAD]` tag**. Sound (R2 M2 asks for a smooth ageing cost), but it must be tagged (S2) |
| lambda_grid from v2 slopes | 9.3: from the Jan-Mar NF front | CHANGED; sound (training months only). "Spanning the slopes" is ambiguous (S3) |
| constraint_variant | 9.3 | Present ("Mode-0" = ST "Blanket", assumed) |
| knob_selection, scored_months, selection_sensitivity, trajectory | 9.1, 9.5 | Present; conflicts with 1.2/test 20 (E2) |
| primary_dispatch_pair RiskTarget(RF) vs SOC-target a2 | 9.6: F(C_ML) vs best NF | CHANGED **without `[LEAD]`**. Sound (avoids picking RF post hoc) but must be tagged (S2) |
| simulator_and_forecasts | 9 intro | Present (v2 simulator, v3 forecasts) |
| dispatch_bootstrap, block, B, seed, statistics | 9.6 | Present |
| dispatch_test (sign-flip) | 9.6 | Present |
| episode_sensitivity: jackknife, top 1/3/5, **episode-resampling bootstrap** | 9.6 | Bootstrap MISSING (S4) |
| equivalence_margins | 9.7: dLPSP +/-0.10 pp; dA +/-5 % | CHANGED consistently with the A objective; not tagged (S2) |
| in_sample_minima SPA | 9.5 | Present |
| forecast_seed_spread | 9.2 | Present |

## 3. Inconsistencies, ambiguities and index checks
Index convention used here (from §0): row t = [t:00, t+1:00); origin t = instant (t+1):00; y_t is known at origin t.

- **E1 Inner-validation label leakage (MUST).**
  - 1.1 purges inner-*train* origins (t + 24 <= end of inner-train). Inner-*validation* origins are bounded only by the
    month. For fold 1 (val = Mar, test = Apr), origin t = Mar 31 23:00 at h = 24 has label Apr 1 23:00, and z_{t,24}
    covers Apr 1 00:00-23:00. Up to 24 h x 5 horizons of test-month labels per fold enter the C_ML/C_B selection,
    the TC-W/RM-N choice, thresholds, Platt, the seed rule and early stopping.
  - Test 1 covers "training" origins only, and test 6 guards test *indices* (origins), not label times. Neither test
    catches this.
- **E2 Dispatch parameter source (MUST).**
  - 1.2 says inner-val predictions are "the only input to ... ex-ante dispatch parameters (9)", and test 20 enforces it.
  - 9.5 uses "out-of-sample forecasts from the rolling folds" for months Apr..m-1, which are files in `predictions/`.
  - 9.5 is the correct, time-respecting design. 1.2 and test 20 must allow test predictions with origin month < m.
- **E3 Hash vs caps (MUST).** The YAML is hashed on day 2, but the caps are written into it later (§4, §10), so
  re-verifying the hash fails. Put the caps in a separate file, hashed as an addendum line (like the ageing model).
- **E4 Dispatch specification (MUST).**
  - Site is not stated: BG only, or BG and KR?
  - Weather setting is not stated: W0?
  - C_ML/C_B in 6.1/6.2 are selected on target (a) per horizon, while dispatch uses target (b) at H = 6. Two coders
    would select differently.
  - Off by one: 9.4 writes `S(t) = ... 1[p_t > theta]`. If S(t) is the target during hour t and p_t is the forecast
    from origin t (instant (t+1):00), the decision uses a forecast issued after hour t has ended. 9.2 and test 21 intend
    S_{t+1} from origin t; the formula must say so.
  - Worked example, hour 14:00-15:00 (row 14): the decision uses origin 13, issued at 14:00, covering
    z = max(y_14..y_19).
  - First hour of each month: the forecast from origin = last hour of month m-1 comes from fold m-1. That is
    acceptable, but 1 Apr 00:00 has no forecast (April is selection-only). State the fallback: N2 at the selected S.
  - Selection runs (9.5): initial SOC for re-simulating candidates on Apr..m-1 is unspecified. Proposal: 0.5 on 1 Apr,
    as in the main run.
- **E5 G4 (MUST).**
  - "at h in {1, 6, 24}" could mean all of them or any of them.
  - "inconclusive if CI straddles 50 %" leaves pass/fail undefined when the point estimate is >= 50 % but the CI lies
    below 50 %, which is impossible for a sensible CI but must still be stated.
  - "the BG model" is not identified. 6.5 needs per-model transfer plus a named composite for G4.
- **E6 R_t meaning (SHOULD).**
  - Event rows 10, 11, 12 (D = 3). Origin t = 12 (instant 13:00, y_13 = 0) gives R = 1, but the remaining outage
    after the origin is 0 h. Origin t = 10 (e = 1) gives R = 3.
  - So R_t = (further outage hours after the origin) + 1 = D - e + 1, where e = run length including row t. The
    definition is correct (R >= 1 for Weibull), but MAE "(h)" and the KM conditional median must use this same scale.
    Otherwise there is a 1-h bias. Say so.
- **E7 Ranking k and CD (MUST, factual).**
  - Weibull AFT and Cox are target-(c) models, so the 6.4 ranking (Brier, target (a)) has k = 25 (BG), not 27.
  - Computed CDs (N = 9): k = 25: q/sqrt2 = 3.658, CD = 12.69; k = 27: 13.83; k = 28: 14.40.
  - "k = 27: CD ~ 12" is wrong under either reading.
- **E8 TC formula vs missing rule (SHOULD).** The formula divides by (W + 1); §0 says "denominator = available days".
  - Index check (a): h in {1..24} gives k0 = ceil(h/24) = 1; label times t+h-24k <= t for all k >= 1. Correct.
    Example h = 24, k = 1: label time t, at the same clock hour as t+24. Correct.
  - Index check (b): window rows (t-24k, t-24k+h], last row t-24k+h <= t because h <= 24 <= 24k. Correct, and the
    window is aligned in clock hour with (t, t+h].
  - Only the denominator needs to change.
- **E9 Static climatology in B (MUST, short).** "Reporting reference only (6.1)" can be read as excluding it from C_B
  selection, which changes C_B. R2 C3.1 said: in B for selection, not the go/no-go reference.
- **E10 Rota-naive (b) undefined (MUST).**
  - Index check (a): h = 1 gives y_{t-1}; h = 3 gives y_{t-1}; h = 6, 12, 24 give y_t. Each matches the most recent
    row <= t with the clock parity of t+h. Correct.
  - Parity of index = parity of clock hour, because days have 24 rows and there is no DST.
  - For (b) at h >= 2 the window contains both parities, so the natural definition is max(y_{t-1}, y_t). B claims all
    members produce (a) and (b).
- **E11 Seed rule details (SHOULD).** "Pooled inner-validation Brier" should say: pooled over the inner-validation
  months of all 9 folds, decided once after seeds 1-10 have run on all folds. Extra seeds 11..n run on all folds.
  Example: SD10 = 0.002 gives n = max(10, ceil(16)) = 16. Note also that the 1.4 split-draw seeds 0-4 are a separate
  namespace from model seeds.
- **E12 G2 (SHOULD).** G2 is "Holm over 5 horizons", but the criterion lists only dBS and a CI, so Holm decides
  nothing. Require Holm-significance as in G1.
- **E13 Dispatch details (SHOULD).**
  - (i) Calendar ageing is sqrt-time with a virtual-time state (refs Eq. 5.15/5.17). The ageing rate depends on
    accumulated Q_loss, so a DP over SOC alone (O1) is not exact, and per-month A is not additive. The initial Q_loss
    on 1 Apr is unspecified.
  - (ii) Headline J for G5 is not stated as pooled May-Dec (sum unserved / sum load) vs a mean of monthly J.
  - (iii) Grid charging in N2/F happens only if the grid is on in hour t+1. That is realised physics, not a forecast;
    state it.
- **E14 L_block scope (MUST).** The rule is defined "per confirmatory comparison", but L_block/L_HAC are also needed
  for G2 (DM + CI), G4 (KR d_t), BSS CIs and the exploratory CIs. Extend the rule to every comparison.
- **E15 Small items (SHOULD).**
  - Target (b) scoring when some y_{t+1..t+h} are missing is not covered.
  - The static climatology for (b) has no smoothing stated.
  - FM (b) uses p_{t+k}, which needs k-step forecasts for every k = 1..h, not only the 5 horizons.
  - The calendar file has no rule for items listed by neither source (Ramadan start, 12 May, Arbaeen). Refs §4
    suggests a separate uncertain-holiday flag.
  - 1.2 says "every evaluation seed"; deterministic models have one run.

## 4. Edits (old -> new)

**[MUST] M1 (E1) - §1.1, purge bullet.**
Old: `same rule between inner-train and inner-validation. Test origins start at the first hour of the test month.`
New: `same rule between inner-train and inner-validation. Inner-validation origins are kept only if t + h <= T_train_end
(per horizon; target (b) the same), so no inner-validation label lies in the test month. Test origins start at the first
hour of the test month.`
And test 1. Old: `(all folds, horizons,\n   targets; also inner-train vs inner-validation).`
New: `(all folds, horizons, targets; also inner-train vs inner-validation, and every inner-validation (origin,
label-time) has label_time <= T_train_end).`

**[MUST] M2 (E2) - §1.2 and test 20.**
Old (1.2): `Platt scaling, the seed rule (5) and\nex-ante dispatch parameters (9).`
New: `Platt scaling and the seed rule (5); ex-ante dispatch parameters (9.5) use only predictions whose origin lies in
months before the month they are applied to.`
Old (test 20): `and selection,\n    threshold, seed-rule and dispatch-parameter code reads only predictions/innerval/.`
New: `and selection, threshold and seed-rule code reads only predictions/innerval/; dispatch-parameter code for month m
reads only predictions with origin < first hour of m.`

**[MUST] M3 (E3) - §4 cap bullet and §10.**
Old: `values go to config/S1_frozen.yaml before any test prediction.`
New: `values go to config/S1_timing_caps.yaml, whose SHA-256 is appended to results/S1/PROTOCOL.sha256 (addendum line)
before any test prediction; config/S1_frozen.yaml is not changed after the hash.`
Old (§10): `values added to the YAML before any\n  test prediction`
New: `values written to config/S1_timing_caps.yaml and hashed as an addendum before any test prediction`

**[MUST] M4 (E4) - §9.2, first two sentences.**
Old: `A decision applied during hour t+1 uses only forecasts with origin <= t. Look-ahead H = 6 h [JC]; input = target (b)
z_{t,H} probability. Primary forecast = C_ML (per-fold selected,`
New: `Site BG; weather W0; primary label. A decision applied during hour t+1 (row t+1) uses only forecasts with origin
<= t. Look-ahead H = 6 h [JC]; input = target (b) probability p_t = P(z_{t,H} = 1) from origin t. C_ML and C_B for
dispatch are selected per fold on inner-validation Brier of target (b) at h = H (not target (a)). For row 1 Apr 00:00
(no forecast) every forecast family uses its S_lo. Primary forecast = C_ML (per-fold selected,`
And §9.4. Old: `` `S(t) = S_lo + (S_hi - S_lo) * 1[p_t > theta]` `` New: `` `S_{t+1} = S_lo + (S_hi - S_lo) * 1[p_t > theta]` (target SOC during row t+1, forecast from origin t) ``
And §9.5, append: `Each candidate is re-simulated on Apr..m-1 from SOC 0.5 on 1 Apr.`

**[MUST] M5 (E5) - §7 G4 and §6.5.**
Old: `BG->KR retains >= 50 % of it at h in {1, 6, 24}; inconclusive if
  the BCa CI of the ratio straddles 50 %;`
New: `the retained share (BSS_strong of BG->KR C_ML / KR-native BSS_strong) has a BCa CI lower bound >= 50 % at each
  of h = 1, 6 and 24 (pass); upper bound < 50 % at any of them (fail); otherwise inconclusive;`
§6.5, append to Transfer: `Every BG model is transferred; G4 uses the composite C_ML selected per fold on BG
inner-validation (transferred) vs KR-native C_ML selected on KR inner-validation; the KR-native gate (> 0.02) is applied
per horizon.`

**[MUST] M6 (E7) - §6.4.**
Old: `(k = 27: CD ~ 12 rank units)`
New: `(k = 25 target-(a) models in BG, 26 in KR, Weibull/Cox excluded; BG CD = 12.7 rank units at N = 9)`

**[MUST] M7 (E9) - §3 B.3.**
Old: `Reporting reference only (6.1).`
New: `Member of B (candidate for C_B); the BSS_clim reference (6.1); not the go/no-go reference.`

**[MUST] M8 (E10) - §3 B.9.**
Old: `(most recent hour <= t with the clock parity of t+h).`
New: `(most recent hour <= t with the clock parity of t+h); (b) y_{t-1} at h = 1, max(y_{t-1}, y_t) at h >= 2.`

**[MUST] M9 (E14) - §6.3 bootstrap.**
Old: `seed 20180102. Block length per confirmatory comparison:`
New: `seed 20180102. Block length per comparison (confirmatory, G2, G4 and every exploratory CI; computed on that
comparison's d_t, for G4 on the KR d_t):`

**[SHOULD] S1 (C0.1) - §0 series bullet:** append `Primary label (grid==0): counts from the WP1 rerun, written to
data_audit.csv before the hash.` (Do not insert 4,328 here unless the rerun confirms it.)

**[SHOULD] S2 (2.3) - §9.3 first line:** prefix with `[LEAD] (ST proposed J = LPSP + lambda*stress and RiskTarget(RF) vs
SOC-target a2; replaced by a smooth ageing cost (R2 M2) and F(C_ML) vs best NF, so that no forecaster is chosen post hoc;
the stress planes stay secondary.)`

**[SHOULD] S3 (lambda grid) - §9.3.**
Old: `5 log-spaced values\nspanning the slopes of the no-forecast front`
New: `5 log-spaced values between the smallest and largest |dLPSP_pp/dA| of adjacent points on the Pareto front of N2
on Jan-Mar`

**[SHOULD] S4 - §9.6.** After `(episode = outage event + preceding 24 h).` add: `Secondary: episode-resampling
bootstrap within month (ST).`

**[SHOULD] S5 (E6) - §0 Target (c):** append: `R_t - 1 = further outage hours after the origin; for an event of length D
seen at elapsed e (run length including row t), R_t = D - e + 1. MAE and the KM reference use this scale.`

**[SHOULD] S6 (E8) - §3 B.4:** Old `+ 0.5) / (W + 1)` New `+ 0.5) / (n_avail + 1)`, with n_avail = the available days
among the W (= W if none are missing).

**[SHOULD] S7 (E11) - §5:** after `over seeds 1-10` add `(pooled over the inner-validation months of all 9 folds; decided
once, then seeds 11..n run on all folds)`.

**[SHOULD] S8 (E12) - §7 G2.**
Old: `vs under W0, dBS <= -0.003`
New: `vs under W0, Holm-significant (two-sided DM) AND dBS <= -0.003`

**[SHOULD] S9 (E13) - §9.3.** Add:
- `A is accumulated with the virtual-time form (Naumann Eq. 5.15/5.17 as copied); initial Q_loss on 1 Apr = 0 [JC].`
- `O1 uses the hourly ageing increment linearised at the start-of-month Q_loss (stated as an approximation).`
- `Headline J = pooled May-Dec LPSP_pp + lambda * A(May-Dec).`
- `Grid charging happens only in rows with realised grid supply.`

**[SHOULD] S10 (E15) - §0, §3, §2.**
- (b) is scored only if all of y_{t+1..t+h} are observed.
- Static climatology (b) uses the same 0.5/1 smoothing.
- FM (b) uses `p_{t+k}` = the k-step forecast from origin t, for k = 1..h.
- Calendar: dates listed by only one source, or by neither (Ramadan start, 12 May, Arbaeen), get a separate
  `uncertain_holiday` flag. The main run uses the certain flag; the sensitivity run adds the uncertain flag.
