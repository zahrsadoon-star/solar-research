# Step 2 tuning

K=1 for every algorithm, seed=42; draws with replacement.

Estimated runtime: 158.60 minutes; feasible: False.

1.25 * (9*(K+2)*sum(max probe seconds per case/model) + 27*sum(BG1 LR/RF max seconds))

25% overhead; outer refit allowance twice late inner fit; includes sanity cost

Config 0 is unchanged. Other configs use n_jobs=-1 where supported (CatBoost thread_count=-1).

Cases execute in separate processes as requested by --n-jobs. Native BLAS/OpenMP limits and LOKY_MAX_CPU_COUNT are one; estimator parameters are unchanged. Explicit estimator parallelism and CatBoost may manage additional threads. The timing estimate is sequential, not measured parallel wall time.

Default CSV metrics have four-decimal precision. Differences use those stored values.

Small differences cannot establish improvements beyond baseline rounding and reproducibility uncertainty. The literal LR reproduction gate remains unresolved unless the lead explicitly changes the criterion or supplies a verified full-precision baseline.

SUBSET ONLY: rankings apply only to the evaluated algorithms and cases; no full-benchmark dominance conclusion is supported.

No significance tests were run. This is one seed, not multiple independent runs; temporal folds are dependent.

Step 1 inference does not transfer to tuned models. MLP early stopping and SVM calibration retain benchmark internal splitting.

Limitations: metering-proxy labels, completed-origin-hour availability, one year per site, seasonal drift, dependent losses, overlapping training, class imbalance, unequal search-space coverage and prior inspection of this test year.

## Duplicate draws

- Logistic Regression: 0 repeated random draws; 0 unique random overrides; 1 unique effective configurations including config 0 (0 repeats).

- Random Forest: 0 repeated random draws; 0 unique random overrides; 1 unique effective configurations including config 0 (0 repeats).

## BG, h=1 hours

| algorithm | brier | default_brier | delta_brier | rank_by_brier | default_rank_by_brier |
|---|---|---|---|---|---|
| Random Forest | 0.120814 | 0.121100 | -0.000286 | 1.000000 | 2.000000 |
| Logistic Regression | 0.134136 | 0.134100 | 0.000036 | 2.000000 | 9.000000 |

Changed rank: Random Forest, Logistic Regression

Config 0 selections:

| algorithm | config_0 / folds |
|---|---|
| Logistic Regression | 9/9 |
| Random Forest | 9/9 |

Measured invocation runtime (including reuse and assembly, excluding historical timing probe): 0.03 minutes (excludes initial timing and interrupted attempts).

Subset only. Top-two membership by Brier is unchanged versus the stored defaults in every case. No full-benchmark dominance claim is made.

## K=1 sanity: BG h=1

| algorithm | metric | recomputed | stored | difference | absolute_difference | tolerance | literal_pass | equal_after_4dp |
|---|---|---|---|---|---|---|---|---|
| Logistic Regression | accuracy | 0.811032 | 0.811000 | 0.000032 | 0.000032 | 1e-09 | False | True |
| Logistic Regression | precision | 0.794426 | 0.794400 | 0.000026 | 0.000026 | 1e-09 | False | True |
| Logistic Regression | recall | 0.875211 | 0.875200 | 0.000011 | 0.000011 | 1e-09 | False | True |
| Logistic Regression | f1 | 0.832864 | 0.832900 | -0.000036 | 0.000036 | 1e-09 | False | True |
| Logistic Regression | auc | 0.886527 | 0.886500 | 0.000027 | 0.000027 | 1e-09 | False | True |
| Logistic Regression | brier | 0.134136 | 0.134100 | 0.000036 | 0.000036 | 1e-09 | False | True |
| Random Forest | accuracy | 0.825428 | 0.825100 | 0.000328 | 0.000328 | nan | not prescribed | False |
| Random Forest | precision | 0.810461 | 0.809900 | 0.000561 | 0.000561 | nan | not prescribed | False |
| Random Forest | recall | 0.881690 | 0.882000 | -0.000310 | 0.000310 | nan | not prescribed | False |
| Random Forest | f1 | 0.844576 | 0.844400 | 0.000176 | 0.000176 | nan | not prescribed | False |
| Random Forest | auc | 0.910910 | 0.910500 | 0.000410 | 0.000410 | nan | not prescribed | False |
| Random Forest | brier | 0.120814 | 0.121100 | -0.000286 | 0.000286 | 0.005000 | True | False |

LR literal tolerance is 1e-9 for each metric; RF tolerance is 0.005 for Brier. Raw differences are reported without causal attribution. Four-decimal equality is a separate diagnostic.
