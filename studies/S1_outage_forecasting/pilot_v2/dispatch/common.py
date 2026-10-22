"""Shared constants and data loading for the S1 dispatch experiment v2.

Data (read-only, data/raw):
  BG  BG18760_with_analysis.xlsx, sheet "Hourly Data": Grid (kWh), Generator (kWh), Total (kWh)
  KR  KR-8760.xlsx, no header: column 0 = grid kWh, column 1 = generator kWh
Load [kWh per hour] = grid + generator (metered consumption; during outages it is capped by the generator
subscription, so outage-hour demand is suppressed demand - see README).

Outage labels:
  "grid0"  (primary)      outage_t = 1 if grid_kwh_t == 0
  "gen"    (sensitivity)  outage_t = 1 if generator_kwh_t > 0      (the label of the v1 pilot)

PV [kW DC] = pv_power_per_kwp (src/pv/model.py, 2018 NASA POWER Baghdad weather, timestamp offset estimated with
estimate_timestamp_offset) * installed kWp. KR uses the Baghdad weather (~80 km away) - a stated limitation.
Evaluation window: April-December 2018 (6,600 h); Jan-Mar are only used to train forecasters.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PILOT = REPO / "studies" / "S1_outage_forecasting" / "pilot"
RAW = REPO / "data" / "raw"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
for p in (str(REPO), str(PILOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

SITES = ("BG", "KR")
LABELS = ("grid0", "gen")
PRIMARY_LABEL = "grid0"
EVAL_START_MONTH = 4
H = 6                                    # forecast look-ahead [h]
SIZES = [(8.0, 10.2), (5.0, 10.2), (8.0, 20.4)]   # (PV kWp, battery kWh)
SEED = 42
YEAR_INDEX = pd.date_range("2018-01-01", periods=8760, freq="h")


@lru_cache(maxsize=None)
def load_site(site: str) -> pd.DataFrame:
    """Hourly 2018 grid/generator energy [kWh] and both outage labels for one site."""
    if site == "BG":
        bg = pd.read_excel(RAW / "BG18760_with_analysis.xlsx", sheet_name="Hourly Data")
        grid, gen = bg["Grid (kWh)"].to_numpy(float), bg["Generator (kWh)"].to_numpy(float)
        total = bg["Total (kWh)"].to_numpy(float)
        if np.abs(grid + gen - total).max() > 1e-9:
            raise ValueError("BG: Grid + Generator != Total")
    elif site == "KR":
        kr = pd.read_excel(RAW / "KR-8760.xlsx", header=None)
        grid, gen = kr[0].to_numpy(float)[:8760], kr[1].to_numpy(float)[:8760]
    else:
        raise ValueError(site)
    d = pd.DataFrame({"grid_kwh": grid, "gen_kwh": gen}, index=YEAR_INDEX)
    d["load_kwh"] = d["grid_kwh"] + d["gen_kwh"]
    d["outage_grid0"] = (d["grid_kwh"] == 0).astype(int)
    d["outage_gen"] = (d["gen_kwh"] > 0).astype(int)
    return d


def site_frame(site: str, label: str) -> pd.DataFrame:
    """Frame with column `outage` set to the requested label (and `load_kwh`), as pilot_s1.features expects."""
    d = load_site(site).copy()
    d["outage"] = d[f"outage_{label}"]
    return d


@lru_cache(maxsize=None)
def pv_unit() -> np.ndarray:
    """Hourly DC PV output [kW per kWp], 2018, Baghdad-local index (8,760 values)."""
    from src.pv.model import PVConfig, estimate_timestamp_offset, load_weather_2018, pv_power_per_kwp
    w = load_weather_2018()
    return pv_power_per_kwp(w, PVConfig(timestamp_offset_min=estimate_timestamp_offset(w))).to_numpy(float)


def eval_mask() -> np.ndarray:
    """Boolean mask of the April-December evaluation hours."""
    return YEAR_INDEX.month >= EVAL_START_MONTH


def outage_events(outage: np.ndarray, load: np.ndarray, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Contiguous outage events: start, duration [h], load during the event [kWh]."""
    o = outage.astype(int)
    starts = np.flatnonzero(np.diff(np.r_[0, o]) == 1)
    ends = np.flatnonzero(np.diff(np.r_[o, 0]) == -1)
    return pd.DataFrame({"start": index[starts], "duration_h": ends - starts + 1,
                         "load_kwh": [load[a:b + 1].sum() for a, b in zip(starts, ends)]})
