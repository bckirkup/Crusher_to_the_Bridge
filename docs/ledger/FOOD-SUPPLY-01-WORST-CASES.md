# FOOD-SUPPLY-01-WORST-CASES
**Date:** 2026-11-16
**Commit:** #1251
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** b310ac70d111475c4a53a7a1e0eb5bc3c5f6ebd4

FOOD-SUPPLY-01 worst-case example runs. Design is frozen in `campaigns/noro/supply_worst_cases_01/DESIGN.md`; ranking artifacts are `campaigns/noro/supply_worst_cases_01/ranking.md` and `ranking.json`; submission/job IDs are in `campaigns/noro/supply_worst_cases_01/LEDGER.md`. AWS Batch image `picard-campaign:noro-supply-worst01` digest `sha256:2a1cafdc5692c81a7bea2bfce9647d7a6384737090e08c99804803e50a847f68` (`ENGINE_GIT_SHA=b310ac70`). S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_01/`.

Run contract: four full-fidelity p06 cells, one seed per block, `epochs=288`, `payload_profile="lean"`, `PYTHONHASHSEED=1`. Seeds were selected by the frozen burden ranking over the completed `noro_supply_seed_scan_01` census: receipt arms use exact `quantity_g * lot_titre_gec_per_g`; `station_lots` uses `lot_servings * lot_titre_gec_per_g * 150 g` because serving mass is drawn later. This is an existence/tail probe, not a prevalence estimate.

Integrity: all four Batch jobs SUCCEEDED and wrote the unchanged zip contract (`summary.json`, `growth_census.json.gz`, `rss_samples.json`). `mechanisms.provisioned_source` resolved the selected arm in every cell. Container wall times were about 64 s (exp), 310 s (cls), 555 s (spr), and 1497 s (meg). `vsp_trigger_epoch` is the first epoch either passenger or crew reported-case counter exceeded the 3% either-channel VSP rule; `trigger_status` is the final escalation state; `outbreak_occurred` is the takeoff label, not the posting flag. Epochs are the summary's 0-based history indices; days use 24 epochs/day.

## Selection

| hull | arm | seed | burden_est (GEC) | burden kind | item lines | lots | venues |
|---|---|---:|---:|---|---|---:|---|
| exp | `declared_receipts` | 917326 | 6.448e8 | exact receipt mass | shellfish | 1 | MainDining |
| cls | `station_lots` | 962793 | 6.636e8 | estimated station servings, 150 g | dairy, shellfish | 2 | MainDining_L |
| spr | `station_lots` | 1004210 | 5.633e8 | estimated station servings, 150 g | salad_leaf, shellfish | 2 | MainDining_L |
| meg | `single_line_receipt` | 1030001 | 5.802e8 | exact receipt mass | shellfish | 1 | MainDining_L |

## Outcomes

| hull | platform | pax+crew | VSP epoch (day) | detect epoch (day) | confirm epoch (day) | peak epoch (day) | peak prevalence | pax infection AR | pax reported AR | crew infection AR | crew reported AR | overall AR | takeoff | final status | lots placed | venue |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|
| exp | expedition_cruise_450 | 316+134 | 63 (3) | 58 (3) | 59 (3) | 115 (5) | 127 | 37.34% | 18.67% | 8.21% | 2.24% | 28.67% | False | LOCKDOWN | 1 | MainDining |
| cls | classic_cruise_1900 | 1338+572 | 69 (3) | 63 (3) | 67 (3) | 133 (6) | 279 | 19.06% | 8.45% | 8.92% | 0.87% | 16.02% | True | LOCKDOWN | 2 | MainDining_L |
| spr | spirit_cruise_3000 | 2100+900 | 36 (2) | 30 (2) | 34 (2) | 119 (5) | 340 | 15.05% | 6.95% | 6.67% | 1.33% | 12.53% | True | LOCKDOWN | 2 | MainDining_L |
| meg | mega_cruise_5000 | 4900+2100 | 158 (7) | 60 (3) | 158 (7) | 287 (12) | 901 | 14.45% | 4.55% | 14.71% | 3.19% | 14.53% | True | CONFIRMED | 1 | MainDining_L |

## Measured / inferred / hypothesis

Measured:

- All four selected seeds crossed the either-channel reported-case posting threshold (`vsp_trigger_epoch` non-null): exp epoch 63 / day 3, cls epoch 69 / day 3, spr epoch 36 / day 2, meg epoch 158 / day 7.
- Passenger reported-case ARs were exp 18.67%, cls 8.45%, spr 6.95%, and meg 4.55%. Passenger infection ARs were 37.34%, 19.06%, 15.05%, and 14.45%; overall attack rates were 28.67%, 16.02%, 12.53%, and 14.53%.
- Receipt-arm witnesses boarded one served contaminated lot each (exp `declared_receipts` shellfish at `MainDining`; meg `single_line_receipt` shellfish at `MainDining_L`). Station-lot witnesses placed two contaminated lots each on cls and spr at `MainDining_L`.
- `outbreak_occurred` was true for cls/spr/meg and false for exp; exp still crossed the reported-case posting threshold and ended `LOCKDOWN`. The takeoff label uses the incidence second derivative at the first VSP-active epoch, so it is not a posting flag.

Inferred:

- Worst-case burden seeds are sufficient to produce VSP-posted voyages on all four hulls, but estimated supply burden does not map monotonically to passenger reported AR: the small expedition declared-receipt seed had the highest passenger reported AR, while the mega receipt seed had the lowest.
- The receipt arms remain more conservative in contaminated-lot count than `station_lots`, but a single high-burden receipt seed can still produce a large passenger-reported excursion on a small hull.

Hypothesis/next:

- These are single-seed existence proofs, not rates; do not fit anchors or flip defaults from them. Next decision: whether to expand to top-k seeds per hull/arm or run paired `station_lots` vs receipt arms on the same seeds to separate supply burden from hull scale and mixing.
