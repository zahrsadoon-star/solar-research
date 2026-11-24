# Statistician review of S1 protocol DRAFT v0.9 and the robustness code

Author: Claude (Statistician agent), 2026-10-22. Read-only review. No existing file was edited, and no analysis was re-run.
Every number quoted from the project comes from a file named next to it. Numbers I computed myself are arithmetic
on design constants: critical values, minimum attainable p-values, and Nemenyi critical differences.

Inputs read:
- `method/S1_protocol.md`: DRAFT v0.9.
- `agent_notes/claude_reviewer2_S1.md`: the section "Statistical weaknesses" and the M/SHOULD items it relies on.
- Branch `origin/claude/s1-robustness-wip`, read with `git show`:
  - `studies/S1_outage_forecasting/pilot_v2/dispatch/README.md`.
  - `studies/S1_outage_forecasting/robustness/{bootstrap.py, stats_tests.py, common.py}`.
  - The headers of `robustness/diebold_mariano.csv` and `robustness/friedman.csv`.
- **Path note:** the two scripts are NOT under `pilot_v2/robustness/`, because that path does not exist on the branch. They are in
  `studies/S1_outage_forecasting/robustness/`.

## 0. Summary

1. **DM lag.** The DM design is sound in form, but the protocol's lag `max(h-1, 24)` is too short for hourly Brier
   differentials. On the pilot, the RF-vs-HourMarkov DM statistic for BG at h = 1 falls from -27.6 at lag 0 to -23.7 at lag 24
   and to -15.1 at lag 168 (`robustness/diebold_mariano.csv`). The variance therefore keeps growing well past 24 h.
   - Fix: tie the HAC bandwidth to the bootstrap block length. Use Bartlett at lag = L_block, which is the Künsch
     equivalence, choose L_block with Politis-White bounded to [48, 168] h, and use fixed-b critical values.
   - HLN is numerically irrelevant at T ≈ 6,600. The factor is 0.9964 at h = 24.
2. **Bootstrap block length.** A fixed 48 h block is not defensible by default. What matters is the dependence of the
   *loss differential* d_t, not the length of outage runs. However, the daily cycle and multi-day events (up to 59 h, BG
   May 28) make dependence at lags of 24-168 h plausible. Use the data-driven rule in 1.3.
3. **Holm family.** Holm must run over exactly the 5 Q1 tests (BG, target a, W0, h ∈ {1,3,6,12,24}). The protocol's
   "all other pairs: Holm-adjusted, exploratory" is meaningless at roughly 10^4 pairs. Report effect sizes and CIs there, with no
   p-values. Q1's "simple" pool must include the trailing-window climatology demanded by Reviewer 2 (M1). Otherwise
   the confirmatory test is against a weak reference.
4. **Friedman/Nemenyi: descriptive only.** With k = 24 models and N = 9 folds, the Nemenyi CD is 12.1 mean-rank units
   on a 1-24 scale, so it cannot separate anything but extremes. Pooling to 45 blocks only reduces the CD to 5.4, and
   that reduction is pseudo-replication.
5. **Dispatch.** The v2 regret minima are in-sample optima over about 556 knob points (README). Replace them with:
   - (i) ex-ante knob selection on preceding months, applied identically to the no-forecast (NF) families;
   - (ii) a paired, month-stratified block bootstrap of per-day contributions on the realised trajectory;
   - (iii) a Hansen SPA / White reality-check test whenever an in-sample best-of-many is shown;
   - (iv) an equivalence (TOST) statement, so that the negative result can be claimed.
6. **Code.** `bootstrap.py` bootstraps the **v1** simulator and the **v1** cached forecasts, not v2. Its CIs therefore do
   not apply to the v2 headline numbers. `stats_tests.py` has a structural power defect: per-horizon Wilcoxon with
   n = 9 and Holm over 15 pairs **cannot** reach p < 0.05. It also has several smaller issues (section 4).

## 1. Inference design for the forecasting comparison (protocol section 6)

### 1.1 Loss and test statistic
- Squared error on a binary outcome (the Brier score) is a strictly proper scoring rule, and the per-origin loss
  `(p - y)^2` is bounded in [0, 1]. DM needs only that d_t is covariance-stationary with a finite long-run variance (LRV),
  and boundedness covers the moment condition.
- The real threat is **non-stationarity**. The BG outage share moves from 0.12 to 0.80 across months, so the mean and the
  variance of d_t shift by month. A pooled HAC estimator with a global mean (stats_tests.py:73) lets month-to-month
  level shifts in d_t enter the residual autocovariances, which inflates the long-run variance. The result is
  conservative rather than anti-conservative, which is acceptable for a confirmatory test.
  - Keep the pooled DM as the primary test.
  - Add a month-stratified sensitivity: demean d_t within each test month, sum the month-wise HAC LRVs, and
    use mean(d) / sqrt(sum_m T_m^2 LRV_m / T^2).
- **Overlap.** For target (a), y_{t+h} forecasts made from consecutive origins overlap. Under correct specification this
  makes d_t at most MA(h-1), which is the theory behind lag h-1 and the HLN correction. In this setting the h-step loss
  differentials are *not* MA(h-1): misspecification and regime persistence give long memory. Lag h-1 is therefore a
  floor, never the setting. The same holds for target (b), and more strongly.
- **HLN.** The factor `sqrt((T+1-2h+h(h-1)/T)/T)` equals 0.99992 at h = 1 and 0.9964 at h = 24 for T = 6,600. It is
  harmless, but it is not a solution. It was derived for the rectangular-kernel, lag h-1 estimator, and adding it to a
  Bartlett estimator with lag 168 has no theoretical basis. Keep it only to match the literature, with t_{T-1} as the
  reference, and state that it changes nothing in practice.

### 1.2 HAC bandwidth (replaces `L = max(h-1, 24)`)
- **Kernel and lag.** Use the Bartlett kernel (Newey-West) with lag L_HAC = L_block, the block length chosen in 1.3.
  - Bartlett-kernel LRV at bandwidth L and the moving-block bootstrap variance with block L are asymptotically
    equivalent (Künsch 1989). Tying them means the DM p-value and the bootstrap CI differ only through the
    sampling distribution, not through bandwidth. A "fragile" flag then points to genuine non-normality and not to a
    tuning mismatch.
- **Why not lag 24.** Bartlett weights at lag j are 1 - j/(L+1). At L = 24, the lag-24 autocovariance, which holds the daily
  cycle of d_t, gets weight 0.04, so the daily periodicity is effectively ignored. The pilot DM statistics fall a
  lot between lag 24 and lag 168, for example BG h = 1 from -23.7 to -15.1 (`diebold_mariano.csv`). This is the
  signature of unmodelled positive dependence at multi-day lags.
- **Automatic rules are too small.** The Newey-West 1994 rule of thumb `4 (T/100)^(2/9)` gives about 10 lags at
  T = 6,600. Do not use it.
- **Critical values.** With L/T ≈ 0.007-0.025, use fixed-b critical values (Kiefer & Vogelsang 2005, Bartlett kernel).
  They are a few percent larger than 1.96, about 2.0 at b = 0.025. *The exact value and the citation must be checked
  by the Literature officer before freeze.* If that is not done, use N(0, 1) and report the fixed-b value as a sensitivity.
- **Sidedness.** Q1 is directional, but G1 adds a magnitude requirement anyway. Use **two-sided** p-values for
  conservatism and report the sign.

### 1.3 Circular moving-block bootstrap within month: block length
- **Is 48 h defensible?** Not as a fixed choice.
  - The relevant quantity is the autocorrelation of d_t = loss_A,t - loss_B,t. It is not the run length of y.
  - Two competent forecasters both get the middle of a long outage right (d_t ≈ 0 there), so long runs do not
    automatically create long memory in d_t.
  - However, both errors concentrate at event onsets and ends, which follow the daily load/rota cycle. Multi-day events
    (BG maximum 59 h, the 10 longest are 19-59 h per `pilot_v2/dispatch/README.md` section 6) and monthly regime shifts add
    dependence beyond 48 h. A 48 h block captures two daily cycles and would understate the variance if the d_t
    autocorrelation function (ACF) is still non-zero at lags 72-168.
  - The pilot DM evidence above suggests that it is.
- **Rule to freeze (data-driven, set before any test prediction):**
  1. For each confirmatory comparison (the 5 Q1 tests), compute the Politis & White (2004) automatic block length for the
     **circular** block bootstrap on the pooled Apr-Dec d_t series. Use the Patton, Politis & White (2009) correction,
     which is the version implemented in `arch.bootstrap.optimal_block_length`; its `circular` column is the one to use.
     Also compute it per test month and take the median.
  2. Set L_block = the larger of the two, rounded **up** to a multiple of 24 h, then clipped to [48, 168] h.
  3. Use the same L_block as the Bartlett HAC lag (1.2).
  4. Freeze the code and the rule. The *value* is a function of the test-set d_t, which is legitimate because it governs
     only precision, not the point estimate. Log the value in `inference/block_lengths.csv`.
  5. As a sensitivity, report the CI at fixed L ∈ {24, 168}. If the confirmatory decision changes between them, label the
     result *fragile*.
  6. Also show the ACF of d_t up to lag 336 for each Q1 comparison, with the ±2/sqrt(T) band, in the supplement.
- **Mechanics.**
  - Resample within each test month m, with month length T_m.
  - Draw ceil(T_m / L) start points uniformly on 1..T_m, wrap circularly *within the month*, concatenate, and truncate
    to T_m, so every replicate keeps the exact month weights.
  - Use the same index set for every model in a comparison (paired), and for the climatology denominator when
    computing BSS. Resample the numerator and the denominator jointly; never resample them separately.
  - B = 9,999. Use the percentile CI for dBS and relative reduction, and a BCa sensitivity for BSS, which is a ratio.
  - Bootstrap p-value: the share of centred replicates beyond the observed |mean d|.
  - The December test month is truncated per horizon (protocol 1.1), so use T_m per horizon.
- **Duration target (c).** The event-cluster bootstrap in the protocol is correct. Stratify it by month as well, and resample
  events, not origins.

### 1.4 Multiple comparisons
- **Confirmatory family = exactly 5 hypotheses:** Q1 at h ∈ {1, 3, 6, 12, 24}, BG, target (a), W0, Holm at family-wise
  α = 0.05. KR (transfer, G4), targets (b) and (c), W1, W2 and the duration models are *not* in the family. The
  protocol should say "BG", because the current text does not name the site.
- **Q1 baseline pool.** Add Reviewer 2's trailing-window hour-of-day climatology (7, 14 and 28 d, selected by inner-validation
  like the others) to the "best simple model" pool. It is cheap and causal, and the pilot shows it is much stronger than
  the expanding climatology (Reviewer 2, M1). Without it, Q1 tests "ML vs weak baselines".
  - Also report BSS against both the expanding and the trailing climatology. Name which one is the headline before freeze.
- **Holm vs dependence.** The five horizons are strongly positively dependent, and Holm is valid but conservative under
  that dependence. A single-step max-|t| (Westfall-Young) adjustment from the same paired block bootstrap would be more
  powerful.
  - This is optional. If it is used, freeze it now and keep Holm as the reported primary to avoid a choice after seeing
    the results.
- **G1 consistency.** G1 needs Holm significance, dBS ≤ -0.005 and relative reduction ≥ 5 % at ≥ 2 of 5 horizons.
  Add "and the 95 % CI upper bound of dBS < 0" so that the magnitude criterion is not met by a point estimate alone.
- **Exploratory pairs (protocol 6.3, last bullet).** Delete "Holm-adjusted p-values" for "all other pairs".
  - The space is 24 models × 5 horizons × 3 targets × 3 weather settings × 2 sites, which is about 10^4 pairs. Holm over
    it is meaningless, and Holm within ad-hoc subsets invites forking paths.
  - Report dBS with 95 % block-bootstrap CIs and no p-values, explicitly labelled exploratory.
  - If p-values are wanted for a named secondary family (e.g. G2: W1 vs W0, 5 horizons), pre-register that family
    and run Holm within it.

### 1.5 Friedman / Nemenyi
- **Precision.** Critical differences, at α = 0.05, use the studentised range divided by √2:

  | k models | N blocks | q_0.05 | Nemenyi CD (mean-rank units) |
  |---|---|---|---|
  | 6 (pilot) | 9 | 2.850 | 2.51 |
  | 6 (pilot) | 45 | 2.850 | 1.12 |
  | 24 (S1) | 9 | 3.637 | **12.12** |
  | 24 (S1) | 45 | 3.637 | 5.42 |

  With 24 models and 9 folds, two models must differ by half the rank scale before Nemenyi separates them. Pooling 45
  horizon × month blocks shrinks the CD by √5 only by treating highly correlated horizons as independent replicates.
- **Independence.** The 9 months are not independent either. They share expanding training windows and the serial
  dependence of the outage process. The robustness code's description of per-horizon blocks as "independent months, the
  conservative version" (stats_tests.py:6-7) is incorrect.
- **Recommendation.** Treat this section as descriptive only.
  - Report mean ranks per horizon (N = 9 blocks, never the 45-block pool).
  - Use CD diagrams with the caveat. Show the Friedman/Iman-Davenport statistic **without** a significance claim, or omit
    p-values entirely.
  - Show the per-fold rank table (protocol 6.4 already says so).
  - Any inferential claim about a pair comes from DM plus the block bootstrap (6.3), never from Nemenyi.

## 2. Dispatch study: honest selection and inference

### 2.1 What v2 did
Source: `pilot_v2/dispatch/README.md`.
- Regret is computed against the NF Pareto front at equal stress, either interpolated or by step.
- The reported numbers are the *minimum* regret per configuration, over about 556 swept forecast-policy points:
  - θ 0.00-0.99 for binary top-up,
  - S_low × S_high for RiskTarget,
  - × 4 forecasters (plus PerfectBinary).
- The NF front is also an in-sample envelope over its own swept knobs.
- The README itself says that no ex-ante threshold choice, bootstrap or significance test was made, and that the minima
  are "optimistic". The largest LPSP gain is 0.23 pp, about 45 kWh over nine months.

A minimum over hundreds of noisy, correlated points is biased downward even if no policy has real value. Two things fix
this:
- (a) an ex-ante, out-of-sample evaluation, which is the primary analysis;
- (b) a multiple-comparison-aware test whenever an in-sample best-of-many is shown.

### 2.2 Primary analysis: ex-ante knob selection (time-respecting)
1. **Scalarise.** A knob can only be selected ex ante against a scalar objective. Pre-register
   `J_λ = LPSP_pp + λ · stress` for a fixed grid of λ, separately for each stress plane: hours with SOC ≥ 80 % (per 100 h),
   and mean SOC (per pp).
   - The λ grid is a `[JC]` and must be frozen *before* the v3 run: 5 log-spaced values per plane, spanning
     the range of NF-front slopes reported in v1/v2. The grid is chosen from the v2 figures, which is acceptable because
     it fixes the question, not the winner.
   - Also report the constraint version: minimise stress subject to LPSP ≤ (Blanket LPSP of the selection window) +
     0.10 pp.
2. **Select on preceding months.** For each test month m ∈ {May..Dec} and each family F (NF a1/a2/b, binary top-up per
   forecaster, RiskTarget per forecaster):
   - choose the knob that minimises J_λ on months Apr..m-1 (expanding);
   - use the *out-of-sample* forecasts for those months, which already exist from the rolling-origin folds.
   - **April** has no out-of-sample history. Use the pre-registered default knob for every family: for binary top-up,
     the cost threshold θ* = c_stress / (c_stress + c_unserved) implied by λ; for NF, S = the value with the same
     implied trade-off. Alternatively, drop April from the evaluation and use it only for selection. Freeze one option;
     I recommend **dropping April from scoring** (cleaner).
3. **Simulate one continuous trajectory.** Use Apr-Dec with the knob switching at month boundaries and the battery
   state carried over. This gives one realised out-of-sample (LPSP, stress, J_λ) per family per λ.
4. **Treat NF identically.** The NF families get exactly the same selection procedure. The comparison is then "best
   ex-ante forecast family vs best ex-ante NF family", where the family winner is *also* selected on preceding months.
   - Pre-register one primary pair: RiskTarget(RF), with S_high selected among {0.8, 0.9, 1.0}, vs SOC-target a2.
   - Other pairs are secondary.
5. **Sensitivity.** Use a rolling 2-month selection window instead of an expanding one, because seasonal regimes differ.
   Also run leave-one-month-out cross-fitting (select on the other 8 months), clearly labelled
   *not time-respecting*, as an upper bound on what ex-ante selection could achieve.
6. Keep the full frontier figures as descriptive context, captioned "in-sample envelope, optimistic".

### 2.3 Inference on a single trajectory
- **Resampling unit.** Use **per-day contributions** from ONE continuous simulation of each policy: unserved kWh,
  load kWh, hours with SOC ≥ 80 %, and the SOC sum. This is what bootstrap.py's "approximate" method does with weekly
  blocks.
  - Battery state stays as realised, so there are no artificial joins.
  - The ratio statistics (LPSP = Σ unserved / Σ load) are recomputed from the resampled sums.
  - Day boundaries are at 00:00 local time.
  - This conditions on the realised state path, which is the right conditioning for "this household, this year". Say
    so in the paper.
- **Scheme.** Use a month-stratified circular block bootstrap of days.
  - Block length: 7 days (168 h) primary, 3 and 14 days as sensitivity. 7 days exceeds the longest BG event (59 h) by
    a wide margin, and multi-day outage clusters stay intact.
  - Resample within each month to keep the seasonal mix fixed. The current bootstrap.py resamples weeks across
    Apr-Dec, so a replicate can contain July five times.
  - Use **paired** resampling: the same day indices for all policies, so differences are computed per replicate.
  - B = 9,999.
- **Statistics.** Report each with a percentile 95 % CI:
  - ΔLPSP (pp, and kWh);
  - Δ hours ≥ 80 %;
  - Δ mean SOC;
  - ΔJ_λ;
  - the share of replicates with Δ < 0.
- **Episode sensitivity.**
  - BG unserved energy is concentrated in a few multi-day events. At the thesis size it is 100 % inside one 59 h event,
    per README section 6.
  - Report a leave-one-episode-out jackknife of ΔLPSP. An episode is an outage event plus the preceding 24 h charging
    window.
  - Report ΔLPSP after removing the top 1, 3 and 5 episodes ranked by unserved energy.
  - Report an episode-resampling bootstrap: resample outage episodes with replacement within month, together with
    their contributions. This bootstrap is secondary.
- **p-value.**
  - Use a sign-flip randomisation test on the paired weekly differences of unserved kWh: 2^k flips, or 9,999 random
    flips if k is large, stratified by month. It assumes symmetric exchangeability of the paired weekly differences
    under H0, so state that assumption.
  - The bootstrap CI is primary. The test is secondary.
- **Equivalence.** The likely outcome is "no material dispatch value", so pre-register an equivalence margin
  `δ = 0.10 pp LPSP` (about 20 kWh on 19.5 MWh BG Apr-Dec load; README "Limitations") and `δ_stress = 100 h ≥ 80 %` `[JC]`.
  - Claim "no practically relevant forecast value" only if the 90 % CI (TOST, α = 0.05 each side) lies inside ±δ.
  - Otherwise the result is "inconclusive", never "no effect".
- **Seeds and models.** Forecasts are not refitted inside the bootstrap, so the CIs are conditional on the fitted
  models. Show RF seed variation separately: the dispatch rerun over the 10 forecast seeds, reported as min/median/max of
  each Δ.

### 2.4 If in-sample best-of-many numbers are reported at all
- Test them with Hansen's (2005) SPA test, or White's (2000) Reality Check, over **all** swept forecast-policy points at a
  fixed λ.
  - Benchmark: the best NF point at that λ, also selected in sample.
  - Loss per resampled unit: the per-day contribution to J_λ.
  - Use the same stratified block bootstrap (7 days).
- H0 is "no forecast-policy point beats the best NF point". Report the SPA consistent p-value next to the minimum
  regret. Without it, the minima must carry the label "selected in sample over N points, not tested".

## 3. Seeds and tuning (protocol sections 4 and 5)

### 3.1 Number of seeds
- **Current draft.** Deep models get 10 seeds, stochastic tree/boosting models 30, and deterministic models 1. The adaptive
  rule switches a deep model to 20 seeds if its seed SD > 0.00125.
- **Recommendation: target precision directly, the same way for every stochastic family.**
  - n_seeds = max(10, ceil((SD_pilot / 0.0005)^2)), capped at 30.
  - SD_pilot is the seed SD of pooled test Brier from the first 10 seeds.
  - The goal is an SE of the seed mean ≤ 0.0005, which is 10 % of the G1 margin of 0.005.
  - The rule changes only precision, not which comparisons are made, so it is legitimate after seeing the first 10.
  - Apply it to deep **and** tree/boosting models alike. The current asymmetric 30 vs 10 has no statistical rationale,
    and RF/ExtraTrees with 500 trees usually have a much smaller seed SD than neural networks.
- **Evaluation seeds must be disjoint from the tuning seed.** Tuning trials use seed 0, so evaluate on seeds 1..n. With
  seed 0 inside the evaluation set, the hyper-parameters were chosen while conditioning on one of the evaluated runs.
  This is not test leakage, but it is mildly optimistic for that run.
- **Determinism, so that test 17 can pass.**
  - Python `random`, NumPy and torch seeds.
  - `torch.use_deterministic_algorithms(True)` and cuDNN deterministic.
  - LightGBM `deterministic=True, force_row_wise=True, seed`.
  - XGBoost `seed` with a fixed `nthread`.
  - CatBoost `random_seed` with a fixed `thread_count`.
  - A fixed thread count everywhere.
  - Log library versions.
- **FMs.** Use deterministic point forecasts (mean or median). Where sampling is used, use a fixed seed and ≥ 20 samples.

### 3.2 Inference unit and reporting of seed variability
- **Confirmatory inference.** Use the per-origin loss averaged over seeds (protocol section 5, as drafted). It is the
  expected loss of a single run and not an ensemble, which is fine.
  - The robustness code instead uses RF seed 42 alone (stats_tests.py:94, 101). For v1.0 this must follow the protocol.
- **Report per model × target × horizon:**
  - seed mean of pooled Brier;
  - seed SD;
  - min-max;
  - for each Q1 comparison, the fraction of seeds whose single-run dBS < 0;
  - the DM statistic range over seeds, as the pilot code already does (DM_min/DM_max).
- **Selection inside Q1** ("best per fold by inner-validation") uses the seed-mean inner-validation Brier. Selection is
  therefore not affected by a lucky seed.

### 3.3 Equal tuning budget
- **Trial counts.** 60 TPE trials per study is a reasonable equal budget. Freeze:
  - `n_startup_trials = 10` (random), then TPE with `multivariate=True`;
  - MedianPruner with `n_startup_trials = 5`, `n_warmup_steps` = 10 epochs (deep) or 100 rounds (boosting).
  - A pruned trial counts as a trial.
- **Fairness caveat.** Equal *trials* is not equal *search effort* across search spaces of different dimension. SVM has 2
  hyper-parameters; boosting has 7. Report, for each study:
  - best-so-far inner-validation Brier vs trial number;
  - a convergence flag, set if the best value improved by > 0.0005 over the last 20 trials.
  - A flagged family is reported as "possibly under-tuned". The budget is NOT extended post hoc.
- **Wall-clock cap.** A cap that is hit only for some families breaks equality. Report the trial count reached, and treat
  a cap hit as a deviation in DEVIATIONS.md.
- **Seeds of the samplers.** A single sampler seed (20180101) for every study is acceptable, provided each study is
  independent. Record the study name ↔ seed mapping.
- **Untuned models.** Baselines, Markov and FMs are untuned by design. State that in tables as "0 trials" rather than
  leaving it implicit.

## 4. Code review (branch origin/claude/s1-robustness-wip, `studies/S1_outage_forecasting/robustness/`)

### 4.1 bootstrap.py
| # | Line(s) | Severity | Issue | Fix |
|---|---|---|---|---|
| B1 | 29, 163 | **High** | It imports the **v1** simulator (`dispatch_value.simulate`) and the **v1** cached forecasts `pilot/results/forecasts_{site}_h6.pkl`. That cache is git-ignored and stale (Reviewer 2 SHOULD-6). v1 also has the issues fixed in v2: the double SOC definition, end-of-hour features, efficiencies and the Mode 0 C-rate. The CIs therefore describe the v1 setup and **cannot be attached to any v2 number**. | Port the bootstrap to `pilot_v2/dispatch/simulator_v2.py` and the hashed v2 forecast cache. |
| B2 | 3-4, 40, 141 | **High** | The comparator is HourMarkov, and the statistic is LPSP at Mode 0's stress. Neither is the M2 question, which is forecast vs the best **no-forecast** family at equal stress. | Bootstrap ΔJ_λ and ΔLPSP vs the ex-ante NF policy (section 2). |
| B3 | 57-58, 84, 124 | Medium | 168 h blocks are drawn **across** Apr-Dec, with no month stratification. Replicates change the seasonal mix: a replicate can over-represent July, BG outage share 0.80, or October, 0.15. That inflates the variance and can shift the centre. | Stratify by month (section 2.3). |
| B4 | 6-7, 58, 84 | Low | 6,600 = 39 × 168 + 48. The short last block is drawn like any other, so replicate length varies (about 6,552-6,720 h). The ratio statistics survive, but the hour-count statistic ("hours ≥ 80 %") changes scale between replicates. | Use a circular wrap so that every block has 168 h, and truncate to 6,600. |
| B5 | 75-78 | Medium (acknowledged in the docstring) | In the "exact" method, the battery state and Mode 0's night test, which uses PV at t-1, run across artificial joins. Forecasts at joins look ahead into the original, not the resampled, future. | Prefer the per-block contribution method as the primary: it has no joins. Keep the exact method as a check. |
| B6 | 72, 85-87, 109-112 | Medium (reproducibility) | Worker inputs travel through the module global `_G`, which is filled *before* `Pool(2)` and relies on `fork` (comment on line 71). On Windows, which is the project PC, `spawn` gives workers an empty `_G`, so it raises `KeyError`. The script cannot run on the project PC as written. | Pass the inputs through `Pool(initializer=..., initargs=...)` or `functools.partial`. |
| B7 | 142, 146 + common.py:54-55 | Medium | `frontier_lpsp_at` returns NaN outside the frontier's range, and `dropna()` silently discards those replicates. The CI is then conditional on "Mode 0's stress lies inside the forecaster's range", which is selection on the outcome. `n_nan` is reported but not used. | Report the NaN share prominently. Define the statistic so that it is always defined, e.g. ΔJ_λ, or score NaN as "no point at equal stress". |
| B8 | common.py:52-59 | Medium | The "frontier" interpolation runs through **all** θ points sorted by hours, including dominated points and chords across unsampled gaps. It is not the Pareto lower envelope (Reviewer 2 M4, the KR Markov/Clim gap). | Interpolate on the lower convex/Pareto envelope only, with the v2 bracket-width rule. |
| B9 | 168-170 | Low | The exact bootstrap pickle is reused if it exists, with no hash of config, seed or N_BOOT, so stale results can be reused silently (the same issue as SHOULD-6). | Hash the configuration into the file name. |
| B10 | 172, 177 | Info | Exact and approximate bootstraps use the same seed, so they get identical block draws: common random numbers. This is fine for comparing the two methods, but they are not independent validations. State that. | Document it. |
| B11 | 36 | Low | B = 1,000 is thin for 2.5 %/97.5 % percentiles. The Monte-Carlo SE of each quantile is non-trivial. | B = 9,999 for reported CIs. |
| B12 | 9-11 | Info | The CIs are conditional on the fitted models (no refit), as acknowledged. | Add the seed spread (section 2.3). |

### 4.2 stats_tests.py
| # | Line(s) | Severity | Issue | Fix |
|---|---|---|---|---|
| S1 | 61, 66, 117-120 | **High (design)** | Per-horizon Wilcoxon signed-rank with n = 9 blocks: the smallest attainable exact two-sided p-value is 2/2^9 = 0.0039. Holm's first multiplier over 15 pairs is 15, so the **smallest Holm-adjusted p is 0.059 > 0.05**. The per-horizon post-hoc table can never show a significant pair, whatever the data. On 45 dependent blocks it is anti-conservative instead. | Drop the per-fold Wilcoxon/Holm. Pairwise inference comes from DM plus the block bootstrap; ranks are descriptive (section 1.5). |
| S2 | 101 | **High** | The primary DM uses HAC lag h-1 (lag 0 at h = 1) with HLN, described as "as specified". Protocol v0.9 now says `max(h-1, 24)`, and section 1.2 above recommends L_block. On BG h = 1 the pilot output is DM = -27.6 at lag 0 vs -15.1 at lag 168 (`diebold_mariano.csv`). Lag h-1 grossly understates the variance. | Use lag = L_block (section 1.2) and report lags 24 and 168 as sensitivity. |
| S3 | 78-82 | Low | HLN is applied only with the lag h-1 variant, and with a t reference; the other lags use the normal distribution. The HLN factor is derived for the rectangular kernel, but the code uses Bartlett (line 76). It is numerically negligible at T ≈ 6,600, but the labelling ("HLN-corrected") overstates what it does. | Keep it consistent: apply the same reference distribution to every lag, or use fixed-b critical values. |
| S4 | 73 | Medium | Pooled demeaning over Apr-Dec. Monthly level shifts in d_t enter the autocovariances, so the result is conservative, but not documented. | Add the month-stratified LRV as a sensitivity (section 1.1). |
| S5 | 92-95, 101 | Medium | The inference unit is a single RF seed (42), with other seeds shown only as a DM range. The protocol says per-origin loss averaged over seeds. | Average losses over seeds 1..n first, then run DM. |
| S6 | 89-91 | Medium | The DM comparators are HourMarkov, Logistic and Climatology (expanding). Per Reviewer 2 M1, the strongest baseline (trailing climatology, seasonal-naive, recency Markov) is missing, so the most important comparison is not tested. | Add the strongest baseline as model_b. |
| S7 | 89-104, 143 | Medium | 2 sites × 5 h × 3 pairs × 3 lags × 11 seeds DM tests are written with **no multiplicity adjustment** and no designation of which are confirmatory. | Mark the 5 Q1 tests as confirmatory (Holm); write everything else without p-values or label it exploratory. |
| S8 | 3-7, 117-119 | Medium | The docstring calls the per-horizon blocks "independent months ... the conservative version". Months share expanding training data and serial dependence, so they are not independent, and N = 9 is low-power rather than conservative. The Friedman p-values (e.g. 1.1e-35 for BG on 45 blocks, `friedman.csv`) are reported without the dependence caveat in the CSV. | Fix the wording. Mark Friedman output as descriptive. |
| S9 | 39-41 | Low | `pivot_table` (default aggfunc = mean) silently averages duplicates. If a model ever appears both as seed -1 and seeded, the rows are merged without warning. | Use `pivot` (which raises on duplicates) or assert uniqueness. |
| S10 | 50 | Info | Nemenyi q = 2.850 is correct for k = 6 only and is hard-coded. With 24 models, use q = 3.637 (studentised range q_0.05(24, ∞)/√2). | Compute q from `scipy.stats.studentized_range`. |
| S11 | 47-48 | OK | The Iman-Davenport F and its df are correct. The ranks (line 49) ascend, so 1 = lowest Brier, which is correct. | n/a |
| S12 | 98-99 | OK | Index alignment and contiguity asserts are good. Keep them, and add a check that the series spans Apr-Dec with no gaps beyond the December truncation. | n/a |

The DM recursion itself (lines 72-77) is a correct Bartlett/Newey-West estimator. `dm` uses `sqrt(lrv/T)`, which is
correct. I found no arithmetic error in it. The problems are bandwidth, unit and family, not algebra.

## 5. Other protocol points with statistical consequences
- **6.1 BSS reference.** BSS against the expanding climatology alone inherits Reviewer 2 M1. Report BSS against the
  trailing 14-d climatology as well, and name the headline before freeze. G1 is defined on dBS, so G1 itself is unaffected.
- **6.1 ECE.** Ten equal-width bins are fine. Add equal-mass bins as a sensitivity. Put the reliability bands on the same
  month-stratified blocks.
- **6.1 MCC/F1 threshold.** Selecting the threshold on inner-validation is correct. Report thresholded metrics as secondary
  only, because they are not proper scores.
- **6.5 Transfer.** Run the same block bootstrap with L_block computed on the KR d_t. G4's "≥ 50 % of native BSS" needs a CI
  on the ratio. Use a paired bootstrap of numerator and denominator, BCa, and declare the result inconclusive if the CI
  straddles 50 %.
- **1.4 Random-split leakage.** This is descriptive and needs no inference. Keep it out of every test family, as drafted.
- **Pre-specified minimum effects.** 0.005 Brier (G1) and 0.003 (G2) are fine. Add the dispatch equivalence margins
  (section 2.3) to section 7.

## Exact settings to freeze in v1.0

### Forecast-comparison inference
- primary_metric: Brier (pooled over Apr-Dec test origins); secondary metrics as in v0.9 6.1
- loss_differential: d_t = seed-mean per-origin Brier of A - same for B (seeds 1..n)
- confirmatory_family: Q1 x h in {1,3,6,12,24}; site BG; target (a); weather W0; 5 hypotheses
- q1_simple_pool: persistence, seasonal-naive, expanding climatology, trailing hour-of-day climatology {7,14,28 d}, Markov-1, Markov-2, logistic (best chosen per fold by inner-validation Brier)
- multiplicity: Holm (1979), family-wise alpha 0.05, two-sided; optional Westfall-Young max-|t| sensitivity
- exploratory_comparisons: effect sizes + 95 % block-bootstrap CIs, no p-values (unless a named secondary family is pre-registered, e.g. G2 with Holm over 5 horizons)
- dm_variance: Newey-West Bartlett kernel, global demeaning
- dm_hac_lag: L_block (as below), never below h-1
- dm_reference: fixed-b Bartlett critical values (Kiefer & Vogelsang 2005; value and citation to verify); report N(0,1) p-value alongside
- dm_hln: applied (factor reported); declared numerically negligible
- dm_sensitivity: HAC lag 24 and 168; month-stratified LRV
- bootstrap_type: circular moving-block, within test month, paired across models (and with climatology for BSS)
- block_length_rule: L_block = clip(ceil24(max(PW_circular(d pooled), median_m PW_circular(d_m))), 48, 168) h; Politis & White (2004) with Patton-Politis-White (2009) correction (arch.bootstrap.optimal_block_length); per confirmatory comparison; values logged to inference/block_lengths.csv
- block_length_sensitivity: fixed 24 h and 168 h
- bootstrap_B: 9,999
- bootstrap_seed: 20180102
- ci_method: percentile (dBS, relative reduction); BCa for BSS and transfer ratio
- fragile_flag: DM (fixed-b) and bootstrap CI disagree at 0.05, OR decision changes between L = 24 and L = 168
- g1_add: 95 % CI upper bound of dBS < 0 in addition to v0.9 criteria
- duration_bootstrap: event-cluster, stratified by test month, B = 9,999
- friedman_nemenyi: descriptive only; per horizon, N = 9 blocks; no 45-block pooling; no p-values in text; q from studentized_range (k = 24: q = 3.637, CD = 12.1)
- acf_report: ACF of d_t to lag 336 for each Q1 comparison (supplement)

### Seeds and tuning
- seeds_stochastic_models (all deep and tree/boosting families alike): n = max(10, ceil((SD10 / 0.0005)^2)), cap 30; SD10 = seed SD of pooled test Brier over the first 10 seeds
- evaluation_seeds: 1..n (tuning seed 0 excluded)
- deterministic_models: 1 run
- fm_sampling: deterministic point forecast; if sampling, seed 0 and >= 20 samples
- seed_reporting: mean, SD, min-max of pooled Brier; share of seeds with dBS < 0 per Q1 comparison; DM range over seeds
- optuna_sampler: TPE, multivariate=True, n_startup_trials=10, seed 20180101
- optuna_trials: 60 per (model, target, horizon-group, re-tuning point); pruned trials count
- optuna_pruner: MedianPruner(n_startup_trials=5, n_warmup_steps=10 epochs | 100 boosting rounds)
- tuning_objective: mean inner-validation Brier, seed 0
- convergence_flag: best-so-far improvement > 0.0005 over the last 20 trials -> "possibly under-tuned", no budget extension
- wall_clock_cap: set from the timing run; any hit logged in DEVIATIONS.md with trials reached
- determinism: python/numpy/torch seeds; torch deterministic algorithms; LightGBM deterministic=True, force_row_wise=True; fixed thread counts; library versions in environment lock

### Dispatch study
- primary_objective: J_lambda = LPSP_pp + lambda * stress; planes: hours SOC >= 80 % (per 100 h) and mean SOC (per pp)
- lambda_grid: 5 log-spaced values per plane, fixed before the v3 run from the v2 NF-front slope range [JC]
- constraint_variant: min stress s.t. LPSP <= Blanket LPSP (selection window) + 0.10 pp
- knob_selection: expanding window of preceding months (Apr..m-1) using out-of-sample forecasts; same procedure for every NF and forecast family; family winner also selected on preceding months
- scored_months: May-Dec (April used for selection only)
- selection_sensitivity: rolling 2-month window; leave-one-month-out cross-fit (labelled not time-respecting)
- trajectory: one continuous simulation, knobs switch at month boundaries, battery state carried
- primary_dispatch_pair: RiskTarget(RF; S_high selected from {0.8, 0.9, 1.0}) vs SOC-target a2
- simulator_and_forecasts: pilot_v2 simulator_v2 + hashed v2 forecast cache (never v1 cache)
- dispatch_bootstrap: paired, month-stratified circular block bootstrap of per-day contributions (unserved kWh, load kWh, hours >= 80 %, SOC sum) from the realised simulation
- dispatch_block_length: 7 days; sensitivity 3 and 14 days
- dispatch_B: 9,999; seed 20180103
- dispatch_statistics: dLPSP (pp, kWh), d hours >= 80 %, d mean SOC, dJ_lambda; percentile 95 % CI; share of replicates < 0
- dispatch_test: month-stratified sign-flip randomisation on weekly paired unserved-kWh differences (secondary)
- episode_sensitivity: leave-one-episode-out jackknife; dLPSP without top 1/3/5 episodes; episode-resampling bootstrap
- equivalence_margins: delta_LPSP = 0.10 pp; delta_stress = 100 h >= 80 % [JC]; TOST with 90 % CI
- in_sample_minima: only with Hansen (2005) SPA p-value over all swept points at fixed lambda vs in-sample best NF; otherwise labelled "selected in sample over N points, untested"
- forecast_seed_spread: dispatch rerun over the RF seeds 1..n, min/median/max of each delta

### Items to verify before freeze (Literature officer)
- Politis & White (2004), Econometric Reviews 23(1), 53-70; Patton, Politis & White (2009), Econometric Reviews 28(4), 372-375.
- Kiefer & Vogelsang (2005), Econometric Theory 21: fixed-b critical-value formula for the Bartlett kernel.
- Hansen (2005), JBES 23(4) (SPA); White (2000), Econometrica 68(5) (Reality Check); Künsch (1989), Annals of Statistics 17(3).
