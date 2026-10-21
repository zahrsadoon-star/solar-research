# Decisions (Zaher)

## 2026-10-21
- **S1 approved and reshaped by Zaher:** a benchmark of **10+ algorithms for forecasting national-grid outages** on the
  Baghdad data (the thesis already had an RF outage model; now compare many methods properly), then show what the
  forecasts are worth for battery dispatch / sizing. Plan: `studies/S1_outage_forecasting/PLAN.md`.
- **S2-S5 deferred**, to be started one at a time after S1 reaches a full draft.
- Fix the legacy PV model before any PV-dependent work: azimuth (PVGIS 0° = South -> pvlib 180°) and UTC -> Baghdad
  local time (+3 h). Done in `solar-sizing-tool/notebooks/thesis_model_corrected.ipynb`.
- Workflow: each study ends with a manuscript draft; then the next study starts.
