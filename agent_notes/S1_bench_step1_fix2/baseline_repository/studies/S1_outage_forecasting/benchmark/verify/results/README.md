# Benchmark verification artifacts

The independent experiment loads the specified raw BG and KR workbooks, audits energy and outage shares,
constructs every enumerated causal predictor, and evaluates the prescribed references, logistic regression
and random forest with expanding monthly training and pooled chronological test predictions.
The original independent implementation was frozen before benchmark source inspection. The fixer extends
that existing work; it is not a newly blinded implementation. No model was refitted during the fixer pass.

Verdict: **REPRODUCED**. 80 of 80 prescribed comparisons pass.
The maximum original forest metric difference is 0.00336580; its cause remains unresolved.
The extra seed check has maximum metric difference 0.00794220; minority-class F1 is seed sensitive.
These are numerical tolerance and descriptive sensitivity checks, with no significance test or superiority claim.
Fresh tests: 68 outcomes, 0 failures, 0 errors, 0 skips.

## Reproduce from repository root (existing environment, no installation)

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare
python studies/S1_outage_forecasting/benchmark/verify/statistical_review.py report
python -m pytest -q tests studies/S1_outage_forecasting/benchmark/verify/tests -o cache_dir=agent_notes/S1_bench_verify/pytest_cache --basetemp=agent_notes/S1_bench_verify/pytest_fixer_tmp --junitxml=studies/S1_outage_forecasting/benchmark/verify/results/pytest_fixer.xml
python studies/S1_outage_forecasting/benchmark/verify/document_fixes.py
```

To refit independently, choose a previously unused name:

```powershell
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py independent --run-name replication
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare --run-name replication
```

Named runs write beneath `runs/`; nonempty directories are rejected. The original run remains here.
Comparison verifies the producing source snapshot, current config and raw input hashes, frozen output hashes,
and complete unique case grids on both sides. A changed current verifier is permitted because comparison
validates the preserved producing source, not a claim that the current script produced the old outputs.
Named runs save their producing source alongside their manifest. The report command describes the original run.
The existing additional-seed artifacts are preserved; `statistical_review.py run` overwrites those derived
seed artifacts and should not be used when preserving that evidence is required.

## Files and limitations

`freeze.json` records original configuration, seeds, software, runtime and hashes. `predictions.csv` and
`independent_metrics.csv` hold pooled predictions and metrics. `data_audit.csv`, `outage_shares.csv`,
`exclusions.csv` and `folds.csv` document loading and eligibility. `comparison.csv` contains every metric
comparison. `leakage_audit.csv` and `random_split_audit.csv` support the audit. `seed_stability.csv` and
`seed_run.json` describe the extra seed. `pytest_fixer.xml` and `fixer_checks.json` record fresh tests.
See ../REPORT.md and the task-notes STATS_REPORT.md for detailed findings.

No chronological leakage was found, conditional on completed origin-hour metering being available.
Random holdout is non-prospective; its entire uplift cannot be attributed to adjacent hours.
The feature enumeration exceeds the README's stated count; all enumerated features were retained.
The limited seed check cannot establish robustness. Proxy labels, unknown metering latency, seasonal
dependence, class imbalance, limited households, data permissions and citation evidence remain weaknesses.
No tuning was introduced, and shared features do not establish equal tuning budgets across algorithms.
Publication corrections to the parent benchmark README require a separately authorized revision.
