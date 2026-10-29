ما حفظت ملفات لأن الجلسة read-only وتعليماتك تمنع التعديل. أدناه نص البروتوكول المقترح لـ `agent_notes/PLAN.md`. ما قرأت `significance.py`، وما نفّذت merge أو إعادة تدريب.

**Protocol: independent check of S1 significance**

1. **Scope and precedence**

The 29 October task specification supersedes the earlier preservation gate and broader study plan. Analyze BG and KR at horizons \(h\in\{1,6\}\) hours, conditional on the saved original-run forecasts. No refitting, tuning, alternative seeds selected for favorable results, dispatch analysis, or changes to primary benchmark artifacts.

Treat Windows/Linux drift as cross-platform numerical variability under the lead’s decision. This is an accepted interpretation, not an experimentally isolated cause.

Before implementation, merge local `origin/main` without network access. Preserve main’s specified benchmark files and results; archive/remove branch rerun artifacts exactly as authorized. Implement the check independently without reading or importing main’s `significance.py`.

2. **Input and alignment**

The sole prediction input is:

`studies/S1_outage_forecasting/benchmark/results/hourly_predictions_top6.csv.gz`

I inspected its `origin/main` version. Columns are:

`site, h, time, y, Extra Trees, Random Forest, CatBoost, LightGBM, XGBoost, Gradient Boosting, Logistic Regression, k-Nearest Neighbours`.

Each case has six populated algorithm columns; other algorithm columns are entirely missing for that case. **There is no reference column.** Consequently, perform 15 unordered algorithm comparisons per case and skip reference comparisons explicitly. Do not reconstruct baselines or obtain their predictions elsewhere.

Validate unique `(site,h,time)` keys, binary labels, finite probabilities in \([0,1]\), six complete algorithm columns per case, and consecutive hourly timestamps. Reject partially missing algorithm columns; never perform pair-specific row deletion. Record input hash, revision, software versions, row counts, and time ranges.

Treat `time` as forecast-origin time under the benchmark convention; derive target time as `time + h hours`. The export alone cannot independently establish training provenance or absence of feature leakage.

3. **Target and temporal evaluation**

The frozen target is:

\[
y_{t,h}=\mathbf1\{\mathrm{grid\_kwh}_{t+h}=0\}.
\]

This is a metering proxy for grid unavailability, predicting the state at \(t+h\), not whether any outage occurs during the intervening interval.

Preserve the existing expanding-window monthly evaluation, April–December 2018. For test-month start \(a_m\):

\[
\mathrm{Train}_{m,h}=\{t:t<a_m,\ t+h<a_m\},
\qquad
\mathrm{Test}_{m,h}=\{t:\operatorname{month}(t)=m\},
\]

intersected with eligible feature/target rows. Training labels must be available before the test month. Test membership follows origin month; targets may cross month boundaries. Exclude targets beyond the observed year.

Features assume completed origin-hour metering is available. Preprocessing is fitted on training data only. Pool chronological out-of-sample forecasts; exclude random-split results.

4. **Shortlists and baselines**

Rank each case’s six populated algorithms by pooled Brier score computed from the supplied probabilities; break exact ties alphabetically. The inspected rankings are:

| Case | Algorithms in Brier order |
|---|---|
| BG, 1 h | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost; Gradient Boosting |
| BG, 6 h | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting; CatBoost; XGBoost |
| KR, 1 h | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM; Gradient Boosting |
| KR, 6 h | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting |

These are inherited test-selected shortlists, not independently selected validation sets. The wider benchmark contains persistence, always-no-outage, and seasonal references, but this artifact cannot support their independent significance checks.

5. **Metrics and hypotheses**

For algorithms \(A,B\), orient each unordered pair by the ranking above:

\[
BS_A=\frac1N\sum_t(p_{A,t}-y_t)^2,\qquad
d_t=(p_{A,t}-y_t)^2-(p_{B,t}-y_t)^2,
\qquad \Delta_{BS}=\bar d.
\]

Negative \(\Delta_{BS}\) favors \(A\). Test:

\[
H_0:E[d_t]=0,\qquad H_1:E[d_t]\ne0.
\]

Secondary discrimination metric:

\[
AUC_A=
\frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
[\mathbf1(p_{A,i}>p_{A,j})+\tfrac12\mathbf1(p_{A,i}=p_{A,j})]}
{N_+N_-},
\qquad
\Delta_{AUC}=AUC_A-AUC_B.
\]

Positive \(\Delta_{AUC}\) favors \(A\). Compute pooled metrics, not averages of monthly metrics. These metrics and differences are dimensionless.

6. **Paired moving-block bootstrap**

For each case, initialize `numpy.random.default_rng(42)` and generate 2,000 resamples:

- Use overlapping, noncircular blocks of 24 consecutive hourly rows.
- Sample starts uniformly with replacement from \(0,\ldots,N-24\).
- Concatenate \(\lceil N/24\rceil\) blocks and truncate to \(N\).
- Reuse identical sampled indices for labels, all algorithms, all pairs, and both metrics.
- Calculate marginal percentile 95% intervals using the 0.025 and 0.975 quantiles with linear interpolation.

Blocks may cross contiguous monthly boundaries, but must never bridge missing hours. Reject unexplained timestamp gaps rather than silently compressing time.

A single-class replicate has undefined AUC. Do not redraw or substitute a value. Record valid replicate counts; conservatively mark its AUC interval unavailable if any replicate is undefined. Brier calculations remain available.

7. **Diebold–Mariano test**

Let \(z_t=d_t-\bar d\). Use Newey–West Bartlett weights:

\[
\hat\gamma_k=\frac1N\sum_{t=k+1}^{N}z_tz_{t-k},
\]

\[
\hat\Omega=\hat\gamma_0+
2\sum_{k=1}^{L}\left(1-\frac{k}{L+1}\right)\hat\gamma_k,
\qquad L=h-1+24.
\]

Thus \(L=24\) for 1-hour forecasts and \(L=29\) for 6-hour forecasts.

Apply the Harvey–Leybourne–Newbold correction:

\[
DM_{\mathrm{HLN}}=
\frac{\bar d}{\sqrt{\hat\Omega/N}}
\sqrt{\frac{N+1-2h+h(h-1)/N}{N}},
\]

\[
p=2\,\Pr(T_{N-1}\ge |DM_{\mathrm{HLN}}|).
\]

Use forecast horizon \(h\), not HAC lag, in the correction.

Identically zero loss differences return mean difference zero, statistic zero, and \(p=1\). For other zero, negative, or nonfinite variance cases, return an explicit invalid/degenerate status and unavailable inferential result; do not silently manufacture significance. Require sufficient sample length for the specified lag.

8. **Multiplicity and top groups**

Apply Holm correction over all \(M=15\) Brier tests within each case:

\[
p^{adj}_{(i)}
=\min\left(1,\max_{j\le i}\{(M-j+1)p_{(j)}\}\right).
\]

Preserve the full family when a test is invalid: use 1 conservatively for adjustment while retaining its invalid status. No correction across cases is claimed.

The descriptive best belongs to the top group. Exclude a competitor only when the best-minus-competitor Brier difference has both:

- Holm-adjusted \(p<0.05\);
- bootstrap upper bound strictly below zero.

Otherwise retain it as “not distinguished from the best”; identify invalid comparisons separately as unresolved. AUC does not determine membership.

**Non-rejection is not equivalence.** These are exploratory within-case results; the group is not a claim of pairwise equivalence among all members.

9. **Comparison with main**

Read main’s `significance.csv` and README only for comparison after calculating the independent results. Main’s reported groups, including the best, are:

| Case | Main’s top group |
|---|---|
| BG, 1 h | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost |
| BG, 6 h | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting |
| KR, 1 h | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM |
| KR, 6 h | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting |

Generate `COMPARISON.md` with both sets, exact membership agreement/disagreement, and unresolved statuses per case.

Explain differences using the specified methodological contrasts: 24-hour versus 168-hour bootstrap blocks, horizon-dependent versus fixed HAC lag, HLN versus no HLN, and Holm over 15 versus five comparisons. Main reports accuracy intervals rather than the requested AUC intervals. Normalize difference signs before comparing estimates.

Do not claim that any single method change caused a disagreement without isolating it. Saved probability rounding can also produce small numerical differences from calculations using unrounded predictions.

10. **Seeds, falsification, and validity**

Preserve benchmark seed 42; bootstrap seed is 42. Bootstrap replicates are not independent training runs. This check cannot satisfy the broader study’s multiple-training-seed requirement.

A unique-winner claim is unsupported whenever another algorithm remains in the top group. A reliable effect in the opposite direction contradicts a claimed directional advantage. Failure to reject does not falsify equality or prove equivalence. Claims of improvement over a reference cannot be evaluated because reference predictions are absent.

Threats include test-selected shortlists, prior exposure to significance results, temporal nonstationarity, dependence beyond 24 hours, shared expanding training sets, monthly model changes, single-seed training, rounded probabilities, proxy-label error, metering latency, class imbalance, and one year per household. Separate site-specific training is not evidence of geographic transfer. HLN is an approximate correction and does not eliminate these limitations.

11. **Deliverables and acceptance**

The implementation must produce:

- `significance_check/check.py`: independent analysis.
- `significance_check/pairs.csv`: 60 pair rows with effects, intervals, DM statistics, raw/adjusted p-values, sample counts, and validity flags.
- `significance_check/COMPARISON.md`: per-case group comparison and limitations.
- `tests/test_s1_sig_check.py`: identical-forecast handling, clearly better nondegenerate forecasts, repeatable bootstrap, and hand-computed Holm correction.
- `agent_notes/S1_bench_step1/REPRO_NOTE.md`: archived Linux/Windows metric differences, affected algorithms, maximum absolute difference per metric, and maximum rank change.

For Holm, raw `[0.01, 0.04, 0.03]` must yield `[0.03, 0.06, 0.06]`. Also verify HAC/HLN arithmetic, paired contiguous resampling, and comparison completeness.

Reproduction-note values must come from archived keyed comparisons, excluding timing from predictive drift. Do not rerun models or adjust settings to recover agreement. No methodological citations were verified in this offline turn.

**Execution status:** no edits, merge, model fitting, or significance results were produced. Attempted `python -m pytest -q -p no:cacheprovider` with bytecode disabled; pytest failed before collection because no writable temporary directory was available. A passing suite remains required during implementation.