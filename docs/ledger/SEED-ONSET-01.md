# SEED-ONSET-01
**Date:** 2026-09-19
**Commit:** 46e103e
**Pathogens:** sars_cov2_resp
**Status:** open

## Defect

`ExplicitSeed` carried `infection_age_days` but no way to declare the seeded
host's observed onset date, so the seeded host's incubation period was drawn
free from the profile distribution. Whether the Diamond Princess index
"boarded already symptomatic" — a dated fact of the record (cough onset 19
January, boarding 20 January = day 0; Yamagishi 2020, Eurosurveillance
25(23):2000272, grade A) — was decided by a lottery: at the record's
infection age (~5–6 d) the draw passes the geometry gate in only 45% of
seeds, and no threshold fixes it because the gate was mixing "this replicate
drew a short incubation" with "the index boarded symptomatic".

## Fix: `ExplicitSeed.onset_day`

A seed may now declare `onset_day`, the voyage day of the observed symptom
onset (signed — onset before the seed's own epoch is the ordinary case).
The implied incubation is `infection_age_days + onset_day − <seed day>`,
required positive, and is stamped on the infection record rather than drawn.
When onset is still ahead at the seed epoch the host is stamped presymptomatic
(`incubation_days`, `will_present`) and reaches onset at the declared day
through the ordinary progression seam. When onset is already elapsed, the
host is stamped with exactly the symptomatic-arrival record the boarding
channel produces (shared `_stamp_symptomatic_history`), except that the
illness duration is not length-biased — a named index is not a prevalent
sample — and `boarding_state` is left unset rather than masquerading as a
drawn boarder. A declared onset already past the authored shedding window is
a contradictory configuration and raises rather than returning a cleared
host. The Diamond Princess seed declares `onset_day: −1.0` with
`infection_age_days: 6.8`, which only fixes the implied incubation
(6.8 − 1.0 = 5.8 d) at the `sars_cov2_resp` profile's authored incubation
median; the age stays a swept axis.

## What it invalidates

Every `index_geometry_pass_fraction` on the `covid_theta_screen_v7` surface
(THETA-V7-01) is an artifact of the free incubation draw — including 0.45 at
the record's own age — and is void. The empty pre-registered admissible
region is therefore not a statement about Θ: the cells that failed did so on
a gate whose input the model could not express. The fleet-shape observation
at Θ 3.16e7–3.16e9, ages 0–5 d stands on its own numbers; only its geometry
column is superseded. No criterion or threshold in the v7 design was altered.
