"""Perfect-information oracle restricted to the policies' action set, by dynamic programming over SOC.

Why in addition to the LP oracle (oracle_lp.py): the LP may curtail PV surplus voluntarily to keep SOC low. No
policy family can do that (every policy stores PV surplus up to c_max). The DP oracle keeps that rule and only
chooses the grid-charging amount in each grid-on hour, with full knowledge of future outages, load and PV. Its
regret is therefore the value of perfect information *within the policy class*; the LP's extra margin is the value
of also controlling PV storage.

Physics are identical to simulator_v2 (self-discharge, PV -> load, PV surplus -> battery, grid charging limited by
0.5 C terminal power and the 10 kW converter, greedy discharge in outages).
Stage cost: unserved_t + w * c(E_t), c = E_t / C ("meansoc") or 1[E_t / C >= 0.8] ("step80"); no terminal value.
State grid: E in [c_min, c_max], M + 1 equally spaced levels; V_{t+1} is linearly interpolated between levels; the
"no grid charging" end state is always a candidate (exact), other candidates are the grid levels within reach.
The chosen schedule is re-simulated with simulator_v2 in schedule mode, so every reported metric comes from the
simulator, not from the discretised DP.
"""
from __future__ import annotations

import numpy as np

from simulator_v2 import C_MAX_FRAC, C_MIN_FRAC, E0_FRAC, ETA_C, ETA_D, ETA_INV, INV_KW, P_MAX_C, SIGMA, simulate


def _stage_cost(x: np.ndarray, C: float, w: float, kind: str) -> np.ndarray:
    if kind == "meansoc":
        return w * x / C
    return w * (x / C >= 0.8)


def solve_dp(load, grid_on, pv_dc, cap_kwh: float, w: float, kind: str = "meansoc", m_levels: int = 200,
             inv_kw: float = INV_KW, e0_frac: float = E0_FRAC) -> np.ndarray:
    """Backward DP then forward pass; returns the grid-charging schedule g_ac [kW AC] for the simulator."""
    load = np.asarray(load, float)
    on = np.asarray(grid_on, int).astype(bool)
    n = len(load)
    C = float(cap_kwh)
    c_min, c_max = C_MIN_FRAC * C, C_MAX_FRAC * C
    p_dc = P_MAX_C * C
    k_in, k_out = ETA_INV * ETA_C, ETA_D * ETA_INV
    pv_ac = np.minimum(np.asarray(pv_dc, float), inv_kw) * ETA_INV
    pv_load = np.minimum(pv_ac, load)
    surplus = pv_ac - pv_load
    rest = load - pv_load
    eg = np.linspace(c_min, c_max, m_levels + 1)
    dE = eg[1] - eg[0]
    K = int(np.ceil(p_dc * ETA_C / dE)) + 2
    ar = np.arange(K)

    def after_pv(e, t):
        e1 = e * (1 - SIGMA)
        ch = np.maximum(0.0, np.minimum.reduce([np.full_like(e1, surplus[t]), (c_max - e1) / k_in,
                                                np.full_like(e1, p_dc / ETA_INV), np.full_like(e1, inv_kw)]))
        e2 = e1 + ch * k_in
        gmax = np.maximum(0.0, np.minimum.reduce([(c_max - e2) / k_in, (p_dc - ch * ETA_INV) / ETA_INV,
                                                  inv_kw - ch]))
        return e2, gmax

    def best_target(e2, gmax, Vn):
        """argmin over reachable end states of w*c(x) + V_{t+1}(x); returns (value, x)."""
        hi = e2 + gmax * k_in
        f0 = _stage_cost(e2, C, w, kind) + np.interp(e2, eg, Vn)
        fg = _stage_cost(eg, C, w, kind) + Vn
        kmin = np.ceil((e2 - c_min) / dE - 1e-9).astype(int)
        kmax = np.floor((hi - c_min) / dE + 1e-9).astype(int)
        idx = kmin[:, None] + ar[None, :]
        valid = idx <= np.minimum(kmax, m_levels)[:, None]
        vals = np.where(valid, fg[np.minimum(idx, m_levels)], np.inf)
        j = vals.argmin(axis=1)
        vbest = vals[np.arange(len(e2)), j]
        use_grid = vbest < f0 - 1e-12
        x = np.where(use_grid, eg[np.minimum(idx[np.arange(len(e2)), j], m_levels)], e2)
        return np.where(use_grid, vbest, f0), x

    V = np.zeros((n + 1, m_levels + 1))
    for t in range(n - 1, -1, -1):
        e2, gmax = after_pv(eg, t)
        Vn = V[t + 1]
        if on[t]:
            V[t], _ = best_target(e2, gmax, Vn)
        else:
            lim_p = min(p_dc * ETA_INV, inv_kw - pv_load[t])
            dis = np.maximum(0.0, np.minimum.reduce([np.full_like(e2, rest[t]), (e2 - c_min) * k_out,
                                                     np.full_like(e2, lim_p)]))
            x = e2 - dis / k_out
            V[t] = (rest[t] - dis) + _stage_cost(x, C, w, kind) + np.interp(x, eg, Vn)
    # forward pass on the continuous state
    g = np.zeros(n)
    e = np.array([e0_frac * C])
    for t in range(n):
        e2, gmax = after_pv(e, t)
        if on[t]:
            _, x = best_target(e2, gmax, V[t + 1])
            g[t] = max(0.0, (x[0] - e2[0]) / k_in)
            e = x
        else:
            lim_p = min(p_dc * ETA_INV, inv_kw - pv_load[t])
            dis = max(0.0, min(rest[t], (e2[0] - c_min) * k_out, lim_p))
            e = e2 - dis / k_out
    return g


def dp_point(load, grid_on, pv_dc, cap_kwh, w, kind="meansoc", m_levels: int = 200) -> dict:
    """DP schedule re-simulated with simulator_v2 (metrics are the simulator's)."""
    g = solve_dp(load, grid_on, pv_dc, cap_kwh, w, kind, m_levels)
    return simulate(load, grid_on, pv_dc, cap_kwh, g_sched=g * (1 + 1e-9) + 1e-12)
