# noro_supply_solver_screen_01 readout

**Measured at:** `6742f1a456e5717cf813c57bc9b3e34bb532fda5`
S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/`
Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver01@sha256:f25d74cd225bc4ade19a012ba801b25f91289f80f3c3778bfd6c27c343a0053a`
Cells: 88 run zips, 0 failed/missing.

Posting means `vsp_trigger_epoch is not None` (either-channel reported-case VSP rule). ARs are fractions; tables show percents where labelled.

## station_lots_contaminated

| solver | n | posted | posted-conditional pax reported AR (median [IQR]) | VSP epoch median [IQR] | VSP day median [IQR] |
|---|---|---|---|---|---|
| discrete | 16 | 16 (100.0%) | 8.5% [5.5%, 11.1%] | 70.0 [62.2, 98.5] | 3.0 [3.0, 5.0] |
| continuous | 16 | 16 (100.0%) | 7.8% [5.0%, 11.6%] | 83.5 [58.2, 94.2] | 4.0 [3.0, 4.0] |

Paired posting cells: both 16, discrete-only 0, continuous-only 0, neither 0.

| endpoint | paired n | median diff (continuous - discrete) | IQR | sign p | positive/negative/zero |
|---|---|---|---|---|---|
| posted | 16 | 0.000 | [0.000, 0.000] | — | 0/0/16 |
| pax reported AR (both posted) | 16 | -0.2% | [-1.7%, 1.9%] | 0.791 | 6/8/2 |
| VSP epoch (both posted) | 16 | -3.5 | [-9.2, 8.2] | 0.454 | 6/10/0 |

Role partition (all paired seeds; median [IQR] per arm, then paired diff):

| metric | discrete median | continuous median | median diff | sign p | +/-/0 |
|---|---|---|---|---|---|
| passenger reported-case AR | 8.5% | 7.8% | -0.2% | 0.791 | 6/8/2 |
| crew reported-case AR | 1.5% | 1.1% | 0.0% | 0.774 | 5/7/4 |
| passenger ever-ill AR | 11.5% | 10.9% | -0.2% | 0.791 | 6/8/2 |
| crew ever-ill AR | 2.2% | 2.2% | -0.4% | 1.000 | 7/8/1 |
| passenger infection AR | 19.5% | 19.0% | 0.3% | 0.804 | 9/7/0 |
| crew infection AR | 8.2% | 8.2% | 0.0% | 1.000 | 8/8/0 |

Ranges (min–max):

| metric | discrete range | continuous range |
|---|---|---|
| posted-conditional pax reported AR | 2.9%–19.6% | 3.5%–17.7% |
| VSP epoch (posted) | 50.0–283.0 | 40.0–112.0 |
| VSP day (posted) | 3.0–12.0 | 2.0–5.0 |
| passenger reported-case AR | 2.9%–19.6% | 3.5%–17.7% |
| crew reported-case AR | 0.0%–3.7% | 0.0%–4.5% |
| passenger ever-ill AR | 3.2%–25.3% | 5.4%–22.5% |
| crew ever-ill AR | 0.0%–5.2% | 0.0%–5.2% |
| passenger infection AR | 5.4%–36.4% | 7.6%–35.1% |
| crew infection AR | 3.7%–11.9% | 3.7%–12.7% |

Secondary witnesses (medians):

| metric | discrete | continuous | paired median diff | sign p |
|---|---|---|---|---|
| overall attack_rate | 16.6% | 16.1% | 0.2% | 0.607 |
| peak prevalence | 70.0 | 67.0 | 0.5 | 0.581 |
| common_source_events | 24.5 | 27.5 | -0.5 | 0.791 |
| common_source_takers | 172.5 | 192.5 | -3.0 | 0.424 |

## station_lots_quiet

| solver | n | posted | posted-conditional pax reported AR (median [IQR]) | VSP epoch median [IQR] | VSP day median [IQR] |
|---|---|---|---|---|---|
| discrete | 8 | 0 (0.0%) | — [—, —] | — [—, —] | — [—, —] |
| continuous | 8 | 0 (0.0%) | — [—, —] | — [—, —] | — [—, —] |

Paired posting cells: both 0, discrete-only 0, continuous-only 0, neither 8.

| endpoint | paired n | median diff (continuous - discrete) | IQR | sign p | positive/negative/zero |
|---|---|---|---|---|---|
| posted | 8 | 0.000 | [0.000, 0.000] | — | 0/0/8 |
| pax reported AR (both posted) | 0 | — | [—, —] | — | 0/0/0 |
| VSP epoch (both posted) | 0 | — | [—, —] | — | 0/0/0 |

Role partition (all paired seeds; median [IQR] per arm, then paired diff):

| metric | discrete median | continuous median | median diff | sign p | +/-/0 |
|---|---|---|---|---|---|
| passenger reported-case AR | 0.0% | 0.0% | 0.0% | — | 0/0/8 |
| crew reported-case AR | 0.0% | 0.0% | 0.0% | 1.000 | 0/1/7 |
| passenger ever-ill AR | 0.0% | 0.0% | 0.0% | — | 0/0/8 |
| crew ever-ill AR | 0.0% | 0.0% | 0.0% | — | 0/0/8 |
| passenger infection AR | 2.2% | 2.2% | 0.0% | — | 0/0/8 |
| crew infection AR | 3.4% | 3.4% | 0.0% | — | 0/0/8 |

Ranges (min–max):

| metric | discrete range | continuous range |
|---|---|---|
| posted-conditional pax reported AR | —–— | —–— |
| VSP epoch (posted) | —–— | —–— |
| VSP day (posted) | —–— | —–— |
| passenger reported-case AR | 0.0%–0.3% | 0.0%–0.3% |
| crew reported-case AR | 0.0%–0.8% | 0.0%–0.8% |
| passenger ever-ill AR | 0.0%–0.3% | 0.0%–0.3% |
| crew ever-ill AR | 0.0%–0.8% | 0.0%–0.8% |
| passenger infection AR | 0.9%–3.2% | 0.9%–3.2% |
| crew infection AR | 1.5%–4.5% | 1.5%–4.5% |

Secondary witnesses (medians):

| metric | discrete | continuous | paired median diff | sign p |
|---|---|---|---|---|
| overall attack_rate | 2.4% | 2.4% | 0.0% | — |
| peak prevalence | 11.0 | 11.0 | 0.0 | — |
| common_source_events | 1.0 | 1.0 | 0.0 | — |
| common_source_takers | 4.5 | 4.5 | 0.0 | — |

## single_line_receipt_contaminated

| solver | n | posted | posted-conditional pax reported AR (median [IQR]) | VSP epoch median [IQR] | VSP day median [IQR] |
|---|---|---|---|---|---|
| discrete | 10 | 10 (100.0%) | 7.4% [5.2%, 10.8%] | 80.0 [74.2, 94.2] | 4.0 [4.0, 4.8] |
| continuous | 10 | 10 (100.0%) | 6.6% [5.1%, 12.0%] | 89.0 [81.0, 108.2] | 4.0 [4.0, 5.0] |

Paired posting cells: both 10, discrete-only 0, continuous-only 0, neither 0.

| endpoint | paired n | median diff (continuous - discrete) | IQR | sign p | positive/negative/zero |
|---|---|---|---|---|---|
| posted | 10 | 0.000 | [0.000, 0.000] | — | 0/0/10 |
| pax reported AR (both posted) | 10 | -0.3% | [-0.9%, 1.3%] | 1.000 | 4/5/1 |
| VSP epoch (both posted) | 10 | 2.0 | [-3.5, 8.2] | 0.344 | 7/3/0 |

Role partition (all paired seeds; median [IQR] per arm, then paired diff):

| metric | discrete median | continuous median | median diff | sign p | +/-/0 |
|---|---|---|---|---|---|
| passenger reported-case AR | 7.4% | 6.6% | -0.3% | 1.000 | 4/5/1 |
| crew reported-case AR | 1.9% | 1.5% | -0.4% | 0.727 | 3/5/2 |
| passenger ever-ill AR | 8.9% | 8.4% | -0.5% | 0.754 | 4/6/0 |
| crew ever-ill AR | 2.6% | 2.2% | -0.7% | 0.508 | 3/6/1 |
| passenger infection AR | 18.0% | 17.7% | -0.8% | 0.180 | 2/7/1 |
| crew infection AR | 6.3% | 8.6% | 0.7% | 0.180 | 7/2/1 |

Ranges (min–max):

| metric | discrete range | continuous range |
|---|---|---|
| posted-conditional pax reported AR | 4.4%–15.2% | 4.1%–14.2% |
| VSP epoch (posted) | 49.0–122.0 | 49.0–143.0 |
| VSP day (posted) | 3.0–6.0 | 3.0–6.0 |
| passenger reported-case AR | 4.4%–15.2% | 4.1%–14.2% |
| crew reported-case AR | 0.0%–3.0% | 0.0%–3.0% |
| passenger ever-ill AR | 6.0%–20.6% | 6.0%–18.7% |
| crew ever-ill AR | 1.5%–6.0% | 0.0%–5.2% |
| passenger infection AR | 12.0%–32.6% | 11.4%–31.0% |
| crew infection AR | 2.2%–14.9% | 3.0%–15.7% |

Secondary witnesses (medians):

| metric | discrete | continuous | paired median diff | sign p |
|---|---|---|---|---|
| overall attack_rate | 13.9% | 15.4% | -0.3% | 0.344 |
| peak prevalence | 59.0 | 64.5 | -1.5 | 0.508 |
| common_source_events | 9.5 | 11.5 | 0.0 | 0.625 |
| common_source_takers | 144.0 | 137.5 | 0.0 | 1.000 |

## declared_receipts_contaminated

| solver | n | posted | posted-conditional pax reported AR (median [IQR]) | VSP epoch median [IQR] | VSP day median [IQR] |
|---|---|---|---|---|---|
| discrete | 10 | 10 (100.0%) | 8.5% [6.6%, 11.9%] | 75.0 [63.8, 78.2] | 4.0 [3.0, 4.0] |
| continuous | 10 | 10 (100.0%) | 9.3% [5.6%, 11.9%] | 69.0 [61.2, 82.5] | 3.0 [3.0, 4.0] |

Paired posting cells: both 10, discrete-only 0, continuous-only 0, neither 0.

| endpoint | paired n | median diff (continuous - discrete) | IQR | sign p | positive/negative/zero |
|---|---|---|---|---|---|
| posted | 10 | 0.000 | [0.000, 0.000] | — | 0/0/10 |
| pax reported AR (both posted) | 10 | 0.8% | [-0.7%, 1.3%] | 0.508 | 6/3/1 |
| VSP epoch (both posted) | 10 | -1.5 | [-20.2, 4.2] | 1.000 | 5/5/0 |

Role partition (all paired seeds; median [IQR] per arm, then paired diff):

| metric | discrete median | continuous median | median diff | sign p | +/-/0 |
|---|---|---|---|---|---|
| passenger reported-case AR | 8.5% | 9.3% | 0.8% | 0.508 | 6/3/1 |
| crew reported-case AR | 2.6% | 1.9% | -0.8% | 0.754 | 4/6/0 |
| passenger ever-ill AR | 10.6% | 10.3% | -0.6% | 0.508 | 3/6/1 |
| crew ever-ill AR | 4.1% | 3.4% | 0.0% | 1.000 | 4/4/2 |
| passenger infection AR | 20.2% | 21.8% | 0.5% | 0.508 | 6/3/1 |
| crew infection AR | 9.7% | 9.7% | -1.5% | 0.508 | 3/6/1 |

Ranges (min–max):

| metric | discrete range | continuous range |
|---|---|---|
| posted-conditional pax reported AR | 3.8%–16.1% | 4.8%–17.4% |
| VSP epoch (posted) | 57.0–122.0 | 39.0–98.0 |
| VSP day (posted) | 3.0–6.0 | 2.0–5.0 |
| passenger reported-case AR | 3.8%–16.1% | 4.8%–17.4% |
| crew reported-case AR | 0.8%–6.0% | 0.0%–4.5% |
| passenger ever-ill AR | 6.3%–22.5% | 5.7%–21.2% |
| crew ever-ill AR | 1.5%–8.2% | 0.0%–6.0% |
| passenger infection AR | 11.4%–37.0% | 11.4%–34.2% |
| crew infection AR | 6.7%–17.2% | 7.5%–13.4% |

Secondary witnesses (medians):

| metric | discrete | continuous | paired median diff | sign p |
|---|---|---|---|---|
| overall attack_rate | 18.0% | 18.3% | -0.3% | 1.000 |
| peak prevalence | 76.0 | 79.0 | 0.0 | 1.000 |
| common_source_events | 22.0 | 23.5 | 1.0 | 0.508 |
| common_source_takers | 248.0 | 254.5 | 0.0 | 1.000 |

## Notes

- This is a screen, not anchor fitting: the frozen rule is an uncertainty-qualified association; overlapping ranges or few posted cells make a stratum uninformative.
- Quiet controls are station_lots seeds with zero contaminated provisioned lots in the census; they test whether the solver arm alone manufactures posting.
