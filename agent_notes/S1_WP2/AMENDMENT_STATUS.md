# Amendment implementation status

1. Every evaluated candidate has a matching inner-validation parquet, including folds without retuning. Candidate selection and MCC thresholds read these files through a restricted reader. Deterministic reference models use the configured single evaluation seed; tuning uses its separate seed.
2. Test 4 independently checks static-reference invariance and causal updating baselines across all requested horizons and classification targets. Future-label perturbations cannot change the forecast at the current row.
3. Implemented persistence, seasonal-naive, static and trailing climatology, hour-inhomogeneous Markov, midnight-updated recency Markov, and logistic. Window candidates are retained. Strongest selection uses validation Brier; both pooled skill references are reported. Pool explicitly incomplete until later work packages.
4. YAML contains label definitions, issuance convention, horizons, feature windows, priors, candidate windows, tuning/seeds, clipping, bootstrap settings and HAC choices. Corrected circular PW selects day-rounded clipped lengths. DM uses Bartlett HAC, nominal-horizon HLN and two-sided Student t. Smoke bootstrap override is explicit.
5. Holm rejects any hypothesis set differing from the explicit family. Smoke inference contains effect sizes and intervals without p-values. Friedman/Nemenyi is labelled descriptive and computed separately per horizon with studentized_range.
6. Runner is serial with explicit thread limits and an import-safe main entry point. No fork globals or multiprocessing assumptions.

Outstanding scientific prerequisites: approved calendar and independent workbook interval semantics. Smoke is isolated and does not claim a frozen benchmark.
