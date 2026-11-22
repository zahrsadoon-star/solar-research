# Step 2 tuning: execution status and reproduction

The production grid has **not completed**. There are no production tuned-model
findings to report. The historical restricted K=1 sanity run covers:
BG, horizon 1 hour, Logistic Regression and Random Forest, April–December 2018.
See [sanity/tuning_summary.md](sanity/tuning_summary.md) for computed comparisons
and [sanity/sanity.csv](sanity/sanity.csv) for full-precision differences. Those
checkpoints predate the NaN repair and must not be treated as validated against
the current source. The new execution evidence is a bounded full-command probe,
described below; it is not a completed experiment.

## NaN repair and bounded reproduction

The manifest crash came from `effective_parameters.XGBoost[i].missing`, the
estimator's NaN sentinel. Schema 2 represents that sentinel with typed JSON
metadata and restores it to NaN; Python `None` remains JSON null. Strict
`allow_nan=False` remains enabled. Failed fits or undefined validation losses
record `status=failed`, `loss=null`, stage and reason. They consume their original
candidate slot and are excluded from minimum-Brier selection; exact ties retain
the first eligible index. No candidates are redrawn. An all-failed unit or failed
selected outer refit blocks assembly. Single-class AUC is null with an explicit
reason; predictions and required finite fields cannot become null.

Run the bounded reproduction from the repository root with an empty scratch
directory (archive its existing `probe.log` first):

```powershell
& D:\SolarProject\venv312\Scripts\python.exe agent_notes/S1_bench_step2/run_nanfix_probe.py
```

The harness runs the following command with the installed interpreter and stops
the parent and inherited workers at 180 seconds using a Windows Job Object:

```text
python -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG KR --horizons 1 6 --K 8 --n-jobs 4 --out agent_notes/S1_bench_step2/nanfix_probe/
```

It validates completed checkpoints and deletes scratch output except `probe.log`.
See [NANFIX.md](../../../../../agent_notes/S1_bench_step2/NANFIX.md) and
[FIX_REPORT.md](../../../../../agent_notes/FIX_REPORT.md) for measured outcomes.
The probe uses seed 42 and unchanged search spaces and temporal selection.
It supplies no independent replication or inferential test. Surviving this window
does not establish full-grid success, later-fold stability or tuned superiority.
Candidate failures and distinct configurations must be reported by algorithm and
fold before interpreting a completed grid; equal attempts do not imply equal
successful or distinct coverage.

## Reproduce

From the repository root, using the installed offline environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
& D:\SolarProject\venv312\Scripts\python.exe -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG --horizons 1 --K 1 --n-jobs 1 --out studies/S1_outage_forecasting/benchmark/results/tuning/sanity --sanity
```

Repeat the identical command to validate and reuse completed units. A source,
input, environment or candidate change rejects old checkpoints; preserve them
as historical evidence and use a fresh directory for an intentional rerun.
Production assembly validates sanity checkpoints against current provenance and
recomputes the comparison; it does not trust an existing sanity CSV alone.

The full-grid command and frozen timing rule are in
[RUN.md](../../../../../agent_notes/S1_bench_step2/RUN.md). The current review
accepts the serialization repair only; earlier baseline and publication gates
are separate unresolved matters. K=8 is the
minimum prescribed candidate count: no allowed K meets the runtime target.
[timing_estimate_20261122.json](timing_estimate_20261122.json) gives the sequential
estimate from [timing_probe_20261116.csv](timing_probe_20261116.csv). Parallel wall
time has not been measured; only the bounded full-command probe was run for this repair.

## Findings and limitations

LR matches the stored metrics after four-decimal rounding but fails the literal
1e-9 gate for every metric. That gate remains unresolved pending the lead's
explicit precision criterion or a verified full-precision baseline. RF passes
the prescribed Brier tolerance, but its discrepancy from the historical default
run remains unexplained. Small tuned-minus-default differences must not be
described as improvements beyond rounding and reproducibility uncertainty.

The sanity run evaluates only two algorithms and cannot establish RF/Extra Trees
dominance. Rankings are descriptive; second-place boundary ties include every
tied member. Equal candidate counts do not imply equal computation or equal
search coverage. Seed 42 is fixed; this is one realization, not independent
multi-seed evidence. No inferential test was run in this continuation, and Step 1
default-model inference does not transfer to tuned models.

Nested training uses the preceding month for validation, purges both origin and
target boundaries, selects minimum validation Brier with first-index tie breaks,
and refits on outer training rows. Metrics pool outer predictions. Remaining
weaknesses include metering-proxy labels, one year per household, dependent
hourly observations and folds, seasonal drift, prior test-year inspection, and
benchmark-internal MLP/SVM splitting. Dataset permission and publication overlap
still require external verification before manuscript submission.

## Artifact status

- `sanity/`: historical restricted run, with atomic checksummed unit checkpoints and
  the four assembled artifacts, metrics, warnings and execution metadata.
- `historical_sanity_before_fixes/`: obsolete pre-fix source fingerprint; never
  use its summary as current evidence.
- `statistical_audit/`: inherited default-model diagnostic, not a tuned-model run
  and not evidence of tuned multi-seed robustness.
- Old logs, worker diagnostics, `budget.json`, `configurations.json` and
  `source_hashes.json`: provenance of the interrupted run, not completed results.
  Its cumulative partial prediction/configuration files were removed.
- Future production outputs: `tuned_results.csv`, `selected_configs.csv`,
  `tuned_predictions.csv.gz`, `tuning_summary.md`, assembled only after every
  requested checkpoint validates.
