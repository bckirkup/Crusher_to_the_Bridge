# DP-THETA-FIT-01
**Date:** 2026-11-23
**Commit:** 9c40ff3b
**Pathogens:** sars_cov2_resp
**Status:** measured

## Endpoint audit

Repository inspection at the commit above establishes the following endpoint
definitions before any fit design is frozen.

| Record | Quantity | Observation window | Repository evidence |
| --- | --- | --- | --- |
| DP-THETA-PILOT-01 | Secondary infections, excluding the seeded index | First 120 hourly epochs | `docs/ledger/DP-THETA-PILOT-01.md` and `docs/covid/covid_dp_theta_pilot_01_design.md` |
| covid.T3 | Campaign PCR positives, target 634 from 3,063 reported tests | Through day index 31, February 20, 2020 | `data/observation/covid_fit_targets.json`, anchor `covid.T3` |
| Onboard testing at the replay cutoff | 691 positive results from 3,894 RT-PCR tests | Through February 23, including the late crew testing wave | Yamahata & Shibata, Table 1, cited by `data/observation/covid_testing_campaigns.json` |
| Final confirmed count | 712 people who tested positive among 3,711 passengers and crew | Final outbreak total, with no February 23 cutoff assigned to this total in the anchor record | `data/observation/covid_fit_targets.json`, anchors `covid.T4` and `covid.H5` |

The `diamond_princess_2020` scenario in `data/scenarios/covid_hull_scenarios.json`
runs for 35 days from January 20. It declares molecular ascertainment
beginning on February 3. The 120-hour pilot ends before this channel opens.

The cell payload exposes `lab_confirmed_total` separately from
`observables` and `infections_total` in
`picard_framework/covid_boarding_screen.py::cell_payload`.
The declared `covid.T3` channel is `campaign_confirmed`. The payload's
`observables.campaign_positives` counts every positive row in the
campaign specimen log. `observables_from_modality` applies no February 20
cutoff, so a replay with positive specimens in the February 23 wave
includes them in that aggregate. T3 is already a scored anchor. The
final confirmed count also contributes to the serology-informed `covid.H5`
infection estimate, which the repository explicitly holds out forever.

## Interpretation

The February 23 testing table counts positive results and excludes people
transported by emergency disembarkation (footnote c). The final outbreak
report counts people who tested positive. The records establish a
difference in case coverage. They do not explain the entire difference
between 691 and 712. [Yamahata & Shibata, Table 1](https://publichealth.jmir.org/2020/2/e18821/)
and [CDC MMWR, Diamond Princess section](https://www.cdc.gov/mmwr/volumes/69/wr/mm6912e3.htm).

Treating 712 as an onboard February 23 count would change both the
observation window assigned to that number and the population covered.
The pilot supplies no matched-seed evidence about whether the proposed
bracket covers a comparable confirmed-case outcome or whether either
edge is dead or saturated at that endpoint.

## Declaration (2026-11-23)

Benjamin's decision on the endpoint: "Go with A" — the scored endpoint is
the extended horizon through 20 February against `covid.T3`; the onboard
table's 691 of 3,894 through 23 February is the secondary cross-check.

The fit design is frozen in `docs/covid/covid_dp_theta_fit_01_design.md`
(design file `picard_framework/runs/covid_dp_theta_fit_01_design.json`,
campaign `campaigns/covid/dp_theta_fit_01/`): `replay_niid` only, 24
matched seeds 20200205–20200228, full declared voyage, θ {1e7, 3.16e7,
1e8, 3.16e8, 1e9, 3.16e9, 1e10}, 168 cells. The scored quantity is the
count of positive campaign specimens taken on or before day index 31 on
the shipped observation process (crew wave not armed). θ is selected on
the median over the 24 seeds; the side-of-target, dead, saturated,
bracket, selection and representativeness rules are in the design doc.

## Pre-freeze smoke (measured, not scored)

**Measured at:** da6365ba

Two cells, pilot worker with no horizon cap (full voyage), `replay_niid`,
θ=1e10, seeds 20200205 and 20200212:

| Seed | Infected of 3,711 | Before quarantine | Campaign specimens | Campaign positives | `lab_confirmed_total` |
| --- | --- | --- | --- | --- | --- |
| 20200205 | 3,414 | 2,913 | 2,608 | 745 | 3,331 |
| 20200212 | 3,333 | 2,600 | 2,829 | 821 | 3,235 |

Quarantine activated at epoch 391 on both. Measured: the engine runs the
testing campaign inside the extended window and returns positives.
Hypothesis (two seeds): the pilot's lowest θ infects about nine in ten
aboard on the full voyage, so the whole pilot grid sits above the T3
bracket. Neither seed reached the frozen 0.95 saturation threshold, and
that rule is a 24-seed median, so the upper edge is unclassified. Measured on the
same two cells: at attack about 0.9 the campaign returns only 1.2–1.3 ×
the T3 count, so the scored quantity compresses near saturation.

## Local smoke through the registered path (measured, one seed)

**Measured at:** 6e23f0d9

`scripts/campaign run covid/dp_theta_fit_01 --block niid_t1e9_canary
--index 0` (θ=1e9, seed 20200205, full voyage): 3,063 specimens and 777
positives through day 31, last specimen day 31, no wave-tagged specimen,
2,881 secondaries, quarantine activated at epoch 391, resolved platform
`diamond_princess`, susceptibility scale 3.2322e11 = θ·(α+β)/α. Every
audit invariant held. The dry run counts 168 cells over eight blocks.

## Canary (measured, 20 matched seeds at one cell)

**Measured at:** 6e23f0d9 (image
`picard-campaign@sha256:8891880d99c2b2d533d62af077602873141f201be55bd4a762514b34acf4b954`,
job definition `picard-covid-dp-theta-fit-01:1`, Batch array
`653e82d7-351e-48c5-8362-dae004d96601`, 20 of 20 succeeded)

Block `niid_t1e9_canary`: θ=1e9, seeds 20200205–20200224. Readout
`docs/covid/dp_theta_fit_01_canary_readout.json`.

| Quantity | Value |
| --- | --- |
| Scored positives through day 31, in ascending order (per-seed values are in the readout) | 0, 0, 0, 0, 0, 70, 87, 136, 229, 255, 307, 365, 373, 401, 402, 450, 463, 572, 777, 802 |
| Median scored positives (target 634) | 281 |
| Seeds below / above 634 | 18 / 2 |
| Seeds with zero secondaries | 5 |
| Median secondaries; median attack rate | 951; 0.256 |
| Median infections before / during / after quarantine | 11 / 870 / 54 |
| Median specimens through day 31 | 3,063 |
| Median `lab_confirmed_total` | 645 |
| Audit deviations | none on any seed |

Measured: the Batch cell for seed 20200205 reproduces the local smoke
exactly (2,881 secondaries, 777 positives). Measured: 18 seeds are below
634, which already meets the frozen "below" rule for the full 24, so
θ=1e9 is on the low side of T3 whatever the four remaining seeds return.
Measured: the cell is neither dead nor saturated.

Not established: that the grid covers T3. The bracket rule needs
adjacent 24-seed medians, and no cell above 1e9 has been run on the fit
worker. Hypothesis: the bracket lies in (1e9, 3.16e9) or (3.16e9, 1e10);
its only support above 1e9 is two pre-freeze seeds at 1e10 (745 and 821
positives). Hypothesis: the four cells below 1e9 sit further below the
target and serve as the dead-edge reference only.

Hypothesis (20 seeds, one θ): the outcome is strongly seed-dependent at
fixed θ — a quarter of seeds go extinct and the rest spread from 70 to
802 — so the selected θ's median may not describe a typical voyage; the
frozen representativeness flag reports this.

## Fit array (measured, 72 of the 168 declared cells)

**Measured at:** 6e23f0d9 (same pinned image as the canary; job
definitions `picard-covid-dp-theta-fit-01:2`–`:4`; Batch arrays
`d6d64ab8-1665-4f44-a384-4f26afbb101f` (θ=1e9, 4 seeds),
`68cf99ae-0553-41fa-9b70-85b30f1a3b13` (θ=3.16e9, 24 seeds),
`4c2e5d23-8b90-4f2e-bf6c-43687c01e4fc` (θ=1e10, 24 seeds); 52 of 52
succeeded)

Benjamin's decision after the canary: run only the remaining four seeds
at 1e9 plus 3.16e9 and 1e10, and skip the four θ below 1e9. Seeds are
20200205–20200228 at every run θ. Readout
`docs/covid/dp_theta_fit_01_array_readout.json`; no audit deviation on
any of the 72 cells.

| θ | Median scored positives (target 634) | Seeds above / below 634 | Side | Seeds in [317, 1268] | Extinct seeds | Median secondaries | Median attack rate | Median `lab_confirmed_total` | Median infections before / during / after quarantine |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1e9 | 281 | 3 / 21 | below | 11 | 7 | 951 | 0.256 | 645 | 11 / 870 / 54 |
| 3.16e9 | 600 | 11 / 13 | compatible | 19 | 3 | 1,758.5 | 0.474 | 1,282.5 | 136 / 1,197.5 / 98.5 |
| 1e10 | 735.5 | 14 / 10 | compatible | 19 | 3 | 2,956 | 0.797 | 2,546 | 865.5 / 967 / 22 |

No run cell is dead or saturated. Medians are monotone in θ.

### Frozen rules applied to the three run θ

The committed readout carries `selection: null`, because the readout
emits a selection only when all seven declared θ are complete. The
values below come from calling the same `_selection` function on the
three complete rows; no rule was changed.

- Bracket: (3.16e9, 1e10), medians 600 < 634 ≤ 735.5.
- Interpolated θ* (log10-θ between the bracket medians): 4.22e9.
- Selected grid θ (compatible, closest median to 634): 3.16e9.
- Representativeness flag: not raised (19 of 24 seeds in band).

Measured: the seeds 20200205 and 20200212 at 1e10 return 745 and 821
scored positives, the same counts as the pre-freeze smoke.

### Interpretation

Measured: T3 excludes θ=1e9 and passes both 3.16e9 and 1e10. The top
grid value is compatible, so the grid does not bound θ from above.

Measured: the scored count discriminates weakly above the bracket. From
3.16e9 to 1e10 the median attack rate rises from 0.47 to 0.80 and median
secondaries from 1,758.5 to 2,956, while median scored positives rise
only from 600 to 735.5 on a fixed 3,063 specimens.

Inferred: T3 by itself supports θ ≥ about 3e9 on `replay_niid` and does
not separate a half-ship epidemic from a four-fifths-ship one. The
selected 3.16e9 and interpolated 4.22e9 are the frozen rule's output, not
a tight estimate.

Measured, reported only and not selected on: at the selected 3.16e9 the
median all-channel `lab_confirmed_total` is 1,282.5 against the final
CDC count of 712, and median infections are 1,758.5 of 3,711.

Inferred: the four unrun θ below 1e9 would not change the bracket if the
medians stay monotone, which holds on the three run θ. The dead edge of
the grid is unmeasured.

Hypothesis: three seeds (20200210, 20200217, 20200226) are extinct at
all three θ, so early extinction on those seeds is set by the index
host's draw rather than by θ.

## Execution status

Fit read out on three of seven declared θ. The next decision is
Benjamin's: accept θ≈3.16e9–4.22e9 as the T3 fit with the weak upper
bound stated above, or add a second scored observable that separates
attack rates (for example the all-channel confirmed count or a serology
band) before a θ is carried forward.
