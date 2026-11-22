# NaN checkpoint repair

## Root cause

The original failure occurs while writing the manifest before fitting. A scan of all twelve algorithms and all eight candidates found exactly `effective_parameters.XGBoost[i].missing` (i=0..7): Python float NaN. XGBClassifier.get_params(deep=True) supplies its legitimate missing-value sentinel; json_params previously preserved it through permissive json.dumps/json.loads. It is not a pandas None conversion or a validation loss.

## Original traceback

```text
concurrent.futures.process._RemoteTraceback: 
"""
Traceback (most recent call last):
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\process.py", line 264, in _process_worker
    r = call_item.fn(*call_item.args, **call_item.kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\process.py", line 213, in _process_chunk
    return [fn(*args) for args in chunk]
            ^^^^^^^^^
  File "D:\SolarProject\tmp\rev_step2\studies\S1_outage_forecasting\benchmark\tuning.py", line 307, in evaluate_worker
    evaluate(site, h, x, y, candidates, out)
  File "D:\SolarProject\tmp\rev_step2\studies\S1_outage_forecasting\benchmark\tuning.py", line 240, in evaluate
    atomic_json(manifest_path, manifest)
  File "D:\SolarProject\tmp\rev_step2\studies\S1_outage_forecasting\benchmark\tuning.py", line 162, in atomic_json
    json.dump(value, stream, sort_keys=True, allow_nan=False)
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\__init__.py", line 179, in dump
    for chunk in iterable:
                 ^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 432, in _iterencode
    yield from _iterencode_dict(o, _current_indent_level)
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 406, in _iterencode_dict
    yield from chunks
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 406, in _iterencode_dict
    yield from chunks
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 326, in _iterencode_list
    yield from chunks
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 398, in _iterencode_dict
    yield _floatstr(value)
          ^^^^^^^^^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\json\encoder.py", line 240, in floatstr
    raise ValueError(
ValueError: Out of range float values are not JSON compliant: nan
"""

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "D:\SolarProject\tmp\rev_step2\studies\S1_outage_forecasting\benchmark\tuning.py", line 528, in <module>
    main()
  File "D:\SolarProject\tmp\rev_step2\studies\S1_outage_forecasting\benchmark\tuning.py", line 492, in main
    list(pool.map(evaluate_worker, jobs))
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\process.py", line 636, in _chain_from_iterable_of_lists
    for element in iterable:
                   ^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\_base.py", line 619, in result_iterator
    yield _result_or_cancel(fs.pop())
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\_base.py", line 317, in _result_or_cancel
    return fut.result(timeout)
           ^^^^^^^^^^^^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "D:\SolarProject\tools\python\cpython-3.12.15-windows-x86_64-none\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
ValueError: Out of range float values are not JSON compliant: nan

```

## Schema and selection rule

Schema 2 invalidates earlier request/manifests/checkpoints. Canonical hashing and atomic writing use the same normalized parameter representation with `allow_nan=False`. The only nonfinite parameter accepted is XGBClassifier's NaN `missing` sentinel, represented as `{"__float__":"nan","meaning":"XGBoost missing sentinel"}`. `restore_params` reconstructs it as NaN. Ordinary None remains JSON null; unknown nonfinite parameters and required metadata still raise.

Each candidate retains its index, original overrides, status, dimensionless Brier loss, failure stage and reason. Fit/prediction exceptions or nonfinite validation losses produce `status=failed, loss=null`. Failed candidates consume their original budget slot. Selection minimizes `(loss, index)` over successful finite candidates only; exact ties retain the first eligible index. No candidate is redrawn. All-candidate failures and selected outer refit/prediction failures write failed units and stop successful assembly. Failed units are rejected on resume for explicit investigation; completed units are validated and reused.

Only single-class AUC is nullable among metrics and includes `auc_reason`; valid Brier selection remains unaffected. NaN/inf probabilities remain invalid. Checkpoint reading verifies candidate records, the winner, effective parameters, predictions, recomputed metrics and provenance/checksum. No blanket NaN-to-null encoder is used: schema producers explicitly create null only for failed losses or undefined AUC. Search spaces, ordering, seeds, K, temporal design and benchmark/significance sources are unchanged.

The source repair belongs in the existing benchmark tuning module; no unrelated src/ or experiments/ module was introduced. The pre-existing agent_notes/PLAN.md working-tree modification was preserved.

One fixed seed (42), dependent temporal folds; no independent replications or statistical test are claimed. The bounded probe cannot establish full-grid success.

## Probe-discovered regression and correction

The first repair probe exposed a new validation mismatch in the added metric integrity check: XGBoost returns float32 probabilities, whereas JSON reconstructs them as float64. The newly stored fold Brier used float32 and its recomputation used float64. The initial attempt is retained in nanfix_initial_probe.log. `nullable_scores` now explicitly computes ancillary checkpoint metrics from float64 probabilities, matching JSON reconstruction and the existing pooled-output representation. Candidate validation Brier calculations and selection remain unchanged. A regression test covers this round-trip. The full three-minute probe was restarted from empty scratch output after this correction.

## Bounded-process termination

The next probe produced valid checkpoints but the `taskkill /T /F` wrapper did not terminate its process tree within the timeout. The four observed workers were stopped directly with PowerShell; their completed checkpoints were validated before scratch cleanup. This overrun is retained in nanfix_termination_probe.log and is not presented as a correctly bounded run. The probe harness now assigns its subprocess immediately to a Windows Job Object and uses TerminateJobObject at the 180-second deadline, covering inherited workers. The final probe uses unchanged tuning.py, K=8, seed 42 and the same four-case command.

## Final verification

Final probe: 180.004161 seconds; 65 completed units validated, 0 failed units, 69 strict-JSON checkpoint/manifest files. stderr empty: True. TerminateJobObject succeeded: parent and all inherited worker processes stopped. Exit code 1 is deliberate job termination, not a tuning exception. Scratch artifacts were deleted; only probe.log remains.

Full pytest: 99 passed, 107 existing deprecation warnings. Ruff on tuning.py and all tests: passed. Formatting-only changes to two older tests resolve their pre-existing lint findings; their focused rerun passed 46 tests.

## Independent statistician verification

Fresh prescribed probe: 180.0058246999979 seconds, 59 completed units, 0 failed units, 63 strict-JSON checkpoint/manifest files; stderr empty. Exit 1 is deliberate Job Object termination at the deadline. All scratch artifacts removed except nanfix_probe/probe.log. The previous experimenter log is preserved as nanfix_experimenter_probe.log. Verification jobs ran concurrently, so throughput is not a benchmark.

Independent root-cause scan and exact traceback comparison passed; evidence: benchmark/results/tuning/statistical_audit/nanfix_root_cause.json. Fresh seed-42/43 default-only audit and statistical caveats are in ../STATS_REPORT.md. Final pytest: 107 passed, 107 deprecation warnings. Ruff on tuning.py and tests passed. This reviewer added eight parametrized regression cases without changing the existing production repair.

## Fresh fixer probe — 2026-11-22

The prescribed BG/KR, horizons 1/6, K=8, four-worker command survived
180.0058157000458 seconds without a tuning exception; stderr was empty.
65 completed units passed checkpoint validation, with 0 failed units and 69
strict-JSON checkpoint/manifest files. Windows Job Object termination stopped
the parent and inherited workers; exit 1 is deliberate termination. Scratch
output was deleted except nanfix_probe/probe.log. Tests ran concurrently for part
of the window, so throughput is not a performance estimate. No full-grid result
or later-fold success is inferred.

Fresh fixer checks: 107 pytest tests passed (107 warnings, 92.25 seconds); scoped
Ruff and root-cause/traceback verification passed. No production edits were needed
in this pass. The current REVIEW.md has no in-scope MUST-FIX items. PLAN.md and
the results README now distinguish historical planning/sanity evidence from the
current repair.
