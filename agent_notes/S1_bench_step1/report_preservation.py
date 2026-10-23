"""Generate the blocked-step report from the preservation check, without inference."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NOTES = Path(__file__).resolve().parent
BENCH = ROOT / 'studies/S1_outage_forecasting/benchmark'
OUT = BENCH / 'results'
r = json.loads((OUT / 'preservation_check.json').read_text())
assert not r['passed'], 'This report is only for the failed preservation gate.'
diffs = pd.DataFrame(r['differences'])
diffs.to_csv(OUT / 'preservation_differences.csv', index=False)
lines = ['# Step 1 preservation gate: FAILED', '',
         'Significance analysis stopped as explicitly required by task step 1. No new DM, bootstrap, Holm, AUC intervals or top-group conclusions were produced.', '',
         'The original published benchmark artifacts were restored byte-for-byte after archiving the rerun under `results/step1_rerun/`. The new `results/predictions.csv.gz` belongs to that rerun, NOT to the frozen published scores.', '',
         '## What changed', '',
         '- `benchmark.py`: export the existing pooled, clipped test predictions with site, horizon, origin time, target time, origin month, label and all algorithm/reference probabilities. No estimator settings, features, splits or scoring changed.',
         '- Added `tests/test_s1_bench_significance.py`: preservation comparison and full prediction alignment/probability/Brier checks.',
         '- Added task-local preservation checker, original backups, environment metadata, execution logs, and this report.',
         '- Replaced the README Step 1 conclusions with the failed-gate status; old significance artifacts remain historical and are not endorsed by this task.', '',
         '## Evidence', '',
         f'Changed published metric/rank cells: {len(diffs)}. Timing is excluded from this count.', '',
         '| Metric | Maximum absolute difference |', '| --- | ---: |']
lines += [f'| {name} | {value:.10g} |' for name, value in r['max_absolute_difference_by_metric'].items()]
lines += ['', f"Maximum runtime difference: {r['max_absolute_fit_seconds_difference']:.10g} seconds (reported separately).", '',
          'Affected algorithms: ' + ', '.join(sorted(diffs.algorithm.unique())) + '.', '',
          'These are changes at the existing published precision, including changed ranks, not row-order or rounding noise. The cause is unresolved. Previous verification notes also recorded unexplained forest drift; this does not identify a cause for the present differences.', '',
          '## Checks and reproduction', '',
          '`python studies/S1_outage_forecasting/benchmark/benchmark.py` produced the prediction, scores, ranking and figure artifacts. The PowerShell redirected launch returned status 1 with NumPy deprecation warnings; its log contains the completed ranking output. No Python traceback was observed. Output content is checked by pytest.', '',
          '`python agent_notes/S1_bench_step1/check_preservation.py` compares the saved original against the archived rerun; expected exit status 1. Full differences are scripted in `results/preservation_check.json` and `results/preservation_differences.csv`.', '',
          '`python -m pytest -q -o cache_dir=agent_notes/S1_bench_step1/pytest_cache` (see `pytest.log`).', '',
          'Benchmark seed remains 42. One frozen-settings benchmark rerun was performed; no tuning, extra seed search, network access, installation, commit or push. Statistical inference was not run.', '',
          '## Open question', '',
          'The lead must resolve the benchmark reproducibility discrepancy before significance work can continue. The task-specific allowlist places CODEX_REPORT.md here instead of the repository root. The pre-existing modification to agent_notes/PLAN.md was left untouched.', '']
test_log = (NOTES / 'pytest.log').read_text(encoding='utf-16')
summary = next(line for line in reversed(test_log.splitlines()) if 'passed' in line)
lines += ['## Final validation', '', summary, '', 'git diff --check passed. Original benchmark result artifacts have no git diff.', '']
(NOTES / 'CODEX_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
readme = BENCH / 'README.md'
prefix = readme.read_text(encoding='utf-8').split('## Step 1 - significance')[0]
section = '''## Step 1 - significance: stopped at preservation gate

The requested rerun changed published predictive metrics and ranks; it is not rounding noise.
The original benchmark results have been restored. Rerun scores are archived in
`results/step1_rerun/`; `results/predictions.csv.gz` contains the rerun predictions and
must not be treated as predictions underlying the original published scores.

'''
section += f"Maximum absolute Brier difference: {r['max_absolute_difference_by_metric']['brier']:.10g}; maximum rank change: {r['max_absolute_difference_by_metric']['rank_by_brier']:.10g}. "
section += '''See `results/preservation_check.json` and `results/preservation_differences.csv`.

Per the task's stop condition, no new significance pairs, intervals or top groups were computed.
The previous Step 1 conclusions and `significance.csv` / `hourly_predictions_top6.csv.gz`
use a different protocol and are historical, not results of this task. No claim of a
unique winner, a tie, or equivalence is supported by this incomplete step.
Resolve the reproducibility discrepancy before running the planned significance analysis.
'''
readme.write_text(prefix + section, encoding='utf-8')
