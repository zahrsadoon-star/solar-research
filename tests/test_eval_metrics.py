"""Hand-computed correctness fixtures and seeded dependence simulation."""
import numpy as np
import pytest
from scipy import stats
from eval.config import load_config
from eval.metrics import brier, bss, log_loss, reliability, ece, classification, duration_mae, harrell_c, choose_threshold
from eval.inference import dm, bootstrap, holm, descriptive_ranks, circular_indices, pw_circular, block_length

def test_metrics_hand_computed():
    y = np.array([0,1,0,1]); p = np.array([.1,.8,.4,.7])
    assert brier(y,p) == pytest.approx(.075)
    assert bss(y,p,np.full(4,.5)) == pytest.approx(.7)
    assert log_loss(y,p) == pytest.approx(-np.log(.9*.8*.6*.7)/4)
    assert log_loss(np.array([0,1]),np.array([1,0])) == pytest.approx(-np.log(.001))
    m = classification(y,p,.5)
    assert m['roc_auc'] == 1; assert m['pr_auc'] == 1
    assert m['mcc'] == 1; assert m['f1'] == 1
    assert ece(y,p,2) == pytest.approx(.25)
    r = reliability(y,p,2)
    assert r['count'].tolist() == [2,2]
    assert r.mean_prediction.tolist() == pytest.approx([.25,.75])
    assert r.frequency.tolist() == [0,1]
    assert choose_threshold(y,p) == .7
    ties = classification(np.array([0,1]),np.array([.5,.5]),.5)
    assert ties['roc_auc'] == .5; assert ties['pr_auc'] == .5
    assert ties['mcc'] == 0; assert ties['f1'] == pytest.approx(2/3)
    assert reliability(np.array([1]),np.array([1.]))['count'].iloc[-1] == 1
    assert np.isnan(bss(y,p,y))

def test_duration_metrics_hand_computed():
    assert duration_mae(np.array([1,3,5]),np.array([2,9,3]),np.array([1,0,1])) == 1.5
    assert harrell_c(np.array([1,2,3]),np.array([1,3,2]),np.ones(3)) == pytest.approx(2/3)
    assert harrell_c(np.array([1,2,3]),np.array([1,1,2]),np.ones(3)) == pytest.approx(5/6)
    assert harrell_c(np.array([1,2,3]),np.array([9,1,2]),np.array([0,1,1])) == 1

def test_dm_hand_computed():
    # d=[1,2,3,4], centered=[-1.5,-.5,.5,1.5], gamma0=1.25,
    # gamma1=.3125, Bartlett(1)=.5: Omega=1.5625; HLN=sqrt(3/4).
    result = dm(np.array([1.,2.,3.,4.]),1,1)
    expected = 2.5/np.sqrt(1.5625/4)*np.sqrt(3/4)
    assert result['hac_variance'] == 1.5625
    assert result['statistic'] == pytest.approx(expected)
    assert result['pvalue'] == pytest.approx(2*stats.t.sf(expected,3))

def test_bootstrap_ar1_coverage():
    # Fixed before execution: rho=.5, n=720, 40 replications, B=199,
    # block=48, nominal=.95; acceptance .80..1.00 (finite-MC tolerance).
    c = load_config(); rng = np.random.default_rng(c.ar1_seed); covered = 0
    for replication in range(c.ar1_replications):
        innovations = rng.normal(size=c.ar1_n+c.ar1_burnin); x = np.zeros(len(innovations))
        for i in range(1,len(x)): x[i] = c.ar1_rho*x[i-1]+innovations[i]
        x = x[c.ar1_burnin:]; result = bootstrap(x,np.repeat([1,2],c.ar1_n//2),np.mean,c.block_default_h,B=c.ar1_B,seed=c.bootstrap_seed+replication)
        covered += result['lower'] <= 0 <= result['upper']
    assert c.ar1_coverage_min <= covered/c.ar1_replications <= c.ar1_coverage_max

def test_bootstrap_pairing_and_months():
    month = np.repeat([1,2],50); ids = circular_indices(month,12,np.random.default_rng(1))
    assert (month[ids[:50]] == 1).all(); assert (month[ids[50:]] == 2).all()
    x = np.c_[np.arange(100),np.arange(100)]
    out = bootstrap(x,month,lambda a: np.mean(a[:,0]-a[:,1]),12,B=20)
    assert out['lower'] == out['upper'] == 0
    assert block_length(np.zeros(100),month) == 48
    assert pw_circular(np.zeros(100)) == 0

def test_holm_explicit_and_descriptive_ranks():
    assert holm({'a':.01,'b':.04,'c':.03},['a','b','c']) == {'a':.03,'c':.06,'b':.06}
    with pytest.raises(ValueError): holm({'a':.1})
    result = descriptive_ranks(np.tile([1.,2.,3.],(9,1)))
    assert result['mean_ranks'] == [1,2,3]
    assert result['critical_difference'] == pytest.approx(stats.studentized_range.ppf(.95,3,np.inf)/np.sqrt(2)*np.sqrt(12/54))
    assert 'pvalue' not in result
