"""Tests for src/pv/model.py - azimuth convention, local-time alignment, physical plausibility."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pv.model import (PVConfig, estimate_timestamp_offset, legacy_style_poa, load_weather_2018,  # noqa: E402
                          plane_of_array, pv_power_per_kwp, pvgis_to_pvlib_azimuth)


@pytest.fixture(scope="module")
def weather():
    return load_weather_2018()


@pytest.fixture(scope="module")
def offset(weather):
    return estimate_timestamp_offset(weather)


def test_pvgis_to_pvlib_azimuth():
    assert pvgis_to_pvlib_azimuth(0) == 180      # PVGIS south -> pvlib south
    assert pvgis_to_pvlib_azimuth(-90) == 90     # PVGIS east -> pvlib east
    assert pvgis_to_pvlib_azimuth(90) == 270     # PVGIS west -> pvlib west
    assert pvgis_to_pvlib_azimuth(180) == 0      # PVGIS north -> pvlib north


def test_weather_index_is_local_and_complete(weather):
    assert len(weather) == 8760
    assert str(weather.index.tz) == "Etc/GMT-3"
    assert weather.index[0].hour == 0 and weather.index[0].year == 2018


def test_timestamp_offset_is_a_candidate(offset):
    assert offset in (-30.0, 0.0, 30.0)


def test_south_beats_north_at_33N(weather, offset):
    south = plane_of_array(weather, PVConfig(timestamp_offset_min=offset))["poa_global"].sum()
    north = plane_of_array(weather, PVConfig(surface_azimuth_deg=0.0, timestamp_offset_min=offset))["poa_global"].sum()
    assert south > 1.3 * north


def test_pv_peak_is_around_local_noon(weather, offset):
    p = pv_power_per_kwp(weather, PVConfig(timestamp_offset_min=offset))
    # energy-weighted centre of the mean daily profile, at the instant each hourly value represents
    centroid = np.average(np.arange(24), weights=p.groupby(p.index.hour).mean().values) + offset / 60
    # Baghdad solar noon is about 12:03 local (UTC+3, 44.3 E), +/- 16 min equation of time
    assert 11.5 <= centroid <= 12.6


def test_no_generation_at_night(weather, offset):
    p = pv_power_per_kwp(weather, PVConfig(timestamp_offset_min=offset))
    assert p[(p.index.hour <= 3) | (p.index.hour >= 21)].max() == 0


def test_annual_specific_yield_plausible(weather, offset):
    y = pv_power_per_kwp(weather, PVConfig(timestamp_offset_min=offset)).sum()
    assert 1500 < y < 2200   # kWh/kWp/year, Baghdad, fixed optimal tilt


def test_temperature_derating_reduces_output(weather, offset):
    cold = pv_power_per_kwp(weather, PVConfig(gamma_pmax_per_k=0.0, timestamp_offset_min=offset)).sum()
    real = pv_power_per_kwp(weather, PVConfig(timestamp_offset_min=offset)).sum()
    assert real < cold


def test_legacy_style_is_worse_and_early(weather, offset):
    good = plane_of_array(weather, PVConfig(timestamp_offset_min=offset))["poa_global"]
    bad = legacy_style_poa(weather, PVConfig(timestamp_offset_min=offset))
    assert bad.sum() < good.sum()
    peak_good = good.groupby(good.index.hour).mean().idxmax()
    peak_bad = bad.groupby(bad.index.hour).mean().idxmax()
    assert (peak_good - peak_bad) % 24 == 3
