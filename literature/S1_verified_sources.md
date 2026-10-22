# S1 verified sources (literature officer, 2026-10-22)

Checked against: publisher pages, Crossref API records (fetched via WebFetch), arXiv full text (alphaXiv), repository pages.
VERIFIED = bibliographic fields confirmed on the URL given. NOT FOUND = could not be confirmed; do not cite the missing field.
No DOI below was typed from memory; each is copied from the page cited next to it.

---------------------------------------------------------------------------------------------------
## 1. Bibliographic verification

| # | Reference (as it should be cited) | Status | Checked at |
|---|---|---|---|
| 1 | Babu, R. M. (2026). Resilience value of distributed PV and battery systems under grid-unreliability regimes. *Results in Engineering*, 32, 113342. doi:10.1016/j.rineng.2026.113342 | VERIFIED (Crossref: journal, vol 32, article 113342, issue date 2026-12; author ORCID 0009-0005-4316-8190). Data/code: Mendeley Data doi:10.17632/yvcnm54hkc.1 (8 Jul 2026, Univ. of Asia Pacific). Two SSRN preprints also exist (10.2139/ssrn.7090698, 10.2139/ssrn.7124086); cite the journal version. | https://api.crossref.org/works?query.bibliographic=Resilience+value+of+distributed+PV+and+battery+systems+under+grid-unreliability+regimes ; https://data.mendeley.com/datasets/yvcnm54hkc/1 |
| 2 | Kebede, F. S., Olivier, J.-C., Bourguet, S., & Machmoum, M. (2021). Reliability evaluation of renewable power systems through distribution network power outage modelling. *Energies*, 14(11), 3225. doi:10.3390/en14113225 | VERIFIED. **Title correction:** the paper is NOT titled as a "PV-battery sizing" paper; correct title above. Content confirmed: Markov and Weibull outage models, GA sizing of PV-battery, Addis Ababa university building load, 5 years of recorded outages. | https://www.mdpi.com/1996-1073/14/11/3225 ; https://ideas.repec.org/a/gam/jeners/v14y2021i11p3225-d566595.html |
| 3 | Essus, Y., Vatsavai, R. R., & Rachunok, B. (2026). Data leakage inflates generalizability of power outage prediction models. arXiv:2608.24665 [cs.LG], v1, 25 Aug 2026. | VERIFIED (arXiv stamp in full text; affiliations Toronto / NC State). No journal version found. | https://arxiv.org/abs/2608.24665 |
| 4 | Enyam, K. B., Koepele, C., Asare, T., Wallington, K., & Lygeros, J. (2026). Scenario-based stochastic MPC for energy hubs with EV fleets under persistent grid outages. arXiv:2604.18268 [eess.SY], v1, 20 Apr 2026. | VERIFIED. Content confirmed: 2-state CTMC outage model with rates "approximated from resident surveys" (2023), Ashesi Univ. Ghana, SMPC within 0.39 % of perfect-forecast cost; naive MPC up to 6.85 % higher cost and ~446 % more diesel CO2. No journal version found. | https://arxiv.org/abs/2604.18268 |
| 5 | Alshamri, H. A. H. (2019). *Optimal sizing of hybrid renewable systems to improve electricity supply reliability in Iraqi domestic dwellings*. PhD thesis, University of Leeds (Energy Research Institute, School of Chemical and Process Engineering). Submitted 14 Oct 2019; deposited 6 May 2020. White Rose eTheses id 26446; EThOS uk.bl.ethos.804538. | VERIFIED (title, author, year, repository). **No DOI** - cite with the repository URL. Spelling on record is "Alshamri" (not "Al-Shamri"). | https://etheses.whiterose.ac.uk/id/eprint/26446/ |
| 6 | Alshamri, H., Cockerill, T., Tomlin, A. S., Al-Damook, M., & Al Qubeissi, M. (2024). On-off-grid optimal hybrid renewable energy systems for house units in Iraq. *Clean Technologies*, 6(2), 602-624. doi:10.3390/cleantechnol6020032 | VERIFIED. Note: paper mentions Iraq's increasing block tariff (2015 and 2017 IBT prices in figures) but gives no numeric outage hours in the text that was readable. | https://www.mdpi.com/2571-8797/6/2/32 ; https://ideas.repec.org/a/gam/jcltec/v6y2024i2p32-624d1391107.html ; https://eprints.whiterose.ac.uk/212944 |
| 7 | Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. *Solar Energy*, 28(4), 293-302. doi:10.1016/0038-092X(82)90302-4 | VERIFIED (Crossref DOI record). | https://api.crossref.org/works/10.1016/0038-092X(82)90302-4 |
| 8 | Reindl, D. T., Beckman, W. A., & Duffie, J. A. (1990). Evaluation of hourly tilted surface radiation models. *Solar Energy*, 45(1), 9-17. doi:10.1016/0038-092X(90)90061-G | VERIFIED (Crossref). This is the HDKR transposition paper. The companion "Diffuse fraction correlations", *Solar Energy* 45(1), 1-7 (1990) exists (pvlib docs) but its DOI was NOT checked. | https://api.crossref.org/works?query.bibliographic=Evaluation+of+hourly+tilted+surface+radiation+models+Reindl |
| 9a | Anderson, K. S., Hansen, C. W., Holmgren, W. F., Jensen, A. R., Mikofski, M. A., & Driesse, A. (2023). pvlib python: 2023 project update. *Journal of Open Source Software*, 8(92), 5994. doi:10.21105/joss.05994 | VERIFIED (preferred current pvlib citation). | https://joss.theoj.org/papers/10.21105/joss.05994 |
| 9b | Holmgren, W. F., Hansen, C. W., & Mikofski, M. A. (2018). pvlib python: a python package for modeling solar energy systems. *Journal of Open Source Software*, 3(29), 884. doi:10.21105/joss.00884 | VERIFIED (Crossref). | https://api.crossref.org/works/10.21105/joss.00884 |
| 10 | NASA POWER. Acknowledgement text required by NASA: "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division." Data reference: "The data was obtained from the POWER Project's Hourly 2.x.x version on YYYY/MM/DD." | VERIFIED (official referencing page). **No DOI** is given by NASA; record the exact API version and access date from our download log. | https://power.larc.nasa.gov/docs/referencing/ |

---------------------------------------------------------------------------------------------------
## 2. Iraqi electricity context - numbers with sources

### (a) National-grid residential tariff (increasing block tariff, monthly consumption)

| Block (kWh/month) | IQD/kWh | US cents/kWh (Al-Wakeel 2021, at 1,200 IQD/USD) |
|---|---|---|
| 1-1,500 | 10 | 0.83 |
| 1,501-3,000 | 35 | 2.92 |
| 3,001-4,000 | 80 | 6.67 |
| > 4,000 | 120 | 10.00 |

- Al-Wakeel, A. (2021). Local energy systems in Iraq: neighbourhood diesel generators and solar photovoltaic generation. In N. Jenkins (Ed.), *Microgrids and Local Energy Systems*. IntechOpen. doi:10.5772/intechopen.95280. Table 4: Federal Ministry of Electricity residential tariff, September 2020, in US cents (values above). VERIFIED at https://www.intechopen.com/chapters/74439
- Attaqa (energy news site, 19 Nov 2025): the same four blocks in IQD (10 / 35 / 80 / 120), average residential price about 19.375 IQD/kWh, last broad revision in 2016, government review underway. https://attaqa.net/?p=555076 (news source, not peer-reviewed; use only to support the IQD values).
- Alshamri et al. (2024) note that Iraq uses an IBT and model 2015 and 2017 IBT prices; the values were not readable on the page we could fetch. The 2018 data year falls under the 2016/2017 schedule. **Open item:** confirm from thesis Ch. on tariffs that the 2018 schedule equals the table above.

### (b) Neighbourhood (private) generator price, IQD per ampere per month

| Year | Place | Price (IQD/A/month) | Source |
|---|---|---|---|
| summer 2018 | Baghdad | 25,000 (about USD 21) | Al Jazeera, 31 Jul 2018, https://www.aljazeera.com/news/2018/7/31/electricity-cuts-across-iraq-make-life-unbearable-in-summer-heat (news) |
| c. 2014-2019 | Iraq (unnamed region) | 8,000 "controlled" price | Mohammad, A. Th., & Ismael, A. I. (2019). An equivalent photovoltaic solar system to solve the problems of electricity in Iraqi houses. *AIMS Energy*, 7(5), 660-670. doi:10.3934/energy.2019.5.660 (peer-reviewed). https://aimspress.com/aimspress-data/aimse/2019/5/PDF/energy-07-05-660.pdf |
| c. 2020 | Iraq, typical provincial-council tariff | standard line: USD 10 (summer), 7.5 (spring/autumn), 5 (winter); 24-h "golden" line: USD 21 (summer), 12.5 (spring/autumn) | Al-Wakeel (2021), Table 5 (peer-reviewed chapter). Year and city not stated in the table; set by provincial councils. |
| Jun 2023 | Baghdad | 6,000 (day line), 9,000 (night line), 12,000 (24-h golden); +1,000-2,000 without fuel allocation | Shafaq News report, 5 Jun 2023, https://shafaq.com/en/Report/Fuel-allocation-and-rising-ampere-prices-Iraq-grapples-with-chronic-summer-power-shortages (news) |
| Jun 2023 | Najaf | 7,000 official standard; 14,000-17,000 golden (unofficial) | same Shafaq report |
| Sep 2026 | Baghdad | about 20,000 per ampere (5 A = about 100,000 IQD/month); may nearly double in summer | Shafaq News, 22 Sep 2026, https://shafaq.com/en/society/Two-electricity-bills-strain-Iraqi-household-budgets (news) |

Also: Baghdad > 13,000 neighbourhood generators, Iraq 55,000-80,000 (Al-Wakeel 2021). A Karbala-specific ampere price was **NOT FOUND**.

### (c) Daily hours of grid supply / load shedding

- Al-Wakeel (2021): summer 2020, Iraq excluding Kurdistan, consumers averaged 14-16 h/day of electricity of which **only 6-8 h/day from the public grid**; interruptions "up to 18 hours a day".
- Al Jazeera (31 Jul 2018): Baghdad households from 2-4 h/day up to 20 h/day depending on neighbourhood; national production about 70 % of need (Ministry spokesman).
- Mohammad & Ismael (2019, AIMS Energy): grid power available "less than 12 hours per day".
- Jawad & Al-Shammari (2025, NJES 28(2), 212-223, doi:10.29194/NJES.28020212): Baghdad 2023 hourly data, summer outages of 12-14 h on many days; spring up to 5 h; autumn mostly 0-2 h; winter peak 13 h (11 Jan).
- Mrayeh et al. (2025, *Int. J. Heat and Technology*): "Iraqi homes currently experience power outages for 12 hours per day during the summer" (Consensus abstract; DOI not checked).
- MEES (Al-Maleki, 28 Jun 2024): record peak demand 48 GW on 21 Jun 2024 vs about 25 GW generation (gap about 23 GW); 2023: demand 40 GW vs maximum supply 26 GW (gap 14 GW); temperatures above 50 °C. https://www.mees.com/2024/6/28/refining-petrochemicals/iraq-grapples-with-mammoth-summer-peak-load/7cd623a0-354e-11ef-8388-734184aca7a9 (trade press)
- IEA (2019) *Iraq's Energy Sector: A Roadmap to a Brighter Future* (25 Apr 2019): gap between peak demand and maximum grid supply widened 2014-2018; network losses about 40 TWh, four times neighbourhood-generator output. No hours-per-day figure in the web text. https://www.iea.org/reports/iraqs-energy-sector-a-roadmap-to-a-brighter-future
- Our own record (thesis data, 2018): 49 % unavailability, 59 h maximum outage (from novelty_check.md) - consistent with 12 h/day order of magnitude.

### (d) Does load shedding track temperature / peak demand in Iraq?

Evidence FOR (mostly indirect):
- Demand-temperature link is strong: Al-Fahdawi (2015, PhD thesis, Univ. of Anbar, in Arabic) reports consumption-temperature correlation up to r = 0.997 (Nasiriyah, summer) and that gas/diesel plants produce about 20 % less in summer (capacity derating). https://www.home.iqdr.iq/search/print/67be463af95174d72a974aef9f4b4647
- Supply gap peaks with heat: MEES 2024 (48 GW demand vs 25 GW supply at > 50 °C).
- Jawad & Al-Shammari (2025): longest outages in summer for Baghdad 2023, but **no correlation coefficient** reported; winter has a second peak (13 h) that they blame on cold damaging cables -> relation is non-monotonic.
- Abood et al. (2021, LNEE): Baghdad 2018 demand driven mainly by temperature (max/min/mean) via air-conditioning (Consensus abstract).
- Albaqir et al. (2019, *Int. J. Energy Sector Management*): Najaf 11 kV feeder; load-shedding schedule distorts load curves; temperature used as input (Consensus abstract).

Evidence AGAINST / gap: **no peer-reviewed study found that quantifies the correlation between household-level load-shedding hours and temperature in Iraq.** Outage allocation is also driven by provincial quotas and dispatcher decisions (IEEE Spectrum 2008 "Iraq electricity by the numbers": provinces taking more than their share). -> S1 can report this correlation itself from the 2018 record (new, small contribution).

---------------------------------------------------------------------------------------------------
## 3. Prior ML forecasting of load shedding / grid availability (not weather-event outage counts)

| # | Work | What it does | How S1 differs |
|---|---|---|---|
| 1 | Jawad, S. J., & Al-Shammari, S. W. (2025). Convolutional neural networks for predicting power outages in Baghdad. *Al-Nahrain Journal for Engineering Sciences*, 28(2), 212-223. doi:10.29194/NJES.28020212 (VERIFIED, https://nahje.com/index.php/main/article/view/1307) | 1D-CNN predicts outage hours from load (MW) and temperature; hourly 2023 for Baghdad, daily 2019-2023 for two groups of 15 x 132 kV stations; random 80/20 split; MAE 0.0077 (normalised). | **Closest prior work - must be cited.** S1: household level (not 132 kV station groups), two cities, binary/probabilistic availability, time-ordered evaluation against persistence/Markov baselines, and the decision value for PV-battery dispatch. Their random split is exactly the leakage Essus (2026) warns about. |
| 2 | Akinola, S. et al. (2024). Optimal electricity load interruption based on time series classification with super learner and feature filtering. *IEEE Access* (Consensus record, DOI not checked) https://consensus.app/papers/details/65f6810da7e65c938a8c355aaf5c8442/ | Binary classification of South African hourly load-shedding stages (system level) with an ensemble super learner. | National system stage, not a household; no dispatch use. |
| 3 | Sivhugwana, K. S. et al. (2025). Short-term forecasting of unplanned power outages using machine learning algorithms... *Energies* (Consensus, DOI not checked) https://consensus.app/papers/details/2c6e0266c5185b7fb75acf49db524067/ | Hybrid RVM-WT-AdaBoost-RF stack forecasting Eskom unplanned outage (MW) at system level. | System-level MW of unplanned generator outages; S1 forecasts end-user supply state. |
| 4 | Aldarraji, M. et al. (2024). Addressing energy challenges in Iraq: forecasting power supply and demand using AI models. *Heliyon* (Consensus, DOI not checked) https://consensus.app/papers/details/b2b297db6d045eaaa77bee0eddafad30/ | LR, XGBoost, RF, LSTM, TCN, MLP for national supply and demand, MoE data 2019-2021, 24-168 h horizons. | Forecasts national MW, not whether a given household has grid; no outage target or dispatch. |
| 5 | Albaqir, M. A. et al. (2019). A new load forecasting model considering planned load shedding effect. *Int. J. Energy Sector Management* (Consensus, DOI not checked) https://consensus.app/papers/details/9ef6585e53245dd2bc4ce301ca571806/ | Neuro-fuzzy load forecast for an 11 kV Najaf feeder with the shedding schedule as an input. | Uses the schedule as a known input; S1 forecasts the shedding itself. |
| 6 | Osman, M. et al. (2026). LATENT: low-latency anomaly tracking in national electricity time-series... Bangladesh PGCB grid (Consensus) https://consensus.app/papers/details/24749376b20b527490d2bbf260d8575a/ | Unsupervised LSTM + residual model on PGCB generation/demand/load-shedding records; early warning up to 3 h before major outages. | National anomaly detection, not household availability probability. |
| 7 | arXiv:2507.01034 (2025). LSTM electricity forecasting in Benghazi, Libya, under frequent load shedding. https://www.alphaxiv.org/abs/2507.01034 | Load/demand forecasting where load shedding distorts data. | Demand target, not outage target. |
| 8 | arXiv:2509.17097 (2025). ML for campus energy resilience: clustering and time-series forecasting in intelligent load shedding (Univ. of Lagos). https://www.alphaxiv.org/abs/2509.17097 | Forecasts campus load to decide what to shed. | Utility-side shedding decision; S1 is the consumer facing exogenous shedding. |
| 9 | Shah, Z. et al. (2022). The electricity scene from above: exploring power grid inconsistencies using satellite data in Accra, Ghana. *Applied Energy* (Consensus) https://consensus.app/papers/details/6fb371dfda0f5984ad4df1e1fd62d743/ | Detects (nowcasts) outages from nightlights, trained on ground PowerWatch sensors. | Detection after the fact, not forecasting; no dispatch. |
| 10 | Enyam et al. (2026), arXiv:2604.18268 (see sec. 1) and Babu (2026) (see sec. 1) | Use outage *models* (CTMC with survey rates; synthetic regimes with a predictability knob) inside dispatch/sizing. | S1 trains an actual forecaster on a measured household record and measures its dispatch value against these model classes. |

Not relevant but checked: Oluwasuji et al. (AAMAS 2018) allocate load shedding across simulated Nigerian households (no forecasting); GIST-Grid (ICML 2026 MusIML workshop) is Nigerian load forecasting, not outages. No Lebanon or Pakistan study forecasting household supply hours was found.

---------------------------------------------------------------------------------------------------
## 4. Corrections to earlier notes
1. Kebede et al. 2021 title is "Reliability Evaluation of Renewable Power Systems through Distribution Network Power Outage Modelling" (novelty_check.md describes the content correctly but not the title).
2. Babu's full name on the record is Riad Mollik Babu; *Results in Engineering* 32, 113342.
3. Thesis author spelling: Alshamri, Hussain Ali Hatam.
4. Novelty claim must be softened: Jawad & Al-Shammari (2025) already forecast outage hours in Baghdad with ML (station-group level). S1's novelty is household level + honest time-ordered evaluation + value for dispatch.
