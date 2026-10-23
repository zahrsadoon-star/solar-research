# Statistician verification

Verdict: **REPRODUCED**. 80 of 80 original comparisons pass. The largest original RF discrepancy is 0.00336580; its cause remains unresolved, within the specified tolerance. No method was tuned to improve agreement.

## Independence and additional run

The earlier agent's independent implementation and frozen artifacts already existed when this review began. Their source snapshot, configuration, raw-input hashes and output hashes were verified unchanged. This review extends that implementation; it is not a newly blinded implementation. The benchmark source was read after rerunning comparison of the frozen results. Original seed-run counts in REPORT.md describe the original frozen experiment only.

The additional RF seed is 43; the baseline seed is 42. Every original site, horizon and monthly fold was rerun with unchanged model settings and features. Truth and origin alignment were asserted before comparison. Runtime was 231.27 seconds. Maximum metric difference across seeds is 0.00794220. All differences within the existing RF reproduction tolerance: **False**. This is a descriptive sensitivity check, not a pre-registered equivalence test or a population uncertainty estimate. Two seeds cannot establish general robustness. LR and the references are deterministic under this setup and were not refitted for the seed check.

| site | horizon_h | metric | original_seed | new_seed | original | new | abs_diff | within_rf_reproduction_tolerance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BG | 1 | accuracy | 42 | 43 | 0.825428 | 0.826337 | 0.000909 | True |
| BG | 1 | f1 | 42 | 43 | 0.844576 | 0.845219 | 0.000642 | True |
| BG | 1 | auc | 42 | 43 | 0.910910 | 0.910372 | 0.000539 | True |
| BG | 1 | brier | 42 | 43 | 0.120814 | 0.121075 | 0.000261 | True |
| BG | 6 | accuracy | 42 | 43 | 0.777828 | 0.778283 | 0.000455 | True |
| BG | 6 | f1 | 42 | 43 | 0.807919 | 0.808488 | 0.000569 | True |
| BG | 6 | auc | 42 | 43 | 0.848734 | 0.848518 | 0.000216 | True |
| BG | 6 | brier | 42 | 43 | 0.154636 | 0.154584 | 0.000052 | True |
| KR | 1 | accuracy | 42 | 43 | 0.915745 | 0.916503 | 0.000758 | True |
| KR | 1 | f1 | 42 | 43 | 0.699134 | 0.702323 | 0.003189 | True |
| KR | 1 | auc | 42 | 43 | 0.917079 | 0.917618 | 0.000539 | True |
| KR | 1 | brier | 42 | 43 | 0.067614 | 0.067396 | 0.000219 | True |
| KR | 6 | accuracy | 42 | 43 | 0.901880 | 0.900516 | 0.001365 | True |
| KR | 6 | f1 | 42 | 43 | 0.630497 | 0.622555 | 0.007942 | False |
| KR | 6 | auc | 42 | 43 | 0.876247 | 0.875609 | 0.000638 | True |
| KR | 6 | brier | 42 | 43 | 0.081407 | 0.081404 | 0.000002 | True |

Seed-sensitive cases exceeding the existing reproduction tolerance (this threshold is used descriptively, not as an inferential stability criterion):

| site | horizon_h | metric | original_seed | new_seed | original | new | abs_diff | within_rf_reproduction_tolerance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KR | 6 | f1 | 42 | 43 | 0.630497 | 0.622555 | 0.007942 | False |

The fixed-seed reproduction verdict remains unchanged. The additional run does not support an unqualified claim that every metric is stable; the minority-class thresholded F1 warrants explicit seed sensitivity reporting.

## Data and class imbalance

Both loaders were exercised again. The original raw audits report no NaNs, nonnumeric energy cells or negative energy values. Full monthly outage counts and shares remain in `results/outage_shares.csv`.

| site | period | rows | observed | missing | outage_hours | outage_share |
| --- | --- | --- | --- | --- | --- | --- |
| BG | annual | 8760 | 8760 | 0 | 4328.000000 | 0.494064 |
| KR | annual | 8760 | 8760 | 0 | 1229.000000 | 0.140297 |

Train/test class shares across chronological folds (target labels, not origin states):

| site | subset | min | max |
| --- | --- | --- | --- |
| BG | test | 0.154570 | 0.803763 |
| BG | train | 0.364139 | 0.578394 |
| KR | test | 0.026882 | 0.317204 |
| KR | train | 0.058650 | 0.168391 |

No class weighting, resampling, balancing or threshold tuning is used by LR/RF. This matches the prescribed benchmark; imbalance is handled through transparent reference scores and complementary F1, AUC and Brier reporting, not by claiming accuracy alone is sufficient. All audited folds contain both classes. Oversampling is not needed to reproduce the specified probability task, and adding it now would change the experiment. Calibration and minority-class utility are not established by these pooled metrics.

## Leakage and random holdout

Direct source inspection confirms the line-by-line verdicts in `results/leakage_audit.csv`: trailing features use completed observations through the origin, target calendar values are known, future shifts occur only in labels, and the monthly training mask excludes targets entering the test month. StandardScaler is inside the LR pipeline and fitted only on training rows. This assumes completed origin-hour metering is available when a forecast is issued. No future-observation or scaling leakage was found in the chronological evaluation.

The random holdout uses shuffled hourly rows over the eligible full year, month stratification and training-only scaling. This matches the README's descriptive random comparison, but permits future observations relative to test origins and overlapping histories. It is not prospective forecasting evidence. Different populations and training sizes prevent attributing its entire uplift to adjacency. Random-split accuracy was not refitted in this review.

## Statistical tests and multiplicity

The benchmark contains no inferential statistical tests, p-values or confidence intervals. Numerical tolerance checks have no independence or distributional test assumptions, and need no multiplicity correction. A ranking is descriptive: reproduction does not establish superiority. The README's proposed Diebold-Mariano / Wilcoxon analysis is future work, not an existing validated test. Hourly losses are serially dependent and seasonal; expanding monthly fits also share training observations. An IID test of hourly errors or an unqualified independent-fold Wilcoxon test would be unjustified. Any later confirmatory analysis must define its comparison family and account for temporal dependence and multiplicity before inspecting significance; no such test is invented here.

## Automated checks and discrepancies

Pytest: 62 collected outcomes, 0 failures, 0 errors, 0 skips. Existing tests cover real loaders, hand-computed history, future perturbations, training-target boundaries and missing labels. Added checks cover hand-computed threshold/F1/AUC/Brier, wrong loader row counts, and undefined single-class AUC. See `results/pytest_statistician.xml` and the task-notes pytest log.

The feature enumeration contains 19 columns; the task/README description says eighteen. The benchmark and verifier both include every enumerated feature. Missing-value handling differs in the original benchmark but has no observed effect on these complete inputs. Publication precision explains reference/LR discrepancies; RF differences exceed rounding but pass tolerance. Keep the uncertainty about the RF discrepancy explicit.

All additions stay within the explicit write allowlist. Consequently the requested tests are in `verify/tests/test_s1_bench_verify.py`, this report is in `agent_notes/S1_bench_verify/STATS_REPORT.md`, and the implementation report is in the same notes directory. No raw data, legacy file, benchmark source or benchmark result was modified.

Re-run with `python studies/S1_outage_forecasting/benchmark/verify/statistical_review.py run`, then `report` after producing the pytest XML. Use PYTHONDONTWRITEBYTECODE=1 and route pytest cache/temp files to the allowed task notes directory.
