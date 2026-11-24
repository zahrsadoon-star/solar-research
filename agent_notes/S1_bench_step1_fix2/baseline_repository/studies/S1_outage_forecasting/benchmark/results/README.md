# S1 benchmark artifacts: significance blocked

## What was run

The preceding experimenter ran `benchmark.py` once with seed 42, exporting pooled
chronological test probabilities for BG/KR at the specified horizons. The original
published metrics remain in `benchmark_results.csv`; the rerun's scores are under
`step1_rerun/`. `predictions.csv.gz` belongs to that rerun, not to the original scores.
The rerun log and package versions are in `agent_notes/S1_bench_step1/`.
The redirected benchmark launch reported status 1 with warnings; its log contains
the completed ranking output. Exported metrics were separately validated.

The fixer audited git provenance and disabled historical inference; no additional
training run or statistical analysis was performed. Repeating runs until they agree
would not resolve provenance and would risk selecting a favorable rerun.

## Reproduce the audit

From the repository root, without network or installation:

```powershell
python agent_notes/S1_bench_step1/check_preservation.py
python agent_notes/S1_bench_step1/statistical_audit.py
python agent_notes/S1_bench_step1/audit_provenance.py
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='--basetemp=agent_notes/S1_bench_step1/pytest_tmp_fixer -o cache_dir=agent_notes/S1_bench_step1/pytest_cache'
python -m pytest -q
python studies/S1_outage_forecasting/benchmark/significance.py
```

The preservation checker and significance command intentionally exit nonzero.
The latter is disabled unconditionally, even if an audit JSON is edited. It reads
no data and generates no inference artifacts. Historical code is retained in git.

The earlier training command was
`python studies/S1_outage_forecasting/benchmark/benchmark.py`. It overwrites benchmark
outputs; do not rerun against the frozen results without first archiving them and
redirecting `benchmark.OUT` to a fresh directory. Original backups are in
`agent_notes/S1_bench_step1/original_results/`. No settings, features or splits may
be changed to recover agreement.

## Findings and weaknesses

`preservation_check.json` and `preservation_differences.csv` record 135 changed
metric/rank cells, maximum absolute Brier drift 0.0013 and maximum rank change 3.
Timing is excluded. This is not row-order or rounding noise. Predictions reproduce
the archived rerun metrics. `step1_provenance_audit.json` confirms that frozen scores
match the initial git commit, and loader, features, algorithms, scoring and main
functions are structurally unchanged. The run function only gained export code.

Git identifies the committed code, not the actual original producing environment.
No original-run environment manifest was located. The verifier manifest describes
a separate experiment; requirements and rerun versions do not prove original
versions. Package, platform, input or runtime differences cannot be causally assigned
from the available evidence. Original producing-run metadata and/or predictions
are needed to investigate further without changing the frozen experiment.

No new `significance_pairs.csv` or `significance_summary.md` exists. Top groups in
all cases remain unresolved. Existing `significance.csv` and
`hourly_predictions_top6.csv.gz` are historical, incompatible artifacts: they must
not support current conclusions. MUST-FIX 1 and 3 remain blocked by preservation.

After resolution, the planned procedure is paired 24-hour moving-block bootstrap
(2000 resamples, seed 42), Brier and AUC intervals using the same indices, DM with
HAC lag h-1+24 and HLN correction, and within-case Holm over all 21 comparisons.
The plan freezes CSV-derived shortlists as configuration, so inference reads only
predictions. Required statistical unit tests remain pending with that implementation.
No methods references were verified offline.

Test-selected shortlists make inference exploratory. Marginal intervals and
within-case Holm do not establish study-wide superiority; non-rejection is not
equivalence. Longer dependence, seasonality, monthly refitting and single-seed
training limit interpretation; bootstrap draws are not independent training runs.
Features assume completed origin-hour metering is available. Shared outer splits
and features do not establish equal tuning effort; MLP early stopping is internal
and random. Random holdout results are nonprospective.

Fresh fixer validation: 60 passed, 47 warnings in 83.27 seconds (exit 0); see agent_notes/S1_bench_step1/pytest_fixer.log. Existing NumPy timedelta deprecation warnings remain.
