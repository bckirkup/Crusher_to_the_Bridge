# CONTAM-OA-SCOPE-01
**Date:** 2026-11-07
**Commit:** c1e5ff03
**Pathogens:** all
**Status:** closed

## Defect

`tools/contam_fleet_compare.py::_op_set_oa` applied a `set_oa` arm to the
top-level airflow dict, **every** `hvac_zones` group, and `engine_args`.
On hulls with duty-0 declared-`oa_fraction: 1.0` exhaust terminals
(`AHU_HD_*` sanitary branches), an OA sweep therefore overwrote the
exhaust branches' declared outdoor-air/exhaust-capture semantics along
with the supply groups it was meant to sweep.

## Change

`set_oa` now defaults to `scope: "supply_groups"`:

- supply groups (`hvac_duty > 0`, inheriting the top-level duty when
  undeclared) receive the arm value;
- duty-0 groups keep their declared `oa_fraction` (the exhaust-branch
  value, normally 1.0);
- the top-level `oa_fraction` and the engine-level `oa_fraction` argument
  still receive the arm value, because they are the supply-side default
  consumed by the native engine and the ContamX AHS bridge scalar.

The pre-change all-groups behaviour is kept as the labelled baseline
`scope: "all_groups"`; unknown scopes raise `ValueError` instead of being
silently ignored.

## Affected prior measurements

- `CONTAM-FLEET-01` `outdoor_air` and `full_recirc` arms: on platforms
  carrying `AHU_HD_*` duty-0 exhaust branches, the arm also rewrote those
  branches' `oa_fraction`, so the recorded native-vs-ContamX response for
  those arms is not a pure supply-OA sweep. Treat those arm cells as
  superseded by the scoped arm; the committed baseline field arm is
  unaffected because it does not apply JSON-side arm mutations.
- `CONTAM-DIVERGENCE-01` / `CONTAM-COMMISSION-01` mechanism notes are not
  invalidated: they describe engine behaviour, not this compare-tool arm
  mutation. The destroyer 42%-vs-98% hook remains a solver/airflow-field
  divergence measurement, not an OA-scope artifact.

## Tests

`tests/test_contam_fleet_compare.py` locks the destroyer fixture's
duty-0 `AHU_HD_*` groups at `oa_fraction == 1.0` across a graduated
supply-OA sweep, pins `scope: "all_groups"` as the labelled legacy arm,
and rejects unknown scopes.
