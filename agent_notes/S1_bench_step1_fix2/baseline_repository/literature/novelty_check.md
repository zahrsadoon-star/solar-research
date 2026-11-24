# Novelty check (2026-10-21, Consensus search, 2019-2026)

Closest prior work found for the top-ranked directions. Links are Consensus record pages; DOIs still
**[UNVERIFIED]** and must be confirmed from the publisher page before any citation.

## Outage modelling / value of foresight (ideas 1, 2, 5, 8, 11, 14)
- Kebede et al., 2021, *Energies* - GA sizing of PV-battery on a weak Ethiopian grid with recorded outages; Markov vs Weibull outage models; Monte Carlo robustness. -> stochastic outage sizing itself is NOT new. https://consensus.app/papers/details/601e98e5e7d15b98bb8122bf8edf2174/
- Babu, 2026, *Results in Engineering* - "Resilience value of distributed PV and battery systems under grid-unreliability regimes": synthetic regimes (outage fraction, duration, predictability, timing) anchored on Dhaka, Sobol indices; reports that grid-charging permission, not foresight, explains PV reduction, while foresight cuts grid import. -> **closest competitor to idea 8**; uses synthetic regimes and an abstract predictability parameter, not a learned forecaster on measured data. https://consensus.app/papers/details/f7ad2a8c44e7582193221086dc937b89/
- Chatterji et al., 2020, *IEEE Access* - stochastic PV/BESS planning for storm outages (US). https://consensus.app/papers/details/95f0b09a35745657850e61df93b40633/
- Hunter-Rinderle et al., 2023, *IEEE OAJPE* - two-stage stochastic storage scheduling for outage resilience; myopic charging when outage probability is low. https://consensus.app/papers/details/a601970a62765d0b92cc20ed401c7711/
- Samy et al., 2021, *IEEE Access* - MOPSO design with grid availability 70-100 % (Egypt), availability as a fixed percentage. https://consensus.app/papers/details/4d251788c1095b2588d5f6770de6380d/
- Shivam et al., 2021, *Energy Conversion and Management*; Sorour et al., 2021/2022, *IEEE Access* - forecast-based residential EMS, but on reliable grids (cost / self-consumption objectives, no outages).

**Gap:** no study found that tests predictive EMS with a *learned, imperfect* outage forecaster trained on a
*measured* long outage record (49 % unavailability, 59 h max), nor one that checks Babu's (2026) synthetic-regime
conclusion on real data. Probabilistic (quantile/conformal) reserve setting under outages also not found.

## Degradation and heat (ideas 20, 21, 22, 24)
- Sowe et al., 2022, *Journal of Energy Storage* - in islanded mini-grids 80-90 % of capacity fade is calendar ageing; SOC-based derating extends life most. https://consensus.app/papers/details/c6d9e451478c5fc1971faff84d6bd732/
- Wu et al., 2022, *Renewable Energy* - degradation-aware optimal battery capacity for grid-connected PV-battery (no outages). https://consensus.app/papers/details/dc366d6f32c3564dabd3ae3df258c389/
- Apribowo et al., 2022, *Batteries* - review: ambient-temperature degradation is under-represented in BESS planning. https://consensus.app/papers/details/f9fe3bf122765f2fbc83d2abd08e7df4/
- Abdullah, 2026, *Engineering Research Express* - hot-desert (Saudi) PV-BESS-V2H sizing with wear and outage resilience, rule-based EMS.

**Gap:** the specific trade-off that outage-readiness policies (keeping SOC high, as Mode 0 does) accelerate
calendar ageing in extreme heat - and the resulting optimal reserve-SOC policy - was not found.

## Iraq dual-supply market (ideas 6, 30, 31, 32, 39, 45)
- Tahir et al., 2024, *Renewable Energy* - Iraq NDG -> PV transition; Delphi survey; load profiles **adapted from Spain**; HMGS with NDG savings. https://consensus.app/papers/details/f22e73d14deb5faa998c18e36983feb6/
- Bou Gebrael et al., 2026, *Applied Energy* - bi-level game-theoretic model of household PV feed-in vs a monopolistic diesel-generator company (Lebanon). https://consensus.app/papers/details/736f17bcd2cd5d13938a9c0c481e1111/
- Mejeed, 2025, *Energy Storage* - Baghdad home, monthly bills, HOMER PV/BSS vs DG. https://consensus.app/papers/details/1f58105792fd50e0959e6dc2f5c889d0/
- Al-Wakeel, 2021 (book chapter) - description of Iraqi NDG networks and per-ampere monthly billing. https://consensus.app/papers/details/8593dbda2ebb5032b9448a1634ba2660/
- Alasadi et al., 2025 (Najaf, installed system); Al-khaykan et al., 2022, *Energies* (Karbala, HOMER multi-year).

**Gap:** treating the household's **ampere subscription** to the neighbourhood generator as a design variable
(with its hard current cap) jointly with PV and battery, on measured hourly data, was not found.

## Not yet checked
Ideas 15/16/19 (optimiser benchmark, MILP gap, landscape analysis) and 28/29 (transposition, multi-year weather):
first-pass novelty only.
