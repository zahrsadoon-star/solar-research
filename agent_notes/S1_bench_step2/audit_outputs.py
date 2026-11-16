"""Audit completed tuning artifacts against input rows and pooled metrics."""
from pathlib import Path
import hashlib
import json
import os
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies/S1_outage_forecasting/benchmark'))
import tuning as tu


def main() -> None:
    """Check all case/month/model keys, selection minima and dimensionless metrics."""
    out = tu.OUT
    result = pd.read_csv(out / 'tuned_results.csv')
    selected = pd.read_csv(out / 'selected_configs.csv')
    predictions = pd.read_csv(out / 'tuned_predictions.csv.gz', parse_dates=['origin_time', 'target_time'])
    names = list(tu.algorithms())
    k = json.loads((out / 'budget.json').read_text())['K']
    assert len(result) == 4 * len(names)
    assert len(selected) == 4 * 9 * len(names)
    assert not result.duplicated(['site', 'h', 'algorithm']).any()
    assert not selected.duplicated(['site', 'h', 'test_month', 'algorithm']).any()
    assert set(result.K) == {k}
    tu.validate_predictions(predictions, names)
    maximum = 0.0
    counts = {}
    for site in ['BG', 'KR']:
        for h in tu.HORIZONS:
            x, y = tu.case_data(site, h)
            expected = x.index[x.index.month >= 4]
            frame = predictions[(predictions.site == site) & (predictions.h == h)]
            assert frame.origin_time.tolist() == expected.tolist()
            assert np.array_equal(frame.y, y.loc[expected])
            assert (frame.target_time == frame.origin_time + pd.Timedelta(hours=h)).all()
            assert (frame.month == frame.origin_time.dt.month).all()
            counts[f'{site}_{h}'] = len(frame)
            for name in names:
                row = result[(result.site == site) & (result.h == h) & (result.algorithm == name)].iloc[0]
                for metric, value in tu.scores(frame.y.to_numpy(), frame[name].to_numpy()).items():
                    difference = abs(value - row[metric])
                    maximum = max(maximum, difference)
                    assert difference < 1e-12
                    assert abs(row['delta_' + metric] - (row[metric] - row['default_' + metric])) < 1e-12
                configs = tu.configurations(name, k)
                rows = selected[(selected.site == site) & (selected.h == h) & (selected.algorithm == name)]
                assert set(rows.test_month) == set(range(4, 13))
                for _, choice in rows.iterrows():
                    losses = json.loads(choice.inner_briers_json)
                    assert len(losses) == k and np.isfinite(losses).all()
                    assert choice.config_index == int(np.argmin(losses))
                    assert abs(choice.inner_brier - min(losses)) < 1e-12
                    model = tu.estimator(name, configs[int(choice.config_index)], int(choice.config_index))
                    assert json.dumps(json.loads(choice.config_json), sort_keys=True) == json.dumps(tu.json_params(model), sort_keys=True)
    original = json.loads((out / 'source_hashes.json').read_text())
    current = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in original}
    for path, expected_hash in original.items():
        if not path.endswith('/tuning.py'):
            assert current[path] == expected_hash
    (out / 'final_source_hashes.json').write_text(json.dumps(current, indent=2))
    audit = dict(passed=True, result_rows=len(result), selected_rows=len(selected), prediction_rows=len(predictions),
                 case_rows=counts, max_pooled_metric_recompute_difference=maximum, cpu_count=os.cpu_count(),
                 worker_cpu_budget=max(1, (os.cpu_count() or 1) // 4), blas_threads_per_worker=1,
                 joblib_backend='threading', workers=4, candidate_fits=4*9*len(names)*k,
                 selected_outer_refits=4*9*len(names))
    (out / 'audit.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
