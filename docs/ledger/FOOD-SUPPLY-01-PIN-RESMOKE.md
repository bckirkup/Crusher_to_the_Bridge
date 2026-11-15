# FOOD-SUPPLY-01-PIN-RESMOKE
**Date:** 2026-11-15
**Commit:** c8dbb22fe14d58bcc864e2993c0c358c1cebb67d
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** c8dbb22fe14d58bcc864e2993c0c358c1cebb67d

Pinned re-smoke for FOOD-SUPPLY-01 after PR #1239. Same bounded local method as `FOOD-SUPPLY-01-SMOKE.md`: `fl_meg_12d_sens_p06_paxv` reduced to 2,000 agents, seed 8118, 72 epochs, `PYTHONHASHSEED=1`, `growth_chain_census.run_seed(..., payload_profile="lean")`, arms `station_lots` / `single_line_receipt` / `declared_receipts`. The measurement worktree was detached at `origin/main` `c8dbb22f`; only untracked smoke output was written.

Measured at 72 epochs/2,000 agents on seed 8118 (`c8dbb22f`):

- `station_lots`: unchanged from the unpinned smoke — `n_contaminated=0`, `acquired=21`, attack rate 0.035, passenger infection AR 0.0357, passenger ever-ill/reported-case AR 0.0014, no outbreak/VSP trigger.
- `single_line_receipt`: receipt layer now carries `station_zone_pin=['MainDining_L']` and `actual_venues_used=['MainDining_L']`. The contaminated receipt is seed-paired to the unpinned smoke — 7 receipts, 1 infectious `shellfish`, `quantity_servings=442`, `quantity_g=56,239.68`, `q_source_equivalent=0.003141488408576445` — but the lot is pinned to `MainDining_L`: `seeded_epoch=10`, `exhausted_epoch=33`, `windows_covered=14`, `pans_emitted=17`, `servings_served=442`, `dose_credited=14,531,951.81` GEC, 17 `provisioned_lot` events, 275 unique takers. Outcome moved off posting: `n_acquired=91`, attack rate 0.070, passenger infection AR 0.0864, passenger ever-ill AR 0.0236, passenger reported-case AR 0.0207, `detection_epoch=57`, no confirmation/VSP/`outbreak_occurred`.
- `declared_receipts`: receipt layer now carries the same pin; 14 receipts, 1 infectious `shellfish` receipt with `quantity_servings=31`, `quantity_g=5,301.68`, `venues_served=['MainDining_L']`, `q_source_equivalent=0.003141488408576445`; object `seeded_epoch=40`, `exhausted_epoch=41`, `windows_covered=2`, `pans_emitted=2`, `servings_served=31`, `dose_credited=5,034,231.65` GEC, 2 `provisioned_lot` events, 31 unique takers. Outcome is quieter than the unpinned smoke: `n_acquired=19`, attack rate 0.034, passenger infection AR 0.0371, passenger ever-ill AR 0.0029, passenger reported-case AR 0.0021, no outbreak/VSP trigger.

Inferred: PR #1239 preserves receipt contamination draws while moving venue allocation onto the pinned passenger venue. The unpinned `FOOD-SUPPLY-01-SMOKE.md` `single_line_receipt` VSP on seed 8118 was therefore not a like-for-like p06 result; under the pin, the same receipt/lot draw is a suspected/detection excursion but does not post. Hypothesis: the receipt/lot tail lever remains venue breadth/correlation, but the pinned p06 cell needs the ≥20-seed canary to estimate a rate; one seed no longer posts.

Next decision: run the pinned ≥20-seed canary on one mega cell with `station_lots` vs `single_line_receipt`/`declared_receipts`, fixed hash, measuring posted rate, passenger/crew AR, common-source acquisitions/events, receipt/object witnesses, and mass conservation. No default flip or anchor fit.
