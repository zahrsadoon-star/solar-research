# Statistician review: NaN checkpoint repair

## Verified scope and root cause

Reviewed PROJECT_CONTEXT.md, AGENTS.md, prior step-2 notes, the existing uncommitted repair, tuning tests, and read-only benchmark/significance sources. Preserved prior implementation changes. Independently scanned all 12 algorithms at K=8: the only nonfinite effective parameters are XGBoost.missing for all eight candidates. This is XGBoost's legitimate NaN sentinel, not a fitted loss or pandas converting None. The original traceback matches the copy in S1_bench_step2/NANFIX.md exactly. Reproduce with S1_bench_step2/verify_nanfix_root.py; its evidence is results/tuning/statistical_audit/nanfix_root_cause.json under the benchmark directory.

The repair retains strict JSON, encodes the sentinel explicitly and restores it as NaN, while ordinary None round-trips as null. Unknown nonfinite parameters still fail. Failed fits/predictions/undefined Brier consume their original slot, retain a reason and null loss, and cannot win. Eligible finite losses minimize (loss, index); no redraw or altered search design. Only single-class AUC is nullable among metrics. All-failed units stop assembly and are rejected on resume. Schema/source provenance invalidates old checkpoints; this is intentional.

Added regression tests for NaN and both infinities in validation loss alongside a successful candidate, rejection of nonfinite non-sentinel parameters, and either single-class AUC outcome. Existing tests cover failed-candidate checkpoint/resume, selection ties, None restoration, float32 metrics and JSON reconstruction, boundaries, future-feature perturbations and scaler isolation.

## Fresh numerical and seed verification

Re-ran S1_bench_step2/statistical_audit.py with fixed seeds 42 and 43, BG h=1, default LR/RF, all nine outer months. This smaller diagnostic changes random-state parameters only; it does not change production seeds or candidate draws. Saved metrics, predictions, split counts and differences are in benchmark/results/tuning/statistical_audit/. Log: S1_bench_step2/nanfix_seed_audit.log.

All stored pooled metrics recompute within 5.551115123125783e-17. Seed-42 probabilities reproduce stored K=1 results within 1.1102230246251565e-16 (LR) and 5.551115123125783e-16 (RF). LR metrics are unchanged between seeds; RF Brier increases by 0.0002611689645984905. Other RF metric differences are in seed_43_minus_42.csv. These small differences support limited default-model stability only. No equivalence margin/test was prescribed; two seeds do not establish tuned-model or cross-site robustness. Historical full-precision LR versus rounded baseline differences and the unexplained RF baseline discrepancy remain unresolved; no tolerance was relaxed.

## Leakage, imbalance and inference

Both origins and target times are purged at inner and outer training boundaries. Features use observations through the completed origin hour and known target calendar values; future perturbation and training-only scaler tests cover this. Actual availability of completed-hour metering remains an assumption. MLP early stopping and SVM calibration retain internal non-temporal splitting within training data; no claim of entirely forward internal validation is justified.

Every inspected inner/validation/outer/test split contains both classes. Test prevalence varies from 0.1545698924731182 to 0.803763440860215 for BG and from 0.0268817204301075 to 0.3172043010752688 for KR. Class weighting/resampling and threshold tuning are absent by the frozen design. Accuracy alone is therefore insufficient; Brier and minority-class metrics need joint interpretation. AUC null handling avoids an invented score but does not solve imbalance.

No significance tests were performed for this repair or seed diagnostic. Monthly folds share training observations and hourly losses are dependent; folds are not independent runs. Read-only review confirms Step 1 uses normal-approximation Diebold-Mariano with HAC lag 24, Holm within each case, and 168-hour moving-block bootstrap with 2,000 replicates. Within-case correction does not cover the combined study or same-data top-model selection. Bootstrap intervals are pointwise. Seasonality can challenge dependence/stationarity assumptions; fixed lag/block choices have not been empirically validated here. Zero long-run variance is unguarded in dm_test. These are existing limitations, not newly tested significance findings; Step 1 conclusions do not transfer to tuned models.

## Bounded probe and checks

A fresh three-minute full-command probe used the prescribed sites/horizons, K=8 and four workers. It ran concurrently with verification jobs, so checkpoint throughput is not a runtime benchmark. Its retained log is S1_bench_step2/nanfix_probe/probe.log; prior experimenter evidence is preserved separately. Scratch checkpoints are deleted by the harness after validation. Exact completion/check counts are recorded in the final CODEX_REPORT.md.

No benchmark.py, significance.py, legacy/ or data/ edits; no network, installation, commit or push. No full-grid completion or tuned ranking claim.

Fresh outcomes: 180.0058246999979 seconds; 59 completed units validated, zero failed units, 63 strict-JSON checkpoint/manifest files, empty stderr. Deliberate termination stopped parent and inherited workers; only probe.log remains in scratch. Full pytest: 107 passed, 107 deprecation warnings. Targeted Ruff: passed. Full grid intentionally not completed.
