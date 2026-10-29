# Integration status for the independent check

`git merge --no-commit origin/main` failed before merging because Git could not
create `D:/SolarProject/solar-research/.git/worktrees/fix-20261023-s1-bench-step1-significance/ORIG_HEAD.lock`
(permission denied). The shared Git metadata is outside this task's writable root.
No network access, commit, push, or alternate Git metadata workaround was used.
The lead must complete the actual merge in an environment with access to that
metadata; the working-tree preparation is not a completed merge.

The three specified benchmark source/documentation files and every results file
present on local `origin/main` were restored directly from its Git blobs, without
displaying, importing, or inspecting the contents of `significance.py`.
`main_blob_verification.json` records byte-for-byte comparison results. This
restoration can appear as line-ending changes against this branch's HEAD.

The Windows rerun predictions, preservation JSON/CSV and `step1_rerun/` were moved
to `windows_rerun/`; predictions fit the permitted archive size and were retained.
The task's CatBoost information directory was removed. No model was refitted.

The pre-existing `agent_notes/PLAN.md` modification was supplied with the task and
left untouched. The current lead decision supersedes older preservation blockers.
In particular, `benchmark/results/README.md` is a branch-only historical document
(absent from local origin/main), and remains unchanged under the allowed-path
restriction. Its blocking claims do not describe this independent check. Older
audit scripts still refer to the pre-move artifact paths; this task does not rerun
those scripts. Use `write_repro_note.py` and `significance_check/check.py` instead.

The old `tests/test_s1_bench_significance.py` also refers to pre-move predictions
and asserts that main's significance entry point is disabled. This conflicts with
the requested restoration. Updating that file requires an exception to the
explicit allowed-change list; this was requested through the clarification tool.
Executing its obsolete disabled-entry-point test against restored main could
trigger model refitting and overwrite primary artifacts, so that test must not
be executed unchanged. Validation limitations are recorded in CODEX_REPORT.md.
