# DP-THETA-FIT-01
**Date:** 2026-11-23
**Commit:** 9c40ff3b
**Pathogens:** sars_cov2_resp
**Status:** open

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

## Execution status

The endpoint audit is complete. The fit design remains unfrozen. Zero
fit cells ran, so this entry records no selected theta or canary readout.
