"""Reject settings that would silently violate the descriptive EDA protocol."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("s1_eda", ROOT / "scripts" / "s1_eda.py")
assert SPEC is not None and SPEC.loader is not None
EDA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EDA)


@pytest.mark.parametrize("key,value", [
    ("dpi", 72), ("weibull_fixed_location", 1), ("quantile_interpolation", "nearest"),
])
def test_protocol_configuration(key: str, value: object) -> None:
    """Nonprotocol DPI, location (hours), or quantile conventions must fail."""
    config = json.loads((ROOT / "experiments" / "s1_eda.json").read_text())
    config[key] = value
    with pytest.raises(ValueError, match="WP1 protocol requires"):
        EDA.run(config, outage_only=True)


@pytest.mark.parametrize("seed", [0, 17])
def test_complete_temperature_eda(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seed: int) -> None:
    """Daily temperatures (degC) and proxy shares match independent raw aggregation."""
    import numpy as np
    import pandas as pd

    config = json.loads((ROOT / "experiments" / "s1_eda.json").read_text())
    config["seed"] = seed
    monkeypatch.setattr(EDA, "ROOT", tmp_path)
    summary = EDA.run(config)
    output = tmp_path / config["output_directory"]
    daily = pd.read_csv(output / "tables.csv").query("table == 'daily_temperature'")
    weather = pd.read_csv(EDA.RAW / EDA.WEATHER)
    labels = pd.read_excel(EDA.RAW / EDA.ANALYSIS, sheet_name="Hourly Data")["Outage (1/0)"]
    np.testing.assert_allclose(daily["temp_air_c"], weather["temp_air_c"].to_numpy().reshape(-1, 24).max(axis=1))
    np.testing.assert_allclose(daily["outage_share"], labels.to_numpy().reshape(-1, 24).mean(axis=1))
    assert len(daily) == 365 and daily["hours"].eq(24).all()
    expected_dates = pd.date_range("2018-01-01", periods=365, freq="D", tz="Asia/Baghdad")
    assert pd.DatetimeIndex(pd.to_datetime(daily["timestamp"])).tz_convert("Asia/Baghdad").equals(expected_dates)
    np.testing.assert_array_equal(daily["outage_hours"], labels.to_numpy().reshape(-1, 24).sum(axis=1))
    assert summary["status"] == "complete"
    assert summary["label_validation"]["national_status"]["disagreement_count"] == 4
    assert (output / "outage_temperature.png").stat().st_size > 0
