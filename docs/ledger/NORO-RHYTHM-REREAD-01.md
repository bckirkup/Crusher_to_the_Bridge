# NORO-RHYTHM-REREAD-01
**Date:** 2026-11-22
**Commit:** 519c3e97a6ab380f780f32cf92a9df0a53840aca
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 519c3e97a6ab380f780f32cf92a9df0a53840aca

**D3′ verdict.** On the eight-day mega reconstruction, the four seeds that reached take-off with rhythm both off and on averaged **148.0 versus 113.5 onboard acquisitions**, respectively. All four differences favored rhythm on. The mean reduction was 34.5 acquisitions per voyage (23.3%). The older 12-day campaign had only 19 pairs with any onboard acquisition in both arms and showed little conditional difference. A confirmatory paired A/B is warranted for the reconstruction. These archives cannot establish that encounter density explains its result.

## Measured — eight-day reconstruction

From `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_explorer_reconstruction_01/`, read the `meg_declared_five_rhythm_off/` and `meg_declared_five/` run zips. Each had all 100 seeds 8105–8204 on engine `bf0ec16825ed15176fe0362459a72a7be1667f41`. Within every pair, the initially infected IDs matched, the exposure cap was active, and the rhythm layer attached only in the on arm.

**Take-off** uses the reconstruction's prespecified evaluability criterion: at least 20 passenger and 5 crew onsets over eight days after excluding the five declared seeds. **Ignition** means at least one onboard acquisition. For each voyage, secondaries equal `summary.cumulative_ever_infected` minus the number of `initially_infected_agent_ids`. The independent sum of `summary.infections_by_dominant_route` agreed in all 200 zips. This counts acquisitions through all routes. Shipwide infection attack rate (AR) is final ever-infected divided by 7,000 and includes infections present at embarkation. [Campaign design](../../campaigns/noro/explorer_reconstruction_01/DESIGN.md)

| Gate across 100 matched seeds | Off | On | Both | Off only | On only | Neither |
|---|---:|---:|---:|---:|---:|---:|
| Take-off | 6 | 4 | 4 | 2 | 0 | 94 |
| Ignition | 85 | 77 | 74 | 11 | 3 | 12 |

| Selection on matched seeds | Pairs | Mean secondaries off → on | Mean paired difference (on − off) | Mean infection AR off → on |
|---|---:|---:|---:|---:|
| Take-off in both arms | 4 | 148.00 → 113.50 | −34.50 | 2.429% → 1.936% |
| Take-off in either arm | 6 | 170.83 → 114.17 | −56.67 | 2.752% → 1.943% |
| Ignition in both arms | 74 | 29.82 → 22.53 | −7.30 | 0.724% → 0.619% |

The four jointly qualifying seeds were 8164, 8165, 8175 and 8197. Their paired differences were −60, −14, −40 and −24 acquisitions. With four pairs, all four signs agreeing gives a two-sided sign-test p of 0.125. The two off-only qualifiers (8125, 8191) explain why widening the selection changes the estimate. Across the 74 jointly ignited pairs the median difference was zero, with a paired-bootstrap 95% interval of −12.64 to −3.20 for the **mean**. Take-off occurred in 6/74 off and 4/74 on. Over all 100 pairs, the take-off difference was −2 percentage points (off 95% Wilson interval 2.8–12.5%, on 1.6–9.8%). The earlier ≤2-case comparison used mean cumulative **reported** cases by day over all seeds.

## Measured — 12-day rhythm archive

From the same bucket, read `campaign/noro_rhythm_01_v2/{off,on}/fl_mega_12d/`, 200 pairs, seeds 8105–8304. Its archived engine SHA is `3d9d59c64cbe0473603ec26d1452361229268575`. The v1 prefix repeats these seeds. In all 400 v2 zips, `rhythm.json.gz:n_acquired` agreed with the count of distinct people in the acquisition rows and with the route-count sum. All 200 on arms attached the layer and dealt commitments. [Original ledger](NORO-RHYTHM-01.md)

| Gate | Off | On | Both | Off only | On only | Neither | Mean secondaries off → on among both | Mean infection AR off → on among both |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Archived take-off (peak prevalence ≥10) | 194 | 194 | 194 | 0 | 0 | 6 | 0.325 → 0.366 | 0.233% → 0.233% |
| At least one onboard acquisition | 38 | 45 | 19 | 19 | 26 | 136 | 1.79 → 1.58 | 0.246% → 0.243% |

All 194 peak-qualified pairs already met the threshold at epoch zero. The stored `ignited` flag records a positive pool gain on an emesis deposit. Of the 126 off and 127 on voyages flagged, 89 and 87 respectively had zero acquisitions. Conditioning on actual acquisitions gives a mean difference of −0.21 (paired-bootstrap 95% interval −0.79 to +0.21). Both bootstrap intervals above use 20,000 percentile resamples of the selected seed pairs, ordered by seed, with NumPy `default_rng(20261122)` initialized per interval.

**Encounter coverage.** The 12-day zips contain location headcounts for all 288 epochs in both arms. Among the 19 jointly ignited pairs, the mean chance that two people shared a recorded zone rose from 3.77% off to 4.66% on (+0.90 percentage points). For each epoch this is the sum of `n × (n−1)` across zones divided by `N × (N−1)`, excluding the pooled ashore and isolation locations from both counts. The voyage mean weights epochs equally, and the arm mean weights voyages equally. Co-location in a model zone is a proxy for crowding. The eight-day zips contain infection and clinical series but lack the corresponding per-epoch zone headcounts and encounter census.

## Inference and remaining hypothesis

The reconstruction shows a reduction concentrated in the larger simulated outbreaks. Conditioning selects on a post-toggle outcome, so the four-pair estimate describes those seeds. Its magnitude warrants replication before generalizing to other voyages. The two archives use different engines, voyage lengths and take-off criteria. Pooling their seeds would obscure that distinction.

The hypothesis that the rhythm layer changes propagation through dense encounters remains open. Only the older archive measures zone co-location, and its measured crowding shift accompanied little change in secondaries among jointly ignited seeds. The D0 ledger at this checkout is a declared diagnostic design. Neither archive isolates scheduling from the other behavior bundled in `rhythm.enabled`. [D0 ledger](NORO-DOSE-LEDGER-01.md)
