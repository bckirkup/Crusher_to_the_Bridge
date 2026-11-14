# Tranche 56 — Diamond Princess COVID-19 aerosol-transmission model (Azimi et al. 2021)

> **Status:** Reference. Literature tracking only; no model, constant, campaign or ledger change.

**Citation.** Parham Azimi, Zahra Keshavarz, Jose Guillermo Cedeno Laurent, Brent Stephens, and Joseph G. Allen, “Mechanistic transmission modeling of COVID-19 on the Diamond Princess cruise ship demonstrates the importance of aerosol transmission,” *Proceedings of the National Academy of Sciences of the United States of America* 118(8):e2015482118 (2021). DOI 10.1073/pnas.2015482118; PMID 33536312; PMCID PMC7923347. Open access (CC BY 4.0) via PMC/Europe PMC.

**Access and origin.** Full text opened: Europe PMC JATS XML for the article and Europe PMC `supplementaryFiles` for the PMC-hosted SI Appendix PDF (`pnas.2015482118.sapp.pdf`). Origins below are the paper's own locations: **Me** Methods/SI Appendix, **R** Results, **T1/T2** Tables 1–2. Figure values are cited through the Results prose that reports them; no figure was digitized. Consensus search returned the same DOI/PMCID record.

## 1. What the model represents

- A stochastic, discrete-time, discrete-space Markov chain tracks SARS-CoV-2 copies through 12 states: infected-cabin and public-area air/surfaces, hands/URT/LRT for cabin-mate and non-cabin-mate susceptibles, the HVAC system, and inactivation/removal (Me, Markov Chain Model and SI Appendix §1.1; Fig. S1).
- Passenger-accessible space is categorized as cabins or common public areas. The SI estimates mean cabin floor area ~22 m², indoor public floor area ~18,000 m² on decks 5–7, cabin-hallway floor area ~3,700 m², and passenger-accessible outdoor zones ~17,000 m². Floor plans were unavailable for non-public zones such as kitchens, control rooms and crew sleeping cabins, so those zones were assumed to total ~8,000 m², “equal to the floor area of one deck” (Me, SI Appendix §1.1.1).
- During quarantine the model assumes indoor public areas are completely closed and only half of the other indoor spaces operate, for a total operating floor area of ~4,000 m². Ceiling height is assumed 2.5 m for cabins/hallways and 4 m for other indoor public areas (Me, SI Appendix §1.1.1).
- Connected public indoor spaces and HVAC mixing are represented as one well-mixed public-area compartment. Each stateroom is also treated as well-mixed, but infected and non-infected staterooms carry different average exposure concentrations, updated daily from public-area acquisitions (Me, SI Appendix §1.1.1).
- Ventilation is assumed at 9 air changes/h in cabins and 12/h in other indoor locations, with no air recirculation, 100% outdoor supply air, positively pressurized cabins exhausting to hallways/public areas, and cabin-to-public inter-zonal airflow set to 5% of the cabin ventilation rate (Me, SI Appendix §1.1.2).
- Before quarantine, passengers/crew are assumed to spend ~9 h/day in cabins; after quarantine passengers remain mostly in cabins, interior-cabin passengers receive a 1 h outdoor-air break, and one crew member services each cabin for 15 min/day (Me, SI Appendix §1.1.4).
- The scenario design crosses eight uncertain inputs — effective incubation period, effective subclinical infectious period, index-case effective reproduction number, symptomatic/asymptomatic emission ratio, aerosol/droplet emission ratio, minimum cabin close-interaction time, quarantine infection-control efficiency, and URT/LRT ID50 ratio — for 21,600 model iterations (R, Materials and Methods; T1).

## 2. Aerosol-transmission findings

- 132 of 21,600 iterations met the acceptability criteria (R² > 0.95 for modeled vs reported cumulative daily cases and nonnegative R² for daily cases), or 0.6% (R, Results; T1).
- Across the entire simulated period, median (mean) contributions were short-range transmission 36% (35%), long-range aerosol transmission 41% (35%), and fomite transmission 21% (30%) (R, Results; Fig. 2A).
- Across the entire simulated period, median (mean) contributions were larger-droplet sources 28% (41%) and smaller-aerosol sources 72% (59%); the droplet/aerosol difference was significant by Mann–Whitney U test (P < 0.0001) (R, Results; Fig. 2B).
- The accepted iterations estimated 58% (SD 5%) of cases transmitted before passenger quarantine and 42% (SD 5%) after; estimated effective reproduction number was 3.8 (SD 0.9) before and 0.1 (SD 0.2) after quarantine (R, Results; Fig. 3A/B).
- Before quarantine, median (mean) mode contributions were long-range 42% (34%), fomite 37% (46%), and short-range 22% (19%). After quarantine they were long-range 39% (36%), fomite 0.5% (6%), and short-range 58% (59%) (R, Results; Fig. 4).
- Before quarantine, median (mean) droplet/aerosol contributions were 40% (50%) and 60% (50%) (P = 0.32); after quarantine they were 15% (27%) and 85% (73%) (P < 0.0001) (R, Results; Fig. 5).
- The authors' Discussion states that aerosol inhalation likely accounted for >50% of transmission even under their conservative high-ventilation/no-recirculation assumption, and reports a fomite-only best estimate of 98 cases out of 3,711 persons (2.6%) versus more than 700 reported cases (R, Discussion; SI Appendix Table S5).

## 3. Comparison with Crusher's Diamond Princess platform-fidelity approach

This is a structural comparison only, factual to the two texts:

- Azimi et al. collapse the connected passenger-accessible public indoor spaces into a single well-mixed compartment and represent cabins through aggregate infected/non-infected stateroom air states with assumed areas, volumes and airflow splits (Me, SI Appendix §1.1.1–1.1.2).
- Crusher's Diamond Princess platform approach is zone-resolved geometry with a declared airflow network and ContamX-solved airflow/concentration fields. The two representations therefore differ in spatial resolution and airflow closure: Azimi's route shares are conditional on a lumped public compartment and explicitly assumed ventilation/occupancy rules, while Crusher resolves zones and solves the declared network.
- No claim is made here that either approach validates or outperforms the other; this entry records the paper and its assumptions, not a model comparison result.

## 4. Evidence grade and scope decisions

- **Evidence grade:** B for the Diamond Princess model-derived estimates, matching the treatment already recorded in `docs/covid/covid_dp_ventilation_sourcing.md` §1 — a model-derived estimate over accepted iterations on the target hull, not a direct measurement. The authors' geometry, ventilation and occupancy inputs remain C-grade assumptions if they were ever considered for adoption; nothing is adopted here.
- **Parameter provenance register:** no row added. The paper supplies no measured constant in the register's units; its route shares and reproduction-number estimates are model outputs conditioned on reported Diamond Princess case counts, not independent measurements of a profile constant.
- **COVID open ledger:** untouched. The ledger-adjacent values from this same paper (pre/post-quarantine case shares and effective reproduction numbers) are already recorded under `COVID-VENT-AUDIT-01` and `docs/covid/covid_dp_ventilation_sourcing.md`; this entry verifies the citation and adds no new measurement or invalidation.
- **Non-goals observed:** no fitting, no adoption, no simulation, and no change to engine, hull data, tests or campaign artifacts.
