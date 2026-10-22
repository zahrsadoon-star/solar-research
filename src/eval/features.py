"""Causal features; explicitly prefixed oracle weather columns."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler
from .config import Config, load_config

def features(y: pd.Series, weather: pd.DataFrame | None = None, setting: str = 'W0', h: int = 1, calendar: pd.DataFrame | None = None, config: Config | None = None) -> pd.DataFrame:
    """Use observed row t and history; W2 alone reads future hours."""
    c = config or load_config()
    out = {f'y_lag_{k}': y.shift(k) for k in c.label_lags}
    change = y.ne(y.shift()).where(y.notna() & y.shift().notna())
    run = []; start_age = []; end_age = []; last_start = last_end = None; length = 0; prev = np.nan
    for i, state in enumerate(y):
        length = length+1 if state == prev else 1
        if state == 1 and prev == 0: last_start = i
        if state == 0 and prev == 1: last_end = i
        run.append(length if np.isfinite(state) else np.nan)
        start_age.append(i-last_start if last_start is not None else np.nan)
        end_age.append(i-last_end if last_end is not None else np.nan)
        prev = state
    out.update(run_length_h=run, since_start_h=start_age, since_end_h=end_age)
    for w in c.count_windows_h: out[f'outage_count_{w}h'] = y.rolling(w, min_periods=w).sum()
    out['changes'] = change.rolling(c.change_window_h).sum()
    out['outage_share'] = y.rolling(c.share_window_h).mean()
    out['hour_sin'] = np.sin(2*np.pi*y.index.hour/c.season_h)
    out['hour_cos'] = np.cos(2*np.pi*y.index.hour/c.season_h)
    out['day_of_week'] = y.index.dayofweek
    out['friday'] = (y.index.dayofweek == c.friday).astype(int)
    if calendar is not None:
        for col in ['holiday', 'ramadan', 'holiday_uncertain']:
            out[col] = calendar[col].reindex(y.index.normalize()).to_numpy()
    if setting not in ('W0', 'W1', 'W2'): raise ValueError(setting)
    if setting != 'W0':
        if weather is None: raise ValueError('Weather required')
        for col in weather:
            for k in c.weather_lags_h: out[f'{col}_lag_{k}'] = weather[col].shift(k)
            out[f'{col}_mean'] = weather[col].rolling(c.weather_mean_h).mean()
            if setting == 'W2':
                for k in range(1, h+1): out[f'oracle_{col}_lead_{k}'] = weather[col].shift(-k)
    return pd.DataFrame(out, index=y.index)

class TrainPreprocessor(BaseEstimator, TransformerMixin):
    """Training-only fills and scaling, with missing indicators (dimensionless)."""
    def fit(self, X: pd.DataFrame, y=None):
        self.columns_ = list(X.columns)
        self.fill_ = X.mean().fillna(0)
        share = X['y_lag_0'].mean() if 'y_lag_0' in X else 0
        self.fill_.loc[[k for k in X if k.startswith('y_lag_')]] = share
        self.scaler_ = StandardScaler().fit(self._filled(X))
        return self
    def _filled(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.columns_]
        return np.c_[X.fillna(self.fill_).to_numpy(), X.isna().to_numpy(dtype=float)]
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        return self.scaler_.transform(self._filled(X))
