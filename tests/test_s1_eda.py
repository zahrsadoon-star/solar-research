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
