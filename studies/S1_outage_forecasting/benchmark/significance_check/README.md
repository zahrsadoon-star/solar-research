# Independent S1 significance check

Run from the repository root with the existing environment (no installation or network):

```powershell
python studies/S1_outage_forecasting/benchmark/significance_check/check.py
python -m pytest -q --basetemp=agent_notes/S1_bench_step1_fix2/pytest_tmp
python -m ruff check studies/S1_outage_forecasting/benchmark/significance_check/check.py tests/test_s1_sig_check.py tests/test_s1_bench_significance.py
```

The frozen forecast input is `../results/hourly_predictions_top6.csv.gz`.
`config.json` fixes the settings. Current generated artifacts are
`../results/significance_check/pairs.csv`, `manifest.json`, and `brier_intervals.png`.
The old `pairs.csv` and `manifest.json` beside this README are retained historical
artifacts; they are not the current output location.

[COMPARISON.md](COMPARISON.md) is generated against Git revision `cec3552`, not a
moving branch. Current local `main` and its actual integration status are recorded
separately in the output manifest. Main's source and published results are never
executed or overwritten. No model refitting is needed for the independent check.

All unordered pairs among each case's six complete algorithms are compared using
paired moving-block bootstrap Brier/AUC intervals, HAC/HLN Brier tests and
within-case Holm adjustment. The full protocol is in `agent_notes/PLAN.md`.
Reference forecasts are absent; their significance comparisons are unavailable.
Non-rejection is not equivalence. Bootstrap draws are not independent training
runs. See the generated comparison for limitations and per-case evidence.

The task's requested external pytest basetemp and Git merge require permissions
unavailable in this session. See `agent_notes/S1_bench_step1_fix2/FAILURES.md`
and root `CODEX_REPORT.md` for actual checks and outstanding acceptance blockers.
