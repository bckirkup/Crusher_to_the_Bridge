# CONTAM-OLYMPIA-SELFPATH-01
**Date:** 2026-11-17
**Commit:** 23a6dd9e
**Pathogens:** all
**Status:** measured
**Measured at:** 23a6dd9e

## Scope

`olympia_c6` has `VENT_Machinery` (9 rooms) and `VENT_Uptakes` (4 rooms)
overlapping on `PF_Boiler_Port`, `PF_Boiler_Stb`, `HD_Boiler_Port`, and
`HD_Boiler_Stb`; the declared `VENT_Machinery -> VENT_Uptakes` link
(`ladder_well_3`, bidirectional `pressure_opening`, 50 m3/h) is semantically
intended and its JSON is unchanged. Both Contam lanes expanded that link to
room×room pairs without skipping `fr == tr`: the export lane emitted 4
zone→same-zone paths, and the native lane emitted 8 self-path objects because
the bidirectional expansion doubles the self-pairs.

ContamX stalled on the old bundle (recorded in
`CONTAM-FIELD-PRESSURE-REVIEW-01` and `CONTAM-DEFAULT-WEATHER-01`); the owner's
manual deletion of only those 4 PRJ self-paths solved in 0.406 s. This entry
lands the same emission filter in code.

## Fix

- `tools/contamw34_prj.py::_add_cross_zone_paths` and
  `engines/py_contam_bridge.py::_build_cross_zone_paths` now skip `fr == tr`
  at path emission only.
- `pair_flow` is still `flow / (len(from_rooms) * len(to_rooms))` computed
  before filtering; no flow rate, leak area, weather, platform JSON, or
  epidemiological constant changed.
- Regression guard: `tests/test_contam_self_paths.py` re-exports all 77
  committed bundles and builds all 82 native layouts and asserts no emitted
  path has `from_zone == to_zone`; focused unit tests in
  `tests/test_py_contam_bridge.py` and `tests/test_contamw34_dual_path.py`
  pin the unchanged denominator on an overlapping two-group fixture.

## Witnesses

Byte-pin: regenerated all 77 committed bundles with
`scripts/generate_platform_contam_prj.py --ahs-terminal-mode commissioned`
(82 platform dirs; `expedition_cruise_300`, `fletcher_class_destroyer`,
`legend_class_nsc`, `messy_cruise_500`, and `san_antonio_class_lpd` have no
bundle). Within `data/platforms/`, `git diff` against `origin/main`
`0bfc058d` touches only `data/platforms/olympia_c6/contam/platform.prj` and
`path_map.json`; the other 76 bundles are byte-identical. Olympia
`path_map.json` goes 805 → 801 entries and the PRJ flow-path count 805 → 801:
exactly the four self records (`PF_Boiler_Port`, `PF_Boiler_Stb`,
`HD_Boiler_Port`, `HD_Boiler_Stb`) are removed, with renumbering.

Native lane: fingerprints over all 82 platform layouts, before vs after, move
only `olympia_c6` (1115 → 1107 paths; 8 self-path objects removed, 0 added).
The other 81 native fingerprints are unchanged; Olympia has no self-paths
after the change. Pre-existing duplicate `path_id`s beyond self-pairs remain on
8 hulls (including Olympia's shared boiler-room pairs) and are out of scope
here; reported to the owner.

ContamX: `third_party/contamx/contamx3 platform.prj` on the regenerated Olympia
bundle exits 0 on this box (wall 0.010 s; owner measured 0.406 s) and writes
`platform.sim`.

Pressure balance (`tools/diag/contam_pressure_balance_diagnostic.py --hull
olympia_c6 --lane design --lane commissioned`, 300 s timeout): 2 rows, 0
unsolved.

| lane | max abs dP Pa | envelope max abs dP Pa | AHS return-supply m3/h | makeup demand m3/h | makeup per leak m3/h |
|---|---:|---:|---:|---:|---:|
| design | 92.051 | 1.379 | 0.0 | 0.0 | 0.0 |
| commissioned | 27635.768 | 27635.768 | 4491.427 | 4491.427 | 43.187 |

The commissioned row reproduces the residual make-up/envelope-pressure
observation reported after self-path removal (~27.6 kPa at the envelope). The
open-forecastle scenario and any historical dimension are separate follow-up
work; no weather/exposure authoring is in this entry.

## Open item

Olympia's commissioned-lane envelope pressure remains ~27.6 kPa with ~4,491
m3/h make-up demand concentrated through the leak set; that is the separate
make-up/forecastle question, not the self-path stall.
