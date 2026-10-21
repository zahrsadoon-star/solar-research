# Thesis reference results (frozen)

Source: `legacy/thesis_model.ipynb` (copied from `my_final_final_final.ipynb`, 2026-05-20).
These are the values reported in the MSc thesis. They are the regression baseline:
refactored code must reproduce them (within the tolerance stated in the test) or the
difference must be explained in CHANGELOG.md.

| Quantity | Value |
|---|---|
| PV array | 23 panels, 15 kWp |
| Battery | 30.6 kWh |
| Inverter | 10 kW |
| LPSP | 0.65 % |
| LCE | 0.0715 USD/kWh |
| Payback period | 6 years |
| TCOP | 27,255 USD |

Site/data: residential building, Baghdad; hourly load `data/BG1-8760.xlsx` (8,760 h).
EMS: Mode 0 (grid charges battery when SOC < 80 %). Optimiser: GNPSO (GA + PSO hybrid).
Known issue: equations document cites HDKR transposition; code uses pvlib isotropic (Liu-Jordan).

## Status after 2026-10-21 audit
These values were produced by legacy code with two PV-model defects (array facing North; UTC weather on a local-time load). They are kept as the historical thesis baseline. A corrected baseline will be computed with notebooks/thesis_model_corrected.ipynb and the package, and reported side by side.
