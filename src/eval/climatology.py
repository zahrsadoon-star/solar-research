"""Smoothed training-only and per-origin hour-of-day climatologies."""
import numpy as np
import pandas as pd
from .config import Config, load_config
from .targets import targets

class Climatology:
    """Fit probabilities by observed hour (a) or origin hour (b)."""
    def __init__(self, config: Config | None = None, last_month: bool = False):
        self.c = config or load_config(); self.last_month = last_month
    def fit(self, y: pd.Series):
        if self.last_month: y = y[y.index.month == y.index[-1].month]
        grouped = y.groupby(y.index.hour).agg(['sum', 'count']).reindex(range(self.c.season_h), fill_value=0)
        self.probabilities_ = (grouped['sum']+self.c.prior)/(grouped['count']+2*self.c.prior)
        return self
    def predict(self, origins: pd.DatetimeIndex, h: int, kind: str = 'a') -> np.ndarray:
        hours = (origins.hour+h) % self.c.season_h if kind == 'a' else origins.hour
        return self.probabilities_.loc[hours].to_numpy()

def trailing(y: pd.Series, positions: np.ndarray, h: int, days: int, fallback: np.ndarray, kind: str = 'a', config: Config | None = None) -> np.ndarray:
    """Use same-hour daily samples whose entire target is observed by row t."""
    c = config or load_config(); a = y.to_numpy(); result = []
    k0 = int(np.ceil(h/c.season_h))
    for i, base in zip(positions, fallback):
        idx = i-c.season_h*np.arange(k0, k0+days)+(h if kind == 'a' else 0)
        idx = idx[idx >= 0]
        if kind == 'b':
            windows = a[idx[:,None]+np.arange(1,h+1)]
            sample = windows.max(axis=1) if len(idx) else np.array([])
            sample = np.where(np.isfinite(a[idx]),sample,np.nan)
        else: sample = a[idx]
        sample = sample[np.isfinite(sample)]
        result.append((sample.sum()+c.prior)/(len(sample)+2*c.prior) if len(sample) >= c.minimum_daily_samples else base)
    return np.array(result)
