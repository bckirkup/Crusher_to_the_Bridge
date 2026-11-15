# CONTAM-BUNDLE-RESYNC-01
**Date:** 2026-11-15
**Commit:** 0737c5da
**Pathogens:** all
**Status:** open
**Measured at:** 0737c5da

Stage 5 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §6.1). This re-syncs the three committed ContamW bundles that proposal §4.3 measured as stale against their own committed hull JSON. The bundle pair moves together because `path_map.json` defines the sign convention of the solved flow in the adjacent `platform.prj`.

Method: the byte-pinned path was `PYTHONPATH=. .venv/bin/python scripts/generate_platform_contam_prj.py --platform mega_cruise_5000 --platform enterprise_constitution_tos --platform enterprise_galaxy_tng`, which calls `tools.contam_prj_bridge.export_platform_to_prj(..., hobbyist=True)` on the committed `spatial_layout.json` / `air_flow_paths.json` only. No recipe/generator rewrote hull JSON, and no `hvac`, `oa_fraction`, or flow-rate value changed.

## Re-synced bundles and attribution

| Hull | path_map diff | platform.prj diff | Attribution |
|---|---|---|---|
| `mega_cruise_5000` | path_nr 479-482 (`Medical_Door_Leakage`) endpoints reversed | path records 479-482 swap the same room endpoints; flow elements 30/35 (`Crew_to_Engine_Stairwell`) and 31 (`Medical_Door_Leakage`) change `plr_orfc` → `plr_bdq`; flow elements 36-58 (`Sanitary_Makeup`) change `plr_orfc` → `plr_bdq` | #1220 authored the pressure-directed door/stairwell sense (`AHU_Network_Crew_Accommodation`/`AHU_Crew_Deck_D4` → `AHU_Dedicated_Engine`, and crew/public → `AHU_Dedicated_Medical`) as `direction: oneway`, `mechanism: pressure_opening`; exporter stage #1217 emits one-way passive links as sized backdraft dampers. The sanitary elements are exporter stage #1217 acting on the committed S1 semantics (#1216; one-way pin #1213). |
| `enterprise_constitution_tos` | path_nr 173 (`Galley_Service_Exhaust`) `Galley` → `Mess_Hall` becomes `Mess_Hall` → `Galley` | path record 173 swaps endpoints and drops the passive schedule; flow element 31 becomes `fan_cvf`; flow elements 35-44 (`Sanitary_Makeup`) change `plr_orfc` → `plr_bdq` | #1219 authored the galley make-up sense as `direction: oneway`, `mechanism: prescribed_flow`; exporter stage #1217 emits prescribed-flow links as `fan_cvf`. The sanitary elements are the same #1217/S1 attribution as above. |
| `enterprise_galaxy_tng` | path_nr 320 (`Galley_Service_Exhaust`) `Galley` → `Mess_Hall` becomes `Mess_Hall` → `Galley` | path record 320 swaps endpoints and drops the passive schedule; flow element 32 becomes `fan_cvf`; flow elements 35-44 (`Sanitary_Makeup`) change `plr_orfc` → `plr_bdq` | Same as Constitution: #1219 authoring plus #1217 exporter semantics; sanitary elements are #1217 on S1 semantics. |

No diff is attributable to #1221, #1224, #1228, or #1231 on these three hulls: no path_map entry gained `filtered` or `sink`, no ambient sink endpoint was added, and #1221/#1231 did not author links on `mega_cruise_5000` or the two Enterprise hulls. The Enterprise hull JSON is itself recipe-stale per proposal §5.2 (generator regeneration would revert authored links and, for Constitution, drop `hot_bunk_ratio` values); per the best-effort instruction, the bundles were re-synced against the committed JSON anyway.

## Verification

- Fresh exports are byte-stable for everything except the attributed rows: `mega_cruise_5000` path_map 2,623 entries with 4 changed entries and PRJ 56 added / 56 removed lines; each Enterprise path_map has 1 changed entry and PRJ 23 added / 23 removed lines.
- `check-jsonschema --schemafile schemas/contam_path_map.schema.json` passed for all three regenerated `path_map.json` files.
- `PYTHONPATH=. .venv/bin/python tools/contam_commissioned_check.py --platform enterprise_constitution_tos --platform enterprise_galaxy_tng --platform mega_cruise_5000` passed with the local ContamX binary (`third_party/contamx/contamx3`): 567 / 1,429 / 2,623 emitted paths against 63 / 127 / 187 declared rooms, and every commissioned terminal solved inside the default 5% tolerance.

## Finding only: mega recipe OA drift

Regenerating `mega_cruise_5000` from `messy_cruise_500` in memory (nothing written) would add per-group `oa_fraction` to seven HVAC groups that the committed JSON does not carry: `AHU_Dedicated_Engine` 1.0, `AHU_Dedicated_Medical` 0.5, `AHU_Dedicated_Service_Exhaust` 0.3, `AHU_Network_Aft_Dining_Rec` 0.3, and `AHU_Network_Crew_Accommodation` / `AHU_Network_Forward_Public` / `AHU_Network_Midship_Atrium` 0.2. This PR does not regenerate hull JSON and does not choose which side is correct; that remains owner decision §6.3 item 5.

## Status and blast radius

Status stays `open`: this records the bundle re-sync and local solver commissioning proof, not a campaign re-measurement. No frozen campaign directory, S3 prefix, `_v1`/`_v2` cache, committed readout, or prior ledger is touched, and no recorded measurement is invalidated because as-run artifacts keep their frozen inputs. Future P-lane/ContamX work on these hulls will see the re-synced field; existing frozen caches/readouts remain valid as-run.
