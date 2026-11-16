# S1 benchmark step 2 implementation notes

Follow agent_notes/PLAN.md and the task-specific write allowlist. No src/ or experiments/ edits.
The pre-existing change to agent_notes/PLAN.md was not edited by this implementation.

One seeded generator per algorithm; replacement draws; default config zero unchanged;
shared candidate prefixes; nested chronological folds; first-index ties; pooled metrics.
The timing budget is frozen before outer predictions and saved in budget.json.
All nondefault candidates use supported n_jobs=-1 / thread_count=-1 settings.
Default preservation takes precedence over blanket parallel settings for candidate zero.
CatBoost diagnostics are written inside the permitted tuning output directory.

Run from repository root:
python studies/S1_outage_forecasting/benchmark/tuning.py

The script refuses an existing budget.json. Archive an earlier run before reproducing.
Warnings and per-fold checkpoints retain partial evidence. Failed candidates abort the run.
No installation or network is used. One seed only; no statistical significance tests.

Tests:
python -m pytest -q -o cache_dir=agent_notes/S1_bench_step2/pytest_cache --basetemp=agent_notes/S1_bench_step2/pytest_tmp

PYTHONDONTWRITEBYTECODE=1 was set for tests and experiments.
The actual experiment was launched from results/tuning with python -u ../../tuning.py,
redirecting console output to run.log. The script also sets cwd there for future runs.

Execution adjustment: the initial sequential timing measurement froze K=8 before outer
performance inspection. Its conservative estimate exceeded the target even at K=8.
The first four-process execution oversubscribed native threads. It was interrupted;
two BG April checkpoint files completed around interruption and are preserved with
initial_parallel_ prefixes. No scores from those files guided any adjustment.
The restarted four-process run reuses the frozen configuration manifest and budget
via --run-only. Each worker exposes os.cpu_count() // 4 CPUs to joblib/LightGBM through
LOKY_MAX_CPU_COUNT, uses the threading joblib backend, limits OpenMP threads to that
CPU budget and BLAS threads to one. All estimator parameter values, seeds, candidates,
selection rules and outer folds remain unchanged. Some libraries (notably CatBoost)
manage their own threads; their estimator defaults remain unchanged as required.
The initial timing estimate is sequential and was not retroactively revised.

Final launch:
PYTHONDONTWRITEBYTECODE=1, OPENBLAS_NUM_THREADS=1, MKL_NUM_THREADS=1
python -u studies/S1_outage_forecasting/benchmark/tuning.py --run-only
Console log: results/tuning/parallel_limited_run.log.
Post-run artifact validation: python agent_notes/S1_bench_step2/audit_outputs.py
