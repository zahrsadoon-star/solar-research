"""Compare frozen and rerun benchmark metrics at published precision."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NOTES = Path(__file__).resolve().parent
OUT = ROOT / 'studies/S1_outage_forecasting/benchmark/results'
KEYS = ['site', 'h', 'algorithm']


def compare(before: pd.DataFrame, after: pd.DataFrame) -> dict:
    """Return keyed metric differences (dimensionless; runtime in seconds)."""
    if before.duplicated(KEYS).any() or after.duplicated(KEYS).any():
        raise ValueError('Duplicate case/algorithm keys')
    a, b = (frame.set_index(KEYS).sort_index() for frame in (before, after))
    if not a.index.equals(b.index) or not a.columns.equals(b.columns):
        raise ValueError('Benchmark schema or case membership changed')
    if not a['kind'].equals(b['kind']):
        raise ValueError('Algorithm/reference classification changed')
    metrics = [c for c in a.columns if c not in ('kind', 'fit_seconds')]
    differences = []
    for col in metrics:
        for key in a.index:
            old, new = a.loc[key, col], b.loc[key, col]
            if pd.isna(old) and pd.isna(new):
                continue
            if old != new:
                differences.append(dict(zip(KEYS, key)) | {'metric': col, 'before': old,
                                   'after': new, 'difference': new - old})
    return {'passed': not differences, 'comparison': 'Exact published precision, keyed rows; timing excluded',
            'max_absolute_difference_by_metric': {c: float((a[c] - b[c]).abs().max()) for c in metrics},
            'max_absolute_fit_seconds_difference': float((a.fit_seconds - b.fit_seconds).abs().max()),
            'differences': differences}


if __name__ == '__main__':
    result = compare(pd.read_csv(NOTES / 'benchmark_results_before.csv'),
                     pd.read_csv(OUT / 'step1_rerun/benchmark_results.csv'))
    (OUT / 'preservation_check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'differences'}, indent=2))
    raise SystemExit(0 if result['passed'] else 1)

