"""Audit stored K=1 outputs and a limited BG h=1 seed sensitivity diagnostic.

No tuning grid or inferential tests. All losses are dimensionless; horizons are hours.
The two fixed seeds are diagnostics, never used to choose production settings.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "studies/S1_outage_forecasting/benchmark"))
import tuning as tu


def main() -> None:
    """Save pooled metric checks, split prevalence and seed diagnostics under results/."""
    out = tu.OUT / "statistical_audit"
    out.mkdir(exist_ok=True)
    names = ["Logistic Regression", "Random Forest"]
    stored = pd.read_csv(tu.OUT / "sanity/tuned_predictions.csv.gz")
    stored_results = pd.read_csv(tu.OUT / "sanity/tuned_results.csv")
    checks = []
    for name in names:
        expected = stored_results.set_index("algorithm").loc[name]
        for metric, value in tu.scores(stored.y.values, stored[name].values).items():
            checks.append({"algorithm": name, "metric": metric, "recomputed": value,
                               "stored": expected[metric], "difference": value - expected[metric]})
    pd.DataFrame(checks).to_csv(out / "pooled_metric_checks.csv", index=False)
    prevalence = []
    for site in ["BG", "KR"]:
        for h in [1, 6]:
            x, y = tu.case_data(site, h)
            for month in range(4, 13):
                masks = tu.split_masks(x.index, h, month)
                for label, mask in zip(["outer", "test", "inner", "validation"], masks):
                    prevalence.append({"site": site, "h": h, "month": month, "split": label,
                                           "n": int(mask.sum()), "positives": int(y[mask].sum()),
                                           "prevalence": float(y[mask].mean())})
    pd.DataFrame(prevalence).to_csv(out / "class_prevalence.csv", index=False)

    # K=1 needs no candidate comparison: refit the default on each outer training set.
    # Keep production checkpoint manifests and protocol seed untouched.
    x, y = tu.case_data("BG", 1)
    rows, predictions = [], []
    with threadpool_limits(limits=1):
        for seed in [42, 43]:
            for month in range(4, 13):
                outer, test, _, _ = tu.split_masks(x.index, 1, month)
                fold = pd.DataFrame({"seed": seed, "month": month,
                                     "origin_time": x.index[test], "y": y[test].values})
                for name in names:
                    model = tu.estimator(name, {}, 0)
                    parameters = {k: seed for k in model.get_params()
                                  if k.endswith("random_state")}
                    model.set_params(**parameters)
                    model.fit(x[outer], y[outer])
                    fold[name] = tu.probabilities(model, x[test])
                predictions.append(fold)
            print(f"Completed BG h=1 default-only diagnostic seed {seed}", flush=True)
    predictions = pd.concat(predictions, ignore_index=True)
    predictions.to_csv(out / "seed_predictions.csv.gz", index=False)
    for seed, group in predictions.groupby("seed"):
        for name in names:
            rows.append(dict(seed=int(seed), algorithm=name,
                             **tu.scores(group.y.values, group[name].values)))
    results = pd.DataFrame(rows)
    results.to_csv(out / "seed_metrics.csv", index=False)
    differences = results[results.seed == 43].set_index("algorithm")[tu.METRICS] - results[
        results.seed == 42].set_index("algorithm")[tu.METRICS]
    differences.to_csv(out / "seed_43_minus_42.csv")
    repeat = predictions[predictions.seed == 42]
    assert repeat.origin_time.astype(str).tolist() == stored.origin_time.tolist()
    assert np.array_equal(repeat.y.values, stored.y.values)
    pd.DataFrame([{"algorithm": name, "max_probability_difference": float(
        np.max(np.abs(repeat[name].values - stored[name].values)))} for name in names]
    ).to_csv(out / "seed42_repeat_checks.csv", index=False)
    print(differences.to_string())
    summarize()


def summarize() -> None:
    """Summarize saved audit evidence without refitting any model."""
    out = tu.OUT / "statistical_audit"
    prevalence = pd.read_csv(out / "class_prevalence.csv")
    metrics = pd.read_csv(out / "pooled_metric_checks.csv")
    assert ((prevalence.positives > 0) & (prevalence.positives < prevalence.n)).all()
    assert metrics.difference.abs().max() < 1e-12
    summary = {
        "all_splits_have_both_classes": True,
        "max_pooled_metric_discrepancy": float(metrics.difference.abs().max()),
        "test_prevalence_ranges": prevalence[prevalence.split == "test"].groupby(
            "site").prevalence.agg(["min", "max"]).to_dict(orient="index"),
        "seeds": [42, 43], "site": "BG", "h": 1, "K": 1,
        "months": list(range(4, 13)), "inference": "descriptive only",
    }
    (out / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--summarize-only"]:
        summarize()
    else:
        main()
