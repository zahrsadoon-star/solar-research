"""Prediction export and frozen benchmark preservation checks."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'studies/S1_outage_forecasting/benchmark/results'
spec = importlib.util.spec_from_file_location('preservation', ROOT / 'agent_notes/S1_bench_step1/check_preservation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(scope='module')
def benchmark():
    """Load the actual benchmark without running model training."""
    spec = importlib.util.spec_from_file_location('s1_benchmark', OUT.parent / 'benchmark.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize('h', [1, 6])
def test_features_do_not_use_future_observations(benchmark, h: int) -> None:
    """Perturb observations strictly after an origin; past features must agree."""
    rng = np.random.default_rng(43)
    index = pd.date_range('2018-01-01', periods=500, freq='h')
    original = pd.DataFrame({'outage': rng.integers(0, 2, 500),
                             'load_kwh': rng.uniform(0, 10, 500)}, index=index)
    changed = original.copy()
    changed.loc[index[301]:, 'outage'] = 1 - changed.loc[index[301]:, 'outage']
    changed.loc[index[301]:, 'load_kwh'] += 100
    pd.testing.assert_frame_equal(benchmark.features(original, h).iloc[:301],
                                  benchmark.features(changed, h).iloc[:301])


@pytest.mark.parametrize('site', ['BG', 'KR'])
@pytest.mark.parametrize('h', [1, 6])
def test_real_labels_boundaries_and_scaling(benchmark, site: str, h: int) -> None:
    """Check hourly label alignment and training-only scaling at monthly boundaries."""
    data = benchmark.load(site)
    x, y = benchmark.features(data, h), data.outage.shift(-h)
    ok = x.notna().all(axis=1) & y.notna()
    x, y = x[ok], y[ok]
    target = x.index + pd.Timedelta(hours=h)
    exported = pd.read_csv(OUT / 'predictions.csv.gz', parse_dates=['origin_time'])
    case = exported[(exported.site == site) & (exported.h == h)].set_index('origin_time')
    np.testing.assert_array_equal(case.y, y.loc[case.index])
    for month in range(4, 13):
        start = pd.Timestamp(2018, month, 1)
        train = (x.index < start) & (target < start)
        test = x.index.month == month
        assert target[train].max() < x.index[test].min()
        assert y[train].nunique() == y[test].nunique() == 2
    # Exercise a real pipeline: its scaler must retain training-only moments.
    model = benchmark.algorithms()['Logistic Regression']
    model.fit(x[train], y[train])
    expected = x[train].mean().to_numpy()
    np.testing.assert_allclose(model.steps[0][1].mean_, expected)
    model.predict_proba(x[test])
    np.testing.assert_allclose(model.steps[0][1].mean_, expected)


def test_preservation_ignores_order_and_runtime_but_detects_score_drift():
    """Runtime seconds may change; published scores must remain identical."""
    a = pd.DataFrame({'site': ['BG', 'KR'], 'h': [1, 1], 'algorithm': ['A', 'A'],
                      'kind': ['algorithm'] * 2, 'brier': [0.1, 0.2], 'fit_seconds': [1., 2.]})
    b = a.iloc[::-1].copy()
    b['fit_seconds'] = 99.
    assert module.compare(a, b)['passed']
    b.loc[0, 'brier'] += 0.0001
    assert not module.compare(a, b)['passed']
    with pytest.raises(ValueError, match='Duplicate'):
        module.compare(pd.concat([a, a]), b)


def test_export_alignment_and_pooled_scores():
    """Exported hourly probabilities reproduce the rerun's rounded Brier scores."""
    path = OUT / 'predictions.csv.gz'
    if not path.exists():
        pytest.skip('Benchmark export not yet generated')
    p = pd.read_csv(path, parse_dates=['origin_time', 'target_time'])
    assert not p.duplicated(['site', 'h', 'origin_time']).any()
    metadata = ['site', 'h', 'origin_time', 'target_time', 'month', 'y']
    names = p.columns.difference(metadata)
    assert len(names) == 15
    assert p.y.isin([0, 1]).all()
    assert np.isfinite(p[names]).all().all()
    assert ((p[names] >= 0) & (p[names] <= 1)).all().all()
    assert (p.month == p.origin_time.dt.month).all()
    scores = pd.read_csv(OUT / 'step1_rerun/benchmark_results.csv').set_index(['site', 'h', 'algorithm'])
    for (site, h), g in p.groupby(['site', 'h']):
        assert g.origin_time.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all()
        assert (g.target_time - g.origin_time).eq(pd.Timedelta(hours=int(h))).all()
        for name in names:
            actual = ((g[name] - g.y) ** 2).mean()
            assert round(actual, 4) == scores.loc[(site, h, name), 'brier']



def test_historical_significance_is_disabled(tmp_path: Path) -> None:
    """Both CLI and imported entry point must stop without producing files."""
    import subprocess
    import sys

    script = OUT.parent / 'significance.py'
    loaded_spec = importlib.util.spec_from_file_location('disabled_significance', script)
    loaded = importlib.util.module_from_spec(loaded_spec)
    loaded_spec.loader.exec_module(loaded)
    with pytest.raises(SystemExit, match='BLOCKED: benchmark preservation failed'):
        loaded.main()
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert 'Historical significance is disabled' in result.stderr
    assert not list(tmp_path.iterdir())
    assert not hasattr(loaded, 'hourly_predictions')
