"""Additional seed and imbalance audit; preserves the original independent freeze.

Run from the repository root with PYTHONDONTWRITEBYTECODE=1. Units: hours and
kWh in the imported independent features; all reported metrics are dimensionless.
"""
from __future__ import annotations

import json
import time
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from threadpoolctl import threadpool_limits

import verify_benchmark as v


def check_freeze() -> None:
    """Reject changed original inputs, config, source snapshot, or result bytes."""
    frozen = json.loads((v.OUT / "freeze.json").read_text())
    assert v.digest(v.ROOT / "agent_notes/S1_bench_verify/independent_frozen.py") == frozen["source_sha256"]
    assert v.digest(v.HERE / "config.json") == frozen["config_sha256"]
    for site, expected in frozen["input_sha256"].items():
        assert v.digest(v.raw_path(site)) == expected
    for name, expected in frozen["output_sha256"].items():
        assert v.digest(v.OUT / f"{name}.csv") == expected


def run(seed: int = 43) -> None:
    """Repeat every chronological RF fold with an independently fixed new seed."""
    start = time.perf_counter()
    check_freeze()
    baseline = pd.read_csv(v.OUT / "predictions.csv", parse_dates=["origin"])
    predictions, balance = [], []
    for site in v.CONFIG["sites"]:
        frame = v.load_site(site)
        for horizon in v.CONFIG["horizons_h"]:
            x, y = v.features(frame, horizon), frame.outage.shift(-horizon)
            valid = x.notna().all(axis=1) & y.notna()
            x, y = x.loc[valid], y.loc[valid]
            for month in v.CONFIG["test_months"]:
                train, test = v.split_masks(x.index, horizon, month)
                for name, mask in [("train", train), ("test", test)]:
                    balance.append({"site": site, "horizon_h": horizon, "month": month,
                                    "subset": name, "n": int(mask.sum()),
                                    "outages": int(y.loc[mask].sum()), "outage_share": y.loc[mask].mean()})
                model = RandomForestClassifier(**{**v.CONFIG["rf"], "random_state": seed})
                with threadpool_limits(limits=1):
                    model.fit(x.loc[train], y.loc[train])
                    p = model.predict_proba(x.loc[test])[:, 1]
                predictions.append(pd.DataFrame({"site": site, "horizon_h": horizon,
                                                 "origin": x.index[test], "truth": y.loc[test], "RF": p}))
                print(f"Seed {seed}: {site} h={horizon} month={month}", flush=True)
    new = pd.concat(predictions, ignore_index=True)
    paired = baseline.merge(new, on=["site", "horizon_h", "origin"], suffixes=("_original", "_new"), validate="one_to_one")
    assert len(paired) == len(new) == len(baseline)
    np.testing.assert_array_equal(paired.truth_original, paired.truth_new)
    rows = []
    for (site, horizon), group in paired.groupby(["site", "horizon_h"]):
        old = v.metrics(group.truth_original.to_numpy(), group.RF_original.to_numpy())
        fresh = v.metrics(group.truth_new.to_numpy(), group.RF_new.to_numpy())
        for metric in old:
            rows.append({"site": site, "horizon_h": horizon, "metric": metric,
                         "original_seed": v.CONFIG["rf"]["random_state"], "new_seed": seed,
                         "original": old[metric], "new": fresh[metric], "abs_diff": abs(old[metric] - fresh[metric]),
                         "within_rf_reproduction_tolerance": abs(old[metric] - fresh[metric]) <= v.CONFIG["tolerance"]["RF"]})
    result = pd.DataFrame(rows)
    result.to_csv(v.OUT / "seed_stability.csv", index=False)
    new.to_csv(v.OUT / "seed_predictions.csv", index=False)
    pd.DataFrame(balance).to_csv(v.OUT / "class_balance.csv", index=False)
    metadata = {"seed": seed, "elapsed_seconds": time.perf_counter() - start,
                "source_sha256": v.digest(Path(__file__)), "verifier_sha256": v.digest(v.HERE / "verify_benchmark.py"),
                "sklearn": v.sklearn.__version__, "max_abs_diff": float(result.abs_diff.max()),
                "all_within_rf_reproduction_tolerance": bool(result.within_rf_reproduction_tolerance.all()),
                "statistical_test": "none; descriptive fixed-seed sensitivity, not an equivalence test"}
    (v.OUT / "seed_run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    check_freeze()
    print(json.dumps(metadata, indent=2))


def report() -> None:
    """Generate the statistical review from saved empirical evidence."""
    check_freeze()
    comparison = json.loads((v.OUT / "comparison_summary.json").read_text())
    seed = json.loads((v.OUT / "seed_run.json").read_text())
    stability = pd.read_csv(v.OUT / "seed_stability.csv")
    balance = pd.read_csv(v.OUT / "class_balance.csv")
    assert ((balance.outages > 0) & (balance.outages < balance.n)).all()
    ranges = balance.groupby(["site", "subset"]).outage_share.agg(["min", "max"]).reset_index()
    ranges.to_csv(v.OUT / "class_balance_ranges.csv", index=False)
    annual = pd.read_csv(v.OUT / "outage_shares.csv").query("period == 'annual'")
    suites = ET.parse(v.OUT / "pytest_statistician.xml").getroot().findall("testsuite")
    checks = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ["tests", "failures", "errors", "skipped"]}
    (v.OUT / "statistician_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    text = f"""# Statistician verification

Verdict: **{comparison['verdict']}**. {comparison['passed']} of {comparison['comparisons']} original comparisons pass. The largest original RF discrepancy is {comparison['max_abs_diff_by_method']['RF']:.8f}; its cause remains unresolved, within the specified tolerance. No method was tuned to improve agreement.

## Independence and additional run

The earlier agent's independent implementation and frozen artifacts already existed when this review began. Their source snapshot, configuration, raw-input hashes and output hashes were verified unchanged. This review extends that implementation; it is not a newly blinded implementation. The benchmark source was read after rerunning comparison of the frozen results. Original seed-run counts in REPORT.md describe the original frozen experiment only.

The additional RF seed is {seed['seed']}; the baseline seed is {int(stability.original_seed.iloc[0])}. Every original site, horizon and monthly fold was rerun with unchanged model settings and features. Truth and origin alignment were asserted before comparison. Runtime was {seed['elapsed_seconds']:.2f} seconds. Maximum metric difference across seeds is {seed['max_abs_diff']:.8f}. All differences within the existing RF reproduction tolerance: **{seed['all_within_rf_reproduction_tolerance']}**. This is a descriptive sensitivity check, not a pre-registered equivalence test or a population uncertainty estimate. Two seeds cannot establish general robustness. LR and the references are deterministic under this setup and were not refitted for the seed check.

{v.markdown(stability)}

Seed-sensitive cases exceeding the existing reproduction tolerance (this threshold is used descriptively, not as an inferential stability criterion):

{v.markdown(stability.loc[~stability.within_rf_reproduction_tolerance])}

The fixed-seed reproduction verdict remains unchanged. The additional run does not support an unqualified claim that every metric is stable; the minority-class thresholded F1 warrants explicit seed sensitivity reporting.

## Data and class imbalance

Both loaders were exercised again. The original raw audits report no NaNs, nonnumeric energy cells or negative energy values. Full monthly outage counts and shares remain in `results/outage_shares.csv`.

{v.markdown(annual)}

Train/test class shares across chronological folds (target labels, not origin states):

{v.markdown(ranges)}

No class weighting, resampling, balancing or threshold tuning is used by LR/RF. This matches the prescribed benchmark; imbalance is handled through transparent reference scores and complementary F1, AUC and Brier reporting, not by claiming accuracy alone is sufficient. All audited folds contain both classes. Oversampling is not needed to reproduce the specified probability task, and adding it now would change the experiment. Calibration and minority-class utility are not established by these pooled metrics.

## Leakage and random holdout

Direct source inspection confirms the line-by-line verdicts in `results/leakage_audit.csv`: trailing features use completed observations through the origin, target calendar values are known, future shifts occur only in labels, and the monthly training mask excludes targets entering the test month. StandardScaler is inside the LR pipeline and fitted only on training rows. This assumes completed origin-hour metering is available when a forecast is issued. No future-observation or scaling leakage was found in the chronological evaluation.

The random holdout uses shuffled hourly rows over the eligible full year, month stratification and training-only scaling. This matches the README's descriptive random comparison, but permits future observations relative to test origins and overlapping histories. It is not prospective forecasting evidence. Different populations and training sizes prevent attributing its entire uplift to adjacency. Random-split accuracy was not refitted in this review.

## Statistical tests and multiplicity

The benchmark contains no inferential statistical tests, p-values or confidence intervals. Numerical tolerance checks have no independence or distributional test assumptions, and need no multiplicity correction. A ranking is descriptive: reproduction does not establish superiority. The README's proposed Diebold-Mariano / Wilcoxon analysis is future work, not an existing validated test. Hourly losses are serially dependent and seasonal; expanding monthly fits also share training observations. An IID test of hourly errors or an unqualified independent-fold Wilcoxon test would be unjustified. Any later confirmatory analysis must define its comparison family and account for temporal dependence and multiplicity before inspecting significance; no such test is invented here.

## Automated checks and discrepancies

Pytest: {checks['tests']} collected outcomes, {checks['failures']} failures, {checks['errors']} errors, {checks['skipped']} skips. Existing tests cover real loaders, hand-computed history, future perturbations, training-target boundaries and missing labels. Added checks cover hand-computed threshold/F1/AUC/Brier, wrong loader row counts, and undefined single-class AUC. See `results/pytest_statistician.xml` and the task-notes pytest log.

The feature enumeration contains {len(v.features(v.load_site('BG'), v.CONFIG['horizons_h'][0]).columns)} columns; the task/README description says eighteen. The benchmark and verifier both include every enumerated feature. Missing-value handling differs in the original benchmark but has no observed effect on these complete inputs. Publication precision explains reference/LR discrepancies; RF differences exceed rounding but pass tolerance. Keep the uncertainty about the RF discrepancy explicit.

All additions stay within the explicit write allowlist. Consequently the requested tests are in `verify/tests/test_s1_bench_verify.py`, this report is in `agent_notes/S1_bench_verify/STATS_REPORT.md`, and the implementation report is in the same notes directory. No raw data, legacy file, benchmark source or benchmark result was modified.

Re-run with `python studies/S1_outage_forecasting/benchmark/verify/statistical_review.py run`, then `report` after producing the pytest XML. Use PYTHONDONTWRITEBYTECODE=1 and route pytest cache/temp files to the allowed task notes directory.
"""
    (v.ROOT / "agent_notes/S1_bench_verify/STATS_REPORT.md").write_text(text, encoding="utf-8")
    v.report()
    with (v.HERE / "REPORT.md").open("a", encoding="utf-8") as handle:
        handle.write("\n\n## Additional statistician review\n\n" + text.split("\n", 1)[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="run", choices=["run", "report"])
    {"run": run, "report": report}[parser.parse_args().stage]()
