**Verdict: MAJOR_REVISION**

The nested temporal splits and checkpoint validation appear sound on inspection. I found no demonstrated future-label leakage or outcome-driven candidate selection. However, reporting defects and unresolved acceptance gates prevent approval.

**MUST-FIX**

1. **Remove unsupported equivalence claims.** The benchmark `README.md` calls models “statistically equivalent” and “statistically tied.” Nonsignificant difference tests establish neither equivalence nor a best-choice recommendation. Replace these statements with qualified descriptions of the tested comparisons. Step 1 inference must not support tuned-model claims.

2. **Correct subset and tie reporting.** In `tuning.py::reports`, `head(2)` determines dominance even for the two-model sanity run. The saved sanity summary consequently discusses RF/Extra Trees dominance despite never evaluating Extra Trees. Restrict full-benchmark conclusions to the complete requested design, label subsets explicitly, and handle ties at the second-place boundary without arbitrary membership.

3. **Resolve the reproduction gate explicitly.** All six literal LR comparisons fail `1e-9`, although four-decimal agreement holds. The lead must document a precision-compatible acceptance criterion or supply a verified full-precision baseline; rounded agreement cannot silently replace the gate. RF passes its prescribed Brier tolerance, but its historical discrepancy remains unexplained. Small tuned-minus-default differences must not be interpreted as improvements beyond baseline reproducibility and rounding uncertainty.

4. **Validate the sanity evidence used during production assembly.** `tuning.py:479` imports an existing `sanity.csv` without checking its provenance against the production inputs, source and environment. Validate the underlying sanity checkpoints before incorporating that evidence, or clearly mark it as historical and unvalidated.

5. **Close the execution requirements before declaring completion.** The merge remains pending and the recorded repository-wide Ruff check reports 397 violations. Scoped lint success does not satisfy the stated repository-wide gate. Resolve these through the lead’s authorized workflow, then record checks against the merged revision. Do not modify protected files merely to clear lint.

**SHOULD-FIX**

- Add a tiny CLI/process-pool integration test. The existing resume test exercises `evaluate()` with one LR candidate; it does not verify the advertised multi-process command and final artifact assembly.
- Surface convergence warnings by candidate and fold. Successful-unit checkpoints retain warning text, but failed fits can lose captured warnings before publication.
- Make `PLAN.md` self-contained: its frozen-space reference points back to itself, and its statement that CLI flags are unimplemented is stale.
- Describe fairness as **equal candidate counts**, not equal optimization opportunity or computation. Preserve duplicate counts and the frozen search spaces.
- Before journal-level robustness claims, separately preregister broader seed checks, feature ablations and temporal sensitivity analyses. The two-seed default diagnostic cannot establish tuned-model robustness.
- Verify dataset attribution, permission and prior-publication overlap before manuscript submission. Those external sources were not verified in this offline review.

**Verification:** Fresh scoped Ruff and `git diff --check` passed; protected-file diffs were empty. Existing logs report 87 passing tests. I did not rerun the write-producing test suite or launch experiments.

This review was **not saved to `agent_notes/REVIEW.md`** because this assignment and sandbox are read-only. No files were edited.