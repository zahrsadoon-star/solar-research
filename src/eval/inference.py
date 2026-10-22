"""Serial-dependence-aware inference. Exploratory summaries omit p-values."""
from collections.abc import Callable
import numpy as np
import pandas as pd
from scipy import stats
from .config import Config, load_config

def pw_circular(x: np.ndarray) -> float:
    """Corrected PW circular length in observations.

    Algorithm: arch.bootstrap.optimal_block_length documentation/source,
    https://arch.readthedocs.io/en/latest/_modules/arch/bootstrap/base.html
    Politis-White with Patton-Politis-White correction. Constants below belong
    to that published estimator, not study tuning choices.
    """
    x = np.asarray(x, dtype=float); n = len(x)
    if n < 3 or not np.isfinite(x).all(): raise ValueError('PW requires finite observations')
    z = x-x.mean()
    if not np.any(z): return 0.
    kn = max(5, int(np.log10(n))); maximum = min(int(np.ceil(np.sqrt(n)))+kn, n-2)
    cutoff = 2*np.sqrt(np.log10(n)/n)
    covariance = np.array([z[k:] @ z[:n-k]/n for k in range(maximum+1)])
    corr = np.array([abs(z[k:] @ z[:n-k])/np.sqrt((z[k+1:] @ z[k+1:])*(z[:-(k+1)] @ z[:-(k+1)])) if (z[k+1:] @ z[k+1:])*(z[:-(k+1)] @ z[:-(k+1)]) > 0 else np.inf for k in range(maximum+1)])
    stop = next((i-kn for i in range(kn, maximum+1) if np.all(corr[i-kn:i] < cutoff)), None)
    m = min(2*max(stop,1) if stop is not None else maximum, maximum)
    k = np.arange(1,m+1); weight = np.minimum(1., 2*(1-k/m))
    g = 2*np.sum(weight*k*covariance[1:m+1]); lrv = covariance[0]+2*np.sum(weight*covariance[1:m+1])
    if lrv == 0: return float(np.ceil(min(3*np.sqrt(n), n/3)))
    return float(min((2*g*g/((4/3)*lrv*lrv)*n)**(1/3), np.ceil(min(3*np.sqrt(n),n/3))))

def block_length(d: np.ndarray, months: np.ndarray, config: Config | None = None) -> int:
    """Pool and monthly PW, round upward to a day, then clip (hours)."""
    c = config or load_config(); months = np.asarray(months); d = np.asarray(d)
    values = [pw_circular(d[months == m]) for m in np.unique(months)]
    raw = max(pw_circular(d), np.median(values))
    return int(np.clip(c.block_round_h*np.ceil(raw/c.block_round_h), c.block_min_h,c.block_max_h))

def dm(d: np.ndarray, h: int, lag: int) -> dict:
    """Globally demeaned Bartlett HAC, HLN, two-sided t reference."""
    d = np.asarray(d,dtype=float); n = len(d)
    if not np.isfinite(d).all() or n <= h or lag < h-1: raise ValueError('Invalid DM sample/horizon/lag')
    z = d-d.mean(); used = min(lag,n-1)
    omega = z@z/n+2*sum((1-k/(lag+1))*(z[k:]@z[:-k])/n for k in range(1,used+1))
    factor = np.sqrt((n+1-2*h+h*(h-1)/n)/n)
    statistic = d.mean()/np.sqrt(omega/n)*factor if omega > 0 else np.nan
    return {'difference': float(d.mean()), 'hac_variance': float(omega), 'hln': float(factor), 'statistic': float(statistic), 'pvalue': float(2*stats.t.sf(abs(statistic),n-1)), 'lag': lag}

def circular_indices(months: np.ndarray, length: int, rng: np.random.Generator) -> np.ndarray:
    """Same paired indices for all models; blocks wrap within each month."""
    months = np.asarray(months); selected = []
    for month in np.unique(months):
        positions = np.flatnonzero(months == month); n = len(positions)
        starts = rng.integers(0,n,size=int(np.ceil(n/length)))
        local = ((starts[:,None]+np.arange(length)) % n).ravel()[:n]
        selected.append(positions[local])
    return np.concatenate(selected)

def bootstrap(values: np.ndarray, months: np.ndarray, statistic: Callable, length: int, B: int | None = None, seed: int | None = None, method: str = 'percentile', config: Config | None = None) -> dict:
    """Paired monthly circular bootstrap; BCa uses delete-block acceleration.

    Delete nonoverlapping blocks within months for acceleration, preserving
    dependence. This implementation choice is disclosed for lead review.
    """
    c = config or load_config(); B = c.bootstrap_B if B is None else B
    rng = np.random.default_rng(c.bootstrap_seed if seed is None else seed)
    values = np.asarray(values); months = np.asarray(months); point = float(statistic(values))
    draws = np.array([statistic(values[circular_indices(months,length,rng)]) for _ in range(B)])
    quantiles = np.array([c.alpha/2, 1-c.alpha/2])
    if method == 'bca':
        jack = []
        for m in np.unique(months):
            ids = np.flatnonzero(months == m)
            for start in range(0,len(ids),length):
                keep = np.ones(len(values),bool); keep[ids[start:start+length]] = False
                jack.append(statistic(values[keep]))
        centered = np.mean(jack)-np.asarray(jack); den = 6*np.sum(centered**2)**1.5
        acceleration = np.sum(centered**3)/den if den else 0.
        fraction = (sum(draws < point)+.5*sum(draws == point))/B
        z0 = stats.norm.ppf(np.clip(fraction, .5/B,1-.5/B)); z = stats.norm.ppf(quantiles)
        quantiles = stats.norm.cdf(z0+(z0+z)/(1-acceleration*(z0+z)))
    elif method != 'percentile': raise ValueError(method)
    if not np.isfinite(draws).all(): raise ValueError('Undefined bootstrap statistic; report not assessable')
    lo,hi = np.quantile(draws,quantiles)
    return {'estimate': point, 'lower': float(lo), 'upper': float(hi), 'B': B, 'block_h': length, 'method': method}

def holm(pvalues: dict[str,float], hypotheses: list[str] | None = None, config: Config | None = None) -> dict[str,float]:
    """Adjust exactly the declared family; reject missing or extra hypotheses."""
    family = (config or load_config()).q1_hypotheses if hypotheses is None else hypotheses
    if set(pvalues) != set(family): raise ValueError('P-values must match explicit hypothesis family')
    order = sorted(family,key=pvalues.get); result = {}; previous = 0.
    for i,key in enumerate(order):
        previous = max(previous,min(1., (len(order)-i)*pvalues[key])); result[key] = previous
    return result

def descriptive_ranks(losses: np.ndarray, alpha: float | None = None) -> dict:
    """Friedman statistic and Nemenyi CD per horizon; dependent folds, descriptive."""
    a = np.asarray(losses); n,k = a.shape; ranks = stats.rankdata(a,axis=1)
    q = stats.studentized_range.ppf(1-(load_config().alpha if alpha is None else alpha),k,np.inf)/np.sqrt(2)
    return {'label': 'descriptive only; monthly folds are dependent', 'ranks': ranks.tolist(), 'mean_ranks': ranks.mean(axis=0).tolist(), 'friedman_statistic': float(stats.friedmanchisquare(*a.T).statistic), 'critical_difference': float(q*np.sqrt(k*(k+1)/(6*n))), 'folds': n}


def hac_lag(h: int, length: int, config: Config | None = None) -> int:
    """Resolve the declared HAC bandwidth in hours, never below h-1."""
    c = config or load_config()
    if c.hac_method == 'block_length': return max(h-1, length)
    if c.hac_method == 'default_block': return max(h-1, c.block_default_h)
    raise ValueError('Unknown HAC method')


def fixed_b_critical(length: int, n: int, config: Config | None = None) -> float:
    """Unverified-primary-source fixed-b polynomial: sensitivity only."""
    c = config or load_config()
    return float(np.polynomial.polynomial.polyval(length/n, c.fixed_b_coefficients))
