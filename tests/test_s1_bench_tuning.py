"""Fast tests for the frozen S1 equal-budget temporal tuning protocol."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studies" / "S1_outage_forecasting" / "benchmark"))
import tuning as tu


@pytest.mark.parametrize("name", list(tu.SEARCH_SPACES))
def test_default_exact_and_draws_reproducible(name: str) -> None:
    """Config zero includes the complete untouched estimator/pipeline defaults."""
    configs = tu.configurations(name)
    assert len(configs) == 20
    assert configs[0] == {}
    assert tu.json_params(tu.estimator(name, configs[0], 0)) == tu.json_params(tu.algorithms()[name])
    assert configs == tu.configurations(name, seed=42)
    assert configs[:8] == tu.configurations(name, k=8)
    rng = np.random.default_rng(42)
    for config in configs[1:]:
        assert set(config) == set(tu.SEARCH_SPACES[name])
        for key, values in tu.SEARCH_SPACES[name].items():
            assert config[key] in values
            assert config[key] == values[int(rng.integers(len(values)))]


@pytest.mark.parametrize("h", [1, 6])
@pytest.mark.parametrize("month", range(4, 13))
def test_nested_boundaries(h: int, month: int) -> None:
    """Both label time and origin time are strictly before training cutoffs."""
    index = pd.date_range("2018-01-01", "2018-12-31 23:00", freq="h")
    outer, test, inner, valid = tu.split_masks(index, h, month)
    start = pd.Timestamp(year=2018, month=month, day=1)
    previous = start - pd.offsets.MonthBegin(1)
    target = index + pd.Timedelta(hours=h)
    assert (index[outer] < start).all() and (target[outer] < start).all()
    assert (index[inner] < previous).all() and (target[inner] < previous).all()
    assert (index[valid] >= previous).all()
    assert (index[valid] < start).all() and (target[valid] < start).all()
    assert (index[test].month == month).all()
    assert valid.sum() == int((start - previous).total_seconds() / 3600) - h
    assert not (inner & valid).any() and not (outer & test).any()
    assert (outer[inner]).all() and (outer[valid]).all()
    if month == 4:
        assert set(index[valid].month) == {3}


def test_selection_minimum_and_first_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selection uses inner validation labels; exact ties preserve first index."""
    x = pd.DataFrame({"x": np.arange(6)})
    y = pd.Series([0, 1, 0, 1, 1, 1])
    inner = np.array([True, True, False, False, False, False])
    valid = np.array([False, False, True, True, False, False])

    class Stub:
        def __init__(self, p: list[float]) -> None:
            self.p = np.array(p)

        def fit(self, xx: pd.DataFrame, yy: pd.Series) -> None:
            assert xx.index.tolist() == [0, 1]
            assert yy.index.tolist() == [0, 1]

        def predict_proba(self, xx: pd.DataFrame) -> np.ndarray:
            assert xx.index.tolist() == [2, 3]
            return np.column_stack([1 - self.p, self.p])

    monkeypatch.setattr(tu, "estimator", lambda name, config, index: Stub(config["p"]))
    configs = [{"p": [0.4, 0.6]}, {"p": [0.1, 0.9]}, {"p": [0.1, 0.9]}]
    chosen, losses = tu.select_config("stub", configs, x, y, inner, valid)
    assert chosen == 1
    assert losses == pytest.approx([0.16, 0.01, 0.01])
    y.iloc[4:] = 0  # unseen outer labels cannot affect selection
    assert tu.select_config("stub", configs, x, y, inner, valid) == (chosen, losses)


def test_prediction_integrity() -> None:
    """Every model shares complete finite rows and unique case/origin keys."""
    frame = pd.DataFrame(dict(site=["BG", "BG"], h=[1, 1], origin_time=["a", "b"],
                              a=[0.2, 0.7], b=[0.1, 0.9]))
    tu.validate_predictions(frame, ["a", "b"])
    with pytest.raises(ValueError, match="Duplicate"):
        tu.validate_predictions(pd.concat([frame, frame]), ["a", "b"])
    for bad in [np.nan, np.inf, -0.1, 1.1]:
        broken = frame.copy()
        broken.loc[0, "b"] = bad
        with pytest.raises(ValueError, match="Invalid"):
            tu.validate_predictions(broken, ["a", "b"])
