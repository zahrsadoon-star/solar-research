"""Perfect-information oracle (Reviewer 2, M7): linear program over the whole April-December window.

Same physics as simulator_v2 (AC-coupled, eta_inv on every conversion, 0.5 C terminal limit, 10 kW converter, c_min /
c_max, linear self-discharge). The oracle knows every hour's grid status, load and PV in advance.

Per hour t (all kW = kWh/h; pv_load_t = min(pv_ac_t, load_t) is fixed, as PV serves the load first in every policy):
  pc_t  PV surplus into the battery [AC]       0 <= pc_t <= s_t = pv_ac_t - pv_load_t   (rest of s_t is curtailed)
  g_t   grid into the battery [AC]             g_t = 0 in outage hours
  d_t   battery discharge to load [AC]         d_t = 0 in grid-on hours;  d_t <= r_t = load_t - pv_load_t
  u_t   unserved = r_t - d_t in outage hours   (eliminated)
  e_t   stored energy at the end of hour t     c_min <= e_t <= c_max
  e_t = (1 - sigma) e_{t-1} + eta_inv eta_c (pc_t + g_t) - d_t / (eta_d eta_inv),   e_{-1} = e0
  eta_inv (pc_t + g_t) <= 0.5 C;   pc_t + g_t <= 10 kW;   d_t / eta_inv <= 0.5 C;   d_t <= 10 kW - pv_load_t
Objectives (both swept over their weight):
  "meansoc":  min  sum_t u_t + lam * sum_t e_t / C                           (smooth ageing proxy, as specified)
  "hinge80":  min  sum_t u_t + mu * sum_t max(0, e_t - (0.8 C - 0.01 kWh)) / C  (linear surrogate for hours >= 80 %)
The hinge objective is a heuristic for the step cost "hours with SOC >= 80 %"; the exact step-cost oracle would
need a MILP, so the (LPSP, hours >= 80 %) oracle curve is a set of achievable perfect-information schedules, not a
proven lower bound. The mean-SOC curve IS the exact LP frontier at the solved weights.
Solver: scipy.optimize.linprog, method="highs".
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

from simulator_v2 import (C_MAX_FRAC, C_MIN_FRAC, E0_FRAC, ETA_C, ETA_D, ETA_INV, INV_KW, P_MAX_C, SIGMA,
                          simulate)

HINGE_MARGIN_KWH = 0.01


def solve_oracle(load: np.ndarray, grid_on: np.ndarray, pv_dc: np.ndarray, cap_kwh: float, weight: float,
                 objective: str = "meansoc", inv_kw: float = INV_KW, e0_frac: float = E0_FRAC) -> dict:
    """Solve the oracle LP; returns schedules (pc, g, d, e) and the LP's own unserved energy [kWh]."""
    n = len(load)
    C = float(cap_kwh)
    load = np.asarray(load, float)
    on = np.asarray(grid_on, int).astype(bool)
    pv_ac = np.minimum(np.asarray(pv_dc, float), inv_kw) * ETA_INV
    pv_load = np.minimum(pv_ac, load)
    s = pv_ac - pv_load
    r = load - pv_load
    k_in, k_out = ETA_INV * ETA_C, ETA_D * ETA_INV
    ch_ac_max = min(P_MAX_C * C / ETA_INV, inv_kw)
    hinge = objective == "hinge80"
    nv = 5 * n if hinge else 4 * n
    ipc, ig, idd, ie, iz = 0, n, 2 * n, 3 * n, 4 * n
    # objective: sum u = const - sum d
    c = np.zeros(nv)
    c[idd:idd + n] = -1.0
    if hinge:
        c[iz:iz + n] = weight / C
        c[ie:ie + n] = 1e-9           # tie-break so idle SOC is not arbitrary
    else:
        c[ie:ie + n] = weight / C
    bounds = np.zeros((nv, 2))
    bounds[ipc:ipc + n, 1] = np.minimum(s, ch_ac_max)
    bounds[ig:ig + n, 1] = np.where(on, ch_ac_max, 0.0)
    bounds[idd:idd + n, 1] = np.where(on, 0.0, np.maximum(0.0, np.minimum.reduce(
        [r, np.full(n, P_MAX_C * C * ETA_INV), inv_kw - pv_load])))
    bounds[ie:ie + n] = [C_MIN_FRAC * C, C_MAX_FRAC * C]
    if hinge:
        bounds[iz:iz + n] = [0.0, np.inf]
    t = np.arange(n)
    # dynamics: e_t - (1-sigma) e_{t-1} - k_in pc_t - k_in g_t + d_t / k_out = b_t
    rows = np.r_[t, t[1:], t, t, t]
    cols = np.r_[ie + t, ie + t[1:] - 1, ipc + t, ig + t, idd + t]
    vals = np.r_[np.ones(n), np.full(n - 1, -(1 - SIGMA)), np.full(n, -k_in), np.full(n, -k_in),
                 np.full(n, 1.0 / k_out)]
    A_eq = sp.csr_matrix((vals, (rows, cols)), shape=(n, nv))
    b_eq = np.zeros(n)
    b_eq[0] = (1 - SIGMA) * e0_frac * C
    # charging AC limit: pc_t + g_t <= ch_ac_max
    rows_u = [np.r_[t, t]]
    cols_u = [np.r_[ipc + t, ig + t]]
    vals_u = [np.ones(2 * n)]
    b_ub = [np.full(n, ch_ac_max)]
    if hinge:   # e_t - z_t <= 0.8 C - margin
        rows_u.append(np.r_[n + t, n + t]); cols_u.append(np.r_[ie + t, iz + t]); vals_u.append(np.r_[np.ones(n), -np.ones(n)])
        b_ub.append(np.full(n, 0.8 * C - HINGE_MARGIN_KWH))
    nu = 2 * n if hinge else n
    A_ub = sp.csr_matrix((np.concatenate(vals_u), (np.concatenate(rows_u), np.concatenate(cols_u))), shape=(nu, nv))
    res = linprog(c, A_ub=A_ub, b_ub=np.concatenate(b_ub), A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(f"oracle LP failed: {res.message}")
    x = res.x
    d = x[idd:idd + n]
    e = x[ie:ie + n]
    return {"pc": np.clip(x[ipc:ipc + n], 0, None), "g": np.clip(x[ig:ig + n], 0, None), "d": d, "e": e,
            "lp_unserved_kwh": float(np.sum(np.where(on, 0.0, r)) - d.sum()),
            "lp_mean_soc_pct": float(100 * e.mean() / C), "lp_hours_soc_ge_80pct": int(np.sum(e / C >= 0.8)),
            "lp_LPSP_pct": float(100 * (np.sum(np.where(on, 0.0, r)) - d.sum()) / load.sum())}


def oracle_point(load, grid_on, pv_dc, cap_kwh, weight, objective="meansoc") -> dict:
    """Solve the LP and re-simulate its schedule with simulator_v2 (schedule mode); returns both sets of metrics."""
    sol = solve_oracle(load, grid_on, pv_dc, cap_kwh, weight, objective)
    # tiny tolerance so LP round-off does not cut the schedule
    sim = simulate(load, grid_on, pv_dc, cap_kwh, g_sched=sol["g"] * (1 + 1e-9) + 1e-12,
                   pvch_sched=sol["pc"] * (1 + 1e-9) + 1e-12)
    out = {k: v for k, v in sol.items() if k.startswith("lp_")}
    out.update(sim)
    return out
