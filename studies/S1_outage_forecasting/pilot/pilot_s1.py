"""S1 pilot: can grid outages be forecast better than simple baselines? (Baghdad BG and Karbala KR houses, 2018)

Outage label (both sites): 1 when the private/neighbourhood generator supplied energy in that hour (BG workbook's
'Outage (1/0)' equals generator > 0 in every hour). Hours with no grid and no generator energy cannot be told apart
from 'grid on, zero use' - counted and reported.

Protocol: rolling-origin monthly CV (train on all months before the test month, >= 3 months; test months Apr-Dec),
plus a random 80/20 split for the leakage comparison. Features use only information available at hour t.
Run:  python pilot_s1.py   (writes results/ next to this file)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / "data" / "raw"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
HORIZONS = [1, 3, 6, 12, 24]
SEED = 42


# ----------------------------------------------------------------------------- data
def load_sites() -> dict[str, pd.DataFrame]:
    idx = pd.date_range("2018-01-01", periods=8760, freq="h")
    bg = pd.read_excel(RAW / "BG18760_with_analysis.xlsx", sheet_name="Hourly Data")
    kr = pd.read_excel(RAW / "KR-8760.xlsx", header=None)
    wx = pd.read_csv(RAW / "nasa_power_baghdad_2018_hourly_local.csv", index_col=0, parse_dates=True)
    sites = {
        "BG": pd.DataFrame({"grid_kwh": bg["Grid (kWh)"].values, "gen_kwh": bg["Generator (kWh)"].values}, index=idx),
        "KR": pd.DataFrame({"grid_kwh": kr[0].values[:8760], "gen_kwh": kr[1].values[:8760]}, index=idx),
    }
    for name, d in sites.items():
        d["outage"] = (d["gen_kwh"] > 0).astype(int)
        d["load_kwh"] = d["grid_kwh"] + d["gen_kwh"]
        d["temp_c"] = wx["temp_air_c"].values  # Baghdad weather; used for KR only as a regional proxy (ablation)
    return sites


def data_quality(d: pd.DataFrame) -> dict:
    o = d["outage"].values
    starts = np.flatnonzero(np.diff(np.r_[0, o]) == 1)
    ends = np.flatnonzero(np.diff(np.r_[o, 0]) == -1)
    dur = ends - starts + 1
    return {"outage_share": float(o.mean()), "events": int(len(starts)), "outage_hours": int(o.sum()),
            "mean_duration_h": float(dur.mean()), "max_duration_h": int(dur.max()),
            "hours_no_grid_no_gen": int(((d["grid_kwh"] == 0) & (d["gen_kwh"] == 0)).sum())}


# ----------------------------------------------------------------------------- features
def features(d: pd.DataFrame, with_temp: bool) -> pd.DataFrame:
    s = d["outage"]
    f = pd.DataFrame(index=d.index)
    f["state"] = s
    for lag in [1, 2, 3, 6, 12, 23, 24, 48, 168]:
        f[f"lag_{lag}"] = s.shift(lag)
    for w in [6, 12, 24, 168]:
        f[f"roll_{w}"] = s.rolling(w).mean()
    run = s.groupby((s != s.shift()).cumsum()).cumcount() + 1          # hours in current state
    f["run_len"] = run
    f["hour_sin"] = np.sin(2 * np.pi * d.index.hour / 24)
    f["hour_cos"] = np.cos(2 * np.pi * d.index.hour / 24)
    f["dow"] = d.index.dayofweek
    f["month"] = d.index.month
    f["load_lag1"] = d["load_kwh"].shift(1)
    f["load_roll24"] = d["load_kwh"].rolling(24).mean()
    if with_temp:
        f["temp"] = d["temp_c"]
        f["temp_max24"] = d["temp_c"].rolling(24).max()
    return f


def target(d: pd.DataFrame, h: int) -> pd.Series:
    return d["outage"].shift(-h)


# ----------------------------------------------------------------------------- models
class Climatology:
    """P(outage | hour of target time, month) estimated on training data, Laplace smoothed."""
    def fit(self, X, y, t_index):
        g = pd.DataFrame({"y": y, "hr": t_index.hour, "m": t_index.month})
        self.table = g.groupby(["hr", "m"])["y"].agg(["sum", "count"])
        self.by_hour = g.groupby("hr")["y"].agg(["sum", "count"])
        return self

    def predict_proba(self, X, t_index):
        out = []
        for hr, m in zip(t_index.hour, t_index.month):
            if (hr, m) in self.table.index:
                s, c = self.table.loc[(hr, m)]
            else:   # unseen month in training: fall back to hour-of-day climatology
                s, c = self.by_hour.loc[hr]
            out.append((s + 1) / (c + 2))
        return np.array(out)


class HourMarkov:
    """Time-inhomogeneous 2-state Markov chain: transition matrix per hour of day, propagated h steps."""
    def fit(self, series: pd.Series):
        s = series.values.astype(int)
        hrs = series.index.hour
        self.P = np.zeros((24, 2, 2))
        for hr in range(24):
            m = (hrs[:-1] == hr)
            for a in (0, 1):
                sel = m & (s[:-1] == a)
                n1 = s[1:][sel].sum()
                n = sel.sum()
                p1 = (n1 + 1) / (n + 2)
                self.P[hr, a] = [1 - p1, p1]
        return self

    def predict_proba(self, state: np.ndarray, t_index: pd.DatetimeIndex, h: int) -> np.ndarray:
        out = np.empty(len(state))
        for i, (st, t) in enumerate(zip(state, t_index)):
            v = np.array([1.0, 0.0]) if st == 0 else np.array([0.0, 1.0])
            for k in range(h):
                v = v @ self.P[(t.hour + k) % 24]
            out[i] = v[1]
        return out


def ml_models():
    return {
        "Logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5)),
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=SEED),
        "LightGBM": lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=20,
                                       subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                       random_state=SEED, verbose=-1),
    }


# ----------------------------------------------------------------------------- evaluation
def evaluate_site(name: str, d: pd.DataFrame, with_temp: bool) -> tuple[list[dict], pd.DataFrame]:
    rows, preds_all = [], []
    X_all = features(d, with_temp)
    for h in HORIZONS:
        y_all = target(d, h)
        ok = X_all.notna().all(axis=1) & y_all.notna()
        X, y = X_all[ok], y_all[ok].astype(int)
        t_target = X.index + pd.Timedelta(hours=h)
        for test_month in range(4, 13):
            tr = X.index.month < test_month
            te = X.index.month == test_month
            # embargo: drop training rows whose target falls inside the test month
            tr &= t_target < pd.Timestamp(f"2018-{test_month:02d}-01")
            if y[te].nunique() < 2 or tr.sum() < 500:
                continue
            p = {}
            p["Persistence"] = X.loc[te, "state"].values.astype(float)
            clim = Climatology().fit(X[tr], y[tr], t_target[tr])
            p["Climatology"] = clim.predict_proba(X[te], t_target[te])
            mk = HourMarkov().fit(d["outage"][d.index < pd.Timestamp(f"2018-{test_month:02d}-01")])
            p["HourMarkov"] = mk.predict_proba(X.loc[te, "state"].values, X.index[te], h)
            for mname, mdl in ml_models().items():
                mdl.fit(X[tr], y[tr])
                p[mname] = mdl.predict_proba(X[te])[:, 1]
            yt = y[te].values
            for mname, pr in p.items():
                pr = np.clip(pr, 1e-4, 1 - 1e-4)
                rows.append({"site": name, "temp": with_temp, "h": h, "month": test_month, "model": mname,
                             "n": int(te.sum()), "brier": brier_score_loss(yt, pr), "auc": roc_auc_score(yt, pr)})
                preds_all.append(pd.DataFrame({"site": name, "h": h, "model": mname, "y": yt, "p": pr}))
    return rows, pd.concat(preds_all)


def leakage_check(name: str, d: pd.DataFrame) -> list[dict]:
    """Random 80/20 split (as in the thesis) vs the rolling-origin result, LightGBM, same features."""
    out = []
    X_all = features(d, with_temp=(name == "BG"))
    for h in HORIZONS:
        y_all = target(d, h)
        ok = X_all.notna().all(axis=1) & y_all.notna()
        X, y = X_all[ok], y_all[ok].astype(int)
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=X.index.month)
        m = ml_models()["LightGBM"].fit(Xtr, ytr)
        pr = m.predict_proba(Xte)[:, 1]
        out.append({"site": name, "h": h, "split": "random_80_20", "brier": brier_score_loss(yte, pr),
                    "auc": roc_auc_score(yte, pr)})
    return out


def main() -> None:
    sites = load_sites()
    quality = {k: data_quality(v) for k, v in sites.items()}
    rows, leak = [], []
    for name, d in sites.items():
        for wt in ([True, False] if name == "BG" else [False]):
            r, _ = evaluate_site(name, d, wt)
            rows += r
        leak += leakage_check(name, d)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "fold_scores.csv", index=False)
    summ = (res.groupby(["site", "temp", "h", "model"])
               .agg(brier=("brier", "mean"), auc=("auc", "mean"), folds=("month", "count")).reset_index())
    clim = summ[summ.model == "Climatology"][["site", "temp", "h", "brier"]].rename(columns={"brier": "brier_clim"})
    summ = summ.merge(clim, on=["site", "temp", "h"])
    summ["brier_skill_vs_clim"] = 1 - summ["brier"] / summ["brier_clim"]
    summ.to_csv(OUT / "summary.csv", index=False)
    lk = pd.DataFrame(leak)
    roll = summ[(summ.model == "LightGBM") & ((summ.site == "KR") | summ.temp)][["site", "h", "brier", "auc"]]
    lk = lk.merge(roll, on=["site", "h"], suffixes=("_random", "_rolling"))
    lk.to_csv(OUT / "leakage_check.csv", index=False)
    json.dump(quality, open(OUT / "data_quality.json", "w"), indent=1)
    print(json.dumps(quality, indent=1))
    pd.set_option("display.width", 200)
    print(summ.round(4).to_string(index=False))
    print(lk.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
