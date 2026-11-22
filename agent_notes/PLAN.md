**Protocol for `agent_notes/PLAN.md` — task `20261122-s1-bench-step2-nanfix`**

## Status update — 2026-11-22 fixer pass

The protocol below is preserved as planning history from the earlier read-only
session on 2026-11-22. Its statements about unverified provenance and unrun checks
describe that session, not the current repair. The implemented root cause is
XGBoost's `missing` NaN sentinel in manifest effective parameters. See
`S1_bench_step2/NANFIX.md` for the copied traceback, schema and verification
history, and `FIX_REPORT.md` for the latest checks. The current REVIEW.md has no
MUST-FIX items within this repair's scope. Publication limitations remain open.

Historical session statement: Not saved: this session is read-only and explicitly prohibits edits. No implementation, tests or probe were run. The external traceback was not read because work is restricted to this repository.

1. **Scope and hypothesis**

   Repair checkpoint serialization and failure handling while preserving the frozen experiment: BG and KR, horizons 1 and 6 hours, twelve existing algorithms, K=8, unchanged search spaces and candidate ordering. Do not modify `benchmark.py`, `significance.py`, `legacy/` or `data/`.

   The task hypothesis is that schema-aware serialization and explicit candidate failure handling permit strict-JSON checkpointing and deterministic resume without changing valid candidates’ selection or predictions.

   Falsification: any invalid JSON, changed valid configuration, selected failed candidate, accepted invalid prediction, incompatible checkpoint reuse, or resume discrepancy falsifies that claim. Surviving the three-minute probe provides limited execution evidence, not proof that the full grid succeeds.

2. **Data, targets and availability**

   Preserve `benchmark.load`, `features` and `tuning.case_data`. Use the existing BG and KR source workbooks and assigned hourly 2018 chronology; exclude BS.

   For grid energy \(G_t\), in kWh:
   \[
   O_t=\mathbf1(G_t=0),\qquad Y_{t,h}=O_{t+h}.
   \]
   This is a metering proxy for grid unavailability at a future hour. It is not an “any outage within the horizon” target.

   Preserve all nineteen features and the common eligibility mask. Forecast origin \(t\) assumes the current hour’s measurements are complete. Updating observed history during a test month is permitted; refitting within that month is not.

3. **Temporal splits and selection**

   For test-month start \(a_m\), preceding-month start \(v_m\), and next-month start \(a_{m+1}\), intersect these sets with eligible rows:
   \[
   T_m=\{t:t<a_m,\ t+h<a_m\},
   \]
   \[
   E_m=\{t:a_m\le t<a_{m+1}\},
   \]
   \[
   I_m=\{t\in T_m:t<v_m,\ t+h<v_m\},
   \qquad
   V_m=\{t\in T_m:v_m\le t<a_m\}.
   \]
   Evaluate April–December; April validates on March. These definitions match `tuning.split_masks`.

   Fit candidates and preprocessing only on \(I_m\); select using Brier loss on \(V_m\). Among eligible candidates, minimize `(validation_brier, candidate_index)`, preserving first-index exact ties. Refit the selected estimator on \(T_m\), then predict \(E_m\). Test membership follows forecast-origin month; unavailable year-end targets are excluded.

4. **Seeds, budget and baselines**

   Preserve seed 42, benchmark estimator seeds, and a separate `numpy.random.default_rng(42)` for each algorithm. Candidate 0 retains benchmark defaults; candidates 1–7 are the existing draws with replacement. Reuse the same ordered prefix across sites, horizons and folds. Duplicates and failed candidates consume budget; never replace them with additional draws.

   Compare against each algorithm’s stored default results. Retain always-no-outage, persistence and same-hour-last-seven-days references. Do not rerun random splits.

   This task has one seed, not multiple independent runs. Do not describe monthly folds or repeated execution as independent replications.

5. **Metrics**

   Pool outer predictions within each site–horizon–algorithm case. Do not average monthly metrics. With \(\hat y_i=\mathbf1(p_i\ge0.5)\):
   \[
   B=\frac1N\sum_i(p_i-y_i)^2,\qquad
   A=\frac1N\sum_i\mathbf1(\hat y_i=y_i),
   \]
   \[
   P=\frac{TP}{TP+FP},\quad
   R=\frac{TP}{TP+FN},\quad
   F_1=\frac{2TP}{2TP+FP+FN}.
   \]
   Preserve the benchmark’s zero-denominator convention for precision, recall and F1.
   \[
   \mathrm{AUC}=
   \frac{\sum_{i:y_i=1}\sum_{j:y_j=0}
   [\mathbf1(p_i>p_j)+\tfrac12\mathbf1(p_i=p_j)]}
   {N_+N_-}.
   \]
   AUC is undefined when either class is absent; record null with a reason. Brier remains defined on a nonempty single-class evaluation set with valid probabilities. An undefined ancillary AUC must not invalidate an otherwise valid Brier candidate.

   These definitions correspond to `benchmark.scores` and `tuning.select_config`.

6. **Root-cause evidence and nullable schema**

   Identify the exact nonfinite field path, originating value/type, and producing operation before implementing a fix. The existing manifest serializes all effective estimator parameters before fitting; therefore parameter metadata is a plausible source. **Historical planning status: the actual offending field remained unverified at that time; see the status update above for the verified cause.**

   Apply these rules:

   - Fit/prediction failure or undefined validation Brier: record candidate index, original parameters, explicit failure status, `loss: null`, stage and reason; exclude from selection.
   - All candidates ineligible: record a failed unit and prevent a complete-grid summary. Do not silently select candidate 0.
   - Selected outer refit failure: record failure; do not silently substitute another candidate.
   - Legitimate Python `None`: encode as JSON null and restore as `None`.
   - Estimator-specific NaN sentinels: preserve their semantics through explicitly typed metadata and reconstruction rules. Never equate them automatically with Python `None`.
   - Undefined ancillary metrics: permit null only at declared metric fields, with an explanation.
   - Predictions, identities, selected successful losses and required finite metadata: reject nonfinite values.

   Keep `allow_nan=False`. Do not apply blanket NaN/inf replacement. Canonical hashing and writing must use the same schema-normalized representation. Version changed checkpoint semantics and reject incompatible earlier checkpoints.

7. **Required verification**

   The implementer must demonstrate:

   - A fixture containing a failing candidate, successful candidates and an undefined ancillary metric writes strict JSON; resume excludes the failed candidate and preserves the correct winner.
   - Exact ties still choose the lowest eligible index.
   - All-candidate failure prevents successful completion.
   - `max_depth=None` survives serialization, loading and estimator reconstruction as `None`.
   - Any identified NaN sentinel retains its original estimator semantics.
   - NaN/inf predictions and nonnullable fields remain rejected.
   - Resumed and uninterrupted runs agree on candidate records, selected configurations, prediction rows and probabilities; completed units are not fitted again.
   - Existing leakage and provenance checks remain intact.

   Run `python -m pytest -q` and ruff on `tuning.py` and its tests using the prescribed environment, without network or installation.

   Run the specified BG/KR, horizons 1/6, K=8, four-worker command with scratch output under `agent_notes/S1_bench_step2/nanfix_probe/`. Stop after 180 seconds, including its worker processes. Record actual elapsed time, checkpoint progress, errors and termination outcome. Validate completed checkpoints before deleting scratch artifacts, retaining a short log. Do not claim full-grid completion.

8. **Inference and threats to validity**

   No statistical test is authorized for this repair. Existing significance results do not transfer to tuned predictions. Preserve descriptive comparisons and the lead’s rule that differences below approximately 0.005 Brier must not be called improvements.

   Main threats are outcome-dependent candidate exclusion, unequal effective search coverage after failures, silent parameter-semantic changes, missing difficult folds, stale checkpoint reuse, execution nondeterminism, and overinterpreting the short probe. Report failures by candidate and fold.

   Existing study limitations remain: proxy labels, one year per site, seasonal drift, dependent monthly folds, overlapping training windows, prior inspection of the test year, and internal MLP/SVM splitting. The older study plan’s broader inference and dispatch ambitions do not expand this repair’s scope.
