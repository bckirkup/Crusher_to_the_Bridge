# FOOD-SUPPLY-01-SMOKE
**Date:** 2026-11-15
**Commit:** 9ff1b20d
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 9ff1b20d

Bounded local smoke for the FOOD-SUPPLY-01 receipt/lot arm, not a campaign submission. Runs used `fl_meg_12d_sens_p06_paxv` reduced to 2,000 agents under `PYTHONHASHSEED=1`, `growth_chain_census.run_seed(..., payload_profile="lean")`, and campaign-shaped zips (`summary.json` + `growth_census.json.gz`). The worktree had only untracked smoke/tmp files; no tracked source differed from `9ff1b20d`.

Method: arms were `station_lots` control, `single_line_receipt`, and `declared_receipts` with `receipts_per_item_line: 2`. A 1-epoch/100-agent planning sweep over seeds 8105-8130 found contaminated receipt lots only on seed 8118 for both receipt arms: one infectious `shellfish` receipt each. Seed 8125 was also smoked at 24 epochs/2,000 agents; both receipt arms drew zero contaminated receipts there while `station_lots` minted one pinned `MainDining_L` station lot.

Measured at 72 epochs/2,000 agents on seed 8118:

- `station_lots`: `n_contaminated=0`, `events_provisioned_lot=0`, `acquired=17` (ill-handler/diner objects only), attack rate 0.033, passenger infection AR 0.0357, passenger reported-case AR 0.0014, no outbreak/VSP trigger.
- `single_line_receipt`: 7 receipts with 1 infectious `shellfish`; 1 lot of 442 servings / 56,239.68 g, `seeded_epoch=16`, `exhausted_epoch=18`, `windows_covered=26`, `pans_emitted=26`, `servings_served=442`, object `dose_credited=14,592,754.95` GEC, telemetry `dose_credited=15,626,408.43` GEC, `events_provisioned_lot=26`, `takers_served=397`, `acquired=110`, attack rate 0.0795, passenger infection AR 0.0936, passenger ever-ill AR 0.0329, passenger reported-case AR 0.0329, `outbreak_occurred=true`, `vsp_trigger_epoch=63`.
- `declared_receipts`: 14 receipts with 1 infectious `shellfish`; 1 lot of 31 servings / 5,301.68 g partitioned to five venues (`CafeBakery`, `CrewMess_Fwd`, `MainDining_U`, `Pool_Bar_Grill`, `SpecRest_A`), `seeded_epoch=40`, `exhausted_epoch=40`, `windows_covered=4`, `pans_emitted=4`, `servings_served=31`, object `dose_credited=4,279,096.90` GEC, telemetry `dose_credited=4,530,808.48` GEC, `events_provisioned_lot=4` all at epoch 40 / `Meal:Dinner`, cohort sizes 10/35/9/16 with servings taken 1/13/8/9, `takers_served=191`, `acquired=33`, attack rate 0.041, passenger infection AR 0.0436, passenger ever-ill AR 0.0064, passenger reported-case AR 0.0021, no outbreak/VSP trigger.

Measured caveat: receipt modes ignore `station_zone_pin`. In the receipt witness `station_zone_pin` is `None`; `single_line_receipt` served ten Dining zones while `declared_receipts` partitioned the contaminated shellfish receipt across five. The p06 passenger-pin cell is therefore not a like-for-like venue comparator for receipt arms.

Inferred: the receipt layer is mechanically live — receipts, per-line contamination states, preparation filtering, venue partitioning, lot quantity/mass witnesses, and object/event rows all reach the census payload. On this one contaminated seed, the shared single-line receipt produced a much larger and earlier supply-chain excursion than the partitioned declared receipt because it combined a 442-serving lot, ten served venues, and a day-0 start; the declared arm drew a 31-serving lot with a later start and only four same-epoch dinner pans. Hypothesis: receipt-count/lot-size correlation is a plausible rare-tail lever, but one contaminated seed is not a rate; the 26-seed planning sweep found only one contaminated voyage per receipt arm.

Next decision: before a canary, choose whether to fix receipt `station_zone_pin` carry-through or explicitly scope the canary to unpinned/all-venue cells. Then run at least 20 paired seeds on one mega cell with `station_lots` vs `single_line_receipt`/`declared_receipts`, fixed hash, measuring posted rate, passenger/crew AR, common-source acquisitions/events, receipt/object witnesses, and mass conservation. No default flip or anchor fit.
