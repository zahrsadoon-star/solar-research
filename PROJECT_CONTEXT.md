# PROJECT CONTEXT - read this first (every agent, every session)

Owner: **Zaher** (electrical engineer, MSc EE at UNITEN, Malaysia; from Nasiriyah, Iraq). Talk to him in Iraqi Arabic
(casual); code, docs and papers in English. He wants honest feedback, including about mistakes.

## The two projects
| Repo | Goal |
|---|---|
| `solar-sizing-tool` | Grow the thesis Colab code into a complete, open PV-battery sizing program for weak grids (package -> CLI -> Colab -> Streamlit app -> docs). |
| `solar-research` | Q1-target papers built on the thesis data, one study at a time: pilot -> full experiments -> draft. |

## Thesis baseline
- MSc thesis: optimal sizing of a residential PV-battery system in **Baghdad** with **GNPSO** (GA + PSO hybrid),
  Mode 0 EMS (grid charges the battery when SOC < 80 %), benchmarked against HOMER Pro.
- Reported results (`legacy/REFERENCE_RESULTS.md`): 23 x 650 W panels (~15 kWp), 30.6 kWh battery, 10 kW inverter,
  LPSP 0.65 %, LCE 0.0715 USD/kWh, payback 6 y, TCOP 27,255 USD.
- Presented at ICSEIECT 2026 (Kuala Lumpur), Best Presentation Award.

## Known defects in the legacy code (found 2026-10-21) - DO NOT reproduce them
1. **Azimuth**: PVGIS reports azimuth with 0° = South; pvlib needs 180° = South. Legacy passed 0 to pvlib -> array faced
   **North**. Effect: annual plane-of-array irradiation 1,410 instead of 2,097 kWh/m² (-33 %; the corrected value is +49 %
   over legacy).
2. **Time base**: PVGIS TMY is **UTC**; the load is **Baghdad local time (UTC+3, no DST since 2008)**. Legacy relabelled
   TMY onto the local index without shifting -> PV peak at 09:00 local instead of ~12:00.
   Correct method: solar geometry on UTC instants, then roll every weather series by +3 h onto the local index.
3. Legacy azimuth/time fixes are applied in `solar-sizing-tool/notebooks/thesis_model_corrected.ipynb` (search
   `FIX (2026-10-21)`). Numbers in REFERENCE_RESULTS.md were produced by the defective code; the corrected baseline
   must be recomputed and both kept (legacy vs corrected) for transparency.
4. Other open points (docs/legacy_map.md): economic definitions differ between stages (LCE denominator, payback),
   fitness saturation, equations document cites HDKR but code uses isotropic transposition.

## Data (`data/raw/`, manifest with sha256 in `data/raw/MANIFEST.json`)
| File | What it is |
|---|---|
| `BG1-8760.xlsx` (= `data/BG1-8760.xlsx`) | **Primary dataset** - Baghdad household, 2018, hourly, local time. Sheet1: Date & Time, National Grid (kWh), Generator (kWh), Total Load (kWh). Also Weekdays/Weekends profiles. This is the file the thesis Colab read from Drive. |
| `BG1-8760_v2026-04_homer_folder.xlsx` | Same plus sheet **National Status** (1 = national grid on). |
| `BG18760_with_analysis.xlsx` | Analysis workbook: Hourly Data with **Outage (1/0)**, hourly/monthly profiles, **Outage Events** (1,064 events, 4,324 outage h, mean 4.06 h), Thesis Check. Best source for outage forecasting. |
| `BG1-8760_v2026-03_downloads.xlsx` | Older 2-column export (load, generator). Superseded - do not use. |
| `BS-8760.xlsx`, `KR-8760.xlsx` | Two more households (2 columns, 8,760 h). City/meaning to confirm with Zaher before use. |
| `Baghdad_Grid_Reliability_HOMER.csv`, `Baghdad_Grid_RealTimeRates_HOMER.csv`, `BG1_HOMER_Load.csv`, `PV_LONGI_650W_1module_Baghdad_HOMER.csv`, `homer_pro_data_simulation.csv` | HOMER Pro inputs/outputs used for benchmarking. |
| `hourly_load_8760.csv` | NOT Baghdad (2006-2008 household dataset, starts 2006-12-16). Unrelated; ignore unless asked. |
Site: lat 33.322535, lon 44.339421. Panel: LONGi Hi-MO X10 650 W (datasheet in knowledge/thesis).

## Local-only material (not in git): `D:\SolarProject\knowledge\`
`thesis/` latest thesis chapters (docx/pdf), conference paper, Colab printout, datasheet, flowchart.
`data/` copies of all datasets + `SCHEMA_DUMP.txt` + `pvgis_tmy_baghdad.csv` (cached PVGIS TMY, UTC) + `pv_fix_effect.json`.
Thesis reference PDFs: `C:\Users\lenovo\OneDrive - Universiti Tenaga Nasional\Desktop\final thesess\references\`.

## Research decisions
See `solar-research/DECISIONS.md`. Current study: **S1 - grid-outage forecasting benchmark** (10+ algorithms) and its
value for battery dispatch/sizing. Later studies follow one by one after S1's draft.

## Conventions
- Units in names (`load_kw`, `energy_kwh`); hourly steps; local Baghdad time index for everything that meets the load.
- Every number in a paper comes from a script; fixed seeds; no invented data or citations.
- Codex agents implement on branches `codex/<task-id>`; Claude reviews and merges to `main`.
