# NORO-EMESIS-PLUME-DOSE-01
**Date:** 2026-11-26
**Commit:** 993a5a0
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** ead2ce799606262d97fd6745cf9c4dda05172054

Paired-seed local readout of recipient-inhaled emesis-aerosol dose under the
merged event-moment plume. No engine mechanism, profile, constant, or campaign
configuration is changed here, and no AWS job was submitted. The measurement
instrument is `tools/noro_diag/emesis_plume_dose_measurement.py` at the
measurement SHA, using read-only wrappers that consume no RNG.

Raw per-voyage artifacts are committed under
`docs/norovirus/noro_emesis_plume_dose_01/classic_cruise_1900/`:

- `seed8105_event_pulse.json.gz`
- `seed8105_compartment_average.json.gz`
- `seed8106_event_pulse.json.gz`
- `seed8106_compartment_average.json.gz`

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
It is the route-input inhaled exposure mass the model books, not an
infection-effective dose and not an infection probability. Inhalation does not
deplete the emitted mass, and one emitted mass can expose many recipients, so
the recipient-summed dose is not mass-conserving and is not bounded by emitted
mass.

The configuration witness is measured in every artifact: the requested plume
mode resolved exactly, the catalogued rhythm layer was active,
`room_air_removal` resolved `first_order`, the pulse was 15 minutes, and the
declared local/adjacent volumes were 2.88/8.82 m³.

## Voyage totals, measured

| seed | arm | emesis events | emitting hosts | emitted aerosol GEC | exposure rows | exposed recipients | recipient-summed inhaled GEC | mean per exposed recipient GEC | max per exposed recipient GEC | paired contrast GEC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8105 | `event_pulse` | 1 | 1 | 402.826 | 1,219 | 1,219 | 118.783 | 0.09744 | 0.09744 | +54.411 |
| 8105 | `compartment_average` | 4 | 2 | 8,463.659 | 41 | 36 | 64.3715 | 1.7881 | 30.5142 | — |
| 8106 | `event_pulse` | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 |
| 8106 | `compartment_average` | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — |

The firing gate passes on seed 8105: event count is positive and the
`event_pulse` rows carry complete `distance_class`, receiving-volume,
event-fraction, opportunity-window/minute, removal, and exposure-hour fields.
Seed 8106 has no emesis event in either arm, so it contributes a measured
zero/zero pair but no mechanism evidence. One firing seed proves the pathway is
not dead in the default configuration; two paired seeds do not size incidence,
an effect, or significance.

## Shared first emission, measured

Both seed-8105 arms begin with the same emission: epoch 21, agent 1582,
`Laundry`, episode load 25,073,955.798 GEC, volume 60.325 mL, emitted aerosol
402.826 GEC. That shared emission gives the cleanest exposure comparison
because it is upstream of downstream infection feedback.

| exposure set for the shared emission | rows | recipients | recipient-summed inhaled GEC | mean GEC per row |
| --- | ---: | ---: | ---: | ---: |
| `event_pulse`, all rows as implemented | 1,219 | 1,219 | 118.783 | 0.09744 |
| `event_pulse`, epoch occupants only | 9 | 9 | 0.877 | 0.09744 |
| `event_pulse`, rhythm-committed nonoccupants | 0 | 0 | 0 | — |
| `event_pulse`, no-evidence nonoccupants | 1,210 | 1,210 | 117.906 | 0.09744 |
| `compartment_average` | 9 | 9 | 1.0353 | 0.1150 |

The occupant-only row subset is a decomposition of measured rows, **not** a
corrected-event-pulse arm: removing rows inside the simulation would change
challenge draws and downstream infections. Within that limitation, the
implemented `event_pulse` total is 114.7× the compartment dose for the same
emission, while its nine-occupant subset is 0.847× the compartment dose.

## Distance, time, volume, and removal decomposition, measured

All seed-8105 `event_pulse` rows came from the single `Laundry` event and were
classified `room`; no `local` or `adjacent` row occurred. Seed 8106 had no
rows.

| distance class | rows | recipients | dose GEC | receiving volume m³ | opportunity min | removal h⁻¹ | exposure h |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `local` | 0 | 0 | 0 | — | — | — | — |
| `adjacent` | 0 | 0 | 0 | — | — | — | — |
| `room` | 1,219 | 1,219 | 118.783 | 280.0 | 15.0 | 7.5 | 0.112886 |

Every row used the full `[0, 15]` minute fallback window and `presence_share`
1.0. The measured zero local/adjacent counts are properties of this seed's
`Laundry` event, not evidence that those classes cannot fire elsewhere.

## Emitted-mass band comparison

The historical 9–906 GEC/voyage figure is emitted aerosol mass under the old
compartment-averaged treatment, not recipient dose. Against that band:

- `event_pulse` seed 8105 emitted 402.826 GEC over the voyage, inside the band.
- `compartment_average` seed 8105 emitted 8,463.659 GEC over the voyage, above
  the band because three later events followed the shared first event:
  992.135 GEC in `Laundry` at epoch 71, 324.968 GEC in `PoolDeck` at epoch 73,
  and 6,743.731 GEC in `CC_D1_A::cabin1346` at epoch 75.
- seed 8106 emitted zero in both arms.

The compartment-arm voyage dose is dominated by the cabin-compartment event:
61.028 of 64.3715 recipient-summed GEC (94.8%) arises at epoch 75, where the
two exposed recipients each carry 30.514 GEC. Whether those later events are
causally attributable to the first aerosol exposure is **not measured**; their
occurrence and mass are measured, but the route attribution of the infections
behind them was not part of this instrument.

## Material implementation defect measured

`NORO-EMESIS-PLUME-01` licenses epoch-occupancy fallback only where no rhythm
commitment resolves the pulse: current epoch occupancy is the coarse fallback.
The measured implementation does not satisfy that clause.

`_emesis_schedule_candidates` scans recipients outside the epoch occupant set,
but calls `_emesis_opportunity_windows`. That helper converts
`presence_overlap_window is None` — no commitment evidence — into full presence
for the whole pulse. Consequently a nonoccupant with no commitment receives the
occupant fallback even though the fallback is licensed only for current
occupants.

The voyage witness quantifies the defect directly. For the seed-8105 shared
emission:

- 9 rows were epoch occupants: 0.877 GEC.
- 0 rows were rhythm-committed nonoccupants.
- 1,210 of 1,219 rows (99.26%) were nonoccupants with no commitment evidence:
  117.906 of 118.783 recipient-summed GEC (99.26%).

Those 1,210 rows are not a statistical fluctuation; they are the fallback
being applied outside its declared domain. They also matter for attribution:
infection challenge resolution consumes RNG per challenged recipient, so the
large spurious exposed set can reorder downstream challenge draws even when it
establishes no infection. The measured raw voyage contrast (+54.411 GEC on
seed 8105) is therefore **not** an attributable event-pulse mechanism effect.
It is what the merged implementation delivers on this seed, including the
defect and downstream divergence.

No engine repair is included in this measurement change. A minimal regression
for the next engine change is: a susceptible outside the emitting unit, with no
rhythm commitment resolving the pulse, must receive no event-pulse row.

## Measured versus inferred

Measured at `ead2ce799606262d97fd6745cf9c4dda05172054`, seeds 8105/8106:
all event counts, emitted masses, exposure rows, recipient-summed doses,
distance/time/volume/removal fields, occupancy/candidate witness categories,
and zero-event seed-8106 outcomes reported above.

Inferred or code-established but not measured as a counterfactual: the exact
corrected-voyage dose after refusing no-evidence nonoccupants. The
occupant-only row exclusion is arithmetic on measured rows, not a corrected
simulation arm, and the downstream effect of removing those challenges is
unknown.

Hypothesis only: repairing the candidate fallback will sharply reduce the
seed-8105 direct `event_pulse` recipient-summed dose. Its effect on infections,
later emesis events, and voyage totals is unmeasured.

## Open decision

Whether to repair the `event_pulse` candidate fallback according to the
plume ledger contract and rerun this paired readout before interpreting
recipient-dose magnitudes. This measurement should not be used as evidence for
the intended plume magnitude until that decision is made.
