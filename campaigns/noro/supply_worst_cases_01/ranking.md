# FOOD-SUPPLY-01 contaminated-seed ranking

Source: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_seed_scan_01/` (3,786 JSONL files, 378,600 rows, 24,980 contaminated served-lot cells).

Method: rank seed/arm/hull cells by summed provisioned-lot burden. Receipt arms use exact `quantity_g * lot_titre_gec_per_g`; `station_lots` uses `lot_servings * lot_titre_gec_per_g * 150 g` because serving mass is drawn later. Venues use object `venues_served`/`zone` plus `provisioned_source.actual_venues_used`.

## Top 10 per hull across arms

| rank | hull | arm | seed | burden est | kind | lots | item lines | venues |
|---:|---|---|---:|---:|---|---:|---|---|
| 1 | exp | declared_receipts | 917326 | 6.448e+08 | exact_receipt_mass | 1 | shellfish | MainDining |
| 2 | exp | declared_receipts | 926940 | 5.866e+08 | exact_receipt_mass | 1 | shellfish | MainDining |
| 3 | exp | declared_receipts | 955132 | 4.842e+08 | exact_receipt_mass | 1 | salad_leaf | MainDining |
| 4 | exp | station_lots | 939824 | 4.314e+08 | estimated_station_servings_150g | 1 | dairy | MainDining |
| 5 | exp | single_line_receipt | 923140 | 4.256e+08 | exact_receipt_mass | 1 | salad_leaf | MainDining |
| 6 | exp | station_lots | 908346 | 4.187e+08 | estimated_station_servings_150g | 2 | deli, shellfish | MainDining |
| 7 | exp | declared_receipts | 905829 | 4.179e+08 | exact_receipt_mass | 1 | shellfish | MainDining |
| 8 | exp | station_lots | 939734 | 4.171e+08 | estimated_station_servings_150g | 1 | bakery | MainDining |
| 9 | exp | station_lots | 911128 | 4.140e+08 | estimated_station_servings_150g | 1 | deli | MainDining |
| 10 | exp | station_lots | 948291 | 4.094e+08 | estimated_station_servings_150g | 1 | shellfish | MainDining |
| 1 | cls | station_lots | 962793 | 6.636e+08 | estimated_station_servings_150g | 2 | dairy, shellfish | MainDining_L |
| 2 | cls | single_line_receipt | 966561 | 6.238e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| 3 | cls | declared_receipts | 970017 | 4.920e+08 | exact_receipt_mass | 1 | fresh_produce | MainDining_L |
| 4 | cls | station_lots | 987772 | 4.545e+08 | estimated_station_servings_150g | 2 | garnish, shellfish | MainDining_L |
| 5 | cls | declared_receipts | 982557 | 4.262e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| 6 | cls | single_line_receipt | 961033 | 4.261e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| 7 | cls | single_line_receipt | 970267 | 4.206e+08 | exact_receipt_mass | 1 | fresh_produce | MainDining_L |
| 8 | cls | station_lots | 971842 | 4.121e+08 | estimated_station_servings_150g | 1 | salad_leaf | MainDining_L |
| 9 | cls | station_lots | 963538 | 4.121e+08 | estimated_station_servings_150g | 1 | dairy | MainDining_L |
| 10 | cls | station_lots | 973303 | 4.110e+08 | estimated_station_servings_150g | 1 | bakery | MainDining_L |
| 1 | spr | station_lots | 1004210 | 5.633e+08 | estimated_station_servings_150g | 2 | salad_leaf, shellfish | MainDining_L |
| 2 | spr | single_line_receipt | 1018738 | 5.268e+08 | exact_receipt_mass | 1 | fresh_produce | MainDining_L |
| 3 | spr | declared_receipts | 1008624 | 4.481e+08 | exact_receipt_mass | 1 | salad_leaf | MainDining_L |
| 4 | spr | station_lots | 1015129 | 4.437e+08 | estimated_station_servings_150g | 1 | shellfish | MainDining_L |
| 5 | spr | station_lots | 1015885 | 4.222e+08 | estimated_station_servings_150g | 1 | garnish | MainDining_L |
| 6 | spr | single_line_receipt | 1006710 | 4.218e+08 | exact_receipt_mass | 1 | salad_leaf | MainDining_L |
| 7 | spr | station_lots | 1015042 | 4.154e+08 | estimated_station_servings_150g | 2 | bakery, salad_leaf | MainDining_L |
| 8 | spr | station_lots | 1001393 | 4.133e+08 | estimated_station_servings_150g | 1 | dairy | MainDining_L |
| 9 | spr | station_lots | 1004358 | 4.048e+08 | estimated_station_servings_150g | 1 | garnish | MainDining_L |
| 10 | spr | station_lots | 1009265 | 3.998e+08 | estimated_station_servings_150g | 1 | garnish | MainDining_L |
| 1 | meg | single_line_receipt | 1030001 | 5.802e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| 2 | meg | declared_receipts | 1031386 | 5.200e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| 3 | meg | station_lots | 1036232 | 4.553e+08 | estimated_station_servings_150g | 2 | bakery, deli | MainDining_L |
| 4 | meg | station_lots | 1020931 | 4.447e+08 | estimated_station_servings_150g | 3 | dairy, deli | MainDining_L |
| 5 | meg | station_lots | 1021334 | 4.302e+08 | estimated_station_servings_150g | 1 | fresh_produce | MainDining_L |
| 6 | meg | station_lots | 1034274 | 4.252e+08 | estimated_station_servings_150g | 1 | fresh_produce | MainDining_L |
| 7 | meg | station_lots | 1027804 | 4.219e+08 | estimated_station_servings_150g | 2 | deli, fresh_produce | MainDining_L |
| 8 | meg | station_lots | 1026685 | 4.211e+08 | estimated_station_servings_150g | 1 | garnish | MainDining_L |
| 9 | meg | station_lots | 1023994 | 4.066e+08 | estimated_station_servings_150g | 2 | dairy, salad_leaf | MainDining_L |
| 10 | meg | station_lots | 1032640 | 4.063e+08 | estimated_station_servings_150g | 1 | fresh_produce | MainDining_L |

## Selected worst-case examples

| hull | arm | seed | burden est | kind | lots | item lines | venues |
|---|---|---:|---:|---|---:|---|---|
| cls | station_lots | 962793 | 6.636e+08 | estimated_station_servings_150g | 2 | dairy, shellfish | MainDining_L |
| exp | declared_receipts | 917326 | 6.448e+08 | exact_receipt_mass | 1 | shellfish | MainDining |
| meg | single_line_receipt | 1030001 | 5.802e+08 | exact_receipt_mass | 1 | shellfish | MainDining_L |
| spr | station_lots | 1004210 | 5.633e+08 | estimated_station_servings_150g | 2 | salad_leaf, shellfish | MainDining_L |
