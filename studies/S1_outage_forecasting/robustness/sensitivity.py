"""Task 4: sensitivity of the frontier comparison to look-ahead H (3, 6, 12 h) and battery size (5.1, 10.2,
20.4 kWh) at 8 kWp; plus the seed sensitivity of the RandomForest forecasts for the base case.

Forecasts: H = 3 and 6 use the pilot cache (pilot/results/forecasts_*_h6.pkl, columns k = 1..H). H = 12 needs
k = 7..12, so dispatch_value.rolling_forecasts is re-run with dispatch_value.H = 12 (same seed 42, same protocol);
its k = 1..6 columns are compared with the pilot cache as a reproducibility check.
CIs: approximate week-block bootstrap (per-block contributions, see bootstrap.py; validated against the exact
re-simulation at the base case in bootstrap_dispatch_ci.csv), 1,000 replicates.
"""
from __future__ import annotations

import time

import matplotlib
import numpy as np
import pandas as pd

import dispatch_value as DV
from bootstrap import (BOOT_SEED, LEARNED, N_BOOT, REF, approx_bootstrap, contributions, frontier_stat,
                       pv_unit, site_inputs, summarise)
from common import CACHE, HERE, PARETO_CAP_KWH, PARETO_THETAS, PILOT, SITES, frontier_lpsp_at
from pilot_s1 import load_sites

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HS = [3, 6, 12]
CAPS = [5.1, 10.2, 20.4]
FCS = ["RandomForest", "Logistic", "HourMarkov", "Climatology"]
RF_SEEDS = [0, 1, 2]


def forecasts(site: str, H: int, seed: int = 42) -> dict[str, pd.DataFrame]:
    if H <= 6 and seed == 42:
        return pd.read_pickle(PILOT / "results" / f"forecasts_{site.lower()}_h6.pkl")
    f = CACHE / f"forecasts_{site.lower()}_h{H}_seed{seed}.pkl"
    if not f.exists():
        DV.H, DV.SEED = H, seed
        t0 = time.time()
        fc = DV.rolling_forecasts(load_sites()[site])
        DV.H, DV.SEED = 6, 42
        pd.to_pickle(fc, f)
        print(f"forecasts {site} H={H} seed={seed}: {time.time() - t0:.0f} s", flush=True)
    return pd.read_pickle(f)


def main() -> None:
    pvu = pv_unit()
    # reproducibility of the H=12 run on k = 1..6
    chk = []
    for site in SITES:
        a, b = forecasts(site, 12), forecasts(site, 6)
        for m in FCS:
            dd = (a[m][list(range(1, 7))] - b[m]).abs().max().max()
            chk.append({"site": site, "model": m, "max_abs_diff_k1to6_vs_pilot_cache": dd})
    pd.DataFrame(chk).to_csv(HERE / "h12_forecast_reproduction_check.csv", index=False)
    print(pd.DataFrame(chk))

    point_rows, ci_rows, front_rows = [], [], []
    for k, site in enumerate(SITES):
        for H in HS:
            fc = forecasts(site, 12 if H == 12 else 6)
            inp = site_inputs(site, H, {f: fc[f] for f in FCS}, pvu=pvu)
            for cap in CAPS:
                t0 = time.time()
                pt = frontier_stat(inp["load"], inp["grid_on"], inp["pv"], inp["risks"], cap, FCS)
                for s_ in ["PV-only", "Blanket"]:
                    r = DV.simulate(inp["load"], inp["grid_on"], inp["pv"], None, cap, s_)
                    pt[f"{s_}_LPSP"], pt[f"{s_}_high_soc_h"] = r["LPSP_pct"], r["hours_soc_ge_80pct"]
                for f in FCS:
                    for th in PARETO_THETAS:
                        r = DV.simulate(inp["load"], inp["grid_on"], inp["pv"], inp["risks"][f], cap, "FC", th)
                        front_rows.append({"site": site, "H": H, "battery_kwh": cap, "forecast": f, "theta": th,
                                           "LPSP_pct": r["LPSP_pct"], "hours_soc_ge_80pct": r["hours_soc_ge_80pct"]})
                point_rows.append({"site": site, "H": H, "battery_kwh": cap, **pt})
                con = contributions(inp, cap, LEARNED + [REF])
                ap = approx_bootstrap(con, LEARNED + [REF], N_BOOT, BOOT_SEED + k)
                ci_rows += summarise(pt, ap, site, "approx_block_contributions", H=H, battery_kwh=cap)
                print(f"{site} H={H} cap={cap}: {time.time() - t0:.0f} s", flush=True)
    pts = pd.DataFrame(point_rows)
    pts.to_csv(HERE / "sensitivity_points.csv", index=False)
    pd.DataFrame(front_rows).to_csv(HERE / "sensitivity_frontiers.csv", index=False)
    ci = pd.DataFrame(ci_rows)
    ci.to_csv(HERE / "sensitivity_ci.csv", index=False)
    print(pts.round(3).to_string(index=False))
    print(ci[ci.comparison.str.endswith(REF)].round(3).to_string(index=False))

    # RF seed sensitivity of the base-case dispatch statistic
    rows = []
    for site in SITES:
        for seed in [42, *RF_SEEDS]:
            fc = forecasts(site, 6, seed)
            inp = site_inputs(site, 6, {f: fc[f] for f in ["RandomForest"]}, pvu=pvu)
            pt = frontier_stat(inp["load"], inp["grid_on"], inp["pv"], inp["risks"], PARETO_CAP_KWH, ["RandomForest"])
            rows.append({"site": site, "rf_seed": seed, "RF_LPSP_at_Mode0_high_soc": pt["RandomForest"],
                         "Mode0_LPSP": pt["Mode0_LPSP"]})
    pd.DataFrame(rows).to_csv(HERE / "dispatch_rf_seed_sensitivity.csv", index=False)
    print(pd.DataFrame(rows).round(3))

    fr = pd.DataFrame(front_rows)
    style = {"RandomForest": "#1b7837", "Logistic": "#762a83", "HourMarkov": "#d6604d", "Climatology": "#999999"}
    for site in SITES:
        fig, axes = plt.subplots(3, 3, figsize=(12, 10))
        for i, H in enumerate(HS):
            for j, cap in enumerate(CAPS):
                ax = axes[i, j]
                for f, c in style.items():
                    x = fr[(fr.site == site) & (fr.H == H) & (fr.battery_kwh == cap) & (fr.forecast == f)]
                    x = x.sort_values("hours_soc_ge_80pct")
                    ax.plot(x.hours_soc_ge_80pct, x.LPSP_pct, "o-", ms=2.5, color=c, label=f)
                p = pts[(pts.site == site) & (pts.H == H) & (pts.battery_kwh == cap)].iloc[0]
                ax.plot(p.Mode0_high_soc_h, p.Mode0_LPSP, "s", ms=8, color="#2166ac", label="Mode0")
                ax.axvline(p.Mode0_high_soc_h, color="#2166ac", lw=0.6, ls=":")
                ax.set_title(f"H={H} h, {cap} kWh", fontsize=9)
                ax.set_xlabel("hours SOC >= 80 %", fontsize=8); ax.set_ylabel("LPSP (%)", fontsize=8)
        axes[0, 0].legend(fontsize=7)
        fig.suptitle(f"{site}: LPSP vs high-SOC hours frontiers, 8 kWp (Apr-Dec)")
        plt.tight_layout(); plt.savefig(HERE / f"sensitivity_frontiers_{site}.png", dpi=130); plt.close()


if __name__ == "__main__":
    main()
