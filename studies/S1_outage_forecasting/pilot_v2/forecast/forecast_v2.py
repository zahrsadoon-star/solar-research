"""S1 pilot v2 - forecasting part, revised after Reviewer 2 (agent_notes/claude_reviewer2_S1.md, M1, M5, M6).

Changes vs pilot v1:
- Primary label outage = (grid_kwh == 0); sensitivity label = (generator_kwh > 0)  [M5]
- Baselines: persistence; seasonal-naive (same hour, previous day); expanding hour-of-day climatology (v1's reference,
  renamed); trailing 7/14/28-day hour-of-day climatology; hour-of-day Markov chain on all past data and on the
  trailing 28 days. Skill is reported against the STRONGEST baseline at each site and horizon  [M1]
- ML models (logistic, random forest, LightGBM) also receive the trailing 14-day climatology as a feature, so they
  are not denied information the baselines use.
- Leakage decomposition: rolling-origin vs blocked monthly CV with future months and a 7-day embargo vs random 80/20,
  all scored on April-December rows  [M6]
- Hourly out-of-sample predictions are saved for significance tests (Diebold-Mariano, bootstrap).
Every value used below is available at forecast time t (targets at t+h).
Run:  python forecast_v2.py      -> results/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RAW = REPO / "data" / "raw"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
HORIZONS = [1, 3, 6, 12, 24]
SEED = 42
IDX = pd.date_range("2018-01-01", periods=8760, freq="h")


def load(site: str, label: str = "grid0") -> pd.DataFrame:
    if site == "BG":
        b = pd.read_excel(RAW / "BG18760_with_analysis.xlsx", sheet_name="Hourly Data")
        grid, gen = b["Grid (kWh)"].values, b["Generator (kWh)"].values
    else:
        k = pd.read_excel(RAW / "KR-8760.xlsx", header=None).iloc[:8760]
        grid, gen = k[0].values.astype(float), k[1].values.astype(float)
    d = pd.DataFrame({"grid_kwh": grid, "gen_kwh": gen}, index=IDX)
    d["load_kwh"] = d.grid_kwh + d.gen_kwh
    d["outage"] = ((d.grid_kwh == 0) if label == "grid0" else (d.gen_kwh > 0)).astype(int)
    return d


# ----------------------------------------------------------------------------- baselines (all causal)
def trailing_hour_clim(o: pd.Series, h: int, days: int) -> pd.Series:
    """P(outage at t+h) = mean of o at the same clock hour as t+h over the previous `days` days, using only
    observations at or before t (lag 24*k - h >= 0)."""
    k0 = int(np.ceil(h / 24))
    lagged = [o.shift(24 * k - h) for k in range(max(k0, 1), max(k0, 1) + days)]
    return (pd.concat(lagged, axis=1).mean(axis=1) * days + 1) / (days + 2)   # Laplace smoothing


def expanding_hour_clim(o: pd.Series, h: int) -> pd.Series:
    """v1 reference: hour-of-day mean of all observations up to t at the target clock hour."""
    k0 = max(int(np.ceil(h / 24)), 1)
    s = o.shift(24 * k0 - h)
    hr = (o.index + pd.Timedelta(hours=h)).hour
    g = s.groupby(hr)
    return ((g.cumsum() + 1) / (g.cumcount() + 1 + 2)).reindex(o.index)


def seasonal_naive(o: pd.Series, h: int) -> pd.Series:
    k0 = max(int(np.ceil(h / 24)), 1)
    return o.shift(24 * k0 - h).astype(float)


def hour_markov(o: pd.Series, h: int, fit_end: pd.Timestamp, window_days: int | None) -> pd.Series:
    """Hour-of-day 2-state Markov chain fitted on data before fit_end (optionally only the last window_days),
    propagated h steps from the state at t."""
    hist = o[o.index < fit_end]
    if window_days:
        hist = hist[hist.index >= fit_end - pd.Timedelta(days=window_days)]
    s, hrs = hist.values, hist.index.hour
    P = np.zeros((24, 2, 2))
    for hr in range(24):
        m = hrs[:-1] == hr
        for a in (0, 1):
            sel = m & (s[:-1] == a)
            p1 = (s[1:][sel].sum() + 1) / (sel.sum() + 2)
            P[hr, a] = [1 - p1, p1]
    out = np.empty(len(o))
    for i, (st, t) in enumerate(zip(o.values, o.index)):
        v = np.array([1.0 - st, float(st)])
        for k in range(h):
            v = v @ P[(t.hour + k) % 24]
        out[i] = v[1]
    return pd.Series(out, index=o.index)


# ----------------------------------------------------------------------------- features for ML
def features(d: pd.DataFrame, h: int) -> pd.DataFrame:
    s = d["outage"]
    f = pd.DataFrame(index=d.index)
    f["state"] = s
    for lag in [1, 2, 3, 6, 12, 23, 24, 48, 168]:
        f[f"lag_{lag}"] = s.shift(lag)
    for w in [6, 12, 24, 168]:
        f[f"roll_{w}"] = s.rolling(w).mean()
    f["run_len"] = s.groupby((s != s.shift()).cumsum()).cumcount() + 1
    tgt = d.index + pd.Timedelta(hours=h)
    f["thr_sin"], f["thr_cos"] = np.sin(2 * np.pi * tgt.hour / 24), np.cos(2 * np.pi * tgt.hour / 24)
    f["target_hour_odd"] = tgt.hour % 2
    f["dow"], f["month"] = d.index.dayofweek, d.index.month
    f["load_lag1"], f["load_roll24"] = d["load_kwh"].shift(1), d["load_kwh"].rolling(24).mean()
    f["clim_trail14"] = trailing_hour_clim(s, h, 14)
    return f


def ml_models():
    return {
        "Logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5)),
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED),
        "LightGBM": lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=20,
                                       subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEED,
                                       verbose=-1),
    }


# ----------------------------------------------------------------------------- evaluation
def run_site(site: str, label: str) -> pd.DataFrame:
    d = load(site, label)
    o = d["outage"]
    preds = []
    for h in HORIZONS:
        y = o.shift(-h)
        X = features(d, h)
        base_static = {
            "Persistence": o.astype(float),
            "SeasonalNaive": seasonal_naive(o, h),
            "ClimExpanding": expanding_hour_clim(o, h),
            "ClimTrail7": trailing_hour_clim(o, h, 7),
            "ClimTrail14": trailing_hour_clim(o, h, 14),
            "ClimTrail28": trailing_hour_clim(o, h, 28),
        }
        ok = X.notna().all(axis=1) & y.notna() & pd.concat(base_static, axis=1).notna().all(axis=1)
        t_target = d.index + pd.Timedelta(hours=h)
        for m in range(4, 13):
            start = pd.Timestamp(f"2018-{m:02d}-01")
            te = ok & (d.index.month == m)
            tr = ok & (d.index < start) & (t_target < start)
            p = {k: v[te].values for k, v in base_static.items()}
            p["MarkovAll"] = hour_markov(o, h, start, None)[te].values
            p["MarkovTrail28"] = hour_markov(o, h, start, 28)[te].values
            for name, mdl in ml_models().items():
                mdl.fit(X[tr], y[tr].astype(int))
                p[name] = mdl.predict_proba(X[te])[:, 1]
            for name, pr in p.items():
                preds.append(pd.DataFrame({"site": site, "label": label, "h": h, "month": m, "model": name,
                                           "time": d.index[te], "y": y[te].astype(int).values,
                                           "p": np.clip(pr, 1e-4, 1 - 1e-4)}))
    return pd.concat(preds, ignore_index=True)


def leakage_decomposition(site: str, label: str) -> list[dict]:
    """LightGBM ROC-AUC on April-December rows under three protocols  [M6]."""
    d = load(site, label)
    o = d["outage"]
    rows = []
    for h in [1, 6, 24]:
        y, X = o.shift(-h), features(d, h)
        ok = X.notna().all(axis=1) & y.notna()
        X, y = X[ok], y[ok].astype(int)
        t_target = X.index + pd.Timedelta(hours=h)
        res = {}
        for proto in ["rolling_origin", "blocked_future_7d_embargo"]:
            ys, ps = [], []
            for m in range(4, 13):
                start, end = pd.Timestamp(f"2018-{m:02d}-01"), pd.Timestamp(f"2018-{m:02d}-01") + pd.offsets.MonthBegin(1)
                te = X.index.month == m
                if proto == "rolling_origin":
                    tr = (X.index < start) & (t_target < start)
                else:
                    gap = pd.Timedelta(days=7)
                    tr = ((t_target < start - gap) | (X.index >= end + gap))
                mdl = ml_models()["LightGBM"].fit(X[tr], y[tr])
                ys.append(y[te].values); ps.append(mdl.predict_proba(X[te])[:, 1])
            res[proto] = roc_auc_score(np.concatenate(ys), np.concatenate(ps))
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=X.index.month)
        mdl = ml_models()["LightGBM"].fit(Xtr, ytr)
        keep = Xte.index.month >= 4
        res["random_80_20"] = roc_auc_score(yte[keep], mdl.predict_proba(Xte[keep])[:, 1])
        rows.append({"site": site, "label": label, "h": h, **{f"auc_{k}": v for k, v in res.items()}})
    return rows


def summarise(pred: pd.DataFrame) -> pd.DataFrame:
    g = pred.groupby(["site", "label", "h", "model"])
    summ = g.apply(lambda x: pd.Series({"brier": brier_score_loss(x.y, x.p), "auc": roc_auc_score(x.y, x.p),
                                        "n": len(x)}), include_groups=False).reset_index()
    base_names = ["Persistence", "SeasonalNaive", "ClimExpanding", "ClimTrail7", "ClimTrail14", "ClimTrail28",
                  "MarkovAll", "MarkovTrail28"]
    best = (summ[summ.model.isin(base_names)].sort_values("brier").groupby(["site", "label", "h"]).first()
            .rename(columns={"model": "best_baseline", "brier": "brier_best_baseline"})[["best_baseline", "brier_best_baseline"]])
    exp = summ[summ.model == "ClimExpanding"].set_index(["site", "label", "h"])["brier"].rename("brier_clim_expanding")
    summ = summ.join(best, on=["site", "label", "h"]).join(exp, on=["site", "label", "h"])
    summ["skill_vs_best_baseline"] = 1 - summ.brier / summ.brier_best_baseline
    summ["skill_vs_clim_expanding_v1ref"] = 1 - summ.brier / summ.brier_clim_expanding
    return summ


def main() -> None:
    preds, leak = [], []
    for site in ["BG", "KR"]:
        for label in ["grid0", "gen"]:
            preds.append(run_site(site, label))
        leak += leakage_decomposition(site, "grid0")
    pred = pd.concat(preds, ignore_index=True)
    pred.to_parquet(OUT / "hourly_predictions.parquet", index=False)
    summ = summarise(pred)
    summ.round(4).to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(leak).round(4).to_csv(OUT / "leakage_decomposition.csv", index=False)
    pd.set_option("display.width", 220)
    show = summ[(summ.label == "grid0") & summ.model.isin(["Logistic", "RandomForest", "LightGBM"])]
    print(show[["site", "h", "model", "brier", "auc", "best_baseline", "brier_best_baseline",
                "skill_vs_best_baseline", "skill_vs_clim_expanding_v1ref"]].round(3).to_string(index=False))
    print(pd.DataFrame(leak).round(3).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
