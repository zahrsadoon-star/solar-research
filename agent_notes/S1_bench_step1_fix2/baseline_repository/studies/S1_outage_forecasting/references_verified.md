# S1 - verified references (Literature officer, Claude agent, 2026-10-22)

Checked against Crossref / publisher / proceedings / arXiv pages. "yes" = title, authors, year, venue and DOI (or
official URL when no DOI exists) confirmed. Page ranges marked "from memory" must be re-checked before submission.

## Forecast comparison and evaluation
| Citation | DOI / URL | Verified | Use in S1 |
|---|---|---|---|
| Diebold & Mariano (1995). Comparing predictive accuracy. J. Business & Economic Statistics 13(3):253-263 | 10.1080/07350015.1995.10524599 | yes | DM test |
| Harvey, Leybourne & Newbold (1997). Testing the equality of prediction mean squared errors. Int. J. Forecasting 13(2):281-291 | 10.1016/S0169-2070(96)00719-4 | yes | small-sample DM correction |
| Demsar (2006). Statistical comparisons of classifiers over multiple data sets. JMLR 7:1-30 | https://www.jmlr.org/papers/v7/demsar06a.html (no DOI) | yes | Friedman/Nemenyi, CD diagrams |
| Tashman (2000). Out-of-sample tests of forecasting accuracy: an analysis and review. Int. J. Forecasting 16(4):437-450 | 10.1016/S0169-2070(00)00065-0 | yes | rolling origin |
| Brier (1950). Verification of forecasts expressed in terms of probability. Monthly Weather Review 78(1):1-3 | 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2 | yes | Brier score |
| Gneiting & Raftery (2007). Strictly proper scoring rules, prediction, and estimation. JASA 102(477):359-378 | 10.1198/016214506000001437 | yes | proper scores |
| Kuensch (1989). The jackknife and the bootstrap for general stationary observations. Ann. Statist. 17(3):1217-1241 | 10.1214/aos/1176347265 | yes (pages from memory) | block bootstrap |
| Newey & West (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica 55(3):703-708 | 10.2307/1913610 | yes (end page from memory) | HAC variance |
| Bergmeir & Benitez (2012). On the use of cross-validation for time series predictor evaluation. Information Sciences 191:192-213 | 10.1016/j.ins.2011.12.028 | yes | time-series CV |
| Bergmeir, Hyndman & Koo (2018). A note on the validity of cross-validation for evaluating autoregressive time series prediction. CSDA 120:70-83 | 10.1016/j.csda.2017.11.003 | yes | CV for lag models |
| Politis & White (2004) automatic block length | - | NOT YET VERIFIED | block-length sensitivity |

## Tools and foundation models
| Citation | DOI / URL | Verified |
|---|---|---|
| Akiba et al. (2019). Optuna. Proc. 25th ACM SIGKDD, 2623-2631 | 10.1145/3292500.3330701 | yes |
| Ansari et al. (2024). Chronos: Learning the language of time series. TMLR | arXiv:2403.07815 (no DOI) | yes |
| Chronos-2: From univariate to universal forecasting (2025), arXiv preprint | arXiv:2510.15821 | partial (author list not extracted) |
| Das, Kong, Sen & Zhou (2024). A decoder-only foundation model for time-series forecasting. ICML 2024, PMLR 235 | https://proceedings.mlr.press/v235/das24c.html | yes |
| Ekambaram et al. (2024). Tiny Time Mixers (TTMs). NeurIPS 2024 | arXiv:2401.03955 | yes |

## Iraq electricity supply and household generators
| Citation | DOI | Verified | Relevance |
|---|---|---|---|
| Istepanian (2014). Iraq's electricity crisis. The Electricity Journal 27(4):51-69 | 10.1016/j.tej.2014.04.006 | yes | supply-deficit background |
| Al-Wakeel (2021). Local energy systems in Iraq: neighbourhood diesel generators and solar PV. In Microgrids and Local Energy Systems (IntechOpen) | 10.5772/intechopen.95280 | yes | generator networks, per-ampere billing |
| Aziz et al. (2020). Feasibility analysis of grid-connected and islanded operation of a solar PV microgrid system: a case study of Iraq. Energy 191 | 10.1016/j.energy.2019.116591 | yes | outage schedules drive sizing |
| Al Essa (2023). Energy assessments of a PV-wind-battery system for residential appliances in Iraq. J. Energy Storage 59:106514 | 10.1016/j.est.2022.106514 | yes | blackout scenarios |
| Alshamri, Cockerill, Tomlin, Al-Damook & Al Qubeissi (2024). On-off-grid optimal hybrid renewable energy systems for house units in Iraq. Clean Technologies 6(2):602-624 | 10.3390/cleantechnol6020032 | yes | same data provenance (Al-Shamri) |
| Tahir et al. (2025). From diesel reliance to sustainable power in Iraq. Renewable Energy 238:121905 | 10.1016/j.renene.2024.121905 | yes | generator replacement economics |

## ML forecasting of power outages
| Citation | DOI | Verified | Relevance |
|---|---|---|---|
| Mbuya et al. (2022). Very short-term blackout prediction for grid-tied PV systems ... weak grids of developing countries. Complexity 2022:4763820 | 10.1155/2022/4763820 | yes | closest analogue |
| Sivhugwana & Ranganai (2025). Short-term forecasting of unplanned power outages using ML. Energies 18(18):4994 | 10.3390/en18184994 | yes | uses DM test vs naive baselines |
| Atrigna et al. (2023). ML fault prediction of distribution grids under heatwaves. IEEE Trans. Industry Applications | 10.1109/TIA.2023.3262230 | yes (vol/issue missing) | heat-driven outages |
| Kabir, Guikema & Quiring (2024). Power outage prediction using data streams. Risk Analysis 44(3):686-704 | 10.1111/risa.14211 | yes | probabilistic outage prediction |
| Eskandarpour & Khodaei (2017). ML based power grid outage prediction in response to extreme events. IEEE Trans. Power Systems 32(4):3315-3316 | 10.1109/TPWRS.2016.2631895 | yes | early ML outage letter |
| Fatima et al. (2024). ML for power outage prediction during hurricanes: review. Eng. Appl. AI 133:108056 | 10.1016/j.engappai.2024.108056 | yes | literature is weather-hazard dominated |

Gap (agent's reading, to be confirmed by a systematic search before the Introduction is written): household-level
forecasting of scarcity-driven load-shedding appears unstudied; Mbuya et al. (2022) is the nearest analogue.
Unresolved: Mejeed (2025) Baghdad PV-battery paper (DOI not found); Chronos-2 author list.
