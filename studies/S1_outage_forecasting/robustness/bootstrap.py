"""Task 3: week-block bootstrap of the dispatch result in the pareto setting (8 kWp, 10.2 kWh, H = 6 h).

Statistic: LPSP of a forecaster's theta-frontier at the number of hours with SOC >= 80 % that Mode 0 has
(linear interpolation along the frontier, theta = 0.05..0.95), and its difference learned - HourMarkov.

EXACT method (main result): Apr-Dec (6,600 h) is cut into 40 blocks of 168 h starting 1 Apr 00:00 (the last block
has 48 h). Each replicate draws 40 blocks with replacement, concatenates load, grid status, PV and the stored
out-of-sample forecast risk of those hours, and re-runs dispatch_value.simulate for Mode 0 and for every
(forecaster, theta) - i.e. the whole frontier is re-simulated per replicate. Limitations: battery state carries
across block joins (artificial jumps in weather/outage history at joins); forecasts are not re-trained, so the CI
is conditional on the fitted models (seed variation of RF is examined separately in sensitivity.py).

APPROXIMATE method (used for the sensitivity grid, validated here): one simulation of the true series, split into
per-block contributions (unserved kWh, load kWh, high-SOC hours) via prefix runs of simulate; replicates sum the
contributions of the drawn blocks. It ignores how the battery state at block starts would change after
resampling.
"""
from __future__ import annotations

import time
from multiprocessing import Pool

import matplotlib
import numpy as np
import pandas as pd

from common import (CACHE, HERE, PARETO_CAP_KWH, PARETO_PV_KWP, PARETO_THETAS, PILOT, SITES,
                    frontier_lpsp_at)
from dispatch_value import simulate
from pilot_s1 import load_sites
from src.pv.model import PVConfig, estimate_timestamp_offset, load_weather_2018, pv_power_per_kwp

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

N_BOOT = 1000
BLOCK_H = 168
BOOT_SEED = 20261022
LEARNED = ["RandomForest", "Logistic"]
REF = "HourMarkov"


def pv_unit() -> np.ndarray:
    w = load_weather_2018()
    return pv_power_per_kwp(w, PVConfig(timestamp_offset_min=estimate_timestamp_offset(w))).values


def site_inputs(site: str, H: int, fc: dict[str, pd.DataFrame], pv_kwp: float = PARETO_PV_KWP,
                pvu: np.ndarray | None = None) -> dict:
    d = load_sites()[site]
    m = d.index.month >= 4
    pvu = pv_unit() if pvu is None else pvu
    return {"load": d["load_kwh"].values[m], "grid_on": (1 - d["outage"].values)[m], "pv": pvu[m] * pv_kwp,
            "risks": {k: v.loc[m, list(range(1, H + 1))].max(axis=1).values for k, v in fc.items()}}


def blocks(n: int) -> list[np.ndarray]:
    return [np.arange(s, min(s + BLOCK_H, n)) for s in range(0, n, BLOCK_H)]


def frontier_stat(load, grid_on, pv, risks: dict, cap: float, forecasters, thetas=PARETO_THETAS) -> dict:
    m0 = simulate(load, grid_on, pv, None, cap, "Mode0")
    out = {"Mode0_LPSP": m0["LPSP_pct"], "Mode0_high_soc_h": m0["hours_soc_ge_80pct"]}
    for f in forecasters:
        sims = [simulate(load, grid_on, pv, risks[f], cap, "FC", th) for th in thetas]
        out[f] = frontier_lpsp_at(np.array([s["hours_soc_ge_80pct"] for s in sims]),
                                  np.array([s["LPSP_pct"] for s in sims]), m0["hours_soc_ge_80pct"])
    return out


# ------------------------------------------------------------------ exact bootstrap (worker globals via fork)
_G: dict = {}


def _rep(idx_blocks: np.ndarray) -> dict:
    ix = np.concatenate([_G["blocks"][b] for b in idx_blocks])
    r = {k: v[ix] for k, v in _G["risks"].items()}
    return frontier_stat(_G["load"][ix], _G["grid_on"][ix], _G["pv"][ix], r, _G["cap"], _G["forecasters"])


def exact_bootstrap(inp: dict, cap: float, forecasters, n_boot: int, seed: int) -> pd.DataFrame:
    bl = blocks(len(inp["load"]))
    rng = np.random.default_rng(seed)
    draws = [rng.integers(0, len(bl), len(bl)) for _ in range(n_boot)]
    _G.update(inp, blocks=bl, cap=cap, forecasters=forecasters)
    with Pool(2) as pool:
        res = pool.map(_rep, draws, chunksize=10)
    return pd.DataFrame(res)


# ------------------------------------------------------------------ approximate (per-block contributions)
def block_contrib(load, grid_on, pv, risk, cap, strategy, theta) -> tuple[np.ndarray, np.ndarray]:
    """Per-block unserved kWh and high-SOC hours of ONE simulation of the true series (prefix differences)."""
    ends = [b[-1] + 1 for b in blocks(len(load))]
    cu, ch = [0.0], [0.0]
    for e in ends:
        s = simulate(load[:e], grid_on[:e], pv[:e], None if risk is None else risk[:e], cap, strategy, theta)
        cu.append(s["unserved_kwh"]); ch.append(s["hours_soc_ge_80pct"])
    return np.diff(cu), np.diff(ch)


def _contrib_job(args):
    key, strategy, theta = args
    return key, theta, block_contrib(_G["load"], _G["grid_on"], _G["pv"],
                                     None if key == "Mode0" else _G["risks"][key], _G["cap"], strategy, theta)


def contributions(inp: dict, cap: float, forecasters, thetas=PARETO_THETAS) -> dict:
    _G.update(inp, cap=cap)
    jobs = [("Mode0", "Mode0", 0.5)] + [(f, "FC", th) for f in forecasters for th in thetas]
    with Pool(2) as pool:
        res = pool.map(_contrib_job, jobs, chunksize=4)
    out = {"load": np.array([inp["load"][b].sum() for b in blocks(len(inp["load"]))])}
    for key, th, (u, h) in res:
        out[(key, th)] = (u, h)
    return out


def approx_bootstrap(con: dict, forecasters, n_boot: int, seed: int, thetas=PARETO_THETAS) -> pd.DataFrame:
    nb = len(con["load"])
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_boot):
        ix = rng.integers(0, nb, nb)
        tot = con["load"][ix].sum()
        u0, h0 = con[("Mode0", 0.5)]
        r = {"Mode0_LPSP": 100 * u0[ix].sum() / tot, "Mode0_high_soc_h": h0[ix].sum()}
        for f in forecasters:
            hrs = np.array([con[(f, th)][1][ix].sum() for th in thetas])
            lp = np.array([100 * con[(f, th)][0][ix].sum() / tot for th in thetas])
            r[f] = frontier_lpsp_at(hrs, lp, r["Mode0_high_soc_h"])
        rows.append(r)
    return pd.DataFrame(rows)


def summarise(point: dict, reps: pd.DataFrame, site: str, method: str, **extra) -> list[dict]:
    rows = []
    for f in LEARNED + ["Mode0"]:
        a = reps[f] if f != "Mode0" else reps["Mode0_LPSP"]
        diff = a - reps[REF]
        pt = (point[f] if f != "Mode0" else point["Mode0_LPSP"]) - point[REF]
        ok = diff.dropna()
        rows.append({"site": site, "method": method, **extra, "comparison": f"{f} - {REF}",
                     "point_diff_pp": pt, "boot_mean_pp": ok.mean(), "boot_sd_pp": ok.std(),
                     "ci95_lo_pp": ok.quantile(0.025), "ci95_hi_pp": ok.quantile(0.975),
                     "share_diff_lt_0": (ok < 0).mean(), "n_valid": len(ok), "n_nan": int(diff.isna().sum())})
    # RF - Logistic (ordering of the learned models) and learned - Mode 0 (does the trigger beat the thesis rule?)
    for a, b in [("RandomForest", "Logistic"), ("RandomForest", "Mode0_LPSP"), ("Logistic", "Mode0_LPSP")]:
        diff = reps[a] - reps[b]
        ok = diff.dropna()
        rows.append({"site": site, "method": method, **extra, "comparison": f"{a} - {b.replace('_LPSP', '')}",
                     "point_diff_pp": point[a] - point[b], "boot_mean_pp": ok.mean(), "boot_sd_pp": ok.std(),
                     "ci95_lo_pp": ok.quantile(0.025), "ci95_hi_pp": ok.quantile(0.975),
                     "share_diff_lt_0": (ok < 0).mean(), "n_valid": len(ok), "n_nan": int(diff.isna().sum())})
    return rows


def main() -> None:
    pvu = pv_unit()
    fcs = LEARNED + [REF]
    summ, fig_data = [], {}
    for k, site in enumerate(SITES):
        fc = pd.read_pickle(PILOT / "results" / f"forecasts_{site.lower()}_h6.pkl")
        inp = site_inputs(site, 6, {f: fc[f] for f in fcs}, pvu=pvu)
        point = frontier_stat(inp["load"], inp["grid_on"], inp["pv"], inp["risks"], PARETO_CAP_KWH, fcs)
        print(site, "point:", {a: round(b, 3) for a, b in point.items()}, flush=True)
        t0 = time.time()
        f_ex = CACHE / f"boot_exact_{site}.pkl"
        if f_ex.exists():
            ex = pd.read_pickle(f_ex)
        else:
            ex = exact_bootstrap(inp, PARETO_CAP_KWH, fcs, N_BOOT, BOOT_SEED + k)
            ex.to_pickle(f_ex)
        print(f"{site} exact bootstrap {time.time() - t0:.0f} s", flush=True)
        ex.assign(site=site).to_csv(HERE / f"bootstrap_replicates_{site}.csv", index=False)
        con = contributions(inp, PARETO_CAP_KWH, fcs)
        ap = approx_bootstrap(con, fcs, N_BOOT, BOOT_SEED + k)
        summ += summarise(point, ex, site, "exact_resimulation")
        summ += summarise(point, ap, site, "approx_block_contributions")
        fig_data[site] = (point, ex)
    s = pd.DataFrame(summ)
    s.to_csv(HERE / "bootstrap_dispatch_ci.csv", index=False)
    print(s.round(3).to_string(index=False))
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
    for ax, site in zip(axes, SITES):
        point, ex = fig_data[site]
        for f, c in [("RandomForest", "#1b7837"), ("Logistic", "#762a83")]:
            ax.hist((ex[f] - ex[REF]).dropna(), bins=40, alpha=0.55, color=c, label=f"{f} - {REF}")
            ax.axvline(point[f] - point[REF], color=c, lw=1.5)
        ax.axvline(0, color="k", lw=0.8, ls="--")
        ax.set_xlabel("LPSP difference at Mode 0's high-SOC hours (pp)")
        ax.set_title(f"{site}: week-block bootstrap, {N_BOOT} replicates (8 kWp, 10.2 kWh, H=6)")
        ax.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(HERE / "bootstrap_dispatch.png", dpi=150); plt.close()


if __name__ == "__main__":
    main()
