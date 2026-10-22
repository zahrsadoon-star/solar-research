# S1 protocol v1 - reference checks (literature officer, 2026-10-22)

Scope: tasks 1-4 of the protocol-v1 literature request. Items already verified in `literature/S1_doi_followup.md` and
`studies/S1_outage_forecasting/references_verified.md` were only re-read against Crossref, not re-researched.
Crossref was queried from the user's PC (PowerShell `Invoke-RestMethod`, api.crossref.org) on 2026-10-22.
[UNVERIFIED] = not confirmed; do not cite or code that item as fact.

## 1. Bibliographic verification

| reference | DOI | how verified | status |
|---|---|---|---|
| Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70. | none found (JSTOR stable 4615733) | Crossref title + bibliographic queries returned no record for this paper (only Holland & Copenhaver 1987, Shaffer 1986 etc.); vol/issue/pages from GESIS KG record https://data.gesis.org/gesiskg/resource/zis-Holm1979A and Wikipedia reference list (JSTOR 4615733, MR 0538597). JSTOR page itself not readable (JS wall). | Verified (no DOI exists in Crossref; cite with JSTOR stable URL https://www.jstor.org/stable/4615733) |
| Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708. | 10.2307/1913610 | api.crossref.org/works/10.2307/1913610 (start page 703 only); end page 708 already verified in S1_doi_followup.md (Econometric Society page) | Verified |
| Harvey, D., Leybourne, S., & Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting*, 13(2), 281-291. | 10.1016/S0169-2070(96)00719-4 | api.crossref.org/works/10.1016/S0169-2070(96)00719-4 | Verified |
| Kiefer, N. M., & Vogelsang, T. J. (2005). A new asymptotic theory for heteroskedasticity-autocorrelation robust tests. *Econometric Theory*, 21(6), 1130-1164. | 10.1017/S0266466605050565 | Crossref DOI record (authors, title, vol 21, issue 6; no page field); pages 1130-1164 from Cambridge Core abstract page https://www.cambridge.org/core/journals/econometric-theory/article/abs/new-asymptotic-theory-for-heteroskedasticityautocorrelation-robust-tests/E4B23DC06C2508DDCFF148E04269AF28 | Verified |
| Hansen, P. R. (2005). A test for superior predictive ability. *Journal of Business & Economic Statistics*, 23(4), 365-380. | 10.1198/073500105000000063 | api.crossref.org/works/10.1198/073500105000000063 | Verified (an SSRN working-paper version has DOI 10.2139/ssrn.264569 - do not cite that one) |
| White, H. (2000). A reality check for data snooping. *Econometrica*, 68(5), 1097-1126. | 10.1111/1468-0262.00152 | api.crossref.org/works/10.1111/1468-0262.00152 | Verified |
| Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. *Journal of Pharmacokinetics and Biopharmaceutics*, 15(6), 657-680. | 10.1007/BF01068419 | api.crossref.org/works/10.1007/bf01068419 | Verified |
| Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: a next-generation hyperparameter optimization framework. In *Proc. 25th ACM SIGKDD Int. Conf. on Knowledge Discovery & Data Mining* (pp. 2623-2631). | 10.1145/3292500.3330701 | api.crossref.org/works/10.1145/3292500.3330701 (Crossref title field is just "Optuna"; subtitle as commonly cited [UNVERIFIED from Crossref]) | Verified (authors, venue, pages); subtitle not in Crossref record |

## 2. Kiefer & Vogelsang (2005): fixed-b critical value, Bartlett kernel, two-sided 5 %

- **Secondary source (not the paper itself):** ForeComp R-package paper, arXiv:2603.07458 ("ForeComp: An R Package for Comparing Predictive Accuracy Using Fixed-Smoothing Asymptotics"), Section 3.2 "DM-FB", Eq. (10), p. 6, read via WebFetch on 2026-10-22. It states that "For the Bartlett kernel, Kiefer and Vogelsang (2005) provide the approximation":

  `q0.975(b) = 1.9600 + 2.9694 b + 0.4160 b^2 - 0.5324 b^3`

  i.e. the 97.5 % quantile, used as the critical value of a **two-sided 5 %** test; b = M/T (bandwidth / sample size).
- **Primary source status: [UNVERIFIED in the published paper].** The published ET article was not accessible (paywall). The Cornell CAE working-paper version (Kiefer & Vogelsang, CAE WP #05-08, Jan 2005, https://cae.economics.cornell.edu/05-08.pdf) contains **no polynomial**; it gives Table I (p. 24) "Asymptotic Critical Values for t*_b Using Bartlett Kernel" on a grid b = 0.02, ..., 1.0 (right-tail values, 90/95/97.5/99 %, 50,000 replications) and says values can be interpolated. Two further secondary sources checked (Cho & Vogelsang 2017, Econometrics 5(1):2; Sun 2013 "Let's fix it") do not quote the polynomial.
- Action: before the protocol is frozen, someone with library access must confirm the coefficients (and table/equation number) in the published ET 21(6) article, or the protocol should cite the ForeComp paper as the source of the formula, or use the grid table in CAE WP 05-08 with interpolation.

## 3. Naumann et al. LFP ageing models

### 3a. Bibliography
| reference | DOI | how verified | status |
|---|---|---|---|
| Naumann, M., Schimpe, M., Keil, P., Hesse, H. C., & Jossen, A. (2018). Analysis and modeling of calendar aging of a commercial LiFePO4/graphite cell. *Journal of Energy Storage*, 17, 153-169. | 10.1016/j.est.2018.01.019 | Crossref DOI record (issued 2018-06; pages 153-169); TUM FIS portal | Verified (DOI correct) |
| Naumann, M., Spingler, F. B., & Jossen, A. (2020). Analysis and modeling of cycle aging of a commercial LiFePO4/graphite cell. *Journal of Power Sources*, 451, 227666. | 10.1016/j.jpowsour.2019.227666 | Crossref DOI record (issued 2020-03); TUM FIS portal | Verified. Crossref gives middle initial "Franz B. Spingler". |

### 3b. Access
- Journal versions: ScienceDirect blocked by a CAPTCHA (not bypassed). Unpaywall: calendar paper = green OA only via mediaTUM record 1435450 (bibliographic record, **no PDF attached**); cycle paper = closed. **Neither journal full text was read.**
- What was read instead: **Naumann, M. (2018). *Techno-economic evaluation of stationary battery energy storage systems with special consideration of aging*. Dr.-Ing. dissertation, Technische Universität München** (submitted 28.03.2018), mediaTUM https://mediatum.ub.tum.de/doc/1434981/1434981.pdf (156 PDF pages; text extracted 2026-10-22). Its p. VI states that sections of the calendar-ageing paper (listed there as "Journal of Energy Storage (16). P. 153-169", i.e. the dissertation misprints the volume) are "partially contained" in Chapters 4 and 5. Equation numbers and pages below are **the dissertation's**, not the journal's. Whether the journal paper prints identical equations/parameters is [UNVERIFIED].

### 3c. Calendar ageing model as printed in the dissertation (Section 5.1, printed pp. 69-75)
Notation as printed (Q_loss = loss of relative discharge capacity, %; R_inc = increase of relative resistance R_DC,10s, %):

- Eq. (5.1), p. 70: `Q_loss,cal(T, SOC, t) = k_temp,Qloss(T) · k_SOC,Qloss(SOC) · √t`
- Eq. (5.2), p. 70: `R_inc,cal(T, SOC, t) = k_temp,Rinc(T) · k_SOC,Rinc(SOC) · t`
- Eq. (5.3), p. 70: `k_temp,Qloss(T) = k_ref,Qloss · exp( −(E_a,Qloss / R) · (1/T − 1/T_ref) )`
- Eq. (5.4), p. 70: same form for R_inc with k_ref,Rinc, E_a,Rinc.
  T_ref = 25 °C = 298.15 K, SOC_ref = 100 %, R = 8.314 J mol^-1 K^-1 (p. 70).
- Eq. (5.12), p. 73: `k_SOC,Qloss(SOC) = c_Qloss · (SOC − 0.5)^3 + d_Qloss` (cubic, fitted on the 40 °C test points at t_end = 29 months)
- Eq. (5.14), p. 74: `k_SOC,Rinc(SOC) = c_Rinc · (SOC − 0.5)^2 + d_Rinc`
- Time exponent: 0.5 for capacity (√t), 1 for resistance (p. 70, Section 5.1.2.1).
- Differential form for varying conditions, Eq. (5.15), p. 75: `dQ_loss/dt = k_temp,Qloss(T) · k_SOC,Qloss(SOC) · (2√t)^-1`; virtual time Eq. (5.17), p. 75: `t* = ( Q_loss / (k_temp,Qloss(T) · k_SOC,Qloss(SOC)) )^2`, recomputed at every change of storage condition (ageing order-independent; rate depends on current SOH).

Table 5.1, p. 74 ("Q_loss and R_inc aging model reference values and parameters"), copied as extracted:

| Parameter | Q_loss | R_inc |
|---|---|---|
| T_ref | 298.15 K | 298.15 K |
| SOC_ref | 100 % | 100 % |
| k_ref | 0.0012571 % s^-0.5 | 3.4194 × 10^-8 % s^-1 |
| a | −2059.8 K | −8638.8 K |
| b | 9.2644 | 29.992 |
| E_a | 17.126 kJ mol^-1 | 71.827 kJ mol^-1 |
| c | 2.8575 | −3.3903 |
| d | 0.60225 | 1.5604 |

(a, b = slope/intercept of the ln(Q_loss) vs 1/T fit, Eqs. 5.7-5.10; E_a = −a·R.) Units imply t in seconds. Validation (Table 5.2, p. 77): absolute errors at end of the dynamic test within −2.2 % ... +1.1 % (Q_loss) and −5.9 % ... +6.9 % (R_inc). Model ignores the initial capacity increase / anode-overhang effect at 0 % and 100 % SOC (p. 69).

Officer's notes (not from the source): (i) "SOC − 0.5" implies SOC as a fraction 0-1 [inferred]; (ii) by arithmetic, k_SOC,Qloss(1.0) = 2.8575·0.125 + 0.60225 = 0.959, not exactly 1 at SOC_ref - check against the journal paper before coding; (iii) the journal abstract says "5 parameters" for the model.

Journal abstract (TUM FIS portal, paraphrased): Sony/Murata LFP/graphite cell; 29-month study, 17 static storage conditions x 3 cells; semi-empirical 5-parameter model of capacity loss and resistance increase; validated on a 9-month dynamic test (15 test points) with errors < 2.2 % (capacity) and < 6.9 % (resistance).

### 3d. Cycle ageing
- **Journal paper (2020, JPS 451:227666): full text NOT accessed.** Abstract (TUM FIS portal, paraphrased): 29-month study, 19 combinations of temperature, C-rate, DOD and SOC; semi-empirical model of capacity loss and resistance increase; validated with two dynamic profiles, absolute errors < 1 % (capacity) and < 2 % (resistance); an "unexpectedly strong, but partly reversible capacity loss is observed with shallow cycles at medium states of charge".
- **Dissertation precursor (Section 5.2, printed pp. 77-84)** - may differ from the 2020 paper [UNVERIFIED]:
  - Eq. (5.18), p. 78: `Q_loss,cyc(C-rate, DOC, FEC) = k_C-rate,Qloss(C-rate) · k_DOC,Qloss(DOC) · √FEC`
  - Eq. (5.19), p. 78: `R_inc,cyc = k_C-rate,Rinc(C-rate) · k_DOC,Rinc(DOC) · FEC`
  - Eqs. (5.20)/(5.21), p. 79: `k_C-rate = a · C-rate + b`
  - Eq. (5.23), p. 80: `k_DOC,Qloss(DOC) = c_Qloss · (DOC − 0.6)^3 + d_Qloss`; Eq. (5.25), p. 81: `k_DOC,Rinc(DOC) = c_Rinc · (DOC − 0.5)^3 + d_Rinc`
  - Table 5.3, p. 82: Q_loss: a = 0.0630, b = 0.0971, c = 4.0253, d = 1.0923; R_inc: a = −0.0020, b = 0.0021, c = 6.8477, d = 0.91882.
  - Combined model Eq. (5.29), p. 84: `Q_loss,comb = Q_loss,cal(T, SOC, t) + Q_loss,cyc(C-rate, DOC, FEC)` (superposition; cycle model = measured ageing minus calendar ageing at the mean SOC). No temperature term in the cycle model (25-40 °C tested only).
- For S1 the calendar model is the one needed (reserve-holding cost); cite the 2018 journal paper and, until the journal text is checked, state that equations were taken from Naumann (2018, dissertation).
- Raw data (not opened): Mendeley Data kxh42bfgtj (calendar), 6hgyr25h8d (cycle).

## 4. Iraq 2018 public holidays, Ramadan, Eid

Sources: TAD = https://www.timeanddate.com/holidays/iraq/2018 (read 2026-10-22; page notes dates "may be preliminary"); OH = https://www.officeholidays.com/countries/iraq/2018 (read 2026-10-22). Neither is an Iraqi government source; no Council of Ministers announcement for 2018 was found online.

| date (2018) | holiday | TAD | OH | flag |
|---|---|---|---|---|
| Mon 1 Jan | New Year's Day | yes | yes | fixed |
| Sat 6 Jan | Army Day | yes | yes (OH marks "regional") | fixed |
| Wed 21 Mar | Nowruz | yes | yes | fixed |
| Mon 9 Apr | Baghdad Liberation Day | no | yes ("regional") | sources disagree [UNVERIFIED] |
| Tue 1 May | Labour Day | yes | yes | fixed |
| Sat 12 May | parliamentary election day | - | - | election date: Wikipedia "2018 Iraqi parliamentary election"; whether a declared holiday [UNVERIFIED] |
| Sun 13 May | day after the election | - | - | **ad hoc**: declared official holiday by the Iraqi government (Kurdistan24, 12 May 2018, https://www.kurdistan24.net/en/story/375837) |
| ~16/17 May - ~14 Jun | Ramadan | not listed | not listed | Start date for Iraq [UNVERIFIED]; Iraqi Shia and Sunni authorities often start on different days. Implied by Eid on 15 Jun: start 16 or 17 May (inference only). |
| Fri 15 - Sun 17 Jun | Eid al-Fitr | 15-17 Jun | 15-19 Jun | moon-dependent; length differs between sources; Shia (Sistani) Eid may have been one day later [UNVERIFIED for 2018] |
| Sat 14 Jul | Republic Day | no | yes | sources disagree [UNVERIFIED] |
| Wed 22 - Sat 25 Aug | Eid al-Adha | yes | yes | moon-dependent; exact government holiday span [UNVERIFIED] |
| Tue 11 Sep | Islamic New Year | yes | yes | moon-dependent |
| Thu 20 Sep | Ashura | yes | yes | moon-dependent |
| Wed 3 Oct | Independence Day | "Observance" (not holiday) | yes | sources disagree; treat as non-holiday in 2018 [UNVERIFIED] |
| ~31 Oct | Arbaeen | not listed | not listed | often declared ad hoc (esp. southern provinces); 2018 status [UNVERIFIED] |
| 20 or 21 Nov | Prophet's Birthday (Mawlid) | Wed 21 Nov | Tue 20 Nov | sources disagree by one day (Sunni/Shia dating differs) [UNVERIFIED] |
| Mon 10 Dec | Victory Day | no | yes | first anniversary of the 2017 victory declaration; holiday status [UNVERIFIED] |
| Tue 25 Dec | Christmas | yes | yes | fixed |

Ad hoc closures (heat-wave days, extra Eid days, bad-weather days) are common in Iraq (e.g. Iraq Business News "public holidays" tag lists heat-wave holidays in 2015-2016), but **no 2018 heat-wave or weather holiday could be confirmed**. Recommendation: encode the fixed and Eid holidays as features, keep the disputed dates as a separate "uncertain-holiday" flag, and test robustness with and without them.
