# CLEAN-OUTBREAK-01
**Date:** 2026-09-18
**Commit:** 9daa4a8
**Pathogens:** all
**Status:** open

SOP-triggered outbreak surface disinfection was applied **once per epoch**
while an outbreak modifier was in force. `ShipSimulation._step_protocols`
called `apply_outbreak_surface_disinfection` →
`TransmissionCore.disinfect_surfaces(4.29, 0.58)` on every epoch the SOP's
`surface_disinfection_log10_reduction` was present. A disinfection pass is a
discrete housekeeping event, not an epoch action: at 1-hour epochs that was
24 full passes per day, each a 4.29-log10 kill — ~100 log10/day of surface
removal, and the rate was epoch-length dependent (the
`clock-unit-safety` skill's named failure mode).

Runtime evidence (`/home/ubuntu/noro_diag/patch_decay.py` traced on a real
classic voyage): one emesis patch deposited at 1.02e7 GEC in unit
`CC_D1_F::cabin1831` was scaled alternately by 0.98808 (the correct
one-epoch surface survival in `_update_surface_pools`) and by 5.1286e-5
(`disinfect_surfaces`, every epoch — the defect), reaching 1.29e-14 by
epoch 20 and ~1e-27 a few epochs later. Fomite pickups then delivered
1e-15..1e-19 GEC. The defect hit every pathogen and every fomite route on
every voyage that reached ALERT — which is every voyage with an import —
and is the dominant reason post-`EMESIS-FOOTPRINT-01` baselines showed zero
onboard secondaries.

## Repair

The outbreak pass is now metered on the clock exactly as routine
housekeeping already is (`_step_routine_surface_cleaning`): per-zone
accumulators advance by `events_per_day(zone_class) *
clock.day_fraction_per_epoch` and fire whole passes.
`TransmissionCore.set_outbreak_disinfection(reduction | None)` is called
every epoch (including epochs with no merged modifiers, so the falling edge
clears); the rising edge fires one immediate ship-wide pass — an outbreak
declaration does trigger an immediate round, and one pass per activation
edge is epoch-length independent. `disinfect_surfaces` keeps its exact
signature and ship-wide behaviour (callers in
`tests/test_surface_cleaning.py`, `tests/test_cleaning_schedule_sweep.py`
unchanged); the per-zone body is now the shared `_disinfect_zone` helper
including `_nested_disinfection_factors`. `apply_outbreak_surface_disinfection`
is deleted, not aliased.

## Pass-rate sourcing

- cabin 1.0/day — VSP 2018 Operations Manual §9.1.1.1.2 "Cabin Cleaning
  (41)": "Cabins that house passengers or crew with AGE must be cleaned and
  disinfected daily while the occupants are ill." Grade A for the
  requirement (the regulator's own prescription for this setting).
  Origin: Tr.
  https://www.cdc.gov/vessel-sanitation/media/files/vsp_operations_manual_2018-508.pdf §9.1.1.1
- default 24.0/day (public areas) — VSP 2018 §9.1.1.1.1 "Continuous
  Disinfection (41)" requires, at ≥2% AGE, cleaning/disinfecting
  hand-contact surfaces of all public areas "on a continuous basis while
  passengers and/or crew are circulating", "without interruption along a
  logical route by deck, venue, and area". VSP gives no circuit time, so
  the per-surface revisit rate is NOT sourced: Grade C declared assumption
  of an hourly circuit, explicitly chosen to preserve the pre-repair
  public-area behaviour at 1-hour epochs so this change is the defect fix
  and nothing else.

## Invalidated measurements

Every voyage outcome measured while an outbreak SOP could fire was taken
under ~100 log10/day of surface removal, including the post-
`EMESIS-FOOTPRINT-01` norovirus baselines: zero onboard secondaries in
12/12 `fl_cls_12d` seeds and 12/12 `fl_exp_12d` seeds of the
`flush_sweep_v1_off_s4` diagnostic arm (run zips under
`telemetry_buffer/noro_diag_2026_09_18/`, extraction under
`/home/ubuntu/noro_diag/`). Those readings are invalid pending
re-measurement on the metered repair; the reported absence of secondary
transmission cannot be attributed to any upstream blocker until the
remeasurement lands. No dose figure measured under the per-epoch pass is
quoted as current.
