# PV model used in the research studies

Implementation: `src/pv/model.py` · tests: `tests/test_pv_model.py` · comparison: `scripts/pv_2018_compare.py`
-> `results/pv/`.

## Differences from the thesis notebook (by design, not a copy)
| Aspect | Thesis notebook | Research model | Why |
|---|---|---|---|
| Weather | PVGIS TMY (typical year, mixed years) | **NASA POWER hourly 2018** | Same year as the measured load and outage record (S1 needs this coincidence) |
| Azimuth | PVGIS value (0 = South) passed to pvlib -> **faced North** | pvlib convention stated explicitly, 180 = South; `pvgis_to_pvlib_azimuth()` for PVGIS inputs | Defect 1 |
| Time base | UTC weather placed on the local load clock -> **3 h early** | Timezone-aware index (Etc/GMT-3); pvlib works on true UTC instants, outputs stay on local time | Defect 2 |
| Hour convention | assumed instantaneous | **Estimated from clear days**: +30 min (each value = interval starting at the label) | Avoids a hidden 30-min bias |
| Transposition | isotropic in code, HDKR in the equations document | Selectable; default **HDKR ('reindl')**, others as sensitivity | Matches the written method; quantifies the choice |
| Diffuse split | given by PVGIS | Erbs decomposition of GHI | NASA hourly product used here provides GHI |

## Equations (hourly)
1. Solar position at t + Δt (Δt = +30 min): pvlib SPA (`pvlib.solarposition.get_solarposition`).
2. Decomposition (Erbs, Klein & Duffie 1982): GHI -> DNI, DHI.
3. Transposition (Reindl et al. 1990, HDKR): POA = beam + anisotropic sky diffuse + ground-reflected (albedo 0.25).
4. Cell temperature (NOCT model): T_cell = T_air + (NOCT − 20)/800 · POA, NOCT = 45 °C.
5. DC output per kWp: P = (POA/1000) · [1 + γ (T_cell − 25)] · (1 − L), γ = −0.0026 K⁻¹, L = 0 (sensitivity later).
Citations to be verified before use in a manuscript.

## Results (results/pv/pv_2018_comparison.csv)
| Case | Annual POA (kWh/m²) | Yield (kWh/kWp) | vs corrected HDKR |
|---|---|---|---|
| Corrected, isotropic | 1,970.1 | 1,826.8 | −2.3 % |
| **Corrected, HDKR** | **2,017.0** | **1,868.6** | 0 |
| Corrected, Hay-Davies | 2,011.9 | 1,864.0 | −0.3 % |
| Corrected, Perez | 2,055.4 | 1,902.0 | +1.9 % |
| Thesis defects (north + 3 h shift) | 1,321.1 | – | −34.5 % |

The transposition choice moves the result by about ±2 %; the two thesis defects move it by about −35 % and shift the
PV peak three hours earlier against the load. Open items: verify NOCT, γ and system losses against the LONGi
Hi-MO X10 datasheet; consider validating the 2018 NASA GHI against a ground station if one becomes available.
