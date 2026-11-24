# Statistical verification of the independent S1 check

## Verified calculations and seed sensitivity

The existing independent implementation was reviewed without reading, importing,
or executing main's significance.py. The original prediction columns are
site, h, time, y, Extra Trees, Random Forest, CatBoost, LightGBM, XGBoost, Gradient Boosting, Logistic Regression, k-Nearest Neighbours. There are six populated algorithms per case and no
reference predictions; all fifteen unordered pairs per case are included.

Recomputed the entire analysis with 2000 moving-block bootstrap draws at each of
seeds 42 and 43. Seed 42 reproduces every saved numeric pair result within CSV
serialization precision. Seed 43 changes 0 pair
decisions. Maximum absolute endpoint changes (dimensionless) are
{"brier_ci_low": 0.00039404735082749966, "brier_ci_high": 0.0002967921697205458, "auc_ci_low": 0.0007353460830184233, "auc_ci_high": 0.0008516449142585095}.
These runs assess bootstrap Monte Carlo sensitivity only, not independent model
training variability. No models were refitted and no settings were tuned.

Original-export Brier and AUC values were recomputed against the published rounded
benchmark table. Maximum absolute differences are
{"auc": 4.222946086496204e-05, "brier": 4.860826813768426e-05}; detailed
values are in original_metric_audit.csv. Treat these as comparisons between saved
rounded predictions and published metrics, not proof of bitwise training replay.

## Leakage and class imbalance

Four new parameterized tests in tests/test_s1_sig_check.py verify original-export
labels against raw data at time+h, strict training-target-before-test boundaries,
both classes in every monthly train/test fold, training-only StandardScaler
moments, and invariance of earlier features under perturbing future observations.
All passed. Source inspection confirms scalers are in sklearn pipelines fitted
on the training fold. Features include completed-origin-hour readings; this
availability assumption remains essential. These checks do not reconstruct the
historical cloud execution. Random-split results are nonprospective; MLP internal
early stopping uses a random validation subset within its outer training set.

Monthly test outage prevalence ranges from 0.02688172 to
0.80376344; original_class_shares.csv records every case/month.
The benchmark uses no explicit class weights or class resampling. Probability
losses retain the observed prevalence; bootstrap rows preserve temporal clusters
and are not class balanced. AUC measures ranking, while Brier reflects calibration
and prevalence. Accuracy alone is inadequate under imbalance. Every observed
fold has both classes; the checker returns unavailable AUC intervals if a bootstrap
replicate loses a class, rather than silently discarding draws.

## Statistical assumptions and interpretation

Verified paired noncircular moving blocks of 24 hours, percentile 95% intervals,
Bartlett Newey-West HAC lag h-1+24, HLN correction and two-sided Student t p-values,
and Holm over all fifteen comparisons within each case. Tests independently check
HAC through a covariance matrix, identical forecasts, a clear advantage, seeded
bootstrap reproducibility, tied AUC scores and a hand-computed Holm example.
Holm permits dependent tests but cannot repair inaccurate marginal p-values.
Pooled seasonal data, shared training sets and monthly refitting challenge weak
stationarity assumptions; dependence beyond 24 hours is not excluded. HLN is an
approximate finite-sample correction. No methodological sources were verified
offline and no citations were invented.

COMPARISON.md agrees with main's top-group membership in three cases. BG 1 h keeps
Gradient Boosting (Holm p about 0.134812 versus main's 0.04801). Main uses longer
blocks, a different HAC lag at h=6, no HLN and five best-versus-other tests rather
than fifteen all-pair tests. The effects of these changes were not individually
isolated. Non-rejection is not equivalence. Shortlists were selected on test scores;
this is exploratory within-case correction, not study-wide confirmatory inference.
Main README's equivalence and proven-winner language is not supported by these tests.

## Integration and validation limitations

The merge was attempted again and failed creating ORIG_HEAD.lock in shared Git
metadata outside the writable repository. All specified main files were freshly
verified byte-for-byte against local origin/main without inspecting significance.py.
The archived Windows drift remains accepted as cross-platform variability under
the lead decision; REPRO_NOTE.md records metric maxima and rank changes.

Ran python -m pytest -q with only the obsolete historical-disabled-entry-point test
excluded through PYTEST_ADDOPTS, to avoid executing main and overwriting artifacts.
Result: 65 passed, 4 failed, 1 skipped, 1 deselected, 58 warnings. The four failures
are old tests using the pre-move predictions path. The skipped test also uses that
path. All eleven independent-check tests passed. An unfiltered passing suite is
not claimed. The already prepared pending_test_update.patch needs an exception to
the allowed-file list. No commit, push, package installation or network access.

Reproduce this audit: python agent_notes/S1_bench_step1/verify_independent.py.
Machine-readable outputs and the alternate-seed pairs are in the same directory.
These are audit artifacts, not manuscript results.
