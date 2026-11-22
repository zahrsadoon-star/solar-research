# Statistician review — Step 2 continuation

The restricted K=1 results reproduce to floating-point precision. This does not
validate tuned rankings: the full grid was deliberately not run. The literal LR
sanity gate remains failed, and repository-wide Ruff and the requested merge remain
blocked as described below. No production seed, search space or model was changed.

## Evidence and reproduction

Read PROJECT_CONTEXT.md, AGENTS.md, current and committed original PLAN.md, prior
implementation/run/sanity notes, the earlier statistical verification, tuning.py,
benchmark.py, significance.py and tuning tests. Existing uncommitted implementation
and artifacts were preserved; this review is not blinded to previous results.

`agent_notes/S1_bench_step2/statistical_audit.py` recomputes all six pooled metrics
from saved K=1 predictions. All agree with saved results within 1e-12. Evidence is
under `studies/S1_outage_forecasting/benchmark/results/tuning/statistical_audit/`:
`pooled_metric_checks.csv`, `seed42_repeat_checks.csv`, `seed_metrics.csv`,
`seed_43_minus_42.csv`, `seed_predictions.csv.gz`, `class_prevalence.csv` and
`audit_summary.json`. These are diagnostic artifacts, not completed tuning results.

The fresh default-only BG, h=1 run uses all nine outer months, seeds 42 and 43,
and unchanged LR/RF hyperparameters. K=1 needs no candidate choice; this diagnostic
refits only the outer models, while the existing sanity checkpoints retain the
original inner validation work. Random-state parameters alone are set to each
diagnostic seed, including LR's otherwise unused lbfgs random-state setting.
Production seed 42 and its checkpoint manifests are untouched. BLAS/OpenMP limits
are one; default RF n_jobs=-1 is retained.

Seed 42 reproduces saved probabilities with maximum absolute differences of
1.11e-16 (LR) and 4.44e-16 (RF); origin times and truth match exactly.
Between seeds 43 and 42, LR's six metrics are unchanged. RF changes are:

| Metric | Seed 43 minus seed 42 |
|---|---:|
| Accuracy | +0.000909229 |
| Precision | +0.001422856 |
| Recall | -0.000281690 |
| F1 | +0.000642438 |
| AUC | -0.000538528 |
| Brier | +0.000261169 |

These small changes support stability only for this limited default-model check.
No equivalence test or predeclared seed-stability margin exists. Two seeds do not
establish robustness for all sites, horizons or tuned models. The prior broader
review in `agent_notes/S1_bench_verify/STATS_REPORT.md` already reports greater
KR h=6 F1 sensitivity; that case was not rerun here.

SANITY.md correctly distinguishes full-precision differences from four-decimal
agreement against benchmark_results.csv. All six literal LR 1e-9 comparisons fail,
although all six agree after four-decimal rounding. RF's absolute Brier difference
is about 0.000285669, below 0.005; its discrepancy exceeds rounding alone and its
cause is unresolved. Fresh seed-42 reproduction does not identify the historical
RF discrepancy's cause. No tolerance was relaxed.

## Leakage and imbalance

Source inspection and automated tests confirm outer training origins AND target
times precede the test boundary. Inner training origins AND targets precede the
validation boundary; validation targets precede the outer test boundary. The
eligibility mask drops unavailable year-end labels and incomplete feature rows.
Features use trailing observations through the completed origin hour; target-hour
calendar features are known in advance. This requires actual availability of
current-hour metering. Test-month feature histories may update as observations
arrive, while each fitted model remains fixed for that month.

Added future-perturbation tests at h=1 and h=6 confirm that changing later metering
cannot alter earlier features. An instrumented scaler test confirms that inner
validation/future extremes cannot enter training means. Existing tests check
default identity, frozen candidate draws, both temporal boundaries, minimum-loss
selection and first-index ties, finite/shared prediction rows, and interrupted
versus uninterrupted outputs with completed units skipped and invalid units rejected.

Class counts and prevalence are saved for every inner, validation, outer and test
split across both sites and horizons. All inspected splits contain both classes.
There is substantial seasonal imbalance, particularly at KR. No weighting,
resampling or threshold optimization was added: preserving defaults is the design.
Use Brier together with precision, recall, F1, AUC and the existing references;
accuracy alone is inadequate. Pooled metrics do not establish minority-class
utility or probability calibration. Class prevalence is not stationary merely
because both classes occur in every split.

MLP early stopping and SVM probability calibration retain benchmark-internal
non-temporal splits. They stay within the outer/inner training data but do not
provide purely forward validation internally. The copied random-split accuracy
is default-only retrospective context, not prospective forecasting evidence.

## Statistical inference and multiplicity

Step 2 performs no inferential tests. Tolerances and rankings are descriptive;
neither requires a p-value correction nor establishes significance or equivalence.
Hourly losses are serially dependent, monthly folds share training data, and
seasonal drift limits stationarity assumptions. Folds are not independent seeds.

Read-only inspection of significance.py confirms Step 1 uses a two-sided
normal-approximation Diebold–Mariano statistic with Newey–West lag 24, Holm within
each site/horizon, and a seven-day moving-block bootstrap with 2,000 replicates.
Holm's implementation sorts p-values, takes monotone running maxima and caps at
one; its family is within-case, not the combined study. HAC and block resampling
address some temporal dependence but their fixed lag/block choices do not prove
adequacy under seasonality. Zero long-run variance is not explicitly guarded in
dm_test. Reference model/top-six selection on the same evaluation outcomes adds
selection uncertainty not removed by within-case Holm. Bootstrap intervals are
pointwise, not simultaneous. No new p-values or significance outputs were generated;
these observations do not constitute empirical validation of Step 1 assumptions,
and none of its conclusions transfers automatically to tuned models.

## Execution constraints and handoff

The required `git merge origin/main` was attempted before edits; Git failed to
create ORIG_HEAD.lock in worktree metadata outside the writable repository.
No merge, commit, push, installation or network operation succeeded or was bypassed.

The existing resumable implementation, cleanup and timing-probe rename were
reviewed. K=8 and the sequential runtime estimate of about 8.40 hours remain frozen;
no permitted K meets the 80-minute budget. RUN.md contains the full command and
parallel-runtime caveats. No performance result was used to change this decision.

Validation command outcomes are recorded in CODEX_REPORT.md and the fresh
pytest_stats.log / ruff_stats_repository.log files. Repository-wide Ruff reports
pre-existing violations, including explicitly protected files; this review does
not change protected code or suppress those failures. benchmark.py, significance.py,
legacy/ and data/ were not edited.
