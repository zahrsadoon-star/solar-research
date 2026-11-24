"""Audit frozen scores and bootstrap seeds; outputs are dimensionless."""
import importlib.util
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from audit_inputs import BASE, historical_bytes, provenance

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'studies/S1_outage_forecasting/benchmark'
OUT = BENCH / 'results/significance_check/statistical_audit'


def main() -> None:
    """Replay two exploratory bootstrap seeds, retaining all comparisons."""
    spec = importlib.util.spec_from_file_location('check', BENCH / 'significance_check/check.py')
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(check.INPUT)
    config = json.loads((check.HERE / 'config.json').read_text())
    original, _ = check.analyze(frame, config)
    alternate, _ = check.analyze(frame, dict(config, seed=43))
    alternate.to_csv(OUT / 'seed43_pairs.csv', index=False)
    saved = pd.read_csv(check.OUTPUT / 'pairs.csv')
    numeric = original.select_dtypes(include='number').columns
    np.testing.assert_allclose(original[numeric], saved[numeric], atol=1e-10, rtol=1e-9)
    scores = pd.read_csv(io.BytesIO(historical_bytes(BASE + 'results/benchmark_results.csv')))
    metrics, classes = [], []
    for site, h, g, names in check.validate(frame, config['cases']):
        for name in names:
            published = scores[(scores.site == site) & (scores.h == h) & (scores.algorithm == name)].iloc[0]
            for metric, value in [('brier', ((g[name]-g.y)**2).mean()), ('auc', check.auc(g.y.to_numpy(), g[name].to_numpy()))]:
                metrics.append({'site': site, 'h': h, 'algorithm': name, 'metric': metric, 'recomputed': value, 'published': published[metric], 'difference': value-published[metric]})
        for month, group in g.groupby(pd.to_datetime(g.time).dt.month):
            classes.append({'site': site, 'h': h, 'month': month, 'n': len(group), 'outage_share': group.y.mean()})
    pd.DataFrame(metrics).to_csv(OUT / 'metric_audit.csv', index=False)
    pd.DataFrame(classes).to_csv(OUT / 'class_shares.csv', index=False)
    intervals = ['brier_ci_low', 'brier_ci_high', 'auc_ci_low', 'auc_ci_high']
    summary = {'provenance': provenance(), 'audit_type': 'same-implementation replay, not independent implementation', 'seeds': [42, 43], 'resamples_each': config['resamples'], 'seed42_reproduced': True,
        'changed_pair_decisions': int((original.a_better != alternate.a_better).sum()),
        'max_interval_endpoint_change': {c: float((original[c]-alternate[c]).abs().max()) for c in intervals},
        'max_absolute_metric_difference': pd.DataFrame(metrics).groupby('metric').difference.apply(lambda s: float(s.abs().max())).to_dict()}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
