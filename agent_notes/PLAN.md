Protocol for `20261023-s1-bench-verify`. No files were edited; this protocol could not be saved because the session is read-only. The task-specific permitted notes location is `agent_notes/S1_bench_verify/PLAN.md`, whereas the role prompt requests `agent_notes/PLAN.md`.

Read: `PROJECT_CONTEXT.md`, `AGENTS.md`, `DECISIONS.md`, the study `PLAN.md`, benchmark `README.md`, and relevant earlier methodology notes. **`benchmark.py` and its results CSV remain unopened.** README results were necessarily visible; independence therefore means independent implementation, not blinding to all reported results.

**Scope and hypothesis**

Verify only BG and KR, horizons \(h\in\{1,6\}\) hours, and five methods: always no outage, persistence, same-hour history, logistic regression, and random forest. The latest decision supersedes dispatch, duration forecasting, additional horizons, tuning, and model-ranking inference.

The verification hypothesis is that an independently implemented, causal pipeline reproduces the specified benchmark metrics within the predefined tolerances. Numerical reproduction and absence of leakage are separate findings: matching a defective implementation would not establish validity.

**1. Independence and data audit**

Before reading benchmark code or result CSV:

- Implement the loader, features, references, models, splits, metrics, and tests independently.
- Run them and freeze their source hashes, configuration, and outputs.
- Record Python/package versions, input hashes, elapsed runtime, seeds, and thread settings.
- Do not import benchmark helpers or reuse its preprocessing.

Load:

| Site | Input | Selection |
|---|---|---|
| BG | `data/raw/BG18760_with_analysis.xlsx` | Sheet `Hourly Data`; `Grid (kWh)` and `Generator (kWh)` |
| KR | `data/raw/KR-8760.xlsx` | No header; first 8,760 rows; columns 0 and 1 |

Assign an hourly local-time index starting `2018-01-01 00:00`, without sorting observations or introducing a timezone conversion.

For grid energy \(G_t\) and generator energy \(D_t\), in kWh:

\[
O_t=\mathbf1(G_t=0),\qquad L_t=G_t+D_t.
\]

Missing grid measurements must produce missing outage labels, not silently become non-outages. Do not round small positive grid values to zero, impute, clip negatives, or repair observations silently.

Export selected row counts, missing/non-numeric counts, negative-value counts, and annual/monthly outage shares. For each period \(A\):

\[
q_A=\frac{\sum_{t\in A,\;G_t\text{ observed}}O_t}
{\#\{t\in A:G_t\text{ observed}\}}.
\]

Report each denominator and missing count. Unexpected row counts or invalid measurements must be investigated before declaring reproduction.

**2. Target and information availability**

The target is \(Y_{t,h}=O_{t+h}\), not “any outage during the next \(h\) hours.”

Forecasts use completed observations through row \(t\). If timestamps denote interval starts, the forecast is issued after that interval completes; the report must state this availability convention. Calendar values for the future target hour are known in advance.

Freeze the following 18 features:

| Features | Exact definition |
|---|---|
| Current outage | \(O_t\) |
| Eight lagged outages | \(O_{t-k}\), \(k\in\{1,2,3,6,12,24,48,168\}\) |
| Three rolling outage means | \(w^{-1}\sum_{j=0}^{w-1}O_{t-j}\), \(w\in\{6,24,168\}\) |
| Current-state duration | Consecutive observed rows ending at \(t\) with state \(O_t\), including \(t\); first row of a run equals 1 hour |
| Two target-hour features | \(\sin(2\pi c/24)\), \(\cos(2\pi c/24)\), \(c=\operatorname{hour}(t+h)\) |
| Origin weekday | Monday = 0 through Sunday = 6 |
| Same-hour history | \(S_{t,h}=7^{-1}\sum_{d=1}^{7}O_{t+h-24d}\) |
| Lagged load | \(L_{t-1}\) |
| Rolling load | \(24^{-1}\sum_{j=0}^{23}L_{t-j}\) |

Require complete rolling windows and seven observed same-hour values. For the specified horizons, every same-hour reference index is at or before \(t\).

Compute features on the continuous chronology; do not reset state duration or histories at month boundaries. Drop rows with any missing feature **or target**, preserving exclusion counts. Use the same retained rows for all five methods.

**3. Methods and temporal splits**

Reference probabilities are:

\[
p^{(0)}_{t,h}=0,\qquad
p^{(\mathrm{persist})}_{t,h}=O_t,\qquad
p^{(\mathrm{hour})}_{t,h}=S_{t,h}.
\]

Logistic regression: `StandardScaler` followed by `LogisticRegression(max_iter=3000)`, otherwise scikit-learn 1.7 defaults. Fit the scaler exclusively on each training fold.

Random forest: `RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=42)`, otherwise defaults. Fix execution to one thread for reproducibility. Use positive-class probabilities for both models. No tuning, calibration, reweighting, or threshold selection.

For each site, horizon, and test month \(m=4,\ldots,12\), let \(a_m\) be the month start and \(a_{m+1}\) the next month start:

\[
\mathrm{Train}_{m,h}=\{t:t<a_m\ \land\ t+h<a_m\},
\]
\[
\mathrm{Test}_{m,h}=\{t:a_m\le t<a_{m+1}\}.
\]

Intersect both sets with eligible rows. Refit models monthly. Test-month observations through the current origin may update causal features, but cannot update fitted parameters during that month.

Test targets may fall in the next month; this follows the requested **origin-month** assignment. Exclude targets beyond the available year. Save origin time, target time, fold, truth, and probabilities so split assertions are independently inspectable.

**4. Metrics**

Pool predictions over all nine test folds within each site–horizon–method case. Do not average monthly metrics.

With \(\hat y_i=\mathbf1(p_i\ge0.5)\):

\[
\mathrm{Accuracy}=\frac1N\sum_i\mathbf1(\hat y_i=y_i),
\]

\[
F_1=\frac{2TP}{2TP+FP+FN},
\qquad
\mathrm{Brier}=\frac1N\sum_i(p_i-y_i)^2.
\]

Set F1 to zero when its denominator is zero and record that convention.

\[
\mathrm{AUC}
=\frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
[\mathbf1(p_i>p_j)+\tfrac12\mathbf1(p_i=p_j)]}{N_+N_-}.
\]

AUC is undefined for a single-class evaluation sample; report it as such rather than assigning a numerical score.

**5. Comparison and falsification**

Only after independent outputs are frozen, open `benchmark_results.csv`. Match the time-ordered rows explicitly by site, horizon, and method.

Create a long-form comparison table containing metric, ours, theirs, absolute difference, tolerance rule, and pass/fail:

- References: equal after rounding to four decimal places.
- Logistic regression: absolute difference \(\le0.002\).
- Random forest: absolute difference \(\le0.005\).

Retain unrounded independent metrics. Record published precision; do not silently widen tolerances.

A missing required result or any out-of-tolerance metric falsifies **full numerical reproduction**. Any feature using observations after \(t\), training target entering the test month, or preprocessing fitted using held-out observations falsifies the causal-validity claim.

Verdicts:

- **REPRODUCED:** all required comparisons pass.
- **PARTLY:** some required comparisons pass and others fail or are unavailable.
- **NOT REPRODUCED:** none pass, or a fundamental failure prevents a comparable evaluation.

Report leakage status separately, prominently, even when all numbers match. Preserve initial outputs when investigating mismatches; never tune the verifier to obtain agreement.

**6. Leakage and random-split audit**

After comparison, read `benchmark.py`. Enumerate relevant source lines for loading, shifts, rolling windows, state duration, target-calendar construction, historical means, load features, target creation, missing-row filtering, scaling, fitting, and split masks. Give each a verdict: causal, leaking, or unresolved, with its latest information timestamp.

For the random 80/20 comparison, document the actual eligible population, split unit, fraction, seed, shuffling, stratification, preprocessing scope, model settings, and scoring. The README does not fully specify these details, so distinguish consistency with its stated description from unresolved choices.

Randomly interleaving hours allows later observations into training relative to some test origins. Treat its scores as a descriptive comparison, not prospective forecasting evidence or proof that the entire score difference is caused by leakage.

**7. Seeds, statistical tests, and checks**

This task uses numerical tolerance checks, **not a statistical significance test**. No p-values, confidence intervals, or model-superiority claims are warranted from reproduction alone.

The specified RF seed is 42; default logistic regression is deterministic here. Repeating the same seed checks repeatability, not independent-run uncertainty. The broader multi-run requirement remains unmet by this deliberately single-seed verification; do not claim otherwise or substitute seed averages for the requested comparison.

Required fast checks:

- Both loaders return 8,760 rows and valid binary observed labels.
- A synthetic same-hour history with values \([1,0,1,0,1,0,1]\) returns \(4/7\), independently of values after the origin.
- Training target timestamps precede each test-month boundary.
- Altering future observations leaves earlier features unchanged.

Run `python -m pytest -q` during implementation and record the outcome. The requested `tests/test_s1_bench_verify.py` conflicts with the explicit write allowlist; this needs resolution before implementation writes that file. Root `CODEX_REPORT.md` has the same scope conflict.

**Threats to validity and deliverables**

Main limitations are proxy-label misclassification, uncertain metering availability, assigned timestamps, one year per household, temporal dependence, seasonal change, class imbalance, single-seed variability, unspecified estimator defaults, and prior visibility of README outcomes. Two separately trained household models do not establish geographic transfer.

The implementation should export audit tables, fold eligibility counts, pooled predictions, metrics, comparisons, and a leakage audit beneath `benchmark/verify/`. Generate every reported empirical number from the verification script and retain it in `verify/results/`. No benchmark execution, pytest run, empirical result, or reproduction verdict was produced in this read-only methodology turn.