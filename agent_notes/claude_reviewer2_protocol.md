# Reviewer 2 - S1 protocol v0.9

Reviewer: Claude (acting as Reviewer 2), 2026-10-22. Object: `method/S1_protocol.md` (DRAFT v0.9, 189 lines).
Also read: `agent_notes/claude_reviewer2_S1.md` (pilot review), `studies/S1_outage_forecasting/PLAN.md`, `PLAN_2W.md`.
I edited no existing file, ran no code and ran no git. Every number below comes from those four files. I produced no new
results.

## Verdict: **FREEZE_AFTER_EDITS**

The forecasting half is close to freezable. The splits, purge, tuning budget, inference design, confirmatory family and
leakage tests are careful and mostly unambiguous. Four things block a v1.0 freeze:

1. **The skill reference is still the weak reference that the pilot review overturned (M1).** BSS and G1 use the
   expanding hour-of-day climatology, which scored Brier 0.251 in BG in the pilot. The trailing-window climatology,
   recency Markov and semi-Markov baselines are missing from the classification targets, and there is no
   "strongest baseline" rule.
2. **The label decision from M5 is not taken.** The label is still `generator > 0`, with no `grid_kwh == 0` sensitivity
   run and no handling of the KR odd/even-hour pattern. G4 depends on KR.
3. **There is no dispatch (RQ3) section.** M2, M7 and SHOULD 1/3/5/7 cannot be honoured by a protocol that never mentions
   dispatch. WP7 is on day 9, and nothing currently stops its policy families, oracle, ageing cost and threshold rule from
   being chosen after the forecasts are seen.
4. **Several numeric or semantic choices can be implemented two ways.** These include the "horizon-group", the wall-clock
   cap, how inner-validation predictions are produced on folds that are not re-tuned, Q1 sidedness, the R_t definition,
   the hour-timestamp convention, Markov homogeneity, baseline definitions for target (b), and the "rerun with 20 seeds"
   rule. The WP2 harness is being written now, so each of these will be fixed in code by default if the text does not
   fix it.

All four can be fixed with text edits (section C). None needs new experiments before the freeze. Two harness-relevant
points should go to the WP2 implementer **today**, before the freeze: (i) save inner-validation predictions for every
fold, model and seed; (ii) do not implement leakage test 4 as written, because it would fail for a legitimate
trailing-window baseline (see L3).

---

## A. Pilot findings vs protocol v0.9

Legend: **Yes** = handled; **Partial** = partly handled, gap named; **No** = not handled; **N/A** = report-text issue
that a protocol cannot fix, with the relevant protocol hook noted.

### A.1 MUST-FIX M1-M7
| Item | Status | Where / quote | Gap |
|---|---|---|---|
| M1 weak climatology; add trailing-window clim, seasonal-naive, recency Markov; skill vs **strongest** baseline | **Partial (main point not addressed)** | §2 "the reference is `p_clim(hour) = (n_out(hour) + 0.5) / (n(hour) + 1)` over all training origins; a last-training-month variant is reported as an extra baseline"; §3 seasonal-naive `p = y_{t+h-24}`; §6.1 "BSS = 1 - BS/BS_clim (training-only climatology)" | The primary reference is exactly the expanding hour-of-day mean that M1 showed collapses to Brier ~0.25 (BG). The "last-training-month" variant is static over the test month, so it is not the per-origin trailing window of M1. There is no trailing 7/14/28-d climatology and no recency Markov. There is no strongest-baseline rule for BSS: Q1's "best simple model" set omits the strong baselines. Seasonal-naive was added (good). |
| M2 no-forecast policy families for dispatch; smooth ageing cost | **No** | No dispatch section | RQ3/WP7 are absent from the protocol. |
| M3 "power limit" claim false | **N/A** | §7 "Manuscript tables generated from `metrics/` and `inference/` only" | Report text. The dispatch section should still require an energy- vs power-limited decomposition of unserved energy. |
| M4 untraceable report numbers | **Partial** | §7 layout; "Manuscript tables generated from metrics/ and inference/ only" | Covers forecasting tables. Dispatch outputs and interpolations (the M4 KR chord) are not covered, because dispatch is absent. |
| M5 label ground truth; `grid_kwh==0` primary + sensitivity; KR odd/even; suppressed demand | **Partial (weak)** | §0 "`y_t = 1` if generator energy in hour t > 0 ... Reported as a limitation; not corrected." | There is no `grid==0` sensitivity run and no disagreement-hour count (BG 4 h, KR 14 h per pilot). The KR odd/even pattern (65.4 % of outage hours on odd clock hours) is not mentioned. The phrase "can under-count outages" is not quantified, though the pilot crosstab quantifies it. PLAN.md keeps generator>0 as the operational target, so this is a decision the lead must record either way. |
| M6 random-split confound; add the two control columns | **Partial** | §1.4 "Report `dBS_leak = BS_random - BS_rolling`"; quarantine (test 16) | Only random vs rolling is reported. The random split is scored on Jan-Dec while rolling is scored on Apr-Dec, and the random split's training set includes future months. The pilot's two controls are missing: blocked month-CV with future months and a 7-d embargo, and random split scored on Apr-Dec rows only. |
| M7 "Perfect" is not an oracle; DP/MILP oracle frontier, regret | **No** | No dispatch section | |

### A.2 SHOULD-FIX 1-9
| Item | Status | Where / quote | Gap |
|---|---|---|---|
| S1 decision-time alignment | **Partial** | §2 heading "Information available at the forecast origin (end of hour t)"; lags `y_{t-k}, k = 0..48` | The origin is defined, but the clock convention of the hourly label (hour-beginning vs hour-ending) is not stated. The latency assumption is not stated. The mapping from forecast to dispatch decision hour is absent. Test 8 checks weather time only, not labels. |
| S2 raw `month` feature | **Yes** | §2 "Month and day-of-year excluded `[JC]`: with one year the test month is always an unseen level." | I agree. Optional: add a 720-h outage-share feature so regime level is still visible (SHOULD). |
| S3 `max_k` aggregation vs P(any outage) | **Yes for forecasting** | §0 Target (b) `z_{t,h} = max(y_{t+1..t+h})` | Dispatch must use target (b) directly, which needs the dispatch section to say so. FMs use an independence product for (b) (§3), flagged `[JC]`: acceptable. |
| S4 Markov straw man; semi-Markov / duration hazard | **Partial** | §3 "Markov-1/2 ... Duration: Weibull AFT and penalised Cox PH" | Duration models are used only for target (c). No run-length-aware baseline exists for targets (a)/(b), so "ML beats Markov" can still mean "run length matters". Markov homogeneity and fit window (expanding vs recent) are unspecified. |
| S5 simulator details (topology, efficiencies, SOC definition, C-rate confound, clipped PV) | **No** | - | Dispatch absent. |
| S6 stale cache / reproducibility | **Partial** | §7 `config/` (frozen YAML, git commit, environment lock); test 17 determinism | There is no rule that caches are keyed by a config/feature hash, and no clean-rerun requirement. |
| S7 ex-ante threshold | **Partial** | §6.1 "MCC and F1 at the MCC-maximising threshold on inner-validation"; test 7 | Handled for classification metrics, but inner-validation predictions come from the inner-train model while test predictions come from the refit model (see N7). There is no ex-ante dispatch threshold. |
| S8 PV model (zenith consistency, losses, NOCT, NASA bias, offset grid) | **No** | Test 8 covers only the time base | This belongs in the dispatch section or in a PV-model note that the dispatch section references. |
| S9 KR weather proxy (Baghdad weather for KR) | **No** | §6.5 silent on KR weather | Either state that KR transfer is W0 only, or require the KR NASA POWER series. |

### A.3 Statistical weaknesses
| Weakness | Status | Where / quote | Gap |
|---|---|---|---|
| Per-hour losses saved | **Yes** | §7 "`predictions/` (parquet per model x target x horizon x fold x seed)" | Add inner-validation predictions (N6). |
| DM with HAC vs **strongest** baseline | **Partial** | §6.3 "Diebold-Mariano (1995) with Newey-West (1987) HAC variance, lag `L = max(h - 1, 24)`" | The test is fine, but the comparator set lacks the strong baselines (M1). Q1 sidedness is not stated. |
| Block-bootstrap CIs (forecasting) | **Yes** | §6.3 "circular moving-block bootstrap ... block 48 h, B = 5,000, blocks resampled within test month" | |
| Fold-wise dispersion | **Yes** | §6.1 "pooled ... and per fold"; §6.4 per-fold rank tables | |
| Friedman/Nemenyi only after DM, with caveat | **Yes** | §6.4 "Caveat printed with every diagram ... ranking descriptive only" | |
| "27 of 27" is not a test | **Yes** | §6.2 confirmatory family Q1, Holm | |
| RF vs Logistic needs a test | **Yes (exploratory)** | §6.3 "All other pairs: Holm-adjusted p-values, labelled exploratory" | The Holm family for "all other pairs" is undefined (N12). |
| Dispatch single trajectory; bootstrap LPSP differences | **No** | - | Dispatch absent. |
| Low power, one year | **Partial** | §7 "a NO-GO is a primary finding" | Good. Add a minimum-detectable-effect statement or a simulation-free power remark (SHOULD). |

---

## B. Remaining leakage risks, ambiguities and unfixed numbers

Each item is something two competent coders could implement differently, or something that lets information leak. The
severity tag matches section C.

### B.1 Leakage risks
- **L1 Hour-timestamp convention (MUST).** §0 fixes the weather time base. It never says whether the label row "hour t"
  covers [t:00, t+1:00) (hour-beginning) or [t-1:00, t:00) (hour-ending). If the workbook is hour-ending and the harness
  assumes hour-beginning, then `y_t` at "end of hour t" is really one hour later than assumed, and W1 weather is
  misaligned by 1 h relative to the label. The pilot's +30 min PV offset implies the weather is hour-beginning. That says
  nothing about the label workbook. A test is needed (the dispatch alignment also depends on it).
- **L2 Zero-latency assumption (SHOULD).** The protocol implicitly assumes the label of hour t is known at (t+1):00.
  That is realistic for a household, which sees its own grid state. Say so explicitly. Also note that the instantaneous
  state at (t+1):00, which a real controller has, is deliberately *not* used, so h=1 skill is conservative.
- **L3 Leakage test 4 conflicts with the M1 fix (MUST).** `test_climatology_training_only` requires climatology to be
  "unchanged when test-month labels are shuffled or zeroed". A trailing-window climatology at origin t legitimately uses
  test-month labels at times <= t, so the test would fail, or would push the coder to make the baseline static (the M1
  error again). Split the test in two: static references are unchanged under any test-label change; per-origin baselines
  are unchanged under changes to labels at times > t.
- **L4 Threshold and calibration transfer (SHOULD).** The MCC threshold and the SVM Platt map are fitted on
  inner-validation predictions of the *inner-train* model, then applied to the *refit* model (§1.2). This is not
  leakage, but it is a mismatch, and coders will resolve it differently: refit + reuse, or no refit for SVM. Fix one
  choice.
- **L5 Early stopping and tuning on the same inner-validation month (SHOULD, disclose).** The best epoch/round and the
  Optuna objective both use inner-validation. This makes selection slightly optimistic, but test months are untouched.
  It is acceptable; record it as `[JC]`.
- **L6 Missing-value fallbacks for baselines (MUST, short).** PLAN.md requires "baseline fallback behavior" to be frozen.
  §0 covers missing-indicator features only. It is unspecified what seasonal-naive, persistence, Markov or trailing
  climatology output when their input hour is missing, and what fill value the lag feature itself gets. This matters
  mostly for KR.
- **L7 Canary test 13 is underspecified (SHOULD).** Should the labels be permuted with features recomputed from the
  permuted series, or should only the target column be permuted while features stay unpermuted? The second option is
  the one that should give BSS ~ 0. Say which.

### B.2 Outage label
- **N1 Primary label not decided; no sensitivity (MUST).** The pilot crosstab shows that for BG, `gen>0` and `grid==0`
  differ in exactly 4 h (grid==0 & gen==0). For KR they differ in 14 h, plus 1 h where both are > 0. These hours are
  where the neighbourhood generator was off during a cut, or where data is anomalous. The impact on BG is tiny; it is
  about 1 % of KR outage hours. "Not corrected" is not acceptable for a frozen protocol, because PLAN.md asks to "expose
  disagreements". Freeze both a primary and a sensitivity label, and state that Q1/G1 are re-run on the sensitivity label.
- **N2 KR odd/even-hour pattern (MUST for G4 / §6.5).** The pilot found 65.4 % of KR outage hours on odd clock hours,
  with outage-start counts alternating by hour. Either it is a 2-h rota with a fixed phase, which the hour-of-day
  climatology can capture and which needs a parity-aware naive baseline if the phase drifts, or it is an aggregation
  artefact (for example a half-hour shift). The protocol must pre-register a diagnostic and the consequence of each
  outcome. Otherwise KR results are uninterpretable and the decision on how to treat them will be made after seeing them.

### B.3 Baselines
- **N3 Trailing-window climatology missing (MUST).** Define it per origin. W in {7, 14, 28} d. Use only labels at target
  times `t+h-24k <= t`, i.e. k >= ceil(h/24). Use the same 0.5/1 smoothing. State whether W is chosen on
  inner-validation or all three are reported.
- **N4 Markov specification ambiguous (MUST).** It is not said whether the transition matrix is time-homogeneous or
  hour-of-day-dependent (the pilot used an "HourMarkov"), or whether it is fitted on the full window or recent days.
  Recency Markov: last N in {7, 14, 28} days, refit at 00:00 of each test day using transitions whose both endpoints
  are <= t.
- **N5 No run-length-aware baseline for targets (a)/(b) (MUST).** Add a semi-Markov (alternating-renewal) baseline: an
  empirical discrete hazard of ON and OFF spells by elapsed duration, Laplace 0.5, durations > 48 h pooled, propagated h
  steps by exact recursion over (state, elapsed duration). An hour-of-day logistic-hazard variant is optional.
- **N3b Baselines for target (b) undefined (MUST).** Seasonal-naive (b) = `max(y_{t+1-24..t+h-24})`, valid since h <= 24.
  Climatology (b) = training frequency of `z` by origin hour (and trailing analogue). Persistence (b) = `y_t`. Markov (b)
  is already defined (absorbing chain).
- **N6 Strongest-baseline rule absent (MUST).** BSS needs a reference set and a selection rule. Proposed: per fold,
  pick the baseline with the lowest inner-validation Brier from the frozen baseline set B, then pool. Report BSS against
  both (i) static climatology, for comparison with the literature and the pilot, and (ii) the strongest baseline, which
  is used for G1. Add an ex-post "best baseline on test" as a conservative sensitivity, never used for a claim.
- **N6b Inner-validation predictions on folds that are not re-tuned (MUST).** Q1 selects "per fold by
  inner-validation Brier", but re-tuning happens only at folds 1, 4 and 7. On folds 2, 3, 5, 6, 8 and 9 the protocol must
  say that every model is fit on that fold's inner-train with the reused hyper-parameters and scored on that fold's
  inner-validation, for all seeds. These predictions must be saved, because they are also needed for thresholds, Platt
  scaling and the dispatch threshold. FMs and untuned baselines also need inner-validation predictions.

### B.4 Tuning, seeds, models
- **N7 "horizon-group" undefined (MUST).** §4 says "60 trials per (model, target, horizon-group, re-tuning point)". If a
  group is {1,3,6,12,24}, ML direct models share one study across 5 separate models. If it is one horizon, deep
  multi-output models get 5x the budget per horizon. Define it, for example {1,3} {6,12} {24}, or "per horizon" for
  direct models and "per target" for multi-output models with 5x60 = 300 trials. Equality must be stated per model and
  target, not per study.
- **N8 Wall-clock cap still open (MUST).** If the cap binds for some families and not others, the trial budget is no
  longer equal. Freeze either a number, or a rule (for example "cap = 3 x median trial time from the timing run x 60;
  trials completed under the cap are used; the count of completed trials is reported per study"). Also state whether
  pruned trials count toward the 60. Optuna counts them; say so.
- **N9 Seeds (MUST, short).** "rerun with 20 seeds" could mean 10 more or 20 new. List the seed values (for example
  0..9, 0..29, extension 10..19). State the seed used for tuning trials of tree/boosting models (only deep is stated).
  Record the deviation from PLAN.md ("30 seeds for stochastic models") for the deep models. The SD trigger compares a
  seed SD with an effect size: fine, but say whether it is computed per (target, horizon) or on the overall pooled value.
- **N10 Model count (SHOULD).** "Models (24)" is not reconcilable without a list. Baselines 6 + duration 2 + ML 7 + deep
  5 + FM 4 = 24 if KM is excluded. Adding N3/N4/N5 makes 27. Freeze an explicit list. State that FMs are not run on
  target (c).
- **N11 R_t off-by-one (MUST, short).** "hours from t to the first hour with y = 0" can be read as `k` or `k-1`. Fix it
  as `R_t = min{k >= 1 : y_{t+k} = 0}` (>= 1, so Weibull is valid).

### B.5 Inference and go/no-go
- **N12 Q1 sidedness and the exploratory Holm family (MUST).** Q1 asks "is ... better than", so state that it is
  one-sided, H1: E[d_t] < 0. Define the family for "all other pairs", for example per (target, horizon, weather), all
  pairs among the 27 models.
- **N13 Pooled BSS definition (SHOULD).** State that it is a ratio of means, `1 - sum BS_model / sum BS_ref` over pooled
  origins, not a mean of per-fold ratios.
- **N14 HLN with L != h-1 (SHOULD).** The HLN factor is derived for an (h-1)-truncated rectangular kernel. With n ~ 6,600
  it is negligible either way; state "HLN factor computed with h; t_{n-1} reference".
- **N15 G1 rationale (SHOULD).** "0.005 ~ 2 % of a ~0.25 Brier" uses the weak-climatology Brier. Against a strong
  baseline (pilot trailing-14d BG BSS 0.31 vs the 0.25 reference, i.e. Brier ~0.17) the 5 % relative criterion is the
  binding one. That is fine, but rewrite the rationale. Specify that the >= 2 of 5 horizons count includes at least one
  of h in {1, 3, 6}, which keeps the pilot's 1-6 h intent, or state that the pilot criterion is superseded.
- **N16 G2/G3/G4 selection (MUST, short).** G2: which model is compared, W1 vs W0? Use the same per-fold
  inner-validation-selected composite under each weather setting. G3: "best duration model" is selected by
  inner-validation MAE. G4: the BSS ratio is undefined when KR-native BSS <= 0; state the rule. G4 uses the strongest
  KR baseline.
- **N17 Freeze scope (SHOULD).** Hash the calendar file and the frozen YAML together with the protocol. State that
  PLAN.md's pilot go/no-go is superseded by §7.

### B.6 Dispatch evaluation (RQ3) - entirely missing
- **D1 (MUST).** Either add §9 (proposed text in C.9) or add a sentence that RQ3 is governed by an addendum
  `S1_protocol_dispatch.md`, hashed before any dispatch run on test months and no later than day 8, and that no RQ3 claim
  can rest on v1.0. In both cases v1.0 must already fix what WP2 must *save* for WP7: target (b) at the dispatch
  look-ahead H, issuance time, and inner-validation predictions.
- **D2.** Policy families without forecasts (M2), a true oracle (M7), a smooth ageing cost (M2.3), ex-ante threshold
  and parameter selection (S7), decision alignment (S1), a rate-matched Mode 0 (S5d), and a consistent SOC definition
  (S5c) all belong in the dispatch text.
- **D3.** Suppressed demand: outage-hour load = generator energy, capped by the subscription (M5). Pre-register a
  sensitivity using a load model, or state it as a limitation in every RQ3 table.

---

## C. Proposed text edits for v1.0

Format: **[MUST|SHOULD] Cn - section** / *replace* quoted v0.9 text (or *insert after*) / proposed wording. Where I
propose a numeric value it is marked `[JC]` with a rationale. The lead may change the number before the freeze, but some
number must be frozen.

### C.0 Section 0 - Data and targets
**[MUST] C0.1 - Label.** *Replace* the "Label (proxy)" bullet with:
> - **Label (proxy), primary.** `y_t = 1` if `grid_kwh_t == 0` (no metered grid energy in hour t), else 0 `[JC]` (closest
>   observable to grid unavailability; does not depend on whether the household ran its generator).
> - **Label, sensitivity (S-gen).** `y_t = 1` if `generator_kwh_t > 0`. Disagreement hours (BG: 4 h grid==0 & gen==0;
>   KR: 14 h grid==0 & gen==0, 1 h both > 0; to be recomputed and written to `results/S1/label_disagreement.csv`) are
>   listed with timestamps. Q1, G1 and the Q1 tables are re-run on S-gen; if the G1 decision differs between labels,
>   both are reported and G1 is labelled *label-sensitive*.
> - Neither label is independently verified grid status. "National Status" is derived from grid energy, so agreement
>   with it is not validation. Abstract and every table caption state that labels are inferred from metered consumption.

(If the lead prefers to keep `generator > 0` as primary, for consistency with PLAN.md and the WP1 EDA, swap the two.
What blocks the freeze is the absence of a frozen sensitivity run, not which label is primary. Update the EDA numbers
in §0 accordingly: under grid==0, BG has 4,328 outage hours instead of 4,324, per the pilot crosstab.)

**[MUST] C0.2 - Time convention.** *Insert after* "Time base":
> - **Hour convention.** Row "hour t" covers local clock interval [t:00, t+1:00) (hour-beginning) for labels, load and
>   weather; this is verified for the label workbooks by `test_label_hour_convention` (section 8) before the freeze
>   hash. The **forecast origin t** is the instant (t+1):00. The label of hour t is assumed known at the origin (zero
>   latency) `[JC]` (household observes its own supply). The instantaneous state at (t+1):00 is NOT a feature, so h = 1
>   skill is conservative.

**[MUST] C0.3 - Duration.** *Replace* "remaining duration `R_t` = hours from t to the first hour with y = 0" with:
> remaining duration `R_t = min{k >= 1 : y_{t+k} = 0}` (integer hours, >= 1)

**[MUST] C0.4 - Missing data / fallbacks.** *Replace* the "Missing hours" bullet with:
> - **Missing hours** are never imputed as labels and are excluded from scoring (origin or label time missing). Lag
>   features touching a missing hour take the value of the training-window outage share and a missing indicator = 1.
>   Baseline fallbacks: persistence / seasonal-naive / rota-naive with missing input -> static climatology `p_clim`;
>   Markov / semi-Markov with missing current state -> static climatology; trailing climatology uses the available days
>   in the window (n in the denominator = available days), falling back to `p_clim` if fewer than 3. Counts in
>   `results/S1/data_audit.csv`.

### C.1 Section 1 - Splits
**[MUST] C1.1 - Inner-validation on every fold.** *Replace* section 1.2 with:
> Tune on inner-train, score on inner-validation (section 4) at re-tuning folds. **On every fold** (re-tuned or not),
> every model is fit on that fold's inner-train with the current hyper-parameters, for every seed, and its
> inner-validation predictions are saved to `predictions/innerval/`. These predictions are the only input to per-fold
> model selection (6.2), thresholds (6.1), Platt scaling, and ex-ante dispatch parameters (9). The model is then refit on
> the full training window; iterative models use the early-stopped round/epoch count `[JC]`. Thresholds and Platt
> parameters estimated on the inner-train model are applied unchanged to the refit model `[JC]` (no third split).
> Early stopping and the tuning objective share the inner-validation month (slightly optimistic selection; test months
> untouched) `[JC]`.

**[MUST] C1.2 - Random-split controls (M6).** *Replace* the second sentence of 1.4 onwards with:
> Report for each model/horizon: (i) rolling-origin (main), (ii) blocked month-CV with future months allowed and a 7-day
> embargo, (iii) random 80/20 scored on all rows, (iv) random 80/20 scored on Apr-Dec rows only. Report
> `dBS_leak = BS_(iv) - BS_(i)` and the decomposition (ii)-(i) (future-regime + size) and (iv)-(ii) (temporal
> adjacency), range over 5 draws. Written only to `results/S1/leakage_randomsplit/`; never used for selection, ranking or
> go/no-go (test 16).

### C.2 Section 2 - Information at the origin
**[MUST] C2.1 - Static climatology wording.** *Replace* the "Training-only climatology" bullet with:
> - **Static climatology** `p_clim(hour)` = `(n_out(hour) + 0.5) / (n(hour) + 1)` over all training origins (fit once per
>   fold; labelled "expanding hour-of-day climatology"). It is a *reporting* reference only; the skill reference for
>   go/no-go is the strongest baseline (6.1). The last-training-month variant is dropped (superseded by the trailing
>   climatology in section 3) `[JC]`.

**[SHOULD] C2.2 - Load and regime features.** *Insert after* "Lags":
> - **Load:** total household consumption is NOT a feature in v1.0 `[JC]` (in outage hours it equals generator energy
>   and is capped by the subscription; RQ2 load ablation deferred to a declared exploratory analysis). Add outage share
>   over the past 720 h (regime level, replacing the excluded month).

**[SHOULD] C2.3 - KR weather.** *Insert in* "Weather settings":
> KR uses W0 only unless the KR NASA POWER series (32.6136 N, 44.0430 E) is committed before the freeze; Baghdad
> weather is never used as a KR covariate.

### C.3 Section 3 - Models
**[MUST] C3.1 - Baselines.** *Replace* the "Baselines" bullet with:
> - **Baseline set B** (all untuned except where stated; all produce targets (a) and (b)):
>   1. persistence `p = y_t`; (b) `y_t`.
>   2. seasonal-naive `p = y_{t+h-24}`; (b) `max(y_{t+1-24 .. t+h-24})` (h <= 24, all inputs <= t).
>   3. static climatology (section 2); (b) training frequency of `z_{.,h}` by origin hour.
>   4. **trailing climatology** TC-W, W in {7, 14, 28} days, recomputed at every origin:
>      `p = (sum_{k=k0}^{k0+W-1} y_{t+h-24k} + 0.5) / (W + 1)`, `k0 = ceil(h/24)` (all label times <= t); (b) same with
>      `z_{t-24k,h}` restricted to windows ending <= t. W selected per fold on inner-validation Brier `[JC]`; all three
>      reported.
>   5. Markov-1 and Markov-2, **hour-of-day-inhomogeneous** transition matrices (24 matrices, 0.5 Laplace prior, fall
>      back to the homogeneous matrix for cells with < 10 transitions) fit on the full training window; h-step via
>      product of the hourly matrices; (b) via absorbing-state chain.
>   6. **recency Markov** RM-N: Markov-1 (homogeneous) refit at 00:00 of each day on transitions within the last N days
>      with both endpoints <= t, N in {7, 14, 28}, selected per fold on inner-validation.
>   7. **semi-Markov (alternating renewal)**: empirical discrete hazards of ON and OFF spells by elapsed duration d
>      (0.5 Laplace prior; d > 48 pooled), fit on training-window completed spells plus censored spells; h-step forecast
>      by exact forward recursion over (state, d); (b) by the same recursion with absorption.
>   8. logistic regression (tuned, section 4).
>   9. KR only: **rota-naive** `p = y_{t+h-2*ceil(h/2)}` (most recent hour with the same clock parity as t+h).
> - "Simple models" in 6.2 = B. Static climatology is in B for selection but is not the go/no-go reference.

**[MUST] C3.2 - Model list.** *Replace* the heading "Models (24)" with "Models (27 forecasting + KM reference)", and
append an explicit enumerated list. Add: "FMs produce targets (a) and (b) only."

**[SHOULD] C3.3 - SVM calibration.** *Replace* "Platt scaling for SVM on inner-validation" with:
> Platt scaling for SVM fit on inner-validation predictions of the inner-train SVM (sklearn `CalibratedClassifierCV`
> with a prefit model, not the internal-CV `probability=True`), applied unchanged to the refit SVM.

### C.4 Section 4 - Tuning
**[MUST] C4.1 - Horizon group and budget unit.** *Replace* "60 trials per (model, target, horizon-group, re-tuning
point)" with:
> 60 completed-or-pruned trials per (model, target, horizon, re-tuning point) for direct models; multi-output deep models
> get one study per (target, re-tuning point) with 60 x (number of horizons of that target) trials, objective = mean
> inner-validation Brier over horizons `[JC]` (equal trials per model-horizon). Pruned trials count toward the budget.

**[MUST] C4.2 - Wall-clock cap.** *Replace* "Wall-clock cap per study to be set at freeze from a timing run on the PC
(logged if hit)" with:
> Wall-clock cap per study = <NUMBER from the day-2 timing run> h, frozen in `config/`. If the cap is hit, the study
> ends with the completed trials; the completed-trial count per study is reported, and any model with < 30 completed
> trials in any study is flagged *under-tuned* in every table. The cap does not apply to baselines.

(If the timing run cannot be done before the hash, freeze the rule "cap = 3 x (median trial time in the timing run) x
60" instead of the number.)

**[SHOULD] C4.3 - Tuning seeds.** *Replace* "tuning trials use seed 0" with "tuning trials of every stochastic model
(tree, boosting, deep) use model seed 0".

### C.5 Section 5 - Seeds
**[MUST] C5.1** *Replace* the bullets with:
> - Seeds: deep models 0-9; stochastic tree/boosting 0-29; deterministic models 1 run (seed 0). Deviation from PLAN.md
>   (30 seeds for all stochastic models) recorded for deep models: compute `[JC]`.
> - Adaptive rule (frozen): for each (deep model, target, horizon), if the SD over seeds of pooled test Brier
>   > 0.00125, add seeds 10-19 (20 seeds total) for that model at **all** horizons/targets. The rule is evaluated on
>   **inner-validation** pooled Brier, not test `[JC]` (avoids a test-dependent decision).
> - Inference unit unchanged.

### C.6 Section 6 - Metrics and inference
**[MUST] C6.1 - Skill reference.** *Replace* the "Primary" bullet with:
> - **Primary:** Brier score and two skill scores, both ratios of pooled sums (`1 - sum BS / sum BS_ref`):
>   `BSS_clim` against static climatology (reporting/literature comparison) and `BSS_strong` against the **strongest
>   baseline** = per fold, the member of B with lowest inner-validation Brier for that (target, horizon), applied to the
>   test month and pooled. `BSS_strong` is the go/no-go reference. Sensitivity (never used for a claim): ex-post best
>   single baseline on the pooled test set.

**[MUST] C6.2 - Q1.** *Replace* the Q1 text with:
> Q1, one test per horizon of target (a), W0, primary label (5 tests): composite C_ML (per fold, the ML/DL/FM model with
> lowest seed-mean inner-validation Brier) vs composite C_B (per fold, the member of B with lowest inner-validation
> Brier). One-sided DM test, H1: E[BS_C_ML - BS_C_B] < 0. Holm across the 5 tests, family-wise alpha = 0.05. Ties in
> inner-validation Brier (< 1e-6) are broken by the simpler model (list order in section 3).

**[MUST] C6.3 - Exploratory family.** *Replace* "All other pairs: Holm-adjusted p-values, labelled exploratory" with:
> All other pairs: two-sided DM p-values, Holm-adjusted within each (target, horizon, weather setting) over all model
> pairs; labelled exploratory.

**[SHOULD] C6.4 - HLN.** *Append* to the DM bullet: "HLN factor computed with the nominal horizon h; with n ~ 6,600 it
is negligible."

**[MUST] C6.5 - KR.** *Insert in* 6.5:
> Before any KR model is run, the data module reports for KR and BG: the share of outage hours and outage starts on odd
> clock hours; the hour-of-day histogram of starts and ends; the run-length histogram (mode at 1-2 h?); and, if any
> sub-hourly source exists, the same at native resolution. Pre-registered outcome: if the odd-hour share of starts is
> > 0.60 and is not explained by a documented rota or by the source data (Al-Shamri 2019 / raw logger files), all KR
> results, including G4, are labelled *exploratory (unexplained parity artefact)*. The rota-naive baseline is in B for
> KR in either case. Transfer uses W0.

### C.7 Section 7 - Go/no-go
**[MUST] C7.1 - G1.** *Replace* G1 with:
> **G1 complexity justified:** Q1 Holm-significant AND dBS (C_ML - C_B) <= -0.005 AND relative Brier reduction vs C_B
> >= 5 %, at >= 2 of 5 horizons, of which >= 1 in {1, 3, 6}; evaluated on the primary label and repeated on S-gen. Else
> NO-GO and the recommended forecaster is C_B. Rationale `[JC]`: against a strong baseline (pilot BG Brier ~0.17) the
> 5 % relative criterion binds. This supersedes the pilot criterion in PLAN.md ("BSS >= 10 % vs climatology").

**[MUST] C7.2 - G2-G4 selection.** *Replace* G2-G4 with:
> - **G2:** composite C_all (per-fold inner-validation-selected over all models) under W1 vs under W0, dBS <= -0.003 and
>   95 % block-bootstrap CI excluding 0 at >= 2 horizons.
> - **G3:** duration model selected per fold by inner-validation MAE; C-index >= 0.60 and MAE >= 10 % below the
>   training-KM conditional median, event-cluster bootstrap CI excluding 0.
> - **G4:** with KR-native `BSS_strong` > 0.02, BG->KR retains >= 50 % of it at h in {1, 6, 24}; if KR-native
>   `BSS_strong` <= 0.02, G4 is "not assessable". Exploratory if KR has > 5 % missing hours or the parity rule (6.5) fires.
> - **G5 dispatch value:** see section 9.

### C.8 Section 8 - Leakage tests
**[MUST] C8.1** *Replace* test 4 with:
> 4. `test_reference_causality`: (a) static climatology for fold k is unchanged when test-month labels are shuffled or
>    zeroed; (b) every per-origin baseline (seasonal-naive, trailing climatology, recency Markov, semi-Markov,
>    rota-naive) at origin t is unchanged when labels at times > t are overwritten (500 random origins, all horizons,
>    targets (a) and (b)).

**[MUST] C8.2** *Add* tests:
> 18. `test_label_hour_convention`: label rows are hour-beginning (checked against the workbook's documented timestamps
>     and against event start/end times in "Outage Events"); fails on a 1-h shift.
> 19. `test_label_definitions`: primary and S-gen labels reproduce the frozen disagreement counts in
>     `label_disagreement.csv`.
> 20. `test_innerval_predictions_exist`: for every (model, target, horizon, fold, seed) a test prediction file has a
>     matching inner-validation prediction file, and selection/threshold code reads only `predictions/innerval/`.
> 21. `test_dispatch_decision_alignment` (if section 9 is in v1.0): the decision for hour t+1 reads only forecasts with
>     origin <= t; overwriting all forecasts with origin >= t+1 leaves the decision unchanged.

**[SHOULD] C8.3** *Replace* test 13 with "permute the target column of training rows only (features computed from the
unpermuted series) -> pooled test `BSS_clim` <= 0.01".

**[SHOULD] C8.4** *Add* to section 7 layout: "Every cached artefact (features, predictions) is keyed by a SHA-256 of
(frozen YAML + feature code + data file); a cache with a non-matching key is never read." (Pilot SHOULD-6.)

### C.9 New section 9 - Dispatch evaluation (RQ3) [MUST: either this text, or the deferral sentence in D1]
Proposed text. Numeric choices are marked `[JC]` for the lead to confirm; ageing-model parameters must come from a
source verified by the Literature officer before the hash. I have not verified any battery-ageing source myself.
> **9.1 Simulator.** Verified pilot simulator with: explicit AC-coupled topology; inverter efficiency applied to battery
> discharge and charger efficiency to grid charging (values frozen in `config/`); clipped PV counted in curtailment;
> one SOC definition (`e / E_nameplate`) for rules and metrics; PV with `system_losses = 0.14` `[JC]` and one zenith
> definition. Period Apr-Dec (test months), initial SOC 0.5. Outage-hour load = generator energy (suppressed demand;
> limitation stated in every table; sensitivity with a load-scaling factor 1.25 on outage hours `[JC]`). Unserved energy
> is decomposed into energy-limited and power-limited parts.
> **9.2 Timing.** A decision applied during hour t+1 uses only forecasts with origin <= t (issued at (t+1):00).
> Look-ahead H = 6 h `[JC]`; forecast input = target (b) `z_{t,H}` probability of the inner-validation-selected model
> (and of every model, for the per-model table). Sensitivity H in {3, 12} on day 10.
> **9.3 Cost.** Per test month, `J(lambda) = E_unserved [kWh] + lambda * A`, where A = smooth ageing cost =
> calendar ageing integrated over SOC(t) (SOC-dependent stress function from the verified source) + cycle ageing
> proportional to throughput `[JC]`. lambda grid: 5 values spanning the range where the oracle's unserved energy moves
> from its minimum to the PV-only value `[JC]`, frozen from the training months Jan-Mar before any test run. The
> high-SOC-hours proxy is reported only for continuity with the pilot.
> **9.4 Policy families** (each with its own parameters):
> - N0 PV-only; N1 Mode 0 as in the thesis (0.25 C); N1r Mode 0 rate-matched (0.5 C);
> - N2 **SOC-target, no forecast**: grid-charge at rate c whenever SOC < S; S in {0.30, 0.35, ..., 1.00}, c in
>   {0.25, 0.5} C;
> - N3 **time-window SOC-target**: N2 restricted to a charging window [a, b) local time, a, b on a 3-h grid;
> - N4 **climatology-triggered**: forecast-policy F with p from the strongest baseline (C_B), i.e. no learned model;
> - F **forecast SOC-target**: target `S(t) = S_lo + (S_hi - S_lo) * 1[p_t > theta]` with S_lo, S_hi in the N2 grid and
>   theta in {0.05, 0.10, ..., 0.95};
> - O1 **oracle**: DP over discretised SOC (step 1 % of nameplate) with perfect knowledge of outages, PV and load over the
>   whole test month, minimising J(lambda);
> - O2 **policy-oracle**: family F fed the realised `z_{t,H}` (separates forecast value from policy-class limits).
> **9.5 Ex-ante parameter choice.** For each family and lambda, parameters are chosen to minimise J on the preceding
> month (using inner-validation forecasts for the first test month), then applied to the test month. The
> parameter-swept frontier (E_unserved vs A) is also plotted, but only ex-ante points enter claims. No interpolation
> between sampled operating points is reported as a result.
> **9.6 Metrics and inference.** Per lambda: J, E_unserved, LPSP, A, grid import; regret `J - J_O1`; share of the gap
> closed `(J_best-no-forecast - J_F) / (J_best-no-forecast - J_O1)`. The difference in J between F and the best of
> {N0, N1, N1r, N2, N3, N4} (ex-ante) is tested by a moving-block bootstrap over days (block 7 days, resampled within
> month, B = 5,000) `[JC]`.
> **9.7 G5 dispatch value:** F (with the C_ML forecast) beats the best ex-ante no-forecast family, including N4, with
> 95 % CI of dJ excluding 0 AND gap closed >= 20 % `[JC]`, at >= 2 of 5 lambda values. Else NO-GO, reported as
> "forecast skill without dispatch value beyond a SOC-target rule" (a primary finding).

---

## D. Literature mentioned

The DM (1995), Newey-West (1987), HLN (1997), Kuensch (1989), Holm (1979) and Demsar (2006) citations are those already
in v0.9. I did **not** re-verify them in this pass; the protocol points to `references_verified.md`, which I did not
open (not in my assigned files). Politis & White (2004) remains unverified, as v0.9 states. From memory (not verified),
it has a published correction (Patton, Politis & White, 2009) that the Literature officer should check. I cite no
battery-ageing model; C.9 leaves the source to the Literature officer.

## E. Message for the WP2 implementer (today, before the freeze)
1. Save inner-validation predictions for **every** fold, model and seed (C1.1). Retrofitting this later means rerunning
   everything.
2. Do not implement test 4 as written; implement C8.1.
3. Do not hard-code the label column, the hour convention, "horizon-group", or the climatology as a single static
   table. Make all of them config entries.
4. Baselines must be per-origin functions `f(history <= t, h)`, not per-fold fitted tables. Otherwise the trailing,
   recency and semi-Markov baselines will not fit the interface.
