"""Reproduce WP1 with two seeds and independently audit raw label accounting."""

from itertools import groupby
import json

import numpy as np
import pandas as pd

from s1_eda import ROOT, RAW, ANALYSIS, run


def main() -> None:
    """Save deterministic reproducibility and class counts; durations are hours."""
    config = json.loads((ROOT / "experiments/s1_eda.json").read_text())
    baseline = run(config, outage_only=True)
    alternate_config = config | {"seed": 17, "output_directory": "results/S1/stats_seed17"}
    alternate = run(alternate_config, outage_only=True)
    # Config is the only intended difference. Compare every result/provenance field.
    same_summary = ({k: v for k, v in baseline.items() if k != "config"}
                    == {k: v for k, v in alternate.items() if k != "config"})
    same_tables = ((ROOT / config["output_directory"] / "tables.csv").read_bytes()
                   == (ROOT / alternate_config["output_directory"] / "tables.csv").read_bytes())
    source = pd.read_excel(RAW / ANALYSIS, sheet_name="Hourly Data")
    labels = source["Outage (1/0)"].tolist()
    durations = [len(list(run_values)) for label, run_values in groupby(labels) if label == 1]
    counts = {str(label): labels.count(label) for label in (0, 1)}
    independent = {"event_count": len(durations), "outage_hours": sum(durations),
                   "outage_share": counts["1"] / len(labels),
                   "duration_mean_h": float(np.mean(durations))}
    assert same_summary and same_tables
    assert independent["event_count"] == baseline["event_count"]
    assert independent["outage_hours"] == baseline["outage_hours"]
    assert independent["outage_share"] == baseline["outage_share"]
    assert independent["duration_mean_h"] == baseline["duration_h"]["mean"]
    for key in ("by_month", "by_hour"):
        assert sum(row["hours"] for row in baseline[key]) == len(labels)
        assert sum(row["outage_hours"] for row in baseline[key]) == sum(labels)
    report = {
        "seeds": [config["seed"], 17], "summary_equal_except_config": same_summary,
        "tables_byte_identical": same_tables, "independent_raw_accounting": independent,
        "class_counts": counts, "majority_class_share": max(counts.values()) / len(labels),
        "national_status": baseline["label_validation"]["national_status"],
        "generator": baseline["label_validation"]["generator"],
        "weibull_fit": baseline["weibull_fit"],
        "scope": "Deterministic descriptive EDA; seed invariance is not statistical robustness or independent replication.",
        "statistical_tests": "None: no model comparison or inferential claim in WP1.",
        "weather_available": (RAW / "nasa_power_baghdad_2018_hourly_local.csv").is_file(),
    }
    (ROOT / "results/S1/stats_audit.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(independent))


if __name__ == "__main__":
    main()
