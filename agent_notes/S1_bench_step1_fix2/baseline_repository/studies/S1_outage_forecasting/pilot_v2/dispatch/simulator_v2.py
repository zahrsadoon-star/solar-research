"""Hourly PV-battery dispatch simulator, version 2 (answers Reviewer 2, SHOULD-FIX 5 and M3).

Starts from the logic of pilot/dispatch_value.simulate (thesis simulate_ems) and changes only what the review asked:

Topology (explicit, AC-coupled): PV -> PV inverter (10 kW AC, eta_inv = 0.98) -> AC bus; the battery sits behind a
bidirectional converter with the same eta_inv = 0.98 and shares the 10 kW AC limit.
  PV        pv_ac = min(pv_dc, 10 kW) * eta_inv                    clipped = max(pv_dc - 10 kW, 0)   [kWh DC]
  charge    stored = P_ac_in * eta_inv * eta_c                    (PV surplus or grid; AC side)
  discharge P_ac_out = DC_out * eta_inv = stored_removed * eta_d * eta_inv
  limits    DC power at the battery terminal <= 0.5 C (charge: P_ac_in*eta_inv; discharge: stored*eta_d);
            AC through the converter <= 10 kW; discharge AC <= 10 kW - PV-to-load AC (shared inverter, as in v1)
  energy    c_min = 0.05 C <= E <= c_max = 0.98 C; self-discharge E *= (1 - 2e-5) at the start of every hour
  SOC       one definition everywhere: SOC = E / C (nominal capacity C, kWh)
Hourly order (as v1): self-discharge; PV -> load; PV surplus -> battery (always, up to c_max; may be capped by an
exogenous schedule); then, if the grid is on, the rest of the load from the grid and the policy's grid charging;
if the grid is off, battery discharge serves the rest of the load (never more), the remainder is unserved.

Information: the policy's grid-charging decision for hour t is given by per-hour arrays built *before* the loop
(see policy builders): trig[t] (charge while SOC at the start of hour t < trig[t]), tcap[t] (stop at E = tcap*C),
rate[t] (grid-charging DC power, in C). Builders use only information available at the start of hour t:
grid status of hour t (observable at its start), SOC at the start of hour t, PV of hour t-1, forecasts issued at the
start of hour t. PV of hour t is not used by any decision (it only enters the physics).

Outputs (Apr-Dec window): LPSP_pct = 100 * unserved / load; unserved_kwh; grid_import_kwh (load + charging);
grid_to_battery_kwh (AC); pv_curtailed_kwh (AC PV surplus the battery could not take); pv_clipped_kwh (DC above the
inverter rating); battery_EFC = energy removed from storage / C; mean_soc_pct (end-of-hour SOC); hours_soc_ge_80pct
(end-of-hour SOC >= 0.80); unserved_energy_limited_kwh / unserved_power_limited_kwh (which bound stopped discharge);
balance_residual_kwh (sources - sinks - storage change; must be ~0).
"""
from __future__ import annotations

import numpy as np

ETA_C = 0.95
ETA_D = 0.95
ETA_INV = 0.98
SIGMA = 2e-5          # self-discharge [1/h]
C_MIN_FRAC = 0.05
C_MAX_FRAC = 0.98
P_MAX_C = 0.5         # battery terminal power limit [C]
INV_KW = 10.0
E0_FRAC = (C_MIN_FRAC + C_MAX_FRAC) / 2   # initial SOC, as v1
NIGHT_PV_KW = 0.1     # Mode 0 "night" test (AC PV of hour t-1 below this)


def simulate(load: np.ndarray, grid_on: np.ndarray, pv_dc: np.ndarray, cap_kwh: float,
             trig: np.ndarray | None = None, tcap: np.ndarray | None = None, rate: np.ndarray | None = None,
             *, g_sched: np.ndarray | None = None, pvch_sched: np.ndarray | None = None,
             e0_frac: float = E0_FRAC, inv_kw: float = INV_KW, return_series: bool = False) -> dict:
    """Simulate one policy. Arrays are hourly over the evaluation window.

    load [kWh/h = kW], grid_on [0/1], pv_dc [kW DC], cap_kwh = nominal capacity C [kWh].
    Policy mode: trig/tcap [SOC fraction], rate [C]; omitted trig = never grid-charge (PV-only).
    Schedule mode (oracle re-simulation): g_sched [kW AC from grid into the converter], pvch_sched [kW AC of PV
    surplus allowed into the battery]; both are clipped to the physical limits.
    """
    n = len(load)
    C = float(cap_kwh)
    c_max, c_min = C_MAX_FRAC * C, C_MIN_FRAC * C
    p_dc = P_MAX_C * C
    k_in = ETA_INV * ETA_C                # stored per AC kWh in
    k_out = ETA_D * ETA_INV               # AC out per stored kWh
    sched = g_sched is not None
    L = np.asarray(load, float).tolist()
    G = np.asarray(grid_on, int).tolist()
    P = np.asarray(pv_dc, float).tolist()
    if sched:
        GS = np.asarray(g_sched, float).tolist()
        PS = (np.asarray(pvch_sched, float) if pvch_sched is not None else np.full(n, np.inf)).tolist()
    else:
        TR = (np.zeros(n) if trig is None else np.broadcast_to(np.asarray(trig, float), (n,))).tolist()
        TC = (np.ones(n) if tcap is None else np.broadcast_to(np.asarray(tcap, float), (n,))).tolist()
        RT = (np.full(n, P_MAX_C) if rate is None else np.broadcast_to(np.asarray(rate, float), (n,))).tolist()
    e = e0_frac * C
    e_init = e
    unserved = un_energy = un_power = grid_load = grid_ch = curtailed = clipped = 0.0
    inv_loss_pv = loss_ch = loss_dis = selfdis = removed = 0.0
    soc_sum = 0.0
    high = 0
    if return_series:
        s_e = np.empty(n); s_g = np.empty(n); s_un = np.empty(n); s_ch = np.empty(n); s_dis = np.empty(n)
    for t in range(n):
        soc_start = e / C
        sd = e * SIGMA
        e -= sd
        selfdis += sd
        pv = P[t]
        clip = pv - inv_kw if pv > inv_kw else 0.0
        clipped += clip
        pv_in = pv - clip
        pv_ac = pv_in * ETA_INV
        inv_loss_pv += pv_in - pv_ac
        lt = L[t]
        pv_load = pv_ac if pv_ac < lt else lt
        surplus = pv_ac - pv_load
        rest = lt - pv_load
        # PV surplus -> battery (AC side), limited by headroom, 0.5 C DC, converter AC rating
        ch = min(surplus, (c_max - e) / k_in, p_dc / ETA_INV, inv_kw)
        if sched and PS[t] < ch:
            ch = PS[t]
        if ch < 0.0:
            ch = 0.0
        e += ch * k_in
        loss_ch += ch * (1.0 - k_in)
        curtailed += surplus - ch
        g = 0.0
        dis = 0.0
        if G[t]:
            grid_load += rest
            if sched:
                want = GS[t]
                head = c_max
            else:
                want = np.inf if soc_start < TR[t] else 0.0
                head = TC[t] * C
                if head > c_max:
                    head = c_max
                lim_rate = RT[t] * C / ETA_INV
                if want > lim_rate:
                    want = lim_rate
            g = min(want, (head - e) / k_in, (p_dc - ch * ETA_INV) / ETA_INV, inv_kw - ch)
            if g < 0.0:
                g = 0.0
            e += g * k_in
            loss_ch += g * (1.0 - k_in)
            grid_ch += g
        else:
            lim_e = (e - c_min) * k_out
            lim_p = min(p_dc * ETA_INV, inv_kw - pv_load)
            dis = min(rest, lim_e, lim_p)
            if dis < 0.0:
                dis = 0.0
            out = dis / k_out
            e -= out
            removed += out
            loss_dis += out - dis
            u = rest - dis
            if u > 1e-12:
                unserved += u
                if lim_e <= lim_p:
                    un_energy += u
                else:
                    un_power += u
        soc = e / C
        soc_sum += soc
        if soc >= 0.8:
            high += 1
        if return_series:
            s_e[t] = e; s_g[t] = g; s_un[t] = rest - dis if not G[t] else 0.0; s_ch[t] = ch; s_dis[t] = dis
    total_load = float(np.sum(load))
    pv_total = float(np.sum(pv_dc))
    grid_import = grid_load + grid_ch
    sources = pv_total + grid_import + unserved + e_init
    sinks = total_load + clipped + curtailed + inv_loss_pv + loss_ch + loss_dis + selfdis + e
    res = {"LPSP_pct": 100.0 * unserved / total_load if total_load > 0 else 0.0,"unserved_kwh": unserved, "grid_import_kwh": grid_import,
           "grid_to_battery_kwh": grid_ch, "pv_curtailed_kwh": curtailed, "pv_clipped_kwh": clipped,
           "battery_EFC": removed / C, "mean_soc_pct": 100.0 * soc_sum / n, "hours_soc_ge_80pct": high,
           "unserved_energy_limited_kwh": un_energy, "unserved_power_limited_kwh": un_power,
           "conversion_loss_kwh": inv_loss_pv + loss_ch + loss_dis, "self_discharge_kwh": selfdis,
           "balance_residual_kwh": sources - sinks}
    if return_series:
        res["series"] = {"e_kwh": s_e, "grid_ch_ac": s_g, "unserved": s_un, "pv_ch_ac": s_ch, "dis_ac": s_dis}
    return res


# ----------------------------------------------------------------------------- policy builders
# Each returns (trig, tcap, rate) arrays over the window; all use only start-of-hour information.
Policy = tuple[np.ndarray, np.ndarray, np.ndarray]


def _full(n: int, v: float) -> np.ndarray:
    return np.full(n, float(v))


def pv_only(n: int) -> Policy:
    """Battery charged from PV surplus only."""
    return _full(n, 0.0), _full(n, 1.0), _full(n, P_MAX_C)


def soc_trigger(n: int, s: float, rate_c: float = P_MAX_C) -> Policy:
    """No-forecast rule as specified: grid charges at `rate_c` whenever the grid is on and SOC < s (may overshoot
    s within the hour, bounded by c_max)."""
    return _full(n, s), _full(n, 1.0), _full(n, rate_c)


def soc_target(n: int, s: float, rate_c: float = P_MAX_C) -> Policy:
    """No-forecast SOC target: grid charges at `rate_c` while SOC < s and stops at SOC = s."""
    return _full(n, s), _full(n, s), _full(n, rate_c)


def pv_ac_prev(pv_dc_full: np.ndarray, mask: np.ndarray, inv_kw: float = INV_KW) -> np.ndarray:
    """AC PV of hour t-1 for every hour t in the window (hour 0 of the year uses 0)."""
    ac = np.minimum(pv_dc_full, inv_kw) * ETA_INV
    return np.r_[0.0, ac[:-1]][mask]


def mode0(pv_prev_ac: np.ndarray, rate_c: float = 0.25, threshold: float = 0.8) -> Policy:
    """Thesis Mode 0: grid charging at night while SOC < threshold. 'Night' = AC PV of the previous hour < 0.1 kW
    (PV of hour t is not known at its start). SOC = E / C (fixes v1's E / c_max)."""
    n = len(pv_prev_ac)
    trig = np.where(pv_prev_ac < NIGHT_PV_KW, threshold, 0.0)
    return trig, _full(n, 1.0), _full(n, rate_c)


def binary_topup(risk: np.ndarray, theta: float) -> Policy:
    """Forecast-triggered top-up: grid charges at 0.5 C (up to c_max) when risk_t > theta."""
    n = len(risk)
    return np.where(risk > theta, 2.0, 0.0), _full(n, 1.0), _full(n, P_MAX_C)


def risk_target(risk: np.ndarray, s_low: float, s_high: float = 1.0) -> Policy:
    """Forecast-dependent SOC target: target_t = s_low + (s_high - s_low) * risk_t; charge at 0.5 C while
    SOC < target_t and stop at target_t."""
    tgt = s_low + (s_high - s_low) * np.clip(risk, 0.0, 1.0)
    return tgt, tgt, _full(len(risk), P_MAX_C)
