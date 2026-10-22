"""Consumption-derived labels and horizon/duration targets (hours)."""
import numpy as np
import pandas as pd

def labels(frame: pd.DataFrame, definition: str = 'grid_zero') -> pd.Series:
    """Return a proxy label, preserving missing source energy (kWh)."""
    column, op = {'grid_zero': ('grid_kwh', lambda x: x == 0), 'generator_positive': ('generator_kwh', lambda x: x > 0)}[definition]
    return op(frame[column]).astype(float).where(frame[column].notna()).rename('y')

def targets(y: pd.Series, kind: str, h: int = 1, boundary: pd.Timestamp | None = None) -> pd.DataFrame:
    """Construct targets; duration censor time is the last observed hour."""
    s = y if boundary is None else y.where(y.index <= boundary)
    if kind in ('a', 'b'):
        future = pd.concat([s.shift(-k) for k in ([h] if kind == 'a' else range(1, h+1))], axis=1)
        value = future.max(axis=1).where(future.notna().all(axis=1) & s.notna())
        return pd.DataFrame({'value': value, 'event': value.notna(), 'label_time': y.index + pd.Timedelta(hours=h)}, index=y.index)
    if kind != 'c':
        raise ValueError(kind)
    a = s.to_numpy(); n = len(a)
    values = np.full(n, np.nan); events = np.zeros(n, dtype=bool)
    stops = np.arange(n); next_zero = None; boundary_pos = n-1
    for i in range(n-1, -1, -1):
        if not np.isfinite(a[i]):
            next_zero = None; boundary_pos = i-1
        elif a[i] == 0:
            next_zero = i
        else:
            event = next_zero is not None
            stop = next_zero if event else boundary_pos
            values[i] = stop-i; events[i] = event; stops[i] = stop
    return pd.DataFrame({'value': values, 'event': events, 'label_time': y.index[stops]}, index=y.index)
