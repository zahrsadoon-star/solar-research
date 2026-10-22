# Literature officer notes - S1 (2026-10-22)

Output: literature/S1_verified_sources.md (full table, sources, numbers).

## Method
- Read literature/novelty_check.md and literature/S1_related_work_alphaxiv.md first.
- Verification via publisher pages, Crossref API records (WebFetch), arXiv full text (alphaXiv), White Rose eTheses.
- Search via WebSearch, Consensus (6 queries) and alphaXiv discover (1 query).
- Shell curl to Crossref and nahje.com was blocked by the proxy (403); WebFetch worked instead.

## Verification result
All 10 requested references were VERIFIED. Missing items: neither the thesis nor NASA POWER has a DOI, and the DOI of Reindl 1990a "Diffuse fraction correlations" was not checked.
Corrections: Kebede 2021 title; Babu full name and vol/article number (RinEng 32, 113342); thesis author spelt "Alshamri".

## Key finding for the novelty claim
Jawad & Al-Shammari (2025), NJES 28(2) 212-223, doi:10.29194/NJES.28020212 already applies a 1D-CNN to Baghdad outage hours,
using hourly data for 2023 and daily data for 2019-2023 at 132 kV station-group level, with a random 80/20 split. It must be cited, and S1's
"first ML forecaster of Iraqi load shedding" framing must be dropped. The remaining gap: household level, time-ordered validation,
Markov/persistence baselines, and decision value for PV-battery dispatch.

## Open items for the lead
1. The 2015/2017 IBT values were not readable in Alshamri et al. (2024). Confirm from the thesis that the 2018 schedule = 10/35/80/120 IQD/kWh.
2. No Karbala-specific generator ampere price found. Baghdad 2018 = 25,000 IQD/A/month (Al Jazeera, news); peer-reviewed alternatives
   are Al-Wakeel 2021 (USD 5-10 standard, USD 21 golden summer) and Mohammad & Ismael 2019 (8,000 IQD/A controlled).
3. No peer-reviewed quantification of the load-shedding vs temperature correlation in Iraq. S1 can compute it from the 2018 record and report it.
4. DOIs for the Consensus-only items in the section-3 table (Akinola 2024, Sivhugwana 2025, Aldarraji 2024, Albaqir 2019, Osman 2026,
   Shah 2022, Mrayeh 2025, Abood 2021) are still [UNVERIFIED].
