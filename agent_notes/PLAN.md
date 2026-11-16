Protocol for `20261116-s1-bench-step2-tuning`. No files were edited or saved because this session is read-only. The requested `agent_notes/PLAN.md` also falls outside the task’s narrower notes allowlist, `agent_notes/S1_bench_step2/`.

Read: `PROJECT_CONTEXT.md`, `AGENTS.md`, `DECISIONS.md`, study `PLAN.md`, benchmark README, `benchmark.py`, `significance.py`, and earlier benchmark verification notes.

**1. Scope and hypothesis**

Follow the latest decision: outage forecasting only, BG and KR, horizons \(h\in\{1,6\}\) hours, and the twelve existing algorithms. Older study-plan provisions for dispatch, additional targets, models and horizons are outside this task.

The descriptive question is whether equal-budget tuning changes Brier scores and algorithm rankings relative to existing defaults. No improvement is assumed.

Operational hypotheses:

- For each algorithm and case, tuning improves predictive probability accuracy if \(\Delta B=B_{\text{tuned}}-B_{\text{default}}<0\). A nonnegative difference contradicts improvement for that case.
- Define the existing leading pair as Random Forest and Extra Trees. Its descriptive dominance persists only if both occupy the first two Brier ranks in every case; any other outcome contradicts that specific claim.
- These are descriptive criteria, not statistical significance or equivalence tests.

**2. Data, target and predictors**

Import `load`, `features`, `algorithms`, `scores`, `HORIZONS`, and `SEED` from `benchmark.py`. Do not independently alter preprocessing.

For observed grid energy \(G_t\):

\[
O_t=\mathbf1(G_t=0),\qquad Y_{t,h}=O_{t+h}.
\]

The target is outage status at the future hour, not “any outage during the next \(h\) hours.” It is a metering proxy, not independently verified utility availability.

Preserve the assigned hourly local-time chronology, all nineteen existing features, and the benchmark eligibility mask: all features and the shifted target must be observed. Use identical eligible observations for every algorithm.

Forecast issuance assumes measurements through origin \(t\) are complete and available. Current-hour features require that assumption. Historical features may update during a test month as observations become available; fitted models may not.

**3. Exact nested temporal splits**

For outer test month \(m\in\{\text{April},\ldots,\text{December}\}\), let \(a_m\) denote its start and \(v_m=a_{m-1}\) the preceding month’s start. Intersect all sets below with eligible observations.

\[
T_m=\{t:t<a_m,\ t+h<a_m\},
\]

\[
E_m=\{t:a_m\le t<a_{m+1}\},
\]

\[
I_m=\{t\in T_m:t<v_m,\ t+h<v_m\},
\]

\[
V_m=\{t\in T_m:v_m\le t<a_m\}.
\]

Thus April uses March validation. Validation excludes preceding-month origins whose targets reach the outer test month.

Outer test membership follows **origin month**, matching the benchmark. Targets may enter the following month; unavailable year-end targets are excluded.

For every configuration:

1. Clone the benchmark estimator and apply its configuration.
2. Fit exclusively on \(I_m\), including pipeline scalers.
3. Predict \(V_m\) and calculate Brier loss.
4. Select the smallest validation Brier; break exact ties by lowest configuration index.
5. Fit a fresh selected estimator on \(T_m\).
6. Predict \(E_m\) once.

No outer-test metric, label, rank or convergence outcome may guide configuration selection. Later folds may use previously observed months, as required by expanding-window evaluation.

**4. Frozen search and equal budget**

Configuration 0 is an unchanged clone of `algorithms()[name]`, including pipeline structure, stochastic settings and estimator defaults. Record its full parameters.

Use these explicit candidate lists for configurations 1 onward; all unlisted settings remain at benchmark defaults. Pipeline parameters require the corresponding estimator prefix.

| Algorithm | Random-search space |
|---|---|
| Logistic Regression | `C=[0.01,0.1,1,10,100]` |
| Naive Bayes | `var_smoothing=[1e-12,1e-11,1e-10,1e-9,1e-8,1e-7,1e-6,1e-5]` |
| k-Nearest Neighbours | `n_neighbors=[5,15,25,51]`, `weights=["uniform","distance"]` |
| Decision Tree | `max_depth=[3,5,8,None]`, `min_samples_leaf=[5,20,50]` |
| Random Forest | `n_estimators=[100,300]`, `max_depth=[8,16,None]`, `min_samples_leaf=[1,5,20]`, `max_features=["sqrt",0.5,1.0]` |
| Extra Trees | Same space as Random Forest |
| Gradient Boosting | `learning_rate=[0.03,0.1]`, `n_estimators=[100,300]`, `max_depth=[2,3,5]`, `subsample=[0.8,1.0]` |
| XGBoost | `learning_rate=[0.03,0.05,0.1]`, `n_estimators=[100,300]`, `max_depth=[3,5,7]`, `subsample=[0.8,1.0]` |
| LightGBM | `learning_rate=[0.01,0.03,0.1]`, `n_estimators=[100,300]`, `num_leaves=[15,31,63]`, `subsample=[0.8,1.0]` |
| CatBoost | `learning_rate=[0.03,0.1]`, `iterations=[100,300]`, `depth=[4,6,8]` |
| SVM | `C=[0.1,1,10]`, `gamma=["scale",0.001,0.01,0.1]` |
| Neural Network (MLP) | `hidden_layer_sizes=[(32,),(64,32),(64,)]`, `alpha=[0.0001,0.001,0.01]` |

Initialize one `numpy.random.default_rng(42)` per algorithm. Sample each parameter uniformly from its list, in the displayed order. Generate nineteen random configurations once and reuse the same ordered candidates across all sites, horizons and folds.

Draw **with replacement**: repeated configurations count against the budget and are reported. This permits the required twenty evaluations even for smaller finite spaces. Equal configuration counts do not imply equal numbers of unique configurations or equal computation.

Use \(K=20\) unless the timing rule reduces it for all algorithms equally. A smaller budget uses the same candidate-list prefix.

Keep configuration 0 unchanged even where adding `n_jobs=-1` would change its parameters. Use available parallel settings for other configurations, record them, and flag this conflict between exact-default preservation and the blanket parallelism instruction.

**5. Timing rule**

Before evaluating outer-test performance, time configurations 0 and 1 on a fixed late inner split for all four cases and twelve algorithms. Use only training and validation data.

Estimate total runtime conservatively using the slower timed configuration per algorithm/case, accounting for all nine folds, \(K\) candidate fits, full-training refits, and the required sanity reruns. Record the formula, timings and overhead assumption.

Choose the largest integer \(K\in[8,20]\) estimated to fit approximately eighty minutes. If even \(K=8\) exceeds that estimate, report the infeasibility; do not reduce below eight, selectively shorten models, or drop folds.

Freeze \(K\) before inspecting outer performance. Timing fits are not additional selection candidates.

**6. Metrics and baselines**

Pool all outer predictions within each site–horizon–algorithm case; do not average monthly metrics. Use `scores`, with \(\hat y_i=\mathbf1(p_i\ge0.5)\).

\[
B=\frac1N\sum_i(p_i-y_i)^2,\qquad
A=\frac1N\sum_i\mathbf1(\hat y_i=y_i),
\]

\[
P=\frac{TP}{TP+FP},\quad
R=\frac{TP}{TP+FN},\quad
F_1=\frac{2TP}{2TP+FP+FN}.
\]

Follow `scores` by assigning zero to undefined precision, recall or F1.

\[
\mathrm{AUC}=
\frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
[\mathbf1(p_i>p_j)+\tfrac12\mathbf1(p_i=p_j)]}{N_+N_-}.
\]

Single-class AUC is undefined; flag it rather than fabricate a value.

Primary comparators are each algorithm’s stored default results. Retain existing reference scores for always no outage, persistence and same-hour history as context. Do not tune these references or run another random split.

Report tuned-minus-default differences for predictive metrics. Negative Brier differences indicate improvement; positive accuracy differences indicate improvement. Clearly identify the default CSV’s limited precision.

**7. Reproduction gate**

Run \(K=1\) for LR and RF in BG, \(h=1\), across all outer folds.

Report the literal requested comparisons:

- LR: absolute metric differences against `benchmark_results.csv`, tolerance \(10^{-9}\).
- RF: absolute Brier difference, tolerance \(0.005\).

**The LR requirement has a precision conflict:** `benchmark.py` saves metrics rounded to four decimal places. Raw recomputed metrics cannot generally equal these values within \(10^{-9}\).

Therefore report separately:

- Raw differences and literal pass/fail.
- Equality after the same four-decimal serialization.
- A fresh unchanged-default rerun comparison at full precision, if performed.

The latter checks help diagnose reproduction but do not replace or silently relax the requested CSV check. Report RF differences without attributing them to threading without evidence.

**8. Seeds, inference and failures**

Use seed 42 for candidate generation and preserve benchmark estimator seeds. This is one tuning realization; nine temporal folds are not nine independent stochastic runs.

The general requirement for multiple independent runs remains unmet by the specified single-seed task. State this limitation explicitly rather than expanding the experiment silently.

Run no inferential tests in Step 2. Step 1 uses two-sided Diebold–Mariano tests with Newey–West lag 24, Holm adjustment within each case, and a seven-day moving-block bootstrap with 2,000 replicates. Those findings do not transfer to tuned models. Failure to reject a difference also does not establish equivalence.

Record warnings and failures. Nonfinite validation predictions or failed candidate fits make the planned comparison incomplete; investigate without replacing candidates after seeing scores. Preserve failed-run evidence.

**9. Outputs and checks for implementation**

Within `results/tuning/`, save:

- `tuned_results.csv`: tuned metrics, \(K\), corresponding default columns and metric differences. Label copied random-split accuracy as default-only.
- `selected_configs.csv`: case, outer month, configuration index, JSON parameters and inner Brier.
- `tuned_predictions.csv.gz`: requested keys, truth and all twelve probabilities at full precision.
- `tuning_summary.md`: rankings, rank changes, configuration-0 selection counts and denominators, duplicate counts, runtime decision and sanity results.

Use average ranks for exact ties. For the README, report the six lowest tuned-Brier algorithms per case, with default/tuned Brier and accuracy. Describe changes without significance claims.

Fast tests must cover default-parameter identity, reproducible in-space draws, both origin and target split boundaries, and minimum-Brier selection including tie handling. Also verify unique prediction keys, shared evaluation rows and finite probabilities in \([0,1]\).

Implementation must run `python -m pytest -q` and record its outcome. No tests or experiments were run during this methodology-only review.

**10. Threats to validity**

Principal limitations are proxy-label error, assumed timestamp and metering availability, one year per household, seasonal drift, dependent hourly losses, overlapping training sets, class imbalance, single-seed variability, unequal search-space coverage, and historical result precision.

Additional concerns:

- A single preceding validation month can favor transient regimes.
- MLP internal early stopping and SVM probability calibration retain benchmark internal non-temporal splitting; neither may access the external validation or test sets.
- Previously viewed benchmark outcomes mean this protocol is not blinded.
- Repeated benchmark development on the same test year can create researcher-level adaptation.
- Separate fitting at two households does not demonstrate geographic transfer.
- Equal configuration budgets do not establish equal optimization opportunity or runtime.

Any future-information use, unequal candidate budget, missing outer folds, or outcome-driven search revision invalidates the intended comparison, regardless of the resulting scores.