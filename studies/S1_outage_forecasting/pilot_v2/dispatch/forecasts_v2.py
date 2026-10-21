"""Out-of-sample outage forecasts for the dispatch experiment, regenerated for each label.

Method = pilot/dispatch_value.rolling_forecasts (rolling origin by month, Apr-Dec test months, embargo so no
training target falls in the test month; RandomForest(300, min_samples_leaf=5, seed 42), Logistic(C=0.5),
HourMarkov, Climatology from pilot/pilot_s1.py - imported, not copied), with ONE change for decision-time alignment
(Reviewer 2, SHOULD-FIX 1): the feature `load_roll24` is shifted by one hour, so that every feature in row t is known
at the START of hour t (outage status of hour t is assumed observable at its start; load only up to hour t-1).
Row t, column k = P(outage at t + k | information at the start of hour t), k = 1..6.
Dispatch risk_t = max_k row t (targets t+1 .. t+6).

The cached v1 forecasts (pilot/results/forecasts_*_h6.pkl) used label gen>0 and end-of-hour load features; they are
not used for the dispatch results, only compared in run_all (`forecast_cache_comparison.csv`).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import H, OUT, SEED, site_frame
from pilot_s1 import Climatology, HourMarkov, features   # noqa: E402  (pilot code, imported)

MODELS = ["RandomForest", "Logistic", "HourMarkov", "Climatology"]
CONFIG = {"version": 2, "features": "pilot_s1.features(with_temp=False), load_roll24 shifted +1 h",
          "rf": "n_estimators=300,min_samples_leaf=5,seed=42", "lr": "StandardScaler+LogReg(C=0.5)", "H": H}


def features_start_of_hour(d: pd.DataFrame) -> pd.DataFrame:
    """pilot_s1.features without temperature, with load_roll24 using loads up to hour t-1 only."""
    f = features(d, with_temp=False)
    f["load_roll24"] = d["load_kwh"].shift(1).rolling(24).mean()
    return f


def rolling_forecasts(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Same loop as pilot/dispatch_value.rolling_forecasts, on start-of-hour features."""
    X_all = features_start_of_hour(d)
    out = {m: pd.DataFrame(index=d.index, columns=range(1, H + 1), dtype=float) for m in MODELS}
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


def cache_path(site: str, label: str):
    h = hashlib.sha1(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()[:8]
    return OUT / f"forecasts_{site}_{label}_h{H}_{h}.pkl"


def get_forecasts(site: str, label: str, refit: bool = False) -> dict[str, pd.DataFrame]:
    """Load (or regenerate) the forecasts; cache name carries a hash of CONFIG so it cannot silently go stale."""
    p = cache_path(site, label)
    if p.exists() and not refit:
        return pd.read_pickle(p)
    fc = rolling_forecasts(site_frame(site, label))
    pd.to_pickle(fc, p)
    return fc


def dispatch_risk(fc: dict[str, pd.DataFrame], mask: np.ndarray, outage: np.ndarray) -> dict[str, np.ndarray]:
    """risk_t = max_k P(outage at t+k), k=1..H, for each model over the window, plus the binary
    'PerfectBinary' risk = 1 if an outage actually occurs in t+1..t+H (same policy shape, not an oracle)."""
    risks = {m: fc[m].loc[mask].max(axis=1).to_numpy(float) for m in MODELS}
    for m, r in risks.items():
        if np.isnan(r).any():
            raise ValueError(f"{m}: missing forecasts in the evaluation window")
    o = np.asarray(outage, int)
    n = len(o)
    fut = np.array([o[t + 1:t + 1 + H].max() if t + 1 < n else 0 for t in range(n)], float)
    risks["PerfectBinary"] = fut[mask]
    return risks
