# Independent significance check

Non-rejection is not equivalence. Exploratory within-case Holm only; these groups do not establish pairwise equivalence or study-wide superiority.

| Case | Independent top group | Main top group | Membership | Unresolved |
|---|---|---|---|---|
| BG, 1 h | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost; Gradient Boosting | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost | disagree | none |
| BG, 6 h | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting | agree | none |
| KR, 1 h | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM | agree | none |
| KR, 6 h | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting | agree | none |

## Current-status correction

This document supersedes the scientific-status guidance in the preserved benchmark/results/README.md: significance is no longer blocked by Windows preservation drift, and the original-run significance.csv and hourly_predictions_top6.csv.gz are the primary artifacts for this comparison. That README describes an obsolete preservation gate. The required Git merge is a separate integration requirement; see manifest.json for actual ancestry.

The preserved benchmark/README.md claims statistical equivalence, calls bagged ensembles the best choice, and says Naive Bayes, Decision Tree, SVM and MLP are clearly behind. This check does not support those claims: non-rejection does not establish equivalence, and algorithms outside each saved shortlist were not tested. Its causal explanation of random-split improvement is also unproven; descriptive improvement does not isolate its cause. Primary documents are protected by the task; the lead must correct their wording separately.


## Changed memberships

- BG, 1 h, Gradient Boosting: independent Holm p=0.134812, best-minus-other Brier CI [-0.0115699, -0.00213851]; main Holm p=0.04801, sign-normalized CI [-0.01399, -0.00019]. The competitor is retained by this check.

## Interpretation and method differences

Groups include the descriptive Brier best and competitors not excluded by both Holm p < 0.05 and a strictly negative upper Brier difference CI. Effects here are A minus B: negative Brier favors A; positive AUC favors A. Main reports other-minus-best Brier effects, the opposite orientation.

This check uses paired noncircular 24 h blocks, 2000 draws, seed 42 reset per case, linear percentile 95% marginal intervals, HAC lag h-1+24, HLN correction with horizon h, a two-sided Student t reference with N-1 degrees of freedom, and Holm over all 15 pairs. Main uses 168 h blocks, fixed HAC lag 24, no HLN, and best-versus-others only (Holm over five tests). Main reports accuracy intervals; this check reports AUC intervals. These differences jointly explain why group membership can differ; no single change is causally isolated. Shorter blocks change interval widths and the larger Holm family changes rejection thresholds. Saved probability rounding can also affect estimates.

The primary groups above are read from significance.csv and match the main benchmark README table (kNN denotes k-Nearest Neighbours). Its equivalence wording is not adopted here. No reference prediction column exists in the original export; reference comparisons are skipped.

## Scope and reproducibility

Run `python studies/S1_outage_forecasting/benchmark/significance_check/check.py`. Configuration is in config.json; manifest.json records hashes, revisions, software, sample sizes and time ranges. Only hourly_predictions_top6.csv.gz supplies predictions. No refitting or settings changes are performed. Bootstrap draws are not independent training runs; the saved benchmark has a single training seed (42).

Time is interpreted as forecast-origin time, with target time time+h. The target is grid energy equal to zero at t+h, a metering proxy, not any outage over the interval. Completed-origin-hour metering is assumed available. The export cannot verify training provenance or absence of feature leakage. Shortlists were selected on the test set; prior exposure to primary results, temporal nonstationarity, dependence beyond 24 h, shared expanding training sets, monthly refitting, rounded probabilities, proxy-label error, metering latency, class imbalance and one year per household limit inference. Separate site models do not demonstrate geographic transfer. HLN is approximate. No methodological citations were verified offline.

Common features and outer splits do not establish equal tuning budgets. Without reference forecasts, superiority over persistence or seasonal references remains untested. All inference is conditional on saved single-seed forecasts; bootstrap-seed sensitivity is not training-seed replication. Equal-budget tuning and feature ablations remain future work. Before publication, assess dependence beyond 24 hours and seasonal/monthly heterogeneity under a separately approved protocol, and verify methodological sources.
