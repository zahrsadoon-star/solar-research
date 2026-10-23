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
| Best algorithm (Brier) | Extra Trees | Extra Trees | Random Forest | Random Forest |
| Random Forest accuracy | 82.5 % | 77.8 % | 91.7 % | 90.1 % |
| RF accuracy, random split | 85.3 % | 78.7 % | 92.7 % | 91.7 % |
| Same hour last 7 days (reference) | 75.3 % | 75.3 % | 81.1 % | 81.1 % |
| Always "no outage" (reference) | 46.2 % | 46.2 % | 83.5 % | 83.5 % |

Overall ranking (mean rank by Brier score over the 4 cases): Random Forest 1.5, Extra Trees 1.75, CatBoost 4.25,
LightGBM 5.0, XGBoost 5.0, Gradient Boosting 5.5, Logistic Regression 7.0, kNN 7.5, SVM 8.75, MLP 9.0,
Decision Tree 10.75, Naive Bayes 12.0.

## Reading the numbers
- Tree ensembles win; the top six are within ~1 accuracy point of each other, so "best" needs a significance test
  (next step).
- Accuracy is misleading in Karbala: outages are only ~16 % of hours, so always guessing "no outage" already scores
  83.5 %. Use F1, AUC and Brier score there.
- The random split adds 1-3 accuracy points (Baghdad 1 h: 82.5 -> 85.3 %) because test hours sit next to training
  hours. The thesis's 84 % is consistent with these numbers.

## Next small steps (one at a time)
1. Significance: Diebold-Mariano / Wilcoxon between the top algorithms, with confidence intervals.
2. Hyper-parameter tuning with the same budget for every algorithm (time-ordered validation inside the training months).
3. Feature importance (which information matters).
4. LSTM / GRU on the same task.
