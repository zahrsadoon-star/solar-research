# Research ideas extending the Baghdad MSc thesis

## Scope and evidence boundary

This is a research planning document, not a manuscript or a results report. The effort ranges below are planning estimates for one researcher, including implementation, experiments and an initial paper draft after access to required data; collection, procurement and publication delays are additional. Rankings are qualitative judgments, not measured scores. No improvements or publication outcomes are promised.

Read first: `AGENTS.md` and `README.md`. Baseline evidence: `legacy/REFERENCE_RESULTS.md` and inspected sections of `legacy/thesis_model.py`. The thesis already covers residential PV, battery and inverter sizing, GNPSO, comparisons against GA and PSO, multiple EMS modes, RF outage forecasting, an LSTM load module, forecast-based sizing and economic sensitivity. Merely changing the optimizer, predictor, site or objective weights is insufficient.

The supplied context describes an hourly annual record with approximately half the hours unavailable and a long multiday outage. Those statistics and frozen thesis performance values have not been independently reproduced here and are not new results. `data/BG1-8760.xlsx` is present; its contents were not audited in this task. The code interprets its columns as grid and generator energy, assigns a calendar index and infers grid status from positive grid energy. Meter timestamps, the distinction between zero consumption and outage, and whether generator consumption represents unconstrained demand need validation.

Important baseline qualifications:

- Mode 0 includes low-PV grid charging below a state-of-charge trigger. A threshold-based predictive mode also exists; introducing any forecast-aware controller is therefore not sufficient novelty.
- The combined annual forecast block constructs outage-hour loads from hourly historical means despite an LSTM comment. A new study must distinguish the trained LSTM module from predictions actually used downstream.
- Battery replacement already depends on an aggregate cycling estimate; simply adding a replacement cost is not a new contribution.
- The frozen reference identifies an HDKR-versus-isotropic irradiance-model discrepancy. Correcting it is validation work, not automatically a paper.
- Any corrected simulator must remain separate from the frozen thesis baseline, with differences explained before attributing gains to a new method.

All claims of novelty relative to the wider literature below are **candidate contributions [UNVERIFIED]**, pending a focused literature review. Prior work is described generically; no papers or DOIs are asserted. A Q1 target requires a defensible gap and convincing evidence, not a particular algorithm name.

## Data availability and common evaluation plan

**T — thesis data:** the workbook and legacy code are locally available. Actual grid-status logs, appliance data, measured PV output, battery telemetry, multiple households and additional measured years have not been established as available.

**P — public weather:** official documentation confirms hourly radiation/PV time-series and TMY services in [PVGIS](https://joint-research-centre.ec.europa.eu/pvgis-online-tool_en), solar and meteorological time series through the [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/), and hourly reanalysis through [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=documentation). These are public source options, not downloaded or locally validated datasets. Check Baghdad coverage, variables, access requirements, time conventions and units before use. They do not supply household demand, utility outages, battery aging measurements or future climate projections. Products may share upstream information and must not be treated as independent ground truth.

**C — collection or external evidence needed:** each idea identifies missing inputs explicitly. Synthetic scenarios can support conditional simulation findings but cannot substitute for measured validation. A repeated thesis load year paired with different weather years is weather sensitivity, not independent multiyear household evidence. TMY weather cannot establish historical weather–outage dependence.

For a selected study, preregister primary outcomes, comparisons, scenario construction and compute budgets before examining test performance. Use forward chronological training, validation and held-out evaluation, fitting transformations only on training data and excluding features unavailable at decision time. Preserve outage episodes and seasonal dependence; separate uncertainty across weather/outage scenarios from optimizer variability. A single household-year limits seasonal and geographic generalization.

Proposed stochastic-run protocol: fixed seeds `11, 23, 37, 53, 71, 89, 107, 131, 157, 181`, with every run retained and equal evaluation budgets across stochastic methods. These are proposed settings, not completed runs. Use paired methods on identical held-out scenario blocks; report effect sizes and block-bootstrap confidence intervals, with a paired block-level permutation test for the preregistered primary difference and Holm adjustment for multiple primary comparisons. The blocks must respect estimated dependence; if too few independent blocks exist, present descriptive uncertainty rather than unsupported significance. Optimizer seeds are not independent household observations. Report null findings, failures and computational cost. Method-specific calibration or coverage checks supplement, rather than replace, this protocol.

All eventual manuscript numbers must be generated by repository scripts and saved in `results/`; future equations in `method/` must identify their source and implementing file/function. This task adds no experiments, equations, datasets or manuscript claims.

## Thirty distinct ideas

### 01. Outage-tail-aware sizing
- **Research question:** How much does explicitly modeling outage duration change the cost of protecting a household against severe energy shortfalls?
- **Method:** Fit seasonal semi-Markov outage scenarios with duration-dependent restoration; jointly size equipment under expected cost and conditional value-at-risk of outage-event unserved energy. Compare with empirical replay, independent hourly outage sampling and expected-loss sizing; separate observed-event validation from extrapolated tail stress tests.
- **Data and availability:** T provides inferred outage sequences and load; P supplies weather scenarios. C: direct outage logs and additional years are needed to validate rare-event frequencies.
- **Candidate novelty:** Beyond single-trace sizing and annual reliability averages, identify when duration persistence changes equipment decisions and event-level protection in an intermittent-grid household.
- **Main risk:** One annual trace cannot identify extreme outage tails reliably; robust-looking designs may reflect arbitrary extrapolation.
- **Effort:** 10–14 weeks.

### 02. The operational value of forecasts
- **Research question:** When do improved outage and load forecasts produce measurable dispatch and sizing benefits over simple forecasts?
- **Method:** Run rolling-origin forecasts through the same constrained model-predictive controller; compare persistence, seasonal averages, RF/LSTM and calibrated probabilistic forecasts, with perfect information only as an unattainable bound. Evaluate fixed equipment first, then re-size under each policy to separate forecast value from capacity changes.
- **Data and availability:** T supports limited chronological backtesting; P supplies historical weather inputs. C: genuinely archived weather forecasts are needed for claims about operational weather forecast performance; otherwise use explicitly constructed forecast errors.
- **Candidate novelty:** Establish decision-relevant forecast value and break-even computational/data requirements, extending the thesis's forecasting and predicted-profile sizing rather than claiming a new predictor alone.
- **Main risk:** Forecast improvements may not change decisions, and the available record may be too short for stable comparisons.
- **Effort:** 10–14 weeks.

### 03. Joint capacity and reserve-policy design
- **Research question:** Does co-designing battery capacity and a time-varying reserve policy outperform sizing under fixed EMS rules?
- **Method:** Optimize equipment and a parsimonious reserve policy conditioned on season, outage history and forecast uncertainty; compare jointly optimized, sequentially optimized and fixed Mode 0 designs. Audit all policies under the same physical constraints and common information set.
- **Data and availability:** T supports initial policy training and testing; P provides solar variability. C: prospective controller logs are needed for field-performance claims.
- **Candidate novelty:** Quantify the interaction between hardware investment and reserve policy under unreliable grid charging, beyond selecting among predefined EMS modes.
- **Main risk:** Policy complexity can overfit the one-household trace and obscure whether hardware or control caused the result.
- **Effort:** 10–14 weeks.

### 04. Distributionally robust sizing under scarce outage data
- **Research question:** Can a design remain economical and reliable when the outage distribution estimated from a short record is wrong?
- **Method:** Construct ambiguity sets over duration-aware outage/load scenarios, calibrating uncertainty budgets on training and validation blocks. Compare distributionally robust, nominal stochastic and conservative worst-case sizing under held-out and explicitly shifted distributions; publish the cost of robustness.
- **Data and availability:** T supports initial empirical scenarios; P supplies weather variation. C: further outage records are required to test whether chosen shifts resemble actual changes.
- **Candidate novelty:** Tie robustness to finite outage-data uncertainty and quantify its decision value, distinct from fitting a better tail distribution in Idea 01.
- **Main risk:** Arbitrary ambiguity sets can make the study an exercise in selecting conservatism.
- **Effort:** 12–18 weeks.

### 05. Compound heat, low-solar and outage stress
- **Research question:** Does dependence among heat-driven demand, solar deficits and outages create larger sizing errors than treating these drivers separately?
- **Method:** Align historical weather with verified meter times; compare joint event/block resampling with dependence-breaking controls that preserve seasonal marginals. Attribute failures to individual stresses and their interactions, and re-size for compound-event exposure.
- **Data and availability:** T plus historical P weather can support exploratory alignment. C: independently logged outages and additional coincident load/weather years are needed for credible dependence estimates.
- **Candidate novelty:** Test the investment consequences of compound dependence rather than merely increasing load or outage frequency in separate sensitivities.
- **Main risk:** Assigned timestamps, limited events and common seasonality may create spurious dependence; do not infer causation.
- **Effort:** 12–18 weeks.

### 06. Reliability throughout battery aging
- **Research question:** How should reserve operation and replacement timing change when battery degradation erodes outage protection over the system lifetime?
- **Method:** Couple temperature-dependent calendar aging, cycle-depth damage and usable-power decline to dispatch, sizing and replacement decisions. Compare against the thesis's aggregate cycle-life replacement approximation and report reliability trajectories as well as lifecycle cost.
- **Data and availability:** T supplies load and operating assumptions; P supplies ambient weather. C: chemistry-specific aging parameters, enclosure thermal behavior and preferably battery telemetry are needed; ambient temperature alone is not cell temperature.
- **Candidate novelty:** Maintain a specified service level as storage ages under frequent outages, rather than treating aging only as a replacement expense.
- **Main risk:** Unvalidated aging parameters can dominate the recommended size and replacement year.
- **Effort:** 12–18 weeks.

### 07. Critical-service survival instead of annual LPSP
- **Research question:** Do systems with similar annual unserved-energy fractions offer substantially different continuity for essential household services?
- **Method:** Define service tiers with explicit interruption limits, optimize event-level survival and essential-load coverage, and compare with energy-averaged LPSP sizing at matched cost. Obtain critical-load definitions before optimizing; test sensitivity to household preferences.
- **Data and availability:** T supplies aggregate load and inferred outages; P supplies weather. C: appliance submetering and household-defined service priorities are needed; assumed tiers support scenarios only.
- **Candidate novelty:** Translate energy shortages into service-specific continuity guarantees and reveal investment trade-offs concealed by annual aggregation.
- **Main risk:** Arbitrary critical-load fractions or interruption penalties can predetermine the preferred design.
- **Effort:** 10–16 weeks.

### 08. Cooling flexibility as an alternative to battery capacity
- **Research question:** Can controlled precooling reduce electrical storage requirements while maintaining acceptable indoor conditions during outages?
- **Method:** Couple a calibrated building thermal model with PV-battery sizing and constrained cooling control; compare flexible and inflexible cooling under the same comfort limits. Include rebound demand, humidity where relevant and compressor power constraints.
- **Data and availability:** T provides aggregate electricity; P provides outdoor weather. C: indoor temperature, cooling-circuit power, building properties and occupant comfort requirements need collection.
- **Candidate novelty:** Co-design thermal and electrical buffering specifically for outage continuity, with comfort violations measured rather than hidden as load reductions.
- **Main risk:** Thermal-model error and uncertain occupant acceptance may overwhelm theoretical savings.
- **Effort:** 14–22 weeks.

### 09. Grid-restoration charging congestion
- **Research question:** Does simultaneous household battery charging after grid restoration undermine reliability gains predicted by independent sizing?
- **Method:** Model a constrained feeder with heterogeneous households and correlated outages; compare unconstrained Mode 0 charging with staggered or distributed charging under transformer and voltage limits. Jointly assess household equipment choices and network feasibility.
- **Data and availability:** T can seed a single household case; P supplies common weather. C: feeder topology, ratings, voltage measurements and multiple household profiles are needed; scaled copies are synthetic, not population evidence.
- **Candidate novelty:** Endogenize the ability to recharge after restoration instead of assuming an unlimited grid connection for every household.
- **Main risk:** Without utility data, realistic network conclusions are difficult to validate.
- **Effort:** 16–24 weeks.

### 10. Shared storage with fair outage service
- **Research question:** Under what conditions does shared storage lower cost without transferring outage risk to less flexible households?
- **Method:** Optimize individual and shared assets with network losses, correlated outages and household service constraints; compare cost-sharing mechanisms and participation stability at equal reliability. Vary diversity and correlation separately.
- **Data and availability:** T is one household only; P supplies local weather. C: multiple household profiles, connection costs, local sharing constraints and service preferences need collection.
- **Candidate novelty:** Evaluate whether pooling benefits survive common grid failure and explicit fairness constraints, rather than reporting aggregate savings alone.
- **Main risk:** Artificial household diversity can manufacture storage-sharing benefits.
- **Effort:** 16–24 weeks.

### 11. Diesel subscription as a discrete backup decision
- **Research question:** When should a household retain, reduce or cancel an amperage-based generator subscription after installing PV and storage?
- **Method:** Jointly choose PV-battery size and discrete backup subscription with current limits, service schedules and generator failures; compare cancellation assumptions with partial-retention options under equal outage-service targets.
- **Data and availability:** T contains generator energy and legacy subscription-cost assumptions; P supplies solar scenarios. C: actual contract tiers, service availability and current prices require local verification or collection.
- **Candidate novelty:** Represent the non-marginal cost and capacity of neighborhood generator service, rather than assuming every displaced unit of energy yields proportional savings.
- **Main risk:** Contract and service arrangements vary locally; historic thesis prices cannot establish current economics.
- **Effort:** 8–12 weeks.

### 12. Adaptive investment as grid reliability changes
- **Research question:** Is staged PV-battery investment preferable to a fixed upfront design when future grid reliability is uncertain?
- **Method:** Use multistage scenarios or real-options analysis for modular capacity additions, replacements and resale; compare immediate build-out with adaptive investment. Keep scenario probabilities explicit and test probability-free regret when they are unsupported.
- **Data and availability:** T anchors current operation and P supplies weather. C: longitudinal grid reliability, modular expansion costs and resale evidence are needed for empirically grounded transitions; otherwise use labeled scenarios.
- **Candidate novelty:** Make investment timing and reversibility central decisions rather than repeating one operating year across the asset life.
- **Main risk:** Speculative transition probabilities can dominate the option value.
- **Effort:** 12–18 weeks.

### 13. Meter-derived outage-label uncertainty
- **Research question:** How sensitive are sizing and outage forecasts to classifying zero grid energy as grid unavailability?
- **Method:** Identify ambiguous meter states, use independent status labels on a collected subset, and propagate plausible label error through outage-duration models, forecasts and sizing. Compare bounds from ambiguous labels with designs obtained after verification.
- **Data and availability:** T contains the raw energy series and code's inference rule. C: timestamped voltage/status logging and meter documentation are needed to distinguish zero demand, missing readings and outages; P cannot resolve this.
- **Candidate novelty:** Trace a measurement-definition uncertainty into investment and reliability decisions instead of treating derived outage labels as ground truth.
- **Main risk:** Without independent labels the result is a sensitivity bound, not an estimate of actual misclassification.
- **Effort:** 8–12 weeks.

### 14. Recovering demand suppressed by outages
- **Research question:** Does sizing against observed generator consumption underestimate the demand a reliable household supply would unlock?
- **Method:** Separate served consumption from latent desired demand using appliance/service observations and a censoring-aware model; propagate partial-identification bounds into sizing. Compare present-service replacement with improved-service designs rather than assuming the same load under all supply states.
- **Data and availability:** T provides grid and generator energy; P provides weather covariates. C: appliance inventories, curtailed-use diaries, supply limits and preferably a period of reliable supply are needed.
- **Candidate novelty:** Treat household demand as potentially constrained by the existing supply regime, not an invariant input to replacement sizing.
- **Main risk:** Latent demand is not identifiable from aggregate served energy alone; unsupported causal claims must be avoided.
- **Effort:** 14–22 weeks.

### 15. Subhourly adequacy and inverter sizing
- **Research question:** How often does an hourly-optimal design fail power and service requirements when short-duration demand peaks are represented?
- **Method:** Collect synchronized higher-frequency demand and power data, optimize and replay at multiple resolutions, and compare energy sufficiency with inverter overload and ramp constraints. Separate sustained peaks from motor-start transients that require additional measurements.
- **Data and availability:** T is hourly and cannot reconstruct actual peaks. C: subhourly load/PV data, inverter overload curves and targeted transient measurements are needed; hourly P weather is insufficient for transient validation.
- **Candidate novelty:** Quantify the resolution-dependent gap between energy-based investment decisions and realizable electrical service.
- **Main risk:** Synthetic disaggregation can build in the desired failure rate.
- **Effort:** 12–18 weeks.

### 16. Value of better measurements
- **Research question:** Which additional measurement would reduce PV-battery investment uncertainty most per unit of monitoring cost?
- **Method:** Use a decision-focused value-of-information analysis for outage status, load peaks, solar output and battery temperature; simulate prospective updates under explicit observation models. Validate the predicted value through a limited monitoring pilot where feasible.
- **Data and availability:** T and P support initial uncertainty models. C: sensor costs, error characteristics and pilot observations are needed for actionable acquisition recommendations.
- **Candidate novelty:** Optimize research and monitoring expenditure by its effect on investment regret, rather than ranking uncertain parameters solely by variance.
- **Main risk:** Information value depends strongly on prior assumptions and may exceed benefits realizable with a short campaign.
- **Effort:** 10–16 weeks.

### 17. Weather-source and PV-model decision uncertainty
- **Research question:** Do weather-product and irradiance-model choices change the preferred equipment configuration enough to justify local calibration?
- **Method:** Run a factorial comparison across historical P products, transposition models and thermal models, keeping dates, dispatch and optimization budgets aligned. Measure design transfer regret and variance contributions; separate the frozen-model discrepancy from general uncertainty analysis.
- **Data and availability:** T supplies demand; P supplies candidate radiation and weather series. C: local irradiance or measured PV output is needed to determine accuracy rather than mere disagreement.
- **Candidate novelty:** Convert modeling disagreement into decision consequences and a calibration decision, extending beyond a simple yield-model comparison.
- **Main risk:** Shared upstream data and lack of local truth prevent claims that one product is inherently best.
- **Effort:** 8–12 weeks.

### 18. Cleaning and storage co-design under soiling
- **Research question:** How do cleaning access and water constraints alter the PV-versus-storage trade-off during extended outages?
- **Method:** Couple measured soiling accumulation and cleaning recovery to outage-aware dispatch, panel sizing and cleaning schedules; compare fixed derating with state-dependent losses and water-constrained maintenance.
- **Data and availability:** T supplies load; P supplies weather covariates. C: local soiling ratios, cleaning efficacy, rainfall response, water usage and cleaning costs are needed; weather alone does not measure soiling.
- **Candidate novelty:** Treat recoverable PV loss and maintenance timing as design decisions linked to outage protection rather than a fixed annual derating.
- **Main risk:** Short soiling campaigns may miss seasonal dust events and bias maintenance benefits.
- **Effort:** 12–18 weeks.

### 19. Battery chemistry and passive thermal protection
- **Research question:** When is spending on battery thermal protection more valuable than adding capacity in a hot intermittent-grid setting?
- **Method:** Compare validated chemistry-specific aging and power models with enclosure, insulation and passive/active cooling options; include cooling parasitic loads and heat-related power limits in lifecycle sizing.
- **Data and availability:** T and P supply electrical demand and ambient weather. C: chemistry-specific test data, enclosure measurements, thermal hardware costs and safety limits are needed.
- **Candidate novelty:** Optimize the thermal system as a competing reliability investment; unlike Idea 06, chemistry and thermal hardware are the primary decisions.
- **Main risk:** Non-comparable manufacturer aging curves can produce a misleading chemistry ranking.
- **Effort:** 14–22 weeks.

### 20. Repair delays and component failures
- **Research question:** How much reliability is lost when inverter and battery failures overlap with grid outages and slow repair?
- **Method:** Add component failure/repair states to chronological simulation and optimize redundancy, spare capacity or service contracts. Separate independent failures from explicit common-cause stress scenarios and compare with grid-outage-only sizing.
- **Data and availability:** T and P support operating scenarios. C: component failure records, local repair lead times, spare costs and service-contract terms need collection.
- **Candidate novelty:** Evaluate maintainability and repair logistics as determinants of household resilience, not just component replacement expenses.
- **Main risk:** Sparse failure data and unsupported independence assumptions can dominate reliability estimates.
- **Effort:** 12–18 weeks.

### 21. Carbon cost of maintaining outage reserves
- **Research question:** Can a reliability-oriented grid-charging policy increase lifecycle emissions even while reducing household generator use?
- **Method:** Track charging-source attribution, losses, replacements and service delivered; optimize cost, reliability and lifecycle emissions with uncertainty in grid and generator factors. Separate average-factor accounting from consequential claims requiring marginal factors.
- **Data and availability:** T records load sources and legacy equipment assumptions; P supplies solar scenarios. C: defensible local generation factors, generator fuel curves and component lifecycle inventories require verified external evidence or collection.
- **Candidate novelty:** Reveal reserve-policy and replacement trade-offs that simple avoided-diesel calculations miss, rather than adding an emissions objective alone.
- **Main risk:** Coarse emissions factors may make policy rankings indeterminate.
- **Effort:** 10–16 weeks.

### 22. Affordability-constrained reliability
- **Research question:** Which financing or targeted support mechanisms deliver the greatest reliable essential service for cash-constrained households?
- **Method:** Add upfront budget, repayment and maintenance-affordability constraints to service-based sizing; compare financing and support scenarios using distributional outcomes across measured household types. Keep normative service weights explicit.
- **Data and availability:** T supports a technical case only; P supplies weather. C: consented household budgets, demand diversity, financing terms and service priorities need collection.
- **Candidate novelty:** Distinguish technically cost-optimal designs from financially adoptable ones and measure who receives outage protection.
- **Main risk:** A single building cannot support population or distributional policy conclusions.
- **Effort:** 14–22 weeks.

### 23. Outage-preserving representative periods
- **Research question:** Can reduced time-series representations accelerate sizing without erasing long outage sequences and storage carryover?
- **Method:** Develop event-aware representative sequences that preserve outage runs, seasonal context and inter-period state of charge; compare with conventional representative days and full chronological optimization. Validate every reduced-model design on the untouched full trace and independent scenarios.
- **Data and availability:** T supports the core benchmark; P supplies additional weather variation. C: more measured household/outage years are needed for broad external validation, but not an initial methodological demonstration.
- **Candidate novelty:** Provide an error-controlled reduction method targeted at discontinuous grid access, with full-trace design regret and reliability violations as primary outcomes.
- **Main risk:** Preserving chronology may remove most computational savings, especially for a small design space.
- **Effort:** 10–14 weeks.

### 24. Certified bounds for heuristic sizing
- **Research question:** How close is heuristic sizing to the best physically feasible cost–reliability trade-off under the same model?
- **Method:** Construct a tractable mixed-integer or enumeration benchmark with explicit approximation bounds; compare GNPSO, GA and PSO at equal simulation budgets. Separate solver optimality gaps from model approximation error and validate candidate designs in a common nonlinear simulator.
- **Data and availability:** T supplies the design case and baseline algorithms; P provides stress cases. No new field collection is needed for a computational benchmark; broader claims require additional instances.
- **Candidate novelty:** Deliver defensible bounds and characterize regimes where heuristics fail, extending the thesis's heuristic-versus-heuristic comparison.
- **Main risk:** A benchmark alone may be too narrow for a journal paper; bounds on a simplified model do not certify the original model.
- **Effort:** 10–16 weeks.

### 25. Low-regret sizing rules for installers
- **Research question:** Can transparent sizing rules retain most of the service quality of detailed optimization across credible outage regimes?
- **Method:** Generate a preregistered scenario library, optimize reference designs, and fit sparse rules using interpretable outage-duration, load and solar features. Evaluate worst-case and typical regret on held-out regimes, with abstention outside the training domain.
- **Data and availability:** T and P support a synthetic scenario library. C: diverse measured household and outage profiles are required to validate transfer beyond the thesis home.
- **Candidate novelty:** Produce auditable decision rules with quantified operating limits and regret rather than an opaque surrogate reporting prediction accuracy.
- **Main risk:** Rules may learn the scenario generator and fail on real households.
- **Effort:** 10–16 weeks.

### 26. Vehicle availability as a resilience constraint
- **Research question:** When does bidirectional vehicle charging reduce stationary storage without compromising mobility during grid outages?
- **Method:** Jointly size stationary storage and dispatch vehicle energy with uncertain departure, arrival, driving demand and minimum mobility reserves. Compare realistic vehicle absence with an always-connected upper bound and no-vehicle baseline.
- **Data and availability:** T and P support stationary operation. C: travel diaries, vehicle battery limits, bidirectional hardware compatibility, charging costs and user consent are needed.
- **Candidate novelty:** Resolve the conflict between uncertain vehicle presence, transport service and outage backup instead of counting the entire vehicle battery as stationary capacity.
- **Main risk:** Results may be irrelevant to households without compatible vehicles or affordable equipment.
- **Effort:** 14–20 weeks.

### 27. Dispatch resilient to missing or stale forecasts
- **Research question:** Can a forecast-based EMS preserve outage service when sensors, communication or forecast updates fail?
- **Method:** Introduce documented missing-data and stale-forecast mechanisms; compare normal MPC, a physically constrained fallback and conservative fixed rules. Evaluate switching behavior, recovery and sizing consequences under identical faults.
- **Data and availability:** T and P permit explicitly synthetic fault experiments. C: deployed-device logs and controller trials are needed to estimate real fault frequencies and deployment performance.
- **Candidate novelty:** Co-evaluate forecast benefits and dependence on the information infrastructure, with graceful fallback as a design requirement.
- **Main risk:** Convenient fault injections may favor the proposed fallback; failures and budgets must be set before evaluation.
- **Effort:** 10–14 weeks.

### 28. Minimum useful recharge windows
- **Research question:** Which combinations of outage duration, restoration-window length and charging power make a target service level physically unattainable?
- **Method:** Derive energy and power feasibility bounds with explicit assumptions, then map them against detailed chronological simulations and optimized designs. Separate adding capacity from increasing charging power or improving grid access, and test bound tightness.
- **Data and availability:** T supplies observed restoration/outage sequences and load; P supplies solar variability. C: actual connection limits and charger ratings are needed for site-specific feasibility statements.
- **Candidate novelty:** Explain structural limits to battery-based resilience when the grid returns too briefly to refill storage, rather than assuming reliability can always be purchased with more capacity.
- **Main risk:** Loose bounds may add little beyond simulation; generic storage feasibility theory must be checked before claiming novelty.
- **Effort:** 8–12 weeks.

### 29. Robust household service preferences
- **Research question:** Which PV-battery designs remain defensible when households disagree about the relative importance of cost and interruption severity?
- **Method:** Generate feasible cost–service Pareto sets, elicit preference ranges, and select designs using minimax regret or robust multicriteria analysis. Compare with the thesis's weighted fitness and distinguish preference uncertainty from physical scenario uncertainty.
- **Data and availability:** T and P support the engineering trade-offs. C: structured household preference elicitation is needed; assumed weights allow only conditional illustrations.
- **Candidate novelty:** Quantify decision stability under uncertain service preferences rather than presenting a single arbitrary objective-weight choice as the optimum.
- **Main risk:** A standard Pareto analysis with new weights is incremental unless elicitation and decision-stability findings add substance.
- **Effort:** 10–14 weeks.

### 30. Online adaptation to changing outage regimes
- **Research question:** Can a reserve controller adapt to persistent changes in grid availability without becoming unsafe during the transition?
- **Method:** Combine sequential change detection with constrained model updates and fallback reserves; compare frozen, periodically retrained and adaptive policies in strictly prequential evaluation. Distinguish naturally observed changes from injected scenarios and include false-alarm and adaptation costs.
- **Data and availability:** T supports a limited replay; P supplies weather covariates. C: longer sequential outage/load records and prospective evaluation are needed to validate real regime changes.
- **Candidate novelty:** Study the transition cost and safety of updating outage-dependent control, distinct from offline forecast comparison or long-term capital staging.
- **Main risk:** One seasonal cycle cannot reliably distinguish structural change from seasonality, and synthetic changes may favor the detector.
- **Effort:** 12–18 weeks.

## Ranked top eight

The ranking favors a clear thesis extension, a falsifiable contribution and work that can begin with the existing record. It discounts dependence on unavailable field data and does not imply verified literature novelty or guaranteed journal acceptance. Each candidate should first pass a targeted literature-gap review and baseline/data audit.

1. **Idea 01 — Outage-tail-aware sizing.** Long, persistent interruptions make event-level loss a direct extension of the thesis's annual reliability treatment, and the existing sequence permits an initial comparison without new hardware. The strongest paper would show when persistence changes investment decisions, including null regimes, while keeping rare-tail extrapolation separate from empirical evidence.

2. **Idea 02 — The operational value of forecasts.** This directly extends the RF/LSTM work by testing whether predictive skill changes realized service and cost under causal control, rather than adding another forecasting architecture. It is feasible to start with chronological replay, but actual forecast lineage and limited out-of-sample coverage must be resolved before interpreting gains.

3. **Idea 28 — Minimum useful recharge windows.** Physical feasibility limits can produce a generalizable contribution and explain why extra battery capacity sometimes fails to solve an outage problem. It has a relatively modest data burden and makes a strong complement to an empirical paper, provided the derived bounds are both informative and demonstrably distinct from existing storage-feasibility results.

4. **Idea 04 — Distributionally robust sizing under scarce outage data.** The short observed record makes uncertainty about the outage law a substantive research problem, with a clear comparison between nominal efficiency and protection against distribution error. This ranks below duration-aware sizing because ambiguity-set calibration and external validation are harder, and an overconservative result must be reported without retuning to the test set.

5. **Idea 23 — Outage-preserving representative periods.** This offers a distinct computational-method contribution that can begin with existing data and be judged using full-chronology regret and service failures. It becomes compelling if conventional temporal reduction misses persistent outages and the proposed method preserves adequacy at useful computational savings; either part may fail on the small thesis system.

6. **Idea 06 — Reliability throughout battery aging.** Linking state-of-health decline to future outage service is a materially stronger extension than the thesis's cycle-count replacement approximation. It addresses a practical lifecycle design problem, but chemistry and thermal validation make it slower and more assumption-sensitive than the higher-ranked options.

7. **Idea 11 — Diesel subscription as a discrete backup decision.** The existing grid/generator context gives this idea a concrete economic mechanism: reducing generator energy does not necessarily remove a fixed subscription payment. A verified set of local service tiers could make the study both tractable and useful, while evidence that the contract structure is already well studied would lower its novelty substantially.

8. **Idea 13 — Meter-derived outage-label uncertainty.** The code's explicit inference rule makes this a well-motivated data-to-decision study with direct consequences for both forecasts and sizing. It needs independent status measurements to become more than a hypothetical perturbation exercise, but a modest verification campaign could establish whether the uncertainty matters at all.

## Selection boundary

Choose one central claim rather than combining all eight topics. A coherent first route is Idea 01 as the core contribution, using Idea 28 for physical interpretation and a narrowly scoped Idea 13 audit as a validity check; those supporting analyses should not be advertised as independent discoveries unless warranted. Idea 02 is a distinct alternative centered on forecasting and control, and should not be added merely to increase the apparent number of techniques.

Before committing to a route, verify the literature gap, workbook provenance/time alignment, grid-status interpretation and the actually executed legacy model. Preserve the frozen thesis results, disclose baseline corrections separately, and decide whether available evidence supports a single-household methodological demonstration or whether additional collection is necessary for the intended claims.
