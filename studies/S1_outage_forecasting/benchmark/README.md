# S1 benchmark - 12 algorithms for forecasting grid outages (v1, 2026-10-23)

Scope set by Zaher on 22 Oct 2026: outage forecasting only, small model, compare algorithms, find the best.
Script: `benchmark.py` (one file). Outputs: `results/benchmark_results.csv`, `results/benchmark_fold_scores.csv`,
`results/overall_ranking.csv`, `results/benchmark_accuracy.png`.

**Task.** Will the national grid be off 1 h (and 6 h) ahead? Baghdad (BG) and Karbala (KR) households, 2018, hourly.
Outage = grid energy == 0 (inferred from metering, not a utility log). Same 19 features for every algorithm (recent
outage history, time in current state, clock hour of the target, same clock hour over the last 7 days, recent load).
**Test.** Time-ordered: train on all earlier months, test the next month, April-December (9 folds). The thesis-style
random 80/20 split is also reported for comparison.

## Results (time-ordered test)
| | Baghdad 1 h | Baghdad 6 h | Karbala 1 h | Karbala 6 h |
|---|---|---|---|---|
| Lowest observed Brier | Extra Trees | Extra Trees | Random Forest | Random Forest |
| Random Forest accuracy | 82.5 % | 77.8 % | 91.7 % | 90.1 % |
| RF accuracy, random split | 85.3 % | 78.7 % | 92.7 % | 91.7 % |
| Same hour last 7 days (reference) | 75.3 % | 75.3 % | 81.1 % | 81.1 % |
| Always "no outage" (reference) | 46.2 % | 46.2 % | 83.5 % | 83.5 % |

Overall ranking (mean rank by Brier score over the 4 cases): Random Forest 1.5, Extra Trees 1.75, CatBoost 4.25,
LightGBM 5.0, XGBoost 5.0, Gradient Boosting 5.5, Logistic Regression 7.0, kNN 7.5, SVM 8.75, MLP 9.0,
Decision Tree 10.75, Naive Bayes 12.0.

## Reading the numbers
- Tree ensembles lead the descriptive Brier rankings. These observed rankings do not establish a statistically superior algorithm; significance remains unresolved.
- Accuracy is misleading in Karbala: outages are only ~16 % of hours, so always guessing "no outage" already scores
  83.5 %. Use F1, AUC and Brier score there.
- Random-split accuracy is higher in the reported RF cases (Baghdad 1 h: 82.5 -> 85.3 %). Training composition, sample sizes and test periods also differ, so this comparison does not isolate temporal adjacency as the cause. Random splits are nonprospective.

## Next small steps (one at a time)
1. Significance: Diebold-Mariano / Wilcoxon between the top algorithms, with confidence intervals.
2. Hyper-parameter tuning with the same budget for every algorithm (time-ordered validation inside the training months).
3. Feature importance (which information matters).
4. LSTM / GRU on the same task.

## Step 1 - significance: stopped at preservation gate

The requested rerun changed published predictive metrics and ranks; it is not rounding noise.
The original benchmark results have been restored. Rerun scores are archived in
`results/step1_rerun/`; `results/predictions.csv.gz` contains the rerun predictions and
must not be treated as predictions underlying the original published scores.

Maximum absolute Brier difference: 0.0013; maximum rank change: 3. See `results/preservation_check.json` and `results/preservation_differences.csv`.

Per the task's stop condition, no new significance pairs, intervals or top groups were computed.
The previous Step 1 conclusions and `significance.csv` / `hourly_predictions_top6.csv.gz`
use a different protocol and are historical, not results of this task. No claim of a
unique winner, a tie, or equivalence is supported by this incomplete step.
Resolve the reproducibility discrepancy before running the planned significance analysis.

The historical `significance.py` entry point now exits with a blocking message before
reading data, fitting models or writing artifacts. See `results/README.md` for audit
commands and `results/step1_provenance_audit.json` for repository provenance.
The original producing-run environment is unavailable; the rerun and verifier
manifests are not evidence of that original environment. Drift remains unexplained.

Top groups for BG/1 h, BG/6 h, KR/1 h and KR/6 h are all **unresolved**.
The planned analysis is exploratory: shortlists were selected on the test outcomes,
intervals are marginal, and Holm correction is within each case only. Non-rejection
would not establish equivalence or study-wide superiority. The existing plan freezes
CSV-derived shortlists in configuration, allowing predictions to be the only runtime
data input once preservation is resolved.

Shared features and outer splits support comparability, not equal tuning effort or
optimal performance. MLP uses internal random early stopping. Completed origin-hour
metering is assumed available at forecast issuance; perturbation tests found no
future-feature leakage under this assumption. Longer dependence, seasonal changes,
monthly refitting and single-seed training limit pooled inference. Bootstrap resamples
cannot replace independent training runs. Methodological references remain unverified
and must be checked before publication; this task uses no network.
