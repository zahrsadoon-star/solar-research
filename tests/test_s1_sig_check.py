"""Independent checks of significance arithmetic and hourly resampling."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import t

PATH = Path(__file__).resolve().parents[1] / 'studies/S1_outage_forecasting/benchmark/significance_check/check.py'
spec = importlib.util.spec_from_file_location('s1_sig_check', PATH)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_identical_forecasts() -> None:
    """Identical dimensionless losses have zero effect and p=1."""
    result = check.dm_test(np.zeros(100), 6)
    assert result['brier_diff'] == result['dm_stat'] == 0
    assert result['p_value'] == 1
    assert result['dm_status'] == 'identical'


def test_better_forecast() -> None:
    """A clear nonconstant Brier advantage yields a small two-sided p."""
    rng = np.random.default_rng(12)
    y = rng.integers(0, 2, 2000)
    good = np.where(y, .9, .1)
    bad = rng.uniform(.3, .7, len(y))
    result = check.dm_test((good-y)**2-(bad-y)**2, 6)
    assert result['brier_diff'] < 0
    assert result['p_value'] < .001
    assert result['dm_status'] == 'ok'


def test_hac_hln_against_matrix() -> None:
    """Compare HAC against an explicit Bartlett covariance quadratic form."""
    d = np.random.default_rng(5).normal(.1, 1, 80)
    h, n = 6, len(d)
    lag = h-1+24
    distances = np.abs(np.arange(n)[:, None]-np.arange(n)[None, :])
    weights = np.maximum(0., 1-distances/(lag+1))
    centered = d-d.mean()
    variance = centered @ weights @ centered / n
    stat = d.mean()/np.sqrt(variance/n)*np.sqrt((n+1-2*h+h*(h-1)/n)/n)
    actual = check.dm_test(d, h)
    assert actual['long_run_variance'] == pytest.approx(variance)
    assert actual['dm_stat'] == pytest.approx(stat)
    assert actual['p_value'] == pytest.approx(2*t.sf(abs(stat), n-1))
    assert check.dm_test(np.full(80, .25), h)['dm_status'] == 'invalid_variance'


def test_bootstrap_reproducible_and_paired() -> None:
    """Same seed reproduces intervals and duplicate algorithms stay identical."""
    y = np.tile([0, 1], 60)
    p = np.random.default_rng(8).uniform(size=120)
    probabilities = np.column_stack([p, p, 1-p])
    args = {'block': 24, 'resamples': 30, 'seed': 42}
    a, b = check.bootstrap(y, probabilities, **args)
    c, d = check.bootstrap(y, probabilities, **args)
    np.testing.assert_array_equal(a, c)
    np.testing.assert_array_equal(b, d)
    assert check.interval(a[:, 0]-a[:, 2], .05) == check.interval(c[:, 0]-c[:, 2], .05)
    np.testing.assert_array_equal(a[:, 0], a[:, 1])
    np.testing.assert_array_equal(b[:, 0], b[:, 1])
    indices = check.block_indices(120, 24, np.random.default_rng(42))
    assert len(indices) == 120 and indices.min() >= 0 and indices.max() < 120
    np.testing.assert_array_equal(np.diff(indices.reshape(-1, 24), axis=1), np.ones((5, 23)))
    assert np.isnan(check.auc(np.zeros(10), np.arange(10)))
    assert np.isnan(check.interval(np.array([0., np.nan]), .05)).all()
    assert check.auc(np.array([0, 1, 0, 1]), np.ones(4)) == .5


def test_holm_hand_example() -> None:
    """Hand-computed family-adjusted probabilities, including invalid member."""
    np.testing.assert_allclose(check.holm(np.array([.01, .04, .03])), [.03, .06, .06])
    np.testing.assert_allclose(check.holm(np.array([.01, np.nan, .03])), [.03, 1., .06])


def test_input_validation() -> None:
    """Reject gaps, duplicate keys and partial missingness rather than dropping rows."""
    frame = pd.DataFrame({'site': ['BG']*40, 'h': [1]*40,
        'time': pd.date_range('2018-04-01', periods=40, freq='h'), 'y': np.tile([0, 1], 20)})
    for i in range(6):
        frame[f'model{i}'] = .1*i
    assert len(check.validate(frame, [['BG', 1]])[0][3]) == 6
    with pytest.raises(ValueError, match='Nonconsecutive'):
        check.validate(frame.drop(5), [['BG', 1]])
    with pytest.raises(ValueError, match='Duplicate'):
        check.validate(pd.concat([frame, frame.iloc[:1]]), [['BG', 1]])
    frame.loc[5, 'model0'] = np.nan
    with pytest.raises(ValueError, match='Partial'):
        check.validate(frame, [['BG', 1]])


def test_delivered_pairs_and_comparison() -> None:
    """All four complete families and comparison cases are delivered."""
    pairs = pd.read_csv(check.OUTPUT / 'pairs.csv')
    assert len(pairs) == 60
    assert pairs.groupby(['site', 'h']).size().eq(15).all()
    assert not pairs.duplicated(['site', 'h', 'algorithm_a', 'algorithm_b']).any()
    for _, g in pairs.groupby(['site', 'h']):
        np.testing.assert_allclose(check.holm(g.p_value.to_numpy()), g.p_holm, atol=1e-11)
    text = (PATH.parent / 'COMPARISON.md').read_text(encoding='utf-8')
    for site, h in [('BG', 1), ('BG', 6), ('KR', 1), ('KR', 6)]:
        assert f'| {site}, {h} h |' in text


@pytest.mark.parametrize('site,h', [('BG', 1), ('BG', 6), ('KR', 1), ('KR', 6)])
def test_original_labels_scaling_and_temporal_boundaries(site: str, h: int) -> None:
    """Original export labels align; training targets and scaling precede test hours."""
    model_spec = importlib.util.spec_from_file_location('benchmark_audit', PATH.parent.parent / 'benchmark.py')
    benchmark = importlib.util.module_from_spec(model_spec)
    model_spec.loader.exec_module(benchmark)
    data = benchmark.load(site)
    x, y = benchmark.features(data, h), data.outage.shift(-h)
    valid = x.notna().all(axis=1) & y.notna()
    x, y = x[valid], y[valid]
    target = x.index + pd.Timedelta(hours=h)
    exported = pd.read_csv(check.INPUT, parse_dates=['time'])
    case = exported[(exported.site == site) & (exported.h == h)].set_index('time')
    np.testing.assert_array_equal(case.y, y.loc[case.index])
    for month in range(4, 13):
        start = pd.Timestamp(2018, month, 1)
        train = (x.index < start) & (target < start)
        test = x.index.month == month
        assert target[train].max() < x.index[test].min()
        assert y[train].nunique() == y[test].nunique() == 2
        scaler = benchmark.algorithms()['Logistic Regression'].steps[0][1]
        scaler.fit(x[train])
        np.testing.assert_allclose(scaler.mean_, x[train].mean())
        scaler.transform(x[test])
        np.testing.assert_allclose(scaler.mean_, x[train].mean())
    changed = data.copy()
    origin = data.index[400]
    changed.loc[changed.index > origin, 'outage'] = 1-changed.loc[changed.index > origin, 'outage']
    changed.loc[changed.index > origin, 'load_kwh'] += 100
    pd.testing.assert_frame_equal(benchmark.features(data, h).loc[:origin],
                                  benchmark.features(changed, h).loc[:origin])


def test_bootstrap_matches_shared_draws() -> None:
    """Both dimensionless metrics use the same noncircular hourly draws."""
    y = np.tile([0, 1], 31)
    probabilities = np.random.default_rng(17).uniform(size=(62, 2))
    bs, au = check.bootstrap(y, probabilities, block=24, resamples=7, seed=42)
    rng = np.random.default_rng(42)
    for draw in range(7):
        indices = check.block_indices(len(y), 24, rng)
        np.testing.assert_allclose(bs[draw], ((probabilities[indices] - y[indices, None]) ** 2).mean(axis=0))
        for column in range(2):
            assert au[draw, column] == check.auc(y[indices], probabilities[indices, column])


@pytest.mark.parametrize('value', [-0.01, 1.01, np.inf])
def test_invalid_probabilities_rejected(value: float) -> None:
    """Out-of-range or nonfinite dimensionless probabilities cannot enter inference."""
    frame = pd.DataFrame({'site': ['BG'] * 40, 'h': [1] * 40,
        'time': pd.date_range('2018-04-01', periods=40, freq='h'), 'y': np.tile([0, 1], 20)})
    for i in range(6):
        frame[f'model{i}'] = .1 * i
    frame.loc[0, 'model0'] = value
    with pytest.raises(ValueError, match='invalid probability'):
        check.validate(frame, [['BG', 1]])


def test_single_class_bootstrap_is_unavailable() -> None:
    """Undefined AUC replicates are counted without redraw or partial intervals."""
    frame = pd.DataFrame({'site': ['BG'] * 40, 'h': [1] * 40,
        'time': pd.date_range('2018-04-01', periods=40, freq='h'), 'y': np.zeros(40)})
    for i in range(6):
        frame[f'model{i}'] = .1 * i
    pairs, _ = check.analyze(frame, {'cases': [['BG', 1]], 'block_hours': 24,
        'resamples': 5, 'seed': 42, 'alpha': .05})
    assert pairs.auc_valid_resamples.eq(0).all()
    assert pairs.auc_status.eq('undefined_replicate').all()
    assert pairs[['auc_ci_low', 'auc_ci_high']].isna().all().all()
    assert pairs.dm_status.eq('invalid_variance').all()
    assert not pairs.a_better.any()


def test_auc_matches_sklearn_under_imbalance_and_ties() -> None:
    """Rank AUC agrees with sklearn for imbalanced classes and tied probabilities."""
    from sklearn.metrics import roc_auc_score

    y = np.array([1, 1] + [0] * 98)
    p = np.random.default_rng(43).integers(0, 5, len(y)) / 4
    assert check.auc(y, p) == pytest.approx(roc_auc_score(y, p), abs=1e-14)


def test_holm_is_invariant_to_pair_order() -> None:
    """Family correction is invariant to pair order, including tied p-values."""
    p = np.array([.001, .04, .04, .9, np.nan])
    order = np.array([4, 2, 0, 3, 1])
    np.testing.assert_array_equal(check.holm(p)[order], check.holm(p[order]))
