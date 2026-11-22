# Frozen Step 2 protocol (continuation)

Execution-only changes; no full grid in this session. See S1_bench_step2/RUN.md for commands.

**1. Scope and hypotheses**

Preserve the original Step 2 protocol: BG and KR; horizons \(h\in\{1,6\}\) hours; all twelve existing algorithms; expanding monthly evaluation from April through December 2018. The latest decisions supersede the broader study plan’s dispatch, duration targets, additional horizons and model families.

This continuation changes execution and recovery, not the experiment.

- Tuning improves a case only if \(\Delta B=B_{\mathrm{tuned}}-B_{\mathrm{default}}<0\). A nonnegative difference contradicts improvement for that case.
- RF/Extra Trees dominance persists only if they occupy the first two Brier ranks in every case. A different leading pair contradicts that descriptive claim; ties must be disclosed.
- Resumability succeeds only if interrupted and uninterrupted runs produce identical selected configurations, predictions and derived metrics for the same frozen inputs. Execution times and compression metadata need not match.

These are descriptive criteria, not significance or equivalence tests.

**2. Data, targets and predictors**

Use unchanged `benchmark.load`, `features`, `algorithms`, `scores`, `HORIZONS` and `SEED`.

For grid energy \(G_t\), measured in kWh:

\[
O_t=\mathbf1(G_t=0),\qquad Y_{t,h}=O_{t+h}.
\]

This predicts the metering proxy at the future hour, not whether any outage occurs during the intervening period. Use BG’s analysis workbook and KR’s existing workbook through the benchmark loader. Exclude BS.

Preserve all nineteen features and the existing eligibility mask: every feature and shifted target must be observed. Every algorithm in a case must evaluate identical rows.

Forecast origin \(t\) means the current hour’s measurements are complete and available. Features may incorporate newly observed history during a test month; model parameters remain fixed throughout that month. Preserve the benchmark’s assigned local hourly chronology.

**3. Nested temporal splits**

Let \(a_m\) be the start of test month \(m\), and \(v_m=a_{m-1}\). Intersect these sets with eligible observations:

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

April therefore validates on March. Both training boundaries exclude labels reaching the subsequent evaluation period.

For each candidate, fit exclusively on \(I_m\), including scalers; evaluate Brier loss on \(V_m\). Choose the smallest loss, breaking exact ties by lowest candidate index. Fit a fresh selected estimator on \(T_m\), then predict \(E_m\).

Test membership follows origin month. Test targets may enter the next month; unavailable year-end targets are excluded. No test scores, labels, rankings or observed failures may guide search-space changes.

**4. Frozen candidates, seeds and budget**

Retain these exact ordered search spaces, mirrored in `tuning.py::SEARCH_SPACES`. Do not change parameter values, ordering, defaults or sampling. JSON arrays for MLP hidden layers denote Python tuples.

```json
{
  "Logistic Regression": {
    "logisticregression__C": [
      0.01,
      0.1,
      1,
      10,
      100
    ]
  },
  "Naive Bayes": {
    "gaussiannb__var_smoothing": [
      1e-12,
      1e-11,
      1e-10,
      1e-09,
      1e-08,
      1e-07,
      1e-06,
      1e-05
    ]
  },
  "k-Nearest Neighbours": {
    "kneighborsclassifier__n_neighbors": [
      5,
      15,
      25,
      51
    ],
    "kneighborsclassifier__weights": [
      "uniform",
      "distance"
    ]
  },
  "Decision Tree": {
    "max_depth": [
      3,
      5,
      8,
      null
    ],
    "min_samples_leaf": [
      5,
      20,
      50
    ]
  },
  "Random Forest": {
    "n_estimators": [
      100,
      300
    ],
    "max_depth": [
      8,
      16,
      null
    ],
    "min_samples_leaf": [
      1,
      5,
      20
    ],
    "max_features": [
      "sqrt",
      0.5,
      1.0
    ]
  },
  "Extra Trees": {
    "n_estimators": [
      100,
      300
    ],
    "max_depth": [
      8,
      16,
      null
    ],
    "min_samples_leaf": [
      1,
      5,
      20
    ],
    "max_features": [
      "sqrt",
      0.5,
      1.0
    ]
  },
  "Gradient Boosting": {
    "learning_rate": [
      0.03,
      0.1
    ],
    "n_estimators": [
      100,
      300
    ],
    "max_depth": [
      2,
      3,
      5
    ],
    "subsample": [
      0.8,
      1.0
    ]
  },
  "XGBoost": {
    "learning_rate": [
      0.03,
      0.05,
      0.1
    ],
    "n_estimators": [
      100,
      300
    ],
    "max_depth": [
      3,
      5,
      7
    ],
    "subsample": [
      0.8,
      1.0
    ]
  },
  "LightGBM": {
    "learning_rate": [
      0.01,
      0.03,
      0.1
    ],
    "n_estimators": [
      100,
      300
    ],
    "num_leaves": [
      15,
      31,
      63
    ],
    "subsample": [
      0.8,
      1.0
    ]
  },
  "CatBoost": {
    "learning_rate": [
      0.03,
      0.1
    ],
    "iterations": [
      100,
      300
    ],
    "depth": [
      4,
      6,
      8
    ]
  },
  "SVM": {
    "svc__C": [
      0.1,
      1,
      10
    ],
    "svc__gamma": [
      "scale",
      0.001,
      0.01,
      0.1
    ]
  },
  "Neural Network (MLP)": {
    "mlpclassifier__hidden_layer_sizes": [
      [
        32
      ],
      [
        64,
        32
      ],
      [
        64
      ]
    ],
    "mlpclassifier__alpha": [
      0.0001,
      0.001,
      0.01
    ]
  }
}
```

- Candidate 0 is an unchanged clone of the benchmark estimator.
- Each algorithm receives its own `numpy.random.default_rng(42)`.
- Generate nineteen random configurations with replacement, sampling parameters in their frozen order.
- Reuse the same candidate-list prefix across sites, horizons and folds.
- Duplicate draws count against the budget and must be reported.
- Preserve benchmark estimator seeds and pipeline behavior.

The stored timing rule is:

\[
\widehat T(K)=1.25\left[
9(K+2)\sum_{s,h,a}\max_{c\in\{0,1\}}t_{s,h,a,c}
+27\sum_{a\in\{\mathrm{LR,RF}\}}\max_c t_{\mathrm{BG},1,a,c}
\right].
\]

It includes 25% overhead, a refit allowance twice the late inner-fit cost, and sanity-run costs.

The existing `budget.json` records **K=8, feasible=false**, with an estimated **30,222.667541250412 seconds**. No budget in the prescribed range met the 80-minute target. Retain K=8 as the previously frozen minimum and report this infeasibility explicitly. The estimate is sequential, not a measured parallel wall time or a guaranteed upper bound.

Preserve `timings.csv` as `timing_probe_20261116.csv`. Do not choose K again using interrupted-run performance.

Define `--n-jobs` as execution concurrency without silently changing candidate 0’s estimator parameters. Record worker and native-thread limits.

**5. Metrics and baselines**

Pool all outer predictions within each site–horizon–algorithm case; do not average monthly scores. Let \(\hat y_i=\mathbf1(p_i\ge0.5)\).

\[
B=\frac1N\sum_i(p_i-y_i)^2,\qquad
A=\frac1N\sum_i\mathbf1(\hat y_i=y_i),
\]

\[
P=\frac{TP}{TP+FP},\qquad
R=\frac{TP}{TP+FN},\qquad
F_1=\frac{2TP}{2TP+FP+FN}.
\]

Use the benchmark’s zero convention for undefined precision, recall and F1.

\[
\mathrm{AUC}=
\frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
[\mathbf1(p_i>p_j)+\tfrac12\mathbf1(p_i=p_j)]}{N_+N_-}.
\]

Single-class AUC is undefined and must be flagged.

Primary comparisons are against each algorithm’s stored default metrics. Retain always-no-outage, persistence and same-hour-last-seven-days references as context. Do not rerun random splits; any copied random-split accuracy remains explicitly default-only.

Report tuned-minus-default differences and average ranks for exact ties. Stored default metrics have four-decimal precision; very small differences or rank distinctions may be unresolved by that precision.

**6. Checkpoint protocol**

One completed unit is `(site, h, test_month, algorithm)`. A checkpoint becomes reusable only after candidate selection, outer refitting, prediction and validation all succeed.

Each checkpoint must contain or reference:

- Unit identity and protocol/schema version.
- K, ordered candidates, effective estimator parameters and seeds.
- Input, relevant source-code and environment fingerprints.
- All candidate validation losses and selected index.
- Origin times, target times, truth and full-precision probabilities.
- Warnings, completion status and elapsed time.

Write atomically. A filename alone is not evidence of completion.

On restart, skip only checkpoints matching the frozen experiment and expected row identities. Reject corrupt, incomplete, duplicate or incompatible units; never silently combine different K values, datasets, candidate manifests or implementations. In particular, isolate K=1 sanity checkpoints from K=8 production checkpoints.

Assemble outputs deterministically from the requested complete set. Require unique keys, identical truth and evaluation rows across algorithms, and finite probabilities in \([0,1]\). Missing units must prevent publication of a complete-grid summary.

Old cumulative partial CSVs are not valid new-format checkpoints. The implementer must remove the interrupted prediction/result artifacts as specified, while retaining timing evidence and the frozen protocol provenance. No partial output may be presented as completed results.

**7. Sanity gate and required checks**

Run only K=1, BG, h=1, LR and RF, across all nine outer folds.

In `agent_notes/S1_bench_step2/SANITY.md`, report:

- LR absolute differences for all six metrics against `benchmark_results.csv`, with literal tolerance \(10^{-9}\).
- RF absolute Brier difference, tolerance \(0.005\).
- Separately, equality after four-decimal serialization.

The LR tolerance conflicts with the stored CSV’s rounding. Report literal pass/fail honestly; rounded agreement does not replace the requested check. Do not attribute discrepancies to threading without evidence.

Preserve the four existing test groups:

1. Exact default identity and reproducible, in-space candidate draws.
2. Nested origin-time and target-time boundaries.
3. Minimum-Brier selection and first-index ties.
4. Prediction integrity.

Add a tiny interrupted/resumed-run test proving completed units are not fitted again and assembled scientific outputs equal an uninterrupted run. Include rejection of incompatible or incomplete checkpoints.

The implementer must run `python -m pytest -q` and `ruff check` using the installed environment, without network access or installation. Do not launch the full grid.

**8. Deliverables and inference**

The eventual complete run must assemble:

- `tuned_results.csv`
- `selected_configs.csv`
- `tuned_predictions.csv.gz`
- `tuning_summary.md`

Retain the original reporting requirements, including rankings, metric differences, duplicate counts, configuration-0 selection frequencies and provenance.

`RUN.md` must give the tested PowerShell command using the implemented `--sites`, `--horizons`, `--K`, `--n-jobs` and `--out` syntax, K=8, and the timing caveats above. These flags are implemented; the restricted sanity CLI has been exercised. Full-grid execution is deferred to the lead.

**No inferential statistical tests are authorized in this continuation.** Earlier default-model inference cannot establish significance for tuned models. The specified single seed does not satisfy the broader requirement for multiple independent runs; temporal folds are dependent and cannot substitute for independent seeds. State this limitation rather than silently expanding the experiment.

**9. Threats to validity**

- Metering-proxy errors and uncertain real-time availability of current-hour measurements.
- Assigned timestamps, one year per household, seasonal drift and limited geographic generalizability.
- Dependent hourly losses and overlapping expanding training sets.
- A single validation month favoring transient regimes.
- Class imbalance and threshold-dependent secondary metrics.
- Single-seed variability; unequal effective search coverage despite equal candidate counts.
- Benchmark-internal MLP early stopping and SVM calibration splits.
- Prior inspection and repeated reuse of the same test year.
- Rounded baseline metrics obscuring small differences.
- Stale checkpoints, incomplete aggregation or mixed execution environments.
- Timing extrapolation from only two configurations and uncertain parallel scaling.

Any future-information leakage, outcome-driven search revision, unequal K, omitted folds or incompatible checkpoint reuse invalidates the intended comparison, regardless of scores.