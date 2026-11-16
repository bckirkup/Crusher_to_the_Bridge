# FOOD-SUPPLY-01-REDEPOSIT-WORST
**Date:** 2026-11-16
**Commit:** #1253
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 7a3d3d7828dd34f96c58b10a75fe040b19ffde5a

Paired hand-redeposit contrast on the four highest-burden mega supply seeds. Design is frozen in `campaigns/noro/supply_worst_cases_redeposit_01/DESIGN.md`; submission/job IDs are in `campaigns/noro/supply_worst_cases_redeposit_01/LEDGER.md`. AWS Batch image `picard-campaign:noro-supply-redeposit01` digest `sha256:ae8f91c9d95b3dec6c23da17faef94e024741caf7a86b39d2e47fdc3a5b90673` (`ENGINE_GIT_SHA=7a3d3d78`). S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_redeposit_01/`.

Run contract: eight full-fidelity p06 mega cells, four seeds × `transmission.hand_redeposit_mode` `shedders_only` vs `carriers`, `epochs=288`, `payload_profile="lean"`, `PYTHONHASHSEED=1`. Held fixed: p06 route scale ×2.0, `q_source=0.0047`, passenger/crew prevalence 0.025/0.03, illness draw `point`, `syndromic_comp65`, dose adjustment 7.57, `station_zone_pin=['MainDining_L']`, `intra_epoch_causal_order=legacy`, `intra_epoch_substeps=1`, and `hand_reservoir_mode=hygiene_cycle`. This was designed to isolate the redeposit gate only; it does not test `ordered`, `carriers_ordered`, or `M>1` substeps.

Integrity: all eight Batch jobs SUCCEEDED and wrote the unchanged zip contract (`summary.json`, `growth_census.json.gz`, `rss_samples.json`). `parameters.engine_git_sha` is `7a3d3d78` in all eight cells. `mechanisms.provisioned_source` resolved the intended supply arm and the pinned `MainDining_L` venue in every cell. Receipt-arm provisioned event dose (titre × serving mass × servings) matched the frozen ranking burden exactly for seeds 1030001 and 1031386. Station-lot objects kept the same `lot_servings`/`lot_titre_gec_per_g` across arms, but per-pan `serving_mass_g` draws differed for some pans, so station-lot event-row dose and `common_source_telemetry.dose_credited` are supply-object-paired rather than bit-identical. The lean summary does not echo `hand_redeposit_mode`; the mode is pinned by the manifest tier `config_overrides` and was engine-readback proven on the local smoke (`shedders_only` vs `carriers`, legacy/1/hygiene_cycle), but the artifact does carry post-run witnesses (`meta.row_stream_counts`, `hand_occupancy`) showing the carrier gate/deposit path fired while the non-shedder stool/hygiene stream collapsed (Carrier witness extraction); the arm is therefore not stream-neutral. Treat the carriers contrast as paired-seed directional evidence for the bundled arm, not a stream-neutral redeposit effect size.

`posted` below means `vsp_trigger_epoch is not None` (either-channel reported-case counter crossed the 3% VSP rule). `outbreak_occurred` is the incidence-acceleration takeoff/fizzle label, not the posting flag. Epochs are the summary's 0-based history indices; days use 24 epochs/day. Paired deltas are `carriers − shedders_only` on the same seed.

## Selection

| rank | supply arm | seed | burden_est (GEC) | burden kind | lots | venues |
|---:|---|---:|---:|---|---:|---|
| 1 | `single_line_receipt` | 1030001 | 580,203,309.568 | exact receipt mass | 1 | MainDining_L |
| 2 | `declared_receipts` | 1031386 | 520,046,935.806 | exact receipt mass | 1 | MainDining_L |
| 3 | `station_lots` | 1036232 | 455,349,796.777 | estimated station servings, 150 g | 2 | MainDining_L |
| 4 | `station_lots` | 1020931 | 444,673,387.088 | estimated station servings, 150 g | 3 | MainDining_L |

## Outcomes

| seed | supply arm | mode | posted | VSP epoch/day | detect epoch | confirm epoch | peak epoch/prev | pax infection AR | pax reported AR | crew infection AR | crew reported AR | overall AR | final status |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1030001 | single_line_receipt | carriers | N | — | 55 | — | 232/478 | 7.12% | 2.86% | 10.76% | 2.14% | 8.21% | SUSPECTED |
| 1030001 | single_line_receipt | shedders_only | Y | 158/7 | 60 | 158 | 287/901 | 14.45% | 4.55% | 14.71% | 3.19% | 14.53% | CONFIRMED |
| 1031386 | declared_receipts | carriers | N | — | 224 | — | 258/476 | 7.29% | 1.96% | 10.38% | 2.05% | 8.21% | SUSPECTED |
| 1031386 | declared_receipts | shedders_only | Y | 150/7 | 56 | 150 | 287/892 | 13.67% | 4.31% | 15.33% | 3.81% | 14.17% | CONFIRMED |
| 1036232 | station_lots | carriers | N | — | 77 | — | 251/480 | 7.10% | 2.90% | 10.14% | 1.52% | 8.01% | SUSPECTED |
| 1036232 | station_lots | shedders_only | Y | 118/5 | 74 | 118 | 282/937 | 14.55% | 5.12% | 15.14% | 3.29% | 14.73% | LOCKDOWN |
| 1020931 | station_lots | carriers | Y | 60/3 | 42 | 60 | 267/804 | 10.94% | 4.73% | 17.95% | 4.86% | 13.04% | CONFIRMED |
| 1020931 | station_lots | shedders_only | Y | 59/3 | 42 | 58 | 210/832 | 13.69% | 5.47% | 12.14% | 3.24% | 13.23% | LOCKDOWN |

## Paired contrasts (`carriers − shedders_only`)

| seed | supply arm | Δposted | ΔVSP epoch | Δpax infection AR | Δpax reported AR | Δcrew infection AR | Δcrew reported AR | Δoverall AR | Δcensus acquired | ΔCS dose credited (GEC) | Δhand positive share |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1030001 | single_line_receipt | -1 | lost post | -7.33 pp | -1.69 pp | -3.95 pp | -1.05 pp | -6.32 pp | -442 | -6.64e6 | -0.0284 |
| 1031386 | declared_receipts | -1 | lost post | -6.38 pp | -2.35 pp | -4.95 pp | -1.76 pp | -5.96 pp | -417 | -1.03e6 | -0.0148 |
| 1036232 | station_lots | -1 | lost post | -7.45 pp | -2.22 pp | -5.00 pp | -1.77 pp | -6.72 pp | -470 | -9.03e6 | -0.0254 |
| 1020931 | station_lots | 0 | +1 | -2.75 pp | -0.74 pp | +5.81 pp | +1.62 pp | -0.19 pp | -13 | +2.76e6 | -0.0338 |

`census.n_imports` was unchanged on every pair (144/141/140/150). `census.n_acquired` fell on every pair. On the three seeds that lost posting, `infections_by_dominant_route` fomite counts fell sharply (1030001: 677→231, 1031386: 612→252, 1036232: 652→198) while `common_source_food` dominant infections stayed within about 6 of the paired value (147→141, 151→129, 170→177). Passenger reported-case channel counts show the same split: supply-chain reports stayed roughly paired while aboard reports fell (e.g. seed 1036232 passenger `supply_chain` 125→124 vs `aboard` 123→15; seed 1020931 passenger `supply_chain` 211→199 vs `aboard` 56→32, crew `aboard` 67→101).

## Carrier witness extraction

`meta.row_stream_counts` and `hand_occupancy` were re-read from the eight `growth_census.json.gz` artifacts after the readout. Counts are record counts, not mass.

| seed | supply arm | mode | deposit | pickup | dose | hazard | stool | gate |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1030001 | `single_line_receipt` | `carriers` | 298,050 | 1,024,748 | 1,221,231 | 972,585 | 6,127 | 2,675,431 |
| 1030001 | `single_line_receipt` | `shedders_only` | 146,708 | 872,078 | 1,087,885 | 867,575 | 67,577 | 499,538 |
| 1031386 | `declared_receipts` | `carriers` | 290,964 | 1,010,545 | 1,209,696 | 962,927 | 5,152 | 2,708,542 |
| 1031386 | `declared_receipts` | `shedders_only` | 143,972 | 839,944 | 1,050,017 | 847,818 | 66,882 | 511,697 |
| 1036232 | `station_lots` | `carriers` | 290,222 | 1,008,439 | 1,200,298 | 962,938 | 5,868 | 2,688,039 |
| 1036232 | `station_lots` | `shedders_only` | 149,248 | 808,903 | 1,013,049 | 815,900 | 67,411 | 542,391 |
| 1020931 | `station_lots` | `carriers` | 470,229 | 1,064,161 | 1,282,313 | 987,158 | 9,766 | 2,366,147 |
| 1020931 | `station_lots` | `shedders_only` | 172,850 | 534,353 | 674,191 | 555,886 | 68,461 | 708,388 |

The carrier gate/deposit path was exercised: deposit records rose ~1.9–2.7×, pickup/dose/hazard records rose, and `pickup_gate` evaluations rose ~3.3–5.4×. The same arm collapsed the stool/hygiene stream: `stool` records fell to ~8–14% of `shedders_only`, and `hand_occupancy` counters show `continuous_path_calls` ~1.44–1.50M vs 0/29, `stool_calls` ~95,924–167,809 vs ~1,583,848–1,601,230, and `propensity_draws` ~555–897 vs ~6,620–6,868. `total_quarantine_person_epochs` fell on every pair (77,560→47,206; 84,943→27,975; 194,197→44,175; 815,847→131,567), so the pattern is not faster quarantine/medical response.

## Measured / inferred / hypothesis

Measured:

- `shedders_only` posted all four seeds; `carriers` posted only seed 1020931. Passenger reported-case AR fell on all four pairs by 0.74–2.35 pp, passenger infection AR by 2.75–7.45 pp, and overall AR by 0.19–6.72 pp.
- The three non-posting `carriers` cells ended `SUSPECTED` with `vsp_trigger_epoch=null`; the receipt-arm cells still had `outbreak_occurred=true`, while station_lots seed 1036232 had `outbreak_occurred=false`. None of these are posting flags.
- On the one remaining post (seed 1020931), `carriers` had VSP epoch 60 vs 59, confirmation epoch 60 vs 58, peak epoch 267 vs 210, passenger reported AR 4.73% vs 5.47%, crew infection AR 17.95% vs 12.14%, and overall AR 13.04% vs 13.23%.
- The high `shedders_only` ARs are the expected tail of the selection rule: these are the top-burden contaminated mega seeds, and the two station_lots seeds carry 2–3 lots. Their passenger reported ARs (4.31–5.47%) edge above the earlier single mega receipt example (4.55% for seed 1030001) and above the earlier unselected mega posted-row median (~2.47%, max ~4.94%) that was measured from the SENSITIVITY-01 scan; the real pre-2020 VSP mega posted median remains ~6.00%.
- Post-readout witness extraction from `meta.row_stream_counts` and `hand_occupancy` shows the carrier redeposit path fired (deposit records ~1.9–2.7× `shedders_only`; pickup/dose/hazard records up; `pickup_gate` evaluations ~3.3–5.4×) while stool-event records fell to ~8–14% and hand `stool_calls` fell from ~1.58–1.60M to ~96k–168k. `total_quarantine_person_epochs` also fell on all four pairs (77,560→47,206; 84,943→27,975; 194,197→44,175; 815,847→131,567), so the pattern is not faster quarantine/medical response.

Inferred:

- The `carriers` arm increased deposit/pickup/dose/hazard record counts but reduced acquisitions and AR; because the same arm also collapsed the non-shedder stool/hygiene/self-contact stream and is not stream-neutral, the reduction cannot be assigned to redeposit sign alone. It is a bundled carrier-carriage/redeposit arm, not a clean amplification test. Direct-contact partner sampling still iterates sampled shedders, so carriers did not add hand-to-hand donors even where they redeposited to surfaces/food.
- This is not the same arm as the earlier expedition posted witness: that ledger used `carriers_ordered`/`ordered` arms and non-supply-enriched posted rows. Here `intra_epoch_causal_order=legacy` and `intra_epoch_substeps=1`, so ordering and substep effects are excluded.

Hypothesis/next:

- Four paired seeds are directional, not an effect size, and `station_lot` credited dose is not bit-identical across arms. The discriminating next measurement is a stream-preserving carriers witness: keep non-shedding carriers on the same replenish RNG/event stream as `shedders_only` (or run the null contrast) and add per-run carrier deposit/taker counters; otherwise treat `carriers` as scaffolding and compare distributions at ≥20 seeds before reading the sign. No anchor fitting or default flip follows from this panel.
