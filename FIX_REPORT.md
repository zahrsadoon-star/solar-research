# Fix report — 20261021-s1-wp1-data

Status: partial; do not approve WP1 as complete.

## MUST-FIX disposition

1. BLOCKED: NASA POWER CSV absent from data/raw/; repository filename search found no alternative. Actual schema/units cannot be verified. Full loader and temperature figure/table remain incomplete. Removed acceptance-test skip so missing weather now fails explicitly. Lead must supply file, followed by schema inspection, implementation and rerun. No guessed schema, network use or fabricated data.
2. RESOLVED via uncertainty policy: target is generator operation, a proxy for national-grid unavailability. Source labels and four disagreements retained. Generator agreement is not independent validation. No adjudication without independent evidence. Policy recorded in loader/audit, generated summary, study plan and results README.
3. RESOLVED: replaced unsupported causal assertion with association hypothesis; descriptive scatter cannot establish causality.

## Other review items

- Audited time-only clocks: 7,682 mismatches, each saved. All observed time-only clocks are midnight. Agreement rates explicitly conditional on row order; grid-energy/full-datetime checks retained.
- Enforced Weibull location zero, linear quantiles and 300 dpi.
- Recorded tested dependency pins in requirements-s1.txt (Python 3.12.15).
- Removed timedelta deprecation warnings using explicit seconds.
- Preserved forecast feature restrictions; deferred numerical tuning budgets, search spaces, selection rules, fallbacks, ablations and dependence-aware inference to WP2 protocol approval.

## Checks

- python scripts/s1_eda.py --outage-only: succeeded; regenerated summary, tables, two PNGs. 1,064 events and 4,324 proxy hours; workbook events agree.
- python -m pytest -q: 27 passed, 1 failed, no skips/warnings. Sole failure: test_complete_dataset_contract (missing weather).
- git diff --check: passed. Tracked data/ and legacy/ diffs empty. No commit/push.
- Earlier STATS_REPORT.md is historical, not full WP1 acceptance evidence.

## Files touched

src/outage/data.py; scripts/s1_eda.py; tests/test_outage_data.py; tests/test_s1_eda.py; studies/S1_outage_forecasting/PLAN.md; requirements-s1.txt; results/S1/README.md; results/S1/eda/summary.json; results/S1/eda/tables.csv; results/S1/eda/outage_hour_month.png; results/S1/eda/outage_duration.png; FIX_REPORT.md; CODEX_REPORT.md. Unrelated existing changes retained.

The sandbox rejected the requested .agents/FIX_REPORT.md write because .agents/ is protected/read-only. This root-level report is the fallback; no permissions bypass was attempted.
