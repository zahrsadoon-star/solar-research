# Codex report — statistician review

## Work completed
- Read project guidance, decisions, benchmark, and prior task/verification notes.
- Independently recomputed all pooled predictive metrics from exported probabilities; these match the archived rerun at published precision.
- Confirmed the preservation gate fails: 135 changed metric/rank cells, maximum Brier drift 0.0013 and rank drift 3. Original published artifacts remain restored.
- Audited leakage, class imbalance and the proposed statistical protocol. Added future-perturbation, actual-label, split-boundary, class-presence and scaler-isolation tests.
- Honored the explicit stop condition: no new model seed run, inference, or winner/top-group claims.

## Files touched in this review
- tests/test_s1_bench_significance.py
- agent_notes/S1_bench_step1/statistical_audit.py
- agent_notes/S1_bench_step1/STATS_REPORT.md
- agent_notes/S1_bench_step1/CODEX_REPORT.md (this report, overwritten)
- agent_notes/S1_bench_step1/pytest_statistician.log and task-local pytest cache
- studies/S1_outage_forecasting/benchmark/results/step1_statistical_audit.json
- studies/S1_outage_forecasting/benchmark/results/step1_statistical_class_shares.csv

Earlier agent modifications were preserved. No benchmark model/settings/split edits, protected-directory edits, network access, installation, commit or push in this review. The explicit task allowlist places reports here instead of root CODEX_REPORT.md or agent_notes/STATS_REPORT.md.

## Checks
- python agent_notes/S1_bench_step1/statistical_audit.py: passed; zero archived-rerun metric discrepancies. Preservation failure is reported as data, not hidden by the audit's successful exit.
- python -m pytest -q -o cache_dir=agent_notes/S1_bench_step1/pytest_cache: 59 passed, 47 warnings in 89.36 seconds, exit 0.
- git diff --check: passed.
- Original artifacts match pre-run backup bytes; CSVs match HEAD after newline normalization, figure matches HEAD bytes.

## Open questions and unfinished scope
Resolve frozen-versus-rerun drift before proceeding. Seed stability is not established. DM/bootstrap/Holm implementation and requested inference tests are blocked by step 1, not completed. Clarify the conflict between predictions-only input and selecting algorithms from benchmark_results.csv before subsequent implementation. Statistical assumptions, selection/multiplicity limitations and the distinction between non-rejection and equivalence are documented in STATS_REPORT.md.
