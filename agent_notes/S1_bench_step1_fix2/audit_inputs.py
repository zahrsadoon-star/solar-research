"""Immutable historical inputs and replay provenance; hashes are SHA-256."""
import hashlib
import importlib.metadata
import platform
import subprocess
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'cec3552fc9d739c3c08204d7eb70c22c84cbd70f'
BASE = 'studies/S1_outage_forecasting/benchmark/'


def historical_bytes(path: str) -> bytes:
    """Read a repository-relative input from the fixed historical revision."""
    return subprocess.check_output(['git', 'show', f'{REVISION}:{path}'], cwd=ROOT)


def benchmark_module() -> ModuleType:
    """Load pinned source, preserving repository-relative data resolution."""
    path = BASE + 'benchmark.py'
    module = ModuleType('benchmark_audit')
    module.__file__ = str(ROOT / path)
    # Execute only repository code from the fixed, reviewed Git revision above.
    exec(compile(historical_bytes(path), module.__file__, 'exec'), module.__dict__)  # noqa: S102
    return module


def provenance() -> dict:
    """Record historical sources, current data bytes and installed versions."""
    historical = [BASE + 'benchmark.py', BASE + 'results/benchmark_results.csv']
    local = ['data/raw/BG18760_with_analysis.xlsx', 'data/raw/KR-8760.xlsx',
             BASE + 'results/hourly_predictions_top6.csv.gz',
             BASE + 'significance_check/check.py', BASE + 'significance_check/config.json']
    packages = ['numpy', 'pandas', 'scipy', 'scikit-learn', 'lightgbm', 'catboost', 'xgboost', 'openpyxl']
    return {'revision': REVISION, 'python': platform.python_version(),
            'platform': platform.platform(),
            'versions': {name: importlib.metadata.version(name) for name in packages},
            'historical_sha256': {p: hashlib.sha256(historical_bytes(p)).hexdigest() for p in historical},
            'local_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in local}}
