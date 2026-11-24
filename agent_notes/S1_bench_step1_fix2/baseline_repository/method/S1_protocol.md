# S1 Evaluation Protocol - v1.0 (release candidate; hash on day 2)

**Study:** S1, benchmarking grid-outage forecasters for one Baghdad household (BG), with a transfer test to Karbala (KR),
and the value of the forecasts for home-battery dispatch (RQ3).
**Status:** v1.0-rc written 2026-10-22 18:50 Baghdad by the lead (Claude), from DRAFT v0.9 (git 8da067d) plus every MUST
item of `agent_notes/claude_reviewer2_protocol.md` (R2) and the "Exact settings to freeze" of
`agent_notes/claude_statistician_protocol.md` (ST). Where R2 and ST disagree, the choice and the reason are marked
`[LEAD]`. Day 2 (23 Oct): independent consistency check, then the SHA-256 of this file, of `config/S1_frozen.yaml` and
of the holiday calendar file goes to `results/S1/PROTOCOL.sha256` before any test-set prediction is made. Later changes
go to `results/S1/DEVIATIONS.md` (date, reason, affected results). Supersedes the pilot go/no-go in
`studies/S1_outage_forecasting/PLAN.md`.
**Notation:** `[JC]` = judgement call with a one-line rationale. References: `studies/S1_outage_forecasting/references_verified.md`,
`literature/S1_doi_followup.md`, `literature/S1_protocol_v1_refs.md`.

## 0. Data and targets
- **Series.** BG hourly, 2018-01-01 00:00 to 2018-12-31 23:00 Baghdad local time (UTC+3, no DST), 8,760 h.
  WP1 EDA (label S-gen): 4,324 outage hours, 1,064 events, outage share 0.494, mean event 4.06 h.
- **Label, primary:** `y_t = 1` if `grid_kwh_t == 0` (no metered grid energy in hour t) `[LEAD]` (closest observable
  to grid unavailability; does not depend on whether the household ran its generator).
- **Label, sensitivity (S-gen):** `y_t = 1` if `generator_kwh_t > 0` (the thesis/pilot label). Disagreement hours
  (pilot crosstab: BG 4 h grid==0 & gen==0; KR 14 h grid==0 & gen==0 and 1 h both > 0) are recomputed by script and
  listed with timestamps in `results/S1/label_disagreement.csv`. Q1 and G1 are re-run on S-gen; if the G1 decision
  differs, both are reported and G1 is labelled *label-sensitive*.
- Neither label is independently verified grid status ("National Status" is derived from grid energy, so agreement with
  it is not validation). Every table caption states that labels are inferred from metered consumption.
- **Hour convention.** Row "hour t" covers local clock interval [t:00, t+1:00) (hour-beginning) for labels, load and
  weather; verified for the label workbooks by test 18 before the hash. The **forecast origin t** is the instant
  (t+1):00. The label of hour t is known at the origin (zero latency) `[JC]` (the household observes its own supply).
  The instantaneous state at (t+1):00 is not a feature, so h = 1 skill is conservative.
- **Time base (weather).** `data/raw/nasa_power_baghdad_2018_hourly_local.csv` is ALREADY in Baghdad local time (shift
  done once at download, see its .meta.json). The loader must NOT shift again (test 8).
- **Target (a):** `y_{t+h}`, h in {1, 3, 6, 12, 24}.
- **Target (b):** `z_{t,h} = max(y_{t+1..t+h})`; identical to (a) at h = 1, reported for h in {3, 6, 12, 24}.
- **Target (c):** for origins with `y_t = 1`, remaining duration `R_t = min{k >= 1 : y_{t+k} = 0}` (integer hours >= 1);
  right-censored where the event runs past the last observable hour (1.3). Duration models, the KM reference and MAE all
  use this R_t scale. Targets (b) and (c) are scored only when every needed y in (t, t+h] (resp. the run) is observed.
- **Missing hours** are never imputed as labels and are excluded from scoring (origin or label time missing). Lag
  features touching a missing hour take the training-window outage share plus a missing indicator = 1. Baseline
  fallbacks: persistence / seasonal-naive / rota-naive with missing input -> static climatology; Markov / semi-Markov
  with missing current state -> static climatology; trailing climatology uses the available days in the window
  (denominator = available days), falling back to static climatology if fewer than 3. Counts in `results/S1/data_audit.csv`.

## 1. Splits
### 1.1 Main design: expanding-window rolling-origin CV, monthly folds
| Fold | Training window | Inner-train | Inner-validation | Test month |
|---|---|---|---|---|
| 1 | Jan-Mar | Jan-Feb | Mar | Apr |
| 2 | Jan-Apr | Jan-Mar | Apr | May |
| ... | ... | ... | ... | ... |
| 9 | Jan-Nov | Jan-Oct | Nov | Dec |

- 9 folds, about 6,600 test origins (Apr-Dec) per horizon. First training window = 3 months `[JC]` (smallest window
  leaving a 2-month inner-train set plus a validation month while test months still cover summer and both shoulders).
- **Purge = 24 h (max horizon).** A training origin t is kept only if `t + 24 <= T_train_end`; same rule between
  inner-train and inner-validation (inner-train origin kept only if `t + 24 <= T_innertrain_end`). **Inner-validation
  origins** are kept for horizon h only if `t + h <= T_train_end` (e.g. fold 1, origin 31 Mar 23:00 is dropped for every
  h; origin 31 Mar 00:00 is kept for h <= 23 and dropped for h = 24), so no inner-validation label lies in the test
  month. Test origins start at the first hour of the test month.
- Lags reaching into earlier months are allowed (available at the origin).
- Test origins whose label time t+h passes the test month are scored with the realised label; in December, origins with
  t+h > 2018-12-31 23:00 are dropped for that horizon (so T_m depends on h).

### 1.2 Tuning, inner-validation predictions and refit
Tune on inner-train, score on inner-validation (section 4) at re-tuning folds (1, 4, 7). **On every fold** (re-tuned or
not), every model is fit on that fold's inner-train with the current hyper-parameters, for every evaluation seed, and its
inner-validation predictions are saved to `predictions/innerval/`; untuned baselines and FMs also produce them. These
predictions are the only input to per-fold model selection (6.2), thresholds (6.1), Platt scaling and the seed rule (5).
Ex-ante dispatch parameters for month m (9.5) may read inner-validation predictions and test-fold predictions whose
origin lies before the first hour of month m, and nothing else. The model is then refit on the full training window; iterative models use the
early-stopped round/epoch count `[JC]`. Thresholds and Platt parameters estimated on the inner-train model are applied
unchanged to the refit model `[JC]` (no third split). Early stopping and the tuning objective share the inner-validation
month `[JC]` (slightly optimistic selection; test months untouched).

### 1.3 Duration target and censoring
Training outages still running at `T_train_end` are right-censored there. Test durations may run past the test month
(realised value used). Durations running at 2018-12-31 23:00 are censored.

### 1.4 Random-split leakage quantification (descriptive ONLY)
Models logistic, Markov-2, LightGBM, MLP, LSTM; target (a); W0; seeds 0-4 for the random draws. For each model and
horizon report: (i) rolling-origin (main); (ii) blocked month-CV with future months allowed and a 7-day embargo;
(iii) random 80/20 within each month, scored on all rows; (iv) the same random split scored on Apr-Dec rows only.
Report `dBS_leak = BS_(iv) - BS_(i)` and its decomposition (ii)-(i) (future regime + training size) and (iv)-(ii)
(temporal adjacency), range over 5 draws. Written only to `results/S1/leakage_randomsplit/`; never used for selection,
ranking or go/no-go (test 16). No inference.

## 2. Information available at the forecast origin
- **Lags:** `y_{t-k}`, k = 0..48 and 168; current run length; time since last outage start/end; outage counts over the
  past 6/24/168 h; state changes over the past 24 h; outage share over the past 720 h (regime level).
- **Calendar:** hour of day (sin/cos), day of week, Friday flag, Iraqi public-holiday and Ramadan flags from
  `data/calendar/iraq_2018.csv`, committed and hashed before the freeze. Dates follow
  `literature/S1_protocol_v1_refs.md`; where the two sources disagree, or a date is unverified (Ramadan start,
  12-13 May election days, Arbaeen), the day gets a separate `holiday_uncertain` flag instead of `holiday` `[JC]`;
  all such dates are listed in the file header.
- **Month and day-of-year excluded** `[JC]` (with one year the test month is always an unseen level).
- **Household load is not a feature** in v1.0 `[JC]` (in outage hours it equals generator energy, capped by the
  subscription); a load ablation is a declared exploratory analysis.
- **Weather settings:** W0 none (MAIN); W1 realised weather at hours <= t (lags 0,1,3,6,12,24 + 24-h means), labelled
  optimistic `[JC]` (reanalysis is published with a delay); W2 = W1 + realised weather at t+1..t+h (oracle upper bound,
  never in a headline claim). KR uses W0 only unless the KR NASA POWER series (32.6136 N, 44.0430 E) is committed before
  the hash; Baghdad weather is never a KR covariate.
- Scalers/encoders are fit only on the rows the model is trained on.

## 3. Models (27 forecasting models + KM reference) and probabilities
All baselines are per-origin functions `f(history <= t, h)`, not per-fold fitted tables, unless stated.
- **Baseline set B** (targets (a) and (b)):
  1. persistence `p = y_t`; (b) `y_t`.
  2. seasonal-naive `p = y_{t+h-24}`; (b) `max(y_{t+1-24 .. t+h-24})` (h <= 24, all inputs <= t).
  3. static climatology `p_clim(hour) = (n_out(hour) + 0.5) / (n(hour) + 1)` over all training origins (fit once per
     fold); (b) `(n_z(hour) + 0.5) / (n(hour) + 1)` with `z_{.,h}` by origin hour. It is a candidate for C_B
     like every member of B; it is not the go/no-go reference (it defines `BSS_clim` only, 6.1).
  4. trailing climatology TC-W, W in {7, 14, 28} days, at every origin:
     `p = (sum_{k=k0}^{k0+W-1} y_{t+h-24k} + 0.5) / (W + 1)`, `k0 = ceil(h/24)` (all label times <= t); (b) same with
     `z_{t-24k, h}`, k = k0 .. k0+W-1 (every window (t-24k, t-24k+h] ends <= t). W selected per fold on inner-validation Brier; all three reported.
  5. Markov-1 and Markov-2, hour-of-day-inhomogeneous (24 transition matrices, 0.5 Laplace prior; cells with < 10
     transitions fall back to the homogeneous matrix), fit on the full training window; h-step by product of the hourly
     matrices; (b) via an absorbing-state chain.
  6. recency Markov RM-N: homogeneous Markov-1 refit at 00:00 of each day on transitions within the last N days with
     both endpoints <= t, N in {7, 14, 28}, selected per fold on inner-validation.
  7. semi-Markov (alternating renewal): empirical discrete hazards of ON and OFF spells by elapsed duration d
     (0.5 Laplace prior; d > 48 pooled), fit on training-window completed and censored spells; h-step forecast by exact
     forward recursion over (state, d); (b) by the same recursion with absorption.
  8. logistic regression (tuned, section 4).
  9. KR only: rota-naive `p = y_{t+h-2*ceil(h/2)}` (most recent hour <= t with the clock parity of t+h);
     (b) `max(y_{t-1}, y_t)` for h >= 2 (both parities seen within the window).
  "Simple models" in 6.2 = B.
- **Duration (target (c)):** Weibull AFT and penalised Cox PH (run-length + calendar features), point forecast = median
  survival; reference = Kaplan-Meier conditional median remaining time given elapsed duration (training window).
- **ML:** kNN, SVM-RBF, RF, ExtraTrees, XGBoost, LightGBM, CatBoost; direct strategy (one model per target/horizon).
- **Deep:** MLP, LSTM, GRU, TCN, small Transformer; one multi-output head per target `[JC]` (compute).
- **Zero-shot FMs:** Chronos-2, Chronos-Bolt, TimesFM 2.5, TTM r2; 512-h context ending at t; covariates only in W1/W2
  where supported; deterministic point forecast (mean/median); if sampling is unavoidable, seed 0 and >= 20 samples;
  `p = clip(point forecast, 0, 1)`; target (b) via `1 - prod_k(1 - p_{t+k})` `[JC]` (independence assumption, bias
  reported). FMs produce targets (a) and (b) only.
- **Enumerated list (27):** persistence, seasonal-naive, static climatology, TC (W selected), Markov-1, Markov-2,
  RM (N selected), semi-Markov, logistic, rota-naive (KR only), Weibull AFT, Cox PH, kNN, SVM, RF, ExtraTrees, XGBoost,
  LightGBM, CatBoost, MLP, LSTM, GRU, TCN, Transformer, Chronos-2, Chronos-Bolt, TimesFM 2.5, TTM r2 (BG: 27, rota-naive
  excluded; KR: 28). KM is a reference, not a model.
- **Calibration:** no post-hoc recalibration except Platt scaling for SVM, fit on inner-validation predictions of the
  inner-train SVM (prefit `CalibratedClassifierCV`, not internal-CV `probability=True`), applied unchanged to the refit
  SVM. Log-loss only: clip to [1e-3, 1 - 1e-3]; persistence/seasonal-naive/rota-naive log-loss flagged clip-dominated.

## 4. Tuning (equal budget)
- Optuna (Akiba et al. 2019) TPE, `multivariate=True`, `n_startup_trials=10`, sampler seed 20180101; one study per
  (model, target, horizon, re-tuning point) for direct models with **60 trials**; multi-output deep models get one study
  per (target, re-tuning point) with 60 x (number of horizons of that target) trials, objective = mean inner-validation
  Brier over horizons `[JC]` (equal trials per model-horizon). Pruned trials count. MedianPruner(n_startup_trials=5,
  n_warmup_steps = 10 epochs or 100 boosting rounds). Study name <-> seed mapping logged.
- Tuning trials of every stochastic model use model seed 0 (excluded from evaluation seeds, section 5).
- **Re-tuning at folds 1, 4, 7;** hyper-parameters reused for the next two folds `[JC]` (~3x less compute, still follows
  seasonal drift). Untuned (reported as "0 trials"): persistence, seasonal-naive, climatologies, Markov variants,
  semi-Markov, rota-naive, FMs. TC-W and RM-N choose W/N on inner-validation (3 candidates, not a study).
- **Wall-clock cap (rule frozen; number recorded at the timing run):** cap per study = 3 x (median trial time of that
  family in a timing run on fold 1 with seed 0) x number of trials of the study. The timing run uses fold 1 only and
  touches no test month; values go to `config/S1_timing_caps.yaml`, whose SHA-256 is added as an addendum line to
`results/S1/PROTOCOL.sha256` before any test prediction (the hashed `S1_frozen.yaml` is never edited). If a cap is hit the study
  ends with completed trials, the count is reported, the hit is logged in DEVIATIONS.md, and a model with < 30 completed
  trials in any study is flagged *under-tuned* in every table.
- **Convergence flag:** best-so-far inner-validation Brier improved by > 0.0005 over the last 20 trials -> "possibly
  under-tuned" (reported; budget never extended post hoc).

| Family | Search space (log = log-uniform) |
|---|---|
| Logistic | C log[1e-4, 1e2]; penalty {l1, l2}; no class weights |
| Weibull / Cox | L2 penalizer log[1e-4, 1] |
| kNN | k log-int[5, 200]; weights {uniform, distance}; p {1, 2} |
| SVM | C log[1e-2, 1e2]; gamma log[1e-4, 1] |
| RF / ExtraTrees | 500 trees; max_depth {None, 4-30}; min_samples_leaf log-int[1, 50]; max_features [0.1, 1.0] |
| XGBoost / LightGBM / CatBoost | lr log[0.01, 0.3]; depth [3, 10] (LightGBM num_leaves [8, 256]); min_child log-int[1, 100]; subsample [0.5, 1]; colsample [0.5, 1]; L2 log[1e-3, 10]; <= 2,000 rounds, early stop 100 |
| MLP | 1-3 layers; width {32, 64, 128, 256}; dropout [0, 0.5]; lr log[1e-4, 1e-2]; weight decay log[1e-6, 1e-2] |
| LSTM / GRU | lookback {48, 96, 168, 336}; hidden {16, 32, 64, 128}; 1-2 layers; dropout [0, 0.5]; lr as MLP |
| TCN | channels {16, 32, 64}; kernel {2, 3, 5}; levels so receptive field covers lookback; dropout [0, 0.5] |
| Transformer | d_model {16, 32, 64}; heads {2, 4}; layers 1-3; lookback as LSTM; dropout [0, 0.3] |

Deep training: Adam, batch 128, <= 200 epochs, early stopping on inner-validation Brier (patience 15, best weights
restored, best epoch kept for refit).

## 5. Seeds and determinism
- **Evaluation seeds** 1..n for every stochastic family (tree, boosting, deep); seed 0 is the tuning seed and is not
  evaluated. Deterministic models (logistic, baselines, kNN, SVM, Weibull/Cox, FMs): 1 run.
- **n per model** `[LEAD]` (ST precision rule, applied to all stochastic families alike): start with seeds 1-10;
  `n = max(10, ceil((SD10 / 0.0005)^2))`, cap 30 for tree/boosting and 20 for deep `[JC]` (compute on one PC), where
  SD10 = seed SD of pooled **inner-validation** Brier over seeds 1-10, taken as the maximum over that model's
  (target, horizon) cells `[LEAD]` (R2: decision must not depend on test data). Extra seeds are 11..n. Cap hits are
  reported with the achieved SE. Deviation from PLAN.md ("30 seeds for stochastic models") recorded.
- **Inference unit:** per-origin Brier averaged over seeds (expected loss of a single run, not an ensemble). Per model x
  target x horizon report seed mean, SD and min-max of pooled Brier; for each Q1 comparison the share of seeds with
  single-run dBS < 0 and the DM range over seeds. Selection in 6.2 uses seed-mean inner-validation Brier.
- **Determinism (test 17):** python/NumPy/torch seeds; `torch.use_deterministic_algorithms(True)`, cuDNN deterministic;
  LightGBM `deterministic=True, force_row_wise=True`; XGBoost `seed` with fixed `nthread`; CatBoost `random_seed` with
  fixed `thread_count`; fixed thread counts everywhere; library versions in the environment lock.

## 6. Metrics and statistical inference
### 6.1 Metrics
- **Primary:** Brier score and two skill scores, both ratios of pooled sums `1 - sum BS / sum BS_ref` over pooled test
  origins (never a mean of per-fold ratios): `BSS_clim` vs static climatology (literature/pilot comparison) and
  `BSS_strong` vs the **strongest baseline** C_B = per fold, the member of B with the lowest inner-validation Brier for
  that (target, horizon), applied to the test month and pooled. `BSS_strong` is the headline skill and the go/no-go
  reference. Sensitivity, never used for a claim: ex-post best single baseline on the pooled test set.
- **Secondary:** log-loss, ROC-AUC, PR-AUC (outage = positive), ECE (10 equal-width bins; equal-mass bins as
  sensitivity), reliability curves with bin counts and month-stratified block-bootstrap bands; MCC and F1 at the
  MCC-maximising threshold on inner-validation (secondary only; not proper scores).
- **Duration:** MAE (h) on uncensored test origins; Harrell's C-index; both also at event-start origins only.

### 6.2 Confirmatory family (the only significance statements)
Q1, BG, target (a), W0, primary label, one test per h in {1, 3, 6, 12, 24} (5 tests): composite C_ML (per fold, the
ML/deep/FM model with the lowest seed-mean inner-validation Brier) vs composite C_B (per fold, the member of B with the
lowest inner-validation Brier). Ties (< 1e-6) go to the simpler model (list order in section 3). Selection never uses
test months. **Two-sided** DM p-values with the sign reported `[LEAD]` (ST: conservative; G1 adds the direction and
magnitude). Holm (1979) across the 5 tests, family-wise alpha = 0.05. Optional sensitivity: Westfall-Young single-step
max-|t| from the same paired bootstrap; Holm stays primary.

### 6.3 Pairwise inference respecting serial dependence
- Loss differential `d_t = BS_A,t - BS_B,t` (seed-mean per-origin Brier) over pooled test origins.
- **DM** (Diebold & Mariano 1995): Newey-West (1987) Bartlett HAC variance, global demeaning, lag `L_HAC = L_block`
  (6.3 bootstrap), never below h-1. Reference distribution `t_{T-1}` with the HLN (1997) factor computed with the nominal
  h (declared numerically negligible at T ~ 6,600) `[LEAD]`. Sensitivities: fixed-b Bartlett critical value
  (Kiefer & Vogelsang 2005; polynomial `1.9600 + 2.9694b + 0.4160b^2 - 0.5324b^3` with b = L/T, taken from a secondary
  source - see `literature/S1_protocol_v1_refs.md`; primary-source check pending, hence sensitivity only); HAC lags 24
  and 168; month-stratified LRV (d_t demeaned within month, month LRVs summed).
- **Bootstrap:** circular moving-block (Kuensch 1989), within each test month (T_m per horizon), paired (same indices
  for all models in a comparison and for the BSS reference; numerator and denominator resampled jointly), B = 9,999,
  seed 20180102. Block length (and HAC lag) per comparison - confirmatory, G2, G4 (on KR loss differentials) and every
  exploratory CI alike:
  `L_block = clip(ceil24(max(PW(d pooled), median_m PW(d_m))), 48, 168)` h, PW = Politis & White (2004) automatic
  circular block length with the Patton, Politis & White (2009) correction (`arch.bootstrap.optimal_block_length`,
  circular column); values logged in `inference/block_lengths.csv`; L_block governs precision only. Sensitivity: fixed
  L = 24 h and 168 h. Percentile CIs for dBS and relative reduction; BCa for BSS and ratios. ACF of d_t to lag 336 per
  Q1 comparison in the supplement.
- **Fragile:** DM p-value and bootstrap CI disagree at 0.05, or the decision changes between L = 24 and L = 168.
- **Duration:** event-cluster bootstrap (whole events), stratified by test month, B = 9,999.
- **Effect sizes** with 95 % CIs: dBS, dBSS (pp), relative Brier reduction `1 - BS_A/BS_B`, dAUC, dMAE.
- **Exploratory comparisons** (everything outside 6.2 and the named secondary families in 7): effect sizes + 95 %
  block-bootstrap CIs, **no p-values** `[LEAD]` (ST: Holm over ~10^4 pairs is meaningless).

### 6.4 Descriptive ranking
Mean ranks per horizon over N = 9 folds (Brier, target (a), W0), never pooled to 45 blocks; per-fold rank tables;
Nemenyi CD diagrams (Demsar 2006) over the models that produce target (a) (BG: k = 25, Weibull/Cox excluded; CD at
N = 9 computed with q from `scipy.stats.studentized_range`, about 12.7 rank units per Reviewer-2 v1rc arithmetic) and the
printed caveat that folds are dependent and the ranking is descriptive only; no Friedman p-values in the text.

### 6.5 Karbala
- **Parity diagnostic first** (before any KR model is run): for KR and BG, the share of outage hours and outage starts
  on odd clock hours, hour-of-day histograms of starts and ends, the run-length histogram, and native-resolution
  checks if any sub-hourly source exists. Pre-registered consequence: if the odd-hour share of starts is > 0.60 and is
  not explained by a documented rota or by the source data, all KR results including G4 are labelled *exploratory
  (unexplained parity artefact)*. Rota-naive is in B for KR in either case.
- **Transfer (time-respecting):** for KR test month m, the BG model trained on BG months before m, no retraining, KR's
  own lags and calendar, W0 `[JC]` (contemporaneous BG hours would leak shared national-grid shocks). Same protocol run
  natively on KR with KR's own C_B. Report `dBS_transfer = BS_BG->KR - BS_KR-native` (paired block bootstrap, L_block
  from the KR d_t) and the share of native `BSS_strong` retained (BCa CI).

## 7. Go/no-go (pre-registered)
- **G1 complexity justified:** Q1 Holm-significant AND dBS(C_ML - C_B) <= -0.005 with 95 % CI upper bound < 0 AND
  relative Brier reduction vs C_B >= 5 %, at >= 2 of 5 horizons, of which >= 1 in {1, 3, 6}; primary label, repeated
  on S-gen. Else NO-GO and the recommended forecaster is C_B. Rationale `[JC]`: against a strong baseline (pilot BG
  trailing-14d Brier ~0.17) the 5 % relative criterion binds.
- **G2 weather value** (named secondary family, Holm over 5 horizons): composite C_all (per-fold inner-validation
  selected over all models) under W1 vs under W0, Holm-significant AND dBS <= -0.003 AND 95 % CI excluding 0 at >= 2
  horizons. W2 is an
  upper bound only.
- **G3 duration:** duration model selected per fold by inner-validation MAE; C-index >= 0.60 and MAE >= 10 % below the
  training-KM conditional median, event-cluster CI excluding 0.
- **G4 transfer:** evaluated separately at each h in {1, 6, 24}: transferred model = BG-selected C_ML (per fold),
  compared with KR-native C_ML; retained share = `BSS_strong(BG->KR) / BSS_strong(KR-native)` (both vs KR's C_B).
  At an h with KR-native `BSS_strong` <= 0.02: "not assessable". Otherwise PASS if the BCa 95 % CI lower bound of the
  retained share is >= 0.50, FAIL if the upper bound is < 0.50, else inconclusive. G4 passes if it PASSes at all
  assessable horizons and at least two are assessable. Exploratory if KR has > 5 %
  missing hours or the parity rule (6.5) fires.
- **G5 dispatch value:** section 9.
- **Leakage gate:** any failing test in section 8 blocks every result.
- Reporting: all models at every horizon/target/weather setting, including failures and cap hits; nothing dropped after
  results are seen; a NO-GO is a primary finding; "significant" only within 6.2 and the named secondary family G2.
- **Layout** under `results/S1/`: `config/` (frozen YAML, git commit, environment lock), `predictions/` and
  `predictions/innerval/` (parquet per model x target x horizon x fold x seed), `metrics/`, `inference/`, `figures/`,
  `leakage_randomsplit/`, `dispatch/`, `tests/leakage_report.json`, `DEVIATIONS.md`. Manuscript tables and figures are
  generated by scripts from `metrics/`, `inference/` and `dispatch/` only. Every cached artefact is keyed by SHA-256 of
  (frozen YAML + feature code + data file); a cache with a non-matching key is never read.

## 8. Leakage and correctness tests the harness must pass (pytest)
1. `test_purge_train_labels`: every training (origin, label-time) has `label_time <= T_train_end` (all folds, horizons,
   targets; also inner-train vs inner-validation), and every inner-validation (origin, label-time) has
   `label_time <= T_train_end`.
2. `test_test_origins_after_train`: `min(test origin) > T_train_end`; inner-validation month inside the training window.
3. `test_feature_causality`: for 500 random origins, overwriting all y and weather at times > t leaves W0/W1 features at
   t unchanged; in W2 only declared oracle columns change.
4. `test_reference_causality`: (a) static climatology for fold k is unchanged when test-month labels are shuffled or
   zeroed; (b) every per-origin baseline (seasonal-naive, trailing climatology, recency Markov, semi-Markov, rota-naive)
   at origin t is unchanged when labels at times > t are overwritten (500 random origins, all horizons, targets (a), (b)).
5. `test_scaler_encoder_fit_scope`: scaler/encoder parameters unchanged when test rows are altered.
6. `test_test_index_guard`: test indices wrapped in a guard that raises on access during tuning/selection/thresholds.
7. `test_threshold_from_inner_val`: stored threshold reproduces from inner-validation predictions alone.
8. `test_local_time_no_double_shift`: on the loaded weather, mean GHI is 0 at local hours 0-3 and peaks at local hours
   11-13.
9. `test_target_construction`: on a synthetic series, (a) = `shift(-h)`, (b) = forward rolling max over (t, t+h],
   (c) `R_t = min{k >= 1 : y_{t+k} = 0}` and the censoring flag.
10. `test_duration_censor_at_train_end`.
11. `test_fm_context_sentinel`: sentinels at t+1.. never reach FM inputs; context ends exactly at t.
12. `test_seasonal_naive_index`: reads only `y_{t+h-24}` (and the (b) window), h <= 24.
13. `test_label_permutation_canary`: permute the target column of training rows only (features computed from the
    unpermuted series) -> pooled test `BSS_clim` <= 0.01 (logistic, LightGBM, MLP).
14. `test_iid_null_series`: on i.i.d. Bernoulli(0.5), no model reaches pooled `BSS_clim` > 0.01.
15. `test_transfer_time_order`: every BG training timestamp is earlier than the KR test-month start.
16. `test_randomsplit_quarantine`: no file under `metrics/` or `inference/` contains a random-split run ID.
17. `test_determinism`: same seed + config -> bit-identical predictions for one model per family.
18. `test_label_hour_convention`: label rows are hour-beginning (checked against the workbook's documented timestamps
    and the start/end times in "Outage Events"); fails on a 1-h shift.
19. `test_label_definitions`: primary and S-gen labels reproduce the counts in `label_disagreement.csv`.
20. `test_innerval_predictions_exist`: every test prediction file has a matching inner-validation file; selection,
    threshold and seed-rule code reads only `predictions/innerval/`; dispatch-parameter code for month m reads only
    predictions with origin before month m (overwriting later predictions leaves its choice unchanged).
21. `test_dispatch_decision_alignment`: the decision for hour t+1 reads only forecasts with origin <= t; overwriting all
    forecasts with origin >= t+1 leaves it unchanged.
22. `test_cache_key`: a cached artefact whose key does not match (YAML + code + data) hash is never read.

## 9. Dispatch evaluation (RQ3)
Run in WP7 (day 9) on the simulator v2 after its independent N-version check (`20261022-s1-dispatch-v2-verify`) and
with the hashed v3 forecast outputs of WP2-WP5; never with the v1 simulator or the v1 forecast cache.
### 9.1 Simulator
AC-coupled topology stated explicitly; inverter efficiency on battery discharge and charger efficiency on grid charging
(values in `config/`); clipped PV counted as curtailment; one SOC definition `SOC = e / E_nameplate` for rules and
metrics; PV from `src/pv/model.py` (south azimuth, local time, `system_losses = 0.14` `[JC]`). System = the thesis
design (15 kWp / 30.6 kWh) and, as sensitivity, the size re-optimised with the corrected PV model when the product track
delivers it (labelled). Period: continuous Apr-Dec trajectory, initial SOC 0.5 on 1 Apr, battery state carried across
months. Outage-hour load = generator energy (suppressed demand, limitation stated in every table); sensitivity with a
load factor of 1.25 on outage hours `[JC]`. Unserved energy is decomposed into energy-limited and power-limited parts.
### 9.2 Timing and forecast input
Site BG, weather W0, primary label (S-gen as sensitivity). A decision applied during hour t+1 uses only forecasts with
origin <= t. Look-ahead H = 6 h `[JC]`; input = target (b) `z_{t,H}` probability. For dispatch, C_ML and C_B are
selected per fold on inner-validation Brier of **target (b) at h = H** (not target (a)) `[LEAD]`. Primary forecast =
C_ML, seed-mean probability averaged over evaluation seeds `[JC]` (the operational choice); hours with no forecast
available (1 Apr 00:00, missing origins) use the static-climatology probability; per-model tables use every model; the forecast seed spread is shown by re-running
F over seeds (min/median/max of each delta). Sensitivity H in {3, 12} (day 10).
### 9.3 Objective
Per policy and month `J_lambda = LPSP_pp + lambda * A`, where A is battery degradation over the period in % of nameplate
capacity:
- **calendar part:** the Naumann et al. (2018) LFP calendar model (sqrt-time, Arrhenius temperature term, cubic SOC
  term), integrated over the hourly SOC path at a fixed cell temperature of 30 degC `[JC]`, with equations and
  parameters copied into `method/S1_ageing_model.md` from the published paper (or, if the paper stays inaccessible, from
  Naumann's 2018 TUM dissertation, stated as such) and checked against the source by a second agent;
- **cycle part:** proportional to energy throughput, coefficient from the same source family (Naumann et al. 2020) or,
  if not verifiable, a stated assumption with a +/-50 % sensitivity.
`method/S1_ageing_model.md` and the lambda grid are hashed into `results/S1/PROTOCOL.sha256` (addendum line) before any
dispatch run on test months and no later than day 8; until then no RQ3 claim exists. lambda grid: 5 log-spaced values
spanning the slopes of the no-forecast front computed on Jan-Mar (training months only) `[JC]`. Secondary stress planes,
for continuity with the pilot: hours with SOC >= 80 % (per 100 h) and mean SOC (pp). Constraint variant: minimise A
subject to LPSP <= (Mode-0 LPSP on the selection window) + 0.10 pp.
### 9.4 Policy families
- N0 PV-only; N1 Mode 0 as in the thesis (0.25 C); N1r Mode 0 rate-matched (0.5 C);
- N2 SOC-target, no forecast: grid-charge at rate c whenever SOC < S; S in {0.30, 0.35, ..., 1.00}, c in {0.25, 0.5} C;
- N3 time-window SOC-target: N2 restricted to a charging window [a, b) local time, a and b on a 3-h grid;
- N4 baseline-triggered: family F fed the C_B (strongest baseline) probability, i.e. no learned model;
- F forecast SOC-target: SOC target for hour t+1 `S_{t+1} = S_lo + (S_hi - S_lo) * 1[p_t > theta]`, p_t issued at
  origin t; S_lo and S_hi on the N2 grid,
  theta in {0.05, 0.10, ..., 0.95};
- O1 oracle: DP over SOC discretised at 1 % of nameplate with perfect knowledge of outages, PV and load over each month,
  minimising J_lambda; because sqrt-time calendar ageing is path-dependent, the DP uses the calendar-ageing rate
  linearised at the month's starting virtual time `[JC]`, and the realised O1 path is then re-scored with the exact
  model (O1 is labelled "near-oracle" if the re-scored J differs from the DP value by > 1 %);
- O2 policy-oracle: family F fed the realised `z_{t,H}` (separates forecast value from policy-class limits).
### 9.5 Ex-ante parameter choice (time-respecting)
For each family and lambda, parameters minimise J_lambda on the preceding months Apr..m-1 (expanding, out-of-sample
forecasts from the rolling folds) and are applied to month m. Each selection re-simulation starts on 1 Apr 00:00 at
SOC 0.5 and zero ageing. **April is used for selection only; scoring = May-Dec;** headline J, LPSP and A are pooled
over May-Dec. Policy changes ("best NF" and the primary pair F(C_ML) vs best NF replace ST's RiskTarget(RF) vs SOC-target
a2; the objective uses ageing A instead of the SOC>=80 % stress proxy, per PLAN_2W day 9) are `[LEAD]` decisions.
The family winner among no-forecast families {N0, N1, N1r, N2, N3, N4} ("best NF") is also selected on preceding months.
Sensitivity: rolling 2-month selection window; leave-one-month-out cross-fit labelled *not time-respecting*. Full
swept frontiers are shown as descriptive context, captioned "in-sample envelope, optimistic"; any in-sample minimum
shown carries a Hansen (2005) SPA p-value over all swept points at that lambda vs the in-sample best NF point, or the
label "selected in sample over N points, untested". No interpolation between sampled points is reported as a result.
### 9.6 Metrics and inference
Per lambda: J, LPSP, unserved kWh, A, grid import, the stress planes; regret `J - J_O1`; gap closed
`(J_bestNF - J_F) / (J_bestNF - J_O1)`. Primary pair: F(C_ML) vs best NF, both ex ante. Inference: paired,
month-stratified circular block bootstrap of per-day contributions (unserved kWh, load kWh, A increments, stress
counts) from the realised trajectories, block 7 days (sensitivity 3 and 14), B = 9,999, seed 20180103; ratio statistics
recomputed from resampled sums; percentile 95 % CIs and the share of replicates < 0. Secondary: month-stratified
sign-flip randomisation test on weekly paired unserved-kWh differences. Episode sensitivity: leave-one-episode-out
jackknife, dLPSP without the top 1/3/5 episodes (episode = outage event + preceding 24 h), and an episode-resampling
bootstrap within month (secondary).
### 9.7 G5 dispatch value
- **Value:** F(C_ML) beats best NF with the 95 % CI of dJ excluding 0 AND gap closed >= 20 % `[JC]`, at >= 2 of 5
  lambda values.
- **Equivalence (TOST, Schuirmann 1987, 90 % CI):** "no practically relevant forecast value" is claimed only if the CI
  of dLPSP lies inside +/-0.10 pp AND the CI of dA lies inside +/-5 % of best-NF A `[JC]`, at every lambda.
- Otherwise "inconclusive", never "no effect". Either outcome is a primary finding.

## 10. Open items before the hash (day 2)
- [done 22 Oct 19:20] Independent consistency check (`agent_notes/claude_reviewer2_protocol_v1rc.md`,
  HASH_AFTER_MINOR_EDITS): MUST edits M1-M9 applied (inner-validation purge, dispatch read scope, timing-cap addendum,
  dispatch spec, G4 rule, Nemenyi k, static-climatology role, rota-naive (b), block-length scope) plus SHOULD items
  (G2 Holm, R_t scale, (b)/(c) scoring, uncertain-holiday flag, episode bootstrap, near-oracle O1). Remaining SHOULD
  items are reviewed by the lead on day 2 before the hash.
- `data/calendar/iraq_2018.csv` built from `literature/S1_protocol_v1_refs.md` (disputed dates flagged).
- `config/S1_frozen.yaml` mirroring every number above (WP2 harness reads it).
- Timing run (fold 1, seed 0) for the wall-clock caps: after the WP2 harness exists; values written to
  `config/S1_timing_caps.yaml` and hashed as an addendum line before any test prediction (the cap *rule* is frozen now).
- Test 18 (hour convention) must pass on the BG and KR workbooks.
- Not blocking the hash (blocks only RQ3): `method/S1_ageing_model.md` (day 8 latest); primary-source check of the
  Kiefer & Vogelsang polynomial (sensitivity only).
