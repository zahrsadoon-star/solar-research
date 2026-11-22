# K=1 sanity: BG, h=1, LR and RF

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

LR literal tolerance: 1e-9; RF Brier tolerance: 0.005. Four-decimal equality is a separate check; rounding does not waive literal failures. No cause is assigned to RF differences. Seed 42; nine dependent monthly folds, one realization; no inferential test or full tuning grid was run.
