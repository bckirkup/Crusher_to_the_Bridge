# CONTAM-FLEET-WORKUP: 77-hull readout

Whole-hull airflow comparison of the native prescribed-flow engine and NIST
ContamX 3.4.0.3 on every hull with a committed CONTAM bundle. Numerical
engineering comparison only: it validates no ship, and carries no room-level,
source, organism, dose or voyage quantity. Hulls are never ranked.

Everything below is measured, from the offline package
`contam_fleet_workup_77_package_01.tar.gz`
(SHA-256 `77366e25c6b4c388516dc0c2650b6baf207ae1b9585f820c272d1226028c5964`).
Its `verify.py` passes 48 of 48 checks on a clean unpack with no network.
Sources: the corrected four-hull canary (run 2, #1335) plus 73 hulls measured
here in eight Batch jobs. Design `fb6a0bd5`, hull inputs `d5d50d3a`, fleet
runner `56b1a990f64edae1f95eb32588d0017a34db6d0f`.

## Coverage

| | planned | observed |
|---|---|---|
| hulls | 77 (82 platforms, 5 without a bundle) | 77 |
| matrix rows | 2,156 | 2,156, each exactly once |
| executed rows | 1,591 | 1,591 ok |
| timed cold cells (1 warm-up + 5 measured) | 9,546 | 9,546, no timeout |
| of which ContamX solves | 6,810 | 6,810 |
| cached repeats | 7,955 | 7,955 |
| in-job gate checks | — | 20,649, 0 failed |

Not executed, by design: 525 `structural_nonresponse` rows (the native engine
has no weather input; 75 hulls × 7 weather settings) and 40 `not_applicable`
rows (3 once-through hulls have no recirculated share to vary; 2 sealed hulls
have no relative wind). Excluded platforms, no bundle: `expedition_cruise_300`,
`fletcher_class_destroyer`, `legend_class_nsc`, `messy_cruise_500`,
`san_antonio_class_lpd`.

Of the 1,591 executed rows, both blocks moved from the lane baseline (or are
the baseline) in 1,442; in 148 the solved block did not move while the
downstream block did (the ContamX outdoor-air and recirculation rows, which
change only the mixing inputs); in 1 the downstream block did not move.

## Native against harmonized ContamX, baseline, 77 hulls

Ratio ContamX / native, across hulls (min, median, max):

| block | metric | hulls | min | median | max |
|---|---|---|---|---|---|
| solved | supply total | 77 | 1 | 1.00781 | 1.01187 |
| solved | return total | 77 | 1 | 1.00781 | 1.01187 |
| solved | gross interzone flow | 77 | 0.0123 | 2.554 | 4.509 |
| solved | ambient inward total | 72 | 1.00224 | 1.01432 | 1.20021 |
| solved | ambient outward total | 74 | 0.999396 | 1 | 1.2917 |
| downstream | effective outdoor-air fraction | 77 | 1 | 1 | 1 |
| downstream | whole-hull air change | 77 | 0.999816 | 1.00084 | 1.00805 |
| downstream | clean-air equivalent, with filter | 77 | 0.999889 | 1.00098 | 1.00805 |
| downstream | uniform-tracer material time | 77 | 0.5316 | 0.9956 | 1.5165 |

- With outdoor-air inputs matched, terminal totals and whole-hull air change
  agree within about 1.2 %; the effective outdoor-air fraction is identical.
- The engines differ in what they solve between zones: ContamX gross
  interzone flow is 0.012 to 4.5 times the native value, and material time
  0.53 to 1.52 times.
- Hull balance residual, absolute: native 125 to 57,327 m³/h (median 4,107);
  ContamX 7e-6 to 1.59 m³/h (median 0.0025). The native lane prescribes flows
  and does not close a mass balance; ContamX solves one.
- Uniform-tracer closure error ≤ 7.6e-15 in both lanes.
- ContamX does not resolve outdoor-air or exhaust totals on simple air-handler
  paths: 2,270 result cells are blank with status `unimplemented`, never zero.
  Pressure summaries exist only for ContamX (the native lane has none).

## As-shipped baselines (reference only)

Both untouched lanes, the committed export and the authored `platform.prj`,
gave identical aggregates to each other on all 77 hulls. Against the
harmonized baseline their solved airflow is the same; their outdoor-air
inputs differ on 68 hulls: effective outdoor-air fraction lower by up to 0.8
(median 0.42), whole-hull air change lower by up to 2.70 1/h (median 1.04),
material time longer by up to 0.88 h (median 0.15). On 9 hulls there is no
difference.

## Sensitivity

Operational, both lanes: supply duty ×0.5 and ×1.5 and supply air change ×1.5
ran on all 77 hulls; outdoor-air fraction ×0.5 and recirculated fraction ×0.5
on 74. The two engines' responses (each minus its own baseline) agree to
within 9.2e-9 in effective outdoor-air fraction and 0.018 1/h in air change.

Weather, ContamX only (one-sided): wind speed 0, 5, 10 m/s and heading 90°,
180°, alone and combined, on 75 hulls. Every one of the 525 rows moved the
solved field; one heading-180° row left the downstream block unchanged.
Per-hull responses are in the package (`per_hull_readout.md`, `contrasts.csv`).

## Run times

One cell at a time, one thread, fresh interpreter per cold cell. A cohort is
one job on one host; cohorts are not pooled. Range of per-row medians of the
5 measured repeats, wall ms (min / median / max over the cohort's rows):

| cohort | host CPU | native end-to-end | ContamX end-to-end | ContamX solve only | ContamX import |
|---|---|---|---|---|---|
| canary_run2 | AMD EPYC 9R14 | 0.95 / 15.8 / 486 | 15.5 / 71.4 / 800 | 2.72 / 6.14 / 62.3 | 10.5 / 45.2 / 419 |
| fleet_cohort0 | Xeon 8488C | 2.88 / 8.74 / 44.4 | 28.3 / 58.5 / 147 | 3.10 / 4.75 / 9.97 | 21.6 / 38.9 / 108 |
| fleet_cohort1 | AMD EPYC 9R14 | 2.27 / 13.1 / 140 | 26.6 / 68.4 / 413 | 3.39 / 6.84 / 51.2 | 19.9 / 48.7 / 220 |
| fleet_cohort2 | AMD EPYC 9R14 | 4.47 / 16.0 / 71.6 | 42.0 / 89.2 / 238 | 4.38 / 7.15 / 16.9 | 32.2 / 59.9 / 163 |
| fleet_cohort3 | AMD EPYC 9R14 | 10.2 / 23.6 / 145 | 66.0 / 103 / 397 | 5.95 / 8.79 / 78.5 | 39.9 / 66.5 / 218 |
| fleet_cohort4 | Xeon 8488C | 7.57 / 70.0 / 211 | 52.6 / 208 / 596 | 4.50 / 12.8 / 66.7 | 37.2 / 138 / 312 |
| fleet_cohort5 | Xeon 8488C | 1.27 / 13.7 / 70.3 | 16.5 / 59.8 / 215 | 2.35 / 5.61 / 21.0 | 11.7 / 42.6 / 139 |
| fleet_cohort6 | Xeon 8488C | 2.22 / 17.1 / 59.9 | 24.3 / 80.4 / 185 | 2.80 / 5.70 / 14.6 | 17.8 / 40.3 / 131 |
| fleet_cohort7 | AMD EPYC 9R14 | 8.62 / 48.8 / 165 | 60.1 / 158 / 413 | 5.62 / 12.4 / 32.5 | 46.4 / 105 / 269 |

- The ContamX subprocess itself is a small part of the ContamX lane; most of
  the lane's time is the Python decode of its result files (`contamx_import`).
- Whole-process time is dominated by interpreter start-up and imports: about
  0.83 to 1.6 s per cold cell in either lane.
- Cached downstream repeats (engine already built) are in the package and are
  not comparable with cold cells.
- The 1-minute load average during timing was at most 1.4 on every host.

## Provenance

| cohort | hulls | Batch job | job definition | host | attempts | wall min | gates (failed) | raw artifact SHA-256 |
|---|---|---|---|---|---|---|---|---|
| canary_run2 | 4 | `ac1b56e1-2080-40cc-be8f-b8473ceca793` | canary-01:3 | c7a.8xlarge | 1 | 10.1 | 993 (0) | `b99690680cd30331d4af0ad9e3afba5543d4499668e19c42205cf272f5a7ac8b` |
| fleet_cohort0 | 10 | `1e44ab45-ad2e-4bcf-87ca-687ff782095b` | fleet-01:2 | c7i.8xlarge | 1 | 22.0 | 2,730 (0) | `2cbde92ea0126a980c0699b4c9724c149cafe83be8c92662a9c86aec6cce2f9d` |
| fleet_cohort1 | 9 | `bf3f4891-f2db-471b-86a2-4e3b32073b5f` | fleet-01:3 | c7a.4xlarge | 1 | 20.2 | 2,358 (0) | `493997f7b7b4d290ccb3b0eeb3e366c4f796d68925019a33be371f7a8e4433cd` |
| fleet_cohort2 | 9 | `79be935e-98c5-4ab0-9a5e-cfbdfa7fd191` | fleet-01:4 | c7a.4xlarge | 1 | 20.4 | 2,457 (0) | `38e9f1c6fdb241eca6d0ae8a244f498b2358304ff6d5be94a2eea0297bf35106` |
| fleet_cohort3 | 9 | `a9941ac8-47ad-46a7-a2a4-80c3e1191a81` | fleet-01:5 | c7a.4xlarge | 1 | 21.1 | 2,399 (0) | `7a6e1edf84d67c3da0910ae11e25912ab11a370c4f90d2cff702ab91b767bae8` |
| fleet_cohort4 | 9 | `9a1564dc-06b0-44b1-81d1-ae914cd3ced0` | fleet-01:6 | c7i.8xlarge | 2 | 24.8 | 2,399 (0) | `86c863ab8f01b663b2a417cc75869a35ce94be6443cfe8c147a1639740f19821` |
| fleet_cohort5 | 9 | `1372b774-5110-4bf1-b13d-d51cca8eaf3c` | fleet-01:7 | c7i.8xlarge | 1 | 21.2 | 2,457 (0) | `ab0800a83fe798cf42a7f2e21ee15bdb16740ac93be28fba87a1df3f86658ecd` |
| fleet_cohort6 | 9 | `3bebb032-a5eb-44ef-aff1-843800bccff1` | fleet-01:8 | c7i.8xlarge | 1 | 20.2 | 2,399 (0) | `462e0212d19efac5d981c5d5a3dfa77df3d99eaa61556c734325c6817a0b56f7` |
| fleet_cohort7 | 9 | `99b9d3f6-2e9f-470e-89d7-a015a4047674` | fleet-01:9 | c7a.4xlarge | 2 | 22.3 | 2,457 (0) | `3659a9ae07a3b0396a4ab5be72f2341c6d63f032620c18b776fa6b27e36696f5` |

Fleet image
`picard-campaign@sha256:0a25129f30ec04c66c7c83d5e446c73889a81c188e4985d475aaf36791ae4f79`;
canary image `sha256:e59acd8d426a1304387929dd9c91bb85946b28c0c2357eb7a997e7e16a28e0c3`.
ContamX binary SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b` in every
cohort. Every job hashed all 392 pinned input files before and after: unchanged.
Cohorts 4 and 7 each lost a Spot host before finishing; the retry started from
nothing on a new host and all their records come from the second attempt.

## Limits

- Hull definitions are authored model inputs, not measurements of ships.
- Agreement in the downstream block follows from the solved field plus matched
  outdoor-air inputs; it is not an independent ContamX result.
- Run times hold for these hosts, this image and single-threaded cells. Two
  CPU models were drawn, so cross-cohort timing differences mix hull and host.
- The fleet jobs ran one at a time, but on shared Batch hosts whose other
  tenants are not controlled; the recorded load average is the evidence of
  contention.
