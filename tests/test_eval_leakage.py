"""Protocol leakage tests: independently perturb future information."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from eval.config import load_config
from eval.targets import labels, targets
from eval.splits import monthly_folds, TestIndexGuard, random_month_split
from eval.features import features, TrainPreprocessor
from eval.climatology import Climatology
from eval.models import baseline, logistic, transition_matrices, markov_probability, prepare_baseline
from eval.metrics import bss, choose_threshold
from eval.artifacts import cache_key, write_predictions, read_predictions, select, threshold
from outage.data import load_outage_dataset, RAW, ANALYSIS

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def observations(): return load_outage_dataset()

@pytest.fixture(scope='module')
def series():
    index = pd.date_range('2018-01-01',periods=8760,freq='h',tz='Asia/Baghdad')
    return pd.Series(np.random.default_rng(110).integers(0,2,len(index)).astype(float),index=index)

def test_purge_train_labels(series):
    for h in load_config().horizons:
        for f in monthly_folds(series.index,h):
            for kind in ('a','b','c'):
                for positions,end in [(f.train,f.train_end),(f.inner_train,f.inner_end),(f.inner_val,f.train_end)]:
                    t = targets(series,kind,h,boundary=end).iloc[positions]
                    assert (t.label_time <= end).all()
            assert series.index[f.train[-1]]+pd.Timedelta(hours=24) <= f.train_end

def test_test_origins_after_train(series):
    for h in load_config().horizons:
        for f in monthly_folds(series.index,h):
            assert series.index[f.test[0]] > f.train_end
            assert series.index[f.inner_val[-1]] <= f.train_end
            assert series.index[f.test[-1]]+pd.Timedelta(hours=h) <= series.index[-1]
            assert series.index[f.test[0]].day == 1

def test_feature_causality(series):
    y = series.iloc[:760]; weather = pd.DataFrame({'temp':np.arange(len(y),dtype=float)},index=y.index)
    original = features(y,weather,'W2',3)
    for i in np.random.default_rng(10).choice(np.arange(100,759),500,replace=False):
        changed = y.copy(); changed.iloc[i+1:] = 1-changed.iloc[i+1:]
        w = weather.copy(); w.iloc[i+1:] += 1000
        actual = features(changed,w,'W2',3).iloc[i]
        causal = [k for k in actual.index if not k.startswith('oracle_')]
        pd.testing.assert_series_equal(actual[causal],original.iloc[i][causal])
    assert not any('month' in k or 'day_of_year' in k for k in original)

@pytest.mark.parametrize('kind',['a','b'])
def test_reference_causality(series,kind):
    y = series.iloc[:800]; changed = y.copy(); changed.iloc[500:] = 0
    positions = np.arange(500,780)
    np.testing.assert_array_equal(baseline('climatology',y,positions,y.index[499],6,kind),baseline('climatology',changed,positions,y.index[499],6,kind))
    # 500 distinct origins; all horizons; all implemented updating baselines.
    origins = np.random.default_rng(12).choice(np.arange(100,799),500,replace=False)
    names = ('persistence','seasonal_naive','trailing','recency','markov')
    prepared = {h:prepare_baseline(y,y.index[70],h,kind) for h in load_config().horizons}
    expected = {(h,name): baseline(name,y,origins,y.index[70],h,kind,7,prepared=prepared[h]) for h in load_config().horizons for name in names}
    for j,i in enumerate(origins):
        changed = y.copy(); changed.iloc[i+1:] = 1-changed.iloc[i+1:]
        for h in load_config().horizons:
            for name in names:
                actual = baseline(name,changed,np.array([i]),y.index[70],h,kind,7,prepared=prepared[h])
                assert actual[0] == expected[h,name][j]

def test_scaler_encoder_fit_scope(series):
    X = features(series); altered = X.copy(); altered.iloc[4000:] += 1000
    a = TrainPreprocessor().fit(X.iloc[:3000]); b = TrainPreprocessor().fit(altered.iloc[:3000])
    np.testing.assert_array_equal(a.scaler_.mean_,b.scaler_.mean_)
    np.testing.assert_array_equal(a.fill_,b.fill_)

def test_test_index_guard():
    g = TestIndexGuard(np.arange(10))
    for phase in ('tuning','selection','thresholds','calibration'):
        g.phase = phase
        with pytest.raises(RuntimeError): g.access()
    g.phase = 'evaluation'; assert len(g.access()) == 10

def test_threshold_from_inner_val(tmp_path):
    f = pd.DataFrame({'y':[0,1,0,1],'p':[.1,.7,.3,.9],'seed':[1]*4})
    path = tmp_path/'predictions/innerval/a.parquet'; write_predictions(path,f,'key')
    assert threshold(path,tmp_path,'key') == choose_threshold(f.y.to_numpy(),f.p.to_numpy())
    test_path = tmp_path/'predictions/a.parquet'; write_predictions(test_path,f,'key')
    with pytest.raises(ValueError): threshold(test_path,tmp_path,'key')
    with pytest.raises(ValueError): select({'a':test_path},tmp_path,'key',1e-6)

def test_local_time_no_double_shift(observations):
    means = observations.groupby(observations.index.hour).ghi_wm2.mean()
    assert (means.loc[0:3] == 0).all(); assert 11 <= means.idxmax() <= 13

def test_target_construction():
    idx = pd.date_range('2018-01-01',periods=6,freq='h')
    y = pd.Series([0.,1,1,0,1,1],index=idx)
    pd.testing.assert_series_equal(targets(y,'a',2).value,y.shift(-2),check_names=False)
    np.testing.assert_allclose(targets(y,'b',2).value,[1,1,1,1,np.nan,np.nan],equal_nan=True)
    t = targets(y,'c'); assert t.value.iloc[1] == 2; assert t.event.iloc[1]
    assert t.value.iloc[4] == 1; assert not t.event.iloc[4]
    missing = y.copy(); missing.iloc[2] = np.nan
    assert np.isnan(targets(missing,'b',2).value.iloc[0])

def test_duration_censor_at_train_end():
    idx = pd.date_range('2018-01-01',periods=6,freq='h')
    y = pd.Series([0.,1,1,1,1,0],index=idx)
    t = targets(y,'c',boundary=idx[3]); assert t.value.iloc[1] == 2; assert not t.event.iloc[1]
    assert targets(y,'c').value.iloc[1] == 4

def test_seasonal_naive_index(series):
    for h in load_config().horizons:
        ids = np.arange(100,200)
        np.testing.assert_array_equal(baseline('seasonal_naive',series,ids,series.index[50],h),series.iloc[ids+h-24])
        expected = [series.iloc[i+1-24:i+h+1-24].max() for i in ids]
        np.testing.assert_array_equal(baseline('seasonal_naive',series,ids,series.index[50],h,'b'),expected)

def test_label_permutation_canary(observations):
    y = labels(observations); X = features(y); target = targets(y,'a',1).value
    truth = []; pp = []; refs = []; rng = np.random.default_rng(20180101)
    for f in monthly_folds(y.index,1):
        model = logistic(C=.01)
        model.fit(X.iloc[f.train],rng.permutation(target.iloc[f.train]))
        truth.extend(target.iloc[f.test]); pp.extend(model.predict_proba(X.iloc[f.test])[:,1]); refs.extend(baseline('climatology',y,f.test,f.train_end,1))
    assert bss(np.array(truth),np.array(pp),np.array(refs)) <= .01

def test_iid_null_series(series):
    X = features(series); target = targets(series,'a',1).value
    truth = []; predictions = {n:[] for n in ('persistence','climatology','logistic')}
    for f in monthly_folds(series.index,1):
        truth.extend(target.iloc[f.test]); model = logistic(C=.01).fit(X.iloc[f.train],target.iloc[f.train])
        predictions['logistic'].extend(model.predict_proba(X.iloc[f.test])[:,1])
        for name in ('persistence','climatology'): predictions[name].extend(baseline(name,series,f.test,f.train_end,1))
    for name,p in predictions.items(): assert bss(np.array(truth),np.array(p),np.array(predictions['climatology'])) <= .01

def test_randomsplit_quarantine(series):
    split = random_month_split(series.index,0); assert split['quarantine_only']
    assert set(split['train']).isdisjoint(split['test'])
    for folder in (ROOT/'results/S1/wp2_smoke/metrics',ROOT/'results/S1/wp2_smoke/inference'):
        for path in folder.glob('*'):
            if path.suffix in ('.csv','.json'): assert 'randomsplit_' not in path.read_text()

def test_determinism(series):
    X = features(series.iloc[:1000]); y = targets(series,'a',1).value.iloc[:1000]
    a = logistic(C=.01,seed=1).fit(X.iloc[:700],y.iloc[:700]); b = logistic(C=.01,seed=1).fit(X.iloc[:700],y.iloc[:700])
    np.testing.assert_array_equal(a.predict_proba(X.iloc[700:]),b.predict_proba(X.iloc[700:]))
    for name in ('persistence','climatology','seasonal_naive','trailing','markov','recency'):
        args = (name,series,np.arange(800,900),series.index[699],3)
        np.testing.assert_array_equal(baseline(*args),baseline(*args))

@pytest.mark.xfail(strict=True,reason="BG Read Me reconstructs timestamps from row order and partial January validation; Outage Events is derived from those rows. Neither documents whether metered energy is hour-beginning or hour-ending; KR source hour semantics likewise unverified. Independent interval documentation is required.")
def test_label_hour_convention():
    doc = pd.read_excel(RAW/ANALYSIS,sheet_name='Read Me',header=None).astype(str).to_string()
    assert 'hour-beginning' in doc.lower() or 'hour beginning' in doc.lower()

def test_label_definitions(observations):
    primary = labels(observations); gen = labels(observations,'generator_positive')
    np.testing.assert_array_equal(primary,observations.grid_kwh.eq(0).astype(float))
    np.testing.assert_array_equal(gen,observations.generator_kwh.gt(0).astype(float))
    file = ROOT/'results/S1/label_disagreement.csv'
    assert file.exists(), 'Run experiments/s1_wp2_smoke.py to generate label audit'
    saved = pd.read_csv(file); assert len(saved) == (primary != gen).sum()
    assert saved.primary.sum() == primary[primary != gen].sum()

def test_innerval_predictions_exist():
    root = ROOT/'results/S1/wp2_smoke'; paths = list((root/'predictions').glob('*.parquet'))
    assert paths, 'Run the smoke harness before artifact acceptance tests'
    for path in paths:
        inner = root/'predictions/innerval'/path.name; assert inner.exists()
        table = pd.read_parquet(path); saved = pd.read_parquet(inner)
        assert table.threshold.iloc[0] == choose_threshold(saved.y.to_numpy(),saved.p.to_numpy())
        assert saved.origin.max() < table.origin.min()

def test_cache_key(tmp_path):
    paths = [tmp_path/name for name in ('config.yaml','features.py','data.csv')]
    for path in paths: path.write_text('original')
    key = cache_key(paths); artifact = tmp_path/'cache.parquet'; write_predictions(artifact,pd.DataFrame({'x':[1]}),key)
    for path in paths:
        path.write_text('changed'); new = cache_key(paths); assert new != key
        with pytest.raises(ValueError): read_predictions(artifact,new)
        path.write_text('original')
    assert len(read_predictions(artifact,key)) == 1

def test_markov_exact_power():
    m = np.array([[.8,.2],[.3,.7]])
    matrices = np.tile(m,(24,1,1))
    for state in (0,1):
        assert markov_probability(state,0,6,matrices) == pytest.approx(np.linalg.matrix_power(m,6)[state,1])
        expected = 1-m[state,0]*m[0,0]**5
        assert markov_probability(state,0,6,matrices,'b') == pytest.approx(expected)

def test_climatology_hand_computed_and_last_month():
    from eval.climatology import Climatology, trailing
    index = pd.date_range('2018-01-01',periods=60*24,freq='h')
    y = pd.Series(0.,index=index); y.loc[y.index.month == 2] = 1
    fitted = Climatology().fit(y.iloc[:59*24])
    assert fitted.predict(pd.DatetimeIndex([index[0]]),1)[0] == pytest.approx(28.5/60)
    last = Climatology(last_month=True).fit(y.iloc[:59*24])
    assert last.predict(pd.DatetimeIndex([index[0]]),1)[0] == pytest.approx(28.5/29)
    p = trailing(y,np.array([58*24]),1,7,np.array([.2]))
    assert p[0] == pytest.approx(7.5/8)
    assert trailing(y,np.array([24]),1,7,np.array([.2]))[0] == .2


def test_selection_invariant_to_test_predictions(tmp_path):
    from eval.artifacts import write_predictions, select
    inner = tmp_path/'predictions/innerval'
    a = pd.DataFrame({'y':[0,1], 'p':[.2,.8], 'seed':[1,1]})
    b = pd.DataFrame({'y':[0,1], 'p':[.4,.6], 'seed':[1,1]})
    paths = {'a':inner/'a.parquet','b':inner/'b.parquet'}
    write_predictions(paths['a'],a,'key'); write_predictions(paths['b'],b,'key')
    first = select(paths,tmp_path,'key',1e-6)
    write_predictions(tmp_path/'predictions/a.parquet',a.assign(p=[1,0]),'key')
    write_predictions(tmp_path/'predictions/b.parquet',b.assign(p=[0,1]),'key')
    assert select(paths,tmp_path,'key',1e-6) == first
    assert first[0] == 'a'


def test_generic_model_interface(series):
    from eval.runner import fit_predict
    class ConstantModel:
        def fit(self,X,y): self.p = float(np.mean(y)); return self
        def predict_proba(self,X): return np.tile([1-self.p,self.p],(len(X),1))
    X = features(series.iloc[:100]); y = series.iloc[:100]
    pred = fit_predict(ConstantModel(),X,y,np.arange(50),np.arange(50,100))
    assert np.all(pred == y.iloc[:50].mean())
