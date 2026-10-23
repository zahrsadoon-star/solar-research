"""Audit repository provenance without refitting or altering benchmark artifacts."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'studies/S1_outage_forecasting/benchmark'
PREFIX = 'studies/S1_outage_forecasting/benchmark/'


def git_text(*args: str) -> str:
    """Read repository history as normalized text."""
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def functions(source: str) -> dict[str, str]:
    """Return structural function bodies, excluding source formatting."""
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def main() -> None:
    """Save provenance checks and drift counts; no statistical inference."""
    original = git_text('show', 'baa23da:' + PREFIX + 'benchmark.py')
    current = (BENCH / 'benchmark.py').read_text()
    before, after = functions(original), functions(current)
    frozen = (BENCH / 'results/benchmark_results.csv').read_text()
    initial = git_text('show', 'baa23da:' + PREFIX + 'results/benchmark_results.csv')
    gate = json.loads((BENCH / 'results/preservation_check.json').read_text())
    counts: dict[str, int] = {}
    for row in gate['differences']:
        counts[row['algorithm']] = counts.get(row['algorithm'], 0) + 1
    result = {
        'original_commit': git_text('rev-parse', 'baa23da').strip(),
        'benchmark_history': git_text('log', '--format=%h %s', '--', PREFIX + 'benchmark.py').splitlines(),
        'original_source_sha256_normalized': hashlib.sha256(original.encode()).hexdigest(),
        'current_source_sha256_normalized': hashlib.sha256(current.encode()).hexdigest(),
        'unchanged_functions': {name: before[name] == after[name] for name in before if name != 'run'},
        'run_change': 'Prediction export only; see git diff. No model, feature or split changes.',
        'frozen_results_match_initial_commit_normalized': frozen == initial,
        'changed_cells_by_algorithm': counts,
        'preservation_passed': gate['passed'],
        'original_execution_environment': 'Unavailable: no original producing-run environment manifest located in repository history/notes.',
        'available_environment_evidence': 'run_metadata.json records the export rerun; verify/results/freeze.json records a separate verifier, not the original benchmark run. requirements-s1.txt is not an original-run attestation and omits boosted-tree packages.',
        'cause': 'Unresolved. Code provenance alone cannot establish the execution environment, input bytes or actual executed source of the original producing run. No causal attribution to package versions or parallelism is justified.',
    }
    assert all(result['unchanged_functions'].values())
    assert result['frozen_results_match_initial_commit_normalized']
    (BENCH / 'results/step1_provenance_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
