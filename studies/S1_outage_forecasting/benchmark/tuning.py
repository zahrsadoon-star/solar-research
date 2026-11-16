"""Equal-budget nested temporal tuning; run this file offline to reproduce outputs.

Horizons are hours; probabilities and Brier losses are dimensionless. Configurations
are drawn with replacement, once per algorithm, before any outer predictions.
"""
from __future__ import annotations

import json
import os
import sys
import platform
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import brier_score_loss
from threadpoolctl import threadpool_limits

from benchmark import HORIZONS, SEED, algorithms, features, load, scores

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
                rows.append(dict(site=site, h=h, algorithm=name, config_index=i,
                                 seconds=time.perf_counter() - start))
            print(f"timing {site} h={h} {name}", flush=True)
    timings = pd.DataFrame(rows)
    timings.to_csv(OUT / "timings.csv", index=False)
    slow = timings.groupby(["site", "h", "algorithm"]).seconds.max()
    sanity = sum(slow.loc[("BG", 1, n)] for n in ["Logistic Regression", "Random Forest"])
    estimates = {k: float(1.25 * (9 * (k + 2) * slow.sum() + 9 * 3 * sanity))
                 for k in range(8, 21)}
    feasible = [k for k, seconds in estimates.items() if seconds <= 80 * 60]
    k = max(feasible) if feasible else 8
    decision = dict(K=k, feasible=bool(feasible), estimated_seconds=estimates,
                    formula="1.25 * (9*(K+2)*sum(case/algorithm max timing) + 9*3*sum(BG1 LR/RF max timing))",
                    overhead="25%; full-training refit costs twice the late inner fit; sanity includes selection + refit",
                    timing_seconds=float(timings.seconds.sum()))
    (OUT / "budget.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    return decision


def evaluate(site: str, h: int, x: pd.DataFrame, y: pd.Series, candidates: dict,
             prefix: str = "") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate all nine outer folds; persist fold checkpoints inside tuning outputs."""
    predictions, selected = [], []
    seconds = dict.fromkeys(candidates, 0.0)
    for month in range(4, 13):
        outer, test, inner, valid = split_masks(x.index, h, month)
        fold = pd.DataFrame(dict(site=site, h=h, origin_time=x.index[test],
                                 target_time=x.index[test] + pd.Timedelta(hours=h),
                                 month=month, y=y[test].values))
        for name, configs in candidates.items():
            start = time.perf_counter()
            chosen, losses = select_config(name, configs, x, y, inner, valid)
            model = estimator(name, configs[chosen], chosen)
            model.fit(x[outer], y[outer])
            fold[name] = probabilities(model, x[test])
            seconds[name] += time.perf_counter() - start
            print(f"{prefix or 'tuning'} {site} h={h} month={month} {name} complete", flush=True)
            selected.append(dict(site=site, h=h, test_month=month, algorithm=name,
                                 config_index=chosen, config_json=json.dumps(json_params(model), sort_keys=True),
                                 inner_brier=losses[chosen], inner_briers_json=json.dumps(losses)))
        predictions.append(fold)
        print(f"{prefix or 'tuning'} {site} h={h} month={month} complete", flush=True)
        pd.concat(predictions).to_csv(OUT / f"{prefix}{site}_{h}_predictions.csv.gz", index=False)
        pd.DataFrame(selected).to_csv(OUT / f"{prefix}{site}_{h}_configs.csv", index=False)
    prediction = pd.concat(predictions, ignore_index=True)
    validate_predictions(prediction, list(candidates))
    rows = [dict(site=site, h=h, algorithm=name, K=len(configs), kind="algorithm",
                 **scores(prediction.y.values, prediction[name].values), fit_seconds=seconds[name])
            for name, configs in candidates.items()]
    return pd.DataFrame(rows), pd.DataFrame(selected), prediction


def validate_predictions(frame: pd.DataFrame, names: list[str]) -> None:
    """Reject duplicate keys, missing/shared-row violations and invalid probabilities."""
    if frame.duplicated(["site", "h", "origin_time"]).any():
        raise ValueError("Duplicate prediction key")
    values = frame[names].to_numpy()
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Invalid or missing prediction")


def evaluate_worker(args: tuple) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Isolate each case's diagnostics; limit BLAS oversubscription, not estimator jobs."""
    site, h, x, y, candidates = args
    work = OUT / f"worker_{site}_{h}"
    work.mkdir(exist_ok=True)
    os.chdir(work)
    # Equal worker CPU budgets avoid four all-core estimators oversubscribing.
    # Estimator n_jobs=-1 remains unchanged; joblib/LightGBM see this CPU limit.
    cpu_budget = max(1, (os.cpu_count() or 1) // 4)
    os.environ["LOKY_MAX_CPU_COUNT"] = str(cpu_budget)
    with (work / "warnings.log").open("w", encoding="utf-8") as log:
        def emit(message: Any, category: type, filename: str, lineno: int,
                 file: Any = None, line: Any = None) -> None:
            log.write(warnings.formatwarning(message, category, filename, lineno))
            log.flush()
        warnings.showwarning = emit
        warnings.simplefilter("always")
        from joblib import parallel_backend
        with threadpool_limits(limits=1, user_api="blas"), threadpool_limits(
                limits=cpu_budget, user_api="openmp"), parallel_backend("threading"):
            return evaluate(site, h, x, y, candidates)


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
    lines = ["# Step 2 tuning", f"K={k} for every algorithm, seed={SEED}; draws with replacement.",
             f"Estimated runtime: {budget['estimated_seconds'][k] / 60:.2f} minutes; feasible: {budget['feasible']}.",
             budget["formula"], budget["overhead"],
             "Config 0 is unchanged. Other configs use n_jobs=-1 where supported (CatBoost thread_count=-1).",
             "Four independent cases execute in separate processes with BLAS threads limited to one per process. Each worker exposes max(1, cpu_count // 4) CPUs to joblib/LightGBM and OpenMP, using joblib's threading backend; estimator n_jobs settings are unchanged. CatBoost retains its own thread management. The timing estimate is sequential time, not a measured parallel runtime.",
             "Default CSV metrics have four-decimal precision. Differences use those stored values.",
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
        pair_persists &= set(group.head(2).algorithm) == {"Random Forest", "Extra Trees"}
        if set(group.head(2).algorithm) != set(group.sort_values("default_rank_by_brier").head(2).algorithm):
            changed_top_two.append(f"{site} h={h}")
        lines += [f"## {site}, h={h} hours", table(group[["algorithm", "brier", "default_brier", "delta_brier", "rank_by_brier", "default_rank_by_brier"]]),
                  "Changed rank: " + ", ".join(group.loc[group.rank_by_brier != group.default_rank_by_brier, "algorithm"])]
        counts = selected[(selected.site == site) & (selected.h == h)].groupby("algorithm").config_index.agg(lambda s: f"{(s == 0).sum()}/{len(s)}")
        lines += ["Config 0 selections:", table(counts.rename("config_0 / folds").reset_index())]
        readme += [f"### {site}, h={h} hours (top six by tuned Brier)", table(group.head(6)[["algorithm", "default_brier", "brier", "default_accuracy", "accuracy"]])]
    verdict = ("Top-two membership by Brier changes versus the stored defaults in: " + ", ".join(changed_top_two) + "."
               if changed_top_two else "Top-two membership by Brier is unchanged versus the stored defaults in every case.")
    verdict += (" Random Forest and Extra Trees occupy the first two ranks in every tuned case." if pair_persists else
                " Random Forest and Extra Trees do not occupy both first two ranks in every tuned case.")
    readme += [verdict + " These rankings are descriptive; significance on tuned predictions is a later step.",
               "The literal LR 1e-9 CSV check and four-decimal comparison are reported separately in tuning_summary.md; the stored baseline has limited precision. Only one tuning seed was run."]
    execution_path = OUT / "execution.json"
    if execution_path.exists():
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        actual = f"Measured final parallel evaluation plus sanity runtime: {execution['elapsed_seconds'] / 60:.2f} minutes (excludes initial timing and interrupted attempts)."
        lines.append(actual)
        readme.append(actual)
    lines += [verdict, "## K=1 sanity: BG h=1", table(sanity),
              "LR literal tolerance is 1e-9 for each metric; RF tolerance is 0.005 for Brier. Raw differences are reported without causal attribution. Four-decimal equality is a separate diagnostic."]
    (OUT / "tuning_summary.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
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


def main() -> None:
    """Freeze timing budget, run nested tuning, sanity checks and generated reporting."""
    OUT.mkdir(exist_ok=True)
    # CatBoost's unchanged defaults write diagnostics relative to the working directory.
    os.chdir(OUT)
    if "--report-only" in sys.argv:
        budget = json.loads((OUT / "budget.json").read_text(encoding="utf-8"))
        budget["estimated_seconds"] = {int(k): v for k, v in budget["estimated_seconds"].items()}
        reports(pd.read_csv(OUT / "tuned_results.csv"), pd.read_csv(OUT / "selected_configs.csv"),
                pd.read_csv(OUT / "sanity.csv"), budget,
                {name: configurations(name, budget["K"]) for name in algorithms()})
        return
    resume = "--run-only" in sys.argv
    if (OUT / "budget.json").exists() and not resume:
        raise FileExistsError("Existing run: preserve outputs before starting another run")
    if resume and (OUT / "tuned_results.csv").exists():
        raise FileExistsError("Completed results exist")
    with (OUT / "warnings.log").open("w", encoding="utf-8") as warning_file:
        def log_warning(message: Any, category: type, filename: str, lineno: int,
                        file: Any = None, line: Any = None) -> None:
            warning_file.write(warnings.formatwarning(message, category, filename, lineno))
            warning_file.flush()
        warnings.showwarning = log_warning
        warnings.simplefilter("always")
        cases = {(site, h): case_data(site, h) for site in ["BG", "KR"] for h in HORIZONS}
        candidates = {name: configurations(name) for name in algorithms()}
        manifest = dict(seed=SEED, python=platform.python_version(), search_spaces=SEARCH_SPACES,
                        candidates=candidates, defaults={n: json_params(m) for n, m in algorithms().items()})
        from importlib.metadata import version
        manifest["versions"] = {p: version(p) for p in ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "lightgbm", "catboost"]}
        if resume:
            existing = json.loads((OUT / "configurations.json").read_text(encoding="utf-8"))
            if json.dumps(existing, sort_keys=True) != json.dumps(manifest, sort_keys=True):
                raise ValueError("Frozen configuration/environment mismatch")
            budget = json.loads((OUT / "budget.json").read_text(encoding="utf-8"))
            budget["estimated_seconds"] = {int(k): v for k, v in budget["estimated_seconds"].items()}
        else:
            (OUT / "configurations.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            budget = timing_budget(cases, candidates)
        candidates = {n: c[:budget["K"]] for n, c in candidates.items()}
        print(f"Frozen budget K={budget['K']}, feasible={budget['feasible']}", flush=True)
        baseline = pd.read_csv(HERE / "results" / "benchmark_results.csv")
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=4) as pool:
            parts = list(pool.map(evaluate_worker,
                                 [(site, h, x, y, candidates) for (site, h), (x, y) in cases.items()]))
        results, selected, predictions = [pd.concat([p[i] for p in parts], ignore_index=True) for i in range(3)]
        results["rank_by_brier"] = results.groupby(["site", "h"]).brier.rank(method="average")
        keys = ["site", "h", "algorithm"]
        results = results.merge(baseline.rename(columns={c: "default_" + c for c in baseline if c not in keys}), on=keys, validate="one_to_one")
        for metric in METRICS:
            results["delta_" + metric] = results[metric] - results["default_" + metric]
        results.to_csv(OUT / "tuned_results.csv", index=False)
        selected.to_csv(OUT / "selected_configs.csv", index=False)
        validate_predictions(predictions, list(candidates))
        predictions.to_csv(OUT / "tuned_predictions.csv.gz", index=False)
        baseline[baseline.kind == "reference"].to_csv(OUT / "default_references.csv", index=False)
        sanity_result, _, _ = evaluate("BG", 1, *cases[("BG", 1)],
                                       {n: [{}] for n in ["Logistic Regression", "Random Forest"]}, "sanity_")
        sanity_rows = []
        for _, row in sanity_result.iterrows():
            default = baseline[(baseline.site == "BG") & (baseline.h == 1) & (baseline.algorithm == row.algorithm)].iloc[0]
            for metric in METRICS:
                diff = row[metric] - default[metric]
                tolerance = 1e-9 if row.algorithm == "Logistic Regression" else (0.005 if metric == "brier" else None)
                sanity_rows.append(dict(algorithm=row.algorithm, metric=metric, recomputed=row[metric],
                                        stored=default[metric], difference=diff, absolute_difference=abs(diff),
                                        tolerance=tolerance, literal_pass=abs(diff) <= tolerance if tolerance is not None else "not prescribed",
                                        equal_after_4dp=round(row[metric], 4) == default[metric]))
        sanity = pd.DataFrame(sanity_rows)
        sanity.to_csv(OUT / "sanity.csv", index=False)
        (OUT / "execution.json").write_text(json.dumps(dict(
            workers=4, blas_threads_per_worker=1, elapsed_seconds=time.perf_counter() - started,
            reused_frozen_budget=resume), indent=2), encoding="utf-8")
        reports(results, selected, sanity, budget, candidates)


if __name__ == "__main__":
    main()
