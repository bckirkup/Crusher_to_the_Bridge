# NORO-HAND-CASCADE-01-SPATIO-TEMPORAL-TRIAGE
**Date:** 2026-11-14
**Commit:** e46742af
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** e46742af

## Scope

Spatio-temporal-activity triage for the contact-constant audit. Candidate
spaces are `event_space` (`public`, `sanitary`) and `food_service` (`galley`,
`dining`, `crew_mess`); `cabin` is `berthing_excluded` because cabin-mate
mechanisms already govern berthing. This is a screening index, not a fitted
parameter: `activity_mass_gec = delivered_gec + dose_gec` from post-run
`fomite_mass_balance` zone books, and
`screen_score = activity_mass_gec * SURFACE_CONTACTS_PER_HOUR /
HIGH_TOUCH_AREA_M2`.

Diagnostic: `tools/noro_diag/spatial_contact_triage.py`. Cell:
`fl_exp_12d_sens_p06_paxv` (`expedition_cruise_450`, `norwalk_gi`, 288 epochs),
arm `carriers_ordered`, seeds 8077 and 8038, run with `PYTHONHASHSEED=1`.

## Determinism precondition

Measured: seed 8038 `carriers_ordered` reproduces the committed witness artifact
only under `PYTHONHASHSEED=1` (`124 / 63 / 302232.5893064003 / 10931565.497396061 /
6264823.076130032` infected/symptomatic/dose/delivered/deposited GEC). Under
`PYTHONHASHSEED=0` the same fresh `_run_spec_arm` gave `130 / 86 /
1455721.492520898 / 52604286.25572912 / 29521186.168566264`; earlier random-hash
runs gave `111 / 61 / 1318632.9615008573 / 50689029.23197514 /
19454134.760473896` and a triage run gave `130`. Seed 8077 stayed `74 / 32 /
590029.0614652386 / 25506372.55475977 / 9978453.978031732` in the tested runs.

Inferred: paired-seed witness comparisons are valid only with `PYTHONHASHSEED`
fixed or after the engine is made hash-order independent; hypothesis: set/dict
iteration order is leaking into RNG draws or event ordering. Until then,
uncontrolled-hash witness rows — including seed-8038 DS-M pilot rows — are not
stable measurements.

## Measured ranking

Seed 8077 control: infected 74, symptomatic 32, dose 590029.0614652386,
delivered 25506372.55475977, deposited 9978453.978031732.

| zone_class | scope | candidate | screen_score | activity_mass_gec | delivered_gec | dose_gec | deposited_gec | contacts/h | area_m2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| galley | food_service | yes | 1.74603e7 | 320138 | 317761 | 2377.34 | 342519 | 545.4 | 10.0 |
| dining | food_service | yes | 2.65713e6 | 496659 | 472538 | 24120.6 | 837698 | 42.8 | 8.0 |
| public | event_space | yes | 2.59364e6 | 741041 | 727233 | 13808.5 | 716662 | 21.0 | 6.0 |
| crew_mess | food_service | yes | 357828 | 33441.8 | 31682.8 | 1759.04 | 118724 | 42.8 | 4.0 |
| sanitary | event_space | yes | 158484 | 3773.44 | 58.8008 | 3714.64 | 5219.17 | 21.0 | 0.5 |
| cabin | berthing_excluded | no | 2.92383e8 | 2.45013e7 | 2.39571e7 | 544249 | 7.95763e6 | 17.9 | 1.5 |

Seed 8038 control: infected 124, symptomatic 63, dose 302232.5893064003,
delivered 10931565.497396061, deposited 6264823.076130032.

| zone_class | scope | candidate | screen_score | activity_mass_gec | delivered_gec | dose_gec | deposited_gec | contacts/h | area_m2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| public | event_space | yes | 3.18696e6 | 910561 | 876145 | 34416.3 | 2.03339e6 | 21.0 | 6.0 |
| dining | food_service | yes | 1.24322e6 | 232378 | 229777 | 2600.86 | 479817 | 42.8 | 8.0 |
| crew_mess | food_service | yes | 761151 | 71135.7 | 68107.5 | 3028.2 | 103978 | 42.8 | 4.0 |
| galley | food_service | yes | 441620 | 8097.17 | 8022.55 | 74.6284 | 23733.8 | 545.4 | 10.0 |
| sanitary | event_space | yes | 135628 | 3229.23 | 125.275 | 3103.96 | 15747.2 | 21.0 | 0.5 |
| cabin | berthing_excluded | no | 1.19434e8 | 1.00084e7 | 9.74939e6 | 259009 | 3.60815e6 | 17.9 | 1.5 |

## Interpretation

Measured: no single candidate dominates both seeds. `public` is top on seed
8038 and has the largest in-scope activity on seed 8077, but loses the 8077
screen score to `galley` because `galley` carries the extreme declared
`545.4 contacts/h` constant. `dining` is top-2 on both seeds; `crew_mess` is
mid-ranked on both; `galley` is score-dominant only when that contact constant
multiplies modest activity; `sanitary` has low delivered mass but dose
3103.96–3714.64 GEC, so it may matter through direct hand/mouth exposure rather
than surface delivered mass.

Inferred: the plausible places for detailed spatio-temporal-activity contact
representation are the food-service spaces (`dining`, `crew_mess`, and possibly
`galley`) plus the `public` event space. Berthing/cabin remains governed by the
cabin-mate mechanism and should not be the default per-contact fomite target
despite its larger pooled activity.

Hypothesis: the `galley` `545.4 contacts/h` value is the most suspicious single
denominator; if it is an outlier, the galley-first 8077 ranking is a constant
artifact rather than measured activity. Next decision: fix or control witness
determinism first, then choose between bounded per-contact axes for
`dining`/`public`/`crew_mess` (with a galley-constant sensitivity check) and
contact/behaviour-binding diagnostics.
