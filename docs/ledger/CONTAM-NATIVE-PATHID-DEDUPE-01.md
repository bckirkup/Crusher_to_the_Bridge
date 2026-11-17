# CONTAM-NATIVE-PATHID-DEDUPE-01
**Date:** 2026-11-17
**Commit:** f8d11461
**Pathogens:** all
**Status:** measured
**Measured at:** f8d11461

## Scope

The native `ContamTransportEngine` assigns diagnostic `path_id`s while it
builds `airflow_paths`. Several builders can legitimately emit more than one
path with the same id:

- overlapping bidirectional `cross_zone_links` groups (after
  `CONTAM-OLYMPIA-SELFPATH-01`, `olympia_c6` still had 12 duplicated
  non-self `xzone_ladder_well_3_*` ids);
- repeated `adjacency` records on one room pair — exact duplicates on
  `fletcher_class_destroyer`, `mega_cruise_5000`, and `messy_cruise_500`, and
  distinct `sealed_door` + `passageway` records on `legend_class_nsc` and
  `san_antonio_class_lpd`;
- repeated HVAC rooms on `erie_pg50` and `pope_ap110`.

`path_id` is a diagnostic/compare label: the transport operator aggregates by
zone and path flow, never by `path_id`. The defect was therefore label
collision, not a flow change.

## Fix

`engines/py_contam_bridge.py::_build_airflow_paths` now ends with
`_ensure_unique_path_ids()`. It keeps the first occurrence of each id and
renames only later duplicates with a deterministic `_dup{n}` suffix. No path
object is removed and no `flow_rate_m3h`, `path_type`, filter, sink, or
exchange flag changes.

Regression coverage: `tests/test_py_contam_bridge.py::TestNativePathIdUniqueness`
pins the overlapping bidirectional cross-zone case and the distinct-adjacency
type case; `tests/test_contam_path_ids.py` is the fleet-wide native guard.

## Witnesses

Before this commit, the native fleet had duplicate path ids on 8 hulls
(86 extra path objects): `erie_pg50` 40, `fletcher_class_destroyer` 2,
`legend_class_nsc` 2, `mega_cruise_5000` 4, `messy_cruise_500` 8,
`olympia_c6` 12, `pope_ap110` 16, `san_antonio_class_lpd` 2. Only
`legend_class_nsc` and `san_antonio_class_lpd` had *distinct* paths under one
id (`sealed_door` 2.0 m3/h vs `passageway` 15.0 m3/h in both directions); the
rest were exact duplicate emissions.

After `f8d11461`, the same census reports `duplicate_ids=0` fleet-wide and
`renamed_ids` exactly equal to the prior extra-object counts on those 8 hulls
(40/2/2/4/8/12/16/2). Path counts are unchanged: `erie_pg50` 1402,
`fletcher_class_destroyer` 259, `legend_class_nsc` 169,
`mega_cruise_5000` 2306, `messy_cruise_500` 1021, `olympia_c6` 1107,
`pope_ap110` 2169, `san_antonio_class_lpd` 203.

Focused validation on the committed tree: `pytest tests/test_py_contam_bridge.py
tests/test_contam_path_ids.py tests/test_contam_self_paths.py -q` → 63 passed;
`sonar_guard.py` and the repo Ruff selection on the changed Python files
passed.

## Open item

None for path-id uniqueness. The separate Olympia commissioned-lane
make-up/envelope-pressure residual remains recorded in
`CONTAM-OLYMPIA-SELFPATH-01`.
