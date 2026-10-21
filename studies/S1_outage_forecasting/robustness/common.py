"""Shared paths/helpers for the S1 robustness analysis. Imports the pilot code instead of copying it.

NOTE: pilot/pareto.py runs its whole analysis at import time and writes into pilot/results/, so it is never
imported here; its settings (PV 8 kWp, 10.2 kWh, theta grid 0.05..0.95) are restated below and documented.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "pilot"
REPO = HERE.parents[2]
for p in (str(PILOT), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
SITES = ["BG", "KR"]

# pareto.py settings (restated, not imported - see module docstring)
PARETO_PV_KWP = 8.0
PARETO_CAP_KWH = 10.2
PARETO_THETAS = np.round(np.arange(0.05, 0.96, 0.05), 2)


def test_index(d: pd.DataFrame, h: int, with_temp: bool = False) -> dict[int, pd.DatetimeIndex]:
    """Issue times t of the test rows of pilot_s1.evaluate_site for horizon h, per test month (same masks)."""
    from pilot_s1 import features, target
    X_all = features(d, with_temp)
    y_all = target(d, h)
    ok = X_all.notna().all(axis=1) & y_all.notna()
    X, y = X_all[ok], y_all[ok].astype(int)
    t_target = X.index + pd.Timedelta(hours=h)
    out = {}
    for m in range(4, 13):
        tr = (X.index.month < m) & (t_target < pd.Timestamp(f"2018-{m:02d}-01"))
        te = X.index.month == m
        if y[te].nunique() < 2 or tr.sum() < 500:
            continue
        out[m] = X.index[te]
    return out


def frontier_lpsp_at(hours: np.ndarray, lpsp: np.ndarray, at: float) -> float:
    """LPSP on a forecaster's theta frontier at a given number of high-SOC hours (linear interpolation after
    sorting by hours; this reproduces the REPORT.md numbers, e.g. BG RF 4.07 %, Logistic 3.96 %).
    Returns NaN if `at` lies outside the frontier's range (no extrapolation)."""
    o = np.argsort(hours, kind="stable")
    h, l = np.asarray(hours, float)[o], np.asarray(lpsp, float)[o]
    if at < h[0] or at > h[-1]:
        return np.nan
    # collapse duplicate x values (mean LPSP) so np.interp is well defined
    hu, inv = np.unique(h, return_inverse=True)
    lu = np.bincount(inv, weights=l) / np.bincount(inv)
    return float(np.interp(at, hu, lu))
