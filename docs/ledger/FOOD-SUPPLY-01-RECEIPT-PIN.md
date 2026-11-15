# FOOD-SUPPLY-01-RECEIPT-PIN
**Date:** 2026-11-15
**Commit:** c19b73ef
**Pathogens:** norwalk_gi
**Status:** closed

Defect/fix: the FOOD-SUPPLY-01 receipt modes (`single_line_receipt` and
`declared_receipts`) resolved `provisioned_source.station_zone_pin` and
`station_zone_pin_weights`, but `_cs_plan_receipt_objects` still built
receipt `venues_served` from every served Dining zone and hard-coded the
voyage witness fields to null. The receipt planner now filters the served
Dining venue universe to the pin set before the deterministic receipt
partition and passes that venue set through lot realization, and the
`provisioned_source` witness carries `station_zone_pin` /
`station_zone_pin_weights` like the `station_lots` arm.

Stream contract: venue filtering happens after config resolution and
before receipt partitions without consuming `_cs_rng`, so pinned and
unpinned receipt arms remain seed-paired for receipt contamination states;
only venue allocation and lot realization move. `station_zone_pin_weights`
is carried into the witness, but receipt v1 still uses deterministic venue
partitioning — weighted allocation of one shared receipt across venues
remains the later arm named in `docs/food_supply_01_design.md`. With a
one-zone pin and `receipts_per_item_line=2`, the second declared receipt
has an empty pinned partition, still witnesses contamination, and mints no
lot.

Validation: deterministic FOOD-SUPPLY-01/provisioned-source pytest slice
passed, including new pinned-venue, seed-pairing, and declared-partition
regressions. No new stochastic measurement was run. The pinned
receipt-arm venue witnesses in `FOOD-SUPPLY-01-SMOKE.md` are historical
for venue scope and should be re-measured before a pinned canary.
