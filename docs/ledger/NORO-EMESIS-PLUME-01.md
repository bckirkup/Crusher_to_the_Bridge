# NORO-EMESIS-PLUME-01
**Date:** 2026-11-26
**Commit:** 334e9c51
**Pathogens:** norwalk_gi
**Status:** declared


## Change

The emesis aerosol source-room route now has two declared arms under
`transmission.emesis_event_plume.mode`:

- `event_pulse` (default): each emitted aerosol mass is converted to recipient
  inhaled exposure as emission / receiving volume × breathing rate × the
  recipient's time-integrated presence window, with first-order air removal.
  Exposure records carry `airborne_mass`, `receiving_volume_m3`,
  `event_epoch_fraction`, `opportunity_entry_minutes`,
  `opportunity_exit_minutes`, `removal_per_hour`, `exposure_hours`, and
  `distance_class`.
- `compartment_average`: the labelled pre-change whole-epoch room-average
  baseline.

The coarse distance classes are `local` (same table/unit), `adjacent`
(neighbouring table / outer splash shell), and `room`. This is the coarse
structure licensed by `consensus_tranche_58_emesis_coexposure.md`; it is not a
continuous distance kernel and no radius, concentration, decay constant, or
magnitude is fitted to Marks or any outbreak anchor.

## Declared inputs and provenance

Tranche 58 measured emission fractions and floor geometry but found no licensed
event-moment concentration, receiving volume, pulse duration, decay rate, or
distance kernel. The implementation therefore declares:

- pulse duration 15 min, midpoint of a declared [5, 30] min pre-cleanup /
  avoidance sweep axis (Grade C / null-literature declaration);
- local receiving volume 2.88 m3 = Booth's measured 1.2 m × 1.6 m main-bulk
  footprint × declared 1.5 m breathing/mixing height (Grade C composite);
- adjacent shell receiving volume 8.82 m3 = (measured 7.8 m2 outer footprint −
  1.92 m2 main footprint) × the same declared height (Grade C composite);
- removal from the hull's declared first-order air-exchange map when
  `room_air_removal` is active, otherwise zero under the sealed baseline.

## Recipient opportunity and hull schedules

`RhythmLayer.presence_overlap_window` resolves minute-level ingress/egress and
synchronized egress fronts against the emitted event's reconstructed sub-epoch
position. Rhythm-committed recipients are candidates even when hourly placement
has already moved them to an egress corridor; confinement-overridden bookings do
not count. Where no commitment resolves the pulse, current epoch occupancy is
the coarse fallback and represents presence for the whole pulse. The regression
suite now verifies every catalogued platform builds a rhythm layer when
`rhythm.enabled` is unspecified, preserving the config-level default-on
contract. `explorer_seas_06` remains uncatalogued as the previously declared
Explorer exception; it was not given another hull's schedule.

## Known boundary

This is an event-moment exposure decomposition, not a CFD plume and not a
mass-conserving two-box spatial dispersion model. The emitted mass continues
into the existing reservoir drain for later transport; the event pulse is the
pre-mixing exposure of the same mass before that room-pool tail. Uncommitted
token-fallback movement still has only epoch-resolution opportunity evidence.
Pulse duration and receiving volumes are mandatory sensitivity axes before
interpreting voyage dose magnitudes.
