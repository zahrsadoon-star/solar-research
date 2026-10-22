راجعت السياق وخطة الدراسة والبروتوكول والملاحظات. أدناه خطة المنهجية بالإنكليزي. ما حفظتها إلى `agent_notes/PLAN.md` لأن الجلسة **read-only** وطلبت **No edits**؛ وما شغّلت تجارب أو اختبارات.

**S1 WP2 methodology plan — proposed content for `agent_notes/PLAN.md`**

The controlling specification is the repository’s [v1.0-rc protocol](method/S1_protocol.md), including its incorporated reviewer corrections. It supersedes conflicting choices in the original task and study plan. This document specifies implementation and acceptance requirements; it reports no experimental results.

**1. Scope and configuration**

WP2 builds and validates the evaluation harness, then exercises it using BG, W0, target (a), all five horizons, and the seven requested reference model families. Smoke results cannot establish Q1 or G1: the complete baseline and ML comparison pools arrive in later work packages.

Every numerical setting, model pool, hypothesis family, label definition, split rule, seed, threshold convention and inference option must be represented in a typed configuration loaded from `config/S1_frozen.yaml`. The configuration directory was absent when inspected.

Before benchmark test predictions, hash the protocol, configuration and approved calendar. Record timing caps separately in `config/S1_timing_caps.yaml` and hash them as an addendum. Record subsequent deviations explicitly; never silently amend frozen settings.

**2. Observations, timing and targets**

Load observations through `src/outage/data.py`. Preserve its source `outage` column, which represents generator operation; construct the configured evaluation label separately:

- Primary: \(y_t=\mathbf1[\mathrm{grid\_kwh}_t=0]\).
- S-gen sensitivity: \(y_t=\mathbf1[\mathrm{generator\_kwh}_t>0]\).

Generate timestamped disagreements from the source energies in `results/S1/label_disagreement.csv`. Do not copy counts from prior notes. Both definitions are consumption-derived proxies, not independently verified grid availability.

Under the protocol’s hour-beginning convention, row \(t\) covers \([t,t+1)\), and its forecast is issued at \(t+1\). Row \(y_t\) is assumed available with zero latency. Store both the observed-row timestamp and issuance timestamp to prevent off-by-one errors.

| Target | Definition | Scoring |
|---|---|---|
| (a) | \(y_{t+h}\), \(h\in\{1,3,6,12,24\}\) hours | Require observed origin and target |
| (b) | \(z_{t,h}=\max_{k=1}^{h}y_{t+k}\) | Require every constituent label; report \(h\in\{3,6,12,24\}\) |
| (c) | \(R_t=\min\{k\ge1:y_{t+k}=0\}\), conditional on \(y_t=1\) | Preserve right-censoring; MAE uses uncensored cases |

For an outage of total length \(D\), observed through elapsed length \(e\), \(R_t=D-e+1\). Thus \(R_t-1\), rather than \(R_t\), is the number of further outage hours after issuance.

For a boundary \(b\), a still-running outage contributes \(R_t>b-t\), not an invented completed duration. Censor independently at inner-training, training and dataset boundaries. Never use the eventual completion beyond a fitting or selection boundary.

Missing labels are never imputed for scoring. Missing historical features use training-scope imputation plus missing indicators. The existing WP1 loader rejects incomplete source series; missingness behavior must therefore also be exercised with synthetic fixtures.

**3. Time-respecting splits**

Use nine expanding folds:

| Test month | Training | Inner-training | Inner-validation |
|---|---|---|---|
| April | January–March | January–February | March |
| May | January–April | January–March | April |
| … | … | … | … |
| December | January–November | January–October | November |

Apply these rules using row timestamps consistently:

- Retain fitting origins only when \(t+24\le T_{\mathrm{fit,end}}\), including inner-training.
- Retain inner-validation origins only when \(t+h\le T_{\mathrm{train,end}}\).
- Test origins belong to their assigned calendar month. Historical lags may reach earlier months.
- Test labels may extend into the next month. In December, drop origins whose required labels extend beyond the dataset.
- Duration fitting and selection use boundary-censored observations; test duration outcomes may extend beyond the test month.

The v1.0-rc design specifies an end-of-training purge, not an additional removal of the first test day.

`TestIndexGuard` must reject test access during tuning, selection, threshold estimation and calibration. Boundary assertions must inspect **label times**, not only origin indices.

**4. Features and baseline definitions**

W0 contains label lags \(0,\ldots,48,168\), current run length, time since outage start/end, outage counts over 6/24/168 hours, changes over 24 hours, and outage share over 720 hours. Include hour sine/cosine, day of week, Friday and approved calendar flags. Exclude month, day of year, household load and completed-event information.

W1 adds weather lags \(0,1,3,6,12,24\) and trailing 24-hour means. Local weather is already shifted: localize without shifting again. Label W1 optimistic because realized reanalysis may not be operationally available.

W2 adds explicitly named oracle columns for future weather through the horizon. Keep W2 outside headline operational claims.

Fit preprocessing only on the corresponding fitting rows.

Reference forecasts:

- **Persistence:** \(p_{t,h}=y_t\); the same expression for target (b).
- **Seasonal-naive:** \(p_{t,h}=y_{t+h-24}\); for (b), take the maximum over the corresponding yesterday window.
- **Static climatology:** training-only hour-of-day probability \((n_1+0.5)/(n+1)\), frozen throughout the test month. Target (b) uses training-complete \(z_{t,h}\) grouped by origin hour.
- **Trailing climatology:** for \(k_0=\lceil h/24\rceil\),
  \[
  p_{t,h}=\frac{0.5+\sum_{k=k_0}^{k_0+W-1}y_{t+h-24k}}{1+n_{\mathrm{available}}},
  \qquad W\in\{7,14,28\}.
  \]
  For (b), substitute complete historical \(z_{t-24k,h}\). Select \(W\) on inner-validation and retain all candidate results.
- **Hour-inhomogeneous Markov-1:** estimate 24 transition matrices with the configured 0.5 prior and sparse-count fallback to the homogeneous matrix. Forecast using the ordered product of hourly matrices. A homogeneous matrix power is a special case, not the primary hour-inhomogeneous calculation. Target (b) uses an absorbing-state calculation.
- **Recency Markov:** homogeneous Markov-1 updated at midnight from the preceding \(N\in\{7,14,28\}\) days of available transitions. Select \(N\) on inner-validation.
- **Logistic regression:** direct models per target/horizon, with training-only preprocessing and no class weighting.

Missing persistence/seasonal inputs or missing Markov current state fall back to static climatology. Trailing climatology falls back when fewer than three usable historical daily observations exist.

Logistic belongs to baseline pool \(B\) under v1.0-rc. Select the strongest implemented smoke baseline by inner-validation Brier, but label this pool incomplete. Do not present its winner as the full benchmark \(C_B\).

**5. Tuning, selection and seeds**

Tune logistic at folds 1, 4 and 7; reuse settings for the following two folds. Use 60 Optuna TPE trials, sampler seed 20180101, 10 startup trials and `multivariate=True`; search \(C\) log-uniformly over \([10^{-4},10^2]\) and penalties \(\{l1,l2\}\).

For **every fold**, fit each model on inner-training and save inner-validation predictions before refitting on the full permitted training data. Include untuned baselines and all window candidates. Selection and thresholds must consume these saved predictions exclusively.

Choose \(C_B\), and later \(C_{ML}\), by seed-mean inner-validation Brier. Differences below \(10^{-6}\) use protocol list order.

WP2 reference models have one deterministic evaluation run; repeated identical fits are not independent replications. Reserve model seed 0 for tuning and use evaluation identifier 1 for the deterministic run.

For later stochastic models, start with seeds 1–10 and use
\[
n=\max\left(10,\left\lceil(SD_{10}/0.0005)^2\right\rceil\right),
\]
capped at 30 for trees/boosting and 20 for deep models. Determine the required count from inner-validation losses only. Average **losses**, not probabilities, for inference.

**6. Metrics**

On the common eligible origins, with observed labels \(y_i\) and probabilities \(p_i\):

\[
BS=\frac1n\sum_i(p_i-y_i)^2,\qquad
BSS_{\mathrm{ref}}=1-\frac{\sum_i(p_i-y_i)^2}
{\sum_i(p_i^{\mathrm{ref}}-y_i)^2}.
\]

Report both static-climatology and strongest-baseline skill. Pool numerator and denominator before division; never average monthly BSS values.

\[
LL=-\frac1n\sum_i[y_i\log \tilde p_i+(1-y_i)\log(1-\tilde p_i)],
\]
where \(\tilde p_i=\operatorname{clip}(p_i,10^{-3},1-10^{-3})\). Apply clipping only to log-loss.

ROC-AUC is the fraction of positive–negative pairs correctly ordered, awarding half credit to probability ties. Freeze PR-AUC as non-interpolated average precision,
\[
AP=\sum_j(R_j-R_{j-1})P_j,
\]
subject to lead acceptance of this currently unspecified convention.

Choose the binary threshold by maximum inner-validation MCC and apply it unchanged:

\[
F1=\frac{2TP}{2TP+FP+FN},
\quad
MCC=\frac{TP\,TN-FP\,FN}
{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}.
\]

For ten equal-width probability bins,
\[
ECE=\sum_b\frac{n_b}{n}|\bar y_b-\bar p_b|.
\]
Reliability tables contain bounds, counts, mean predictions and observed frequencies; empty bins remain explicitly empty.

Duration MAE is \(\frac1{n_u}\sum_{\delta_i=1}|R_i-\hat R_i|\). Harrell’s C-index is the concordant fraction of comparable pairs, with half credit for tied predictions; a pair is comparable when the earlier observed duration is an event. Report both metrics over all eligible origins and separately at event starts.

**7. Dependence-aware inference**

For paired models define seed-mean loss differences \(d_t=\ell_{A,t}-\ell_{B,t}\). Use global demeaning and

\[
\hat\gamma_k=T^{-1}\sum_{t=k+1}^{T}(d_t-\bar d)(d_{t-k}-\bar d),
\]
\[
\widehat\Omega=\hat\gamma_0+
2\sum_{k=1}^{L}\left(1-\frac{k}{L+1}\right)\hat\gamma_k,
\]
\[
DM_{\mathrm{HLN}}=
\frac{\bar d}{\sqrt{\widehat\Omega/T}}
\sqrt{\frac{T+1-2h+h(h-1)/T}{T}}.
\]

Use a two-sided \(t_{T-1}\) reference. Set HAC lag to the bootstrap block length, never below \(h-1\):

\[
L=\operatorname{clip}\!\left(
24\left\lceil\frac{\max(PW(d),\operatorname{median}_m PW(d_m))}{24}\right\rceil,
48,168\right).
\]

Use the corrected circular PW estimator specified by the protocol and log each selected length.

Bootstrap paired indices within each test month using circular blocks; truncate each resample to its original monthly length. Jointly resample all comparison losses and reference losses. Use \(B=9999\), seed 20180102; smoke may use \(B=199\). Use percentile intervals for loss differences and relative reduction, and BCa for BSS/ratios.

Only the explicit five Q1 hypotheses receive primary Holm adjustment at familywise \(\alpha=0.05\). Exploratory smoke comparisons receive effect sizes and intervals, **no significance claims or p-values**.

Friedman/Nemenyi outputs are descriptive. Rank within each horizon across nine folds. Compute
\[
CD=\frac{q_{1-\alpha;k,\infty}}{\sqrt2}
\sqrt{\frac{k(k+1)}{6\cdot9}},
\]
using `scipy.stats.studentized_range` and the actual eligible model count.

**8. Hypothesis and falsification criterion**

The scientific hypothesis is that the selected ML/deep/FM composite adds practically meaningful forecasting accuracy beyond the strongest selected baseline.

G1 requires, at at least two horizons including one of \(1,3,6\):

- Q1 Holm significance;
- \(dBS\le-0.005\);
- the 95% interval upper bound below zero;
- relative Brier reduction at least 5%.

Failure yields the predeclared **NO-GO** for added complexity and recommendation of \(C_B\). It does not prove equivalence. An interval excluding the required practical improvement provides stronger evidence against practical benefit than an imprecise nonsignificant result. Repeat the decision under S-gen and report label sensitivity.

WP2 validates the machinery for this decision; its smoke run cannot adjudicate it.

**9. Acceptance checks and validity threats**

Implement tests 1–10, 12, 16–20 and 22; restrict test 13 to logistic and test 14 to persistence, climatology and logistic. Test 4 must separately check frozen static-reference invariance and per-origin baseline causality.

Add hand-calculated metric and DM fixtures, plus a fixed-seed AR(1) bootstrap coverage experiment whose simulation parameters, replication count and binomial coverage tolerance are frozen before execution. Never search seeds until a coverage or null test passes.

Run `python -m pytest -q` in the implementation session and record elapsed time against the ten-minute requirement. A strict expected failure for unresolved hour documentation must remain visible and must not be described as a scientifically cleared gate.

Before implementation freeze, the lead must resolve:

- Workbook evidence for hour-beginning semantics; WP1’s row reconstruction does not independently establish this.
- Static target-(a) climatology’s precise counting/index convention.
- Whether Markov’s “fewer than 10 transitions” means an individual cell or conditioning-state row.
- Threshold candidate set, tie-breaking and degenerate-metric behavior.
- BCa acceleration under dependent observations, degenerate PW/HAC cases and missing-time handling.
- Approved calendar availability; WP2 must not create it inside protected `data/`.

Other limitations are the single-household, single-year scope; prior pilot/EDA exposure; dependent folds; consumption-derived labels; assumed zero observation latency; repeated origins within outage events; seasonal nonstationarity; and conditional-on-fitted-model bootstrap uncertainty.

Write implementation artifacts under the specified `results/S1/` layout, with smoke outputs isolated in `wp2_smoke/`. Generate README numbers from saved outputs. Quarantine random-split results, reject mismatched caches, use Windows-safe execution, and report failures without selective omission.

No files were changed, no results were generated, and no implementation status is asserted by this methodology review.