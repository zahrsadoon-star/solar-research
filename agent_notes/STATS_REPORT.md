# Statistical verification of the S1 significance check

Status: completed the statistical audit of the current branch. Full task acceptance remains blocked by Git/external-temp permissions and repository-wide lint.

## Verified numbers and independent seeds

Recomputed all frozen-prediction comparisons with 2,000 bootstrap draws at each of seeds 42 and 43. Seed 42 reproduces every saved numeric pair result within CSV serialization precision. Seed 43 changes 0 of the 60 pair decisions, so all four top groups remain unchanged. Maximum absolute interval endpoint changes (dimensionless):

```json
{
  "brier_ci_low": 0.00039404735082749966,
  "brier_ci_high": 0.0002967921697205458,
  "auc_ci_low": 0.0007353460830184233,
  "auc_ci_high": 0.0008516449142585095
}
```

Against the published rounded benchmark table, maximum absolute differences from recomputed frozen probabilities are Brier 4.86082681377e-05 and AUC 4.2229460865e-05, both consistent with the table's four-decimal rounding. This verifies stored metrics, not a bitwise historical training replay. Evidence: metric_audit.csv, seed43_pairs.csv and summary.json under results/significance_check/statistical_audit/.

Separately refitted RF and Extra Trees for April at both horizons and sites, using training seeds 42 and 43 with original hyperparameters. Extra Trees has lower Brier in both BG cases and RF in both KR cases at both seeds. Maximum absolute within-model Brier change is 0.00109661317662. These are descriptive rankings, not significance conclusions on the April subset. Evidence: april_seed_scores.csv and april_summary.json. Bootstrap seed stability and training seed stability are distinct checks; neither proves equivalence.


## Scope and preserved work

Read PROJECT_CONTEXT.md, AGENTS.md and earlier agent notes before acting. Kept the pre-existing implementation repairs and the user's PLAN.md. The earlier STATS_REPORT.md described obsolete failures and was superseded by this audit. No published results, legacy/ or data/ were edited. The main merge was retried and failed at ORIG_HEAD.lock due to shared Git metadata permissions. Therefore this is an audit of the current branch, not a merged-main acceptance result.

## Leakage and imbalance

Original exported labels match raw-data labels at origin+h. The existing tests verify strictly earlier training target times, both classes in monthly train/test folds, and unchanged past features when future observations are perturbed. Extended the StandardScaler check from only December to every April–December training fold. Source inspection confirms scaling is inside training-fitted sklearn pipelines. These tests verify current source and export labels, not historical training execution. Current-hour outage and rolling load are assumed available after the origin hour completes; unresolved reporting latency would change this interpretation. The target clock features are calendar information, not future measurements. The random-split comparison is not prospective evaluation; MLP early stopping uses random validation within outer training data.

There is no explicit class weighting or resampling in the benchmark. Keeping observed class frequencies is reasonable for probability scoring, but high accuracy cannot establish useful outage detection. In the April subset, both RF and Extra Trees at both seeds and horizons have KR recall and F1 of zero at the fixed 0.5 threshold, despite accuracy about 0.95833. KR test outage share is 0.0416667. These negative results are retained in april_seed_scores.csv; no threshold or class weights were tuned. AUC remains a ranking measure; Brier depends on calibration and prevalence. Added an independent sklearn AUC cross-check with rare positives and tied scores.

## Statistical tests and multiplicity

Reviewed paired, noncircular moving-block bootstrap with 24-hour blocks and 2,000 replicates per seed. Both algorithms and both metrics share the same sampled rows. Intervals are marginal 95% percentile intervals, not simultaneous confidence bands. Undefined AUC replicates make the interval unavailable rather than being silently replaced. Tests cover these behaviors.

Brier inference uses Bartlett HAC with lag h-1+24, horizon-based HLN correction and two-sided Student t probabilities. The existing independent covariance-matrix test verifies the arithmetic. Holm corrects all 15 pairwise tests within each case; invalid p-values count as one. Added a test of Holm invariance to pair ordering, including ties. Holm tolerates dependent tests but cannot validate marginal p-values whose assumptions fail. No across-case error control is provided. The extra CI exclusion condition does not increase the set of Holm rejections, but the intervals themselves are still marginal.

Temporal dependence beyond a day, pooled seasons, overlapping targets, shared training sets and changing monthly models limit the weak-stationarity approximation. The HLN/t calculation is approximate, not an exact finite-sample result here. Test-selected shortlists make this exploratory. No sources or citations were fabricated or newly verified offline. Failure to reject RF versus Extra Trees does not establish equivalence. The group is defined relative to the descriptive best, not by every pair being tied.

## Historical comparison

COMPARISON.md already gives one line per case against cec3552. Membership agrees for BG 6 h, KR 1 h and KR 6 h. BG 1 h includes Gradient Boosting in this check (Holm p=0.134812); cec3552 excludes it (p=0.04801). The procedures differ in block length, HAC lag, HLN correction and the Holm family size. No single cause was experimentally isolated. References are absent from the frozen shortlist export, so baseline superiority is not established by this check. No numerical tolerance was widened.

## Acceptance checks

- Full current branch suite using a repository-local basetemp: 78 passed, 72 dependency deprecation warnings; no skips or deselections. Logs and JUnit XML: agent_notes/S1_bench_step1_fix2/statistician_pytest.*.
- Exact requested external basetemp, before the two new tests: 61 passed and 15 setup errors, all PermissionError for D:/SolarProject/tmp/pytest/fix2sig. Exact node IDs and causes are appended to FAILURES.md.
- Scoped ruff: passed for the check, both changed test files and both new audit scripts.
- Repository-wide ruff: failed with 834 diagnostics, including the retained baseline diagnostic copy. Excluding only disposable diagnostic/scratch directories leaves 409 existing diagnostics. No blanket exclusions or out-of-scope fixes were made.
- Protected result hashes: all ten existing benchmark artifacts match protected_before.json; statistician_preservation.json records this. This is not a claim that current main's absent artifacts were integrated.
- git diff --check: passed (pre-existing line-ending warnings only).

## Reproduction and limitations

Run python agent_notes/S1_bench_step1_fix2/statistical_audit.py and python agent_notes/S1_bench_step1_fix2/training_seed_audit.py. Outputs are under studies/S1_outage_forecasting/benchmark/results/significance_check/statistical_audit/. The training audit selects April, RF and Extra Trees, original 300 trees and leaf size 5, seeds 42 and 43, before inspecting results. Single-thread fitting changes resource use only. This limited independent-training check cannot establish all-month/all-model seed stability. The frozen full benchmark still has only its original training seed.

Merge and external-basetemp execution require an environment with the necessary filesystem permissions; global lint requires a broader authorized repair scope. No network, installation, commit or push was used.
