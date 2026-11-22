"""Equal-budget nested temporal tuning; run this file offline to reproduce outputs.

Horizons are hours; probabilities and Brier losses are dimensionless. Configurations
are drawn with replacement, once per algorithm, before any outer predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from benchmark import HORIZONS, SEED, algorithms, features, load, scores
from sklearn.base import clone
from sklearn.metrics import brier_score_loss
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "tuning"
SEARCH_SPACES = {
    "Logistic Regression": {"logisticregression__C": [0.01, 0.1, 1, 10, 100]},
    "Naive Bayes": {"gaussiannb__var_smoothing": [1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5]},
    "k-Nearest Neighbours": {"kneighborsclassifier__n_neighbors": [5, 15, 25, 51],
                             "kneighborsclassifier__weights": ["uniform", "distance"]},
    "Decision Tree": {"max_depth": [3, 5, 8, None], "min_samples_leaf": [5, 20, 50]},
    "Random Forest": {"n_estimators": [100, 300], "max_depth": [8, 16, None],
                      "min_samples_leaf": [1, 5, 20], "max_features": ["sqrt", 0.5, 1.0]},
    "Extra Trees": {"n_estimators": [100, 300], "max_depth": [8, 16, None],
                    "min_samples_leaf": [1, 5, 20], "max_features": ["sqrt", 0.5, 1.0]},
    "Gradient Boosting": {"learning_rate": [0.03, 0.1], "n_estimators": [100, 300],
                          "max_depth": [2, 3, 5], "subsample": [0.8, 1.0]},
    "XGBoost": {"learning_rate": [0.03, 0.05, 0.1], "n_estimators": [100, 300],
                "max_depth": [3, 5, 7], "subsample": [0.8, 1.0]},
    "LightGBM": {"learning_rate": [0.01, 0.03, 0.1], "n_estimators": [100, 300],
                 "num_leaves": [15, 31, 63], "subsample": [0.8, 1.0]},
    "CatBoost": {"learning_rate": [0.03, 0.1], "iterations": [100, 300], "depth": [4, 6, 8]},
    "SVM": {"svc__C": [0.1, 1, 10], "svc__gamma": ["scale", 0.001, 0.01, 0.1]},
    "Neural Network (MLP)": {"mlpclassifier__hidden_layer_sizes": [(32,), (64, 32), (64,)],
                             "mlpclassifier__alpha": [0.0001, 0.001, 0.01]},
}
METRICS = ["accuracy", "precision", "recall", "f1", "auc", "brier"]


def configurations(name: str, k: int = 20, seed: int = SEED) -> list[dict[str, Any]]:
    """Return parameter overrides; empty config zero preserves every default."""
    if k < 1:
        raise ValueError("K must be positive")
    rng = np.random.default_rng(seed)
    return [{}] + [{key: values[int(rng.integers(len(values)))]
                   for key, values in SEARCH_SPACES[name].items()} for _ in range(k - 1)]


def estimator(name: str, config: dict[str, Any], index: int) -> Any:
    """Clone the default, preserving config zero and parallelizing random draws."""
    model = clone(algorithms()[name]).set_params(**config)
    if index:
        parallel = {key: -1 for key in model.get_params() if key.endswith("n_jobs")}
        if name == "CatBoost":
            parallel["thread_count"] = -1
        model.set_params(**parallel)
    return model


def json_params(model: Any) -> dict[str, Any]:
    """Serialize full effective parameters, including pipeline component defaults."""
    return json.loads(json.dumps(model.get_params(deep=True), default=repr, sort_keys=True))


def case_data(site: str, h: int) -> tuple[pd.DataFrame, pd.Series]:
    """Load benchmark-eligible rows for a horizon in hours."""
    data = load(site)
    x, y = features(data, h), data.outage.shift(-h)
    ok = x.notna().all(axis=1) & y.notna()
    return x[ok], y[ok].astype(int)


def split_masks(index: pd.DatetimeIndex, h: int, month: int) -> tuple[np.ndarray, ...]:
    """Return outer train/test and inner train/validation masks; h is in hours."""
    start = pd.Timestamp(year=2018, month=month, day=1)
    validation = start - pd.offsets.MonthBegin(1)
    target = index + pd.Timedelta(hours=h)
    outer = (index < start) & (target < start)
    test = (index >= start) & (index < start + pd.offsets.MonthBegin(1))
    inner = outer & (index < validation) & (target < validation)
    valid = outer & (index >= validation)
    return outer, test, inner, valid


def probabilities(model: Any, x: pd.DataFrame) -> np.ndarray:
    """Return checked outage probabilities in [0, 1]."""
    p = model.predict_proba(x)[:, 1]
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid probabilities")
    return p


def select_config(name: str, configs: list[dict[str, Any]], x: pd.DataFrame,
                  y: pd.Series, inner: np.ndarray, valid: np.ndarray) -> tuple[int, list[float]]:
    """Minimize validation Brier; exact ties choose the first candidate."""
    losses = []
    for i, config in enumerate(configs):
        model = estimator(name, config, i)
        model.fit(x[inner], y[inner])
        losses.append(float(brier_score_loss(y[valid], probabilities(model, x[valid]))))
    if not np.isfinite(losses).all():
        raise ValueError("Nonfinite validation loss")
    return int(np.argmin(losses)), losses


def timing_budget(cases: dict, candidates: dict) -> dict:
    """Time December inner fits; estimate seconds with 25% overhead and 2x refits."""
    rows = []
    for (site, h), (x, y) in cases.items():
        _, _, inner, valid = split_masks(x.index, h, 12)
        for name in candidates:
            for i in (0, 1):
                start = time.perf_counter()
                model = estimator(name, candidates[name][i], i)
                model.fit(x[inner], y[inner])
                probabilities(model, x[valid])
                rows.append({"site": site, "h": h, "algorithm": name, "config_index": i,
                                 "seconds": time.perf_counter() - start})
            print(f"timing {site} h={h} {name}", flush=True)
    timings = pd.DataFrame(rows)
    timings.to_csv(OUT / "timings.csv", index=False)
    slow = timings.groupby(["site", "h", "algorithm"]).seconds.max()
    sanity = sum(slow.loc[("BG", 1, n)] for n in ["Logistic Regression", "Random Forest"])
    estimates = {k: float(1.25 * (9 * (k + 2) * slow.sum() + 9 * 3 * sanity))
                 for k in range(8, 21)}
    feasible = [k for k, seconds in estimates.items() if seconds <= 80 * 60]
    k = max(feasible) if feasible else 8
    decision = {"K": k, "feasible": bool(feasible), "estimated_seconds": estimates,
                    "formula": "1.25 * (9*(K+2)*sum(case/algorithm max timing) + 9*3*sum(BG1 LR/RF max timing))",
                    "overhead": "25%; full-training refit costs twice the late inner fit; sanity includes selection + refit",
                    "timing_seconds": float(timings.seconds.sum())}
    (OUT / "budget.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    return decision


SCHEMA = 1


def digest(value: Any) -> str:
    """Hash canonical JSON without dropping floating point precision."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    """Publish a complete JSON document atomically on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def provenance(x: pd.DataFrame, y: pd.Series, candidates: dict) -> dict:
    """Fingerprint eligible inputs, source, ordered candidates and environment."""
    data_hash = hashlib.sha256(pd.util.hash_pandas_object(x, index=True).values.tobytes()
                               + pd.util.hash_pandas_object(y, index=True).values.tobytes()).hexdigest()
    return {"schema": SCHEMA, "seed": SEED, "input_sha256": data_hash,
                "columns": list(x.columns), "dtypes": [str(d) for d in x.dtypes],
                "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__), HERE / "benchmark.py",
                                         HERE / "results/benchmark_results.csv"]},
                "raw_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [HERE.parents[2] / "data/raw/BG18760_with_analysis.xlsx",
                                      HERE.parents[2] / "data/raw/KR-8760.xlsx"]},
                "python": platform.python_version(), "platform": platform.platform(),
                "versions": {p: version(p) for p in ["numpy", "pandas", "scipy", "scikit-learn",
                                                "xgboost", "lightgbm", "catboost", "joblib", "threadpoolctl"]},
                "candidates": candidates,
                "effective_parameters": {n: [json_params(estimator(n, c, i)) for i, c in enumerate(cs)]
                                      for n, cs in candidates.items()}}


def validate_predictions(frame: pd.DataFrame, names: list[str]) -> None:
    """Reject duplicate keys, missing/shared-row violations and invalid probabilities."""
    if frame.duplicated(["site", "h", "origin_time"]).any():
        raise ValueError("Duplicate prediction key")
    values = frame[names].to_numpy()
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Invalid or missing prediction")


def read_checkpoint(path: Path, identity: dict, manifest: dict, rows: dict,
                    name: str) -> dict:
    """Reject corrupt, incomplete or incompatible units before reusing predictions."""
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        unit = envelope["payload"]
        if envelope["sha256"] != digest(unit):
            raise ValueError("checksum")
        # JSON normalizes tuple-valued estimator parameters to lists.
        if (unit["status"] != "complete" or unit["identity"] != identity
                or digest(unit["manifest"]) != digest(manifest) or unit["rows"] != rows):
            raise ValueError("identity, inputs, protocol or completion mismatch")
        losses = np.asarray(unit["losses"], dtype=float)
        chosen = unit["chosen"]
        if (len(losses) != len(manifest["candidates"][name]) or not np.isfinite(losses).all()
                or chosen != int(np.argmin(losses))):
            raise ValueError("invalid selection")
        if digest(unit["parameters"]) != digest(manifest["effective_parameters"][name][chosen]):
            raise ValueError("invalid parameters")
        probabilities_ = np.asarray(unit["probabilities"], dtype=float)
        if (probabilities_.shape != (len(rows["y"]),) or not np.isfinite(probabilities_).all()
                or ((probabilities_ < 0) | (probabilities_ > 1)).any()
                or not np.isfinite(unit["elapsed_seconds"]) or unit["elapsed_seconds"] < 0
                or not isinstance(unit["warnings"], list)):
            raise ValueError("invalid predictions or metadata")
        return unit
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ValueError(f"Invalid checkpoint {path}: {error}") from error


def evaluate(site: str, h: int, x: pd.DataFrame, y: pd.Series, candidates: dict,
             out: Path = OUT, months: tuple[int, ...] = tuple(range(4, 13)),
             read_only: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Resume atomic (site, horizon hours, month, algorithm) units and pool predictions."""
    out = Path(out)
    manifest = provenance(x, y, candidates)
    manifest_path = out / "checkpoints" / f"{site}_{h}_manifest.json"
    if manifest_path.exists():
        if digest(json.loads(manifest_path.read_text(encoding="utf-8"))) != digest(manifest):
            raise ValueError("Incompatible checkpoint manifest; use a separate --out directory")
    elif read_only:
        raise ValueError("Missing checkpoint manifest")
    else:
        atomic_json(manifest_path, manifest)
    expected_files = {f"{site}_{h}_{m}_{digest(n)[:16]}.json"
                      for m in range(4, 13) for n in candidates}
    actual_files = {p.name for p in (out / "checkpoints").glob(f"{site}_{h}_*.json")}
    if actual_files - expected_files - {manifest_path.name}:
        raise ValueError("Unexpected or duplicate checkpoint unit")
    predictions, selected = [], []
    seconds = dict.fromkeys(candidates, 0.0)
    for month in months:
        outer, test, inner, valid = split_masks(x.index, h, month)
        if not all(mask.any() for mask in (outer, test, inner, valid)):
            raise ValueError("Empty temporal split")
        rows = {"origin_time": x.index[test].astype(str).tolist(),
                    "target_time": (x.index[test] + pd.Timedelta(hours=h)).astype(str).tolist(),
                    "y": y[test].tolist()}
        fold = pd.DataFrame(dict(site=site, h=h, month=month, **rows))
        for name, configs in candidates.items():
            identity = {"site": site, "h": h, "test_month": month, "algorithm": name}
            path = out / "checkpoints" / f"{site}_{h}_{month}_{digest(name)[:16]}.json"
            if not path.exists():
                if read_only:
                    raise ValueError(f"Missing checkpoint {identity}")
                start = time.perf_counter()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    chosen, losses = select_config(name, configs, x, y, inner, valid)
                    model = estimator(name, configs[chosen], chosen)
                    model.fit(x[outer], y[outer])
                    p = probabilities(model, x[test])
                unit = {"status": "complete", "identity": identity, "manifest": manifest, "rows": rows,
                            "chosen": chosen, "losses": losses, "parameters": json_params(model),
                            "probabilities": p.tolist(), "elapsed_seconds": time.perf_counter() - start,
                            "warnings": [str(w.message) for w in caught]}
                atomic_json(path, {"payload": unit, "sha256": digest(unit)})
                print(f"completed {site} h={h} month={month} {name}", flush=True)
            unit = read_checkpoint(path, identity, manifest, rows, name)
            fold[name] = unit["probabilities"]
            seconds[name] += unit["elapsed_seconds"]
            selected.append(dict(**identity, config_index=unit["chosen"],
                                 config_json=json.dumps(unit["parameters"], sort_keys=True),
                                 inner_brier=unit["losses"][unit["chosen"]],
                                 inner_briers_json=json.dumps(unit["losses"])))
        predictions.append(fold)
    prediction = pd.concat(predictions, ignore_index=True)
    prediction["origin_time"] = pd.to_datetime(prediction.origin_time)
    prediction["target_time"] = pd.to_datetime(prediction.target_time)
    validate_predictions(prediction, list(candidates))
    results = []
    for name, configs in candidates.items():
        if prediction.y.nunique() < 2:
            raise ValueError("Single-class pooled target: AUC is undefined; no complete summary")
        results.append(dict(site=site, h=h, algorithm=name, K=len(configs), kind="algorithm",
                            **scores(prediction.y.values, prediction[name].values), fit_seconds=seconds[name]))
    return pd.DataFrame(results), pd.DataFrame(selected), prediction


def evaluate_worker(args: tuple) -> None:
    """Run one case with fixed native limits; estimator parameters remain unchanged."""
    site, h, x, y, candidates, out = args
    work = out / f"worker_{site}_{h}"
    work.mkdir(parents=True, exist_ok=True)
    previous = Path.cwd()
    os.chdir(work)  # CatBoost default diagnostic files must stay in this output tree.
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"
    from joblib import parallel_backend
    try:
        with threadpool_limits(limits=1), parallel_backend("threading", n_jobs=1):
            evaluate(site, h, x, y, candidates, out)
    finally:
        os.chdir(previous)


def table(frame: pd.DataFrame) -> str:
    """Render Markdown without optional dependencies; metrics are dimensionless."""
    def format_value(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.9g}" if 0 < abs(value) < 1e-5 else f"{value:.6f}"
        return str(value)
    return "| " + " | ".join(frame.columns) + " |\n|" + "---|" * len(frame.columns) + "\n" + "\n".join(
        "| " + " | ".join(format_value(v) for v in row) + " |"
        for row in frame.itertuples(index=False, name=None))


def reports(results: pd.DataFrame, selected: pd.DataFrame, sanity: pd.DataFrame,
            budget: dict, candidates: dict) -> None:
    """Generate the summary, README section and figure from computed results."""
    k = budget["K"]
    expected = {(s, h, n) for s in ("BG", "KR") for h in HORIZONS for n in SEARCH_SPACES}
    complete_design = set(results[["site", "h", "algorithm"]].itertuples(index=False, name=None)) == expected
    lines = ["# Step 2 tuning", f"K={k} for every algorithm, seed={SEED}; draws with replacement.",
             f"Estimated runtime: {budget['estimated_seconds'][k] / 60:.2f} minutes; feasible: {budget['feasible']}.",
             budget["formula"], budget["overhead"],
             "Config 0 is unchanged. Other configs use n_jobs=-1 where supported (CatBoost thread_count=-1).",
             "Cases execute in separate processes as requested by --n-jobs. Native BLAS/OpenMP limits and LOKY_MAX_CPU_COUNT are one; estimator parameters are unchanged. Explicit estimator parallelism and CatBoost may manage additional threads. The timing estimate is sequential, not measured parallel wall time.",
             "Default CSV metrics have four-decimal precision. Differences use those stored values.",
             "Small differences cannot establish improvements beyond baseline rounding and reproducibility uncertainty. The literal LR reproduction gate remains unresolved unless the lead explicitly changes the criterion or supplies a verified full-precision baseline.",
             "Complete benchmark design." if complete_design else "SUBSET ONLY: rankings apply only to the evaluated algorithms and cases; no full-benchmark dominance conclusion is supported.",
             "No significance tests were run. This is one seed, not multiple independent runs; temporal folds are dependent.",
             "Step 1 inference does not transfer to tuned models. MLP early stopping and SVM calibration retain benchmark internal splitting.",
             "Limitations: metering-proxy labels, completed-origin-hour availability, one year per site, seasonal drift, dependent losses, overlapping training, class imbalance, unequal search-space coverage and prior inspection of this test year.",
             "## Duplicate draws"]
    for name, configs in candidates.items():
        unique = len({json.dumps(c, sort_keys=True) for c in configs[1:]})
        effective_unique = len({json.dumps(json_params(estimator(name, c, i)), sort_keys=True)
                                for i, c in enumerate(configs)})
        lines.append(f"- {name}: {k-1-unique} repeated random draws; {unique} unique random overrides; "
                     f"{effective_unique} unique effective configurations including config 0 ({k-effective_unique} repeats).")
    readme = ["## Step 2 - tuning", "Run `python studies/S1_outage_forecasting/benchmark/tuning.py` from the repository root.",
              f"Equal budget K={k}, including unchanged config 0; seed 42. Last training month validates each candidate; April validates on March. Origins and targets are purged at both training boundaries. Selection uses inner Brier only.",
              f"Timing estimate: {budget['estimated_seconds'][k] / 60:.2f} minutes. Details, full rankings, warnings, predictions and sanity checks: `results/tuning/`."]
    pair_persists = True
    changed_top_two = []
    for (site, h), group in results.groupby(["site", "h"]):
        group = group.sort_values("brier")
        if group.brier.duplicated(keep=False).any():
            lines.append(f"Exact Brier ties for {site} h={h}: "
                         + ", ".join(group.loc[group.brier.duplicated(keep=False), "algorithm"]))
        tuned_top = top_two_members(group, "brier")
        default_top = top_two_members(group, "default_brier")
        if len(tuned_top) > 2 or len(default_top) > 2:
            lines.append("Second-place boundary tie: all tied members are included; no unique leading pair.")
        pair_persists &= tuned_top == {"Random Forest", "Extra Trees"}
        if tuned_top != default_top:
            changed_top_two.append(f"{site} h={h}")
        lines += [f"## {site}, h={h} hours", table(group[["algorithm", "brier", "default_brier", "delta_brier", "rank_by_brier", "default_rank_by_brier"]]),
                  "Changed rank: " + ", ".join(group.loc[group.rank_by_brier != group.default_rank_by_brier, "algorithm"])]
        counts = selected[(selected.site == site) & (selected.h == h)].groupby("algorithm").config_index.agg(lambda s: f"{(s == 0).sum()}/{len(s)}")
        lines += ["Config 0 selections:", table(counts.rename("config_0 / folds").reset_index())]
        readme += [f"### {site}, h={h} hours (top six by tuned Brier)", table(group.head(6)[["algorithm", "default_brier", "brier", "default_accuracy", "accuracy"]])]
    verdict = ("Top-two membership by Brier changes versus the stored defaults in: " + ", ".join(changed_top_two) + "."
               if changed_top_two else "Top-two membership by Brier is unchanged versus the stored defaults in every case.")
    if complete_design:
        verdict += (" Random Forest and Extra Trees form the unique leading pair in every tuned case." if pair_persists else
                    " Random Forest and Extra Trees do not form a unique leading pair in every tuned case.")
    else:
        verdict = "Subset only. " + verdict + " No full-benchmark dominance claim is made."
    readme += [verdict + " These rankings are descriptive; significance on tuned predictions is a later step.",
               "The literal LR 1e-9 CSV check and four-decimal comparison are reported separately in tuning_summary.md; the stored baseline has limited precision. Only one tuning seed was run."]
    execution_path = OUT / "execution.json"
    if execution_path.exists():
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        actual = f"Measured invocation runtime (including reuse and assembly, excluding historical timing probe): {execution['elapsed_seconds'] / 60:.2f} minutes (excludes initial timing and interrupted attempts)."
        lines.append(actual)
        readme.append(actual)
    lines += [verdict, "## K=1 sanity: BG h=1", table(sanity),
              "LR literal tolerance is 1e-9 for each metric; RF tolerance is 0.005 for Brier. Raw differences are reported without causal attribution. Four-decimal equality is a separate diagnostic."]
    (OUT / "tuning_summary.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    if complete_design:
        path = HERE / "README.md"
        original = path.read_text(encoding="utf-8").split("\n## Step 2 - tuning")[0]
        path.write_text(original.rstrip() + "\n\n" + "\n\n".join(readme) + "\n", encoding="utf-8")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 4, figsize=(18, 6))
    for ax, ((site, h), group) in zip(axes, results.groupby(["site", "h"])):
        group = group.sort_values("brier")
        ax.plot(group.default_brier, group.algorithm, "o", label="Default")
        ax.plot(group.brier, group.algorithm, "x", label="Tuned")
        ax.invert_yaxis()
        ax.set_title(f"{site}, {h} h")
        ax.set_xlabel("Brier score")
        ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "tuned_brier.png", dpi=160)
    plt.close(fig)


def top_two_members(group: pd.DataFrame, metric: str) -> set[str]:
    """Include all exact ties at the second order statistic of a unitless loss."""
    cutoff = group[metric].nsmallest(min(2, len(group))).max()
    return set(group.loc[group[metric] <= cutoff, "algorithm"])


def validated_sanity(baseline: pd.DataFrame) -> pd.DataFrame:
    """Rebuild sanity evidence only from checkpoints matching current provenance."""
    path = HERE / "results/tuning/sanity"
    candidates = {n: configurations(n, 1) for n in ("Logistic Regression", "Random Forest")}
    try:
        x, y = case_data("BG", 1)
        results, _, _ = evaluate("BG", 1, x, y, candidates, path, read_only=True)
    except (ValueError, OSError) as exc:
        return pd.DataFrame({"status": [f"Unavailable: sanity checkpoints not validated: {exc}"]})
    return sanity_comparison(results, baseline)


def frozen_budget() -> dict:
    """Recompute the frozen budget from the historical timing probe (seconds)."""
    timings = pd.read_csv(HERE / "results/tuning/timing_probe_20261116.csv")
    slow = timings.groupby(["site", "h", "algorithm"]).seconds.max()
    sanity = sum(slow.loc[("BG", 1, n)] for n in ["Logistic Regression", "Random Forest"])
    estimates = {k: float(1.25 * (9 * (k + 2) * slow.sum() + 27 * sanity)) for k in range(1, 21)}
    feasible = [k for k in range(8, 21) if estimates[k] <= 80 * 60]
    return {"K": max(feasible) if feasible else 8, "feasible": bool(feasible), "estimated_seconds": estimates,
                "formula": "1.25 * (9*(K+2)*sum(max probe seconds per case/model) + 27*sum(BG1 LR/RF max seconds))",
                "overhead": "25% overhead; outer refit allowance twice late inner fit; includes sanity cost"}


def sanity_comparison(results: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Compare full precision K=1 metrics with the four-decimal stored baseline."""
    rows = []
    for _, row in results.iterrows():
        default = baseline[(baseline.site == "BG") & (baseline.h == 1)
                           & (baseline.algorithm == row.algorithm)].iloc[0]
        for metric in METRICS:
            diff = row[metric] - default[metric]
            tolerance = 1e-9 if row.algorithm == "Logistic Regression" else (0.005 if metric == "brier" else None)
            rows.append({"algorithm": row.algorithm, "metric": metric, "recomputed": row[metric],
                             "stored": default[metric], "difference": diff, "absolute_difference": abs(diff),
                             "tolerance": tolerance,
                             "literal_pass": abs(diff) <= tolerance if tolerance is not None else "not prescribed",
                             "equal_after_4dp": round(row[metric], 4) == default[metric]})
    return pd.DataFrame(rows)


def main() -> None:
    """Run only requested cases; reuse checked units, then assemble complete outputs."""
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="+", choices=["BG", "KR"], default=["BG", "KR"])
    parser.add_argument("--horizons", nargs="+", type=int, choices=HORIZONS, default=HORIZONS)
    parser.add_argument("--K", type=int, default=8)
    parser.add_argument("--n-jobs", type=int, default=1, help="Number of concurrent case processes")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--sanity", action="store_true", help="Only K=1 BG h=1 LR/RF, all nine months")
    args = parser.parse_args()
    if args.n_jobs < 1 or not 1 <= args.K <= 20:
        parser.error("--n-jobs must be positive and --K must be between 1 and 20")
    if len(set(args.sites)) != len(args.sites) or len(set(args.horizons)) != len(args.horizons):
        parser.error("Duplicate sites or horizons")
    if args.sanity and (args.K != 1 or args.sites != ["BG"] or args.horizons != [1]):
        parser.error("--sanity requires --K 1 --sites BG --horizons 1")
    OUT = args.out.resolve()
    root = HERE.parents[2].resolve()
    if not OUT.is_relative_to(root) or any(OUT.is_relative_to(root / p) for p in ["data", "legacy"]):
        parser.error("--out must be inside the repository and outside data/ and legacy/")
    OUT.mkdir(parents=True, exist_ok=True)
    names = ["Logistic Regression", "Random Forest"] if args.sanity else list(algorithms())
    candidates = {n: configurations(n, args.K) for n in names}
    cases = {(site, h): case_data(site, h) for site in args.sites for h in args.horizons}
    request = {"schema": SCHEMA, "sites": args.sites, "horizons": args.horizons, "K": args.K,
                   "algorithms": names, "months": list(range(4, 13))}
    request_path = OUT / "request.json"
    if request_path.exists() and json.loads(request_path.read_text()) != request:
        raise ValueError("Incompatible output request; use a separate --out directory")
    atomic_json(request_path, request)
    started = time.perf_counter()
    workers = min(args.n_jobs, len(cases))
    jobs = [(s, h, x, y, candidates, OUT) for (s, h), (x, y) in cases.items()]
    if workers == 1:
        for job in jobs:
            evaluate_worker(job)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(evaluate_worker, jobs))
    # Read every required unit again. Missing/corrupt units prevent final publication.
    parts = [evaluate(s, h, x, y, candidates, OUT, read_only=True) for (s, h), (x, y) in cases.items()]
    results, selected, predictions = [pd.concat([p[i] for p in parts], ignore_index=True) for i in range(3)]
    validate_predictions(predictions, names)
    baseline = pd.read_csv(HERE / "results/benchmark_results.csv")
    results["rank_by_brier"] = results.groupby(["site", "h"]).brier.rank(method="average")
    keys = ["site", "h", "algorithm"]
    results = results.merge(baseline.rename(columns={c: "default_" + c for c in baseline if c not in keys}),
                            on=keys, validate="one_to_one")
    for metric in METRICS:
        results["delta_" + metric] = results[metric] - results["default_" + metric]
    results.to_csv(OUT / "tuned_results.csv", index=False)
    selected.to_csv(OUT / "selected_configs.csv", index=False)
    predictions.to_csv(OUT / "tuned_predictions.csv.gz", index=False)
    baseline[baseline.kind == "reference"].to_csv(OUT / "default_references.csv", index=False)
    sanity = validated_sanity(baseline) if not args.sanity else pd.DataFrame()
    if args.sanity:
        sanity = sanity_comparison(results, baseline)
        sanity.to_csv(OUT / "sanity.csv", index=False)
        note = ("# K=1 sanity: BG, h=1, LR and RF\n\n" + table(sanity)
                + "\n\nLR literal tolerance: 1e-9; RF Brier tolerance: 0.005. "
                "Four-decimal equality is a separate check; rounding does not waive literal failures. "
                "No cause is assigned to RF differences. Seed 42; nine dependent monthly folds, "
                "one realization; no inferential test or full tuning grid was run.\n")
        (root / "agent_notes/S1_bench_step2/SANITY.md").write_text(note, encoding="utf-8")
    atomic_json(OUT / "execution.json", {"workers": workers, "requested_workers": args.n_jobs,
                "blas_threads_per_worker": 1, "openmp_threads_per_worker": 1, "loky_max_cpu_count": 1,
                "estimator_parameters_unchanged": True, "elapsed_seconds": time.perf_counter() - started})
    budget = frozen_budget()
    budget["K"] = args.K
    atomic_json(OUT / "runtime_estimate.json", budget)
    reports(results, selected, sanity, budget, candidates)


if __name__ == "__main__":
    main()
