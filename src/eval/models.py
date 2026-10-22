"""Reference models. All history updates are causal in observed row time."""
from typing import Protocol
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from .config import Config, load_config
from .features import TrainPreprocessor
from .climatology import Climatology, trailing
from .targets import targets

class ProbabilityModel(Protocol):
    def fit(self, X: pd.DataFrame, y: np.ndarray): ...
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray: ...

def logistic(C: float = 1., penalty: str = 'l2', seed: int = 1, config: Config | None = None):
    """Direct logistic model with training-only preprocessing; probabilities unitless."""
    c = config or load_config()
    return make_pipeline(TrainPreprocessor(), LogisticRegression(C=C, penalty=penalty, solver='liblinear', random_state=seed, max_iter=c.logistic_max_iter, tol=c.logistic_tol))

def transition_matrices(y: pd.Series, config: Config | None = None, hourly: bool = True) -> np.ndarray:
    """Laplace-smoothed source-hour transition matrices; sparse cells fall back."""
    c = config or load_config(); a = y.to_numpy(); counts = np.zeros((c.season_h, 2, 2))
    valid = np.isfinite(a[:-1]) & np.isfinite(a[1:])
    valid &= np.diff(y.index.asi8) == pd.Timedelta(hours=1).value
    source = np.flatnonzero(valid)
    np.add.at(counts, (y.index.hour.to_numpy()[source], a[source].astype(int), a[source+1].astype(int)), 1)
    total = counts.sum(axis=0)+c.prior; total /= total.sum(axis=1, keepdims=True)
    matrices = counts+c.prior; matrices /= matrices.sum(axis=2, keepdims=True)
    for hour in range(c.season_h):
        for state in range(2):
            if not hourly or np.any(counts[hour, state] < c.markov_min_cell): matrices[hour, state] = total[state]
    return matrices

def markov_probability(state: int, hour: int, h: int, matrices: np.ndarray, kind: str = 'a') -> float:
    """Exact ordered matrix product; (b) absorbs at the first future outage."""
    distribution = np.eye(2)[state]
    if kind == 'b':
        # The current outage is not a future event; first transition is unabsorbed.
        distribution = distribution @ matrices[hour % len(matrices)]
        for k in range(1, h):
            matrix = matrices[(hour+k) % len(matrices)].copy(); matrix[1] = [0, 1]
            distribution = distribution @ matrix
    else:
        if np.all(matrices == matrices[0]): return float((distribution @ np.linalg.matrix_power(matrices[0], h))[1])
        for k in range(h): distribution = distribution @ matrices[(hour+k) % len(matrices)]
    return float(distribution[1])

def prepare_baseline(y: pd.Series, fit_end: pd.Timestamp, h: int, kind: str = 'a', config: Config | None = None) -> tuple[Climatology, np.ndarray]:
    """Prepare frozen fold statistics once; online history remains separate."""
    c = config or load_config(); fit = y.loc[:fit_end]
    climate_y = fit if kind == 'a' else targets(fit, kind, h)['value']
    return Climatology(c).fit(climate_y), transition_matrices(fit,c)


def baseline(name: str, y: pd.Series, positions: np.ndarray, fit_end: pd.Timestamp, h: int, kind: str = 'a', window: int | None = None, config: Config | None = None, prepared: tuple[Climatology, np.ndarray] | None = None) -> np.ndarray:
    """Forecast at t using at most labels <= t; fitting stops at fit_end."""
    c = config or load_config()
    if prepared is None: prepared = prepare_baseline(y,fit_end,h,kind,c)
    climate, fitted_matrices = prepared
    fallback = climate.predict(y.index[positions], h, kind)
    if name == 'climatology': return fallback
    if name == 'trailing': return trailing(y, positions, h, window or c.window_days[0], fallback, kind, c)
    a = y.to_numpy(); out = fallback.copy(); matrices = None; cache = {}
    if name == 'markov': matrices = fitted_matrices
    for j, i in enumerate(positions):
        if name == 'persistence': value = a[i]
        elif name == 'seasonal_naive':
            inds = np.array([i+h-c.season_h]) if kind == 'a' else np.arange(i+1-c.season_h, i+h+1-c.season_h)
            if inds.min() < 0 or inds.max() > i: continue
            value = np.max(a[inds])
        elif name in ('markov', 'recency'):
            if not np.isfinite(a[i]): continue
            if name == 'recency':
                midnight = y.index[i].normalize()
                if midnight not in cache:
                    hist = y[(y.index >= midnight-pd.Timedelta(days=window or c.window_days[0])) & (y.index < midnight)]
                    cache[midnight] = transition_matrices(hist, c, hourly=False)
                matrices = cache[midnight]
            value = markov_probability(int(a[i]), y.index[i].hour, h, matrices, kind)
        else: raise ValueError(name)
        if np.isfinite(value): out[j] = value
    return out

