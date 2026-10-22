"""S1 (narrowed scope): which algorithm forecasts grid outages best?

One small, self-contained benchmark - no battery, no dispatch, no PV.
Question: will the national grid be OFF in the next hour (h = 1) / in 6 hours (h = 6)?
Data: Baghdad (BG) and Karbala (KR) households, 2018, hourly; outage = grid energy == 0 (inferred from metering).
Same features and same time-ordered evaluation for every algorithm, so the comparison is fair:
  - train on all months before the test month, test on that month, for April ... December (9 folds)
  - also reported: a random 80/20 split (the thesis approach) to show how much it inflates accuracy
Algorithms (12): Logistic Regression, Naive Bayes, k-Nearest Neighbours, Decision Tree, Random Forest, Extra Trees,
Gradient Boosting, XGBoost, LightGBM, CatBoost, Support Vector Machine, Neural Network (MLP).
Reference points (not algorithms): always "no outage", persistence (same as now), same clock hour last 7 days.
Run:  python benchmark.py      -> results/
"""
from __future__ import annotations

import time
from pathlib import Path

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[2] / "data" / "raw"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
SEED = 42
HORIZONS = [1, 6]
IDX = pd.date_range("2018-01-01", periods=8760, freq="h")
NAMES = {"BG": "Baghdad", "KR": "Karbala"}


def load(site: str) -> pd.DataFrame:
    if site == "BG":
        b = pd.read_excel(RAW / "BG18760_with_analysis.xlsx", sheet_name="Hourly Data")
        grid, gen = b["Grid (kWh)"].values, b["Generator (kWh)"].values
    else:
        k = pd.read_excel(RAW / "KR-8760.xlsx", header=None).iloc[:8760]
        grid, gen = k[0].values.astype(float), k[1].values.astype(float)
    d = pd.DataFrame({"grid_kwh": grid, "gen_kwh": gen}, index=IDX)
    d["load_kwh"] = d.grid_kwh + d.gen_kwh
    d["outage"] = (d.grid_kwh == 0).astype(int)
    return d


def features(d: pd.DataFrame, h: int) -> pd.DataFrame:
    """Only information known at forecast time t; target is the grid state at t + h."""
    s = d["outage"]
    f = pd.DataFrame(index=d.index)
    f["now"] = s
    for lag in [1, 2, 3, 6, 12, 24, 48, 168]:
        f[f"lag_{lag}h"] = s.shift(lag)
    for w in [6, 24, 168]:
        f[f"share_last_{w}h"] = s.rolling(w).mean()
    f["hours_in_state"] = s.groupby((s != s.shift()).cumsum()).cumcount() + 1
    tgt = d.index + pd.Timedelta(hours=h)
    f["target_hour_sin"] = np.sin(2 * np.pi * tgt.hour / 24)
    f["target_hour_cos"] = np.cos(2 * np.pi * tgt.hour / 24)
    f["weekday"] = d.index.dayofweek
    k0 = max(int(np.ceil(h / 24)), 1)       # same clock hour as the target, previous 7 days (known at t)
    f["same_hour_last_7d"] = pd.concat([s.shift(24 * k - h) for k in range(k0, k0 + 7)], axis=1).mean(axis=1)
    f["load_last_h"] = d["load_kwh"].shift(1)
    f["load_last_24h"] = d["load_kwh"].rolling(24).mean()
    return f


def algorithms() -> dict:
    sc = StandardScaler
    return {
        "Logistic Regression": make_pipeline(sc(), LogisticRegression(max_iter=3000)),
        "Naive Bayes": make_pipeline(sc(), GaussianNB()),
        "k-Nearest Neighbours": make_pipeline(sc(), KNeighborsClassifier(n_neighbors=25)),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED),
        "Extra Trees": ExtraTreesClassifier(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED),
        "Gradient Boosting": GradientBoostingClassifier(random_state=SEED),
        "XGBoost": XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=5, subsample=0.8,
                                 colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbosity=0),
        "LightGBM": lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=31, subsample=0.8,
                                       subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1),
        "CatBoost": CatBoostClassifier(iterations=300, depth=6, random_seed=SEED, verbose=False),
        "SVM": make_pipeline(sc(), SVC(C=1.0, probability=True, random_state=SEED)),
        "Neural Network (MLP)": make_pipeline(sc(), MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500,
                                                                  early_stopping=True, random_state=SEED)),
    }


def scores(y, p) -> dict:
    yhat = (p >= 0.5).astype(int)
    return {"accuracy": accuracy_score(y, yhat), "precision": precision_score(y, yhat, zero_division=0),
            "recall": recall_score(y, yhat, zero_division=0), "f1": f1_score(y, yhat, zero_division=0),
            "auc": roc_auc_score(y, p), "brier": brier_score_loss(y, p)}


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows, folds, rand = [], [], []
    for site in ["BG", "KR"]:
        d = load(site)
        for h in HORIZONS:
            X, y = features(d, h), d["outage"].shift(-h)
            ok = X.notna().all(axis=1) & y.notna()
            X, y = X[ok], y[ok].astype(int)
            t_target = X.index + pd.Timedelta(hours=h)
            preds = {n: [] for n in list(algorithms()) + ["Always no outage", "Persistence", "Same hour last 7 days"]}
            ys, secs = [], {n: 0.0 for n in algorithms()}
            for m in range(4, 13):
                start = pd.Timestamp(f"2018-{m:02d}-01")
                tr = (X.index < start) & (t_target < start)
                te = X.index.month == m
                ys.append(y[te].values)
                preds["Always no outage"].append(np.zeros(te.sum()))
                preds["Persistence"].append(X.loc[te, "now"].values.astype(float))
                preds["Same hour last 7 days"].append(X.loc[te, "same_hour_last_7d"].values)
                for name, mdl in algorithms().items():
                    t0 = time.time()
                    mdl.fit(X[tr], y[tr])
                    p = mdl.predict_proba(X[te])[:, 1]
                    secs[name] += time.time() - t0
                    preds[name].append(p)
                    folds.append({"site": site, "h": h, "month": m, "algorithm": name,
                                  **scores(y[te].values, p)})
            yy = np.concatenate(ys)
            for name, ps in preds.items():
                p = np.clip(np.concatenate(ps), 0, 1)
                rows.append({"site": site, "h": h, "algorithm": name,
                             "kind": "reference" if name in ("Always no outage", "Persistence",
                                                             "Same hour last 7 days") else "algorithm",
                             **scores(yy, p), "fit_seconds": round(secs.get(name, 0.0), 1)})
            # thesis-style random split, for comparison only
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=X.index.month)
            for name, mdl in algorithms().items():
                mdl.fit(Xtr, ytr)
                rand.append({"site": site, "h": h, "algorithm": name,
                             "accuracy_random_split": accuracy_score(yte, mdl.predict(Xte))})
    return pd.DataFrame(rows), pd.DataFrame(folds), pd.DataFrame(rand)


def main() -> None:
    res, folds, rand = run()
    res = res.merge(rand, on=["site", "h", "algorithm"], how="left")
    res = res.sort_values(["site", "h", "brier"]).reset_index(drop=True)
    res["rank_by_brier"] = res[res.kind == "algorithm"].groupby(["site", "h"])["brier"].rank().astype("Int64")
    res.round(4).to_csv(OUT / "benchmark_results.csv", index=False)
    folds.round(4).to_csv(OUT / "benchmark_fold_scores.csv", index=False)
    # average rank across the 4 site x horizon cases (lower = better)
    avg = (res[res.kind == "algorithm"].groupby("algorithm")["rank_by_brier"].mean().sort_values()
           .rename("mean_rank").reset_index())
    avg.round(2).to_csv(OUT / "overall_ranking.csv", index=False)

    pd.set_option("display.width", 200)
    cols = ["algorithm", "accuracy", "f1", "auc", "brier", "accuracy_random_split", "rank_by_brier"]
    for (site, h), g in res.groupby(["site", "h"]):
        print(f"\n=== {NAMES[site]}, outage in {h} h (time-ordered test, Apr-Dec) ===")
        print(g[cols].round(3).to_string(index=False))
    print("\n=== Overall ranking (mean rank by Brier score over 4 cases) ===")
    print(avg.round(2).to_string(index=False))

    fig, axes = plt.subplots(1, 4, figsize=(17, 4.6), sharey=True)
    order = avg.algorithm.tolist()
    for ax, ((site, h), g) in zip(axes, res[res.kind == "algorithm"].groupby(["site", "h"])):
        g = g.set_index("algorithm").loc[order]
        ax.barh(range(len(g)), g.accuracy * 100, color="#2166ac")
        ref = res[(res.site == site) & (res.h == h) & (res.algorithm == "Same hour last 7 days")].accuracy.item()
        ax.axvline(ref * 100, color="#d6604d", ls="--", label="same hour last 7 days")
        ax.set_xlim(50, 100); ax.set_title(f"{NAMES[site]}, {h} h ahead"); ax.set_xlabel("accuracy (%)")
        ax.set_yticks(range(len(g))); ax.set_yticklabels(order)
    axes[0].invert_yaxis(); axes[0].legend(fontsize=8, loc="lower right")
    plt.tight_layout(); plt.savefig(OUT / "benchmark_accuracy.png", dpi=200)


if __name__ == "__main__":
    main()
