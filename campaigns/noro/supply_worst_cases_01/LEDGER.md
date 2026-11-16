# FOOD-SUPPLY-01 worst-case examples ledger

**Date:** 2026-11-16
**Pathogens:** norwalk_gi
**Status:** exp canary succeeded; cls/spr/meg running
**Parent scan:** `campaigns/noro/supply_seed_scan_01/` (`docs/ledger/FOOD-SUPPLY-01-SEED-SCAN.md`)

## Design and ranking

- Frozen design: `DESIGN.md`.
- Ranking artifact: `ranking.md` / `ranking.json`, generated from the completed
  `noro_supply_seed_scan_01` JSONL (`3,786` files, `378,600` rows,
  `24,980` contaminated served-lot cells).
- Ranking rule: sum provisioned-lot burden per seed/arm/hull. Receipt arms use
  exact `quantity_g * lot_titre_gec_per_g`; `station_lots` uses
  `lot_servings * lot_titre_gec_per_g * 150 g` because serving mass is drawn
  later. Venues use object `venues_served`/`zone` plus
  `provisioned_source.actual_venues_used`.
- Selected examples: exp `declared_receipts` 917326, cls `station_lots` 962793,
  spr `station_lots` 1004210, meg `single_line_receipt` 1030001.

## AWS Batch pins

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-worst01@sha256:2a1cafdc5692c81a7bea2bfce9647d7a6384737090e08c99804803e50a847f68`
- `ENGINE_GIT_SHA`: `b310ac70d111475c4a53a7a1e0eb5bc3c5f6ebd4`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_01/`
- Jobdef revisions: canary `picard-noro-supply-worst-cases-01:1`; size-1 array
  attempts `:2`-`:4` were rejected by AWS (`Array Job size must be greater than
  1`); the three remaining cells were submitted as single jobs on `:5`, `:6`,
  and `:7`.

## Cells

| block | tier | seed | arm | job id | status |
|---|---|---:|---|---|---|
| `exp_declared_receipts_917326` | `fl_exp_12d_sens_p06_paxv_declared_receipts` | 917326 | `declared_receipts` | `3e6e3d48-be2d-4c31-84e3-5de58e38af8c` | SUCCEEDED |
| `cls_station_lots_962793` | `fl_cls_12d_sens_p06_paxv` | 962793 | `station_lots` | `c34c4798-d520-4079-966a-d3479a4d4990` | RUNNING |
| `spr_station_lots_1004210` | `fl_spr_12d_sens_p06_paxv` | 1004210 | `station_lots` | `9bb7c424-58c1-4636-9899-65afde27b3d2` | RUNNING |
| `meg_single_line_receipt_1030001` | `fl_meg_12d_sens_p06_paxv_single_line_receipt` | 1030001 | `single_line_receipt` | `b4e5a09a-a35e-4fc0-9775-145533f135e9` | RUNNING |

## Canary readout (exp declared_receipts 917326)

- Zip contract intact: `summary.json`, `growth_census.json.gz`,
  `rss_samples.json`; `num_epochs=288`, `trigger_status=LOCKDOWN`.
- Supply witness resolved as designed: `lot_layer_mode=declared_receipts`,
  `receipts_per_item_line=2`, `n_lots=1`, `n_lots_placed=1`,
  `n_contaminated=1`, `contaminated_by_item_line={shellfish: 1}`,
  `actual_venues_used=[MainDining]`.
- Measured endpoints: ever infected 129 (passenger 118, crew 11); reported
  cases 62 (passenger 59, crew 3); passenger infection attack rate 0.3734;
  passenger reported-case rate 0.1867; crew infection attack rate 0.0821;
  crew reported-case rate 0.0224.

## Next decision

After the remaining three jobs reach terminal states, sync the four zips,
extract final posted AR, VSP trigger epoch/day, passenger/crew channels, peak
epoch, and supply witnesses, then write the canonical readout. No anchor
fitting or default flip.
