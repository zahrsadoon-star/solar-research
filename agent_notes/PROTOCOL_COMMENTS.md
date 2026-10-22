# Protocol implementation comments

The repository release candidate controls this implementation. No protected source was changed.

- The approved calendar is absent. Smoke features omit holiday/Ramadan fields; benchmark execution fails closed. The lead must supply the calendar through the appropriate work package.
- Workbook Read Me describes positional reconstruction and partial January timestamp validation. Neither it nor the derived Outage Events table establishes interval-start versus interval-end energy semantics. Test 18 is a strict expected failure, not clearance of the scientific leakage gate. KR semantics also remain unverified.
- Static target-(a) climatology counts available training labels by their observed hour and queries the target hour. Target-(b) climatology counts training-complete windows by origin hour.
- A sparse transition cell triggers fallback of its entire conditioning-state row to preserve normalization. Recency fits at midnight exclude the row beginning at midnight, whose energy is not yet available at that issuance instant.
- Threshold candidates are distinct validation probabilities plus the all-negative rule. Equal MCC selects the smallest threshold. Degenerate ROC/AP and undefined ratios return NaN; zero-denominator MCC/F1 return zero.
- BCa acceleration uses a delete-nonoverlapping-block jackknife within month; this dependence-aware choice requires lead approval before benchmark inference.
- The corrected PW circular estimator is implemented locally because arch is unavailable and package installation is blocked. Its reference is the published arch source documentation: https://arch.readthedocs.io/en/latest/_modules/arch/bootstrap/base.html . Constants internal to this named estimator are mathematical algorithm constants rather than study settings.
- Dispatch and its parameter-selection rules remain WP7, not implemented here. The artifact selection API rejects paths outside predictions/innerval/.
