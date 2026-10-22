"""Typed configuration; numerical defaults live only in the frozen YAML."""
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/S1_frozen.yaml"

@dataclass(frozen=True)
class Config:
    """Study choices; h fields use hours and day fields use days."""
    label: str
    sensitivity_label: str
    hour_convention: str
    issuance_offset_h: int
    horizons: list[int]
    horizons_b: list[int]
    first_test_month: int
    last_test_month: int
    purge_h: int
    season_h: int
    label_lags: list[int]
    count_windows_h: list[int]
    change_window_h: int
    share_window_h: int
    weather_lags_h: list[int]
    weather_mean_h: int
    friday: int
    calendar_path: str
    prior: float
    climatology_method: str
    window_days: list[int]
    minimum_daily_samples: int
    markov_min_cell: int
    models: list[str]
    evaluation_seeds: list[int]
    tuning_seed: int
    sampler_seed: int
    retune_folds: list[int]
    trials: int
    startup_trials: int
    logistic_C: list[float]
    logistic_penalties: list[str]
    logistic_max_iter: int
    logistic_tol: float
    smoke_trials: int
    selection_tolerance: float
    logloss_clip: float
    ece_bins: int
    alpha: float
    bootstrap_B: int
    smoke_B: int
    bootstrap_seed: int
    block_default_h: int
    block_min_h: int
    block_max_h: int
    block_round_h: int
    hac_method: str
    hac_sensitivities_h: list[int]
    fixed_b_coefficients: list[float]
    q1_hypotheses: list[str]
    random_test_fraction: float
    random_seeds: list[int]
    threshold_rule: str
    pr_auc: str
    seed_precision: float
    initial_seeds: int
    max_tree_seeds: int
    max_deep_seeds: int
    timing_cap_multiplier: int
    ar1_seed: int
    ar1_rho: float
    ar1_n: int
    ar1_burnin: int
    ar1_replications: int
    ar1_B: int
    ar1_coverage_min: float
    ar1_coverage_max: float
    causality_origins: int
    hour_evidence_path: str
    timing_caps_path: str

@lru_cache(maxsize=8)
def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load and validate study configuration without repeatedly reading disk."""
    c = Config(**yaml.safe_load(path.read_text()))
    if c.purge_h < max(c.horizons): raise ValueError("Purge shorter than maximum horizon")
    if c.hour_convention != "hour_beginning": raise ValueError("Unsupported hour convention")
    if c.tuning_seed in c.evaluation_seeds: raise ValueError("Tuning seed cannot be evaluated")
    if len(c.evaluation_seeds) != 1: raise ValueError("Reference models are deterministic: one evaluation seed required")
    return c
