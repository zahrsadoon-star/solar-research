"""Fast tests for the frozen S1 equal-budget temporal tuning protocol."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studies" / "S1_outage_forecasting" / "benchmark"))
import tuning as tu


def test_top_two_includes_boundary_ties() -> None:
    """A boundary tie cannot arbitrarily pick a unique pair (unitless loss)."""
    group = pd.DataFrame({"algorithm": ["a", "b", "c", "d"], "brier": [0.1, 0.2, 0.2, 0.3]})
    assert tu.top_two_members(group, "brier") == {"a", "b", "c"}
    assert tu.top_two_members(group.iloc[::-1], "brier") == {"a", "b", "c"}


def test_sanity_rejects_unvalidated_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    """A historical CSV cannot bypass source/input/environment validation."""
    monkeypatch.setattr(tu, "case_data", lambda *args: (None, None))

    def incompatible(*args: object, **kwargs: object) -> None:
        assert kwargs["read_only"] is True
        raise ValueError("Incompatible checkpoint manifest")

    monkeypatch.setattr(tu, "evaluate", incompatible)
    result = tu.validated_sanity(pd.DataFrame())
    assert "not validated" in result.iloc[0].status


def test_subset_report_has_no_dominance_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity-only reports cannot assert conclusions about twelve algorithms."""
    monkeypatch.setattr(tu, "OUT", tmp_path)
    results = pd.DataFrame({"site": ["BG"] * 2, "h": [1] * 2,
                            "algorithm": ["Logistic Regression", "Random Forest"],
                            "brier": [0.2, 0.1], "default_brier": [0.2, 0.1],
                            "delta_brier": [0., 0.], "rank_by_brier": [2., 1.],
                            "default_rank_by_brier": [2., 1.],
                            "default_accuracy": [0.7, 0.8], "accuracy": [0.7, 0.8]})
    selected = results[["site", "h", "algorithm"]].assign(config_index=0)
    budget = {"K": 1, "estimated_seconds": {1: 1}, "feasible": False,
              "formula": "test", "overhead": "test"}
    tu.reports(results, selected, pd.DataFrame({"status": ["test"]}), budget,
               {n: [{}] for n in results.algorithm})
    summary = (tmp_path / "tuning_summary.md").read_text()
    assert "SUBSET ONLY" in summary
    assert "Extra Trees" not in summary


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
    assert [r["loss"] for r in losses] == pytest.approx([0.16, 0.01, 0.01])
    y.iloc[4:] = 0  # unseen outer labels cannot affect selection
    assert tu.select_config("stub", configs, x, y, inner, valid) == (chosen, losses)


def test_prediction_integrity() -> None:
    """Every model shares complete finite rows and unique case/origin keys."""
    frame = pd.DataFrame({"site": ["BG", "BG"], "h": [1, 1], "origin_time": ["a", "b"],
                              "a": [0.2, 0.7], "b": [0.1, 0.9]})
    tu.validate_predictions(frame, ["a", "b"])
    with pytest.raises(ValueError, match="Duplicate"):
        tu.validate_predictions(pd.concat([frame, frame]), ["a", "b"])
    for bad in [np.nan, np.inf, -0.1, 1.1]:
        broken = frame.copy()
        broken.loc[0, "b"] = bad
        with pytest.raises(ValueError, match="Invalid"):
            tu.validate_predictions(broken, ["a", "b"])


@pytest.mark.parametrize("h", [1, 6])
def test_features_cannot_see_future(h: int) -> None:
    """Perturb future metering; features through the origin hour stay identical."""
    index = pd.date_range("2018-01-01", periods=600, freq="h")
    rng = np.random.default_rng(43)
    data = pd.DataFrame({"outage": rng.integers(0, 2, len(index)),
                         "load_kwh": rng.uniform(0, 10, len(index))}, index=index)
    changed = data.copy()
    changed.iloc[401:, 0] = 1 - changed.iloc[401:, 0]
    changed.iloc[401:, 1] += 1000
    pd.testing.assert_frame_equal(tu.features(data, h).iloc[:401],
                                  tu.features(changed, h).iloc[:401])


def test_scaler_fits_only_inner_training(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation/future extremes must not enter fitted scaling means (unitless)."""
    from sklearn.preprocessing import StandardScaler

    original = StandardScaler.fit
    means = []

    def record(self: StandardScaler, x: pd.DataFrame, *args: object,
               **kwargs: object) -> StandardScaler:
        result = original(self, x, *args, **kwargs)
        means.append(self.mean_.copy())
        return result

    monkeypatch.setattr(StandardScaler, "fit", record)
    x = pd.DataFrame({"x": [0., 1., 2., 3., 1000., 2000., 100000.]})
    y = pd.Series([0, 1, 0, 1, 0, 1, 0])
    inner = np.arange(7) < 4
    valid = (np.arange(7) >= 4) & (np.arange(7) < 6)
    tu.select_config("Logistic Regression", [{}, {"logisticregression__C": 10}],
                     x, y, inner, valid)
    np.testing.assert_allclose(means, [[1.5], [1.5]])


def test_resume_matches_uninterrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An interruption preserves completed units; assembly reads them without fitting."""
    import json

    index = pd.date_range("2018-01-01", "2018-05-31", freq="12h")
    x = pd.DataFrame({"x": np.sin(np.arange(len(index)))}, index=index)
    y = pd.Series(np.arange(len(index)) % 2, index=index)
    candidates = {"Logistic Regression": [{}]}
    full = tu.evaluate("BG", 1, x, y, candidates, tmp_path / "full", months=(4, 5))
    original = tu.select_config
    calls = []

    def interrupt(*args: object) -> tuple:
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("simulated interruption")
        return original(*args)

    monkeypatch.setattr(tu, "select_config", interrupt)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5))
    assert len(list((tmp_path / "resumed/checkpoints").glob("BG_1_4_*.json"))) == 1
    calls.clear()
    resumed = tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5))
    assert len(calls) == 1  # April was skipped; only May selected/fitted.
    for i in range(3):
        left, right = full[i], resumed[i]
        if i == 0:
            left, right = (f.drop(columns="fit_seconds") for f in (left, right))
        pd.testing.assert_frame_equal(left, right)

    def fail(*args: object) -> None:
        raise AssertionError("Completed units must never fit again")

    monkeypatch.setattr(tu, "select_config", fail)
    monkeypatch.setattr(tu, "probabilities", fail)
    repeated = tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5), read_only=True)
    for left, right in zip(resumed, repeated):
        pd.testing.assert_frame_equal(left, right)
    with pytest.raises(ValueError, match="Incompatible"):
        tu.evaluate("BG", 1, x, y, {"Logistic Regression": [{}, {}]}, tmp_path / "resumed", months=(4, 5))
    altered = y.copy()
    altered.iloc[0] = 1 - altered.iloc[0]
    with pytest.raises(ValueError, match="Incompatible"):
        tu.evaluate("BG", 1, x, altered, candidates, tmp_path / "resumed", months=(4, 5))
    checkpoint = next((tmp_path / "resumed/checkpoints").glob("BG_1_4_*.json"))
    saved = checkpoint.read_text()
    envelope = json.loads(saved)
    envelope["payload"]["status"] = "incomplete"
    envelope["sha256"] = tu.digest(envelope["payload"])
    checkpoint.write_text(json.dumps(envelope))
    with pytest.raises(ValueError, match="Invalid checkpoint"):
        tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5), read_only=True)
    checkpoint.write_text('{"broken":')
    with pytest.raises(ValueError, match="Invalid checkpoint"):
        tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5), read_only=True)
    checkpoint.unlink()
    with pytest.raises(ValueError, match="Missing checkpoint"):
        tu.evaluate("BG", 1, x, y, candidates, tmp_path / "resumed", months=(4, 5), read_only=True)


def test_typed_parameters_and_strict_json(tmp_path: Path) -> None:
    """None and the dimensionless XGBoost NaN sentinel retain distinct semantics."""
    import json

    from xgboost import XGBClassifier

    params = tu.json_params(tu.estimator("Decision Tree", {"max_depth": None}, 1))
    path = tmp_path / "params.json"
    tu.atomic_json(path, params)
    restored = tu.restore_params(json.loads(path.read_text()))
    assert restored["max_depth"] is None
    assert tu.estimator("Decision Tree", restored, 1).max_depth is None
    params = tu.json_params(tu.estimator("XGBoost", {}, 0))
    tu.atomic_json(path, params)
    restored = tu.restore_params(json.loads(path.read_text()))
    assert np.isnan(XGBClassifier(**restored).missing)
    for bad in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError):
            tu.atomic_json(path, {"required": bad})
        with pytest.raises(ValueError):
            tu.digest({"required": bad})


def test_failed_candidate_nullable_auc_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed fits consume budget; single-class outer AUC is null, never a fake score."""
    import json

    index = pd.date_range("2018-01-01", "2018-04-30", freq="12h")
    x = pd.DataFrame({"x": np.sin(np.arange(len(index)))}, index=index)
    y = pd.Series(np.arange(len(index)) % 2, index=index)
    y.loc[index.month == 4] = 0
    configs = {"Decision Tree": [{"max_depth": -1}, {"max_depth": None}, {"max_depth": None}]}
    full = tu.evaluate("BG", 1, x, y, configs, tmp_path, months=(4,))
    path = next((tmp_path / "checkpoints").glob("BG_1_4_*.json"))
    envelope = json.loads(path.read_text(), parse_constant=lambda v: pytest.fail(v))
    unit = envelope["payload"]
    assert unit["chosen"] == 1
    assert unit["losses"][0] is None
    assert unit["candidate_records"][0]["status"] == "failed"
    assert unit["candidate_records"][0]["stage"] == "fit"
    assert unit["metrics"]["auc"] is None
    assert unit["metrics"]["auc_reason"]

    def fail(*args: object) -> None:
        raise AssertionError("Must not fit completed units")

    monkeypatch.setattr(tu, "select_config", fail)
    resumed = tu.evaluate("BG", 1, x, y, configs, tmp_path, months=(4,), read_only=True)
    for a, b in zip(full, resumed):
        pd.testing.assert_frame_equal(a, b)
    unit["chosen"] = 0
    envelope["sha256"] = tu.digest(unit)
    tu.atomic_json(path, envelope)
    with pytest.raises(ValueError, match="invalid selection"):
        tu.evaluate("BG", 1, x, y, configs, tmp_path, months=(4,), read_only=True)


@pytest.mark.parametrize("failure", ["all", "refit", "undefined"])
def test_failed_unit_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    """No eligible loss or a selected refit failure prevents successful assembly."""
    import json

    index = pd.date_range("2018-01-01", "2018-04-30", freq="12h")
    x = pd.DataFrame({"x": np.arange(len(index))}, index=index)
    y = pd.Series(np.arange(len(index)) % 2, index=index)
    configs = {"Decision Tree": [{"max_depth": -1}] if failure == "all" else [{}]}
    if failure == "undefined":
        monkeypatch.setattr(tu, "brier_score_loss", lambda *args: np.nan)
    if failure == "refit":
        from sklearn.tree import DecisionTreeClassifier
        original = DecisionTreeClassifier.fit

        def fit(self: object, xx: pd.DataFrame, yy: pd.Series) -> object:
            if xx.index.max().month == 3:
                raise ValueError("outer failure")
            return original(self, xx, yy)

        monkeypatch.setattr(DecisionTreeClassifier, "fit", fit)
    with pytest.raises(ValueError, match="Failed unit"):
        tu.evaluate("BG", 1, x, y, configs, tmp_path, months=(4,))
    path = next((tmp_path / "checkpoints").glob("BG_1_4_*.json"))
    unit = json.loads(path.read_text())["payload"]
    assert unit["status"] == "failed"
    assert unit["reason"]
    if failure != "refit":
        assert unit["losses"] == [None]
    with pytest.raises(ValueError, match="Invalid checkpoint"):
        tu.evaluate("BG", 1, x, y, configs, tmp_path, months=(4,), read_only=True)

@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nonfinite_prediction_candidate_is_failed(monkeypatch: pytest.MonkeyPatch, bad: float) -> None:
    """Nonfinite probability cannot become a nullable successful loss."""
    x = pd.DataFrame({"x": [0, 1, 2, 3]})
    y = pd.Series([0, 1, 0, 1])

    class Stub:
        def fit(self, xx: pd.DataFrame, yy: pd.Series) -> None:
            pass

        def predict_proba(self, xx: pd.DataFrame) -> np.ndarray:
            return np.full((len(xx), 2), bad)

    monkeypatch.setattr(tu, "estimator", lambda *args: Stub())
    chosen, records = tu.select_config("stub", [{}], x, y, np.arange(4) < 2, np.arange(4) >= 2)
    assert chosen is None
    assert records[0]["status"] == "failed"
    assert records[0]["loss"] is None
    assert records[0]["stage"] == "prediction"


def test_float32_checkpoint_metrics_match_json() -> None:
    """Stored ancillary metrics use JSON's float64 reconstruction, not float32 rounding."""
    import json

    p = np.array([0.12345, 0.98765, 0.45678], dtype=np.float32)
    y = np.array([0, 1, 0])
    restored = np.asarray(json.loads(json.dumps(p.tolist(), allow_nan=False)))
    assert tu.nullable_scores(y, p) == tu.nullable_scores(y, restored)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_undefined_loss_excluded_with_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: float,
) -> None:
    """Undefined dimensionless Brier consumes one draw without defeating a valid draw."""
    import json

    x = pd.DataFrame({"x": [0., 1., 2., 3.]})
    y = pd.Series([0, 1, 0, 1])
    losses = iter([bad, 0.25])
    monkeypatch.setattr(tu, "brier_score_loss", lambda *args: next(losses))
    chosen, records = tu.select_config(
        "Decision Tree", [{}, {}], x, y, np.arange(4) < 2, np.arange(4) >= 2,
    )
    assert chosen == 1
    assert records[0]["loss"] is None
    assert records[0]["status"] == "failed"
    assert records[0]["stage"] == "validation_brier"
    assert records[0]["reason"] == "ValueError: Nonfinite validation Brier"
    path = tmp_path / "selection.json"
    tu.atomic_json(path, {"chosen": chosen, "records": records})
    assert json.loads(path.read_text(), parse_constant=lambda v: pytest.fail(v))["records"] == records


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_unknown_nonfinite_parameter_rejected(bad: float) -> None:
    """Only the documented XGBoost missing sentinel may bypass finite parameter checks."""
    with pytest.raises(ValueError):
        tu.json_params(tu.estimator("Decision Tree", {"max_depth": bad}, 1))


@pytest.mark.parametrize("label", [0, 1])
def test_single_class_auc_only_is_nullable(label: int) -> None:
    """Either single-class target leaves Brier defined and AUC explicitly unavailable."""
    y = np.full(4, label)
    p = np.array([0.1, 0.3, 0.6, 0.8])
    metrics = tu.nullable_scores(y, p)
    assert metrics["auc"] is None
    assert metrics["auc_reason"]
    assert metrics["brier"] == pytest.approx(np.mean((y - p) ** 2))
    assert all(np.isfinite(metrics[key]) for key in tu.METRICS if key != "auc")
