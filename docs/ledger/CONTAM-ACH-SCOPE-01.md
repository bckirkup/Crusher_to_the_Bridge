# CONTAM-ACH-SCOPE-01
**Date:** 2026-11-08
**Commit:** 03658422
**Pathogens:** all
**Status:** closed

## Defect

`tools/contam_fleet_compare.py::_op_scale_ach` multiplied `ach` on every
`hvac_zones[]` group with no scope. Duty-0 groups are exhaust-only
terminals whose flow is `ach × V_room` in both lanes, so an unscoped
`scale_ach` also scales the sanitary exhaust branches. That is the gap
recorded for Phase 2 DC04 in `docs/proposals/contam_phase2_scope_manifest.md`
§2.4/§11.1: the high-turnover arm must preserve the duty-zero/OA-one
groups unchanged.

## Change

`scale_ach` now accepts `scope` with the same vocabulary as `set_oa`:

- default `scope: "supply_groups"` scales only groups with positive
  `hvac_duty` (inheriting the top-level duty when undeclared) and leaves
  duty-0 groups' `ach` untouched;
- `scope: "all_groups"` reproduces the pre-change all-groups mutation and
  is labelled `(legacy all_groups)` in the arm edits;
- unknown scopes raise `ValueError`.

The supply-group predicate is shared with `set_oa` (and the existing
largest-supply-group selector), so the two ops cannot drift on what
counts as a supply group. `scale_ach` remains in `_FIELD_OPS`, so every
scope still forces a fresh ContamX export+solve.

## Caller audit / affected prior measurements

Caller audit found one arm-spec measurement caller: `ach_surge` in
`data/config/contam_compare/fleet_arms.json`. The only other in-repo
`scale_ach` references are the compare tool, its tests, and docs/proposals;
none are fleet-compare measurement callers. `ach_surge` is now explicitly
`scope: "all_groups"`, which is exactly the mutation the prior unscoped op
applied, so `CONTAM-FLEET-01`'s `ach_surge` cells remain valid measurements
of the labelled all-groups surge arm and are not superseded or void. The new
default `supply_groups` has no prior fleet-compare measurements, so nothing
else is superseded. `CONTAM-FIELD-OPS-01` and `CONTAM-OA-SCOPE-01` are
unaffected.

## Tests

`tests/test_contam_fleet_compare.py` locks the destroyer fixture's
supply groups scaling while duty-0 `AHU_HD_*` groups keep their declared
`ach`, pins `scope: "all_groups"` as an exact legacy-baseline reproduction,
rejects unknown scopes, keeps `scale_ach` classified as a field op, and
pins the `ach_surge` arm spec to the labelled all-groups scope.
