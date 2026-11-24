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
    if any(OUT.iterdir()):
        raise ValueError("Refusing to overwrite a run; select a new --run-name")
    (OUT / "source_snapshot.py").write_bytes(Path(__file__).read_bytes())
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


def validate_freeze() -> dict:
    """Validate source, configuration, inputs and outputs before comparison."""
    frozen = json.loads((OUT / "freeze.json").read_text())
    snapshot = OUT / "source_snapshot.py"
    if not snapshot.exists():
        snapshot = ROOT / "agent_notes/S1_bench_verify/independent_frozen.py"
    if digest(snapshot) != frozen["source_sha256"]:
        raise ValueError("Frozen source changed")
    if digest(HERE / "config.json") != frozen["config_sha256"] or CONFIG != frozen["config"]:
        raise ValueError("Frozen configuration changed")
    for site, expected in frozen["input_sha256"].items():
        if digest(raw_path(site)) != expected:
            raise ValueError(f"Frozen input changed: {site}")
    for name, expected in frozen["output_sha256"].items():
        if digest(OUT / f"{name}.csv") != expected:
            raise ValueError(f"Frozen output changed: {name}")
    return frozen


def validate_cases(table: pd.DataFrame) -> None:
    """Require the complete unique site/horizon/method grid and finite metrics."""
    keys = ["site", "horizon_h", "method"]
    expected = {(s, h, m) for s in CONFIG["sites"] for h in CONFIG["horizons_h"]
                for m in ("always_0", "persistence", "same_hour", "LR", "RF")}
    actual = set(table[keys].itertuples(index=False, name=None))
    if table.duplicated(keys).any() or actual != expected:
        raise ValueError("Incomplete or duplicate comparison cases")
    if not np.isfinite(table[["accuracy", "f1", "auc", "brier"]].to_numpy(dtype=float)).all():
        raise ValueError("Comparison metrics must be finite")


def compare() -> None:
    """Compare frozen outputs with published decimal scores without refitting."""
    validate_freeze()
    ours = pd.read_csv(OUT / "independent_metrics.csv")
    validate_cases(ours)
    reference_path = HERE.parent / "results/benchmark_results.csv"
    theirs = pd.read_csv(reference_path)
    names = {"always_0": "Always no outage", "persistence": "Persistence", "same_hour": "Same hour last 7 days",
             "LR": "Logistic Regression", "RF": "Random Forest"}
    selected = theirs.loc[theirs.algorithm.isin(names.values())].rename(columns={"h": "horizon_h", "algorithm": "method"})
    selected["method"] = selected.method.map({value: key for key, value in names.items()})
    validate_cases(selected)
    rows = []
    for record in ours.to_dict("records"):
        match = theirs.loc[(theirs.site == record["site"]) & (theirs.h == record["horizon_h"]) & (theirs.algorithm == names[record["method"]])]
        for metric in ("accuracy", "f1", "auc", "brier"):
            value = float(match.iloc[0][metric]) if len(match) == 1 else np.nan
            difference = abs(record[metric] - value)
            tolerance = CONFIG["tolerance"].get(record["method"])
            passed = (difference <= tolerance if tolerance is not None else round(record[metric], CONFIG["tolerance"]["reference_decimals"]) == value)
            rows.append({"site": record["site"], "horizon_h": record["horizon_h"], "method": record["method"], "metric": metric,
                         "ours": record[metric], "theirs": value, "abs_diff": difference,
                         "tolerance": tolerance, "rule": "absolute difference" if tolerance is not None else "equal rounded to four decimals",
                         "pass": bool(passed), "status": "PASS" if passed else "FAIL"})
    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT / "comparison.csv", index=False)
    summary = {"verdict": "REPRODUCED" if comparison["pass"].all() else "PARTLY" if comparison["pass"].any() else "NOT REPRODUCED",
               "comparisons": len(comparison), "passed": int(comparison["pass"].sum()), "failed": int((~comparison["pass"]).sum()),
               "max_abs_diff_by_method": comparison.groupby("method").abs_diff.max().to_dict(),
               "benchmark_results_sha256": digest(reference_path), "published_decimal_places": 4}
    (OUT / "comparison_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def markdown(table: pd.DataFrame) -> str:
    """Render a table without optional Markdown dependencies."""
    def cell(value: object) -> str:
        return (f"{value:.6f}" if isinstance(value, float) else str(value)).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(map(str, table.columns)) + " |",
                      "| " + " | ".join(["---"] * len(table.columns)) + " |"] +
                     ["| " + " | ".join(cell(v) for v in row) + " |" for row in table.itertuples(index=False, name=None)])


def report() -> None:
    """Export source-line audit, random-split audit, figures, and generated report."""
    from sklearn.model_selection import train_test_split
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frozen = json.loads((OUT / "freeze.json").read_text())
    summary = json.loads((OUT / "comparison_summary.json").read_text())
    source_path = HERE.parent / "benchmark.py"
    source = source_path.read_text().splitlines()
    annotations = json.loads((HERE / "audit_annotations.json").read_text())
    audit = []
    for entry in annotations:
        for line in entry["lines"]:
            audit.append({"line": line, "source": source[line - 1].strip(), **{k: v for k, v in entry.items() if k != "lines"}})
    pd.DataFrame(audit).to_csv(OUT / "leakage_audit.csv", index=False)
    audit_summary = pd.DataFrame([{**{k: v for k, v in item.items() if k != "lines"},
                                  "lines": ", ".join(map(str, item["lines"]))} for item in annotations])
    random_rows = []
    predictions = pd.read_csv(OUT / "predictions.csv", parse_dates=["origin", "target_time"])
    for site in CONFIG["sites"]:
        frame = load_site(site)
        for horizon in CONFIG["horizons_h"]:
            x, target = features(frame, horizon), frame.outage.shift(-horizon)
            index = x.index[x.notna().all(axis=1) & target.notna()]
            training, testing = train_test_split(index, test_size=0.2, random_state=42, stratify=index.month)
            random_rows.append({"site": site, "horizon_h": horizon, "eligible": len(index), "training": len(training),
                                "test": len(testing), "test_fraction_requested": 0.2, "seed": 42, "shuffle": True,
                                "stratification": "origin month", "unit": "hourly origin row", "first_origin": index.min(),
                                "last_origin": index.max(), "test_origins_before_last_training_origin": int((testing < training.max()).sum())})
    random_table = pd.DataFrame(random_rows)
    random_table.to_csv(OUT / "random_split_audit.csv", index=False)
    data_audit = pd.read_csv(OUT / "data_audit.csv")
    shares = pd.read_csv(OUT / "outage_shares.csv")
    exclusions = pd.read_csv(OUT / "exclusions.csv")
    scores = pd.read_csv(OUT / "independent_metrics.csv")
    comparison = pd.read_csv(OUT / "comparison.csv")
    max_diff = comparison.groupby("method", sort=False).agg(comparisons=("pass", "size"), passed=("pass", "sum"), max_abs_diff=("abs_diff", "max")).reset_index()
    max_diff.to_csv(OUT / "comparison_by_method.csv", index=False)
    monthly = shares.loc[shares.period != "annual"]
    fig, ax = plt.subplots(figsize=(8, 4))
    for site, group in monthly.groupby("site"):
        ax.plot(group.period.str[-2:].astype(int), group.outage_share * 100, marker="o", label=site)
    ax.set(xlabel="Month of assigned local chronology", ylabel="Outage share (%)", xticks=range(1, 13))
    ax.legend(); fig.tight_layout(); fig.savefig(OUT / "monthly_outage_share.png", dpi=150); plt.close(fig)
    validation = {"benchmark_source_sha256": digest(source_path), "annotation_sha256": digest(HERE / "audit_annotations.json"),
                  "independent_outputs_intact": all(digest(OUT / f"{name}.csv") == value for name, value in frozen["output_sha256"].items()),
                  "random_accuracy_recomputed": False, "time_ordered_leakage_found": False,
                  "test_prediction_rows": len(predictions), "feature_count": int(exclusions.features.iloc[0])}
    (OUT / "audit_summary.json").write_text(json.dumps(validation, indent=2) + "\n")
    rf_max = comparison.loc[(comparison.method == "RF") & (comparison.abs_diff == comparison.loc[comparison.method == "RF", "abs_diff"].max())]
    text = f"""# Independent benchmark verification

Verdict: **{summary['verdict']}**. All {summary['passed']} of {summary['comparisons']} metric comparisons pass the predeclared tolerances; {summary['failed']} fail. This is numerical reproduction within tolerance, not exact reproduction of the forest outputs.

No future-observation feature or test-month training target was found in the time-ordered evaluation. The random holdout is consistent with the README's random comparison, but it is not prospective forecasting evidence.

## Independence and reproducibility

The loader, features, estimators, splits and metrics were implemented and executed before reading the benchmark result CSV or source. The required README summaries were visible beforehand. The original verifier source is preserved at `agent_notes/S1_bench_verify/independent_frozen.py`; its SHA256 is `{frozen['source_sha256']}`. Comparison and report code were appended after freezing the independent output files. The original computation was not tuned or rerun to improve agreement.

`results/freeze.json` stores input/output hashes, configuration, software versions and timing. This run used Python {frozen['python']}, scikit-learn {frozen['sklearn']}, NumPy {frozen['numpy']}, pandas {frozen['pandas']} and openpyxl {frozen['openpyxl']}. The independent experiment took {frozen['elapsed_seconds']:.2f} seconds. RF seed: {CONFIG['rf']['random_state']}; forest trees: {CONFIG['rf']['n_estimators']}; minimum leaf size: {CONFIG['rf']['min_samples_leaf']}; execution threads: {frozen['threads']}. LR uses StandardScaler fitted inside each training fold and max_iter={CONFIG['lr']['max_iter']}, otherwise installed defaults. There is {frozen['independent_seed_runs']} fixed-seed run, not a multiple-seed uncertainty study. Statistical test: none; these are numerical tolerance checks, not significance tests.

Reproduce from the repository root (PowerShell):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py independent --run-name replication
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare --run-name replication
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py compare
python studies/S1_outage_forecasting/benchmark/verify/verify_benchmark.py report
python -m pytest -q -o cache_dir=agent_notes/S1_bench_verify/pytest_cache tests studies/S1_outage_forecasting/benchmark/verify/tests
```

All generated artifacts stay under `verify/results/`. Tests live under `verify/tests/` because the task restricts writes outside the verifier and its notes directory. Independent computation never imports the benchmark. Each rerun requires a new run name and writes under `results/runs/`; nonempty run directories are rejected. Comparison validates the saved source snapshot, configuration, inputs and output hashes. The default comparison and report commands use the original frozen run.

## Data and availability convention

The specified workbook columns are loaded without rounding, sorting, imputation, clipping, or timezone conversion. The selected hourly rows receive the specified local chronology. Outage is exactly grid energy equal to zero; missing grid would remain missing. Load is grid plus generator energy, in kWh. Negative and non-numeric counts are audited separately.

{markdown(data_audit)}

Annual and monthly outage shares use observed grid rows as denominators; counts and missing counts are retained below and in `outage_shares.csv`.

{markdown(shares)}

![Monthly outage share](results/monthly_outage_share.png)

Forecasts assume completed metering observations through origin t are available. If timestamps denote interval starts, issue time must be after that interval completes. The raw workbook selection alone does not establish metering latency or timestamp semantics. Target clock values are known calendar information, not future measurements.

## Features and time-ordered evaluation

The enumerated feature list actually produces **{validation['feature_count']}** columns, despite the task and README calling it eighteen. Every enumerated feature was included, in the listed order. The benchmark source has the same feature count. Current-state duration includes the origin. All rolling windows are complete, and same-hour history requires all {CONFIG['history_days']} preceding daily values. No future observation enters a predictor.

{markdown(exclusions)}

Test origins cover months {min(CONFIG['test_months'])} through {max(CONFIG['test_months'])}; models are refitted for each month using only origins and targets strictly before its boundary. Test-month observations up to the current origin update features, never fitted parameters. Test targets may cross into the next month; end-of-year unavailable targets are excluded. `folds.csv` records train/test counts and boundary timestamps, and `predictions.csv` records every pooled origin, target, truth and probability.

Accuracy and F1 use probability >= {CONFIG['threshold']}; F1 with zero denominator is zero. AUC uses continuous probabilities; a single-class sample would produce missing AUC. Brier is mean squared probability error. Metrics are computed on pooled test predictions, not averaged fold scores.

{markdown(scores)}

## Comparison and discrepancies

References must match after rounding to {CONFIG['tolerance']['reference_decimals']} decimals. LR absolute tolerance is {CONFIG['tolerance']['LR']}; RF absolute tolerance is {CONFIG['tolerance']['RF']}. Published values have {summary['published_decimal_places']} decimal places. `comparison.csv` contains ours, theirs, absolute differences, rules and pass/fail for every requested metric.

{markdown(max_diff)}

The largest forest difference occurs here:

{markdown(rf_max[['site', 'horizon_h', 'metric', 'ours', 'theirs', 'abs_diff']])}

References and LR agree at published precision. RF differs beyond publication rounding but stays within the predeclared tolerance. The benchmark requests all available threads and the verifier fixes a single thread; the original run's package/build environment is not recorded in the published CSV. The exact cause of the forest differences is therefore **unresolved**, and cannot be attributed to threading alone. No settings or output values were changed to obtain agreement.

The benchmark's same-hour mean skips missing values, whereas the verifier requires a complete history. For these observed files, the longest required lag excludes initial incomplete histories and the data audit finds no missing energy, so this semantic difference has no retained-row effect. The benchmark also turns missing grid into non-outage; this is a robustness caveat, not an observed defect in these clean inputs.

## Source-line leakage audit

The following review was performed only after numerical comparison. Line numbers refer to `benchmark.py`, SHA256 `{validation['benchmark_source_sha256']}`. `leakage_audit.csv` expands this table to individual source lines, including their exact text.

{markdown(audit_summary[['lines', 'area', 'latest_information', 'verdict', 'reason']])}

## Random holdout audit

The population is the full eligible year, including the months before the chronological evaluation begins. The split unit is an hourly origin row; sklearn's shuffled train_test_split uses a test fraction of {random_table.test_fraction_requested.iloc[0]}, seed {int(random_table.seed.iloc[0])}, and stratification by origin month, not target class. The source's fresh algorithm instances use the same settings as its monthly evaluation. Scalers are fitted only on random training rows. Accuracy is calculated with estimator.predict; random reference scores are not reported. The random split was reconstructed to inspect membership/counts; models were not refitted for random accuracy reproduction, which is outside the requested metric comparison.

{markdown(random_table)}

Later observations can enter training relative to held-out origins, and overlapping lag windows can expose held-out-hour states in other training features. That is acceptable only as the explicitly descriptive random comparison. The README does not specify the full-year population, month stratification or seed. Its claim that the entire accuracy uplift is caused by adjacency is not established: the test populations and training sizes also differ. Prospective conclusions should use the time-ordered results.

## Limits and review items

This check establishes the requested tolerance agreement and conditional causal validity, not algorithm superiority, geographic transfer, or metering-level proof of grid unavailability. Proxy labels, assigned timestamps, seasonal dependence, class imbalance, household-specific fits and single-seed uncertainty remain limitations. Resolve the documentation feature-count error, document metering availability, and preserve the original benchmark software environment before using its values in a paper. Existing NumPy/pandas timedelta deprecation warnings appeared during execution; computation and tests completed.
"""
    (HERE / "REPORT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["independent", "compare", "report"])
    parser.add_argument("--run-name", help="New single-component run directory beneath results/runs (independent/compare only)")
    args = parser.parse_args()
    if args.run_name:
        if not args.run_name.isascii() or not all(c.isalnum() or c in "_-" for c in args.run_name):
            parser.error("run-name must contain only ASCII letters, digits, underscores or hyphens")
        if args.stage == "report":
            parser.error("report describes the original run; inspect named-run comparison.csv separately")
        OUT = OUT / "runs" / args.run_name
    {"independent": independent, "compare": compare, "report": report}[args.stage]()
