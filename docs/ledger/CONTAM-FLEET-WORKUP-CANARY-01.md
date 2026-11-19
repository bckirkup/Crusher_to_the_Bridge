# CONTAM-FLEET-WORKUP-CANARY-01
**Date:** 2026-11-19
**Commit:** d5d50d3a7bc30d50231e6f27b5083925f26c9c23
**Pathogens:** all
**Status:** measured
**Measured at:** 5f524b8104dc2ca09a36d822b257f015af1fd8f4

**Amends [CONTAM-FLEET-WORKUP-PROTOCOL-01](CONTAM-FLEET-WORKUP-PROTOCOL-01.md)
for the four-hull canary. The matrix, hulls and row IDs are unchanged.** No
pathogen, occupant or stochastic outcome is involved; no seeds apply.

**Measured before any timing.** On all four canary hulls, halving the
outdoor-air fraction changes the exported ContamX project and no solved path
flow. ContamX reports zero flow on every simple-AHS outdoor-air, exhaust and
recirculation path. Outdoor-air fraction therefore reaches the ContamX lane
only through the import-side recirculation synthesis, which is shared model
code. Wind does reach the solver.

**Amendment.** Results are reported in two labelled blocks: `solved_airflow`
(the lane's own field; unresolved quantities blank, not 0) and
`downstream_mixing` (the shared operator on that field; derived). Gates read
realized terminal flow, realized effective mixing and the solved field
digest. Criteria, definitions and tolerances:
`campaigns/contam/fleet_workup_canary_01/design/canary_criteria.json`.

**Canary result.** One AWS Batch job
(`3940f345-8c40-4dcb-842b-800d44178266`), 77 of 77 executed rows, 318 timed
ContamX solves, no failure. Both outdoor-air rows leave the ContamX solved
field unchanged on all four hulls and move only the derived mixing block.
Baseline tracer material time, native vs harmonized ContamX: destroyer 0.356
vs 0.497 h, Enterprise 0.492 vs 0.485 h, expedition 0.489 vs 0.493 h, West
Virginia 1.710 vs 0.909 h. Cold end-to-end wall time, native vs ContamX:
0.98 vs 17.0 ms on the 9-zone hull to 497 vs 797 ms on the 198-zone hull.
Full readout and provenance:
`campaigns/contam/fleet_workup_canary_01/READOUT.md`.

**Where.** Campaign `contam/fleet_workup_canary_01`; running record in its
`LEDGER.md`. Runner `tools/diag/contam_fleet_workup_run.py`, cell
`contam_fleet_workup_cell.py`, gates `contam_fleet_workup_gates.py`, reducer
`contam_fleet_workup_reduce.py`.

**Limits.** Two models are compared numerically; neither is validated
against a ship. The downstream block shares one mass-balance model across
lanes. Test levels are assumed, not measured. The other 73 hulls are not
run; that is Benjamin's decision after the canary readout.
