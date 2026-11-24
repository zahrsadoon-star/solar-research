"""PV generation model for the research studies (rewritten, not copied from the thesis notebook).

Why a new model: the thesis notebook (a) passed the PVGIS azimuth (0 deg = South) straight to pvlib, whose
convention is 180 deg = South, so the array faced North, and (b) placed UTC weather on the Baghdad-local load index
without the +3 h shift. Studies on 2018 outages also need weather from **the same year** as the load/outage record,
not a typical meteorological year. This module therefore:

1. uses measured-year 2018 hourly weather (NASA POWER, already converted to Baghdad local time),
2. works with a timezone-aware index (Etc/GMT-3 = UTC+3, Iraq has no DST since 2008) so pvlib computes solar
   geometry on true UTC instants while every output stays on the local-time index of the load,
3. states the azimuth convention explicitly (pvlib: 0 = N, 90 = E, 180 = S, 270 = W) and offers a converter
   for PVGIS-style azimuths,
4. estimates the timestamp convention of the hourly data (start / middle / end of interval) from clear-sky days
   instead of assuming it,
5. lets the transposition model be chosen (isotropic, HDKR ['reindl'], Perez) for sensitivity analysis.

Equations (all per hour, units in brackets):
  Decomposition (Erbs et al., 1982):            GHI [W/m2] -> DNI, DHI [W/m2]           pvlib.irradiance.erbs
  Transposition:                                POA = beam + sky diffuse + ground-reflected  pvlib.irradiance.get_total_irradiance
  Cell temperature (NOCT / Ross model):         T_cell = T_air + (NOCT - 20) / 800 * POA  [degC]
  DC power per kWp:                             P = (POA / 1000) * (1 + gamma * (T_cell - 25)) * (1 - L)  [kW/kWp]
    gamma = temperature coefficient of Pmax [1/K], L = lumped system losses [-]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

REPO = Path(__file__).resolve().parents[2]
WEATHER_2018 = REPO / "data" / "raw" / "nasa_power_baghdad_2018_hourly_local.csv"
LOCAL_TZ = "Etc/GMT-3"   # fixed UTC+3 (POSIX sign convention: GMT-3 means UTC+3)


@dataclass(frozen=True)
class Site:
    latitude: float = 33.322535      # Baghdad house BG (Al-Shamri 2019; thesis CONFIG)
    longitude: float = 44.339421
    altitude_m: float = 34.0         # ASSUMPTION: Baghdad ~34 m a.s.l.; only affects clear-sky / airmass slightly


@dataclass(frozen=True)
class PVConfig:
    tilt_deg: float = 31.3                    # thesis value (latitude - 2 deg)
    surface_azimuth_deg: float = 180.0        # pvlib convention: 180 = due South
    transposition: str = "reindl"             # 'isotropic' | 'reindl' (HDKR) | 'haydavies' | 'perez'
    albedo: float = 0.25                      # ASSUMPTION: dry urban/desert ground
    noct_c: float = 45.0                      # thesis CONFIG 'pv_noct' (LONGi Hi-MO X10 datasheet to verify)
    gamma_pmax_per_k: float = -0.0026         # thesis CONFIG 'pv_temp_coeff_pmax' (datasheet to verify)
    system_losses: float = 0.0                # lumped soiling/wiring/mismatch; 0 = same as thesis, vary in sensitivity
    timestamp_offset_min: float | None = None # None = estimate from data (see estimate_timestamp_offset)


def pvgis_to_pvlib_azimuth(pvgis_azimuth_deg: float) -> float:
    """Convert a PVGIS azimuth (0 = South, East negative, West positive) to pvlib (0 = North, clockwise)."""
    return float((pvgis_azimuth_deg + 180.0) % 360.0)


def load_weather_2018(path: Path = WEATHER_2018) -> pd.DataFrame:
    """Hourly 2018 weather on a timezone-aware Baghdad-local index (8,760 rows).

    Columns: temp_air_c [degC], rel_humidity_pct [%], wind_speed_10m_ms [m/s], ghi_wm2 [W/m2].
    """
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = df.index.tz_localize(LOCAL_TZ)
    if len(df) != 8760 or df.isna().any().any():
        raise ValueError(f"weather file must have 8,760 complete rows, got {len(df)} rows")
    return df


def estimate_timestamp_offset(weather: pd.DataFrame, site: Site = Site(),
                              candidates_min: tuple[float, ...] = (-30.0, 0.0, 30.0)) -> float:
    """Which point of the hour does each hourly GHI value represent?

    For each candidate offset, compare measured GHI with Ineichen clear-sky GHI computed at (timestamp + offset)
    on the clearest 10 % of days, and return the offset with the lowest RMSE. -30 = value centred on the hour
    ending at the label (label = interval end), +30 = label is the interval start, 0 = instantaneous at the label.
    """
    loc = pvlib.location.Location(site.latitude, site.longitude, tz=LOCAL_TZ, altitude=site.altitude_m)
    daily = weather["ghi_wm2"].resample("D").sum()
    errors = {}
    for off in candidates_min:
        t = weather.index + pd.Timedelta(minutes=off)
        cs = loc.get_clearsky(t, model="ineichen")["ghi"].values
        ratio = daily / pd.Series(cs, index=weather.index).resample("D").sum()
        clear_days = ratio.nlargest(max(1, len(ratio) // 10)).index
        mask = weather.index.normalize().isin(clear_days)
        errors[off] = float(np.sqrt(np.mean((weather["ghi_wm2"].values[mask] - cs[mask]) ** 2)))
    return min(errors, key=errors.get)


def plane_of_array(weather: pd.DataFrame, cfg: PVConfig = PVConfig(), site: Site = Site()) -> pd.DataFrame:
    """Plane-of-array irradiance [W/m2] on the local-time index of `weather`.

    Solar geometry is evaluated at the representative instant of each interval (timestamp + offset); because the
    index is timezone-aware, pvlib converts to UTC internally, which is what removes the thesis's 3-hour shift.
    """
    off = cfg.timestamp_offset_min
    if off is None:
        off = estimate_timestamp_offset(weather, site)
    t = weather.index + pd.Timedelta(minutes=off)
    solpos = pvlib.solarposition.get_solarposition(t, site.latitude, site.longitude, altitude=site.altitude_m)
    ghi = weather["ghi_wm2"].clip(lower=0).values
    zen = solpos["zenith"].values
    dni_extra = pvlib.irradiance.get_extra_radiation(t).values
    erbs = pvlib.irradiance.erbs(ghi, zen, t.dayofyear)
    dni = np.nan_to_num(np.asarray(erbs["dni"], dtype=float))
    dhi = np.nan_to_num(np.asarray(erbs["dhi"], dtype=float))
    kwargs = {}
    if cfg.transposition in ("reindl", "haydavies", "perez"):
        kwargs["dni_extra"] = dni_extra
    if cfg.transposition == "perez":
        kwargs["airmass"] = pvlib.atmosphere.get_relative_airmass(solpos["apparent_zenith"].values)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=cfg.tilt_deg, surface_azimuth=cfg.surface_azimuth_deg,
        solar_zenith=solpos["apparent_zenith"].values, solar_azimuth=solpos["azimuth"].values,
        dni=dni, ghi=ghi, dhi=dhi, albedo=cfg.albedo, model=cfg.transposition, **kwargs)
    out = pd.DataFrame({k: np.nan_to_num(np.asarray(poa[k], dtype=float)) for k in
                        ["poa_global", "poa_direct", "poa_diffuse"]}, index=weather.index)
    out["dni_wm2"], out["dhi_wm2"], out["solar_zenith_deg"] = dni, dhi, zen
    out.attrs["timestamp_offset_min"] = off
    return out


def pv_power_per_kwp(weather: pd.DataFrame, cfg: PVConfig = PVConfig(), site: Site = Site()) -> pd.Series:
    """Hourly DC output [kW per kWp installed] on the local-time index (equations in the module docstring)."""
    poa = plane_of_array(weather, cfg, site)
    g = poa["poa_global"].clip(lower=0)
    t_cell = weather["temp_air_c"] + (cfg.noct_c - 20.0) / 800.0 * g
    p = (g / 1000.0) * (1.0 + cfg.gamma_pmax_per_k * (t_cell - 25.0)) * (1.0 - cfg.system_losses)
    s = p.clip(lower=0).rename("pv_kw_per_kwp")
    s.attrs["timestamp_offset_min"] = poa.attrs["timestamp_offset_min"]
    return s


def legacy_style_poa(weather: pd.DataFrame, cfg: PVConfig = PVConfig(), site: Site = Site()) -> pd.Series:
    """Reproduces the two thesis defects on the same weather, for comparison only.

    1. Azimuth 0 passed to pvlib -> array faces North.
    2. Time base: the thesis computed irradiance on UTC instants but placed it on the local load clock, so the value
       shown at local hour t is the one that really belongs to local hour t + 3 (PV peak appears ~3 h early).
    """
    bad = PVConfig(**{**cfg.__dict__, "surface_azimuth_deg": 0.0})
    poa = plane_of_array(weather, bad, site)["poa_global"].values
    return pd.Series(np.roll(poa, -3), index=weather.index, name="poa_global_legacy")
