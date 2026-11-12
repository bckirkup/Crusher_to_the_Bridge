# NORO-HAND-CASCADE-01-SUBSTEPS
**Date:** 2026-11-10
**Commit:** 8a3d4b99
**Pathogens:** all
**Status:** open

Second stage of the hand/fomite cascade repair: the fixed-step arm for the
solver gate proposed in `docs/proposals/noro_hand_cascade_solver_gate.md`.
This entry records the landed mechanism, not a campaign result. No anchor was
fitted and no VSP/Park/attack-rate target was used to choose a constant.

## Landed mechanism (default-off arm)

`transmission.intra_epoch_substeps` defaults to `1`, which keeps the ordered
M=1 call sequence. `M > 1` requires `transmission.intra_epoch_causal_order =
"ordered"` and currently supports only pooled fomite with
`sanitary_visit_mode = "none"` and no `per_surface` fomite arm; other
combinations raise `ValueError` at `TransmissionCore` construction.

For `M > 1`, the engine repeats only the hand-mediated contamination cycle
`M` times per epoch: hand maintenance, emesis-patch pickup, surface
deposits/pickups, food-pool hand deposits/growth/ingestion, and per-substep
hand hygiene. Emesis and isolated-quarter deposits, sanitary visits,
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
- Sanitary-visit and per-surface fomite arms are rejected for `M > 1` until
  their epoch-once side effects are separated from the contamination loop.
- `M > 1` is not stream-neutral with `M = 1`: it repeats hand-hygiene and
  contact draws per substep by design, so paired-seed attribution must treat
  it as a different stochastic realization, not a pure refinement.
- Infection-serial transmission still cannot chain inside an epoch; challenge
  resolution remains once per epoch after all pathogen pathways.
