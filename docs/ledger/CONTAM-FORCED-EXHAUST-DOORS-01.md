# CONTAM-FORCED-EXHAUST-DOORS-01
**Date:** 2026-11-14
**Commit:** 01a3482e
**Pathogens:** all
**Status:** open
**Measured at:** 541b9f4f5011ba9c93a5af35c7ca909ce9876026

Pressure-directed door/stairwell leakage class of
`docs/proposals/forced_exhaust_audit_and_fix_plan.md` §5.5 row 4. This entry
authors direction/descriptions and records decisions only; row 5 (ducted
relief/medical exhaust) is a later session. The branch commits carrying the
data/test changes are `826d8f86` and `541b9f4f`; measurements below were taken
on that tree.

## Taxonomy reconciliation

The audit names 7 `pressure_directed` links on four platforms, matching plan
§2.4/§5.5: `mega_cruise_5000` (3), `messy_cruise_500` (2),
`expedition_cruise_300` (1), and `fletcher_class_destroyer` (1). All seven
descriptions stated a pressure regime, so none falls in the "reviewed, no
change, reason" bucket. `path` strings were not renamed; `path` is consumed by
committed `contam/path_map.json` artifacts and by flow-compare attribution.

The committed `docs/proposals/forced_exhaust_audit_summary.json` is a pre-S1
artifact (`direction_present: 0` fleet-wide) but its `pressure_directed`
counts match the live tree; the measurements here use
`tools/diag/forced_exhaust_audit.py` on the current tree.

## Decisions

Every link keeps `mechanism: "pressure_opening"`, `filtered: false`,
`is_hvac_ducted: false`, and an unchanged `flow_rate_m3h`; only `direction`
and, where the stated regime ran opposite the old declaration, `from`/`to`
changed.

Kept declared sense — engine-room negative pressure draws air from crew
accommodation/service spaces; ISO 9943:2009 A.2.3 adjacent-space
pressure-ordering analogy, Grade C:

| Platform | Path | Link | m³/h |
|---|---|---|---:|
| `mega_cruise_5000` | `Crew_to_Engine_Stairwell` | `AHU_Network_Crew_Accommodation` → `AHU_Dedicated_Engine` | 4,000.0 |
| `mega_cruise_5000` | `Crew_to_Engine_Stairwell` | `AHU_Crew_Deck_D4` → `AHU_Dedicated_Engine` | 2,000.0 |
| `messy_cruise_500` | `Crew_to_Engine_Stairwell` | `AHU_Network_Crew_Accommodation` → `AHU_Dedicated_Engine` | 4,000.0 |

Reversed declared sense — the stated regime runs opposite the old
declaration:

| Platform | Path | Before → after | m³/h | Basis |
|---|---|---|---:|---|
| `expedition_cruise_300` | `MedBay_Door_Leakage` | `AHU_MedBay_Dedicated` → `AHU_2_Main` ⇒ `AHU_2_Main` → `AHU_MedBay_Dedicated` | 50.0 | MedBay negative pressure, net inflow from surrounding public/corridor air; CDC VSP 2025 §33.2.1–§33.2.2; ISO 9943:2009 A.2.3 |
| `fletcher_class_destroyer` | `access_trunk_boilers` | `HVAC_Berthing` → `HVAC_Boiler_Rooms` ⇒ `HVAC_Boiler_Rooms` → `HVAC_Berthing` | 150.0 | Boiler-room positive pressure pushes air upward to second-deck berthing/mess; ISO 9943:2009 A.2.3; naval hull, Grade C |
| `mega_cruise_5000` | `Medical_Door_Leakage` | `AHU_Dedicated_Medical` → `AHU_Network_Crew_Accommodation` ⇒ `AHU_Network_Crew_Accommodation` → `AHU_Dedicated_Medical` | 100.0 | Medical/Isolation Ward strictly negative relative to crew/public corridors; CDC VSP 2025 §33.2.1–§33.2.2; ISO 9943:2009 A.2.3 |
| `messy_cruise_500` | `Medical_Door_Leakage` | `AHU_Dedicated_Medical` → `AHU_Network_Crew_Accommodation` ⇒ `AHU_Network_Crew_Accommodation` → `AHU_Dedicated_Medical` | 100.0 | Medical/Isolation Ward strictly negative relative to crew/public corridors; CDC VSP 2025 §33.2.1–§33.2.2; ISO 9943:2009 A.2.3 |

## Standards basis

Clause-level citations only: CDC VSP 2025 Construction Standards
§33.2.1–§33.2.2 for the medical/isolation negative-pressure links, and ISO
9943:2009 A.2.3 as the adjacent-space pressure-ordering analogy for the
engine/boiler regimes. No standard text is committed here. No magnitude was
proposed, re-derived, or re-chosen from either lane's output.

## Audit and flow-compare measurements

`tools/diag/forced_exhaust_audit.py` reconciles 82 platforms / 1,011 links
before and after. Before this change the seven `pressure_directed` links
reported `native_reverse_on_stated_oneway` with 53 native reverse room paths
(expedition 9, fletcher 6, mega 14, messy 24). After this change the class
reports zero `native_reverse_on_stated_oneway` flags, zero native reverse
paths, and fleet `native_reverse_paths_on_stated_oneway` is 0.

The audit tool's `exporter_*` columns remain the pre-X1 diagnostic
(`exporter_reads_direction: False`), so they are not the X1 exporter state;
exporter evidence is the scratch-export note below.

Native flow-compare path counts
(`tools.contam_flow_compare.native_links_report`) move only by removal of the
reverse cross-zone leg on each formerly bidirectional link:

| Hull | `n_paths` before → after | `cross_zone` before → after |
|---|---:|---:|
| `expedition_cruise_300` | 478 → 469 | 366 → 357 |
| `fletcher_class_destroyer` | 265 → 259 | 184 → 178 |
| `mega_cruise_5000` | 2355 → 2341 | 1640 → 1626 |
| `messy_cruise_500` | 1095 → 1071 | 742 → 718 |

The moves are the expected native consequence of removing reverse
pressure-directed legs and reversing the declared sense where the stated
regime required it; no flow magnitude changed.

## Exact-integral material-times

`tools/diag/forced_exhaust_audit.py exact-check`, native lane only
(`contamx_lane: false`), frozen Phase 1 tracer, horizon 12 h, sampling step
1 h, filter efficiency 0.5, natural decay 0. Sources are the expanded endpoint
rooms plus `Engine_Room` where present. Values are exact retained-mass
material-time `exact_h` in hours, before → after; unchanged sources and
sub-1e-6 numerical dust are omitted. Sanitary aggregate material-times are
unchanged on all four hulls.

| Hull | Source | Before | After |
|---|---|---:|---:|
| `expedition_cruise_300` | `Cabin_Deck4_Port` | 0.454953 | 0.454919 |
| `expedition_cruise_300` | `Cabin_Deck4_Stbd` | 0.454953 | 0.454919 |
| `expedition_cruise_300` | `Cabin_Deck5_Port` | 0.455040 | 0.455006 |
| `expedition_cruise_300` | `Cabin_Deck5_Stbd` | 0.455092 | 0.455058 |
| `expedition_cruise_300` | `Casino` | 0.339825 | 0.339728 |
| `expedition_cruise_300` | `Engine_Room` | 0.250901 | 0.250900 |
| `expedition_cruise_300` | `Library` | 0.275841 | 0.275710 |
| `expedition_cruise_300` | `Main_Dining_Room` | 0.430972 | 0.430936 |
| `expedition_cruise_300` | `MedBay` | 0.152798 | 0.136563 |
| `expedition_cruise_300` | `Reception_Lobby` | 0.391074 | 0.390914 |
| `expedition_cruise_300` | `Theater_Lounge` | 0.447613 | 0.447570 |
| `fletcher_class_destroyer` | `Boiler_Room_1` | 0.083057 | 0.083499 |
| `fletcher_class_destroyer` | `Boiler_Room_2` | 0.082449 | 0.082834 |
| `fletcher_class_destroyer` | `Engine_Room_Aft` | 0.116787 | 0.117387 |
| `fletcher_class_destroyer` | `Engine_Room_Fwd` | 0.115299 | 0.115791 |
| `fletcher_class_destroyer` | `Enlisted_Berthing_Aft` | 0.336111 | 0.355430 |
| `fletcher_class_destroyer` | `Enlisted_Berthing_Fwd` | 0.326715 | 0.346469 |
| `fletcher_class_destroyer` | `Mess_Deck` | 0.286961 | 0.307989 |
| `mega_cruise_5000` | `CC_D4_A` | 0.513214 | 0.501509 |
| `mega_cruise_5000` | `CC_D4_F` | 0.513214 | 0.501509 |
| `mega_cruise_5000` | `CC_D4_M` | 0.512494 | 0.500829 |
| `mega_cruise_5000` | `CrewMess_Fwd` | 0.281766 | 0.269500 |
| `mega_cruise_5000` | `Crew_Mess_Main` | 0.314804 | 0.305542 |
| `mega_cruise_5000` | `Engine_Room_Aft` | 0.169617 | 0.166621 |
| `mega_cruise_5000` | `Isolation_Ward` | 0.254608 | 0.253650 |
| `mega_cruise_5000` | `Medical_Center` | 0.265245 | 0.264794 |
| `messy_cruise_500` | `Crew_Mess_Forward` | 0.348612 | 0.343627 |
| `messy_cruise_500` | `Crew_Mess_Main` | 0.374167 | 0.371054 |
| `messy_cruise_500` | `Crew_Quarters_D1` | 0.392661 | 0.390904 |
| `messy_cruise_500` | `Crew_Quarters_D2` | 0.392924 | 0.391197 |
| `messy_cruise_500` | `Crew_Quarters_D3` | 0.393072 | 0.391345 |
| `messy_cruise_500` | `Crew_Quarters_D4` | 0.393043 | 0.391318 |
| `messy_cruise_500` | `Engine_Control_Room` | 0.162653 | 0.096221 |
| `messy_cruise_500` | `Engine_Room_Aft` | 0.101279 | 0.099940 |
| `messy_cruise_500` | `Isolation_Ward` | 0.209671 | 0.206250 |
| `messy_cruise_500` | `Medical_Center` | 0.216530 | 0.214900 |

## PRJ/exporter evidence

No affected hull is byte-pinned by
`tests/test_contamw34_commissioned.py::test_design_mode_is_byte_stable`; that
test pins only `destroyer_baseline` and `expedition_cruise_450`.
`mega_cruise_5000` does carry a committed P-lane `contam/platform.prj` +
`path_map.json`. A scratch regeneration (not committed) emits the authored
one-way `pressure_opening` links through the X1 `plr_bdq` element path and
reverses only the `Medical_Door_Leakage` path-map endpoints, but it also
rewrites unrelated pre-existing one-way pressure-opening elements.
Mirroring the galley precedent, the committed mega PRJ was not regenerated
here.

## Tests

- `tests/test_contam_forced_exhaust_doors.py` pins all seven links'
  endpoints, direction, mechanism, filtration, unchanged magnitudes, and
  description tokens.
- `tests/test_forced_exhaust_audit.py` now asserts the `pressure_directed`
  class has 7 links, all `direction_declared == "oneway"`, zero native
  reverse paths, and no `native_reverse_on_stated_oneway` flag.
- Existing S1 migration invariants pass without exemptions: the row-4
  changes are direction/endpoint authoring with unchanged mechanism/filtered,
  and `_legacy_link` preserves a differing `direction` declaration.
- `schemas/air_flow_paths.schema.json` validation and
  `tools/sanity_checker.py --from-config` pass on the changed platform data.

## Blast radius / non-goals

No `flow_rate_m3h` value changed; no magnitude was proposed or sourced. No
engine/exporter code changed; no epidemiological constant changed; no path
string renamed; row-5 ducted exhaust links are untouched; frozen campaign,
readout, cache, and prior CONTAM ledgers are untouched. Any pre-change
airborne/downstream-map dose figure resting on native reachability through
these seven links is historical on that channel at baseline `01a3482e`;
the pathogen open ledgers carry the withdrawal note.

Status stays `open`: this entry records the landed authoring, native
measurements, structural tests, and exporter inspection, not a campaign
re-measurement.
