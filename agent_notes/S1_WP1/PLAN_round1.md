WP1 is blocked by the missing weather CSV. Inspection also found four outage/status disagreements under positional alignment. No files were changed; the protocol below could not be saved to `.agents/PLAN.md` because this session is read-only.

**Protocol — task `20261021-s1-wp1-data`**

1. **Scope and evidence**

   WP1 establishes a reproducible dataset and descriptive EDA. It does not test forecasting superiority or battery-dispatch value.

   Read: `PROJECT_CONTEXT.md`, `AGENTS.md`, `DECISIONS.md`, and `studies/S1_outage_forecasting/PLAN.md`. `.agents/` exists but contains no notes.

   Inspection findings are provisional audit observations, not manuscript results. The implementation must reproduce and save them under `results/S1/eda/`.

2. **Sources and alignment**

   Use `BG18760_with_analysis.xlsx`, sheet `Hourly Data`, with these exact mappings:

   | Source column | Output |
   |---|---|
   | `Timestamp` | DatetimeIndex |
   | `Grid (kWh)` | `grid_kwh` |
   | `Generator (kWh)` | `generator_kwh` |
   | `Total (kWh)` | `load_kwh` |
   | `Outage (1/0)` | `outage` |
   | `Hour`, `Month` | Validate against index |

   Require exactly 8,760 unique, monotonically increasing hourly timestamps from `2018-01-01 00:00` through `2018-12-31 23:00`. Localize naive timestamps to `Asia/Baghdad`; do not shift already-local data by three hours.

   The workbook’s `Read Me` states that annual timestamps were reconstructed from row order, with partial January validation. Preserve that provenance limitation.

   The required `nasa_power_baghdad_2018_hourly_local.csv` is absent. Its exact headers, units, missing-value codes, and timestamp convention remain **unverified**. Once supplied, inspect them before implementing the mapping to the four requested weather columns. Join one-to-one on local timestamps and require complete coverage. No fabricated weather, substitution, interpolation, or silent row dropping.

   Record source hashes, sheet names, column mappings, software versions, and alignment decisions in generated output.

3. **Label validation**

   Retain the analysis workbook’s `outage` as the authoritative task label:

   \[
   y_t\in\{0,1\},\qquad 1=\text{grid unavailable}.
   \]

   Compare it with:

   \[
   z_t=1-\text{national status}_t,\qquad
   g_t=\mathbf1(\text{generator kWh}_t>0).
   \]

   The status source is `BG1-8760_v2026-04_homer_folder.xlsx`, sheet `National Status`, columns `Date & Time`, `National Grid (kWh)`, and `Status (1=National / 0=No)`.

   Inspection found 745 full datetimes and 8,015 time-only entries. Therefore, do not perform a timestamp join across the whole sheet. Permit explicitly disclosed row-order alignment only after confirming:

   - Both sources contain 8,760 data rows.
   - Every usable status datetime matches the corresponding analysis timestamp.
   - Every corresponding grid-energy value matches.

   These checks passed during inspection. This supports positional correspondence but does not independently establish the missing timestamps.

   For comparator \(c\), report:

   \[
   A_c=\frac{\sum_{t\in V_c}\mathbf1(y_t=c_t)}{|V_c|},
   \]

   where \(V_c\) contains valid aligned pairs. Report coverage separately; missing comparisons must never count as agreements.

   `validate_outage_labels()` must return, at minimum: row count, alignment method, valid comparison counts, coverage, agreement rates, disagreement counts, disagreement timestamps and source values, missing counts, and invalid-binary counts.

   Inspection found four status disagreements and zero generator-proxy disagreements. Preserve every discrepancy; do not overwrite labels. Generator agreement is a consistency check because the workbook describes generator-derived outages.

4. **Event definition and workbook comparison**

   An event is a maximal consecutive run of \(y_t=1\). Use inclusive start and end timestamps:

   \[
   d_i=1+\frac{\text{end}_i-\text{start}_i}{1\text{ hour}}.
   \]

   Return `start`, `end`, `duration_h`, `start_hour`, and `month`; hour and month refer to event onset. Events crossing midnight or month boundaries remain single events.

   Require:

   \[
   \sum_i d_i=\sum_t y_t.
   \]

   The workbook’s `Outage Events` header is on Excel row 3. Compare event records using `Start timestamp`, `Start hour`, `Month`, and `Duration (h)`, as well as the `Statistic`/`Value` summary.

   Treat 1,064 events, 4,324 hours, and approximately 4.06 hours mean duration as workbook reference values, not acceptance targets to force. Save computed values, workbook values, and signed differences. Compare individual starts and durations, not only totals.

   Include boundary-touching runs in annual accounting, but identify their potentially censored durations separately.

5. **EDA metrics and figures**

   For any group \(G\), including month, hour, and month-by-hour:

   \[
   H_G=\sum_{t\in G}y_t,\qquad
   P_G=H_G/|G|.
   \]

   Save denominators alongside outage hours and shares. Report event count, mean, median, minimum, maximum, sample standard deviation, and 95th percentile duration. Specify linear interpolation for quantiles. Monthly event counts use onset month; monthly outage hours use each hour’s actual month.

   Daily temperature analysis uses complete local calendar days:

   \[
   P_d=\frac1{24}\sum_{t\in d}y_t,\qquad
   T_d^{\max}=\max_{t\in d}T_t.
   \]

   Plot daily outage share against daily maximum temperature as a descriptive association. Do not infer causality or use realized daily maximum temperature as an earlier forecast input.

   Required PNGs at 300 dpi:

   - Month-by-hour outage probability heatmap, fixed probability scale.
   - Duration histogram with one-hour bins and a fitted Weibull overlay.
   - Daily outage share versus daily maximum temperature.

   For the Weibull overlay, fit complete-event durations by maximum likelihood with location fixed at zero:

   \[
   f(d;k,\lambda)=\frac{k}{\lambda}(d/\lambda)^{k-1}
   e^{-(d/\lambda)^k},\quad d>0.
   \]

   Record shape, scale, included/excluded event counts, and fitting failures. This is a descriptive continuous approximation to discrete hourly durations, not evidence that durations follow a Weibull distribution.

   Produce `summary.json` and a tidy tables CSV containing the underlying plotted summaries. Missing weather blocks the complete deliverable.

6. **Temporal separation and future targets**

   Full-year EDA is descriptive. Record that the year has been inspected; later evaluation months cannot be described as wholly unseen.

   Proposed exact implementation of the study’s monthly expanding-window evaluation, for WP2:

   - Initial training: January–March.
   - Outer evaluation: April through December, one month per fold.
   - Each fold trains only on preceding months.
   - Inner validation uses expanding monthly folds within outer training, beginning with January training and February validation.
   - Fit preprocessing, feature selection, calibration, and tuning exclusively within training partitions.

   At forecast origin \(t\), information is available only through \(t\). For \(h\in\{1,3,6,12,24\}\):

   \[
   Y_{t,h}=y_{t+h},\qquad
   A_{t,h}=\max_{j=1,\ldots,h}y_{t+j}.
   \]

   Require the entire target interval to remain within its assigned partition. Purge training origins whose targets cross the next partition boundary. Past observations may supply evaluation lags; future observations may not.

   Remaining duration at an ongoing-outage origin is the number of subsequent outage hours, excluding the current hour. Do not expose completed-event duration before restoration. Treat unresolved events as censored and prevent event outcomes from crossing training cutoffs.

7. **Baselines, seeds, and statistical tests**

   WP1 requires no stochastic model runs, baseline leaderboard, or inferential significance tests. Data checks and EDA are deterministic.

   For later forecasting, retain the study baselines: persistence, same-hour-yesterday, and training-only hour/month climatology. Because expanding training lacks observations for an unseen month, prespecify fallback to training-only hour climatology, then overall training prevalence. Never estimate climatology from evaluation labels.

   Use seeds `0–29` for later stochastic models, retaining all runs. Seeds measure algorithmic variability; they are not independent temporal samples.

   Primary later classification metrics:

   \[
   BS=\frac1N\sum_t(p_t-y_t)^2,\qquad
   BSS=1-\frac{BS_{\rm model}}{BS_{\rm climatology}},
   \]

   \[
   LL=-\frac1N\sum_t[y_t\log p_t+(1-y_t)\log(1-p_t)].
   \]

   Clip probabilities to \([10^{-15},1-10^{-15}]\) for log-loss. Define BSS as undefined when baseline Brier loss is zero. The remaining study metrics and their exact conventions belong in WP2.

   Preserve the planned Friedman/Nemenyi and paired Diebold–Mariano analyses for WP2, with explicit handling of temporal dependence and overlapping horizons. Do not treat hourly observations or seeds as independent datasets. No significance claim is warranted from WP1.

8. **Falsification and threats to validity**

   WP1 fails its data-readiness criterion if complete hourly coverage, valid weather alignment, binary labels, or event accounting cannot be established. Any disagreement falsifies perfect cross-source agreement; it does not identify which source is correct.

   WP1 cannot establish forecasting skill or dispatch benefit. The study’s later go/no-go criterion requires at least 10% Brier skill at the specified short horizons and at least 10% dispatch improvement versus Mode 0 at equal system size. Failure must be reported without retuning the criterion.

   Principal threats: reconstructed timestamps; malformed status timestamps; shared provenance of labels and generator-derived events; unresolved label disagreements; missing weather and uncertain weather timing; one household and one year; seasonality and serial dependence; boundary censoring; hourly discretization; and researcher exposure to full-year EDA.

Checks performed: read-only workbook inspection and alignment checks. Pytest initially failed because no writable temporary directory was available; retrying with capture and cache disabled collected no tests. Neither `.agents/PLAN.md` nor `CODEX_REPORT.md` was written.