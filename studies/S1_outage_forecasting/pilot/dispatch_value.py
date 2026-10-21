"""S1 pilot, criterion 2: is an outage forecast worth anything for home-battery dispatch?

Same PV/battery for every strategy (thesis design: 15 kWp, 30.6 kWh, 10 kW inverter) with the corrected 2018 PV
model (south-facing, Baghdad local time, src/pv/model.py). Load and outages: house BG (Baghdad) or KR (Karbala), 2018. KR uses Baghdad 2018 weather as a proxy
(Karbala is ~80 km away; flagged as a limitation).
Forecasts are out-of-sample (rolling-origin by month, as in pilot_s1.py), so evaluation covers April-December.

Strategies (grid ON hours; during outages every strategy does the same: PV -> load, then battery, rest unserved):
  PV-only       battery charged by PV surplus only
  Mode0         thesis rule: PV surplus + grid charging at night (PV < 0.1 kW) when SOC < 80 %, at 0.25 C
  Blanket       grid tops the battery up whenever SOC < 100 %, at 0.5 C
  FC-<model>    PV surplus; grid tops up at 0.5 C only when risk_t = max_k P(outage at t+k), k=1..H, exceeds theta
  Mode0+FC      Mode0 plus the forecast-triggered top-up
  Perfect       FC rule with risk = 1 if an outage really occurs within H hours (upper bound)
Battery/inverter equations follow the thesis simulate_ems (legacy/thesis_model.py cells 52-55).
Run:  python dispatch_value.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
from pilot_s1 import Climatology, HourMarkov, features, load_sites  # noqa: E402
from src.pv.model import PVConfig, estimate_timestamp_offset, load_weather_2018, pv_power_per_kwp  # noqa: E402

OUT = HERE / "results"
H = 6                                   # look-ahead window [h]
THETAS = [0.3, 0.5, 0.7]
PV_KWP = 23 * 0.650                     # thesis: 23 x 650 W
INV_KW = 10.0
ETA_INV = 0.98
SEED = 42


# ----------------------------------------------------------------------------- forecasts
def rolling_forecasts(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Out-of-sample P(outage at t+k), k = 1..H, for April-December. Returns {model: DataFrame[t, k]}."""
    X_all = features(d, with_temp=False)
    out = {m: pd.DataFrame(index=d.index, columns=range(1, H + 1), dtype=float)
           for m in ["RandomForest", "Logistic", "HourMarkov", "Climatology"]}
    for k in range(1, H + 1):
        y_all = d["outage"].shift(-k)
        ok = X_all.notna().all(axis=1) & y_all.notna()
        X, y = X_all[ok], y_all[ok].astype(int)
        t_target = X.index + pd.Timedelta(hours=k)
        for m in range(4, 13):
            start = pd.Timestamp(f"2018-{m:02d}-01")
            tr = (X.index < start) & (t_target < start)
            te = X.index.month == m
            rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED)
            lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5))
            out["RandomForest"].loc[X.index[te], k] = rf.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
            out["Logistic"].loc[X.index[te], k] = lr.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
            mk = HourMarkov().fit(d["outage"][d.index < start])
            out["HourMarkov"].loc[X.index[te], k] = mk.predict_proba(X.loc[te, "state"].values, X.index[te], k)
            cl = Climatology().fit(X[tr], y[tr], t_target[tr])
            out["Climatology"].loc[X.index[te], k] = cl.predict_proba(X[te], t_target[te])
    return out


# ----------------------------------------------------------------------------- simulator
def simulate(load: np.ndarray, grid_on: np.ndarray, pv_kw: np.ndarray, risk: np.ndarray | None,
             cap_kwh: float, strategy: str, theta: float = 0.5) -> dict:
    c_max, c_min = 0.98 * cap_kwh, 0.05 * cap_kwh
    eta_c = eta_d = 0.95
    sigma = 2e-5
    p_max = 0.5 * cap_kwh                      # 0.5 C
    e = (c_max + c_min) / 2
    n = len(load)
    unserved = grid_buy = grid_to_bat = curtailed = discharged = 0.0
    soc_sum = high_soc_h = 0.0
    for t in range(n):
        e *= (1 - sigma)
        pv = min(pv_kw[t], INV_KW) * ETA_INV
        pv_load = min(pv, load[t])
        surplus, rest = pv - pv_load, load[t] - pv_load
        ch = max(0.0, min(surplus, (c_max - e) / eta_c, p_max))
        e += ch * eta_c
        curtailed += surplus - ch
        if grid_on[t]:
            grid_buy += rest
            soc = e / c_max
            want = 0.0
            if strategy in ("Mode0", "Mode0+FC") and pv < 0.1 and soc < 0.80:
                want = 0.5 * p_max
            if strategy == "Blanket":
                want = p_max
            if strategy in ("FC", "Mode0+FC", "Perfect") and risk[t] > theta:
                want = p_max
            g = max(0.0, min(want, (c_max - e) / eta_c, p_max - ch))
            e += g * eta_c
            grid_buy += g
            grid_to_bat += g
        else:
            dis = max(0.0, min(rest, (e - c_min) * eta_d, p_max, INV_KW - pv_load))
            e -= dis / eta_d
            discharged += dis
            unserved += rest - dis
        soc_sum += e / cap_kwh
        high_soc_h += e / cap_kwh >= 0.8
    total = load.sum()
    return {"LPSP_pct": 100 * unserved / total, "unserved_kwh": unserved, "grid_import_kwh": grid_buy,
            "grid_to_battery_kwh": grid_to_bat, "pv_curtailed_kwh": curtailed,
            "battery_EFC": discharged / cap_kwh, "mean_soc_pct": 100 * soc_sum / n,
            "hours_soc_ge_80pct": int(high_soc_h)}


def main(site: str = "BG") -> None:
    d = load_sites()[site]
    w = load_weather_2018()
    pv = pv_power_per_kwp(w, PVConfig(timestamp_offset_min=estimate_timestamp_offset(w))).values * PV_KWP
    cache = OUT / f"forecasts_{site.lower()}_h6.pkl"
    if cache.exists():
        fc = pd.read_pickle(cache)
    else:
        fc = rolling_forecasts(d)
        pd.to_pickle(fc, cache)
    eval_mask = d.index.month >= 4
    load, grid_on, pv_e = d["load_kwh"].values[eval_mask], (1 - d["outage"].values)[eval_mask], pv[eval_mask]
    o = d["outage"].values
    perfect = np.array([o[t + 1:t + 1 + H].max() if t + 1 < len(o) else 0 for t in range(len(o))])[eval_mask]
    risks = {m: f.loc[eval_mask].max(axis=1).values for m, f in fc.items()}

    rows = []
    pv_unit = pv_e / PV_KWP                       # kW per kWp
    for pv_kwp in [5.0, 8.0, PV_KWP]:
        pv_k = pv_unit * pv_kwp
        for cap in [5.1, 10.2, 20.4, 30.6]:
            def add(strategy, forecast, theta, risk):
                rows.append({"pv_kwp": round(pv_kwp, 2), "battery_kwh": cap, "strategy": strategy,
                             "forecast": forecast, "theta": theta,
                             **simulate(load, grid_on, pv_k, risk, cap, strategy, theta)})
            for s_ in ["PV-only", "Mode0", "Blanket"]:
                add(s_, "-", np.nan, None)
            for th in THETAS:
                add("Perfect", "perfect", th, perfect)
                for m, r in risks.items():
                    add("FC", m, th, r)
                    add("Mode0+FC", m, th, r)
    res = pd.DataFrame(rows)
    key = ["pv_kwp", "battery_kwh"]
    ref = res[res.strategy.isin(["PV-only", "Blanket", "Mode0"])].pivot_table(
        index=key, columns="strategy", values=["unserved_kwh", "grid_to_battery_kwh"])
    ref.columns = [f"{a}__{b}" for a, b in ref.columns]
    res = res.join(ref, on=key)
    pv_u, bl_u = res["unserved_kwh__PV-only"], res["unserved_kwh__Blanket"]
    # share of the reliability gain of always-charging (Blanket) that a strategy achieves, and the grid
    # charging it needs relative to Blanket
    res["gain_captured_pct"] = 100 * (pv_u - res.unserved_kwh) / (pv_u - bl_u).replace(0, np.nan)
    res["grid_charging_vs_blanket_pct"] = 100 * res.grid_to_battery_kwh / res["grid_to_battery_kwh__Blanket"]
    res["unserved_vs_Mode0_pct"] = 100 * (res.unserved_kwh / res["unserved_kwh__Mode0"] - 1)
    res = res.drop(columns=[c for c in res.columns if "__" in c])
    res.insert(0, "site", site)
    res.round(3).to_csv(OUT / f"dispatch_value_{site}.csv", index=False)
    pd.set_option("display.width", 230)
    show = res[(res.theta.isna()) | ((res.theta == 0.5) & res.forecast.isin(["perfect", "RandomForest", "HourMarkov", "Climatology"]))]
    cols = key + ["strategy", "forecast", "LPSP_pct", "unserved_kwh", "grid_to_battery_kwh",
                  "gain_captured_pct", "grid_charging_vs_blanket_pct", "unserved_vs_Mode0_pct"]
    print(show[cols].round(1).to_string(index=False))
    print(f"\nApr-Dec: thesis PV {pv_e.sum():.0f} kWh; load {load.sum():.0f} kWh; outage share {1 - grid_on.mean():.3f}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "BG")
