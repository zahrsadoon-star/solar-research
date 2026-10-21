# Changelog

## 2026-10-21 - Project created
- Repository scaffolded; thesis notebook and Baghdad 8,760-h load data copied as baseline.
- Research roadmap and integrity rules for agents added.

## 2026-10-21 - Data, context, agents
- data/BG1-8760.xlsx replaced by the 4-column version the thesis Colab actually used (OneDrive/Drive copy); all datasets added under data/raw/ with MANIFEST.json.
- PROJECT_CONTEXT.md added (read first). agents/ added: five-agent Codex pipeline.
- Found two PV-model defects in legacy code (North-facing azimuth, UTC vs local time): annual POA 1,410 -> 2,097 kWh/m2 after correction.
- DECISIONS.md: S1 (outage-forecasting benchmark, 10+ models) approved; studies/S1_outage_forecasting/PLAN.md.

## 2026-10-21 - Research PV model (Claude, cloud session)
- New src/pv/model.py built for the studies (not copied from the notebook): 2018 NASA POWER weather, explicit pvlib azimuth (180 = South), timezone-aware Baghdad time, hour convention estimated from clear days (+30 min), selectable transposition (default HDKR). 9 tests pass.
- results/pv: corrected annual POA 2,017 kWh/m2 (HDKR); thesis-style defects give 1,321 (-34.5 %) and a PV peak 3 h early.
