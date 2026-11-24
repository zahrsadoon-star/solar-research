# Independent significance check

Historical comparator: `cec3552`; current local main is recorded separately in `../results/significance_check/manifest.json`. Non-rejection is not equivalence.

| Case | Independent top group | cec3552 top group | Finding and evidence |
|---|---|---|---|
| BG, 1 h | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost; Gradient Boosting | Extra Trees; Random Forest; CatBoost; LightGBM; XGBoost | differ; Gradient Boosting: check Holm p=0.134812, Brier CI [-0.0115699, -0.00213851]; historical Holm p=0.04801, sign-normalized CI [-0.01399, -0.00019]; RF/Extra Trees Holm p=1, Brier CI [-0.00155765, 0.000640751]; exclusion rule not met; unresolved: none |
| BG, 6 h | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting | Extra Trees; Random Forest; Logistic Regression; Gradient Boosting | agree: same competitors survive the joint exclusion rule; RF/Extra Trees Holm p=0.842612, Brier CI [-0.00209053, 0.000200737]; exclusion rule not met; unresolved: none |
| KR, 1 h | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM | Random Forest; CatBoost; Extra Trees; XGBoost; LightGBM | agree: same competitors survive the joint exclusion rule; RF/Extra Trees Holm p=0.398496, Brier CI [-0.00162407, -1.42615e-05]; exclusion rule not met; unresolved: none |
| KR, 6 h | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting | Random Forest; Extra Trees; k-Nearest Neighbours; LightGBM; XGBoost; Gradient Boosting | agree: same competitors survive the joint exclusion rule; RF/Extra Trees Holm p=1, Brier CI [-0.000832352, 0.000793155]; exclusion rule not met; unresolved: none |

## Interpretation and reproducibility

Groups contain the descriptive lowest-Brier algorithm and competitors not excluded by both Holm p < 0.05 and a strictly negative upper Brier interval. This does not establish equivalence or pairwise equality. Invalid comparisons remain unresolved. Effects are A minus B: negative Brier favors A; positive AUC favors A. Historical Brier effects are other minus best and are sign-normalized above.

The check uses paired noncircular 24-hour blocks, 2000 draws, seed 42 reset per case, linear percentile 95% marginal intervals, Bartlett HAC lag h-1+24, horizon-based HLN correction, two-sided Student t with N-1 degrees of freedom, and Holm over all 15 pairs within each case. cec3552 uses 168-hour blocks, fixed HAC lag 24, no HLN correction, and Holm over five best-versus-other comparisons. These choices differ jointly; no membership change is attributed to one choice without isolating it. No across-case error control is claimed.

Only frozen hourly_predictions_top6.csv.gz supplies forecasts. Reference probabilities (no-outage, persistence, seasonal) are absent; reference significance comparisons are unavailable. No superiority over those baselines is claimed. The core frozen-forecast check performs no refitting or settings search. A supplementary exploratory audit refits RF and Extra Trees for April only, both sites/horizons, seeds 42/43. This deviates from the original no-refitting protocol (documented in agent_notes/PLAN.md); its selection is not established as prespecified. The saved full-benchmark training seed is 42; bootstrap replicates are not independent training runs. The April subset does not meet the full-benchmark multiple-run requirement; both models have zero April KR recall at both horizons and seeds. The supplementary bootstrap-seed audit checks same-implementation replay and Monte Carlo stability, not independent implementation correctness or block-length/HAC sensitivity.

Run `python studies/S1_outage_forecasting/benchmark/significance_check/check.py`. Config is beside the script; CSV, JSON and figure outputs are under `../results/significance_check/`. The manifest records source revision, input hash, software versions, case sizes and origin/target ranges.

Origins are completed hourly observations; the target is grid_kwh at t+h equal to zero, a metering proxy. Evaluation is April-December 2018 with expanding monthly training, excluding training labels reaching the test month. The export alone cannot establish training provenance. Leakage tests audit source behavior separately.

This is exploratory: shortlists were test-selected and primary results already seen. Limitations include dependence beyond 24 hours, seasonal nonstationarity, shared training sets, monthly model changes, one training seed, rounded probabilities, proxy-label error, uncertain metering latency, class imbalance, unequal tuning budgets and one year per household. Separate models do not demonstrate geographic transfer. Methodological citations remain [UNVERIFIED] offline. The accepted Windows/Linux drift interpretation was not causally isolated.
