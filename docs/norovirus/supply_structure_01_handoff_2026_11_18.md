# SUPPLY-STRUCTURE-01 handoff (2026-11-18)

> **Status:** Handoff record. Reports no new numbers; every figure is quoted from `docs/norovirus/supply_structure_01_design.md`, `docs/norovirus/cruise_food_supply_sourcing_survey_2026_11_18.md`, `docs/literature/consensus_tranche_57_cruise_food_supply_chain.md`, `docs/ledger/PROVISIONED-SOURCE-01.md`, the supply solver-screen readouts/ledgers, and the merged Stage A implementation in PR #1319.

## 1. The question

How should cruise food-supply structure be modeled across hull classes without running massive campaigns of quiet mega cruises? The motivating distinction is that posting frequency is not introduction frequency: `PROVISIONED-SOURCE-01` already made objects-per-voyage proportional through `N_lots · q_source`, while `P(post | minted)` dilutes by hull. The open structural hypotheses are shared upstream source lots, venue/menu incidence by service class, and hull/venue lot scale.

## 2. Current hypothesis

Keep `provisioned_source` / `common_source` as the in-voyage causal engine and treat supply structure as a separate labelled scenario layer. Stage A is a cheap supply-side census/surrogate over orthogonal `source_cluster`, `venue_menu`, and `lot_scale` arms that records minted-exposure witnesses without requiring postings; Stage B is a small paired-seed ABM confirmation only for arms/hulls the surrogate identifies near the posting threshold. The flat independent station census remains the default and the mean-introduction null until a witness justifies a flip.

## 3. Evidence for

- `docs/norovirus/cruise_food_supply_sourcing_survey_2026_11_18.md` and `docs/literature/consensus_tranche_57_cruise_food_supply_chain.md`: consumption-side venue/food diversity rises with hull size; procurement is described as centralized/self-sufficient with turnaround loading and at-sea restocking; Rispens 2020 is the measured shared-upstream-lot bridge (~22,000 lb frozen raspberries supplied to a whole cruise fleet).
- `docs/ledger/PROVISIONED-SOURCE-01.md`: `N_lots` is 21/35/63/70 on exp/cls/spr/mega; one hull-invariant `q_source` put the three small hulls in-band, while mega's measured in-band window was roughly 3–4× the small-hull window because `P(post | minted)` dilutes by hull.
- `docs/norovirus/supply_solver_screen_handoff_2026_11_17.md` and the screen01/02/03 readouts/ledgers: on the frozen supply seeds, `station_lots` overposts relative to the VSP comparator on small hulls, receipt strata are nearer the posting-rate order, and mega posting is rare (station_lots 1/16 per solver arm, receipts 0/10, quiet 0/8), so supply-structure shape should be studied before more quiet mega ABM cells.
- PR #1319: `provisioned_source.supply_structure` now carries declared `source_cluster` rungs (`independent`, `line_shared`, `venue_group_shared`, `fleet_shared`), `venue_menu` service-class masks (`flat`, `passenger_raw`, `buffet_specialty`), and `lot_scale.servings_multiplier`, with supply witnesses on `provisioned_source` and closed `common_source_objects` rows; absent/flat remains bit-identical and receipt-layer composition raises in v1.

## 4. Evidence against / unexplained

- The sourcing survey found the key mechanism inputs unmeasured: per-venue menu incidence, vendor/source sharing matrices, cruise-specific lot-size distributions, and in-transit viral load/degradation. The Stage A arms are therefore declared Grade C structural scenarios, not fitted mechanisms.
- `venue_menu` v1 masks only the three nonzero-prevalence raw/RTE lines (`shellfish`, `salad_leaf`, `fresh_produce`); garnish/prepared census lines are intentionally mask-invariant, and receipt-layer `raw_rte_only` service eligibility is out of scope for the station-census arms. A Devin Review finding that crew messes still serve contaminated prepared/garnish lots was triaged rejected on that boundary.
- The Stage A census/surrogate has not yet been run at campaign scale; the merged PR proves config/witness plumbing and local smoke, not a supply-structure posting or AR result.
- No Stage B ABM confirmation has been run; Stage B remains gated on Stage A naming informative arms/hulls.

## 5. PRs this session

- #1313 — cruise food-supply sourcing survey and Consensus tranche 57; adopts no constants.
- #1318 — frozen `SUPPLY-STRUCTURE-01` design contract: decoupled supply-structure layer, Stage A census/surrogate, Stage B small paired-seed ABM confirmation, no anchor fitting.
- #1319 — Stage A implementation: engine `supply_structure` resolution/helpers/witnesses, seed-scanner `--structure` arms and validation, structure-aware artifact names, integrity tests, docs status; flat remains default.
- Earlier solver-screen stages (#1275, #1280–#1283, #1292–#1295) are closed in `docs/norovirus/supply_solver_screen_handoff_2026_11_17.md`.

## 6. Running jobs

None. No campaign array was submitted for SUPPLY-STRUCTURE-01; the Stage A scanner smoke was local only and its artifacts were not committed.

## 7. What is now void

Nothing. No committed measurement is withdrawn by these stages; `docs/norovirus/norovirus_open_ledger.md` §1 is unchanged. There is still no supply-structure posting/AR measurement, and the flat census remains the shipped default.

## 8. The single open decision

Decide whether to spec/run the Stage A supply-structure census campaign on the merged scanner (orthogonal arms × hulls/seeds, cheap one-epoch census rows) or hold at the merged implementation. Stage B targeted ABM confirmation should wait until Stage A identifies which arms/hulls are informative near the posting threshold; do not substitute massive quiet mega cruises for the census.

## 9. Do not reopen

- Do not fit any constant to VSP/Park/attack-rate/passenger-crew anchors; supply-structure arms are declared structural scenarios, not anchor fits.
- Do not flip the shipped default off `flat` until a Stage A/B witness justifies it.
- Do not compose `supply_structure` arms with FOOD-SUPPLY-01 receipt layers in v1; the engine raises explicitly rather than silently mislabeling the arm.
- Do not treat the seed census as a posted-AR measurement; it is a boarding/prevalence and minted-exposure witness only.
- Do not read `outbreak_occurred` as posting; posted means `vsp_trigger_epoch is not None`.
- Do not treat the literature/industry survey as a measurement of record; it is an evidence map with explicit unmeasured gaps.
- Do not run massive quiet mega campaigns to learn supply-structure shape; use the cheap census/surrogate first.
