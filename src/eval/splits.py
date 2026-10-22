"""Monthly expanding windows and explicit quarantine controls."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .config import Config, load_config

@dataclass(frozen=True)
class Fold:
    number: int
    train: np.ndarray
    inner_train: np.ndarray
    inner_val: np.ndarray
    test: np.ndarray
    train_end: pd.Timestamp
    inner_end: pd.Timestamp

def monthly_folds(index: pd.DatetimeIndex, h: int, config: Config | None = None) -> list[Fold]:
    """Purge fitting origins by maximum horizon; no first-test-day deletion."""
    c = config or load_config()
    out = []
    for month in range(c.first_test_month, c.last_test_month+1):
        start = pd.Timestamp(year=index[0].year, month=month, day=1, tz=index.tz)
        end = start-pd.Timedelta(hours=1)
        inner_start = start-pd.DateOffset(months=1)
        inner_end = inner_start-pd.Timedelta(hours=1)
        out.append(Fold(len(out)+1, np.flatnonzero(index+pd.Timedelta(hours=c.purge_h) <= end), np.flatnonzero(index+pd.Timedelta(hours=c.purge_h) <= inner_end), np.flatnonzero((index >= inner_start) & (index+pd.Timedelta(hours=h) <= end)), np.flatnonzero((index.month == month) & (index+pd.Timedelta(hours=h) <= index[-1])), end, inner_end))
    return out

class TestIndexGuard:
    """Reject every read while tuning, thresholding, or selecting."""
    def __init__(self, indices: np.ndarray):
        self.__indices = indices.copy()
        self.phase = 'tuning'
    def access(self) -> np.ndarray:
        if self.phase != 'evaluation':
            raise RuntimeError('Test indices unavailable during tuning/selection/thresholds')
        return self.__indices.copy()

def random_month_split(index: pd.DatetimeIndex, seed: int, config: Config | None = None) -> dict:
    """Thesis-style random draws; output is always quarantine-only."""
    c = config or load_config(); rng = np.random.default_rng(seed)
    test = np.concatenate([rng.choice(np.flatnonzero(index.month == m), int(sum(index.month == m)*c.random_test_fraction), replace=False) for m in np.unique(index.month)])
    return {'train': np.setdiff1d(np.arange(len(index)), test), 'test': np.sort(test), 'quarantine_only': True, 'run_id': f'randomsplit_{seed}'}
