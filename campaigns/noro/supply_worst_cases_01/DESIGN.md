# FOOD-SUPPLY-01 worst-case examples

**Date:** 2026-11-16
**Pathogens:** norwalk_gi
**Status:** design frozen before cells run
**Parent scan:** `campaigns/noro/supply_seed_scan_01/` (`docs/ledger/FOOD-SUPPLY-01-SEED-SCAN.md`)

## Question

The seed scan measured which voyage seeds board contaminated provisioned
supply. This bounded example panel asks the next question: for the largest
supply-burden seeds on each hull, what final posted attack rate and VSP timing
does the full p06 passenger-venue cell produce?

## Ranking rule (frozen)

Rank contaminated served-lot seeds by estimated lot burden:

- receipt lots: `quantity_g * lot_titre_gec_per_g` (measured mass and titre);
- station lots: `lot_servings * lot_titre_gec_per_g * 150 g` (serving mass is
  drawn later; 150 g is the declared serving-mass midpoint, so station-lot
  burden is an estimate, not an exact mass).

Selection: highest estimated burden seed per hull across the three supply arms
in `noro_supply_seed_scan_01`. Ties are broken by larger `lot_servings`, then
by lower seed id. Receipt arms are compared by exact mass; station lots by the
midpoint estimate above.

## Cells (frozen)

| block | tier | seed | arm | selected burden witness |
|---|---:|---:|---|---|
| `exp_declared_receipts_917326` | `fl_exp_12d_sens_p06_paxv_declared_receipts` | 917326 | `declared_receipts` | shellfish, 575 servings, 131,023 g, titre 4,921 GEC/g |
| `cls_station_lots_962793` | `fl_cls_12d_sens_p06_paxv` | 962793 | `station_lots` | dairy + shellfish, 1,146 servings, max titre 4,557 GEC/g |
| `spr_station_lots_1004210` | `fl_spr_12d_sens_p06_paxv` | 1004210 | `station_lots` | salad_leaf + shellfish, 833 servings, max titre 4,804 GEC/g |
| `meg_single_line_receipt_1030001` | `fl_meg_12d_sens_p06_paxv_single_line_receipt` | 1030001 | `single_line_receipt` | shellfish, 524 servings, 116,103 g, titre 4,997 GEC/g |

All cells use the p06 passenger-venue tier shape: 288 epochs, dose adjustment
7.57, `syndromic_comp65`, `station_zone_pin` passenger Dining venue, and
`--payload lean` for census memory.

## Endpoints

Report, per cell:

- `posted` / `outbreak_occurred` and `vsp_trigger_epoch` (timing);
- passenger and crew infection AR, ever-ill AR, and reported-case AR;
- common-source provisioned-lot events/takers/dose credited;
- census acquisitions/imports and role checkpoints;
- supply witness (`n_lots_placed`, `actual_venues_used`, item lines) so the
  full run can be checked against the 1-epoch scan row for the same seed/arm.

Admissibility/integrity: the run is valid only if the summary supply witness
shows the same arm mode and contaminated item lines as the scan row; a mismatch
is a defect, not a model result.

Diagnostics reported but never selected on: quiet-voyage acquisition counts,
crew-only posts, and non-supply common-source events.

## Non-goals

- No anchor fitting and no claim that these four seeds estimate a rate.
- No default flip of `station_lots` vs receipt arms.
- No renewal-boarding or contact-constant changes.
- No CE comparator work; CE remains paused pending the missing-constants audit.
