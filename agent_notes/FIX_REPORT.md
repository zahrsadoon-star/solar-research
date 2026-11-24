# Fix report — fix5 S1 significance review

Status: PARTIAL; acceptance is not complete. No commit or push was made.

## Review disposition

1. MUST-FIX main integration: **blocked**. Retried `git merge --no-commit
   --no-ff main`; Git cannot create shared `ORIG_HEAD.lock` outside the writable
   workspace. No metadata workaround was used. Regenerated the integration
   manifest: main is not an ancestor and 92 source/result entries do not match
   or are absent. Ten pre-existing published branch artifacts remain byte-for-byte
   unchanged (`S1_bench_step1_fix2/fixer_preservation.json`). This does not certify
   preservation of all main results. Merge in a writable environment, preserving
   main's published results, remains necessary.
2. MUST-FIX acceptance: **blocked in part**. Required external-basetemp run:
   63 passed, 15 setup errors, all permission errors on
   `D:\SolarProject\tmp\pytest\fix2sig`. Full suite using a repository-local
   basetemp: 78 passed, 72 dependency warnings, no skips. Scoped Ruff passes;
   full `python -m ruff check` has 834 diagnostics, including protected legacy
   files and other files outside this task's permitted scope. No blanket lint
   exclusions or out-of-scope source repairs were introduced. Full acceptance
   requires a lead decision reconciling lint scope with protected files.
3. MUST-FIX historical audit inputs: **fixed**. Added `audit_inputs.py`; the
   supplementary metric audit reads scores from full revision
   cec3552fc9d739c3c08204d7eb70c22c84cbd70f, and the training audit executes source
   from that same revision while resolving input data within this repository.
   Both summaries record source/data hashes, Python/platform and estimator versions.
   The historical score table and training source match the prior working-tree
   versions modulo Git line endings; settings were not changed.
4. MUST-FIX protocol deviation: **fixed**. PLAN.md now documents the retrospective
   2026-11-24 amendment, its timing after the supplementary run, the April-only
   RF/Extra Trees scope and lack of evidence of prespecification. Removed that
   claim from audit docstrings. Generated COMPARISON distinguishes the core
   no-refitting check from the supplementary refits and expressly states that
   this does not meet full-benchmark independent-training-run requirements.
5. MUST-FIX failure inventory: **fixed to available evidence**. FAILURES.md now
   lists all 15 statistician setup errors and all 15 current setup errors with
   node IDs and exact causes, separately from the original five failures. No
   post-merge result is claimed because the merge did not occur.

## Documentation and findings

Added `studies/S1_outage_forecasting/benchmark/results/significance_check/README.md`
with commands, statistical procedure, seeds, provenance, findings and weaknesses.
Regenerated the primary comparison and output manifest. BG 1 h differs (Gradient
Boosting retained); the other three cases agree with cec3552. RF/Extra Trees
non-rejection does not establish equivalence. April KR recall/F1 remain zero.
The supplementary bootstrap audit is same-implementation replay, not an independent
implementation or a dependence-sensitivity experiment. Longer-block/HAC sensitivity,
historical leakage provenance and source verification remain limitations.

Earlier disposable baseline_repository and temporary directories remain. A prior
agent's deletion was rejected by automatic approval review (recorded in FAILURES.md);
no workaround was attempted here. They must not be staged as deliverables.

## Validation evidence

All new logs are in `agent_notes/S1_bench_step1_fix2/`:
- `fixer_requested.log` / XML: prescribed-basetemp failures.
- `fixer_pytest.log` / XML: 78 passed with workspace basetemp.
- `fixer_ruff_scoped.log`: modified code/tests/audit scripts pass.
- `fixer_ruff_repository.log`: 834 full-repository lint diagnostics.
- `fixer_check.log`, `fixer_training.log`, `fixer_statistical.log`: rerun analyses.
- `fixer_preservation.json`: protected branch result hashes unchanged.

`git diff --check` passes with line-ending warnings only. No tests were removed,
skipped or loosened in this follow-up. No legacy/data edits, network access or
package installation occurred. Existing uncommitted work was retained.

Final audit completion: the pinned bootstrap audit finished successfully; seed 42
reproduces saved results and seed 43 changes no pair decisions. Verified all recorded
local input/source hashes against current bytes. The April audit retains all 16
rows, and KR recall/F1 are zero in every retained row. Numerical conclusions remain
unchanged after pinning historical source and score inputs.
