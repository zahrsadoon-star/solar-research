# Decisions (Zaher)

## 2026-10-21
- **S1 approved and reshaped by Zaher:** a benchmark of **10+ algorithms for forecasting national-grid outages** on the
  Baghdad data (the thesis already had an RF outage model; now compare many methods properly), then show what the
  forecasts are worth for battery dispatch / sizing. Plan: `studies/S1_outage_forecasting/PLAN.md`.
- **S2-S5 deferred**, to be started one at a time after S1 reaches a full draft.
- Fix the legacy PV model before any PV-dependent work: azimuth (PVGIS 0° = South -> pvlib 180°) and UTC -> Baghdad
  local time (+3 h). Done in `solar-sizing-tool/notebooks/thesis_model_corrected.ipynb`.
- Workflow: each study ends with a manuscript draft; then the next study starts.

## 2026-10-21 (lead decision, Zaher asked Claude to decide)
- **Datasets:** one paper per study, not one paper per house. S1 uses **BG (Baghdad) as primary and KR (Karbala) as a
  second site** with a different outage regime; this makes one stronger paper than two thin ones. **BS (Basra)** had a
  24-h grid supply and no outages, so it is kept for later sizing studies as a reliable-grid contrast case.
- S1 pilot (studies/S1_outage_forecasting/pilot/REPORT.md): forecasting criterion met at both sites -> GO.

## 2026-10-22 (lead decisions, protocol v1.0-rc)
- S1 primary outage label = grid_kwh == 0 (closest observable to grid unavailability); generator > 0 (thesis label) is a pre-registered sensitivity. BG differs in 4 h only.
- Q1 confirmatory test two-sided with Holm over 5 horizons; exploratory comparisons get effect sizes + CIs, no p-values.
- Dispatch (RQ3) objective = LPSP + lambda x battery ageing (Naumann LFP calendar model + throughput cycle term), primary pair = forecast policy vs best ex-ante no-forecast policy; ageing equations hashed as an addendum by day 8.
- Framing pending Zaher: given Mohammed et al. 2026 and Jawad & Al-Shammari 2025, S1 is framed as a calibrated benchmark vs strong baselines + decomposition of dispatch value (a negative result is publishable).
