# Statistician review: S1 WP1

The outage-only EDA is reproducible; WP1 remains incomplete because
`data/raw/nasa_power_baghdad_2018_hourly_local.csv` is absent. The complete
loader, weather alignment and temperature figure remain unverified.

## Verification

Read PROJECT_CONTEXT.md, AGENTS.md, study PLAN.md and existing agent notes;
inspected real workbook sheets, columns and sample records. Ran
`python scripts/s1_stats_check.py`: reruns EDA with seeds 0 and 17, counts
raw-label runs independently with itertools.groupby, and reconciles monthly
and hourly denominators/totals. Evidence: `results/S1/stats_audit.json`,
`results/S1/eda/`, and `results/S1/stats_seed17/`.

All summary fields except configuration match; tables.csv is byte-identical.
This is deterministic reproducibility, not independent statistical replication
or out-of-sample stability.

- 8,760 rows; 4,324 outage hours; outage share 0.49360730593607305.
- 1,064 events; mean 4.06390977443609 h. Workbook event records and summaries agree.
- National-status agreement 0.9995433789954338; generator agreement 1.0;
  both cover all rows. Generator validation is not independent because the
  workbook labels are generator-derived.
- Four disagreements: local 2018-07-21 20:00/21:00 and 2018-07-22 06:00/10:00.
  All have outage=0, national status=0, grid=0 and generator=0. No labels were
  changed. Absence of generator output does not establish grid availability;
  the lead needs to resolve this operational definition before forecasting claims.
- Weibull MLE shape 1.3908196124819705, scale 4.519271344947114 h, location zero;
  1,064 included events and no boundary exclusions.

## Leakage and imbalance

The loader preserves raw energy and labels exactly (automated test). No
scaling, smoothing, learned transformation or imputation is applied. WP1 has
no forecasting feature matrix, split or scaler: future-feature availability
and train-only preprocessing cannot yet be certified. Completed-event ends
and durations use subsequent hours; they must not be forecast features.
Realized daily maximum temperature is unavailable at an earlier daily origin.
Same-hour generator/grid energy reveals label information; future energy
cannot enter predictors. Full-year calendar shares are descriptive only;
forecast climatology and preprocessing must be fitted in each training fold,
with target-boundary purging. Full-year EDA exposure must remain disclosed.

Class counts: 4,436 available, 4,324 outage; majority share 0.506392694063927.
There is no substantial overall imbalance, and no resampling/weighting in
this descriptive task. Later fold prevalence and calibration need checking;
annual balance does not imply balance in each month/hour. Weighting must
use training data only.

## Statistical assumptions and multiplicity

No inferential tests, p-values or model comparisons are produced in WP1, so
multiple-comparison adjustment is inapplicable. The Weibull is a descriptive
continuous approximation to discrete, potentially dependent durations; the
overlay is not a goodness-of-fit test. No interval or survival adequacy claim
is verified. Later seeds must not be treated as independent temporal samples.
Overlapping horizons and serial dependence require appropriate treatment in
Diebold-Mariano tests. Friedman/Nemenyi requires defensible independent blocks;
monthly folds should not automatically be assumed independent. Prespecify
comparison families and multiplicity control for model/horizon comparisons.
These remain WP2 checks, not implemented WP1 inference.

## Tests and limitations

Added independent synthetic run reconstruction at seeds 0/17, raw-value
preservation, and detection of offsetting event-reference errors even when
total hours are unchanged. Synthetic sequences are test fixtures only.
`python -m pytest -q`: 23 passed, 1 skipped (weather absent), 23 timedelta
deprecation warnings. `git diff --check` passed; tracked data/legacy diff empty.

Annual timestamps were reconstructed. Positional status alignment checks grid
energy and full datetimes; time-only entries cannot establish calendar dates.
Weather schema, units, sentinels and coverage remain unverified. No data/legacy
edits, network calls, commits or pushes.

The requested `.agents/STATS_REPORT.md` write was rejected by sandbox approval
settings because `.agents/` is read-only. This root-level report is the fallback.
