"""Pareto fronts, regret against the best no-forecast policy, and gap to the oracle.

Plane = (stress x, LPSP y), x = mean_soc_pct or hours_soc_ge_80pct; lower is better on both.
Pareto front: the simulated points not dominated by any other point of the same set (sorted by x).

Regret of a forecast-policy point (x_f, y_f) against the no-forecast (NF) set, two ways:
  regret_step   = y_f - min{ y_b : NF point with x_b <= x_f }
                  (compares only with operating points that were actually simulated; most favourable to forecasts)
  regret_interp = y_f - B(x_f), B = linear interpolation between the two ADJACENT points of the NF Pareto front
                  that bracket x_f (the width of that bracket is reported as interp_bracket_width); for x_f beyond the
                  largest front x, B = the last front point (achievable at lower stress). For x_f below the least
                  stressed NF point both are NaN (no NF policy reaches that stress).
regret < 0 means the forecast policy beats every no-forecast policy at equal (or lower) stress.
Gap to oracle = y - O(x), O = the oracle front with the same interpolation rule (for the LP mean-SOC frontier the
chord lies above the true convex frontier, so the gap is a slight underestimate).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pareto_front(df: pd.DataFrame, x: str, y: str = "LPSP_pct") -> pd.DataFrame:
    """Non-dominated rows (min x, min y), sorted by x."""
    d = df.sort_values([x, y]).reset_index(drop=True)
    keep, best = [], np.inf
    for i, yy in enumerate(d[y].to_numpy()):
        if yy < best - 1e-12:
            keep.append(i)
            best = yy
    return d.iloc[keep].reset_index(drop=True)


def step_value(ref: pd.DataFrame, x: str, xq: np.ndarray, y: str = "LPSP_pct") -> np.ndarray:
    """min y over reference points with x_ref <= xq (NaN if none)."""
    f = pareto_front(ref, x, y)
    xs, ys = f[x].to_numpy(float), f[y].to_numpy(float)
    i = np.searchsorted(xs, xq, side="right") - 1
    return np.where(i >= 0, ys[np.clip(i, 0, None)], np.nan)


def interp_value(ref: pd.DataFrame, x: str, xq: np.ndarray, y: str = "LPSP_pct") -> tuple[np.ndarray, np.ndarray]:
    """Linear interpolation between adjacent front points; returns (value, bracket width)."""
    f = pareto_front(ref, x, y)
    xs, ys = f[x].to_numpy(float), f[y].to_numpy(float)
    xq = np.asarray(xq, float)
    val = np.full(len(xq), np.nan)
    width = np.full(len(xq), np.nan)
    j = np.searchsorted(xs, xq, side="right")       # xs[j-1] <= xq < xs[j]
    inside = (j >= 1) & (j < len(xs))
    a, b = np.clip(j - 1, 0, len(xs) - 1), np.clip(j, 0, len(xs) - 1)
    wa = np.where(inside, (xq - xs[a]) / np.where(xs[b] > xs[a], xs[b] - xs[a], 1.0), 0.0)
    val[inside] = (ys[a] + wa * (ys[b] - ys[a]))[inside]
    width[inside] = (xs[b] - xs[a])[inside]
    beyond = j >= len(xs)
    val[beyond] = ys[-1]
    width[beyond] = 0.0
    return val, width


def regret_table(fc: pd.DataFrame, nf: pd.DataFrame, x: str) -> pd.DataFrame:
    """Per forecast-policy point: regret_step, regret_interp, bracket width."""
    out = fc.copy()
    xq = out[x].to_numpy(float)
    out["nf_step_LPSP"] = step_value(nf, x, xq)
    out["nf_interp_LPSP"], out["interp_bracket_width"] = interp_value(nf, x, xq)
    out["regret_step_pp"] = out["LPSP_pct"] - out["nf_step_LPSP"]
    out["regret_interp_pp"] = out["LPSP_pct"] - out["nf_interp_LPSP"]
    return out


def oracle_gap(points: pd.DataFrame, oracle: pd.DataFrame, x: str) -> np.ndarray:
    v, _ = interp_value(oracle, x, points[x].to_numpy(float))
    return points["LPSP_pct"].to_numpy(float) - v
