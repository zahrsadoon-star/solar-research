"""Independent outage benchmark; run `independent` before `compare`.

All observations through the completed origin hour are available. Energy is kWh,
lags/durations are hours, and probabilities and metric values are dimensionless.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
import pandas as pd
import sklearn
import openpyxl
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "results"
CONFIG = json.loads((HERE / "config.json").read_text())


def digest(path: Path) -> str:
    """Return SHA256 of file bytes (dimensionless)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_path(site: str) -> Path:
    """Resolve the specified raw energy workbook."""
    return ROOT / "data/raw" / {"BG": "BG18760_with_analysis.xlsx", "KR": "KR-8760.xlsx"}[site]


def load_site(site: str) -> pd.DataFrame:
    """Load exactly the specified rows; energy columns are kWh, cadence is 1 h."""
    if site == "BG":
        raw = pd.read_excel(raw_path(site), sheet_name="Hourly Data")[["Grid (kWh)", "Generator (kWh)"]]
    elif site == "KR":
        raw = pd.read_excel(raw_path(site), header=None).iloc[:8760, :2]
    else:
        raise ValueError(site)
    if len(raw) != 8760:
        raise ValueError(f"{site}: expected 8760 selected rows, got {len(raw)}")
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    numeric.columns = ["grid_kwh", "generator_kwh"]
    numeric.index = pd.date_range("2018-01-01", periods=len(numeric), freq="h")
    numeric.attrs["non_numeric"] = int((raw.notna() & raw.apply(pd.to_numeric, errors="coerce").isna()).sum().sum())
    numeric["load_kwh"] = numeric.grid_kwh + numeric.generator_kwh
    numeric["outage"] = numeric.grid_kwh.eq(0).astype(float).where(numeric.grid_kwh.notna())
    return numeric


def same_hour_history(outage: pd.Series, horizon_h: int) -> pd.Series:
    """Mean of seven prior days at the target clock hour, using only times <= t."""
    offsets = [24 * day - horizon_h for day in range(1, CONFIG["history_days"] + 1)]
    if min(offsets) < 0:
        raise ValueError("History would use future observations")
    return pd.concat([outage.shift(offset) for offset in offsets], axis=1).mean(axis=1, skipna=False)


def features(frame: pd.DataFrame, horizon_h: int) -> pd.DataFrame:
    """Build all listed causal features; state duration counts hours including t."""
    outage = frame.outage
    result = pd.DataFrame({"outage_now": outage})
    for lag in CONFIG["lags_h"]:
        result[f"outage_lag_{lag}h"] = outage.shift(lag)
    for window in CONFIG["windows_h"]:
        result[f"outage_mean_{window}h"] = outage.rolling(window).mean()
    durations: list[float] = []
    previous, duration = np.nan, 0
    for state in outage:
        duration = duration + 1 if pd.notna(state) and state == previous else 1
        durations.append(float(duration) if pd.notna(state) else np.nan)
        previous = state
    result["state_duration_h"] = durations
    target_clock = (frame.index + pd.Timedelta(hours=horizon_h)).hour
    result["target_hour_sin"] = np.sin(2 * np.pi * target_clock / 24)
    result["target_hour_cos"] = np.cos(2 * np.pi * target_clock / 24)
    result["origin_weekday"] = frame.index.dayofweek
    result["same_hour"] = same_hour_history(outage, horizon_h)
    result["load_lag_1h_kwh"] = frame.load_kwh.shift(1)
    result["load_mean_24h_kwh"] = frame.load_kwh.rolling(24).mean()
    return result


def split_masks(index: pd.DatetimeIndex, horizon_h: int, month: int) -> tuple[np.ndarray, np.ndarray]:
    """Purge training origins whose target reaches the test month (times in h)."""
    boundary = pd.Timestamp(2018, month, 1)
    return ((index < boundary) & (index + pd.Timedelta(hours=horizon_h) < boundary), index.month == month)


def metrics(truth: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    """Pooled dimensionless metrics; undefined AUC is NaN, zero-denominator F1 is zero."""
    predicted = probability >= CONFIG["threshold"]
    return {"accuracy": accuracy_score(truth, predicted), "f1": f1_score(truth, predicted, zero_division=0),
            "auc": roc_auc_score(truth, probability) if len(np.unique(truth)) == 2 else np.nan,
            "brier": brier_score_loss(truth, probability)}


def independent() -> None:
    """Run and freeze the independent experiment without opening benchmark artifacts."""
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    audit, shares, folds, predictions, exclusions = [], [], [], [], []
    for site in CONFIG["sites"]:
        frame = load_site(site)
        audit.append({"site": site, "rows": len(frame), "non_numeric": frame.attrs["non_numeric"],
                      **{f"{col}_{check}": int(fn(frame[col]).sum()) for col in ["grid_kwh", "generator_kwh"]
                         for check, fn in [("nan", pd.isna), ("negative", lambda s: s < 0)]}})
        for period, subset in [("annual", frame)] + [(f"2018-{m:02d}", frame.loc[frame.index.month == m]) for m in range(1, 13)]:
            shares.append({"site": site, "period": period, "rows": len(subset), "observed": subset.outage.count(),
                           "missing": subset.outage.isna().sum(), "outage_hours": subset.outage.sum(), "outage_share": subset.outage.mean()})
        for horizon in CONFIG["horizons_h"]:
            x = features(frame, horizon)
            y = frame.outage.shift(-horizon)
            valid = x.notna().all(axis=1) & y.notna()
            exclusions.append({"site": site, "horizon_h": horizon, "features": x.shape[1], "raw_rows": len(x),
                               "feature_missing": int(x.isna().any(axis=1).sum()), "target_missing": int(y.isna().sum()),
                               "excluded": int((~valid).sum()), "retained": int(valid.sum())})
            x, y = x.loc[valid], y.loc[valid]
            for month in CONFIG["test_months"]:
                train, test = split_masks(x.index, horizon, month)
                boundary = pd.Timestamp(2018, month, 1)
                assert (x.index[train] + pd.Timedelta(hours=horizon) < boundary).all()
                folds.append({"site": site, "horizon_h": horizon, "month": month, "train_n": int(train.sum()), "test_n": int(test.sum()),
                              "train_last_origin": x.index[train].max(), "train_last_target": x.index[train].max() + pd.Timedelta(hours=horizon),
                              "test_first_origin": x.index[test].min(), "test_last_origin": x.index[test].max()})
                probabilities = {"always_0": np.zeros(test.sum()), "persistence": x.loc[test, "outage_now"].to_numpy(),
                                 "same_hour": x.loc[test, "same_hour"].to_numpy()}
                for name, model in [("LR", make_pipeline(StandardScaler(), LogisticRegression(**CONFIG["lr"]))),
                                    ("RF", RandomForestClassifier(**CONFIG["rf"]))]:
                    with threadpool_limits(limits=1):
                        model.fit(x.loc[train], y.loc[train])
                        probabilities[name] = model.predict_proba(x.loc[test])[:, 1]
                predictions.append(pd.DataFrame({"site": site, "horizon_h": horizon, "month": month,
                                                 "origin": x.index[test], "target_time": x.index[test] + pd.Timedelta(hours=horizon),
                                                 "truth": y.loc[test].to_numpy(), **probabilities}))
                print(f"Finished {site} h={horizon} month={month}", flush=True)
    pooled = pd.concat(predictions, ignore_index=True)
    scores = []
    for (site, horizon), group in pooled.groupby(["site", "horizon_h"]):
        for method in ["always_0", "persistence", "same_hour", "LR", "RF"]:
            scores.append({"site": site, "horizon_h": horizon, "method": method, "n": len(group), **metrics(group.truth.to_numpy(), group[method].to_numpy())})
    tables = {"data_audit": pd.DataFrame(audit), "outage_shares": pd.DataFrame(shares), "folds": pd.DataFrame(folds),
              "exclusions": pd.DataFrame(exclusions), "predictions": pooled, "independent_metrics": pd.DataFrame(scores)}
    for name, table in tables.items():
        table.to_csv(OUT / f"{name}.csv", index=False)
    metadata = {"config": CONFIG, "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                "sklearn": sklearn.__version__, "openpyxl": openpyxl.__version__, "elapsed_seconds": time.perf_counter() - start,
                "threads": 1, "independent_seed_runs": 1, "statistical_test": "none; numerical tolerance checks only",
                "source_sha256": digest(Path(__file__)), "config_sha256": digest(HERE / "config.json"),
                "input_sha256": {site: digest(raw_path(site)) for site in CONFIG["sites"]},
                "output_sha256": {name: digest(OUT / f"{name}.csv") for name in tables}}
    (OUT / "freeze.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["independent"])
    args = parser.parse_args()
    independent()
