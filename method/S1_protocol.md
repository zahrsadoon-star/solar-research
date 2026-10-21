# S1 Evaluation Protocol - DRAFT v0.9 (to be frozen on day 2)

**Study:** S1, benchmarking grid-outage forecasters for one Baghdad household (BG), with a transfer test to Karbala (KR)
**Status:** DRAFT written 2026-10-22 by the Claude Statistician agent, edited by the lead. Day 2 (23 Oct): Reviewer-2
pass, then freeze as v1.0. At freeze the SHA-256 of this file goes to `results/S1/PROTOCOL.sha256` before any
test-set prediction is made; later changes go to `results/S1/DEVIATIONS.md` (date, reason, affected results).
**Notation:** `[JC]` = judgement call, followed by a one-line rationale. Verified references:
`studies/S1_outage_forecasting/references_verified.md`.

## 0. Data and targets
- **Series.** BG hourly, 2018-01-01 00:00 to 2018-12-31 23:00 Baghdad local time (UTC+3, no DST): 8,760 h,
  4,324 outage hours, 1,064 events, outage share 0.494, mean event 4.06 h (results/S1/eda, WP1).
- **Label (proxy).** `y_t = 1` if generator energy in hour t > 0. It misses outages during which the household did not
  run the generator, so it can under-count outages. Reported as a limitation; not corrected.
- **Time base.** `data/raw/nasa_power_baghdad_2018_hourly_local.csv` is ALREADY in Baghdad local time (the UTC->local
  shift was done once at download; see its .meta.json). The loader must NOT shift again. Unit test in section 8.
- **Target (a):** `y_{t+h}`, h in {1, 3, 6, 12, 24}.
- **Target (b):** `z_{t,h} = max(y_{t+1..t+h})`; identical to (a) at h = 1, so reported for h in {3, 6, 12, 24}.
- **Target (c):** for origins with `y_t = 1`, remaining duration `R_t` = hours from t to the first hour with y = 0;
  right-censored where the event runs past the last observable hour (1.3).
- **Missing hours** are never imputed as labels; excluded from scoring; lag features touching them get a missing
  indicator; counts in `results/S1/data_audit.csv`.

## 1. Splits
### 1.1 Main design: expanding-window rolling-origin CV, monthly folds
| Fold | Training window | Inner-train | Inner-validation | Test month |
|---|---|---|---|---|
| 1 | Jan-Mar | Jan-Feb | Mar | Apr |
| 2 | Jan-Apr | Jan-Mar | Apr | May |
| ... | ... | ... | ... | ... |
| 9 | Jan-Nov | Jan-Oct | Nov | Dec |

- 9 folds, about 6,600 test origins (Apr-Dec) per horizon.
- **First training window = 3 months** `[JC]`: smallest window leaving a 2-month inner-train set plus a full validation
  month while the test months still cover the summer peak and both shoulder seasons.
- **Purge/embargo = 24 h (max horizon).** A training origin t is kept only if `t + 24 <= T_train_end`; same rule between
  inner-train and inner-validation. Test origins start at the first hour of the test month.
- Lags reaching into earlier months are allowed (available at the origin).
- Test origins whose label time t+h passes the test month are scored with the realised label; in December, origins
  with t+h > 2018-12-31 23:00 are dropped for that horizon.

### 1.2 Tuning and refit
Tune on inner-train, score on inner-validation (section 4), refit on the full training window with the selected
hyper-parameters; iterative models use the early-stopped round/epoch count `[JC]` (avoids a second validation split).

### 1.3 Duration target and censoring
Training outages still running at `T_train_end` are right-censored there (never recorded as events). Test durations
may run past the test month (realised value used). Durations running at 2018-12-31 23:00 are censored.

### 1.4 Thesis-style random split (leakage quantification ONLY)
Within each month 20 % of hours drawn as test, 80 % train, seeds 0-4, no purge; models logistic, Markov-2, LightGBM,
MLP, LSTM; target (a), W0. Report `dBS_leak = BS_random - BS_rolling` per model and horizon (range over 5 draws).
Written only to `results/S1/leakage_randomsplit/`; never used for selection, ranking or go/no-go (test 16).

## 2. Information available at the forecast origin (end of hour t)
- **Lags:** `y_{t-k}`, k = 0..48 and 168; current run length; time since last outage start/end; outage counts over the
  past 6/24/168 h; state changes over the past 24 h.
- **Calendar:** hour of day (sin/cos), day of week, Friday flag, Iraqi public-holiday and Ramadan flags from a calendar
  file committed before the freeze (sources must be verified by the Literature officer).
- **Month and day-of-year excluded** `[JC]`: with one year the test month is always an unseen level.
- **Weather settings:** W0 none (MAIN); W1 realised weather at hours <= t (lags 0,1,3,6,12,24 + 24-h means) - labelled
  optimistic `[JC]` because reanalysis is published with a delay; W2 = W1 + realised weather at t+1..t+h (oracle upper
  bound, never in a headline claim).
- **Training-only climatology:** `P(outage | hour, month)` cannot be estimated for an unseen test month, so the
  reference is `p_clim(hour) = (n_out(hour) + 0.5) / (n(hour) + 1)` over all training origins; a last-training-month
  variant is reported as an extra baseline `[JC]` (full window = more stable, more conservative skill reference).
- Scalers/encoders fit only on the rows the model is trained on.

## 3. Models (24) and probabilities
- **Baselines:** persistence `p = y_t`; seasonal-naive `p = y_{t+h-24}`; climatology (above); Markov-1/2 with 0.5
  Laplace prior, exact matrix power / pair-state recursion, target (b) via an absorbing-state chain; logistic.
- **Duration:** Weibull AFT and penalised Cox PH (run-length + calendar features), point forecast = median survival;
  baseline = Kaplan-Meier conditional median remaining time given elapsed duration (training window).
- **ML:** kNN, SVM-RBF, RF, ExtraTrees, XGBoost, LightGBM, CatBoost; direct strategy (one model per target/horizon).
- **Deep:** MLP, LSTM, GRU, TCN, small Transformer; one multi-output head per target `[JC]` (compute).
- **Zero-shot FMs:** Chronos-2, Chronos-Bolt, TimesFM 2.5, TTM r2; 512-h context ending at t; covariates only in W1/W2
  where supported; `p = clip(mean forecast, 0, 1)`; target (b) via `1 - prod_k(1 - p_{t+k})` `[JC]` (independence
  assumption, bias reported).
- No post-hoc recalibration except Platt scaling for SVM on inner-validation `[JC]` (calibration is benchmarked).
  Log-loss only: clip to [1e-3, 1 - 1e-3]; persistence/seasonal-naive log-loss flagged as clip-dominated.

## 4. Tuning (equal budget)
- Optuna TPE, sampler seed 20180101, **60 trials per (model, target, horizon-group, re-tuning point)**; objective =
  mean inner-validation Brier; MedianPruner after 5 trials for every iterative model. Wall-clock cap per study to be
  set at freeze from a timing run on the PC (logged if hit).
- Re-tuning at folds 1, 4, 7; hyper-parameters reused for the next two folds `[JC]` (~3x less compute, still follows
  seasonal drift). Untuned: persistence, seasonal-naive, climatology, Markov; FMs use fixed 512-h context.

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
restored, best epoch kept for refit); tuning trials use seed 0.

## 5. Seeds
- Deep models: 10 seeds; stochastic tree/boosting models: 30 seeds; deterministic models (logistic, Markov, baselines,
  kNN, SVM, Weibull/Cox, FMs with seed 0 where sampling occurs): 1 run.
- Rationale: SE of a seed mean = SD/sqrt(n); 10 seeds -> 0.32 SD at affordable compute; cheap models get 30.
- Adaptive rule (frozen): if a deep model's seed SD of pooled Brier > 0.00125 (25 % of the minimum effect in 7), rerun
  with 20 seeds.
- Inference unit: per-origin Brier averaged over seeds (performance of a typical single run; averaging probabilities
  would be an unfair ensemble). Seed SD reported alongside.

## 6. Metrics and statistical inference
### 6.1 Metrics
- **Primary:** Brier score and Brier skill `BSS = 1 - BS/BS_clim` (training-only climatology), pooled over the 9 test
  folds per (target, horizon) and per fold.
- **Secondary:** log-loss, ROC-AUC, PR-AUC (outage = positive), MCC and F1 at the MCC-maximising threshold on
  inner-validation, ECE with 10 fixed equal-width bins, reliability curves with bin counts and block-bootstrap bands.
- **Duration:** MAE (h) on uncensored test origins; Harrell's C-index; both also at event-start origins only.

### 6.2 Confirmatory family (only these claims get a significance statement)
Q1, one test per horizon of target (a), W0 (5 tests): is "best ML/DL/FM model chosen per fold by inner-validation
Brier" better than "best simple model (persistence, seasonal-naive, climatology, Markov-1/2, logistic) chosen the same
way"? Selection never uses test months. Holm (1979) across the 5 tests, family-wise alpha = 0.05.

### 6.3 Pairwise tests respecting serial dependence
- `d_t = BS_A,t - BS_B,t` over pooled test origins.
- p-value: Diebold-Mariano (1995) with Newey-West (1987) HAC variance, lag `L = max(h - 1, 24)` `[JC]` (outage runs and
  the daily cycle autocorrelate `d_t` beyond h - 1), Harvey-Leybourne-Newbold (1997) correction, t_{n-1} reference.
- 95 % CI: circular moving-block bootstrap (Kuensch 1989), block 48 h, B = 5,000, blocks resampled within test month;
  sensitivity with automatic block length (Politis & White 2004 - citation still to be verified).
- DM p-value and bootstrap CI disagreeing at 0.05 -> labelled *fragile*.
- Duration intervals: event-cluster bootstrap (whole events), B = 5,000.
- Effect sizes with 95 % CIs: dBS, dBSS (pp), relative Brier reduction `1 - BS_A/BS_B`, dAUC, dMAE.
- All other pairs: Holm-adjusted p-values, labelled exploratory.

### 6.4 Descriptive ranking
Friedman + Nemenyi critical-difference diagrams (as in Demsar 2006) over 9 folds x 5 horizons = 45 blocks, Brier,
target (a), W0. Caveat printed with every diagram: blocks are not independent, p-values anti-conservative, ranking
descriptive only. Per-fold rank tables also reported.

### 6.5 Karbala transfer (time-respecting)
For KR test month m, use the BG model trained on BG months before m, no retraining, KR's own lags and calendar `[JC]`
(contemporaneous BG training hours would leak shared national-grid shocks). Same protocol natively on KR; BSS against
KR training-only climatology. Report `dBS_transfer = BS_BG->KR - BS_KR-native` (95 % block-bootstrap CI) and the share
of native BSS retained.

## 7. Go/no-go thresholds (pre-registered)
- **G1 complexity justified:** Q1 Holm-significant AND dBS <= -0.005 AND relative Brier reduction >= 5 %, at >= 2 of 5
  horizons; else NO-GO and the recommended forecaster is the best simple baseline `[JC]` (0.005 ~ 2 % of a ~0.25 Brier).
- **G2 weather value:** W1 beats W0 with dBS <= -0.003 and CI excluding 0 at >= 2 horizons; W2 only as upper bound.
- **G3 duration:** best duration model C-index >= 0.60 and MAE >= 10 % below the training-KM conditional median, CI
  excluding 0.
- **G4 transfer:** BG->KR keeps >= 50 % of KR-native BSS at h in {1, 6, 24}; exploratory if KR has > 5 % missing hours.
- **Leakage gate:** any failing test in section 8 blocks every result.
- Reporting: all 24 models at every horizon/target/weather setting, including failures and time-cap hits; nothing
  dropped after results are seen; a NO-GO is a primary finding; "significant" only within the confirmatory family.
- Layout under `results/S1/`: `config/` (frozen YAML, git commit, environment lock), `predictions/` (parquet per model x
  target x horizon x fold x seed), `metrics/`, `inference/`, `figures/`, `leakage_randomsplit/`,
  `tests/leakage_report.json`, `DEVIATIONS.md`. Manuscript tables generated from `metrics/` and `inference/` only.

## 8. Leakage tests the harness must pass (pytest)
1. `test_purge_train_labels`: every training (origin, label-time) has `label_time <= T_train_end` (all folds, horizons,
   targets; also inner-train vs inner-validation).
2. `test_test_origins_after_train`: `min(test origin) > T_train_end`; inner-validation month inside the training window.
3. `test_feature_causality`: for 500 random origins, overwriting all y and weather at times > t leaves W0/W1 features at
   t unchanged; in W2 only declared oracle columns change.
4. `test_climatology_training_only`: fold-k climatology unchanged when test-month labels are shuffled or zeroed.
5. `test_scaler_encoder_fit_scope`: scaler/encoder parameters unchanged when test rows are altered.
6. `test_test_index_guard`: test indices wrapped in a guard that raises on access during tuning/threshold selection.
7. `test_threshold_from_inner_val`: stored threshold reproduces from inner-validation predictions alone.
8. `test_local_time_no_double_shift`: on the loaded weather, mean GHI is 0 at local hours 0-3 and peaks at local hours
   11-13 (fails if the already-local file is shifted again).
9. `test_target_construction`: on a synthetic series, (a) = `shift(-h)`, (b) = forward rolling max over (t, t+h],
   (c) correct remaining duration and censoring flag.
10. `test_duration_censor_at_train_end`.
11. `test_fm_context_sentinel`: sentinels at t+1.. never reach foundation-model inputs; context ends exactly at t.
12. `test_seasonal_naive_index`: reads only `y_{t+h-24}`, h <= 24.
13. `test_label_permutation_canary`: permuted training labels -> pooled test BSS <= 0.01 (logistic, LightGBM, MLP).
14. `test_iid_null_series`: on i.i.d. Bernoulli(0.5), no model reaches pooled BSS > 0.01.
15. `test_transfer_time_order`: every BG training timestamp earlier than the KR test-month start.
16. `test_randomsplit_quarantine`: no file under `metrics/` or `inference/` contains a random-split run ID.
17. `test_determinism`: same seed + config -> bit-identical predictions for one model per family.

## Open items before freeze (day 2)
- Reviewer-2 pass on this draft (especially G1 thresholds, excluded month feature, DM lag choice).
- Timing run on the PC to set the wall-clock cap; check GPU availability for deep models and FMs.
- Verify Politis & White (2004) and the Iraqi holiday/Ramadan calendar source.
