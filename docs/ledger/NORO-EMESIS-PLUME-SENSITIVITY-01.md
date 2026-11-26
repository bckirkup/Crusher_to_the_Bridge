# NORO-EMESIS-PLUME-SENSITIVITY-01
**Date:** 2026-11-26
**Commit:** f07c97a
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f07c97a30b398ef4e2419d2db7bd6da0c3e121d7

Sensitivity readout for the declared event-moment emesis-plume pulse-duration
and receiving-volume axes on `classic_cruise_1900`. No pathogen profile,
epidemiological constant, plume parameter, mechanism, or campaign configuration
was changed, and no AWS job was submitted.

Raw per-voyage artifacts and the aggregate JSON are committed under
`docs/norovirus/noro_emesis_plume_sensitivity_01/classic_cruise_1900/`:

- `seed8002_compartment_average_p15_v1.json.gz`
- `seed8002_event_pulse_p5_v1.json.gz`
- `seed8002_event_pulse_p15_v1.json.gz`
- `seed8002_event_pulse_p30_v1.json.gz`
- `seed8002_event_pulse_p15_v0.1.json.gz`
- `seed8002_event_pulse_p15_v10.json.gz`
- `seed8105_compartment_average_p15_v1.json.gz`
- `seed8105_event_pulse_p15_v1.json.gz`
- `emesis_plume_sensitivity_readout.json`

The per-cell artifact `design` block is the original pre-fallback frozen design
and still names the 8105/8106 pair; it is retained unmodified as raw provenance.
The authoritative seed declaration for this readout is the next section and the
`seed_declaration` block in the aggregate JSON.

## Seed substitution and firing gate, measured

At measurement commit `f07c97a30b398ef4e2419d2db7bd6da0c3e121d7`, a
tooling-only descendant of main `4abbd2cd57f128fa3d33c09105cd495f2836d10b`, the
originally intended firing seed 8105 produced zero emesis events and zero
exposure rows in both central arms over 288 epochs. That is a measured
current-`main` realization change from the post-repair baseline at
`953c6eab619ad1b5db694c4ad46a2efce8ce6b45`; this readout does not attribute the
shift to a particular intervening merge and does not treat it as an engine
defect. No engine or configuration fix was made.

The fallback used historical event-bearing seeds from `NORO-EMESIS-SIZE-01` in
the predeclared order 8002 then 8018. Seed 8002, the first candidate in that
order, fired and was selected. Seed 8105 is retained as the measured zero-event
witness at the same SHA. Seed 8106 was not rerun: once 8105 had to be replaced
as the firing realization, the canonical 8105/8106 floor no longer existed, and
8105 itself supplied the current-SHA zero witness. Consequently this is an
event-conditioned single-realization sensitivity measurement, not a revival of
the canonical paired-seed population floor. Because seed 8002 was selected from
a historical event-bearing block, even its event-conditioned magnitude is
selection-enriched and is not a random firing-voyage magnitude.

Every seed-8002 `event_pulse` cell passes the firing gate: positive emesis-event
count, positive exposure-row count, complete distance/volume/event-fraction/
opportunity/removal/exposure-hour fields, exact requested mode resolution, an
active catalogued rhythm layer, and `room_air_removal` resolving `first_order`.
Every cell has zero uncommitted-nonoccupant rows and zero uncommitted-nonoccupant
dose.

## Frozen measurement

| field | value |
| --- | --- |
| hull | `classic_cruise_1900`, declared complement 1,910 |
| frame | 288 one-hour epochs |
| bundle | shipped `active_profiles` |
| arms | `event_pulse` and labelled `compartment_average` baseline |
| axis seed | 8002 |
| zero-event witness | 8105 |
| pulse axis | 5, 15, 30 minutes at receiving-volume scale 1 |
| receiving-volume axis | local/adjacent declared-volume scale 0.1, 1, 10 at pulse 15 minutes |
| statistic | voyage-total exact credited recipient-inhaled emesis-aerosol GEC, summed over recipients |
| attribution contrast | shared first-emission dose, with voyage totals reported separately |

“Exact credited dose” is the full-precision `_accumulate` return before
route-efficiency, NPI, susceptibility/protection, and dose-response scaling. It
is route-input inhaled exposure mass, not infection-effective dose and not an
infection probability. Recipient-summed dose is not mass-conserving because one
emitted mass can expose many recipients and inhalation does not deplete the
reservoir.

The volume axis scales only the declared local and adjacent receiving volumes:
2.88/8.82 m³ at scale 1, 0.288/0.882 m³ at scale 0.1, and 28.8/88.2 m³ at
scale 10. Room receiving volumes remain the hull-declared compartment volumes.

## Central paired arms, measured

| seed | arm | emesis events | emitting hosts | emitted aerosol GEC | exposure rows | exposed recipients | recipient-summed inhaled GEC | voyage contrast GEC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8002 | `event_pulse` | 2 | 2 | 23,807.638 | 222 | 210 | 1,958.012 | +1,698.813 |
| 8002 | `compartment_average` | 1 | 1 | 23,695.400 | 104 | 104 | 259.198 | — |
| 8105 | `event_pulse` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8105 | `compartment_average` | 0 | 0 | 0 | 0 | 0 | 0 | — |

The whole-voyage seed-8002 contrast is not by itself a clean exposure-arithmetic
contrast because the arms do not have identical later emission histories. The
attribution-clean comparison is the shared first emission below.

## Shared first emission and paired decomposition, measured

Both central arms share the epoch-14 `MainDining_U` emission by host 1216
exactly: 23,695.400 GEC emitted aerosol, same host-event index, episode load,
and volume. Their 104 `(event, recipient)` exposure keys are identical. Across
all five seed-8002 `event_pulse` sensitivity cells, the first emission also has
the same 104 keys (1 local, 4 adjacent, 99 room), so the axis ordering is
measured on a constant recipient-opportunity set. On that shared emission:

| measure | `event_pulse` | `compartment_average` | contrast |
| --- | ---: | ---: | ---: |
| recipient-summed inhaled GEC | 1,957.935 | 259.198 | +1,698.737 |
| exposure rows | 104 | 104 | 0 |

The compartment-average rows do not themselves carry event-pulse distance-class
fields. The table below therefore maps each compartment-average row onto the
distance class of its identical event-pulse exposure key. All 104 shared rows
are MainDining rows with 15 opportunity minutes per row, 4.0 h⁻¹ removal, and
0.158030 integrated exposure hours per row.

| distance class | rows | recipients | receiving volume m³ | `event_pulse` GEC | `compartment_average` GEC | contrast GEC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `local` | 1 | 1 | 2.88 | 780.122 | 2.492 | +777.630 |
| `adjacent` | 4 | 4 | 8.82 | 1,018.935 | 9.969 | +1,008.966 |
| `room` | 99 | 99 | 1,400 | 158.877 | 246.737 | −87.860 |

Thus the positive shared-emission contrast is entirely a near-field effect:
local plus adjacent rows gain 1,786.596 GEC under `event_pulse`, while the
99 room rows lose 87.860 GEC relative to the whole-compartment average.

## Pulse-duration axis, measured

Voyage totals include any later dose-dependent emission-history divergence;
“shared first-emission dose” is the attribution-clean ordering statistic.

| pulse minutes | events | emitted aerosol GEC | exposure rows | voyage dose GEC | shared first-emission dose GEC | ratio to 15 min shared dose |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 3 | 23,716.815 | 145 | 878.023 | 878.018 | 0.448441 |
| 15 | 2 | 23,807.638 | 222 | 1,958.012 | 1,957.935 | 1 |
| 30 | 2 | 23,734.866 | 206 | 2,680.366 | 2,678.219 | 1.367879 |

Both orderings match the declared arithmetic: dose is monotone nondecreasing in
pulse duration for the voyage total and for the shared first emission. The
shared-dose span is 3.050× across [5, 30] minutes. The shared first-emission
decomposition is:

| pulse minutes | local GEC | adjacent GEC | room GEC | integrated exposure hours per row |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 349.839 | 456.932 | 71.247 | 0.070867 |
| 15 | 780.122 | 1,018.935 | 158.877 | 0.158030 |
| 30 | 1,067.113 | 1,393.781 | 217.325 | 0.216166 |

## Receiving-volume axis, measured

| volume scale | events | emitted aerosol GEC | exposure rows | voyage dose GEC | shared first-emission dose GEC | ratio to scale-1 shared dose |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.1 | 2 | 23,705.216 | 283 | 18,158.126 | 18,149.455 | 9.269691 |
| 1 | 2 | 23,807.638 | 222 | 1,958.012 | 1,957.935 | 1 |
| 10 | 3 | 23,796.304 | 235 | 338.832 | 338.783 | 0.173031 |

Both orderings match the declared arithmetic: dose is monotone nonincreasing as
the receiving-volume scale increases, for the voyage total and for the shared
first emission. The shared-dose span is 53.572× across the declared order-of-
magnitude scaling range. The shared first-emission decomposition is:

| volume scale | local GEC | adjacent GEC | room GEC | local/adjacent volume m³ |
| ---: | ---: | ---: | ---: | --- |
| 0.1 | 7,801.224 | 10,189.353 | 158.877 | 0.288 / 0.882 |
| 1 | 780.122 | 1,018.935 | 158.877 | 2.88 / 8.82 |
| 10 | 78.012 | 101.894 | 158.877 | 28.8 / 88.2 |

The volume result is exactly the declared arithmetic on the shared emission:
local and adjacent dose scale by 10 in each direction while the unscaled room
dose is bit-identical across the three cells. The total ratio is not exactly 10
or 0.1 because the room component is unscaled.

## Later emission-history divergence, measured

The first emission is identical in every seed-8002 sensitivity cell. Later
events are not:

| cell | later seed-8002 events after epoch 14 |
| --- | --- |
| pulse 5, volume 1 | epoch 78 `PoolDeck`, 20.000 GEC; epoch 138 cabin `PC_D8_P_A::cabin1193`, 1.415 GEC |
| pulse 15, volume 1 | epoch 88 `PoolDeck`, 112.238 GEC |
| pulse 30, volume 1 | epoch 86 `MainDining_U`, 39.466 GEC |
| pulse 15, volume 0.1 | epoch 80 `MainDining_U`, 9.816 GEC |
| pulse 15, volume 10 | epoch 81 `PoolDeck`, 64.348 GEC; epoch 141 cabin `PC_D8_P_A::cabin1193`, 36.556 GEC |

All of those later events are emitted by host 1193. Host 1193 is also one of
the four adjacent recipients of the shared first emission, with measured
first-event dose 254.734 GEC in the central `event_pulse` cell versus 2.492 GEC
for the identical exposure key in `compartment_average`; the compartment arm has
no later emission. This is measured row/event evidence. The inference that the
later event-pulse emissions are downstream infection feedback from the larger
near-field dose is consistent with that evidence, but this readout does not
trace the infection challenge or RNG draws further. For that reason voyage
totals are reported, while axis-order validation uses the shared first emission.

## Measured versus inferred

Measured at `f07c97a30b398ef4e2419d2db7bd6da0c3e121d7`: seed 8105's zero-event
pair, seed 8002's firing gate, event counts, emitted masses, exposure rows,
recipient-summed doses, shared first-emission identity, distance/volume/
opportunity/removal decomposition, monotone axis ordering, absence of
uncommitted-nonoccupant dose, and all configuration witnesses. All eight
artifacts record the same engine git SHA.

Inferred, not independently measured: the shared first-emission contrast is
exposure arithmetic rather than RNG-stream disruption because the emission
records and `(event, recipient)` exposure keys are identical and the observer
consumes no RNG. Later divergence is consistent with dose-dependent infection
feedback, but its exact challenge-level path is not traced.

Not measured: population event incidence, a voyage-dose distribution,
statistical significance, infection-effective dose, infection probability, or
the empirical correctness of the declared pulse duration and receiving volumes.
One firing realization cannot size the zero-event mass; seed 8105's measured
zero pair is a witness to that rare-event power limitation, not a second
event-conditioned sensitivity estimate.

## Open decision

Whether the measured 53.572× shared-dose response across the declared
receiving-volume scaling range is acceptable as a sensitivity band for
downstream use, or whether the Grade C plume geometry/pulse declarations must be
evidenced or narrowed before anyone interprets voyage recipient-dose magnitude.
