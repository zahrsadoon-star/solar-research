# Statistician review: S1 WP1 weather completion

This review supersedes the earlier missing-weather report. The requested loader,
local-hour join, temperature figure/table and housekeeping were already present
when this review began. Inspected those changes and reran the complete EDA.
FIX_REPORT.md in agent_notes/ now records the completed weather fixes and final checks.

## Reproduction and independent accounting

Ran `python scripts/s1_stats_check.py` with seeds 0 and 17, now using the complete
weather dataset rather than the obsolete outage-only path. All summary fields
except configuration match, and tables.csv is byte-identical. Evidence is in
results/S1/stats_audit.json, results/S1/eda/ and results/S1/stats_seed17/.
This is deterministic reproducibility, not independent stochastic replication
or evidence of out-of-sample stability. No forecasting experiment exists in WP1.

Independent itertools.groupby accounting confirms 4,324 positive-generator hours
in 1,064 events, share 0.49360730593607305 and mean duration 4.06390977443609 h.
Monthly/hourly denominators and totals reconcile. Independent 24-row daily
blocks confirm all 365 daily maxima, proxy-hour totals and shares, with 24 hours
per local day. Daily maximum temperature ranges from 12.1 to 49.16 degC.
These quantities are generated and stored by the audit script, not hand estimates.

## Alignment, units and unresolved labels

The loader requires exactly 8,760 ordered unique consecutive local hours of 2018,
rejects incomplete or shifted coverage and nonfinite measurements, and joins
one-to-one. Naive weather timestamps are already Baghdad local time; localization
introduces no clock shift. Tests compare every weather value against the CSV,
preserving degC, percent, m/s and W/m2 without conversion. No missing-data fill,
scaling or smoothing is performed. Metadata documents an upstream UTC-to-local
conversion; the loader correctly does not repeat it. This review checks the
supplied file, not the upstream download against NASA's remote service.

Workbook hours are constructed by position from 2018-01-01 00:00 local. Only
745 full datetimes check calendar alignment; time-only Excel cells cannot
establish dates. Their mismatches remain diagnostic, and status agreement is
conditional on row order. Existing raw-energy checks and full-datetime rejection
tests pass. The target remains generator energy > 0, a proxy, not verified grid
unavailability. Perfect generator agreement is internal consistency only.

All four disagreements remain exposed: 2018-07-21 20:00/21:00 and
2018-07-22 06:00/10:00 local. Each has source proxy=0, national status=0,
grid energy=0 and generator energy=0. No adjudication or relabeling was done.

## Leakage, imbalance and inference

WP1 has no forecasting feature matrix, scaler, training split or model selection.
No learned preprocessing leakage was found in this descriptive pipeline; future
forecasting leakage safety cannot yet be certified. Completed-event durations,
future grid/generator energy, realized daily maximum temperature and full-year
climatology must not be available to earlier forecast origins. Fit preprocessing
and climatology inside training folds, purge target overlap, and disclose full-year
EDA exposure. Observed daily maxima are valid only for this retrospective plot.

Class counts are 4,436 proxy-negative and 4,324 proxy-positive; majority share is
0.506392694063927. Overall balance needs no resampling for descriptive EDA.
Negative proxy labels do not prove grid availability. Future fold/month/horizon
prevalence, calibration and training-only weighting still require verification.

No inferential tests, p-values or model comparisons are produced, so there is no
current multiple-testing adjustment. Temperature remains an association hypothesis;
the scatter establishes neither causality nor forecast skill. The fitted Weibull
(shape 1.3908196124819705, scale 4.519271344947114 h, location zero) is a descriptive
continuous approximation to discrete and potentially serially dependent events,
not a validated survival distribution or goodness-of-fit test. All 1,064 events
are included; none touches a year boundary. For WP2, seeds are not independent
temporal samples; overlapping horizons need dependence-aware inference, and
Friedman/Nemenyi blocks cannot automatically be treated as independent months.
Prespecify comparison families and multiplicity control before model comparisons.

## Automated checks and discrepancies

Extended the daily-temperature integration test to both seeds and added explicit
local-day date and proxy-hour checks. The first run exposed a test comparison of
CSV fixed-offset timezone metadata against a named timezone; normalize both to
Asia/Baghdad before comparison. No data or join error was involved.
The old audit script would overwrite complete EDA with partial outage-only results;
fixed it and regenerated both seed outputs with weather.

Final verification results are recorded in CODEX_REPORT.md. No edits to data/ or
legacy/, no network calls, and no commits or pushes. WP2 inference and independently
verified grid labels remain outside the scope of WP1 acceptance.
