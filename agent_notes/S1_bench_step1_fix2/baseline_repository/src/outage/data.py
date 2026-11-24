"""Hourly Baghdad outage data; raw files are always read-only."""

from datetime import datetime, time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
ANALYSIS = "BG18760_with_analysis.xlsx"
STATUS = "BG1-8760_v2026-04_homer_folder.xlsx"
WEATHER = "nasa_power_baghdad_2018_hourly_local.csv"
TZ = "Asia/Baghdad"
WEATHER_UNITS = {
    "temp_air_c": "degC", "rel_humidity_pct": "%",
    "wind_speed_10m_ms": "m/s", "ghi_wm2": "W/m2",
}
ENERGY_COLUMNS = {
    "Grid (kWh)": "grid_kwh", "Generator (kWh)": "generator_kwh",
    "Total (kWh)": "load_kwh", "Outage (1/0)": "outage",
}


def _check_hourly(df: pd.DataFrame) -> None:
    """Require finite binary labels and an ordered, gap-free hourly index."""
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.hasnans:
        raise ValueError("Expected a DatetimeIndex without NaT")
    if not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError("Timestamps must be unique and increasing")
    if len(idx) > 1 and not (np.diff(idx.as_unit("s").asi8) == 3600).all():
        raise ValueError("Timestamps must be consecutive hours")
    if not df["outage"].isin([0, 1]).all():
        raise ValueError("Outage labels must be nonmissing binary values")


def load_outage_observations(raw_dir: Path = RAW) -> pd.DataFrame:
    """Read outage/energy observations without weather (kWh per hourly row).

    BG18760_with_analysis.xlsx, 'Hourly Data': Timestamp, Grid (kWh),
    Generator (kWh), Total (kWh), Hour, Month, Outage (1/0).
    'Read Me' says timestamps were reconstructed from row order with partial
    January validation. Build the index by position from 2018-01-01 00:00
    Baghdad local time. BG Date & Time cells are mostly time-only Excel
    values; only full datetimes can check calendar alignment (745 in the
    supplied National Status sheet). Never reconstruct dates from time-only cells.
    This partial dataset is explicitly NOT the complete WP1 dataset.
    """
    source = pd.read_excel(Path(raw_dir) / ANALYSIS, sheet_name="Hourly Data")
    supplied = pd.DatetimeIndex(pd.to_datetime(source["Timestamp"])).tz_localize(TZ)
    expected = pd.date_range("2018-01-01", periods=8760, freq="h", tz=TZ)
    if not supplied.equals(expected):
        raise ValueError("Hourly Data must cover exactly the 8,760 local hours of 2018")
    idx = expected  # Reconstruct by position; analysis timestamps are a consistency check.
    if not np.array_equal(source["Hour"], idx.hour) or not np.array_equal(source["Month"], idx.month):
        raise ValueError("Workbook Hour/Month disagree with Timestamp")
    df = source[list(ENERGY_COLUMNS)].rename(columns=ENERGY_COLUMNS)
    df.index = idx.rename("timestamp")
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError("Missing or nonfinite hourly observations")
    _check_hourly(df)
    df["outage"] = df["outage"].astype(int)
    return df


def load_outage_dataset(raw_dir: Path = RAW) -> pd.DataFrame:
    """Join weather to generator-operation proxy observations by local hour.

    Weather timestamps are naive Baghdad clocks, already UTC+3. Localize,
    never shift; preserve degC, %, m/s and W/m2 values without conversion.
    Require every local hour of 2018 exactly once and finite measurements;
    never interpolate, substitute weather or adjudicate source outage labels.
    """
    path = Path(raw_dir) / WEATHER
    if not path.is_file():
        raise FileNotFoundError(f"Required local weather file is missing: {path}")
    weather = pd.read_csv(path)
    required = {"time_local_baghdad", *WEATHER_UNITS}
    if not required.issubset(weather.columns):
        raise ValueError(f"Missing weather columns: {sorted(required - set(weather.columns))}")
    if len(weather) != 8760:
        raise ValueError("Weather must contain exactly 8,760 hourly rows")
    idx = pd.DatetimeIndex(pd.to_datetime(weather.pop("time_local_baghdad"), errors="raise"))
    if idx.tz is not None:
        raise ValueError("Weather timestamps must be naive Baghdad local time")
    expected = pd.date_range("2018-01-01", periods=8760, freq="h", tz=TZ)
    idx = idx.tz_localize(TZ)
    if not idx.equals(expected):
        raise ValueError("Weather must cover unique, ordered, consecutive local hours of 2018")
    weather = weather[list(WEATHER_UNITS)].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(weather.to_numpy(dtype=float)).all():
        raise ValueError("Weather measurements must be finite and nonmissing")
    weather.index = idx.rename("timestamp")
    observations = load_outage_observations(raw_dir)
    return observations.join(weather, how="left", validate="one_to_one")


def validate_outage_labels(
    df: pd.DataFrame | None = None, raw_dir: Path = RAW,
) -> dict[str, Any]:
    """Report agreements without changing labels; energy values are in kWh.

    National Status columns: Date & Time, National Grid (kWh),
    Status (1=National / 0=No). Use 1-status, with disclosed row alignment
    only after checking all grid energies, full datetimes and time-only clocks.
    Time-only values do not establish calendar dates independently.
    Clock mismatches are exposed; agreement rates remain conditional on row
    order, not evidence of independently confirmed timestamp alignment.
    """
    if df is None:
        df = load_outage_observations(raw_dir)
    _check_hourly(df)
    status = pd.read_excel(Path(raw_dir) / STATUS, sheet_name="National Status")
    expected = pd.date_range("2018-01-01", periods=8760, freq="h", tz=TZ)
    if len(status) != len(df) or not df.index.equals(expected):
        raise ValueError("Status alignment requires all 8,760 ordered 2018 hours")
    if not np.array_equal(status["National Grid (kWh)"], df["grid_kwh"]):
        raise ValueError("Cannot align status: grid energies differ")
    full_dates = 0
    time_only = 0
    clock_disagreements = []
    for stamp, value in zip(df.index, status["Date & Time"]):
        if isinstance(value, datetime):
            if pd.Timestamp(value).tz_localize(TZ) != stamp:
                raise ValueError("Status full datetime disagrees with analysis timestamp")
            full_dates += 1
        elif isinstance(value, time):
            if value != stamp.time():
                clock_disagreements.append({"timestamp": stamp.isoformat(), "source_clock": value.isoformat()})
            time_only += 1
        else:
            raise ValueError(f"Unrecognized status timestamp: {value!r}")
    y = df["outage"].to_numpy()
    s = pd.to_numeric(status["Status (1=National / 0=No)"], errors="raise").to_numpy(dtype=float)
    gen = df["generator_kwh"].to_numpy(dtype=float)
    result: dict[str, Any] = {
        "row_count": len(df), "alignment_method": "conditional_row_order_checked_grid_energy_and_full_datetimes",
        "full_datetime_count": full_dates, "time_only_count": time_only,
        "time_only_clock_agreement_count": time_only - len(clock_disagreements),
        "time_only_clock_disagreement_count": len(clock_disagreements),
        "time_only_clock_disagreements": clock_disagreements,
        "alignment_limitation": "Index built by position from 2018-01-01 00:00 Baghdad local; only full datetimes check calendar alignment. Time-only Excel cells are diagnostic only; agreement is conditional on row order.",
        "target_definition": "Positive generator energy; proxy for national-grid unavailability.",
        "uncertainty_policy": "Retain workbook labels and expose all disagreements; no adjudication without independent evidence.",
        "provenance_note": "Generator comparison is not independent: workbook labels are generator-derived.",
    }
    for name, values, valid, missing, invalid in [
        ("national_status", 1-s, np.isin(s, [0, 1]), np.isnan(s), ~np.isnan(s) & ~np.isin(s, [0, 1])),
        ("generator", (gen > 0).astype(int), np.isfinite(gen), np.isnan(gen), ~np.isnan(gen) & ~np.isfinite(gen)),
    ]:
        bad = np.flatnonzero(valid & (y != values))
        count = int(valid.sum())
        result[name] = {
            "valid_comparison_count": count, "coverage": count / len(df),
            "agreement_rate": float((y[valid] == values[valid]).mean()) if count else None,
            "disagreement_count": len(bad), "missing_count": int(missing.sum()),
            "invalid_binary_count": int(invalid.sum()) if name == "national_status" else 0,
            "invalid_source_count": int(invalid.sum()),
            "disagreements": [
                {"timestamp": df.index[i].isoformat(), "outage": int(y[i]),
                 "comparator_outage": int(values[i]), "national_status": float(s[i]),
                 "grid_kwh": float(df["grid_kwh"].iloc[i]), "generator_kwh": float(gen[i])}
                for i in bad
            ],
        }
    return result


def outage_events(df: pd.DataFrame) -> pd.DataFrame:
    """Return maximal outage runs, inclusive endpoints and duration in hours.

    start_hour/month refer to onset; runs crossing calendar boundaries remain
    intact. Boundary-touching runs are retained in annual accounting.
    """
    _check_hourly(df)
    mask = df["outage"].to_numpy(dtype=bool)
    edges = np.diff(np.r_[False, mask, False].astype(int))
    starts, stops = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    idx = df.index
    result = pd.DataFrame({"start": idx[starts], "end": idx[stops-1],
                           "duration_h": stops-starts, "start_hour": idx[starts].hour,
                           "month": idx[starts].month})
    if int(result["duration_h"].sum()) != int(mask.sum()):
        raise AssertionError("Event hours do not equal outage hours")
    return result


def validate_outage_events(df: pd.DataFrame, raw_dir: Path = RAW) -> dict[str, Any]:
    """Compare individual event starts/durations and workbook summary (hours)."""
    events = outage_events(df)
    sheet = pd.read_excel(Path(raw_dir) / ANALYSIS, sheet_name="Outage Events", header=2)
    refs = sheet.loc[sheet["Event #"].notna()]
    starts = pd.DatetimeIndex(pd.to_datetime(refs["Start timestamp"])).tz_localize(TZ)
    differences = []
    for i in range(max(len(events), len(refs))):
        if i >= len(events) or i >= len(refs):
            differences.append({"event_row": i+1, "reason": "unmatched record"})
            continue
        actual = events.iloc[i]
        reference = refs.iloc[i]
        for field, value in {"start": starts[i], "duration_h": reference["Duration (h)"],
                             "start_hour": reference["Start hour"], "month": reference["Month"]}.items():
            if actual[field] != value:
                differences.append({"event_row": i+1, "field": field,
                                    "computed": str(actual[field]), "workbook": str(value)})
    stats = sheet.dropna(subset=["Statistic", "Value"]).set_index("Statistic")["Value"]
    duration = events["duration_h"]
    computed = {"Number of outage events": len(events), "Total outage hours": int(duration.sum()),
                "Mean duration (h)": float(duration.mean()), "Median duration (h)": float(duration.median()),
                "95th percentile duration (h)": float(duration.quantile(.95, interpolation="linear")),
                "Longest outage (h)": int(duration.max())}
    return {"computed_event_count": len(events), "workbook_event_count": len(refs),
            "record_differences": differences,
            "summary_comparison": {key: {"computed": value, "workbook": float(stats[key]),
                                         "difference": value-float(stats[key])} for key, value in computed.items()}}
