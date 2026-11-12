# NORO-HAND-CASCADE-01-SUBSTEPS
**Date:** 2026-11-12
**Commit:** 596d6296
**Pathogens:** all
**Status:** open

Second stage of the hand/fomite cascade repair: the fixed-step arm for the
solver gate proposed in `docs/proposals/noro_hand_cascade_solver_gate.md`.
This entry records the landed mechanism, not a campaign result. No anchor was
fitted and no VSP/Park/attack-rate target was used to choose a constant.

## Landed mechanism (default-off arm)

`transmission.intra_epoch_substeps` defaults to `1`, which keeps the ordered
M=1 call sequence. `M > 1` requires `transmission.intra_epoch_causal_order =
"ordered"` and supports pooled fomite with `sanitary_visit_mode =
"dwell_weighted"`; the `per_surface` fomite arm still raises `ValueError` at
`TransmissionCore` construction.

For `M > 1`, the engine repeats the hand-mediated contamination cycle `M`
times per epoch: hand maintenance, dwell-weighted sanitary deposit/pickup,
emesis-patch pickup, surface deposits/pickups, food-pool hand
deposits/growth/ingestion, and per-substep hand hygiene. The sanitary visit
schedule is drawn once per epoch; each substep exposes that schedule with the
same epoch-fixed dwell share while contact counts use the shorter substep
clock, and a stool-event venue is exposed once per epoch on the first substep
after `_replenish_hand` records it. Emesis and isolated-quarter deposits,
aerosol/common-source/environmental/caregiver routes, and the epoch-boundary
infection challenge stay outside the loop. Substep duration is derived as
`SimClock.hours_per_epoch / M`; per-hour contact rates are exercised through
the same kernels at the shorter clock, and count-like rates use the existing
`SimClock.probability_per_epoch` / decay conversions rather than a hard-coded
"10-minute" assumption.

The witness harness gains `carriers_ordered_sub2`, `carriers_ordered_sub4`,
and `carriers_ordered_sub12` arms, and its mode key now carries `m<M>` so
substep rows do not collapse into the M=1 rows.

## Scope limits

- This is the DS-M arm only. The continuous/event-driven reference and the
  convergence decision are still open in the solver-gate proposal.
- The per-surface fomite arm is still rejected for `M > 1`; sanitary visits
  are now inside the loop with an epoch-fixed visit schedule.
- `M > 1` is not stream-neutral with `M = 1`: it repeats hand-hygiene and
  contact draws per substep by design, so paired-seed attribution must treat
  it as a different stochastic realization, not a pure refinement.
- Infection-serial transmission still cannot chain inside an epoch; challenge
  resolution remains once per epoch after all pathogen pathways.
