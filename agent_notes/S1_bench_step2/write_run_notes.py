"""Generate the lead's run instructions from the retained timing evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies/S1_outage_forecasting/benchmark'))
import tuning as tu


def main() -> None:
    """Write timing estimates in seconds and exact PowerShell commands."""
    budget = tu.frozen_budget()
    out = tu.HERE / 'results/tuning'
    (out / 'timing_estimate_20261122.json').write_text(json.dumps(budget, indent=2), encoding='utf-8')
    seconds = budget['estimated_seconds'][budget['K']]
    command = r'''$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
& D:\SolarProject\venv312\Scripts\python.exe -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG KR --horizons 1 6 --K 8 --n-jobs 4 --out studies/S1_outage_forecasting/benchmark/results/tuning'''
    sanity = r'''& D:\SolarProject\venv312\Scripts\python.exe -u studies/S1_outage_forecasting/benchmark/tuning.py --sites BG --horizons 1 --K 1 --n-jobs 1 --out studies/S1_outage_forecasting/benchmark/results/tuning/sanity --sanity'''
    text = f'''# Full-grid handoff

Run from the repository root, after the lead resolves the pending merge of origin/main.
The required merge was attempted first but Git could not create ORIG_HEAD.lock in the
main repository's worktree metadata outside the writable sandbox. No merge occurred.
No commit or push was made. PLAN.md now records the frozen spaces explicitly and describes the implemented CLI.

```powershell
{command}
```

Repeat the identical command after an interruption. Completed compatible units are
validated and skipped. Do not use --run-only; it has been replaced by automatic resume.
--n-jobs is concurrent case processes; it does not change candidate estimator parameters.
BLAS/OpenMP and LOKY CPU limits are one per worker; explicitly parallel estimators and
CatBoost can manage extra threads. The full process-pool grid has not been executed
in this session. CLI parsing/help and the sanity command were exercised.

## Frozen budget and runtime

K={budget['K']}; feasible={budget['feasible']}. The historical probe gives
{seconds:.6f} seconds = {seconds / 60:.2f} minutes = {seconds / 3600:.2f} hours
for the sequential estimate including overhead, refits and sanity. No K in [8,20]
meets the 80-minute target, so the rule retains the minimum K=8. K=20 estimates
{budget['estimated_seconds'][20] / 3600:.2f} hours. This is not a measured parallel
wall time or an upper bound; four workers do not imply a guaranteed fourfold speedup.
Allow a long unattended run. The native execution limits differ from the historical
probe; actual timing must be recorded rather than asserted in advance.

Formula: `{budget['formula']}`.
{budget['overhead']}. Timing inputs: `results/tuning/timing_probe_20261116.csv`
relative to the benchmark directory. Machine-readable recomputation:
`results/tuning/timing_estimate_20261122.json`. Reproduce this note with
`python agent_notes/S1_bench_step2/write_run_notes.py`.

## Sanity only

```powershell
{sanity}
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
'''
    text += '\n## Acceptance status\n\nSee ../FIX_REPORT.md for unresolved merge, repository-wide lint and reproduction gates.\n'
    (ROOT / 'agent_notes/S1_bench_step2/RUN.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
