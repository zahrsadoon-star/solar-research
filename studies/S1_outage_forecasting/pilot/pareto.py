"""Pareto view for RQ3: reliability vs. time spent at high state of charge (a battery-ageing proxy) for each
forecaster as the trigger threshold theta varies. Uses cached out-of-sample forecasts from dispatch_value.py.
Run: python pareto.py   ->  results/pareto_<site>.csv, results/pareto.png"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[2]))
from dispatch_value import H, PV_KWP, simulate  # noqa: E402
from pilot_s1 import load_sites  # noqa: E402
from src.pv.model import PVConfig, estimate_timestamp_offset, load_weather_2018, pv_power_per_kwp  # noqa: E402

OUT = HERE / "results"
PV, CAP = 8.0, 10.2
THETAS = np.round(np.arange(0.05, 0.96, 0.05), 2)
w = load_weather_2018()
pv_unit = pv_power_per_kwp(w, PVConfig(timestamp_offset_min=estimate_timestamp_offset(w))).values
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, site in zip(axes, ["BG", "KR"]):
    d = load_sites()[site]
    fc = pd.read_pickle(OUT / f"forecasts_{site.lower()}_h6.pkl")
    m = d.index.month >= 4
    load, grid_on, pv = d["load_kwh"].values[m], (1 - d["outage"].values)[m], pv_unit[m] * PV
    o = d["outage"].values
    perfect = np.array([o[t + 1:t + 1 + H].max() if t + 1 < len(o) else 0 for t in range(len(o))])[m]
    rows = []
    for s in ["PV-only", "Mode0", "Blanket"]:
        rows.append({"forecast": s, "theta": np.nan, **simulate(load, grid_on, pv, None, CAP, s)})
    risks = {k: v.loc[m].max(axis=1).values for k, v in fc.items()} | {"Perfect": perfect}
    for name, r in risks.items():
        for th in THETAS:
            rows.append({"forecast": name, "theta": th, **simulate(load, grid_on, pv, r, CAP, "FC", th)})
    res = pd.DataFrame(rows); res.insert(0, "site", site)
    res.round(3).to_csv(OUT / f"pareto_{site}.csv", index=False)
    style = {"RandomForest": "#1b7837", "Logistic": "#762a83", "HourMarkov": "#d6604d",
             "Climatology": "#999999", "Perfect": "k"}
    for name, c in style.items():
        x = res[res.forecast == name].sort_values("hours_soc_ge_80pct")
        ax.plot(x.hours_soc_ge_80pct, x.LPSP_pct, "o-" if name != "Perfect" else "--", ms=3, color=c, label=name)
    for s, mk in [("PV-only", "v"), ("Mode0", "s"), ("Blanket", "^")]:
        x = res[res.forecast == s]
        ax.plot(x.hours_soc_ge_80pct, x.LPSP_pct, mk, ms=9, color="#2166ac", label=s)
    ax.set_xlabel("hours with SOC ≥ 80 % (Apr–Dec)"); ax.set_ylabel("LPSP (%)")
    ax.set_title(f"{ {'BG': 'Baghdad', 'KR': 'Karbala'}[site]}: {PV:g} kWp, {CAP} kWh")
    # numbers for the report: at Blanket's LPSP + 0.5 pp, fewest high-SOC hours per forecaster
    bl = res[res.forecast == "Blanket"].iloc[0]
    print(f"\n{site}: Blanket LPSP {bl.LPSP_pct:.2f} %, high-SOC h {bl.hours_soc_ge_80pct}; Mode0 LPSP "
          f"{res[res.forecast=='Mode0'].LPSP_pct.item():.2f} %, high-SOC h {res[res.forecast=='Mode0'].hours_soc_ge_80pct.item()}")
    for name in style:
        x = res[(res.forecast == name) & (res.LPSP_pct <= bl.LPSP_pct + 0.5)]
        if len(x):
            b = x.sort_values("hours_soc_ge_80pct").iloc[0]
            print(f"  {name:12s} theta {b.theta:.2f}: LPSP {b.LPSP_pct:.2f} %, high-SOC h {b.hours_soc_ge_80pct}, "
                  f"({100*(1-b.hours_soc_ge_80pct/bl.hours_soc_ge_80pct):.0f} % fewer than Blanket)")
        else:
            print(f"  {name:12s} never within 0.5 pp of Blanket")
axes[0].legend(fontsize=7)
plt.tight_layout(); plt.savefig(OUT / "pareto.png", dpi=200)
