**Verdict: MAJOR_REVISION**

Stopping at the preservation gate was correct and explicitly required. This is an honestly reported blocked analysis, not a completed significance study. Reviewed `agent_notes/PLAN.md` and the task-specific `agent_notes/S1_bench_step1/STATS_REPORT.md`; the root `agent_notes/STATS_REPORT.md` is absent.

**MUST-FIX**

1. **Resolve predictive drift before inference.** I independently confirmed 135 changed metric/rank cells and maximum absolute Brier drift of 0.0013. Exported probabilities reproduce the archived rerun’s Brier scores, not the frozen published scores. Establish the original code/environment provenance and explain the discrepancy. Do not change settings, widen tolerances, or select favorable reruns to recover agreement.

2. **Prevent accidental use of the historical significance implementation.** `benchmark/significance.py` still refits models, uses 168-hour blocks, fixes HAC lag at 24, omits HLN correction, compares only against the best, and estimates accuracy rather than AUC differences. Its zero-difference case also divides by zero. Clearly disable or mark this entry point as historical while the gate remains failed. The README warning alone does not prevent incompatible results being regenerated.

3. **Complete the specified analysis only after preservation is resolved.** Required outputs are absent: `significance_pairs.csv` and `significance_summary.md`. Implement the planned 21 comparisons per case, paired 24-hour bootstrap, horizon-dependent HAC lag, HLN correction, Holm adjustment, AUC intervals, and required statistical tests. Current passing export tests do not validate those methods. Their deferral is justified; their eventual completion remains necessary.

4. **Remove conflicting claims from the README.** “Tree ensembles win” overstates descriptive rankings while significance remains unresolved. The random-versus-temporal split difference does not isolate adjacency as its cause: training composition, sample sizes, and test periods also differ. Describe observed differences without causal attribution or a proven-winner claim.

**SHOULD-FIX**

- Preserve the plan’s exploratory interpretation prominently: test-selected shortlists, marginal intervals, and within-case Holm correction do not establish study-wide superiority. Non-rejection is not equivalence.
- Describe fairness narrowly. Shared features and outer splits support comparability, but fixed heterogeneous settings and MLP internal early stopping do not establish equal tuning effort or optimal performance. Equal-budget tuning and ablations belong to later approved steps.
- Document longer dependence, seasonal changes, and monthly refitting as limitations of pooled inference. Bootstrap replicates do not replace independent training seeds.
- Keep the completed-origin-hour availability assumption explicit. Inspection and passing perturbation tests found no demonstrated future-feature leakage; random-split results remain nonprospective.
- Reconcile shortlist input handling with the existing plan, which already proposes frozen CSV-derived configuration. Add verified methodological sources before publication; none were independently verified here.

**Verification:** Independent preservation and exported-Brier checks confirmed the reported blocker. Read-only pytest execution produced **44 passed, 15 setup errors**, caused by unavailable writable temporary directories. The earlier log records 59 passes; I cannot claim a fresh full-suite pass.

No files were edited. `agent_notes/REVIEW.md` was not saved because this session is read-only.