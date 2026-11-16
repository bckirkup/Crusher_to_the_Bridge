# FOOD-SUPPLY-01 worst-case examples ledger

**Date:** 2026-11-16
**Pathogens:** norwalk_gi
**Status:** canary running
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
- Jobdef: `picard-noro-supply-worst-cases-01:1`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_01/`

## Cells

| block | tier | seed | arm | status |
|---|---|---:|---|---|
| `exp_declared_receipts_917326` | `fl_exp_12d_sens_p06_paxv_declared_receipts` | 917326 | `declared_receipts` | canary RUNNING |
| `cls_station_lots_962793` | `fl_cls_12d_sens_p06_paxv` | 962793 | `station_lots` | pending canary |
| `spr_station_lots_1004210` | `fl_spr_12d_sens_p06_paxv` | 1004210 | `station_lots` | pending canary |
| `meg_single_line_receipt_1030001` | `fl_meg_12d_sens_p06_paxv_single_line_receipt` | 1030001 | `single_line_receipt` | pending canary |

## Canary

- Job: `3e6e3d48-be2d-4c31-84e3-5de58e38af8c`
- Name: `picard-noro-supply-worst-cases-01-exp_declared_receipts_917326-20261116-135031-canary`
- Submitted as a single `--canary --index 0` job before the remaining three
  blocks, per campaign preflight.

## Next decision

After the canary reaches SUCCEEDED, inspect the run zip for
`mechanisms.provisioned_source` (`lot_layer_mode`, `receipts_per_item_line`,
`n_lots_placed`, `actual_venues_used`) and the unchanged summary/timeseries
contract; then submit the remaining three blocks, aggregate final posted AR,
VSP trigger epoch/day, passenger/crew channels, and supply witnesses, and write
the canonical readout. No anchor fitting or default flip.
