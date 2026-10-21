"""Compares the corrected 2018 PV model with the thesis-style defects and transposition choices.
Writes results/pv/pv_2018_comparison.csv, results/pv/pv_2018_hourly.csv and results/pv/diurnal_profile.png.
Run from the repo root:  python scripts/pv_2018_compare.py
"""
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.pv.model import (PVConfig, estimate_timestamp_offset, legacy_style_poa, load_weather_2018,  # noqa: E402
                          plane_of_array, pv_power_per_kwp)

OUT = REPO / "results" / "pv"
OUT.mkdir(parents=True, exist_ok=True)
w = load_weather_2018()
off = estimate_timestamp_offset(w)
rows = []
base = PVConfig(timestamp_offset_min=off)
for model in ["isotropic", "reindl", "haydavies", "perez"]:
    cfg = PVConfig(transposition=model, timestamp_offset_min=off)
    poa = plane_of_array(w, cfg)["poa_global"]
    p = pv_power_per_kwp(w, cfg)
    rows.append({"case": f"corrected, {model}", "annual_poa_kwh_m2": poa.sum() / 1000,
                 "yield_kwh_per_kwp": p.sum(), "poa_peak_hour_local": int(poa.groupby(poa.index.hour).mean().idxmax())})
legacy = legacy_style_poa(w, base)
rows.append({"case": "thesis defects (north + 3 h shift), reindl", "annual_poa_kwh_m2": legacy.sum() / 1000,
             "yield_kwh_per_kwp": float("nan"),
             "poa_peak_hour_local": int(legacy.groupby(legacy.index.hour).mean().idxmax())})
tab = pd.DataFrame(rows).round(1)
ref = tab.loc[tab.case == "corrected, reindl", "annual_poa_kwh_m2"].item()
tab["poa_vs_corrected_reindl_pct"] = (100 * (tab.annual_poa_kwh_m2 / ref - 1)).round(1)
tab.to_csv(OUT / "pv_2018_comparison.csv", index=False)
print(f"timestamp offset estimated from clear days: {off:+.0f} min")
print(tab.to_string(index=False))

good = plane_of_array(w, base)["poa_global"]
pd.DataFrame({"poa_global_wm2": good.values, "pv_kw_per_kwp": pv_power_per_kwp(w, base).values},
             index=w.index.tz_localize(None)).to_csv(OUT / "pv_2018_hourly.csv", index_label="time_local_baghdad")
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.plot(good.groupby(good.index.hour).mean(), "o-", label="corrected (south, local time)")
ax.plot(legacy.groupby(legacy.index.hour).mean(), "s--", label="thesis defects (north, 3 h early)")
ax.set_xlabel("hour of day (Baghdad local)"); ax.set_ylabel("mean POA irradiance (W/m²)")
ax.set_xticks(range(0, 24, 3)); ax.legend(fontsize=8); ax.set_title("Baghdad 2018 (NASA POWER), tilt 31.3°")
plt.tight_layout(); plt.savefig(OUT / "diurnal_profile.png", dpi=200)
