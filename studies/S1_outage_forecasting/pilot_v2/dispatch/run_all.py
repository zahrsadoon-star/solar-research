"""S1 dispatch experiment v2 - regenerates every CSV and figure in results/.

Run:  /home/claude/venv/bin/python run_all.py [--refit]      (--refit regenerates the cached forecasts)
Steps: (1) out-of-sample forecasts per site and label (forecasts_v2); (2) for every site x label x size: all policy
families, the LP oracle and the DP oracle (parallel, 2 processes); (3) Pareto fronts, regret and oracle gaps
(frontier.py); (4) M3 unserved-energy split and longest outages; (5) figures (PNG, 200 dpi).
"""
from __future__ import annotations

import argparse
import json
import time
from multiprocessing import Pool

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import simulator_v2 as S  # noqa: E402
from common import (H, LABELS, OUT, PILOT, PRIMARY_LABEL, SITES, SIZES, YEAR_INDEX, eval_mask, load_site,  # noqa: E402
                    outage_events, pv_unit)
from forecasts_v2 import MODELS, dispatch_risk, get_forecasts  # noqa: E402
from frontier import interp_value, oracle_gap, pareto_front, regret_table  # noqa: E402
from oracle_dp import dp_point  # noqa: E402
from oracle_lp import oracle_point  # noqa: E402

GRID_S = np.round(np.arange(0.30, 1.0001, 0.05), 2)          # as specified
GRID_S_EXT = np.round(np.arange(0.10, 0.2501, 0.05), 2)     # extension (see README): closes the gap to PV-only
GRID_S_FINE = np.array([0.76, 0.77, 0.78, 0.79, 0.795])     # extension (see README): resolves the 80 % step cost
GRID_MODE0_THR = np.round(np.arange(0.30, 0.9501, 0.05), 2)
GRID_THETA = np.round(np.arange(0.0, 0.99001, 0.01), 2)
GRID_SLOW = np.round(np.arange(0.20, 0.8001, 0.05), 2)
S_HIGHS = (1.0, 0.9, 0.8)
W_LP_MEAN = np.r_[1e-7, np.logspace(-1, 1.2, 22)]
W_LP_HINGE = np.logspace(-2, 1.5, 12)
W_DP_MEAN = np.r_[1e-6, np.logspace(-1, 1.2, 13)]
W_DP_STEP = np.r_[1e-6, np.logspace(-2, 1.5, 13)]
FC_MODELS = MODELS + ["PerfectBinary"]
THESIS_SIZE = (23 * 0.650, 30.6)
PLANES = {"meansoc": "mean_soc_pct", "hours80": "hours_soc_ge_80pct"}
SITE_NAME = {"BG": "Baghdad (BG)", "KR": "Karbala (KR)"}
# categorical palette (dataviz reference palette, fixed order)
COLORS = {"RandomForest": "#2a78d6", "Logistic": "#eb6834", "HourMarkov": "#1baf7a", "Climatology": "#eda100",
          "PerfectBinary": "#6250d6"}


def window(site: str, label: str, kwp: float):
    d = load_site(site)
    m = eval_mask()
    outage = d[f"outage_{label}"].to_numpy(int)
    pv_full = pv_unit() * kwp
    return d, m, outage, d["load_kwh"].to_numpy(float)[m], 1 - outage[m], pv_full, pv_full[m]


def run_config(cfg: tuple[str, str, float, float]) -> pd.DataFrame:
    site, label, kwp, cap = cfg
    d, m, outage, load, on, pv_full, pv = window(site, label, kwp)
    n = len(load)
    risks = dispatch_risk(get_forecasts(site, label), m, outage)
    prev = S.pv_ac_prev(pv_full, m)
    rows = []

    def add(cls, family, model, knob_name, knob, res):
        res = {k: v for k, v in res.items() if not k.startswith("lp_") or k in ("lp_LPSP_pct", "lp_mean_soc_pct")}
        rows.append({"site": site, "label": label, "pv_kwp": kwp, "battery_kwh": cap, "class": cls,
                     "family": family, "model": model, "knob": knob_name, "knob_value": knob, **res})

    sim = lambda pol: S.simulate(load, on, pv, cap, *pol)  # noqa: E731
    add("no_forecast", "PV-only", "-", "-", np.nan, sim(S.pv_only(n)))
    for s in np.sort(np.r_[GRID_S_EXT, GRID_S, GRID_S_FINE]):
        add("no_forecast", "SOC-trigger", "-", "S", s, sim(S.soc_trigger(n, s)))
        add("no_forecast", "SOC-target", "-", "S", s, sim(S.soc_target(n, s)))
    add("no_forecast", "Mode0-thesis-0.25C", "-", "threshold", 0.8, sim(S.mode0(prev, 0.25, 0.8)))
    add("no_forecast", "Mode0-ratematched-0.5C", "-", "threshold", 0.8, sim(S.mode0(prev, 0.5, 0.8)))
    for thr in GRID_MODE0_THR:
        add("no_forecast", "Mode0-sweep-0.25C", "-", "threshold", thr, sim(S.mode0(prev, 0.25, thr)))
        add("no_forecast", "Mode0-sweep-0.5C", "-", "threshold", thr, sim(S.mode0(prev, 0.5, thr)))
    for mdl in FC_MODELS:
        r = risks[mdl]
        thetas = [0.5] if mdl == "PerfectBinary" else GRID_THETA
        for th in thetas:
            add("forecast", "Binary", mdl, "theta", th, sim(S.binary_topup(r, th)))
        for sh in S_HIGHS:
            for sl in GRID_SLOW:
                if sl <= sh + 1e-9:
                    add("forecast", f"RiskTarget-Sh{sh:.1f}", mdl, "S_low", sl, sim(S.risk_target(r, sl, sh)))
    for w in W_LP_MEAN:
        add("oracle", "LP-meansoc", "oracle", "lambda", w, oracle_point(load, on, pv, cap, w, "meansoc"))
    for w in W_LP_HINGE:
        add("oracle", "LP-hinge80", "oracle", "mu", w, oracle_point(load, on, pv, cap, w, "hinge80"))
    for w in W_DP_MEAN:
        add("oracle", "DP-meansoc", "oracle", "w", w, dp_point(load, on, pv, cap, w, "meansoc"))
    for w in W_DP_STEP:
        add("oracle", "DP-step80", "oracle", "w", w, dp_point(load, on, pv, cap, w, "step80"))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- analysis
def _step_at(front: pd.DataFrame, x: str, xq: float) -> float:
    """Lowest LPSP among front points with stress <= xq (NaN if none)."""
    s = front[front[x] <= xq]
    return float(s.LPSP_pct.min()) if len(s) else np.nan


def _x_needed(front: pd.DataFrame, x: str, lpsp: float) -> float:
    """Least stress at which the front reaches LPSP <= lpsp (NaN if never)."""
    s = front[front.LPSP_pct <= lpsp]
    return float(s[x].min()) if len(s) else np.nan

CFG_KEY = ["site", "label", "pv_kwp", "battery_kwh"]


def analyse(pts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reg_rows, reg_sum, gap_sum, head = [], [], [], []
    for key, g in pts.groupby(CFG_KEY, sort=False):
        nf = g[g["class"] == "no_forecast"]
        fc = g[g["class"] == "forecast"]
        lp = g[g.family.str.startswith("LP")]
        dp = g[g.family.str.startswith("DP")]
        for plane, x in PLANES.items():
            r = regret_table(fc, nf, x)
            r["plane"] = plane
            r["gap_oracle_LP_pp"] = oracle_gap(r, lp, x)
            r["gap_oracle_DP_pp"] = oracle_gap(r, dp, x)
            reg_rows.append(r)
            # regret summary per model x (family | any)
            for mdl in FC_MODELS:
                rm = r[r.model == mdl]
                for fam, sub in [("any", rm)] + list(rm.groupby("family")):
                    ok = sub.dropna(subset=["regret_interp_pp"])
                    rec = dict(zip(CFG_KEY, key), plane=plane, model=mdl, family=fam, n_points=len(sub),
                               n_comparable=len(ok), n_regret_step_lt0=int((ok.regret_step_pp < 0).sum()),
                               n_regret_interp_lt0=int((ok.regret_interp_pp < 0).sum()))
                    if len(ok):
                        i = ok.regret_interp_pp.idxmin()
                        j = ok.regret_step_pp.idxmin()
                        rec.update(min_regret_interp_pp=ok.loc[i, "regret_interp_pp"], x_at_min_interp=ok.loc[i, x],
                                   knob_at_min_interp=f"{ok.loc[i, 'family']}:{ok.loc[i, 'knob']}={ok.loc[i, 'knob_value']}",
                                   bracket_width_at_min_interp=ok.loc[i, "interp_bracket_width"],
                                   min_regret_step_pp=ok.loc[j, "regret_step_pp"], x_at_min_step=ok.loc[j, x],
                                   median_regret_interp_pp=ok.regret_interp_pp.median(),
                                   min_gap_oracle_DP_pp=ok.gap_oracle_DP_pp.min(),
                                   min_gap_oracle_LP_pp=ok.gap_oracle_LP_pp.min())
                    reg_sum.append(rec)
            # oracle gaps of every family's front
            groups = [("no_forecast", "ALL", nf)] + [("no_forecast", f, s) for f, s in nf.groupby("family")]
            groups += [("forecast", f"{mdl}:any", fc[fc.model == mdl]) for mdl in FC_MODELS]
            groups += [("oracle", "DP", dp), ("oracle", "LP", lp)]
            for cls, name, sub in groups:
                fr = pareto_front(sub, x)
                gdp, glp = oracle_gap(fr, dp, x), oracle_gap(fr, lp, x)
                k = fr.LPSP_pct.idxmin()
                gap_sum.append(dict(zip(CFG_KEY, key), plane=plane, cls=cls, family=name, front_points=len(fr),
                                    min_LPSP_pct=fr.LPSP_pct.min(), x_at_min_LPSP=fr.loc[k, x],
                                    gap_DP_at_min_LPSP_pp=gdp[k], gap_LP_at_min_LPSP_pp=glp[k],
                                    min_gap_DP_pp=np.nanmin(gdp) if np.isfinite(gdp).any() else np.nan,
                                    median_gap_DP_pp=np.nanmedian(gdp) if np.isfinite(gdp).any() else np.nan,
                                    min_gap_LP_pp=np.nanmin(glp) if np.isfinite(glp).any() else np.nan,
                                    median_gap_LP_pp=np.nanmedian(glp) if np.isfinite(glp).any() else np.nan,
                                    x_range=f"{fr[x].min():.1f}-{fr[x].max():.1f}"))
            # headline per config x plane
            learned = r[r.model.isin(["RandomForest", "Logistic", "HourMarkov", "Climatology"])].dropna(
                subset=["regret_interp_pp"])
            perf = r[r.model == "PerfectBinary"].dropna(subset=["regret_interp_pp"])
            nff = pareto_front(nf, x)
            dpf, lpf = pareto_front(dp, x), pareto_front(lp, x)
            # (i) skill value: ML forecasters vs the best of no-forecast AND the statistical forecasters
            stat_ref = pd.concat([nf, fc[fc.model.isin(["HourMarkov", "Climatology"])]])
            ml = regret_table(fc[fc.model.isin(["RandomForest", "Logistic"])], stat_ref, x).dropna(
                subset=["regret_interp_pp"])
            # (ii) stress saved at equal LPSP: NF stress needed to reach the forecast point's LPSP minus its own
            xneed = np.array([_x_needed(nff, x, yv) for yv in learned.LPSP_pct])
            saving = xneed - learned[x].to_numpy(float)
            ks = int(np.nanargmax(saving)) if np.isfinite(saving).any() else None
            mlpts = fc[fc.model.isin(["RandomForest", "Logistic"])]
            srf = pareto_front(stat_ref, x)
            ml_saving = np.array([_x_needed(srf, x, yv) for yv in mlpts.LPSP_pct]) - mlpts[x].to_numpy(float)
            ml_saving_rel = ml_saving / np.array([_x_needed(srf, x, yv) for yv in mlpts.LPSP_pct])
            # (iii) sensitivity: NF restricted to the grids exactly as specified (S = 0.30..1.00 step 0.05)
            ext = nf.family.isin(["SOC-trigger", "SOC-target"]) & (
                (nf.knob_value < 0.30 - 1e-9) | np.isclose(nf.knob_value.to_numpy(float)[:, None], GRID_S_FINE).any(axis=1))
            nf_spec = nf[~ext]
            rs_spec = regret_table(learned.drop(columns=[c for c in learned.columns if c.startswith(("nf_", "regret",
                                   "interp_"))]), nf_spec, x).dropna(subset=["regret_interp_pp"])
            nfs_front = pareto_front(nf_spec, x)
            sav_spec = np.array([_x_needed(nfs_front, x, yv) for yv in learned.LPSP_pct]) - learned[x].to_numpy(float)
            bi = learned.loc[learned.regret_interp_pp.idxmin()]
            bs = learned.loc[learned.regret_step_pp.idxmin()]
            head.append(dict(zip(CFG_KEY, key), plane=plane,
                             nf_min_LPSP_pct=nff.LPSP_pct.min(), nf_best_family=nff.loc[nff.LPSP_pct.idxmin(), "family"],
                             nf_x_at_min=nff.loc[nff.LPSP_pct.idxmin(), x],
                             learned_min_regret_interp_pp=bi.regret_interp_pp,
                             learned_best_interp=f"{bi.model}/{bi.family}:{bi.knob}={bi.knob_value}",
                             learned_x_at_best_interp=bi[x], learned_bracket_width=bi.interp_bracket_width,
                             learned_min_regret_step_pp=bs.regret_step_pp,
                             learned_best_step=f"{bs.model}/{bs.family}:{bs.knob}={bs.knob_value}",
                             learned_n_points_regret_interp_lt0=int((learned.regret_interp_pp < 0).sum()),
                             learned_n_comparable=len(learned),
                             ml_min_regret_vs_nf_and_stat_pp=ml.regret_interp_pp.min() if len(ml) else np.nan,
                             ml_min_regret_step_vs_nf_and_stat_pp=ml.regret_step_pp.min() if len(ml) else np.nan,
                             learned_max_stress_saving_equal_LPSP=saving[ks] if ks is not None else np.nan,
                             learned_stress_saving_at_LPSP=learned.LPSP_pct.iloc[ks] if ks is not None else np.nan,
                             learned_stress_saving_point=(f"{learned.model.iloc[ks]}/{learned.family.iloc[ks]}:"
                                                          f"{learned.knob.iloc[ks]}={learned.knob_value.iloc[ks]}"
                                                          if ks is not None else ""),
                             learned_stress_saving_rel_pct=100 * saving[ks] / xneed[ks] if ks is not None else np.nan,
                             ml_max_stress_saving_vs_nf_and_stat=np.nanmax(ml_saving) if np.isfinite(ml_saving).any() else np.nan,
                             ml_max_stress_saving_vs_nf_and_stat_rel_pct=100 * np.nanmax(ml_saving_rel)
                             if np.isfinite(ml_saving_rel).any() else np.nan,
                             learned_stress_saving_x=learned[x].iloc[ks] if ks is not None else np.nan,
                             specgrid_learned_min_regret_interp_pp=rs_spec.regret_interp_pp.min(),
                             specgrid_learned_min_regret_step_pp=rs_spec.regret_step_pp.min(),
                             specgrid_learned_max_stress_saving=np.nanmax(sav_spec) if np.isfinite(sav_spec).any() else np.nan,
                             perfectbinary_min_regret_interp_pp=perf.regret_interp_pp.min() if len(perf) else np.nan,
                             oracle_DP_min_LPSP_pct=dpf.LPSP_pct.min(),
                             oracle_DP_x_at_min=dpf.loc[dpf.LPSP_pct.idxmin(), x],
                             oracle_LP_min_LPSP_pct=lpf.LPSP_pct.min(),
                             oracle_LP_x_at_min=lpf.loc[lpf.LPSP_pct.idxmin(), x],
                             nf_LPSP_at_oracle_DP_x=_step_at(nff, x, dpf.loc[dpf.LPSP_pct.idxmin(), x]),
                             learned_LPSP_at_oracle_DP_x=_step_at(pareto_front(learned, x), x,
                                                                  dpf.loc[dpf.LPSP_pct.idxmin(), x]),
                             nf_x_to_within_0p05_of_oracle=_x_needed(nff, x, dpf.LPSP_pct.min() + 0.05),
                             learned_x_to_within_0p05_of_oracle=_x_needed(pareto_front(learned, x), x,
                                                                          dpf.LPSP_pct.min() + 0.05),
                             learned_min_gap_DP_pp=learned.gap_oracle_DP_pp.min(),
                             learned_min_gap_LP_pp=learned.gap_oracle_LP_pp.min()))
    return (pd.concat(reg_rows, ignore_index=True), pd.DataFrame(reg_sum), pd.DataFrame(gap_sum),
            pd.DataFrame(head))


# ----------------------------------------------------------------------------- M3
def m3_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    split, events = [], []
    for site in SITES:
        for label in LABELS:
            d, m, outage, load, on, pv_full, pv = window(site, label, 1.0)
            idx = YEAR_INDEX[m]
            ev = outage_events(1 - on, load, idx).sort_values(["duration_h", "load_kwh"], ascending=False)
            max_out_load = float(load[on == 0].max())
            for kwp, cap in SIZES + [THESIS_SIZE]:
                p = pv * kwp
                prev = S.pv_ac_prev(pv_full * kwp, m)
                usable_ac = (S.C_MAX_FRAC - S.C_MIN_FRAC) * cap * S.ETA_D * S.ETA_INV
                pols = {"PV-only": S.pv_only(len(load)), "Mode0-thesis-0.25C": S.mode0(prev, 0.25, 0.8),
                        "Blanket (SOC-trigger 1.0)": S.soc_trigger(len(load), 1.0)}
                for name, pol in pols.items():
                    r = S.simulate(load, on, p, cap, *pol, return_series=True)
                    un = r["series"]["unserved"]
                    # unserved per event
                    o = (1 - on).astype(int)
                    st = np.flatnonzero(np.diff(np.r_[0, o]) == 1)
                    en = np.flatnonzero(np.diff(np.r_[o, 0]) == -1)
                    ev_un = np.array([un[a:b + 1].sum() for a, b in zip(st, en)])
                    dur = en - st + 1
                    top5 = np.sort(ev_un)[::-1][:5].sum()
                    split.append({"site": site, "label": label, "pv_kwp": round(kwp, 2), "battery_kwh": cap,
                                  "policy": name, "unserved_kwh": r["unserved_kwh"], "LPSP_pct": r["LPSP_pct"],
                                  "energy_limited_kwh": r["unserved_energy_limited_kwh"],
                                  "power_limited_kwh": r["unserved_power_limited_kwh"],
                                  "energy_limited_share_pct": 100 * r["unserved_energy_limited_kwh"] / r["unserved_kwh"]
                                  if r["unserved_kwh"] > 0 else np.nan,
                                  "unserved_in_events_ge_12h_kwh": ev_un[dur >= 12].sum(),
                                  "unserved_in_top5_events_kwh": top5,
                                  "usable_battery_ac_kwh": usable_ac, "max_outage_hour_load_kwh": max_out_load,
                                  "discharge_ac_limit_kw": min(0.5 * cap * S.ETA_INV, S.INV_KW),
                                  "pv_clipped_kwh": r["pv_clipped_kwh"]})
            for rank, (_, e) in enumerate(ev.head(10).iterrows(), 1):
                events.append({"site": site, "label": label, "rank": rank, "start": e.start,
                               "duration_h": int(e.duration_h), "load_kwh": e.load_kwh})
    return pd.DataFrame(split), pd.DataFrame(events)


# ----------------------------------------------------------------------------- forecast checks
def forecast_checks() -> pd.DataFrame:
    """Brier score of each model's P(outage at t+k) on Apr-Dec, both labels, and the difference between the
    regenerated gen-label forecasts and the v1 cache (pilot/results/forecasts_*_h6.pkl)."""
    rows = []
    m = eval_mask()
    for site in SITES:
        old = pd.read_pickle(PILOT / "results" / f"forecasts_{site.lower()}_h6.pkl")
        for label in LABELS:
            fc = get_forecasts(site, label)
            o = load_site(site)[f"outage_{label}"]
            for mdl in MODELS:
                for k in range(1, H + 1):
                    y = o.shift(-k).to_numpy()[m]
                    p = fc[mdl][k].to_numpy(float)[m]
                    ok = ~np.isnan(y)
                    rec = {"site": site, "label": label, "model": mdl, "k": k,
                           "brier": float(np.mean((p[ok] - y[ok]) ** 2))}
                    if label == "gen":
                        rec["mean_abs_diff_vs_v1_cache"] = float(np.nanmean(np.abs(p - old[mdl][k].to_numpy(float)[m])))
                    rows.append(rec)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- figures
def figures(pts: pd.DataFrame, reg: pd.DataFrame) -> None:
    for label in LABELS:
        for plane, x in PLANES.items():
            fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
            for i, site in enumerate(SITES):
                for j, (kwp, cap) in enumerate(SIZES):
                    ax = axes[i, j]
                    g = pts[(pts.site == site) & (pts.label == label) & (pts.pv_kwp == kwp) & (pts.battery_kwh == cap)]
                    nf = g[g["class"] == "no_forecast"]
                    ax.scatter(nf[x], nf.LPSP_pct, s=9, color="#b4b4b4", zorder=1, label="no-forecast points")
                    f = pareto_front(nf, x)
                    ax.step(f[x], f.LPSP_pct, where="post", color="#333333", lw=2, zorder=3,
                            label="best no-forecast (front)")
                    for mdl, col in COLORS.items():
                        f = pareto_front(g[(g["class"] == "forecast") & (g.model == mdl)], x)
                        ax.plot(f[x], f.LPSP_pct, "-o" if mdl != "PerfectBinary" else "--o", ms=2.5, lw=1.6,
                                color=col, zorder=2, label=f"{mdl} (front)")
                    for fam, ls in [("DP", ":"), ("LP", "-.")]:
                        f = pareto_front(g[g.family.str.startswith(fam)], x)
                        ax.plot(f[x], f.LPSP_pct, ls, color="#000000", lw=1.6, zorder=4,
                                label=f"oracle {fam}" + (" (policy action set)" if fam == "DP" else " (may curtail PV)"))
                    ax.set_title(f"{SITE_NAME[site]}: {kwp:g} kWp, {cap} kWh", fontsize=10)
                    ax.set_xlabel({"meansoc": "mean SOC (%)", "hours80": "hours with SOC ≥ 80 % (Apr–Dec)"}[plane])
                    ax.set_ylabel("LPSP (%)")
                    ax.grid(alpha=0.25, lw=0.5)
                    top = max(nf.LPSP_pct.max(), 1.0) * 1.1
                    ax.set_ylim(0, top)
                    for s in ("top", "right"):
                        ax.spines[s].set_visible(False)
            axes[0, 0].legend(fontsize=7, loc="upper right")
            fig.suptitle(f"S1 dispatch v2 - LPSP vs {plane} - label {label}", fontsize=11)
            fig.tight_layout()
            fig.savefig(OUT / f"pareto_{plane}_{label}.png", dpi=200)
            plt.close(fig)
    # regret plot, primary label
    for plane, x in PLANES.items():
        fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
        for i, site in enumerate(SITES):
            for j, (kwp, cap) in enumerate(SIZES):
                ax = axes[i, j]
                g = reg[(reg.site == site) & (reg.label == PRIMARY_LABEL) & (reg.pv_kwp == kwp) &
                        (reg.battery_kwh == cap) & (reg.plane == plane)]
                for mdl, col in COLORS.items():
                    sub = pareto_front(g[g.model == mdl].dropna(subset=["regret_interp_pp"]), x)
                    ax.plot(sub[x], sub.regret_interp_pp, "-o", ms=2.5, lw=1.4, color=col, label=mdl)
                ax.axhline(0, color="#333333", lw=1)
                ax.set_title(f"{SITE_NAME[site]}: {kwp:g} kWp, {cap} kWh", fontsize=10)
                ax.set_xlabel({"meansoc": "mean SOC (%)", "hours80": "hours with SOC ≥ 80 %"}[plane])
                ax.set_ylabel("regret vs best no-forecast (pp LPSP)")
                ax.grid(alpha=0.25, lw=0.5)
                for s in ("top", "right"):
                    ax.spines[s].set_visible(False)
        axes[0, 0].legend(fontsize=7)
        fig.suptitle(f"Regret of each forecaster's front (interpolated baseline), {plane}, label {PRIMARY_LABEL}; "
                     "< 0 = forecast beats no-forecast", fontsize=11)
        fig.tight_layout()
        fig.savefig(OUT / f"regret_{plane}_{PRIMARY_LABEL}.png", dpi=200)
        plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refit", action="store_true", help="regenerate the forecasts")
    ap.add_argument("--analyse-only", action="store_true", help="re-run analysis/figures from policy_points.csv")
    a = ap.parse_args()
    t0 = time.time()
    if a.analyse_only:
        pts = pd.read_csv(OUT / "policy_points.csv")
        reg, reg_sum, gap_sum, head = analyse(pts)
        reg.to_csv(OUT / "regret_points.csv", index=False)
        reg_sum.to_csv(OUT / "regret_summary.csv", index=False)
        gap_sum.to_csv(OUT / "oracle_gap_summary.csv", index=False)
        head.to_csv(OUT / "headline.csv", index=False)
        figures(pts, reg)
        return
    for site in SITES:
        for label in LABELS:
            get_forecasts(site, label, refit=a.refit)
    print(f"forecasts ready ({time.time() - t0:.0f} s)", flush=True)
    pv_unit()
    cfgs = [(s, l, kwp, cap) for l in LABELS for s in SITES for kwp, cap in SIZES]
    with Pool(2) as pool:
        parts = pool.map(run_config, cfgs)
    pts = pd.concat(parts, ignore_index=True)
    print(f"simulations done ({time.time() - t0:.0f} s); max |balance residual| "
          f"{pts.balance_residual_kwh.abs().max():.2e} kWh", flush=True)
    pts.to_csv(OUT / "policy_points.csv", index=False)
    reg, reg_sum, gap_sum, head = analyse(pts)
    reg.to_csv(OUT / "regret_points.csv", index=False)
    reg_sum.to_csv(OUT / "regret_summary.csv", index=False)
    gap_sum.to_csv(OUT / "oracle_gap_summary.csv", index=False)
    head.to_csv(OUT / "headline.csv", index=False)
    split, events = m3_tables()
    split.to_csv(OUT / "m3_unserved_split.csv", index=False)
    events.to_csv(OUT / "m3_longest_outages.csv", index=False)
    forecast_checks().to_csv(OUT / "forecast_checks.csv", index=False)
    figures(pts, reg)
    json.dump({"runtime_s": round(time.time() - t0, 1), "n_policy_points": int(len(pts)),
               "max_abs_balance_residual_kwh": float(pts.balance_residual_kwh.abs().max())},
              open(OUT / "run_info.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    print(head.round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
