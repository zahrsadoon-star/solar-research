# Independent S1 significance check

Current results documentation lives here because the task protects primary benchmark
documents and restricts new outputs to significance_check/. The older
`../results/README.md` describes a superseded preservation gate; see
[COMPARISON.md](COMPARISON.md) for explicit corrections and the generated case table.

## Run and reproduce

From the repository root, using the existing Python environment (numpy, pandas,
scipy; no installation or network needed):

The final full-suite command requires the pending test-file repair described in
agent_notes/FIX_REPORT.md first. Do not run it against the obsolete primary-entry-point
test, which can overwrite primary artifacts. Analysis commands are independent of
that repair.

```powershell
python studies/S1_outage_forecasting/benchmark/significance_check/check.py
python agent_notes/S1_bench_step1/write_repro_note.py
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP=(Resolve-Path agent_notes/S1_bench_step1).Path
$env:TMP=$env:TEMP
$env:PYTEST_ADDOPTS='--basetemp=agent_notes/S1_bench_step1/pytest_tmp_fixer_current -o cache_dir=agent_notes/S1_bench_step1/pytest_cache'
python -m pytest -q
```

The analysis reads only `../results/hourly_predictions_top6.csv.gz` for forecasts.
Its metadata columns are site, h, time and y. Algorithm columns are sparse across
cases, with six populated algorithms per case and no reference forecasts.
`../results/significance.csv` is read afterward solely for the comparison.
No primary analysis is imported or executed and no model is refitted.

`config.json` fixes 24-hour moving blocks, 2000 resamples, seed 42, and 95% intervals.
`pairs.csv` contains all 15 pairs per case, Brier and AUC differences and marginal
intervals, DM with Bartlett HAC lag h-1+24 and HLN correction, two-sided Student t
p-values and within-case Holm adjustment. `manifest.json` records input and code
hashes, software, sample coverage and actual Git ancestry and primary blob checks.

## Findings and weaknesses

The generated comparison agrees with primary top-group membership in three of four
cases. BG 1 h retains Gradient Boosting in this check. The two procedures differ
in block length, HAC lag, HLN correction and multiplicity family; individual causes
were not isolated. Non-rejection is not equivalence. These are exploratory,
within-case conclusions conditional on a test-selected shortlist and saved
single-training-seed forecasts. Bootstrap draws are not independent training runs.

Reference superiority, equal tuning budgets, feature ablations, longer temporal
dependence and seasonal heterogeneity remain untested. The protocol does not
establish a causal explanation for random-split improvement. Methodological
sources still require verification before publication. See COMPARISON.md for
the full interpretation and `agent_notes/S1_bench_step1/REPRO_NOTE.md` for accepted
Linux/Windows metric drift. Windows rerun artifacts are not analysis inputs.

Integration and full-suite acceptance are reported in `agent_notes/FIX_REPORT.md`;
the existence of these outputs does not establish that the required merge occurred.
