**Protocol for `agent_notes/PLAN.md` — fix5 S1 significance check**

Read-only review completed. No files were edited or saved; no merge, model run, pytest run, or lint run was performed. The reported “5 failed, 65 passed, 1 skipped” remains task-supplied evidence, not a result reproduced here.

1. **Scope and preservation**

   Follow the narrowed forecasting-only decision and the existing independent-check protocol. Analyze BG and KR at horizons \(h\in\{1,6\}\) hours using frozen original-run forecasts. No refitting, tuning, dispatch analysis, new target definitions, or result-driven changes to statistical settings.

   During implementation, merge local `main` without network access. Record its exact revision and preserve every pre-existing main file under `studies/S1_outage_forecasting/benchmark/results/` byte-for-byte. Compare historical conclusions specifically with `cec3552`; distinguish that revision from current main.

   Store new numerical outputs under `benchmark/results/significance_check/`, as required by this task. Do not overwrite published results.

2. **Input, targets, and leakage controls**

   Use only `benchmark/results/hourly_predictions_top6.csv.gz` for significance calculations. Record its SHA-256, source revision, software versions, case sizes, and timestamp ranges.

   Validate unique `(site,h,time)` keys, consecutive hourly origins, binary labels, finite probabilities in \([0,1]\), and exactly six complete algorithm columns per case. Entirely missing columns indicate algorithms outside that case’s shortlist. Reject partially missing columns; do not delete rows separately by pair.

   The target is:
   \[
   y_{t,h}=\mathbf1\{\mathrm{grid\_kwh}_{t+h}=0\}.
   \]
   This is a metering proxy for grid unavailability at a future hour.

   Preserve April–December 2018 expanding-window monthly evaluation. For test-month start \(a_m\):
   \[
   \mathrm{Train}_{m,h}=\{t:t<a_m,\ t+h<a_m\},
   \qquad
   \mathrm{Test}_{m,h}=\{t:\operatorname{month}(t)=m\},
   \]
   intersected with rows having eligible features and observed targets. Exclude targets beyond the observation period.

   Features may use completed-origin-hour observations and known calendar information. Fit preprocessing on training rows only. Verify future-observation perturbation invariance, target alignment, and training-label boundaries. Random-split results are excluded from inference. The prediction export alone cannot establish training provenance.

3. **Comparators and baselines**

   Analyze all unordered pairs among each case’s six saved algorithms. Rank by pooled Brier score, breaking exact ties alphabetically: 15 comparisons per case, 60 overall.

   The benchmark’s reference forecasts are:
   \[
   p_{\mathrm{no\ outage}}=0,\quad
   p_{\mathrm{persistence}}=y_t,\quad
   p_{\mathrm{seasonal}}=\frac17\sum_{k=1}^{7}y_{t+h-24k}.
   \]
   Their probabilities are absent from the frozen shortlist export. Explicitly report reference significance comparisons as unavailable; do not reconstruct them or claim superiority over them.

4. **Metrics**

   Primary metric and paired effect:
   \[
   BS_A=\frac1N\sum_t(p_{A,t}-y_t)^2,\qquad
   d_t=(p_{A,t}-y_t)^2-(p_{B,t}-y_t)^2,\qquad
   \Delta_{BS}=\bar d.
   \]
   Negative differences favor \(A\).

   Secondary metric:
   \[
   AUC_A=
   \frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
   [\mathbf1(p_{A,i}>p_{A,j})+\tfrac12\mathbf1(p_{A,i}=p_{A,j})]}
   {N_+N_-},
   \qquad \Delta_{AUC}=AUC_A-AUC_B.
   \]
   Positive AUC differences favor \(A\). All metrics are dimensionless. Pool hourly out-of-sample predictions; do not average monthly scores.

5. **Seeds and bootstrap intervals**

   Preserve training seed 42. Reset `numpy.random.default_rng(42)` separately for each case.

   Generate 2,000 paired moving-block bootstrap replicates using overlapping, noncircular blocks of 24 consecutive hours. Sample starts uniformly from \(0,\ldots,N-24\), concatenate \(\lceil N/24\rceil\) blocks, and truncate to \(N\). Reuse identical indices for labels, all algorithms, and both metrics.

   Report marginal 95% percentile intervals using linear-interpolated quantiles at 0.025 and 0.975. Never bridge missing hours. Record single-class AUC replicate counts; if any replicate is undefined, mark its AUC interval unavailable without redrawing.

   Bootstrap replicates are not independent training runs. This frozen single-seed check does not fulfill the broader study’s multiple-training-run requirement.

6. **Significance tests and multiplicity**

   Test two-sided \(H_0:E[d_t]=0\). With \(z_t=d_t-\bar d\):
   \[
   \hat\gamma_k=N^{-1}\sum_{t=k+1}^{N}z_tz_{t-k},
   \]
   \[
   \hat\Omega=\hat\gamma_0+
   2\sum_{k=1}^{L}\left(1-\frac{k}{L+1}\right)\hat\gamma_k,
   \qquad L=h-1+24.
   \]
   Apply the horizon-based Harvey–Leybourne–Newbold correction:
   \[
   DM=\frac{\bar d}{\sqrt{\hat\Omega/N}}
   \sqrt{\frac{N+1-2h+h(h-1)/N}{N}},
   \qquad p=2\Pr(T_{N-1}\ge|DM|).
   \]

   Identically zero differences return statistic zero and \(p=1\). Other degenerate or nonfinite variance cases receive explicit invalid status and unavailable inference.

   Apply Holm adjustment over all 15 Brier comparisons within each case:
   \[
   p^{adj}_{(i)}=
   \min\left(1,\max_{j\le i}(15-j+1)p_{(j)}\right).
   \]
   Retain invalid tests in the family using 1 for adjustment while preserving their invalid status. No across-case error control is claimed.

   These formulas follow the existing repository protocol and correspond to `check.py` functions `analyze`, `auc`, `bootstrap`, `dm_test`, and `holm`. External methodological citations remain **[UNVERIFIED]** in this offline review.

7. **Top groups and falsification**

   Include the lowest-Brier algorithm in the top group. Exclude a competitor only when its best-minus-competitor comparison has both Holm-adjusted \(p<0.05\) and a Brier interval upper bound strictly below zero. Flag invalid comparisons as unresolved.

   “Top group” means not distinguished from the descriptive best under this rule. It does not establish equivalence or pairwise equality.

   The operational claim that RF and Extra Trees remain indistinguishable is contradicted in a case if their comparison satisfies both exclusion criteria. Exact reproduction of main’s group membership fails if any member changes. A unique-winner claim is unsupported whenever another algorithm remains in the group. Failure to reject equality cannot prove equivalence; no equivalence margin was specified.

8. **Comparison with `cec3552`**

   Generate one honest line per case containing both groups, agreement or difference, and the relevant comparison evidence.

   Existing `COMPARISON.md` reports the following historical outcomes; these must be regenerated before acceptance:

   | Case | Existing comparison |
   |---|---|
   | BG, 1 h | Differ: independent check retains Gradient Boosting; main excludes it. |
   | BG, 6 h | Agree: Extra Trees, RF, Logistic Regression, Gradient Boosting. |
   | KR, 1 h | Agree: RF, CatBoost, Extra Trees, XGBoost, LightGBM. |
   | KR, 6 h | Agree: all six shortlisted algorithms. |

   Explain methodological differences: 24-hour versus 168-hour bootstrap blocks, horizon-dependent versus fixed HAC lag, HLN correction versus none, and Holm over 15 versus five comparisons. Normalize effect signs. Do not attribute a membership change to one methodological choice without isolating it.

9. **Failure diagnosis and acceptance**

   In a writable implementation session, capture the requested baseline run:
   ```powershell
   python -m pytest -q --basetemp=D:\SolarProject\tmp\pytest\fix2sig
   ```
   Record each failing node ID, exact exception/assertion, relevant paths, and evidenced cause in `agent_notes/S1_bench_step1_fix2/FAILURES.md`.

   Source inspection identifies two hazards requiring controlled execution: tests reference moved prediction artifacts, and `test_historical_significance_is_disabled` invokes the restored significance entry point. The latter may refit models and overwrite protected results. Reproduce against an isolated disposable repository copy with writes confined there; preserve a truthful baseline failure record.

   Fix obsolete contracts while retaining meaningful coverage. Do not delete or skip tests. Widen a tolerance only for the task-authorized Windows/Linux drift, supported by the exact affected comparison and observed difference in its test docstring. The historical maximum Brier difference of 0.0013 is not a blanket tolerance for unrelated failures.

   Verify paired resampling, hand-calculated HAC/HLN and Holm arithmetic, identical forecasts, degenerate variance, missingness rejection, reproducibility, leakage controls, and complete comparison output. Finish with the full pytest suite, `ruff check`, protected-file hash verification, and `CODEX_REPORT.md`. Do not commit or push.

10. **Threats to validity**

   Test-selected shortlists and prior exposure make this exploratory, not a newly blinded confirmatory analysis. Other limitations include dependence beyond 24 hours, seasonal nonstationarity, shared expanding training sets, monthly model changes, one training seed, rounded probabilities, proxy-label error, uncertain metering latency, class imbalance, unequal tuning budgets, and one year per household. Separate site-specific models do not demonstrate geographic transfer. Platform drift has an accepted lead interpretation but was not causally isolated.