# CODEX_REPORT — fix5 S1 fixer/documenter

Status: PARTIAL. Review MUST-FIX items 3 and 4 are repaired; item 5 has a complete
available failure inventory. Integration and full acceptance remain blocked.

## Work and files touched in this follow-up

- `agent_notes/S1_bench_step1_fix2/audit_inputs.py`: new fixed-revision source/score
  loader and data/software provenance.
- `statistical_audit.py`, `training_seed_audit.py` in that directory: use pinned
  inputs and record provenance; remove unsupported prespecification claim.
- `studies/S1_outage_forecasting/benchmark/significance_check/check.py` and generated
  `COMPARISON.md`: distinguish core frozen analysis from supplementary refitting.
- `studies/S1_outage_forecasting/benchmark/results/significance_check/`: regenerated
  primary/audit outputs and added README with reproduction and limitations.
- `agent_notes/PLAN.md`: retrospective protocol deviation, timing and narrow scope.
- `agent_notes/S1_bench_step1_fix2/FAILURES.md`: all omitted setup node IDs/causes,
  current requested-basetemp outcome and merge failure; added logs and preservation
  verification in the same directory.
- `agent_notes/FIX_REPORT.md` and this report: review disposition and acceptance.

Existing uncommitted repairs and notes were preserved. No commit, push, network,
installation, legacy/ edit or data/ edit. No test/tolerance changes in this follow-up.

## Checks and findings

- Required external-basetemp pytest: 63 passed, 15 setup errors (permission denied).
- Full pytest with workspace basetemp: 78 passed, 72 dependency warnings, no skips.
- Scoped Ruff on modified implementation/tests/audits: passes.
- Repository-wide Ruff: 834 diagnostics; includes protected legacy and out-of-scope
  files. These were not suppressed or modified.
- `git diff --check`: passes, line-ending warnings only.
- Ten existing published result hashes unchanged. Refreshed integration manifest
  truthfully reports unmerged main and 92 absent/nonmatching source/result entries.
- Comparison agrees for three cases; BG 1 h retains Gradient Boosting unlike
  cec3552. No equivalence or broad superiority claim. April KR recall/F1 stay zero.

## Unresolved requirements

Git merge fails creating shared ORIG_HEAD.lock outside the writable repository.
The prescribed pytest temporary path is likewise outside the permitted workspace.
No permission bypass was attempted. Integration and post-merge acceptance need
an appropriately writable environment. Repository-wide lint needs the lead to
reconcile the permitted repair scope with diagnostics in protected files.
Earlier diagnostic copies remain after the prior documented cleanup rejection;
do not stage those directories. See agent_notes/FIX_REPORT.md for full details.

Both supplementary audits completed with pinned provenance. Verified seed-42 replay,
no changed pair decisions for seed 43, current local hashes, all 16 April training
rows and the zero KR recall/F1 results. Numerical conclusions remain unchanged.
