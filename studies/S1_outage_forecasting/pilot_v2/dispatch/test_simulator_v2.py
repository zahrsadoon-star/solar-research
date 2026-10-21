"""Hand-checked unit tests for simulator_v2, the oracles and the start-of-hour information rules.
Run: /home/claude/venv/bin/python -m pytest -q   (from this folder)"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import simulator_v2 as S
from oracle_dp import dp_point
from oracle_lp import oracle_point

SIG, KIN, KOUT = S.SIGMA, S.ETA_INV * S.ETA_C, S.ETA_D * S.ETA_INV


def one(load, on, pv, cap, pol=None, **kw):
    n = len(load)
    pol = pol if pol is not None else S.pv_only(n)
    return S.simulate(np.array(load, float), np.array(on), np.array(pv, float), cap, *pol, return_series=True, **kw)


def test_discharge_pays_inverter_and_battery_efficiency():
    r = one([1.0], [0], [0.0], 10.0, e0_frac=0.98)
    e_exp = 9.8 * (1 - SIG) - 1.0 / (0.95 * 0.98)          # 1 kWh AC needs 1.07411 kWh from storage
    assert r["series"]["e_kwh"][0] == pytest.approx(e_exp, abs=1e-12)
    assert r["unserved_kwh"] == 0 and r["battery_EFC"] == pytest.approx(1 / (0.95 * 0.98) / 10)
    assert abs(r["balance_residual_kwh"]) < 1e-12


def test_grid_charging_rate_limit_and_target_cap():
    # uncapped trigger: one hour at 0.5 C DC = 5 kW DC -> 5/0.98 kW AC from the grid, 4.75 kWh stored
    r = one([0.0], [1], [0.0], 10.0, S.soc_trigger(1, 0.3), e0_frac=0.05)
    assert r["grid_to_battery_kwh"] == pytest.approx(5 / 0.98)
    assert r["series"]["e_kwh"][0] == pytest.approx(0.5 * (1 - SIG) + 4.75)
    # capped target 0.3: stops at E = 3.0 kWh
    r = one([0.0], [1], [0.0], 10.0, S.soc_target(1, 0.3), e0_frac=0.05)
    assert r["series"]["e_kwh"][0] == pytest.approx(3.0)
    assert r["grid_to_battery_kwh"] == pytest.approx((3.0 - 0.5 * (1 - SIG)) / KIN)
    # 0.25 C (thesis Mode 0 rate): 2.5 kW DC
    r = one([0.0], [1], [0.0], 10.0, S.soc_trigger(1, 0.9, rate_c=0.25), e0_frac=0.05)
    assert r["grid_to_battery_kwh"] == pytest.approx(2.5 / 0.98)


def test_no_grid_charging_during_outage_and_trigger_uses_start_soc():
    r = one([0.0], [0], [0.0], 10.0, S.soc_trigger(1, 1.0), e0_frac=0.05)
    assert r["grid_to_battery_kwh"] == 0
    r = one([0.0], [1], [0.0], 10.0, S.soc_trigger(1, 0.5), e0_frac=0.5)   # SOC 0.5 is not < 0.5
    assert r["grid_to_battery_kwh"] == 0


def test_clipping_separate_from_curtailment():
    r = one([0.0], [1], [12.0], 10.0, e0_frac=0.05)
    assert r["pv_clipped_kwh"] == pytest.approx(2.0)
    ch = 5 / 0.98                                     # PV surplus into battery limited by 0.5 C DC
    assert r["pv_curtailed_kwh"] == pytest.approx(9.8 - ch)
    assert abs(r["balance_residual_kwh"]) < 1e-12


def test_unserved_split_power_vs_energy():
    r = one([8.0], [0], [0.0], 10.0, e0_frac=0.98)       # 0.5 C -> 5 kW DC -> 4.9 kW AC
    assert r["unserved_kwh"] == pytest.approx(8 - 4.9)
    assert r["unserved_power_limited_kwh"] == pytest.approx(3.1) and r["unserved_energy_limited_kwh"] == 0
    r = one([1.0], [0], [0.0], 10.0, e0_frac=0.05)       # empty battery
    assert r["unserved_energy_limited_kwh"] == pytest.approx(1.0) and r["unserved_power_limited_kwh"] == 0
    # inverter shared with PV: PV 6 kW AC to load leaves 4 kW for the battery
    r = one([12.0], [0], [6 / 0.98], 20.0, e0_frac=0.98)
    assert r["unserved_kwh"] == pytest.approx(12 - 6 - 4)


def test_soc_definition_is_energy_over_nominal():
    r = one([0.0], [1], [0.0], 10.0, e0_frac=0.8)        # self-discharge pushes it just below 0.8 C
    assert r["hours_soc_ge_80pct"] == 0
    r = one([0.0], [1], [0.0], 10.0, e0_frac=0.81)
    assert r["hours_soc_ge_80pct"] == 1 and r["mean_soc_pct"] == pytest.approx(81 * (1 - SIG))
    # c_max = 0.98 C: a SOC target of 1.0 stops at 0.98
    r = one([0.0] * 3, [1] * 3, [0.0] * 3, 10.0, S.soc_target(3, 1.0), e0_frac=0.05)
    assert r["series"]["e_kwh"].max() == pytest.approx(9.8)


def _random_case(n=300, seed=0):
    rng = np.random.default_rng(seed)
    load = rng.uniform(0.2, 3.0, n)
    on = (rng.uniform(size=n) > 0.4).astype(int)
    hour = np.arange(n) % 24
    pv = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * rng.uniform(4, 13, n)
    return load, on, pv


def test_energy_balance_all_policies():
    load, on, pv = _random_case()
    n = len(load)
    risk = np.random.default_rng(1).uniform(size=n)
    pols = [S.pv_only(n), S.soc_trigger(n, 0.7), S.soc_target(n, 0.6), S.binary_topup(risk, 0.4),
            S.risk_target(risk, 0.3), S.mode0(np.r_[0.0, pv[:-1]], 0.25)]
    for pol in pols:
        for cap in (5.1, 10.2, 20.4):
            r = S.simulate(load, on, pv, cap, *pol)
            assert abs(r["balance_residual_kwh"]) < 1e-8
            assert r["unserved_energy_limited_kwh"] + r["unserved_power_limited_kwh"] == pytest.approx(r["unserved_kwh"])
    r = S.simulate(load, on, pv, 10.2, g_sched=np.full(n, 2.0), pvch_sched=np.full(n, 1.0))
    assert abs(r["balance_residual_kwh"]) < 1e-8


def test_mode0_night_uses_previous_hour_pv():
    pv_full = np.array([0.0, 5.0, 0.0, 0.0])
    mask = np.ones(4, bool)
    trig, _, _ = S.mode0(S.pv_ac_prev(pv_full, mask), 0.25, 0.8)
    assert list(trig) == [0.8, 0.8, 0.0, 0.8]     # hour 2 has PV 0 but hour 1 had 5 kW -> not "night"
    pv2 = pv_full.copy(); pv2[3] = 9.0              # changing PV of hour 3 cannot change the decision at hour 3
    assert S.mode0(S.pv_ac_prev(pv2, mask))[0][3] == trig[3]


def test_lp_oracle_resimulates_and_bounds_policies():
    load, on, pv = _random_case(240, 3)
    n = len(load)
    o = oracle_point(load, on, pv, 10.2, 1e-7)
    assert o["unserved_kwh"] == pytest.approx(o["lp_unserved_kwh"], abs=1e-4)
    assert abs(o["balance_residual_kwh"]) < 1e-8
    for pol in (S.pv_only(n), S.soc_trigger(n, 1.0), S.soc_target(n, 0.6)):
        assert o["lp_unserved_kwh"] <= S.simulate(load, on, pv, 10.2, *pol)["unserved_kwh"] + 1e-6
    dp = dp_point(load, on, pv, 10.2, 1e-6)
    assert dp["unserved_kwh"] >= o["lp_unserved_kwh"] - 1e-4        # DP has fewer options than the LP
    blanket = S.simulate(load, on, pv, 10.2, *S.soc_trigger(n, 1.0))["unserved_kwh"]
    assert dp["unserved_kwh"] <= blanket + 1e-6                       # ... but at least as many as Blanket
    hi = oracle_point(load, on, pv, 10.2, 50.0)                       # large ageing weight -> lower SOC
    assert hi["mean_soc_pct"] <= o["mean_soc_pct"] + 1e-9


def test_forecast_features_known_at_start_of_hour():
    from forecasts_v2 import features_start_of_hour
    idx = pd.date_range("2018-01-01", periods=400, freq="h")
    rng = np.random.default_rng(0)
    d = pd.DataFrame({"outage": (rng.uniform(size=400) > 0.6).astype(int), "load_kwh": rng.uniform(0, 3, 400)},
                     index=idx)
    f1 = features_start_of_hour(d)
    d2 = d.copy(); d2.iloc[300, d2.columns.get_loc("load_kwh")] += 100.0
    f2 = features_start_of_hour(d2)
    assert f1.iloc[:301].equals(f2.iloc[:301])      # load of hour 300 does not enter row 300


def test_perfect_binary_risk_looks_only_ahead():
    from forecasts_v2 import MODELS, dispatch_risk
    n = 30
    o = np.zeros(n, int); o[10] = 1
    fc = {m: pd.DataFrame(np.zeros((n, 6)), columns=range(1, 7)) for m in MODELS}
    r = dispatch_risk(fc, np.ones(n, bool), o)["PerfectBinary"]
    assert list(np.flatnonzero(r)) == [4, 5, 6, 7, 8, 9]
