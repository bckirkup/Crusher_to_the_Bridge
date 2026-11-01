# CONTAM-PRJNAME-01
**Date:** 2026-11-01
**Commit:** 196ae778
**Pathogens:** all
**Status:** measured
**Measured at:** 196ae778

Implements ranked fix #6 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): committed-prj zone-name normalization at prj parse.

## Defect

Committed GA prjs name zones under CONTAMW limits: underscores stripped,
names truncated to the 15-char field, colliding names deduplicated as
`<base>_<N>`; a handful of zones were also renamed in JSON after their
prj was written. `path_map_from_prj` emitted those mangled names
verbatim, so every committed-prj consumer silently aliased or dropped
endpoints that did not match JSON ids — `contam_fleet_compare`'s
committed lane under-counted the network (dose_l1 understated), the
audit mis-reported renames as prj/json-only zones, and the
ContamXTransportEngine prj fallback dropped every path touching a
mangled name.

## Fix

`prj_zone_aliases(prj_zone_names, canonical_zone_ids,
declared_aliases=None)` in `tools/contamw34_prj.py` resolves mangled
names in order:

1. `declared_aliases` — explicit `{prj_name: zone_id}` pairs validated
   against the canonical set;
2. exact name;
3. `normalize_prj_zone_name` — underscores stripped + 15-char
   truncation; colliding candidates claimed in canonical declaration
   order;
4. positional alignment — only when real-zone counts are equal **and**
   every mechanically resolved pair lands on the same index (prj and
   JSON then share zone order; covers post-prj renames and ContamW
   `_N` dedup names). When either check fails the leftover names stay
   unresolved instead of guessing.

`path_map_from_prj(text, zone_ids, declared_aliases=...)` normalizes
endpoints whenever canonical ids are supplied (raw names preserved when
not — the standalone-PRJ contract is unchanged). Wired through:
`ContamXTransportEngine.build_contamx_engine` prj fallback,
`tools/contam_fleet_compare._contamx_field` committed lane,
`tools/contam_prj_bridge.simplify_prj_to_platform` (path_map now carries
simplified ids),
`tools/ship_blueprint_import/author_contam.validate_prj_offline`, and
`tools/museum_hull_audit.py` (local strip/truncate helpers deleted in
favour of the shared resolver).

The 9 true post-prj renames on count-mismatched hulls (positional
correctly refuses to fire — json-only `*_Sup` zones break index
alignment) are declared via `zone_aliases` in the hulls'
`contam/hobbyist_overrides.json`: assistance_ar17 `Gun_Crew_Qtrs`→
`Gun_Crew_Quarters`; luzon_arg2 `CrewsBerthing_1`→`Crews_Berthing_2nd_F`;
squier_ap130 `FanHatchBlkSup`→`Fan_Hatch_Block_Sup`,
`Galley_Cx_Up`→`Galley_Complex_Up`, `Medical_Cx_2D`→`Medical_Complex_2D`,
`TroopBerthing_1`–`_4`→`Troop_Berthing_{3D_B,3D_C,1P_B,1P_C}` (paired by
shared-neighbor context, not index — counts mismatch by design).

## Measured

Fleet-wide parse of all 75 committed-prj hulls (196ae778 + this diff):
zero unresolved real zone names, zero non-canonical path endpoints
(phantom `ahsN(Ret)/(Sup)` names stay raw by design). Post-fix
`museum_hull_audit` re-run on the audit drift set: prj_only 0 on every
hull; resolved rename pairs erie 18, lexington 46, saratoga 40,
olympia 58; residual json-only zones are the 4 genuine post-prj inserts
(`Gun_Tubs_Sup`, `Gun_Weather_Sup`, `HD_Sup`, `Lounge_Sup`) — honest
inserts, not drift.

Design trap recorded: a loose `<base>_<N>` "ContamW dedup" rule
mis-aliases literal renamed zones (gosper_apa170 `TroopBerthing_2` is a
true rename of `Troop_Berthing_3D_Mid`, not the second
`Troop_Berthing_2D`); the dedup rule was dropped — index-validated
positional resolution covers every real `_N` case on count-equal hulls,
and declared aliases cover the rest.

Tests: `tests/test_prj_zone_names.py` — per-rule unit coverage (norm
collision order, positional accept/refuse, declared-alias validation),
committed-hull endpoint resolution + graded coverage sensitivity on
erie_pg50, and a fleet invariant asserting zero unresolved real prj
zones on every committed-prj hull. `toy_broken` fixture gained a 4th
real prj zone (`orphan_prj`) so its count mismatch keeps `aux_prj` in
the genuine prj-only class.

Closes the last ranked item of CONTAM-MUSEUM-01.
