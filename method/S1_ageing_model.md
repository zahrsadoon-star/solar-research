# S1 - LFP ageing model for the dispatch cost (Literature officer, 2026-10-22)

Purpose: give the dispatch simulation a smooth ageing cost A so that "keep the battery full" is not free.
Rule used in this file: everything in sections 1-4 is copied from a source that was actually read (source named per item).
Section 5 is the team's adaptation and is marked [JC]. Nothing below was typed from memory.

## 1. Sources and what was actually read

| # | Source | DOI / URL | How verified | What was read |
|---|---|---|---|---|
| S-a | Naumann, M., Schimpe, M., Keil, P., Hesse, H. C., & Jossen, A. (2018). Analysis and modeling of calendar aging of a commercial LiFePO4/graphite cell. *Journal of Energy Storage*, 17, 153-169. | 10.1016/j.est.2018.01.019 | Crossref API record (title, 5 authors, vol 17, pp 153-169, issued 2018-06); mediaTUM record 1435450 (bibliographic only, no full text attached) | **Journal full text NOT read.** ScienceDirect returned a CAPTCHA page; mediaTUM has no PDF for this record. |
| S-b | Naumann, M., Spingler, F. B., & Jossen, A. (2020). Analysis and modeling of cycle aging of a commercial LiFePO4/graphite cell. *Journal of Power Sources*, 451, 227666. | 10.1016/j.jpowsour.2019.227666 | Crossref API record (title, 3 authors, vol 451, article 227666, issued 2020-03); mediaTUM record 1536844 (bibliographic only) | **Journal full text NOT read** (same access barriers). |
| S-c | Naumann, M. (2018). *Techno-economic evaluation of stationary battery energy storage systems with special consideration of aging*. Dr.-Ing. dissertation, Technische Universitaet Muenchen (submitted 28.03.2018, accepted 03.07.2018; examiners A. Jossen, U. Wagner). | https://mediatum.ub.tum.de/doc/1434981/1434981.pdf (open access, 156 pp.) | Full PDF opened from mediaTUM in a browser session and text-extracted page by page | **Read in full for Chapter 4 (test matrices) and Chapter 5 (pp. 69-86 of the printed numbering; PDF pp. 87-104): calendar model Sec. 5.1, cycle model Sec. 5.2, combined model Sec. 5.3, Tables 5.1-5.3, Eqs. 5.1-5.30.** |
| S-d | Collath, N., Tepe, B., Englberger, S., Jossen, A., & Hesse, H. (2022). Aging aware operation of lithium-ion battery energy storage systems: a review. *Journal of Energy Storage*, 55, 105634. | 10.1016/j.est.2022.105634 | Crossref API record; text read as reprinted in Collath's TUM dissertation (2024), https://mediatum.ub.tum.de/download/1741530/1741530.pdf | Table 2 ("Algebraic form of selected semi-empirical degradation models"), column "Naumann (LFP) [18,19]" where [18] = S-a and [19] = S-b. |
| S-e | Collath, N., Cornejo, M., Engwerth, V., Hesse, H., & Jossen, A. (2023). Increasing the lifetime profitability of battery energy storage systems through aging aware operation. *Applied Energy*, 348, 121531. | 10.1016/j.apenergy.2023.121531 | Crossref API record; text read as reprinted in Collath (2024) dissertation | Appendix A, Eqs. (29)-(35): the Naumann model as cited from S-a [48] and S-b [49], including virtual-time handling and a MILP linearisation at 25 C. |
| S-f | SimSES (TUM open-source simulation tool), PyPI package `simses` 2.1.1, files `simses/model/degradation/sony_lfp_calendar.py` and `sony_lfp_cyclic.py` | https://pypi.org/project/simses/ | Wheel downloaded and source read | Implemented parameter values; code docstrings cite S-a (calendar) and S-b (cycle). Secondary; used only as a cross-check of numbers. |

### What this means for citation (important)
- The **equations and parameter values below are copied from the dissertation S-c**, Chapter 5. The dissertation states (List of Publications, footnote, p. VI): self-produced sections of the lead-author journal paper (3) = S-a "are partially contained in this thesis ... in particular ... Chapter ... 5 (3)". So Chapter 5.1 is the thesis version of the S-a calendar model.
- The **functional forms** of both the calendar and the cycle model, as published in S-a and S-b, are independently confirmed by S-d (Table 2) and S-e (Eqs. 30-31), both written by the same TUM group and citing S-a/S-b.
- The **numerical parameters** in S-c Tables 5.1 and 5.3 are identical to those implemented in SimSES (S-f), whose code attributes them to S-a and S-b (calendar k_ref stored in per-unit, i.e. /100; see Sec. 2).
- **UNVERIFIED:** the equation numbers, table numbers and page locations *inside the journal papers S-a and S-b*, and whether S-b's published parameters differ from the 2018 thesis values (the cycle study ran to 885 days in the thesis; S-b appeared two years later). Cite as: "model of Naumann et al. (2018, 2020), parameters as given in Naumann (2018, Tables 5.1 and 5.3)". Before submission, someone with library access should open S-a and S-b and record their own equation/table numbers.

## 2. Calendar ageing model (copied from S-c, Sec. 5.1)

Cell: Sony/Murata US26650FTC1, LiFePO4/graphite, 26650 cylindrical, 2.85 Ah datasheet / 3.0 Ah measured (S-c Table 4.1).
Q_loss = loss of relative discharge capacity in %; R_inc = increase of relative resistance R_DC,10s in % (S-c p. 69).

Eq. 5.1  Q_loss,cal(T, SOC, t) = k_temp,Qloss(T) * k_SOC,Qloss(SOC) * sqrt(t)
Eq. 5.2  R_inc,cal(T, SOC, t) = k_temp,Rinc(T) * k_SOC,Rinc(SOC) * t
Eq. 5.3  k_temp,Qloss(T) = k_ref,Qloss * exp( -(E_a,Qloss / R) * (1/T - 1/T_ref) )
Eq. 5.4  k_temp,Rinc(T) = k_ref,Rinc * exp( -(E_a,Rinc / R) * (1/T - 1/T_ref) )
Eq. 5.12 k_SOC,Qloss(SOC) = c_Qloss * (SOC - 0.5)^3 + d_Qloss
Eq. 5.14 k_SOC,Rinc(SOC) = c_Rinc * (SOC - 0.5)^2 + d_Rinc

with R = 8.314 J mol^-1 K^-1, T_ref = 25 C = 298.15 K, SOC_ref = 100 % (S-c p. 70).
(Eqs. 5.5-5.11 and 5.13 are the parameter-identification steps; Eqs. 5.9/5.10: E_a = -a * R.)

**Table 5.1 (S-c p. 74): "Q_loss and R_inc aging model reference values and parameters"**

| Parameter | Q_loss | R_inc |
|---|---|---|
| T_ref | 298.15 K | 298.15 K |
| SOC_ref | 100 % | 100 % |
| k_ref | 0.0012571 % s^-0.5 | 3.4194 x 10^-8 % s^-1 |
| a | -2059.8 K | -8638.8 K |
| b | 9.2644 | 29.992 |
| E_a | 17.126 kJ mol^-1 | 71.827 kJ mol^-1 |
| c | 2.8575 | -3.3903 |
| d | 0.60225 | 1.5604 |

Units implied by the table: t in **seconds**, T in **kelvin**, SOC as a **fraction 0-1** (the formulas subtract 0.5), Q_loss and R_inc in **%**.
Cross-check S-f: SimSES stores K_REF_QLOSS = 1.2571e-05 (per-unit, = 0.0012571 %/100), EA_QLOSS = 17126.0 J/mol, C = 2.8575, D = 0.60225; K_REF_RINC = 3.4194e-10 (per-unit), EA_RINC = 71827.0, C = -3.3903, D = 1.5604. Consistent with Table 5.1.

Differential form and path dependence (S-c Sec. 5.1.3, p. 75):
Eq. 5.15 dQ_loss/dt = q_loss(T, SOC, t) = k_temp,Qloss(T) * k_SOC,Qloss(SOC) * (2 sqrt(t))^-1
Eq. 5.16 dR_inc/dt = r_inc(T, SOC) = k_temp,Rinc(T) * k_SOC,Rinc(SOC)
Eq. 5.17 t*_cal,Qloss(T, SOC, Q_loss) = ( Q_loss / (k_temp,Qloss(T) * k_SOC,Qloss(SOC)) )^2
"the virtual time t* is defined, representing the time until the same Q_loss is reached under the new storage conditions" and must be recomputed whenever conditions change (S-c p. 75). The dynamic study showed independence of the order of storage conditions (S-c p. 75).

Reported accuracy: static fit errors up to about 2 % (Q_loss, 40/60 C) and up to 4 % (R_inc, 60 C) (S-c p. 72); SOC fit at 40 C below 1.5 % (Q_loss) (S-c p. 74); dynamic validation errors at end of test between -2.2 % and +1.2 % (Q_loss) and -5.9 % to +6.9 % (R_inc) (S-c Table 5.2, p. 77).

## 3. Cycle ageing model (copied from S-c, Sec. 5.2; form confirmed for S-b by S-d and S-e)

"Pure" cycle ageing = measured cycle-test ageing minus the calendar ageing of the matching storage test point (average SOC and temperature) (S-c pp. 77-78).

Eq. 5.18 Q_loss,cyc(C-rate, DOC, FEC) = k_C-rate,Qloss(C-rate) * k_DOC,Qloss(DOC) * sqrt(FEC)
Eq. 5.19 R_inc,cyc(C-rate, DOC, FEC) = k_C-rate,Rinc(C-rate) * k_DOC,Rinc(DOC) * FEC
Eq. 5.20 k_C-rate,Qloss(C-rate) = a_Qloss * C-rate + b_Qloss
Eq. 5.21 k_C-rate,Rinc(C-rate) = a_Rinc * C-rate + b_Rinc
Eq. 5.23 k_DOC,Qloss(DOC) = c_Qloss * (DOC - 0.6)^3 + d_Qloss
Eq. 5.25 k_DOC,Rinc(DOC) = c_Rinc * (DOC - 0.5)^3 + d_Rinc

**Table 5.3 (S-c p. 82): "Q_loss and R_inc aging model reference values and parameters"**

| Parameter | Q_loss | R_inc |
|---|---|---|
| a | 0.0630 | -0.0020 |
| b | 0.0971 | 0.0021 |
| c | 4.0253 | 6.8477 |
| d | 1.0923 | 0.91882 |

Units: FEC = full-equivalent cycles (dimensionless); DOC (depth of cycle) as a fraction 0-1; C-rate in h^-1; Q_loss,cyc and R_inc,cyc in %. The table itself gives no units; the fraction convention for DOC is confirmed by S-c's own check that a 100 % DOC, 1 C cell reaches 20 % pure-cycle capacity loss "after about 8500 FEC" (S-c p. 84), which the equations reproduce only with DOC = 1.0 (computed: about 8,560 FEC [JC check]). SimSES (S-f) also uses DOC as a fraction and divides the % result by 100.
SimSES lists D_RINC = 0.9182 vs. 0.91882 in S-c Table 5.3 (rounding difference; use the thesis value).
Temperature: "the temperature influence is neglected in this cycle aging model and only represented in the calendar aging model" (S-c p. 82; based on 25 vs 40 C test points).

Differential form (S-c Sec. 5.2.3, p. 83):
Eq. 5.26 dQ_loss,cyc/dFEC = k_C-rate,Qloss(C-rate) * k_DOC,Qloss(DOC) * (2 sqrt(FEC))^-1
Eq. 5.27 dR_inc,cyc/dFEC = k_C-rate,Rinc(C-rate) * k_DOC,Rinc(DOC)
Eq. 5.28 FEC*_cyc = ( Q_loss / (k_C-rate,Qloss(C-rate) * k_DOC,Qloss(DOC)) )^2   (virtual FEC)

Combined model (S-c Sec. 5.3, p. 84): simple superposition
Eq. 5.29 Q_loss,comb = k_temp,Qloss(T) k_SOC,Qloss(SOC) sqrt(t) + k_C-rate,Qloss(C-rate) k_DOC,Qloss(DOC) sqrt(FEC)
Eq. 5.30 R_inc,comb = k_temp,Rinc(T) k_SOC,Rinc(SOC) t + k_C-rate,Rinc(C-rate) k_DOC,Rinc(DOC) FEC
Stress is characterised by a half-cycle detection algorithm (DOC, mean C-rate, mean SOC per half-cycle) (S-c p. 85). Validation over 885 days at 40 C: capacity error about 0.5 % (PV home-storage profile) and about 1 % (PV + primary-control-reserve profile) at end of test (S-c pp. 85-86).

## 4. Validity range (from S-c)

| Item | Range tested | Notes (S-c) |
|---|---|---|
| Calendar, temperature | stored at 0, 10, 25, 40, 60 C (Table 4.4) | Model fitted with 25, 40, 60 C only; 0 and 10 C "show ambiguous results" (p. 72). Treat < 25 C as extrapolation. |
| Calendar, SOC | 0 to 100 % (9 levels at 40 C; 0/50/100 % at 25 and 60 C) (Table 4.4) | Anode-overhang effects at very low/high SOC not modelled (p. 69); larger errors at SOC 87.5 % and 100 % (p. 74). |
| Calendar, duration | 29 months static; 9 months (270 d) dynamic | |
| Cycle, temperature | 25 and 40 C (Table 4.6) | Additional ageing expected below 25 C or above 40 C, not covered (p. 77). |
| Cycle, C-rate | fit uses 0.2, 0.5, 1.0 C at 80 % DOC (Fig. 5.4) | Asymmetric/2 C discharge test points exist in Table 4.6 but are not in the fitted C-rate law. |
| Cycle, DOC | 5-100 % (plus a 1 % point) around 50 % mean SOC | DOC < 80 % show "unsteady aging trends with periods in which the capacity increases again, which is not described by the aging model" (p. 77). Model does not include mean-SOC dependence of cycling. |
| Cycle, duration | up to about 11,000 FEC, 885 days | |

## 5. How to use as a smooth ageing cost A in an hourly dispatch simulation at 25 C  [JC - team adaptation, not from the papers]

All of this section is the team's proposal. Only the equations it starts from are from S-c.

1. **Temperature.** At T = 25 C the Arrhenius factor equals 1, so k_temp,Qloss = k_ref,Qloss = 0.0012571 % s^-0.5 = 0.0012571 * sqrt(3600) = 0.075426 % h^-0.5. [JC] Fixing 25 C is an assumption (indoor, conditioned battery). Baghdad ambient temperatures are far above this in summer; by Eq. 5.3 the calendar rate would be x1.25 at 35 C and x1.54 at 45 C [JC computation]. Report a sensitivity run at 35 C rather than claiming 25 C is realistic.
2. **Calendar part, integrated over SOC(t).** Keep the state Q_cal (in %). For each hour h with SOC_h (use the hour-average or the end-of-hour SOC; state which):
   - k_h = k_ref * (2.8575 (SOC_h - 0.5)^3 + 0.60225)   [% h^-0.5]
   - t*_h = (Q_cal / k_h)^2   (Eq. 5.17)
   - dQ_cal,h = k_h * ( sqrt(t*_h + 1 h) - sqrt(t*_h) )   (equivalent to integrating Eq. 5.15 with virtual time; same as S-e Eq. 33)
   - Smooth marginal form for optimisation [JC]: dQ_cal/dt = k_h / (2 sqrt(t*_h)) = k_h^2 / (2 Q_cal). For a short planning horizon treat Q_cal as constant (S-e makes the same simplification), so the per-hour calendar cost is a smooth, convex-in-k function of SOC: A_cal,h = lambda * k(SOC_h)^2 / (2 Q_cal0) * 1 h. Note k(SOC) > 0 on [0,1] (minimum 0.245 at SOC = 0), but k(SOC)^2 is not convex in SOC everywhere; if the optimiser needs convexity, use a piecewise-linear fit (S-e used 10 segments).
   - Q_cal must start > 0 (sqrt(t) has infinite slope at t = 0). [JC] Initialise from the battery's assumed age (e.g. Q_cal after 1 year at 50 % SOC, 25 C = 4.25 % by Eq. 5.1) and state it.
3. **Cycle part, integrated over throughput.** FEC per hour = (E_charged,h + E_discharged,h) / (2 * E_nominal) [JC definition; S-c uses Ah-throughput-based FEC]. The model also needs DOC and C-rate per half-cycle. Options [JC]:
   - (a) Reference: run the S-c half-cycle detection post hoc on the simulated SOC series and apply Eqs. 5.26/5.28 per half-cycle (exact model use, but not smooth).
   - (b) Smooth proxy for the optimiser: fix C-rate at the battery's typical household rate (e.g. 0.25-0.5 C) and DOC at a representative value, giving a constant k_cyc = (0.0630 C + 0.0971)(4.0253 (DOC - 0.6)^3 + 1.0923) and dQ_cyc,h = k_cyc^2 / (2 Q_cyc) * dFEC_h (virtual-FEC marginal form). Evaluate (b) against (a) and report the gap.
4. **Money.** A_h = lambda * (dQ_cal,h + dQ_cyc,h), with lambda = battery replacement cost / capacity-loss budget to end of life (e.g. 20 %-points if EOL = 80 % SOH) [JC; the 20 % EOL criterion is the one S-c uses on p. 83, the cost basis is the team's]. Resistance increase (R_inc) is ignored in A [JC]; say so.
5. **Sanity checks (computed by the team from S-c Table 5.1/5.3) [JC]:** at 25 C, one year of storage gives Q_cal = 1.73 % (SOC 0), 4.25 % (SOC 0.5), 6.77 % (SOC 1.0). So holding the battery full versus half-full costs about 2.5 %-points of capacity in the first year; this is the term that makes "always-full reserve" non-free in the S1 value-of-forecast comparison. Pure cycle loss for 365 cycles at 0.5 C and 80 % DOC: about 2.8 %.
6. **What must be stated in the paper [JC]:** model fitted on one 3 Ah Sony/Murata 26650 LFP cell type; calendar fit 25-60 C; cycle fit 25-40 C and 0.2-1 C; no cycling-SOC dependence; parameters taken from Naumann (2018) Tables 5.1 and 5.3; the household pack's actual cells may age differently, so A is an indicative cost and its scale lambda should be varied in a sensitivity analysis.
