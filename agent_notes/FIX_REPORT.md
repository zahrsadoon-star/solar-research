# Fix report — independent check complete; integration and test exception pending

## Review disposition

- MUST-FIX 1 remains blocked by filesystem permissions. A fresh `git merge origin/main`
  failed creating ORIG_HEAD.lock in shared Git metadata outside the writable worktree.
  No merge, commit or push occurred. Copying protected blobs is not integration.
  The lead must merge with writable Git metadata and keep the specified main files.
- MUST-FIX 2 awaits an explicit allowed-path exception. The obsolete
  `tests/test_s1_bench_significance.py` is outside the task's allowed list. Requested
  authorization to update archive paths and replace the execution test with a
  nonexecuting blob-preservation check. The concrete patch is already available at
  `agent_notes/S1_bench_step1/pending_test_update.patch`. Do not execute the obsolete
  entry-point test: it can run primary analysis and overwrite protected artifacts.
  An unfiltered passing full suite is NOT claimed.
- MUST-FIX 3 resolved in the permitted generated COMPARISON.md: explicitly supersedes
  the old preservation gate and unsupported equivalence, superiority and causal
  claims. Protected primary documents remain unchanged; lead correction is pending.

## Work performed

Reviewed the existing independent implementation and original export schema without
reading or executing main's significance.py. Re-ran the frozen 24-hour, 2000-draw,
seed-42 analysis without refitting models. Retained all-pairs DM/HAC/HLN, within-case
Holm, Brier intervals and AUC intervals. No reference forecasts exist.

Updated the comparison generator with baseline fairness, single-training-seed limits,
future equal-budget tuning and ablations, longer dependence and seasonal assessment,
and unverified methodological sources. Replaced hard-coded integration status with
actual Git ancestry and protected-blob identity checks. Added significance_check/README.md
with reproduction and findings because benchmark/results/README.md is outside allowed
new-output paths and must not be rewritten here. Regenerated the accepted drift note;
no settings changes or training reruns were made to recover platform agreement.

Results agree with main's group membership in three cases; BG 1 h retains Gradient
Boosting. Non-rejection is not equivalence. The saved forecasts support only exploratory
within-case inference. Windows rerun artifacts remain archived separately.

## Checks and handoff

- Independent tests: 11 passed, 19 existing NumPy timedelta warnings.
- git diff --check: passed (line-ending notices only).
- data/, legacy/, method/ and src/: no working-tree changes.
- Full-suite acceptance requires the test-file exception and subsequent unfiltered
  `python -m pytest -q`; no deselection-based pass is claimed.
- Fresh generated manifest records actual ancestry and primary preservation.

The pending test-file exception is necessary because the task explicitly restricts
allowed paths; the review requests that exception. The merge needs an environment
with writable shared Git metadata, which this session cannot grant or bypass.

Fresh full-suite collection: `python -m pytest -q --collect-only` succeeded with
71 tests collected and one existing warning. Collection is not test execution and
does not satisfy the unfiltered full-suite requirement.
