# FOOD-SUPPLY-01-CANARY
**Date:** 2026-11-15
**Commit:** 43ecb68ddbe3b111137bdfcc5cdbb8080a664ffc
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 43ecb68ddbe3b111137bdfcc5cdbb8080a664ffc

Pinned local canary for the FOOD-SUPPLY-01 receipt/lot arms. Bounded diagnostic only: `fl_meg_12d_sens_p06_paxv` reduced to 2,000 agents and 72 epochs, seeds 8105–8124, `PYTHONHASHSEED=1`, `growth_chain_census.run_seed(..., payload_profile="lean")`, arms `station_lots` / `single_line_receipt` / `declared_receipts`. The measurement worktree was detached at `origin/main` `43ecb68d`; no AWS submission, no fitting, and no default flip.

Integrity: 20/20 seeds completed for every arm with no row errors and no missing seeds. Receipt witnesses were present on receipt arms (`single_line_receipt`: 140 receipts = 20 seeds × 7 item lines; `declared_receipts`: 280 receipts = 20 seeds × 14 item lines). Across all eight provisioned-lot objects, planned servings were conserved (`sum(event servings_taken) == object servings_served == lot_servings`) and objects ended `exhausted` with `objects_perished=0`. Credited dose was below nominal planned pan dose because takers are credited when present in the zone during the window; credited/planned dose ratios were 0.3457–0.6452.

## Arm summary

| arm | ok | posted | VSP | acquired | attack mean/median/max | pax infection AR mean/max | pax reported AR mean/max | CS-food acquisitions | fomite acquisitions |
|---|---:|---:|---:|---:|---|---|---|---:|---:|
| station_lots | 20/20 | 1 (5.00%) | 1 | 452 | 0.0330 / 0.0307 / 0.0745 | 3.54% / 9.00% | 0.26% / 3.00% | 170 | 258 |
| single_line_receipt | 20/20 | 0 (0.00%) | 0 | 344 | 0.0303 / 0.0285 / 0.0700 | 3.18% / 8.64% | 0.15% / 2.07% | 63 | 264 |
| declared_receipts | 20/20 | 0 (0.00%) | 0 | 278 | 0.0286 / 0.0288 / 0.0350 | 2.95% / 3.79% | 0.06% / 0.21% | 6 | 259 |

CS-food acquisitions on `station_lots` provisioned-lot seeds were 85/33/11/13/10/17 for seeds 8114/8115/8116/8120/8123/8124 (169 total); the remaining station_lots CS-food acquisition was seed 8108 with no provisioned lot. Receipt arms had CS-food acquisitions only on seed 8118: 63 for `single_line_receipt`, 6 for `declared_receipts`.

## Provisioned-lot witnesses

| seed | arm | item/supply | venues | epochs | windows/pans | planned servings | credited dose (GEC) | lot servings | titre GEC/g | outcome |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 8114 | station_lots | fresh_produce | MainDining_L | 10–33 | 14/17 | 438 | 9,901,743.51 | 438 | 255.841 | posted, VSP@70, detection@49 |
| 8115 | station_lots | garnish | MainDining_L | 16–43 | 19/19 | 139 | 25,801,844.94 | 139 | 2,378.966 | no detection |
| 8116 | station_lots | salad_leaf | MainDining_L | 40–43 | 4/4 | 64 | 23,556,130.29 | 64 | 4,724.114 | no detection |
| 8118 | single_line_receipt | shellfish (raw_or_rte_no_kill) | MainDining_L | 10–33 | 14/17 | 442 | 14,531,951.81 | 442 | 477.865 | detection@57, no VSP |
| 8118 | declared_receipts | shellfish (raw_or_rte_no_kill) | MainDining_L | 40–41 | 2/2 | 31 | 5,034,231.65 | 31 | 1,471.810 | no detection |
| 8120 | station_lots | deli | MainDining_L | 7–12 | 8/8 | 72 | 2,375,317.93 | 72 | 406.771 | no detection |
| 8123 | station_lots | garnish | MainDining_L | 10–12 | 4/4 | 65 | 1,632,339.18 | 65 | 586.657 | no detection |
| 8124 | station_lots | shellfish | MainDining_L | 16–18 | 3/4 | 69 | 566,244.25 | 69 | 171.895 | no detection |

Receipt witnesses: `single_line_receipt` drew 139 `none` and 1 `infectious` receipt; `declared_receipts` drew 279 `none` and 1 `infectious` receipt. Both infectious receipts were seed 8118 `shellfish` with `q_source_equivalent=0.003141488408576445`; receipt `q_line` was nonzero only for `shellfish`, `salad_leaf`, and `fresh_produce`, and zero for `deli`, `bakery`, `dairy`, and `garnish`.

Measured:

- The only post in the canary was `station_lots` seed 8114: one `fresh_produce` provisioned lot in `MainDining_L`, 17 `provisioned_lot` events, 438 planned servings, 9.90M credited GEC, 85 CS-food acquisitions, attack rate 0.0745, passenger infection AR 9.00%, passenger reported-case AR 3.00%, `detection_epoch=49`, `confirmation_epoch=70`, `vsp_trigger_epoch=70`.
- Receipt arms did not post on any of the 20 seeds. `single_line_receipt` seed 8118 was the largest receipt excursion — 442 planned servings, 17 events, 14.53M credited GEC, 63 CS-food acquisitions, attack rate 0.070, passenger reported-case AR 2.07%, `detection_epoch=57`, but no confirmation/VSP/`outbreak_occurred`. `declared_receipts` seed 8118 partitioned the same contaminated shellfish receipt into a 31-serving lot with 2 events, 5.03M credited GEC, 6 CS-food acquisitions, attack rate 0.034, and no detection.
- `station_lots` minted six provisioned lots on six seeds, including item lines the receipt layer assigns zero high-income prevalence (`garnish` twice, `deli` once) plus sourced lines (`fresh_produce`, `salad_leaf`, `shellfish`). Only the `fresh_produce` lot posted; the higher-credited-dose `garnish` and `salad_leaf` lots did not post, so credited dose mass alone does not determine the VSP tail.
- Fomite acquisitions were similar across arms (258/264/259), while CS-food acquisitions were 170/63/6. In this pinned cell the receipt/lot layer reduced provisioned supply-chain primers rather than amplifying them.

Inferred: under the pinned p06 cell, the receipt/lot layer is more conservative than `station_lots`: it zeroes unsourced item lines and, for `declared_receipts`, partitions lots into smaller venue/time windows. The single post came from `station_lots` `fresh_produce`, a line receipts could contaminate, but the receipt arms did not draw a contaminated `fresh_produce` receipt on seed 8114; with only one contaminated receipt seed, the receipt posting rate is unresolved but observed 0/20.

Hypothesis/next: the mega tail is not rescued by the receipt/lot layer as configured. The next decision is whether to expand receipt seed coverage for a rate estimate, test multiple concurrent sourced-item lots in the same meal windows, or keep `station_lots` as the tail baseline while using receipts as a provenance filter. No anchor fitting or default flip is implied.
