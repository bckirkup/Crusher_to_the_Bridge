# FOOD-SUPPLY-01-SEED-SCAN
**Date:** 2026-11-16
**Commit:** 7d0eb006e521f607b611ce4d0599c6af074f9d94
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 357dfac06103ed6b496e2428099d13b8d5117ddc

FOOD-SUPPLY-01 seed-initiation census. Design is frozen in `campaigns/noro/supply_seed_scan_01/DESIGN.md`; submission/job IDs are in `campaigns/noro/supply_seed_scan_01/LEDGER.md`. AWS Batch image `picard-campaign:noro-supply-seed01` digest `sha256:54fc294e0f203e21952a31b1fef00f4294e46669eb6e3c1f9b657a6f39d6f521` (`ENGINE_GIT_SHA=357dfac0`). S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_seed_scan_01/`.

Run contract: 126,200 unique voyage seeds across exp/cls/spr/meg, three arms (`station_lots`, `single_line_receipt`, `declared_receipts`), `epochs=1`, `num_agents=100`, `payload_profile="lean"`, `PYTHONHASHSEED=1`. That is 378,600 one-epoch seed scans in 3,786 JSONL chunks. This is a boarding/prevalence census only: it measures which seeds draw contaminated provisioned supply, not posted attack rate, roles, or timing.

Integrity: all 12 Batch arrays SUCCEEDED, 3,786/3,786 children SUCCEEDED, 0 child failures, 378,600 rows, 0 row-level `error` fields, 0 missing `provisioned_source` blocks. The pre-Batch canary child (`616746f6-ad28-49f5-829d-43d10cce24d5`) wrote 100 rows with 0 errors before the arrays were submitted.

## Seed boarding prevalence

`station_lots` uses scalar `q_source_drawn=0.0047` for every station-item line. Receipt arms use per-item-line sourced prevalences drawn per voyage; `q_source_equivalent` is therefore seed-continuous (exp/cls/spr/meg mean about 0.00277, range about 0.00088–0.00466) rather than the station_lots scalar.

| hull | arm | seeds scanned | boarding witness | witness count | seed prevalence | unit contamination | served lot objects |
|---|---|---:|---|---:|---:|---:|---:|
| exp | station_lots | 56,000 | seeds with >=1 contaminated station lot | 5,354 | 9.561% [9.320, 9.807] | 5,608 / 1,176,000 station draws = 0.4769% | 5,608 |
| cls | station_lots | 34,000 | seeds with >=1 contaminated station lot | 5,221 | 15.356% [14.977, 15.743] | 5,658 / 1,187,893 = 0.4763% | 5,658 |
| spr | station_lots | 19,000 | seeds with >=1 contaminated station lot | 4,775 | 25.132% [24.520, 25.753] | 5,432 / 1,179,969 = 0.4604% | 5,432 |
| meg | station_lots | 17,200 | seeds with >=1 contaminated station lot | 4,697 | 27.308% [26.647, 27.979] | 5,436 / 1,191,372 = 0.4563% | 5,436 |
| exp | single_line_receipt | 56,000 | seeds with >=1 contaminated receipt / served lot | 1,051 | 1.877% [1.768, 1.993] | 1,058 / 392,000 receipts = 0.2699% | 1,058 |
| cls | single_line_receipt | 34,000 | seeds with >=1 contaminated receipt / served lot | 688 | 2.024% [1.879, 2.179] | 693 / 238,000 = 0.2912% | 693 |
| spr | single_line_receipt | 19,000 | seeds with >=1 contaminated receipt / served lot | 385 | 2.026% [1.835, 2.237] | 386 / 133,000 = 0.2902% | 386 |
| meg | single_line_receipt | 17,200 | seeds with >=1 contaminated receipt / served lot | 348 | 2.023% [1.823, 2.245] | 351 / 120,400 = 0.2915% | 351 |
| exp | declared_receipts | 56,000 | seeds with >=1 contaminated receipt | 2,115 | 3.777% [3.622, 3.938] | 2,147 / 784,000 = 0.2739% | 1,070 |
| cls | declared_receipts | 34,000 | seeds with >=1 contaminated receipt | 1,301 | 3.826% [3.628, 4.036] | 1,324 / 476,000 = 0.2782% | 672 |
| spr | declared_receipts | 19,000 | seeds with >=1 contaminated receipt | 747 | 3.932% [3.664, 4.217] | 754 / 266,000 = 0.2835% | 370 |
| meg | declared_receipts | 17,200 | seeds with >=1 contaminated receipt | 699 | 4.064% [3.779, 4.369] | 709 / 240,800 = 0.2944% | 361 |

For receipt arms the served-lot seed witness is the boarding witness that matches `station_lots`: `single_line_receipt` served-lot seeds are 1,051 / 688 / 385 / 348 (same counts as contaminated-receipt seeds because every contaminated single-line receipt was service-eligible and venue-bearing in this pinned scan); `declared_receipts` served-lot seeds are 1,065 / 669 / 366 / 361 = 1.902% / 1.968% / 1.926% / 2.099%.

Wilson 95% intervals are shown for seed prevalence; unit contamination is contaminated lots/receipts divided by station draws or receipt draws.

## Lot size and titre

Contaminated supply lots are large enough that lot size is not the receipt-arm bottleneck. Across arms and hulls, served `lot_servings` stayed in the designed 30–600 range with medians ~116–157 and means ~172–210; `lot_titre_gec_per_g` medians were ~836–952 GEC/g with means ~1353–1514 and max ~5000.

| arm | hull | lot_servings mean / median / min / max | lot_titre mean / median / min / max (GEC/g) |
|---|---|---|---|
| station_lots | exp | 190.0 / 134.0 / 30 / 600 | 1389.7 / 865.0 / 150.0 / 4998.2 |
| station_lots | cls | 192.9 / 139.0 / 30 / 600 | 1382.4 / 852.3 / 150.1 / 4999.6 |
| station_lots | spr | 187.0 / 131.0 / 30 / 600 | 1378.8 / 838.2 / 150.0 / 4999.2 |
| station_lots | meg | 189.0 / 130.0 / 30 / 600 | 1411.1 / 910.5 / 150.0 / 4999.6 |
| single_line_receipt | exp | 183.9 / 129.0 / 30 / 600 | 1352.8 / 835.8 / 150.3 / 4994.7 |
| single_line_receipt | cls | 188.4 / 129.0 / 30 / 598 | 1408.3 / 910.3 / 151.1 / 4992.3 |
| single_line_receipt | spr | 172.5 / 116.5 / 30 / 600 | 1513.7 / 904.4 / 153.3 / 4966.3 |
| single_line_receipt | meg | 210.3 / 157.0 / 31 / 584 | 1434.7 / 949.7 / 156.3 / 4997.3 |
| declared_receipts | exp | 194.0 / 138.0 / 30 / 597 | 1402.6 / 917.5 / 150.1 / 4997.4 |
| declared_receipts | cls | 187.3 / 135.0 / 30 / 600 | 1400.9 / 894.9 / 150.1 / 4997.5 |
| declared_receipts | spr | 178.8 / 122.0 / 30 / 591 | 1452.3 / 952.1 / 154.2 / 4994.2 |
| declared_receipts | meg | 181.0 / 132.0 / 30 / 591 | 1481.8 / 919.4 / 151.1 / 4975.6 |

Receipt served lots also carry mass witnesses: `quantity_g` means were ~25.6k–31.7k g with medians ~15.8k–21.6k g and maxima ~120k–143k g.

## Item-line composition

`station_lots` contaminates all seven item lines in roughly equal proportions within each hull (per-hull item counts were in the ~754–839 range per line), including lines the receipt layer assigns zero high-income prevalence (`deli`, `bakery`, `dairy`, `garnish`). Receipt arms contaminated only the three sourced raw/RTE lines. Across both receipt arms, contaminated receipts were shellfish 4,930 (66.4%), salad_leaf 1,418 (19.1%), fresh_produce 1,074 (14.5%); served lots were shellfish 3,288 (66.3%), salad_leaf 940 (18.9%), fresh_produce 733 (14.8%). No receipt-arm row produced `rna_positive_noninfectious` or a contaminated `deli`/`bakery`/`dairy`/`garnish` receipt.

`declared_receipts` drew 4,934 contaminated receipts but only 2,473 became served lots. The split is exactly venue-driven under the pinned single-Dining-zone cells: 2,473 contaminated receipts were `receipt_index=0` with a nonempty `venues_served` and a `lot_id`; 2,461 were `receipt_index=1` with `venues_served=[]` and no lot. `_cs_receipt_venue_sets` partitions the pinned venue list, so with one pinned zone the second declared receipt per item line has no venue and cannot board a lot.

## Measured / inferred / hypothesis

Measured:

- `station_lots` boards a contaminated provisioned lot on 20,047 / 126,200 seeds (15.889%) overall, rising with station count: exp 9.561%, cls 15.356%, spr 25.132%, meg 27.308%. Per-station contamination was ~0.456–0.477%, consistent with scalar `q_source=0.0047` across 21/35/63/70 station-item lines.
- Receipt arms board served contaminated lots far more rarely: `single_line_receipt` 2,472 / 126,200 seeds (1.959%) and `declared_receipts` 2,461 / 126,200 seeds (1.950%) when counted by served lots. Per-receipt contamination was ~0.27–0.29%.
- `declared_receipts` doubles contaminated receipt draws versus `single_line_receipt` (4,862 vs 2,472 contaminated-receipt seeds overall) but does not increase served-lot yield because half of the declared receipts are venue-empty under the single pinned Dining zone.
- Lot size/titre distributions are similar across arms; the receipt-arm reduction is in contamination eligibility/venue realization, not in smaller lots.

Inferred:

- For the pinned p06 passenger-venue cell, `station_lots` is a much richer supply-chain primer than either receipt arm. The receipt layer is more conservative because it restricts contamination to sourced raw/RTE item lines and, for `declared_receipts`, spends half of its contaminated receipts on venue-empty receipt indices under a one-zone pin.
- These JSONL seed lists are reusable for stratified full-fidelity runs: they identify exact seeds that board contaminated station lots or served receipt lots without paying for quiet full voyages.

Hypothesis/next:

- The posted-AR tail still needs full-fidelity paired runs on enriched seeds. The cheap scan says the supply-chain boarding bottleneck is prevalence/eligibility/venue realization, not lot mass; whether any of these seeds convert into large posted passenger AR remains unmeasured.
- Next decision: select stratified full-run seeds from `station_lots` contaminated lots (and a smaller receipt served-lot set) for the reduced 2,000-agent/72-epoch paired screen, with lot size/titre and item line as stratifiers. Do not fit anchors or flip defaults from this census.
