# Fix report: preservation remains blocked

## Review disposition

- MUST-FIX 1: investigated, unresolved. `results/step1_provenance_audit.json`
  identifies the initial code/results commit and confirms unchanged computational
  functions and preserved published scores. The export is the only change to the
  run function. No original producing-run environment manifest was located; rerun
  metadata and the independent verifier cannot attest that environment. The fresh
  audit confirms 135 changed metric/rank cells and maximum Brier drift 0.0013.
  Cause remains unknown. No settings changes, wider tolerances or selected reruns.
- MUST-FIX 2: resolved. Replaced historical significance implementation with an
  unconditional blocking entry point, including imported `main()` use. It cannot
  refit or write historical results. Added a regression test for CLI/import behavior.
- MUST-FIX 3: blocked by MUST-FIX 1 and the explicit stop-on-drift instruction.
  No new inference or statistical implementation/tests were claimed. Required pair
  and summary outputs remain absent. Completing them now would violate the gate.
- MUST-FIX 4: resolved. Removed winner claims and causal attribution of random-split
  uplift. Descriptive ranks remain labeled as observations.

SHOULD-FIX documentation now covers exploratory selection, marginal intervals,
within-case Holm, non-equivalence, heterogeneous tuning, MLP early stopping,
seasonality/monthly refitting/longer dependence, training-seed uncertainty and
completed-origin-hour availability. The existing plan's frozen CSV-derived shortlist
configuration resolves the input-handling ambiguity; it is not yet implemented.
No methodological references were verified or invented.

## Files changed in this fixer pass

- `studies/S1_outage_forecasting/benchmark/significance.py`: disabled historical entry point.
- `studies/S1_outage_forecasting/benchmark/README.md`: factual interpretation and limitations.
- `studies/S1_outage_forecasting/benchmark/results/README.md`: artifact status and reproduction.
- `agent_notes/S1_bench_step1/audit_provenance.py` and
  `studies/S1_outage_forecasting/benchmark/results/step1_provenance_audit.json`: provenance audit.
- `tests/test_s1_bench_significance.py`: disabled-entry-point regression test.
- Existing preservation/statistical audit outputs refreshed without model fitting.
- `agent_notes/S1_bench_step1/pytest_fixer.log`: fresh test log; task-local temporary/cache files.
- `agent_notes/FIX_REPORT.md` and `CODEX_REPORT.md`: explicitly requested reports.

Prior agents' benchmark export, notes and artifacts were retained. No data, legacy,
method, src, pilots, estimator settings, features or splits changed. No network,
installation, commit or push. Frozen benchmark artifacts match backups byte-for-byte
and git after CSV newline normalization. Published metric values were not changed;
rerun values DO differ, so preservation is NOT passed.

## Checks and remaining input

- Preservation checker: expected failure (exit 1); no tolerance relaxation.
- Statistical audit: exported probabilities match all archived rerun pooled metrics.
- Provenance audit: passed structural-function and original-score preservation checks.
- `git diff --check`: passed (line-ending notices only).
- Full-suite result is appended below; full command is in `results/README.md`.

To continue, recover the original producing-run environment/source/input provenance
and, ideally, its saved predictions. Committed source alone cannot explain drift.
No further experiment was justified without that evidence. This is a blocked step,
not a completed significance study and not a claim of tied algorithms.

Full validation: python -m pytest -q completed with 60 passed, 47 warnings in 83.27 seconds; exit 0. Task-local basetemp/cache were supplied via PYTEST_ADDOPTS. Warnings are existing NumPy timedelta deprecations.
