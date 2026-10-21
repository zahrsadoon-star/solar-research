"""Core event accounting, real-source audits and explicit missing-input behavior."""

from pathlib import Path
from itertools import groupby

import numpy as np
import pandas as pd
import pytest

from outage.data import (
    RAW, STATUS, WEATHER, load_outage_dataset, load_outage_observations, outage_events,
    validate_outage_events, validate_outage_labels,
)


@pytest.fixture(scope="module")
def observations() -> pd.DataFrame:
    return load_outage_observations()


def test_observation_contract(observations: pd.DataFrame) -> None:
    assert len(observations) == 8760
    assert observations.index.is_monotonic_increasing
    assert observations.index.is_unique
    assert str(observations.index.tz) == "Asia/Baghdad"
    assert (np.diff(observations.index.as_unit("s").asi8) == 3600).all()
    assert not observations.isna().any().any()
    assert observations["outage"].isin([0, 1]).all()
    assert pd.api.types.is_integer_dtype(observations["outage"])


def test_real_event_accounting(observations: pd.DataFrame) -> None:
    events = outage_events(observations)
    assert events["duration_h"].sum() == observations["outage"].sum()
    assert ((events["end"] - events["start"]).dt.total_seconds() / 3600 + 1 == events["duration_h"]).all()
    audit = validate_outage_events(observations)
    assert not audit["record_differences"]
    assert all(abs(item["difference"]) < 1e-10 for item in audit["summary_comparison"].values())


def test_label_audit_preserves_labels(observations: pd.DataFrame) -> None:
    before = observations.copy(deep=True)
    summary = validate_outage_labels(observations)
    assert {"row_count", "alignment_method", "national_status", "generator"} <= summary.keys()
    for name in ["national_status", "generator"]:
        assert {"valid_comparison_count", "coverage", "agreement_rate", "disagreement_count",
                "disagreements", "missing_count", "invalid_binary_count"} <= summary[name].keys()
        assert summary[name]["coverage"] == 1
    assert summary["national_status"]["disagreement_count"] == 4
    assert summary["generator"]["disagreement_count"] == 0
    pd.testing.assert_frame_equal(before, observations)


@pytest.mark.parametrize("labels, durations", [([], []), ([0, 0], []), ([1], [1]),
    ([1, 1, 1], [3]), ([1, 0, 1], [1, 1]), ([0, 1, 1, 0], [2])])
def test_event_boundaries(labels: list[int], durations: list[int]) -> None:
    df = pd.DataFrame({"outage": labels}, index=pd.date_range("2018-01-31 23:00", periods=len(labels), freq="h", tz="Asia/Baghdad"))
    events = outage_events(df)
    assert events["duration_h"].tolist() == durations
    if labels == [1, 1, 1]:
        assert events.iloc[0]["month"] == 1  # Crossing month remains one run.


@pytest.mark.parametrize("kind", ["gap", "duplicate", "reverse", "nan", "nonbinary"])
def test_event_rejects_bad_input(kind: str) -> None:
    df = pd.DataFrame({"outage": [0., 1., 0.]}, index=pd.date_range("2018-01-01", periods=3, freq="h"))
    if kind == "gap":
        df = df.iloc[[0, 2]]
    elif kind == "duplicate":
        df.index = pd.DatetimeIndex([df.index[0], df.index[0], df.index[2]])
    elif kind == "reverse":
        df = df.iloc[::-1]
    else:
        df.iloc[1, 0] = np.nan if kind == "nan" else 2
    with pytest.raises(ValueError):
        outage_events(df)


def test_loader_fails_closed_without_weather(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="weather"):
        load_outage_dataset(tmp_path)


def test_loader_requires_real_schema_inspection(tmp_path: Path) -> None:
    (tmp_path / WEATHER).touch()
    with pytest.raises(NotImplementedError, match="inspect"):
        load_outage_dataset(tmp_path)


@pytest.fixture(scope="module")
def status_sheet() -> pd.DataFrame:
    return pd.read_excel(RAW / STATUS, sheet_name="National Status")


@pytest.mark.parametrize("field", ["National Grid (kWh)", "Date & Time"])
def test_alignment_rejects_mismatches(
    observations: pd.DataFrame, status_sheet: pd.DataFrame, monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    source = status_sheet.copy(deep=True)
    source.loc[0, field] = 99 if field == "National Grid (kWh)" else pd.Timestamp("2018-01-02")
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: source)
    with pytest.raises(ValueError, match="grid energies|full datetime"):
        validate_outage_labels(observations)


def test_missing_invalid_status_excluded_from_agreement(
    observations: pd.DataFrame, status_sheet: pd.DataFrame, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = status_sheet.copy(deep=True)
    source["Status (1=National / 0=No)"] = source["Status (1=National / 0=No)"].astype(float)
    source.loc[0, "Status (1=National / 0=No)"] = np.nan
    source.loc[1, "Status (1=National / 0=No)"] = 2
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: source)
    audit = validate_outage_labels(observations)["national_status"]
    assert audit["valid_comparison_count"] == len(observations)-2
    assert audit["missing_count"] == audit["invalid_binary_count"] == 1
    assert audit["agreement_rate"] == pytest.approx(1 - 4/(len(observations)-2))


def test_complete_dataset_contract() -> None:
    df = load_outage_dataset()
    assert len(df) == 8760 and not df.isna().any().any()
    assert set(df.columns) == {"grid_kwh", "generator_kwh", "load_kwh", "outage", "temp_air_c",
                               "rel_humidity_pct", "wind_speed_10m_ms", "ghi_wm2"}


def test_alignment_exposes_time_only_mismatch(
    observations: pd.DataFrame, status_sheet: pd.DataFrame, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report inconsistent clocks without claiming validated time alignment."""
    from datetime import time

    source = status_sheet.copy(deep=True)
    row = next(i for i, value in enumerate(source["Date & Time"]) if isinstance(value, time))
    source.loc[row, "Date & Time"] = time((observations.index[row].hour + 1) % 24)
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: source)
    audit = validate_outage_labels(observations)
    assert {"timestamp": observations.index[row].isoformat(),
            "source_clock": source.loc[row, "Date & Time"].isoformat()} in audit["time_only_clock_disagreements"]
    assert audit["time_only_clock_agreement_count"] + audit["time_only_clock_disagreement_count"] == audit["time_only_count"]


@pytest.mark.parametrize("seed", [0, 17])
def test_event_runs_independent_oracle(seed: int) -> None:
    """Synthetic binary sequences check run accounting, with durations in hours."""
    rng = np.random.default_rng(seed)
    for prevalence in (0.01, 0.5, 0.99):
        labels = (rng.random(1000) < prevalence).astype(int)
        df = pd.DataFrame({"outage": labels}, index=pd.date_range(
            "2018-01-31 12:00", periods=len(labels), freq="h", tz="Asia/Baghdad"))
        expected = [len(list(values)) for label, values in groupby(labels) if label == 1]
        events = outage_events(df)
        assert events["duration_h"].tolist() == expected
        reconstructed = pd.Series(0, index=df.index)
        for event in events.itertuples():
            reconstructed.loc[event.start:event.end] += 1
        np.testing.assert_array_equal(reconstructed, labels)


def test_observations_preserve_raw_values(observations: pd.DataFrame) -> None:
    """Ensure loading introduces no scaling, smoothing, or label replacement."""
    from outage.data import ANALYSIS, ENERGY_COLUMNS

    source = pd.read_excel(RAW / ANALYSIS, sheet_name="Hourly Data")
    for original, output in ENERGY_COLUMNS.items():
        np.testing.assert_array_equal(source[original], observations[output])


def test_event_validation_detects_corrupt_reference(
    observations: pd.DataFrame, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equal annual duration totals must not conceal wrong individual events."""
    from outage.data import ANALYSIS

    source = pd.read_excel(RAW / ANALYSIS, sheet_name="Outage Events", header=2)
    source.loc[0, "Duration (h)"] += 1
    source.loc[1, "Duration (h)"] -= 1
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: source)
    differences = validate_outage_events(observations)["record_differences"]
    assert [(item["event_row"], item["field"]) for item in differences] == [
        (1, "duration_h"), (2, "duration_h")]
