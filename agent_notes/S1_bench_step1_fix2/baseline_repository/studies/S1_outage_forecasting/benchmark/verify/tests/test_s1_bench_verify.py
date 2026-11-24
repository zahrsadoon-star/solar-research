"""Fast independent-loader, history, and causality checks."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path(__file__).resolve().parents[1] / "verify_benchmark.py"
SPEC = importlib.util.spec_from_file_location("s1_independent_verifier", PATH)
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


@pytest.mark.parametrize("site", ["BG", "KR"])
def test_loader(site: str) -> None:
    frame = verify.load_site(site)
    assert len(frame) == 8760
    assert frame.outage.isin([0, 1]).all()
    assert not frame.isna().any().any()


@pytest.mark.parametrize("horizon", [1, 6])
def test_history_hand_computed_and_causal(horizon: int) -> None:
    series = pd.Series(np.zeros(250))
    origin = 180
    for day, value in enumerate([1, 0, 1, 0, 1, 0, 1], start=1):
        series.iloc[origin + horizon - 24 * day] = value
    assert verify.same_hour_history(series, horizon).iloc[origin] == pytest.approx(4 / 7)
    series.iloc[origin + 1:] = 1
    assert verify.same_hour_history(series, horizon).iloc[origin] == pytest.approx(4 / 7)


def test_all_features_causal_and_duration() -> None:
    index = pd.date_range("2018-01-01", periods=250, freq="h")
    frame = pd.DataFrame({"outage": np.zeros(250), "load_kwh": np.ones(250)}, index=index)
    before = verify.features(frame, 6)
    assert before.shape[1] == 19  # Listed features total nineteen, despite the spec's label.
    assert before.state_duration_h.iloc[180] == 181
    frame.iloc[181:] = 9
    pd.testing.assert_frame_equal(before.iloc[:181], verify.features(frame, 6).iloc[:181])


@pytest.mark.parametrize("horizon", [1, 6])
def test_training_targets_precede_boundary(horizon: int) -> None:
    index = pd.date_range("2018-01-01", periods=8760 - horizon, freq="h")
    for month in range(4, 13):
        train, test = verify.split_masks(index, horizon, month)
        assert (index[train] + pd.Timedelta(hours=horizon) < pd.Timestamp(2018, month, 1)).all()
        assert (index[test].month == month).all()


def test_missing_grid_not_silently_non_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = pd.DataFrame({"Grid (kWh)": np.ones(8760), "Generator (kWh)": np.zeros(8760)})
    raw.iloc[0, 0] = np.nan
    monkeypatch.setattr(verify.pd, "read_excel", lambda *args, **kwargs: raw)
    assert pd.isna(verify.load_site("BG").outage.iloc[0])


def test_metrics_hand_computed_threshold_and_probability_scores() -> None:
    """Check dimensionless scores, including the exact threshold tie."""
    result = verify.metrics(np.array([0, 0, 1, 1]), np.array([0.0, 0.5, 0.5, 1.0]))
    assert result == pytest.approx({"accuracy": 3 / 4, "f1": 4 / 5,
                                    "auc": 7 / 8, "brier": 1 / 8})


def test_loader_rejects_wrong_row_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not silently assign a full-year chronology to incomplete input."""
    raw = pd.DataFrame({"Grid (kWh)": [0], "Generator (kWh)": [1]})
    monkeypatch.setattr(verify.pd, "read_excel", lambda *args, **kwargs: raw)
    with pytest.raises(ValueError, match="expected 8760"):
        verify.load_site("BG")


def test_metrics_single_class_explicitly_undefined_auc() -> None:
    """An all-non-outage subset has undefined AUC and zero positive F1."""
    result = verify.metrics(np.zeros(4), np.zeros(4))
    assert np.isnan(result["auc"])
    assert result["f1"] == 0
    assert result["accuracy"] == 1
    assert result["brier"] == 0


@pytest.mark.parametrize("defect", ["missing", "duplicate", "unexpected", "nonfinite"])
def test_comparison_rejects_invalid_grid(defect: str) -> None:
    """Incomplete or ambiguous comparisons must never yield reproduction."""
    table = pd.read_csv(verify.HERE / "results/independent_metrics.csv")
    verify.validate_cases(table)
    if defect == "missing":
        table = table.iloc[1:]
    elif defect == "duplicate":
        table = pd.concat([table, table.iloc[:1]])
    elif defect == "unexpected":
        table.loc[0, "site"] = "unknown"
    else:
        table.loc[0, "auc"] = np.nan
    with pytest.raises(ValueError):
        verify.validate_cases(table)


def test_original_freeze_and_changed_input_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Original provenance validates, while input tampering fails closed."""
    verify.validate_freeze()
    original_digest = verify.digest
    monkeypatch.setattr(verify, "digest", lambda path: "changed" if path == verify.raw_path("BG") else original_digest(path))
    with pytest.raises(ValueError, match="Frozen input changed"):
        verify.validate_freeze()


def test_independent_refuses_existing_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse overwrite before loading data or fitting models."""
    marker = tmp_path / "freeze.json"
    marker.write_text("original")
    monkeypatch.setattr(verify, "OUT", tmp_path)
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        verify.independent()
    assert marker.read_text() == "original"
