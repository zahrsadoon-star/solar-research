# Fix report — 20261122-s1-bench-step2-finish

Status: **partially resolved; acceptance blocked**. No full grid, installation,
network access, commit or push. Work started from an already dirty working tree;
the resumable implementation, deleted partial outputs and earlier audit artifacts
were inherited, not newly created by this fixer pass.

## MUST-FIX disposition

1. **Resolved.** Benchmark README replaces unsupported statistical equivalence,
   tie and best-choice claims with qualified descriptions of the tested default
   comparisons. Explicitly excludes inference about tuned or untested models.
2. **Resolved.** Reports verify the exact complete site/horizon/algorithm design
   before making full-benchmark statements. Subsets are labelled. Top-two sets
   include all exact ties at the second-place boundary. Regression tests cover
   subset reporting and boundary ties.
3. **Unresolved acceptance decision, documented.** LR's literal 1e-9 comparison
   fails for all six metrics despite four-decimal agreement. RF passes the
   prescribed Brier tolerance; its historical discrepancy remains unexplained.
   No threshold was silently changed and no full-precision baseline invented.
   The lead was asked for a precision criterion; absent an explicit decision,
   the literal gate remains failed. Reports warn that small differences cannot
   establish improvements beyond rounding and baseline reproducibility.
4. **Resolved.** Production assembly rebuilds sanity comparisons only after
   read-only validation of all underlying sanity checkpoints against current
   inputs, ordered candidates, source and environment. Missing/incompatible
   evidence is explicitly unavailable. A stale CSV cannot bypass validation.
5. **Blocked.** The first merge attempt failed because ORIG_HEAD.lock is outside
   the writable worktree. No merge occurred. HEAD remains 50af4bf; origin/main
   is 78e65c3218695aa981f91573dafdf472b93f7c55. Repository-wide Ruff reports 397
   violations, including protected legacy files and out-of-scope code. No lint
   rules were disabled and no protected code changed. The lead must merge and
   resolve the repository gate through its authorized workflow, then rerun
   checks against the merged revision. Scoped success does not close this gate.

## Changes and evidence

- `tuning.py`: subset/tie reporting and validated sanity assembly.
- `tests/test_s1_bench_tuning.py`: three regressions for those corrections;
  retains candidate identity, temporal boundaries, selection, prediction and
  interrupted/resumed-run equality tests.
- Benchmark `README.md`: qualified Step 1 inference.
- `agent_notes/PLAN.md`: self-contained frozen search spaces and current CLI
  status, removing the inherited read-only role narrative and self-reference.
- `RUN.md` and `write_run_notes.py`: full command, frozen K=8, sequential timing
  estimate and explicit unresolved acceptance gates.
- `results/tuning/README.md`: reproduction, artifact status, findings and limits.
- Fresh K=1 sanity artifacts and `SANITY.md` generated from current source.
  Old sanity evidence is labelled historical in
  `historical_sanity_before_fixes/`; deletion was policy-blocked, so it was safely
  archived within the repository. Production does not load it.
- `CODEX_REPORT.md`: overwritten with this pass's outcome.

The full-grid estimate remains the frozen probe-derived 30222.667541 seconds
(about 8.40 hours sequential), not a measured parallel runtime. K=8 is retained
because no K in the prescribed range meets the target. Equal candidate counts
do not imply equal compute or search coverage. No tuned robustness claim follows
from the inherited default-model diagnostic.

## Checks

- `python -m pytest -q` using venv312, repository-local cache/temp directories:
  **90 passed**, 89 warnings, 90.11 seconds (`S1_bench_step2/pytest_fixer.log`).
- Repository-wide `ruff check`: **FAILED, 397 violations**
  (`S1_bench_step2/ruff_fixer_repository.log`).
- Scoped Ruff for tuning.py and tuning tests: passed.
- `git diff --check`: passed; Git reports line-ending conversion notices.
- Protected-path diff (`legacy/`, `data/`, benchmark.py, significance.py): empty.
- Only BG h=1 K=1 LR/RF across nine outer folds was rerun. See
  `S1_bench_step2/sanity_fixer.log`, `SANITY.md`, and current sanity checkpoints.

## Remaining work

Lead: resolve MUST-FIX 3 and 5, then run the full command in RUN.md. A tiny
CLI/process-pool integration test and richer failed-fit warning context remain
SHOULD-FIX suggestions, not completed here. Multi-seed tuning, ablations,
temporal sensitivity, dataset permission and publication-overlap verification
remain outside this continuation. Do not declare full acceptance yet.

Resume verification: repeated the same sanity CLI with only DeprecationWarning display suppressed; Python exit code 0, no completed-unit fit messages, and final artifacts assembled. See agent_notes/S1_bench_step2/sanity_resume_fixer.log (empty successful output). The first invocation completed all 18 units and artifacts; PowerShell wrapped its deprecation-warning stderr as NativeCommandError. No Python traceback occurred.
