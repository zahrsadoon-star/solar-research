# Full-grid handoff

Run from the repository root, after the lead resolves the pending merge of origin/main.
The required merge was attempted first but Git could not create ORIG_HEAD.lock in the
main repository's worktree metadata outside the writable sandbox. No merge occurred.
No commit or push was made. PLAN.md now records the frozen spaces explicitly and describes the implemented CLI.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
& D:\SolarProject\venv312\Scripts\python.exe -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG KR --horizons 1 6 --K 8 --n-jobs 4 --out studies/S1_outage_forecasting/benchmark/results/tuning
```

Repeat the identical command after an interruption. Completed compatible units are
validated and skipped. Do not use --run-only; it has been replaced by automatic resume.
--n-jobs is concurrent case processes; it does not change candidate estimator parameters.
BLAS/OpenMP and LOKY CPU limits are one per worker; explicitly parallel estimators and
CatBoost can manage extra threads. The full process-pool grid has not been executed
in this session. CLI parsing/help and the sanity command were exercised.

## Frozen budget and runtime

K=8; feasible=False. The historical probe gives
30222.667541 seconds = 503.71 minutes = 8.40 hours
for the sequential estimate including overhead, refits and sanity. No K in [8,20]
meets the 80-minute target, so the rule retains the minimum K=8. K=20 estimates
18.26 hours. This is not a measured parallel
wall time or an upper bound; four workers do not imply a guaranteed fourfold speedup.
Allow a long unattended run. The native execution limits differ from the historical
probe; actual timing must be recorded rather than asserted in advance.

Formula: `1.25 * (9*(K+2)*sum(max probe seconds per case/model) + 27*sum(BG1 LR/RF max seconds))`.
25% overhead; outer refit allowance twice late inner fit; includes sanity cost. Timing inputs: `results/tuning/timing_probe_20261116.csv`
relative to the benchmark directory. Machine-readable recomputation:
`results/tuning/timing_estimate_20261122.json`. Reproduce this note with
`python agent_notes/S1_bench_step2/write_run_notes.py`.

## Sanity only

```powershell
& D:\SolarProject\venv312\Scripts\python.exe -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG --horizons 1 --K 1 --n-jobs 1 --out studies/S1_outage_forecasting/benchmark/results/tuning/sanity --sanity
```

K=1 checkpoints and artifacts live in the separate sanity directory. The sanity
command generates SANITY.md from its saved metrics. Literal LR tolerance and rounded
agreement are separate checks; do not silently waive the literal gate.

## Recovery and output integrity

Each completed (site,h,test_month,algorithm) is an atomic checksummed JSON checkpoint
under checkpoints/. It records row identities/truth/probabilities, all validation
losses, chosen parameters, K through candidate count, seed, input/source/environment
fingerprints, warnings and elapsed seconds. A changed source, environment, candidate
manifest, input or request is rejected. An incompatible/incomplete/corrupt checkpoint
must be investigated; use a fresh output directory for a deliberately different run.
Temporary .tmp files are unpublished and safely overwritten when a unit retries.
Do not launch two writers against the same output directory.

After every requested unit validates, assembly creates tuned_results.csv,
selected_configs.csv, tuned_predictions.csv.gz, tuning_summary.md, and tuned_brier.png.
Pooled metrics use all outer predictions, with average ranks for exact ties.
Historical cumulative partial predictions/configurations were removed; old logs,
budget, configurations and source hashes remain provenance of the interrupted run,
not completed results or reusable checkpoints. Production results are absent until
the lead completes the grid. Sanity artifacts are explicitly a restricted K=1 run.

Only seed 42 is specified. Temporal folds are dependent, not independent runs;
no inferential significance tests were run or authorized here.

## Acceptance status after fixer review

Do not treat this handoff as acceptance of every MUST-FIX. The merge remains
blocked by worktree Git metadata permissions. Repository-wide Ruff still reports
397 violations, including protected and out-of-scope files; scoped lint success
is not a substitute. The lead must resolve these through the authorized workflow
and rerun checks against the merged revision.

LR's literal 1e-9 reproduction criterion remains failed. Four-decimal agreement
is diagnostic only, pending an explicit lead decision or a verified full-precision
baseline. RF passes the specified Brier tolerance but its historical discrepancy
is unexplained. Small differences cannot establish improvements beyond baseline
reproducibility and rounding uncertainty.

The fixer reran only the prescribed K=1 sanity experiment after changing tuning.py.
The previous sanity directory is archived as historical_sanity_before_fixes/
and cannot pass current source validation. Production assembly now validates
underlying sanity checkpoints and recomputes comparisons, or explicitly reports
that evidence is unavailable. See results/tuning/README.md for artifact status.
