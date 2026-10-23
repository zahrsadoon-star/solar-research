Protocol for `20261023-s1-bench-step1-significance`. **No files were edited or saved:** this session is read-only and explicitly requests no edits. The task allowlist permits `agent_notes/S1_bench_step1/PLAN.md`, whereas the role prompt names `agent_notes/PLAN.md`.

Read: `PROJECT_CONTEXT.md`, `AGENTS.md`, `DECISIONS.md`, study `PLAN.md`, benchmark README, benchmark and significance scripts, results CSV, and earlier verification notes.

**1. Scope and hypothesis**

Follow the latest decision: outage forecasting only, BG and KR, horizons \(h\in\{1,6\}\) hours, with all existing algorithms, settings, features and splits frozen.

Primary question: does the observed lowest-Brier algorithm outperform the other shortlisted algorithms? Secondary question: do shortlisted algorithms outperform “Same hour last 7 days”?

For each comparison:
\[
H_0:E[d_t]=0,\qquad H_1:E[d_t]\ne0,
\quad d_t=(p_{A,t}-y_t)^2-(p_{B,t}-y_t)^2.
\]
Negative differences favor A.

This is **exploratory inference after observing rankings**, conditional on the fitted forecasts. It is not a newly preregistered confirmatory experiment.

**2. Target, information availability and splits**

Use the existing target:
\[
y_{t,h}=\mathbf1\{\mathrm{grid\_kwh}_{t+h}=0\}.
\]

This is a metering proxy for grid unavailability, not independently verified outage status. Predict the state at \(t+h\), not “any outage before \(t+h\).”

Retain the existing hourly local-time index, missing-row exclusions and all 19 features. Features may use completed observations through origin \(t\); this assumes origin-hour metering is available when issuing the forecast. Fit preprocessing only on each training set.

For test-month start \(a_m\), April through December:
\[
\mathrm{Train}_{m,h}=\{t:t<a_m,\ t+h<a_m\},
\]
\[
\mathrm{Test}_{m,h}=\{t:\operatorname{month}(t)=m\}.
\]

Intersect both with existing eligible rows. Refit monthly; update histories causally within the month without refitting parameters. Test membership follows **origin month**; targets may enter the following month. Exclude targets beyond the available year.

Pool chronological test predictions within each site–horizon case. Random-split predictions are excluded from significance analysis.

**3. Prediction export and preservation gate**

Export the predictions already produced by `benchmark.py`; do not refit inside `significance.py`.

Required columns:

`site, h, origin_time, target_time, month, y`, plus all 12 algorithm and three reference probability columns.

Preserve full numerical precision and the benchmark’s existing probability clipping. Assert:

- Unique `(site, h, origin_time)` keys and chronological ordering.
- `target_time = origin_time + h hours`.
- `month` equals origin month.
- Binary labels and finite probabilities in \([0,1]\).
- Identical rows for all comparisons.
- Consecutive hourly origins within each case; fail on unexplained gaps.

Before rerunning, preserve the original results artifact. Compare keyed rows, ignoring row order. Require unchanged published predictive metrics and ranks at the existing serialization precision. Report maximum differences; stop on substantive changes rather than widening tolerances or changing models.

**Specification conflict:** `fit_seconds` measures runtime and will naturally change. Treat timing separately from predictive invariance and report it explicitly. Literal whole-file numerical invariance cannot be promised. Previous verification tolerances are not appropriate for this stricter preservation gate.

**4. Frozen shortlist and references**

Freeze the following order from the existing results and `rank_by_brier`; stored ranks resolve ties introduced by four-decimal Brier rounding.

| Case | Top six, in rank order |
|---|---|
| BG, 1 h | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost; Gradient Boosting |
| BG, 6 h | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting; CatBoost; XGBoost |
| KR, 1 h | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM; Gradient Boosting |
| KR, 6 h | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting |

The three exported references are:
\[
p^{(0)}_{t,h}=0,\qquad p^{(\mathrm{persist})}_{t,h}=O_t,
\qquad p^{(\mathrm{seasonal})}_{t,h}
=\frac17\sum_{k=1}^{7}O_{t+h-24k}.
\]

Test all 15 unordered shortlist pairs plus six shortlist-versus-seasonal-reference pairs: **21 comparisons per case**. Use rank order for A/B orientation; for reference comparisons, A is the algorithm.

**Input conflict resolution:** freeze these CSV-derived shortlists as configuration in `significance.py`, so its only runtime data input is `predictions.csv.gz`. Validate shortlist provenance during the preservation check. Do not dynamically select a different shortlist from rerun results.

**5. Metrics and paired moving-block bootstrap**

Primary metric:
\[
\mathrm{Brier}_A=\frac1N\sum_t(p_{A,t}-y_t)^2,\qquad
\Delta_{\mathrm{Brier}}=\bar d.
\]

Secondary metric:
\[
\mathrm{AUC}_A=
\frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
[\mathbf1(p_{A,i}>p_{A,j})+\tfrac12\mathbf1(p_{A,i}=p_{A,j})]}
{N_+N_-},
\]
\[
\Delta_{\mathrm{AUC}}=\mathrm{AUC}_A-\mathrm{AUC}_B.
\]
Positive AUC differences favor A. Compute pooled metrics, not averages of monthly metrics.

For each case:

- Initialize `numpy.random.default_rng(42)`.
- Draw 2,000 resamples using overlapping, noncircular blocks of 24 consecutive hours.
- Sample block starts uniformly from \(0,\ldots,N-24\), with replacement.
- Concatenate \(\lceil N/24\rceil\) blocks and truncate to \(N\) rows.
- Reuse the exact same row indices for labels, every algorithm, both metrics and every pair.
- Compute percentile intervals at 2.5% and 97.5%, using linear quantile interpolation.

Blocks may cross adjacent monthly fold boundaries because the target analysis pools continuous test hours. Never bridge a genuine timestamp gap.

If a bootstrap sample contains only one class, its AUC is undefined. Do not redraw it or substitute a numerical AUC. Record the valid count; conservatively mark the AUC interval unavailable if any required replicate is undefined. Brier analysis remains valid.

These are marginal intervals, not simultaneous confidence intervals.

**6. Diebold–Mariano test**

Let \(z_t=d_t-\bar d\). Use:
\[
\hat\gamma_k=\frac1N\sum_{t=k+1}^{N}z_tz_{t-k},
\]
\[
\hat\Omega=\hat\gamma_0+
2\sum_{k=1}^{L}\left(1-\frac{k}{L+1}\right)\hat\gamma_k,
\qquad L=h-1+24.
\]

Thus the fixed HAC lags are 24 and 29 hourly steps. The choice adds daily dependence to the horizon-related lag allowance; it is not selected using significance results.

Apply the Harvey–Leybourne–Newbold correction:
\[
DM_{\mathrm{HLN}}=
\frac{\bar d}{\sqrt{\hat\Omega/N}}
\sqrt{\frac{N+1-2h+h(h-1)/N}{N}},
\]
\[
p=2\,\Pr(T_{N-1}\ge|DM_{\mathrm{HLN}}|).
\]

Use forecast horizon \(h\), not HAC lag \(L\), in the correction.

Edge conventions:

- Identically zero differences: statistic \(0\), \(p=1\).
- Exactly constant nonzero differences: signed infinite statistic and limiting \(p=0\), explicitly flagged as degenerate.
- Other nonpositive or nonfinite variance estimates: report an invalid test; do not silently repair them or declare significance.
- Reject insufficient sample lengths.

**7. Multiplicity and top-group definition**

Apply Holm correction to all 21 Brier-test p-values within each case. For sorted p-values:
\[
p^{\mathrm{adj}}_{(i)}
=\min\left(1,\max_{j\le i}\{(M-j+1)p_{(j)}\}\right),
\qquad M=21.
\]

Do not reduce the correction family to comparisons against the best. No cross-case correction is specified, so avoid study-wide familywise claims.

Include the descriptive best in its top group. Include another shortlisted algorithm when its comparison against the best has:

- Holm-adjusted \(p\ge0.05\), **or**
- A Brier-difference interval containing zero, including endpoints.

Declare an algorithm worse only when both criteria support the best in the correct direction. Invalid tests remain “unresolved.”

“Not distinguished from the best” does **not** establish equivalence. Top-group membership is not transitive and does not imply that every member is indistinguishable from every other member. AUC is descriptive and does not redefine this group.

**8. Seeds, falsification and validity limits**

Keep benchmark seed 42 and bootstrap seed 42. Bootstrap replicates are not independent model-training runs. Earlier seed-sensitivity evidence does not establish robustness for all algorithms; the broader multiple-run requirement remains unresolved within this frozen task.

A unique-winner claim is unsupported if any shortlisted competitor remains in the top group. A significant difference in the opposite direction contradicts the claimed superiority. Failure to beat the seasonal reference leaves added predictive value unsupported. Neither nonsignificance nor a zero-covering interval proves equality.

Leakage, misalignment or substantive benchmark drift invalidates this analysis regardless of favorable p-values.

Principal threats are test-set shortlist selection, prior visibility of significance results, seasonal nonstationarity, dependence longer than the fixed block/HAC windows, shared expanding training histories, single-seed training uncertainty, proxy-label error, assumed timestamps and metering availability, class imbalance, and only one year per household. Separately trained household models do not demonstrate geographic transfer. HLN correction does not remove these limitations.

**9. Implementation acceptance and reporting**

Required tests:

- Identical forecasts produce \(DM=0,\ p=1\).
- A clearly better synthetic forecast with nonzero loss variance produces the expected sign and small p-value.
- A hand-calculated nondegenerate example verifies HAC weights, HLN correction and Student-t p-value.
- Fixed-seed bootstrap intervals repeat exactly and use paired contiguous blocks.
- Holm example: raw `[0.01, 0.04, 0.03]` maps to `[0.03, 0.06, 0.06]`.
- Export alignment, comparison completeness and invalid-input handling.

During implementation, run `python -m pytest -q` without network access or installation.

Produce `results/significance_pairs.csv` with effect estimates, intervals, test statistics, raw/adjusted p-values, sample counts and validity flags; generate `results/significance_summary.md` and the README section from those outputs. Replace the existing significance conclusions: they used a different protocol and cannot be carried forward.

No benchmark rerun, tests, new significance results or top-group conclusions were produced in this read-only methodology turn.