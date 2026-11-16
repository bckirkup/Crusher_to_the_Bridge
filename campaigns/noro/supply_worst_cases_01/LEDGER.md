# FOOD-SUPPLY-01 worst-case examples ledger

**Date:** 2026-11-16
**Pathogens:** norwalk_gi
**Status:** complete
**Canonical readout:** `docs/ledger/FOOD-SUPPLY-01-WORST-CASES.md`
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
| `cls_station_lots_962793` | `fl_cls_12d_sens_p06_paxv` | 962793 | `station_lots` | `c34c4798-d520-4079-966a-d3479a4d4990` | SUCCEEDED |
| `spr_station_lots_1004210` | `fl_spr_12d_sens_p06_paxv` | 1004210 | `station_lots` | `9bb7c424-58c1-4636-9899-65afde27b3d2` | SUCCEEDED |
| `meg_single_line_receipt_1030001` | `fl_meg_12d_sens_p06_paxv_single_line_receipt` | 1030001 | `single_line_receipt` | `b4e5a09a-a35e-4fc0-9775-145533f135e9` | SUCCEEDED |

## Readout summary

All four seeds crossed the either-channel reported-case posting threshold. Passenger reported-case ARs were exp 18.67%, cls 8.45%, spr 6.95%, and meg 4.55%; VSP trigger epochs were 63 / 69 / 36 / 158 (days 3 / 3 / 2 / 7 at 24 epochs/day). Full tables and measured/inferred/hypothesis separation are in `docs/ledger/FOOD-SUPPLY-01-WORST-CASES.md`.

## Next decision

Expand to top-k seeds per hull/arm, or run paired `station_lots` vs receipt arms on the same seeds to separate supply burden from hull scale and mixing. No anchor fitting or default flip.
