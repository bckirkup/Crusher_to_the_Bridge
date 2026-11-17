# noro_supply_solver_screen_01 — ledger

**Status:** design frozen; no cells run yet.
**Date:** 2026-11-16

## Scope

Expedition p06 screen requested by Benjamin: stratified contaminated supply seeds plus quiet controls on `fl_exp_12d_sens_p06_paxv`, paired `transmission.contamination_solver` `discrete` vs `continuous` to assess sensitivity and range of AR, timing, and role partition.

## Frozen inputs

- Design: `campaigns/noro/supply_solver_screen_01/DESIGN.md`
- Seed selection: `campaigns/noro/supply_solver_screen_01/seed_selection.json`
- Manifest: `campaigns/noro/supply_solver_screen_01/manifest.json`
- Spec: `campaigns/noro/supply_solver_screen_01/campaign.json`

## Counts

- 88 cells total: 2 solver arms x 44 seeds.
- Per solver: station_lots 16 contaminated + 8 quiet, single_line_receipt 10, declared_receipts 10.
- Campaign blocks: 8 (supply arm x solver, with station quiet split into two blocks).

## Preflight status

- [x] Local smoke: solver override reaches engine; output contract unchanged.
  - 24-epoch smoke, seed 900470 station_lots: discrete `acquired=47`, continuous `acquired=53`; both zips carry `parameters.tier_id` = `fl_exp_12d_sens_p06_paxv_station_lots_{discrete,continuous}` and the same summary/census/rss members.
- [x] Dry-run count matches 88 (block array sizes 16+16+10+10+10+10+8+8).
- [x] Local full-length canary, seed 900470 station_lots, 288 epochs, payload lean:
  - discrete: attack_rate 0.2489, pax_reported 0.1329, crew_reported 0.0299, `vsp_trigger_epoch=57`, peak 110 at epoch 224, acquired 108, wall 66.4 s, RSS 385824 KB.
  - continuous: attack_rate 0.2067, pax_reported 0.1108, crew_reported 0.0299, `vsp_trigger_epoch=53`, peak 92 at epoch 119, acquired 89, wall 82.7 s, RSS 449764 KB.
  - One seed only; this is plumbing/timing evidence, not solver attribution.
- [ ] Image built and digest pinned in `campaign.json`.
- [ ] Manifest uploaded to S3.
- [ ] AWS canary child inspected.
- [ ] ETA reported; user decides on array.

## Measurements

No sweep measurements yet. The two full-length canary rows above are preflight witnesses only.
