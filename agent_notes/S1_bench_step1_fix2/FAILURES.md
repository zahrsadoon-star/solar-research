# Failure diagnosis

Local main is 673d7622d1d22a6bc80f2bb2679e8ebaa40e859f; branch HEAD is aa09b51.

## Integration blocker

git merge --no-commit --no-ff main failed before integration:

```text
fatal: update_ref failed for ref 'ORIG_HEAD': cannot lock ref 'ORIG_HEAD': Unable to create 'D:/SolarProject/solar-research/.git/worktrees/fix5-20261023-s1-bench-step1-significance/ORIG_HEAD.lock': Permission denied
```

No metadata workaround, commit, push or network access was used. Main is not merged. The passing branch suite excludes main-only later tests.

## Exact requested basetemp

Ran unmodified tests in an isolated complete copy inside this repository:

```powershell
python -m pytest -q --basetemp=D:\SolarProject\tmp\pytest\fix2sig --junitxml=requested.xml
```

Result: 4 failed, 50 passed, 1 skipped, 16 errors. Four failures are the missing prediction path described below; all 16 setup errors are external-basetemp permission errors. Exact errors:

- `tests/test_outage_data.py::test_loader_fails_closed_without_weather`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_column]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_hour]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[extra_hour]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[duplicate]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[reverse]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[shift]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[half_hour]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nat]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[aware]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nan]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[inf]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[text]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_s1_bench_significance.py::test_historical_significance_is_disabled`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_s1_eda.py::test_complete_temperature_eda[0]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`
- `tests/test_s1_eda.py::test_complete_temperature_eda[17]`: `failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"`

## Controlled writable-basetemp baseline

python -m pytest -q --basetemp=pytest_tmp --junitxml=baseline.xml in the complete isolated copy reproduced 5 failed, 65 passed, 1 skipped. Full tracebacks: baseline_local.log and baseline_local.xml.

### `tests/test_s1_bench_significance.py::test_real_labels_boundaries_and_scaling[1-BG]`

```text
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\SolarProject\\worktrees\\fix5-20261023-s1-bench-step1-significance\\agent_notes\\S1_bench_step1_fix2\\baseline_repository\\studies\\S1_outage_forecasting\\benchmark\\results\\predictions.csv.gz'
```

The test reads benchmark/results/predictions.csv.gz, but the retained file is agent_notes/S1_bench_step1/windows_rerun/predictions.csv.gz. Its score table is windows_rerun/step1_rerun/benchmark_results.csv.

### `tests/test_s1_bench_significance.py::test_real_labels_boundaries_and_scaling[1-KR]`

```text
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\SolarProject\\worktrees\\fix5-20261023-s1-bench-step1-significance\\agent_notes\\S1_bench_step1_fix2\\baseline_repository\\studies\\S1_outage_forecasting\\benchmark\\results\\predictions.csv.gz'
```

The test reads benchmark/results/predictions.csv.gz, but the retained file is agent_notes/S1_bench_step1/windows_rerun/predictions.csv.gz. Its score table is windows_rerun/step1_rerun/benchmark_results.csv.

### `tests/test_s1_bench_significance.py::test_real_labels_boundaries_and_scaling[6-BG]`

```text
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\SolarProject\\worktrees\\fix5-20261023-s1-bench-step1-significance\\agent_notes\\S1_bench_step1_fix2\\baseline_repository\\studies\\S1_outage_forecasting\\benchmark\\results\\predictions.csv.gz'
```

The test reads benchmark/results/predictions.csv.gz, but the retained file is agent_notes/S1_bench_step1/windows_rerun/predictions.csv.gz. Its score table is windows_rerun/step1_rerun/benchmark_results.csv.

### `tests/test_s1_bench_significance.py::test_real_labels_boundaries_and_scaling[6-KR]`

```text
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\SolarProject\\worktrees\\fix5-20261023-s1-bench-step1-significance\\agent_notes\\S1_bench_step1_fix2\\baseline_repository\\studies\\S1_outage_forecasting\\benchmark\\results\\predictions.csv.gz'
```

The test reads benchmark/results/predictions.csv.gz, but the retained file is agent_notes/S1_bench_step1/windows_rerun/predictions.csv.gz. Its score table is windows_rerun/step1_rerun/benchmark_results.csv.

### `tests/test_s1_bench_significance.py::test_historical_significance_is_disabled`

```text
ModuleNotFoundError: No module named 'benchmark'
```

The obsolete disabled-entry-point test imports restored significance.py via importlib, but sibling benchmark is not on sys.path. Failure is at import benchmark as bm, before main() or refitting. Fixing only sys.path would expose the obsolete disabled-entry-point expectation and could overwrite published results.

## Repairs

Repointed archived-export tests, including their score table; removed the obsolete missing-file skip so absence now fails. Replaced the disabled-entry-point contract with source comparison against main without executing it. CRLF/LF normalization applies only to this source test; result bytes are audited separately. Retained label, training-boundary, scaling and rounded-score checks. No tolerance widened. Added paired-draw, invalid-probability and undefined-AUC tests.

Final branch suite: 76 passed, 72 warnings (dependency deprecations), recorded in final_pytest.log and XML.

## Setup limitations

An initial command was interrupted before producing pytest output when its working directory was found to be the original repository. Protected files remained unchanged. Early isolated runs lacked scripts/ or experiments/; complete-copy reruns above supersede those setup failures. baseline_incomplete_copy.log retains that preliminary output.

Automatic approval review rejected recursive deletion of the disposable baseline_repository and pytest_tmp directories with reason "blocked by policy". These task-generated directories remain, and are not deliverable source. No alternative deletion method was attempted. See CODEX_REPORT.md for full lint and integration blockers.

## Statistician follow-up (2026-11-24)

Retried `git merge --no-commit --no-ff main`: the same ORIG_HEAD.lock permission error prevents integration. No Git metadata workaround was used.

Current repaired suite with the exact requested external basetemp: 61 passed, 15 setup errors. No assertion failures. Each setup error below has the same cause: `PermissionError: [WinError 5] Access is denied` for `D:\SolarProject\tmp\pytest\fix2sig`. Full tracebacks: statistician_requested_pytest.log.



- `tests/test_outage_data.py::test_loader_fails_closed_without_weather`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_column]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_hour]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[extra_hour]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[duplicate]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[reverse]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[shift]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[half_hour]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nat]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[aware]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nan]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[inf]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[text]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_s1_eda.py::test_complete_temperature_eda[0]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).
- `tests/test_s1_eda.py::test_complete_temperature_eda[17]`: `PermissionError: [WinError 5] Access is denied: D:\SolarProject\tmp\pytest\fix2sig` (setup).

## Fixer follow-up (2026-11-24)

Merge retried: identical ORIG_HEAD.lock permission failure; main remains unmerged.

Requested-basetemp rerun: **63 passed, 15 setup errors**, no assertion failures.
Full tracebacks: `fixer_requested.log`; machine-readable nodes and errors: `fixer_requested.xml`.

- `tests/test_outage_data.py::test_loader_fails_closed_without_weather`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_column]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[missing_hour]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[extra_hour]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[duplicate]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[reverse]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[shift]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[half_hour]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nat]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[aware]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[nan]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[inf]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_outage_data.py::test_weather_rejects_invalid_input[text]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_s1_eda.py::test_complete_temperature_eda[0]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"
- `tests/test_s1_eda.py::test_complete_temperature_eda[17]`: failed on setup with "PermissionError: [WinError 5] Access is denied: 'D:\\SolarProject\\tmp\\pytest\\fix2sig'"

No post-merge result exists because integration is blocked. The original five failures above remain distinct from these filesystem setup errors.

Final current-branch validation: `python -m pytest -q
--basetemp=agent_notes/S1_bench_step1_fix2/fixer_pytest_tmp
--junitxml=agent_notes/S1_bench_step1_fix2/fixer_pytest.xml` completed with
**78 passed, 72 warnings, no skips** (`fixer_pytest.log`). No test tolerances
were changed in this follow-up. Full repository Ruff still reports 834 diagnostics;
scoped changed-file lint passes. These are not post-merge acceptance results.
