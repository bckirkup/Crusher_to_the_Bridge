# NORO-EMESIS-PLUME-FALLBACK-01
**Date:** 2026-11-26
**Commit:** 49b1226
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 953c6eab619ad1b5db694c4ad46a2efce8ce6b45

Repair and paired re-readout of the recipient-opportunity defect measured in
[NORO-EMESIS-PLUME-DOSE-01](NORO-EMESIS-PLUME-DOSE-01.md). The repair changes
no pathogen profile, epidemiological constant, pulse duration, receiving
volume, removal value, or campaign configuration. No AWS job was submitted.

Raw per-voyage artifacts are committed under
`docs/norovirus/noro_emesis_plume_fallback_01/classic_cruise_1900/`:

- `seed8105_event_pulse.json.gz`
- `seed8105_compartment_average.json.gz`
- `seed8106_event_pulse.json.gz`
- `seed8106_compartment_average.json.gz`

## Repair

`_emesis_schedule_candidates` now consults
`RhythmLayer.presence_overlap_window` directly for a nonoccupant. A `None`
result — no commitment evidence — refuses the candidate instead of passing
through `_emesis_opportunity_windows`, whose full-pulse fallback is licensed
only for current epoch occupants. A rhythm-committed nonoccupant can still be
a candidate; confinement, ashore/departed state, isolation, and caregiver
absorption remain refusals.

Regression coverage: `test_uncommitted_nonoccupant_is_not_a_schedule_candidate`
proves the uncommitted nonoccupant receives no event-pulse row, while the
pre-existing `test_rhythm_committed_pre_egress_candidate_is_dosed` lock proves
the committed candidate path still fires. The focused rhythm/emesis suite is
65/65 green at the measurement commit.

## Frozen measurement

| field | value |
| --- | --- |
| hull | `classic_cruise_1900`, declared complement 1,910 |
| frame | 288 one-hour epochs |
| bundle | shipped `active_profiles` |
| arms | `event_pulse` and `compartment_average` |
| seeds | 8105/8106, paired |
| statistic | voyage-total exact credited recipient-inhaled emesis-aerosol GEC, summed over recipients |
| contrast | `event_pulse` minus `compartment_average` on the same seed |

“Exact credited dose” is the full-precision `_accumulate` return before
route-efficiency, NPI, susceptibility/protection, and dose-response scaling.
It is route-input inhaled exposure mass, not infection-effective dose and not
an infection probability. Recipient-summed dose is not mass-conserving because
one emitted mass can expose many recipients and inhalation does not deplete
the reservoir.

The configuration witness is measured in every artifact: requested plume mode
resolved exactly, the catalogued rhythm layer was active,
`room_air_removal` resolved `first_order`, the pulse was 15 minutes, and the
declared local/adjacent volumes were 2.88/8.82 m³.

## Voyage totals, measured

| seed | arm | emesis events | emitting hosts | emitted aerosol GEC | exposure rows | exposed recipients | recipient-summed inhaled GEC | mean per exposed recipient GEC | max per exposed recipient GEC | paired contrast GEC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8105 | `event_pulse` | 4 | 2 | 8,463.659 | 41 | 36 | 497.035 | 13.8065 | 247.098 | +432.664 |
| 8105 | `compartment_average` | 4 | 2 | 8,463.659 | 41 | 36 | 64.3715 | 1.7881 | 30.5142 | — |
| 8106 | `event_pulse` | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 |
| 8106 | `compartment_average` | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — |

The firing gate passes on seed 8105: event count is positive and all 41
`event_pulse` rows carry complete distance-class, receiving-volume,
event-fraction, opportunity-window/minute, removal, and exposure-hour fields.
Seed 8106 again contributes a measured zero/zero pair but no mechanism
evidence.

## Recipient-opportunity witness, measured

All 41 seed-8105 `event_pulse` rows are epoch occupants. None is an
uncommitted nonoccupant (`observer_uncommitted_nonoccupant`: 0 rows, 0 GEC),
and no rhythm-committed nonoccupant candidate receives a row in this voyage.
The rows therefore use the licensed occupant fallback rather than the defect
quantified in NORO-EMESIS-PLUME-DOSE-01.

The seed-8105 pulse decomposition is:

| distance class | rows | recipients | recipient-summed inhaled GEC |
| --- | ---: | ---: | ---: |
| `local` | 2 | 2 | 494.197 |
| `adjacent` | 0 | 0 | 0 |
| `room` | 39 | 34 | 2.838 |

Receiving volumes are 2.88 m³ on the two `local` rows, 280 m³ on 17 `room`
rows, and 2,100 m³ on 22 `room` rows. Every row has 15 opportunity minutes.
Removal is 3.0 h⁻¹ on the two local rows, 7.5 h⁻¹ on the 17 Laundry rows, and
49.327381 h⁻¹ on the 22 PoolDeck rows; corresponding integrated exposure
hours are 0.175878, 0.112886, and 0.020273. Event epoch fractions are 0.0098,
0.3516, 0.5, and 0.7656 across the four emissions.

## Emission-resolved contrast, measured

The post-repair seed-8105 arms have identical emission records and identical
`(event, recipient)` exposure keys: four events, 41 rows, and 36 recipients in
both arms. The seed-8105 compartment-average artifact also exactly reproduces
the pre-repair compartment-average event records, stable exposure rows, and
64.37154278053652 GEC total, because candidate scanning is gated off in that
arm and the probe consumes no RNG. This is the control showing that the repair
and instrumentation did not move the baseline arm.

| epoch | zone | rows | emitted aerosol GEC | `event_pulse` dose GEC | `compartment_average` dose GEC | contrast GEC |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 21 | `Laundry` | 9 | 402.826 | 0.877 | 1.035 | −0.158 |
| 71 | `Laundry` | 8 | 992.135 | 1.920 | 2.266 | −0.347 |
| 73 | `PoolDeck` | 22 | 324.968 | 0.0414 | 0.0414 | ≈0 |
| 75 | `CC_D1_A::cabin1346` | 2 | 6,743.731 | 494.197 | 61.028 | +433.169 |

The voyage contrast is therefore dominated by two local cabin-mate rows in the
2.88 m³ declared receiving volume: each recipient is credited 247.098 GEC
under `event_pulse` versus 30.514 GEC under `compartment_average`. The room
events slightly reduce dose under the pulse because the time-integrated
15-minute opportunity is shorter than the whole-epoch average, while the
high-removal PoolDeck event is nearly unchanged because removal dominates
both integrals.

## Historical emitted-mass band

The historical 9–906 GEC per-voyage band is emitted aerosol mass under the old
treatment, not recipient inhaled dose. Against that emitted-mass scale only:
seed 8105 emits 8,463.659 GEC in both arms, above the band; seed 8106 emits
zero because no emesis event occurs. The recipient-summed inhaled doses —
497.035 GEC under `event_pulse` and 64.3715 GEC under `compartment_average` on
seed 8105 — are numerically inside 9–906 but are a different quantity and are
not validated by that band.

## Measured versus inferred

Measured at `953c6eab619ad1b5db694c4ad46a2efce8ce6b45`: the repair, regression
behavior, seed-8105/8106 event counts, emitted masses, exposure rows,
recipient doses, occupancy witness, distance/volume/opportunity/removal
decomposition, identical post-repair emission/exposure keys, and the
compartment-arm pre/post control equality.

Inferred, not measured as a population claim: on this seed the identical
realized emission and recipient histories make the row-level contrast clean
exposure arithmetic rather than the pre-repair spurious-candidate artifact.
That does not prove every seed or parameter cell keeps outcome histories
identical; dose-dependent infection outcomes can diverge. Two paired seeds
prove firing and measure this realization but do not size incidence, a voyage
distribution, or significance.

The large local-dose contribution follows the declared 2.88 m³ local receiving
volume and 15-minute pulse. It is not a fitted magnitude and does not validate
those declared sensitivity axes.

## Open decision

Whether the next measurement should spend seeds on the declared pulse-duration
and receiving-volume sensitivity axes before any interpretation of voyage
recipient-dose magnitude.
