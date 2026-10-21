# S1 - Forecasting national-grid outages on an intermittent grid: a 10+ model benchmark and its value for home storage

## Research questions
- **RQ1** Which model families predict grid outages in Baghdad best, at which horizons, and is the difference significant?
- **RQ2** Which information matters (outage history, calendar, load, temperature)? (permutation importance / SHAP / ablation)
- **RQ3** What is a forecast worth? Feed each model's forecasts into a predictive battery-dispatch rule and measure
  LPSP, grid import and cost against Mode 0, blanket pre-charging and perfect foresight.
- **RQ4** Do conclusions transfer to a second region? KR (Karbala house, outages inferred from private-generator use). BS (Basra house) was supplied by the grid 24 h, so it has no outages to label.

## Positioning (from literature/S1_related_work_alphaxiv.md)
Prior outage forecasting targets weather-driven, region-level outages; random splits inflate their scores
(arXiv:2608.24665). Outage-aware dispatch on weak grids has used a Markov chain with survey-estimated rates
(arXiv:2604.18268). S1's contribution: household-level forecasting of chronic load shedding from a measured record,
and whether learned models add dispatch value **beyond a fitted Markov chain**.

## Data
`data/raw/BG18760_with_analysis.xlsx` (Hourly Data: Outage 1/0; Outage Events) cross-checked with
`data/raw/BG1-8760_v2026-04_homer_folder.xlsx` (National Status). Exogenous: hourly 2018 air temperature for Baghdad
(NASA POWER / ERA5, downloaded by the lead because agents have no network) - temperature drives load-shedding.
Limit: one year (8,760 h, 1,064 events); judge effect sizes accordingly.

## Targets and horizons
- Classification: grid status at t+h for h = 1, 3, 6, 12, 24 h; and "any outage in (t, t+h]".
- Regression / survival: remaining duration of an ongoing outage.

## Models (>= 10, same tuning budget for each)
Baselines: persistence, seasonal-naive (same hour yesterday), climatology (P(outage | hour, month)).
Statistical: 1st/2nd-order Markov chain, logistic regression, Weibull/Cox duration model (duration target).
ML: kNN, SVM, Random Forest, Extra Trees, XGBoost, LightGBM, CatBoost.
Deep: MLP, LSTM, GRU, TCN, small Transformer.
Time-series foundation models, zero-shot (downloaded from Hugging Face to D:/SolarProject/models, Apache-2.0): Chronos-2 (with temperature as covariate), Chronos-Bolt, TimesFM 2.5, TinyTimeMixer r2. Question: does a pretrained model with no outage-specific training beat models trained on the Baghdad record?

## Evaluation protocol (no leakage)
- Rolling-origin time-series CV (expanding window, monthly folds); hyper-parameters tuned only inside training folds.
  The thesis used random 20 %-per-month test splits, which leak neighbouring hours; quantify that difference as a
  methodological finding.
- Metrics: Brier, log-loss, ROC-AUC, PR-AUC, MCC, F1, calibration (reliability curves, ECE); duration: MAE, C-index.
- 30 seeds for stochastic models; Friedman + Nemenyi across models; Diebold-Mariano on Brier loss for key pairs;
  effect sizes with confidence intervals.

## Downstream value (RQ3)
Predictive rule: if P(outage within h) > threshold, pre-charge from grid to a target SOC. Same PV/battery for all
cases, **corrected** PV model (south-facing, local time). Compare with Mode 0, blanket pre-charge, perfect foresight.

## Pilot go/no-go
Best model beats climatology by >= 10 % Brier skill at h = 1-6 h, and forecast-based dispatch changes LPSP or grid
import by >= 10 % vs Mode 0 at equal size. Otherwise report honestly and discuss with Zaher.

## Work packages (chained Codex tasks)
1. Data module + outage-event validation + EDA tables/figures
2. Evaluation harness (rolling-origin CV, metrics, statistical tests) with leakage tests
3. Baselines + statistical models
4. Tree / boosting models
5. Deep models
6. Results aggregation, statistics, publication figures
7. Downstream dispatch value
8. Manuscript draft (after Zaher reviews the results)
