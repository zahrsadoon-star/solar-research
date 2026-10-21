"""Deterministic WP1 EDA. Run with --outage-only while weather is unavailable."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache" / "s1_matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import weibull_min

from outage.data import (
    ANALYSIS, ENERGY_COLUMNS, RAW, STATUS, WEATHER, load_outage_dataset,
    load_outage_observations, outage_events, validate_outage_events, validate_outage_labels,
)


def grouped(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Return hourly denominators, outage hours and shares for calendar groups."""
    work = df.assign(month=df.index.month, hour=df.index.hour)
    table = work.groupby(keys)["outage"].agg(hours="size", outage_hours="sum").reset_index()
    table["outage_share"] = table["outage_hours"] / table["hours"]
    return table


def run(config: dict[str, Any], outage_only: bool = False) -> dict[str, Any]:
    """Write reproducible descriptive tables/figures; temperatures are deg C."""
    for key, required in {"dpi": 300, "weibull_fixed_location": 0,
                          "quantile_interpolation": "linear"}.items():
        if config.get(key) != required:
            raise ValueError(f"WP1 protocol requires {key}={required!r}")
    np.random.seed(config["seed"])
    df = load_outage_observations() if outage_only else load_outage_dataset()
    output = ROOT / config["output_directory"]
    if not output.resolve().is_relative_to((ROOT / "results" / "S1").resolve()):
        raise ValueError("Output must stay under results/S1")
    output.mkdir(parents=True, exist_ok=True)
    events = outage_events(df)
    duration = events["duration_h"]
    boundary = (events["start"] == df.index[0]) | (events["end"] == df.index[-1])
    complete = duration[~boundary]
    fit: dict[str, Any] = {"included_events": len(complete), "excluded_boundary_events": int(boundary.sum()),
                           "method": "maximum likelihood, location fixed at zero", "failure": None,
                           "interpretation": "Descriptive continuous approximation to discrete hourly durations."}
    try:
        shape, location, scale = weibull_min.fit(complete, floc=config["weibull_fixed_location"])
        if not np.isfinite([shape, location, scale]).all() or shape <= 0 or scale <= 0:
            raise ValueError("Invalid Weibull fit")
        fit.update(shape=float(shape), location_h=float(location), scale_h=float(scale))
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        fit["failure"] = str(exc)

    month, hour, joint = grouped(df, ["month"]), grouped(df, ["hour"]), grouped(df, ["month", "hour"])
    month["event_count"] = month["month"].map(events.groupby("month").size()).fillna(0).astype(int)
    counts, edges = np.histogram(duration, bins=np.arange(.5, duration.max()+1.5, 1))
    histogram = pd.DataFrame({"duration_h": edges[:-1]+.5, "event_count": counts,
                              "density": counts / len(duration)})
    curve = pd.DataFrame({"duration_h": np.linspace(.01, duration.max()+1, 1000)})
    if fit["failure"] is None:
        curve["density"] = weibull_min.pdf(curve["duration_h"], shape, loc=location, scale=scale)
    tables = [table.assign(table=name) for name, table in [
        ("month", month), ("hour", hour), ("month_hour", joint),
        ("duration_histogram", histogram), ("weibull_density", curve),
        ("events", events.assign(boundary_censored=boundary)),
    ]]

    fig, ax = plt.subplots(figsize=(10, 5))
    heat = joint.pivot(index="month", columns="hour", values="outage_share")
    im = ax.imshow(heat, vmin=0, vmax=1, aspect="auto", origin="lower", cmap="viridis")
    ax.set(xticks=range(24), yticks=range(12), yticklabels=range(1, 13),
           xlabel="Local hour (Asia/Baghdad)", ylabel="Month", title="Generator-derived outage proxy, 2018")
    fig.colorbar(im, ax=ax, label="Outage share")
    fig.tight_layout()
    fig.savefig(output / "outage_hour_month.png", dpi=config["dpi"])
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(histogram["duration_h"], histogram["density"], width=1, alpha=.65, label="All observed runs")
    if fit["failure"] is None:
        ax.plot(curve["duration_h"], curve["density"], label="Weibull fit (complete runs)")
    ax.set(xlabel="Outage proxy duration (h)", ylabel="Density (1/h)", title="Generator-derived event durations")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "outage_duration.png", dpi=config["dpi"])
    plt.close(fig)

    if not outage_only:
        daily = df.resample("D").agg(hours=("outage", "size"), outage_hours=("outage", "sum"),
                                      temp_air_c=("temp_air_c", "max"))
        if not daily["hours"].eq(24).all():
            raise ValueError("Daily temperature analysis requires complete 24-hour local days")
        daily["outage_share"] = daily["outage_hours"] / daily["hours"]
        tables.append(daily.reset_index().assign(table="daily_temperature"))
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(daily["temp_air_c"], daily["outage_share"], alpha=.5, s=16)
        ax.set(xlabel="Daily maximum air temperature (deg C)", ylabel="Daily outage share",
               title="Descriptive association; not a causal estimate", ylim=(0, 1))
        fig.tight_layout()
        fig.savefig(output / "outage_temperature.png", dpi=config["dpi"])
        plt.close(fig)

    sources = [ANALYSIS, STATUS] + ([] if outage_only else [WEATHER])
    summary = {
        "status": "partial_weather_unavailable" if outage_only and not (RAW / WEATHER).exists() else
                  "partial_outage_only" if outage_only else "complete",
        "config": config, "row_count": len(df), "outage_hours": int(df["outage"].sum()),
        "outage_share": float(df["outage"].mean()), "event_count": len(events),
        "duration_h": {"mean": float(duration.mean()), "median": float(duration.median()),
                       "minimum": int(duration.min()), "maximum": int(duration.max()),
                       "sample_std_ddof1": float(duration.std(ddof=1)),
                       "p95": float(duration.quantile(.95, interpolation=config["quantile_interpolation"]))},
        "by_month": month.to_dict("records"), "by_hour": hour.to_dict("records"),
        "label_validation": validate_outage_labels(df), "event_validation": validate_outage_events(df),
        "weibull_fit": fit,
        "boundary_events": events.loc[boundary].astype(str).to_dict("records"),
        "source_sha256": {name: hashlib.sha256((RAW / name).read_bytes()).hexdigest() for name in sources},
        "source_sheets": {ANALYSIS: ["Hourly Data", "Outage Events", "Read Me"], STATUS: ["National Status"]},
        "energy_column_mapping": ENERGY_COLUMNS,
        "weather": {"file": WEATHER, "present": (RAW / WEATHER).is_file(), "schema": "UNVERIFIED",
                    "temperature_analysis_generated": not outage_only},
        "versions": {name: importlib.metadata.version(name) for name in
                     ["numpy", "pandas", "scipy", "matplotlib", "openpyxl"]} | {"python": sys.version},
        "limitations": ["Annual timestamps reconstructed from row order; partial January validation.",
                        "Outage is a generator-operation proxy, not independently verified grid unavailability.",
                        "Source labels retained; national-status disagreements unresolved without independent evidence.",
                        "Generator agreement is internal consistency, not independent validation.",
                        "Completed-event duration, future energy, realized daily maximum temperature and full-year climatology must not enter earlier forecasts.",
                        "Full-year descriptive EDA inspected: later evaluation months are not wholly unseen.",
                        "One household and one year; no causal or forecasting inference.",
                        "No inferential statistical test or independent stochastic runs: deterministic WP1 EDA.",
                        "Boundary-touching runs may be censored; excluded from Weibull fitting."],
    }
    pd.concat(tables, ignore_index=True).to_csv(output / "tables.csv", index=False)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments" / "s1_eda.json")
    parser.add_argument("--outage-only", action="store_true", help="Explicit partial EDA without weather")
    args = parser.parse_args()
    result = run(json.loads(args.config.read_text(encoding="utf-8")), args.outage_only)
    print(json.dumps({key: result[key] for key in ["status", "row_count", "outage_hours", "event_count"]}))
