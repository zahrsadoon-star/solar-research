# Execution notes

Followed the parent `agent_notes/PLAN.md` methodology. The README was read as
required, so independence is of implementation, not blinding to its summary.
The independent script, configuration, and fast tests were implemented before
opening either benchmark source or benchmark result CSV. A pre-comparison copy
of the implementation is retained as `independent_frozen.py`; the run manifest
hashes that implementation and all independent output tables.

The enumerated feature list contains nineteen columns, despite being described
as eighteen. Implement all listed columns without silently dropping one.

The task's write allowlist conflicts with its requested root test/report paths.
Keep all writes inside the allowlist: use `benchmark/verify/tests/` for the test
file and this notes directory for `CODEX_REPORT.md`. Explicitly pass both the
repository and verifier test directories to pytest because repository discovery
defaults to the root tests directory. Disable bytecode and relocate pytest's
cache to this directory.

No tuning, extra seeds, network access, package installation, commits, or pushes.
The requested single fixed-seed numerical check does not satisfy the broader
research requirement for independent-run uncertainty estimates. No statistical
significance test is appropriate for this reproduction task.
