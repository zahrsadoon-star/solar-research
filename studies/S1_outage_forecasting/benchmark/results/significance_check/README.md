# S1 frozen-forecast significance check

Run offline from the repository root with `D:\SolarProject\venv312\Scripts\python.exe`
(the commands below abbreviate that interpreter as `python`):

```powershell
python studies/S1_outage_forecasting/benchmark/significance_check/check.py
python agent_notes/S1_bench_step1_fix2/statistical_audit.py
python agent_notes/S1_bench_step1_fix2/training_seed_audit.py
python -m pytest -q --basetemp=D:\SolarProject\tmp\pytest\fix2sig
python -m ruff check
```

If sandbox permissions prevent the prescribed temporary directory, a diagnostic
run uses `--basetemp=agent_notes/S1_bench_step1_fix2/fixer_pytest_tmp`. This does
not substitute for the required external-directory or post-merge acceptance run.
No package installation or network access is needed.

## What was run

The primary check consumes frozen `../hourly_predictions_top6.csv.gz` and
`../../significance_check/config.json`, not newly fitted forecasts. It compares
all 15 pairs of six shortlisted models in each BG/KR, 1/6-hour case using paired
24-hour moving-block bootstrap (2,000 draws, seed 42), Brier and AUC percentile
intervals, HAC/HLN Brier tests and within-case Holm adjustment. A competitor is
excluded only when its comparison with the lowest-Brier model meets both the
adjusted significance and directional Brier-interval criteria. Non-rejection
is not equivalence. `pairs.csv`, `brier_intervals.png` and `manifest.json` record
the outputs and provenance. The generated
[comparison](../../significance_check/COMPARISON.md) compares against cec3552.

The supplementary bootstrap audit replays the same implementation with seeds
42/43, retains every comparison, and checks metrics against the score table at
`cec3552fc9d739c3c08204d7eb70c22c84cbd70f`. It checks replay consistency and
Monte Carlo stability, not independent implementation correctness. The separate
April-only training audit fits RF and Extra Trees with seeds 42/43, both sites
and horizons, using source pinned to that same revision. Both audit summaries
under `statistical_audit/` record source/data hashes and package versions.
This supplementary refitting was an exploratory deviation from the no-refitting
protocol, documented retrospectively on 2026-11-24 in `agent_notes/PLAN.md`;
there is no evidence that its selection was prespecified.

## Findings and weaknesses

- BG 1 h differs from cec3552: this check retains Gradient Boosting in the top
  group. Block length, HAC/HLN choices and multiplicity families differ jointly;
  no single choice has been isolated as the cause.
- BG 6 h agrees: Extra Trees, RF, Logistic Regression and Gradient Boosting.
- KR 1 h agrees: RF, CatBoost, Extra Trees, XGBoost and LightGBM.
- KR 6 h agrees: all six shortlisted algorithms.

RF and Extra Trees remain statistically indistinguishable under this decision
rule. Seed-43 resampling changes no pair decisions. April training retains the
RF/Extra Trees ordering across the two seeds, but both models have zero KR recall
and F1 at both horizons and seeds. This negative result limits practical outage
detection claims. One fold and two models cannot establish full-benchmark
training stability; bootstrap replicates are not independent training runs.

The shortlist was test-selected, tuning budgets differ, baseline probabilities
are absent, and the frozen benchmark has only one training seed. Dependence
sensitivity to longer blocks and other HAC bandwidths remains untested. Shared
training sets, seasonal variation, rounded probabilities, class imbalance and
one year per household further limit inference. Source-level leakage checks do
not establish historical training provenance. Completed-hour meter readings
must actually be available at forecast issuance; their latency is unknown.
Methodological citations remain [UNVERIFIED] pending source verification.

## Integration and acceptance

The refreshed manifest reports actual Git ancestry and main-blob matches. Main
integration remains blocked by permission to create shared `ORIG_HEAD.lock`
outside this workspace. Existing published branch results were preserved, but
this is not equivalent to integrating every main result. Repository-wide Ruff
also includes failures in protected `legacy/` and other files outside the allowed
repair scope. See `agent_notes/FIX_REPORT.md` for exact acceptance outcomes.
