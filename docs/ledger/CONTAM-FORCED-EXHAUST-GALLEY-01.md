# CONTAM-FORCED-EXHAUST-GALLEY-01
**Date:** 2026-11-14
**Commit:** ac5cec46
**Pathogens:** all
**Status:** open
**Measured at:** 28f2fc68136f1d0f416ddd0713b8ee958c674fd8

Galley class of `docs/proposals/forced_exhaust_audit_and_fix_plan.md` §5.5
rows 1–3. This entry authors direction/mechanism/filtered/descriptions and
records decisions only; rows 4–5 (doors, ducted exhaust) are later sessions.
The branch commit carrying the data/test changes is `28f2fc68`; measurements
below were taken on that tree.

## Taxonomy reconciliation

The audit names 22 `galley_related` links fleet-wide. Nine map to §5.5 rows
1–3 and are authored here. The remaining galley-named links are outside this
row set and were left untouched: `Dining_to_Galley_Transfer`
(`mega_cruise_5000`, `messy_cruise_500`), `Galley_Service_Door`,
`galley_supply`, `galley_to_troop_mess`, and the ordinary mess/galley
ladder-well/passage links.

`path` strings were not renamed. `path` is consumed by committed
`contam/path_map.json` artifacts and by flow-compare attribution, so the
descriptions carry the "make-up transfer, not recirculated exhaust" wording
instead.

## Decisions

Row 1 — `Dining_Galley_Exhaust` on five cruise hulls. Kept the declared
dining → galley sense, now explicit as `direction: "oneway"`,
`mechanism: "prescribed_flow"`, `filtered: false`, with a description citing
the standards basis and keeping `ASSUMED-GALLEY-TRANSFER-MAGNITUDE` Grade C.
This is the dining → galley make-up transfer induced by galley exhaust, not
recirculated exhaust.

| Platform | Declared link | m³/h |
|---|---|---:|
| `classic_cruise_1900` | `MainDining_L` → `MainGalley` | 12,000 |
| `diamond_princess` | `International` → `MainGalley` | 18,000 |
| `expedition_cruise_450` | `MainDining` → `MainGalley` | 8,000 |
| `greg_mortimer` | `DiningRoom` → `MainGalley` | 5,000 |
| `spirit_cruise_3000` | `MainDining_L` → `MainGalley` | 15,000 |

Row 2 — `Galley_Service_Exhaust` on the two fiction hulls. The declared
sense was `Galley` → `Mess_Hall`, against plan §1.2(2): the served galley is
the lower-pressure exhaust boundary, so transfer air crosses inward only.
Decision: flip the declared sense to mess → galley, `oneway`,
`prescribed_flow`, `filtered: false`; magnitude unchanged.

| Platform | New declared link | m³/h |
|---|---|---:|
| `enterprise_constitution_tos` | `Mess_Hall` → `Galley` | 5,000 |
| `enterprise_galaxy_tng` | `Mess_Hall` → `Galley` | 8,000 |

Row 3 — recirculated galley exhaust. `expedition_cruise_300`
`Galley_Exhaust_Return` (`AHU_3_Service` → `AHU_2_Main`, 600 m³/h) is kept as
a filtered prescribed-flow leg, but the description now states it is partial
return of non-galley service-area air; galley hood exhaust is 100% overboard
and is not recirculated. `san_antonio_class_lpd`
`galley_exhaust_to_mess` (`HVAC_Galley` → `HVAC_Crew_Habitable`, 400 m³/h)
keeps its endpoints and prescribed-flow mechanism, but `filtered` is now
`false`: the declared galley-exhaust recirculation to crew habitable spaces is
judged unintended by the naval analogy to CDC VSP 2025 §33.2.1 / ISO 9943
§4.1, so the leg carries no filtration/recirculation credit. Its magnitude and
HVAC-group membership are unchanged pending the later ducted-exhaust row.

## Standards basis

Clause-level citations only: CDC VSP 2025 Construction Standards §33.2.1–
§33.2.5 and ISO 9943:2009 §4.1, §5.2, Annex A A.2.1/A.2.3/A.3, as registered
in the audit plan. No standard text is committed here. ISO 9943 §5.1's
supply-side heat-load formula remains unused for values; no magnitude was
re-derived or re-chosen from either lane's output.

DP/GM as-built leads are Grade C only: `diamond_princess` (built 2004 MHI
Nagasaki, refurbished February 2019 pre-COVID) and `greg_mortimer` are the
two real vessels eligible for as-built sourcing. Edison reports water-wash
galley hoods (automated grease cleaning; era vendors Halton Marine KWH /
Loipart-Electrolux / MHI-era Japanese subcontractors) and 100% single-pass
outdoor-air supply with direct-to-atmosphere exhaust and zero recirculation.
That corroborates mechanism; it provides no magnitudes.

## Audit and flow-compare measurements

`tools/diag/forced_exhaust_audit.py audit` reconciles 82 platforms / 1,011
links before and after. On the nine galley rows, before this change seven
links reported `native_reverse_on_stated_oneway` with seven native reverse
paths; after this change the galley class reports zero
`native_reverse_on_stated_oneway` flags and zero native reverse paths.
`expedition_cruise_300` and `san_antonio_class_lpd` were already stated
one-way and had no reverse paths; San Antonio changed only `filtered`.

The audit tool's `exporter_*` columns remain the pre-X1 diagnostic
(`exporter_reads_direction: False`), so the non-ducted row-1/2 links still
show `exporter_orifice_on_stated_prescribed_flow` there. That flag is not the
X1 exporter state; exporter evidence is the regenerated PRJ below.

Native flow-compare path counts (`tools.contam_flow_compare.native_links_report`)
move only by removal of the reverse cross-zone leg on each formerly
bidirectional galley link:

| Hull | `n_paths` before → after | `cross_zone` before → after |
|---|---:|---:|
| `classic_cruise_1900` | 736 → 735 | 447 → 446 |
| `diamond_princess` | 1557 → 1556 | 1042 → 1041 |
| `enterprise_constitution_tos` | 465 → 464 | 268 → 267 |
| `enterprise_galaxy_tng` | 1215 → 1214 | 832 → 831 |
| `expedition_cruise_300` | 478 → 478 | 366 → 366 |
| `expedition_cruise_450` | 274 → 273 | 99 → 98 |
| `greg_mortimer` | 287 → 286 | 106 → 105 |
| `san_antonio_class_lpd` | 207 → 207 | 105 → 105 |
| `spirit_cruise_3000` | 1141 → 1140 | 739 → 738 |

## Exact-integral material-times

`tools/diag/forced_exhaust_audit.py exact-check`, native lane only
(`contamx_lane: false`), frozen Phase 1 tracer, horizon 12 h, sampling step
1 h, filter efficiency 0.5, natural decay 0. Sources are the link endpoints
plus `Engine_Room` where present. Values are exact retained-mass material-time
`exact_h` in hours, before → after; unchanged sources are omitted.
`expedition_cruise_300` had no changed sources.

| Hull | Source | Before | After |
|---|---|---:|---:|
| `classic_cruise_1900` | `Engine_Room` | 0.224605 | 0.221824 |
| `classic_cruise_1900` | `MainDining_L` | 0.263489 | 0.245040 |
| `classic_cruise_1900` | `MainGalley` | 0.249300 | 0.221505 |
| `diamond_princess` | `Engine_Room` | 0.227854 | 0.221021 |
| `diamond_princess` | `International` | 0.342953 | 0.287430 |
| `diamond_princess` | `MainGalley` | 0.305835 | 0.219613 |
| `enterprise_constitution_tos` | `Galley` | 0.255057 | 0.205550 |
| `enterprise_constitution_tos` | `Mess_Hall` | 0.266383 | 0.226743 |
| `enterprise_galaxy_tng` | `Galley` | 0.218969 | 0.213539 |
| `enterprise_galaxy_tng` | `Mess_Hall` | 0.219910 | 0.215565 |
| `expedition_cruise_450` | `Engine_Room` | 0.225925 | 0.219955 |
| `expedition_cruise_450` | `MainDining` | 0.317645 | 0.265323 |
| `expedition_cruise_450` | `MainGalley` | 0.285509 | 0.216494 |
| `greg_mortimer` | `DiningRoom` | 0.301874 | 0.235833 |
| `greg_mortimer` | `Engine_Room` | 0.217380 | 0.209479 |
| `greg_mortimer` | `MainGalley` | 0.275720 | 0.194185 |
| `san_antonio_class_lpd` | `Crew_Mess` | 0.259407 | 0.259543 |
| `san_antonio_class_lpd` | `Galley` | 0.193990 | 0.225195 |
| `san_antonio_class_lpd` | `Passageway_Main` | 0.268249 | 0.268460 |
| `san_antonio_class_lpd` | `Ship_Enlisted_Berthing` | 0.293304 | 0.293339 |
| `spirit_cruise_3000` | `Engine_Room` | 0.225529 | 0.221820 |
| `spirit_cruise_3000` | `MainDining_L` | 0.275808 | 0.250527 |
| `spirit_cruise_3000` | `MainGalley` | 0.257699 | 0.221286 |

The moves are the expected native consequence of removing reverse galley
legs and, on San Antonio, removing recirculation filtration credit; they are
not the D1 sanitary-pin identity move. The frozen Phase 1/Phase 2 E-lane
caches are unchanged by this data authoring.

## PRJ/exporter evidence

Only `data/platforms/expedition_cruise_450/contam/platform.prj` was
regenerated: it is the only affected hull whose committed design-mode PRJ is
byte-pinned by `tests/test_contamw34_commissioned.py::test_design_mode_is_byte_stable`
(the other pinned hull, `destroyer_baseline`, has no galley row). The diff is
the expected galley element change from the X1 exporter semantics
(`plr_orfc` bidirectional pressure opening → `fan_cvf` prescribed flow);
`path_map.json` is unchanged. Other committed P-lane PRJs were not
regenerated because doing so surfaced unrelated pre-existing X1 catch-up on
non-galley one-way pressure-opening links.

`tools/contam_commissioned_check.py` passed locally on the regenerated
`expedition_cruise_450` PRJ with the repo ContamX binary inside the
commissioned terminal tolerance and reported no reversed prescribed
cross-zone leg.

## Tests

- `tests/test_contam_forced_exhaust_galley.py` pins the nine authored links:
  declared sense, `oneway`/`prescribed_flow`/`filtered`, positive unchanged
  `flow_rate_m3h`, and the standards/Grade-C description tokens.
- `tests/test_forced_exhaust_audit.py` asserts the galley class reports zero
  `native_reverse_on_stated_oneway`.
- `tests/test_contam_s1_migration.py` carries post-S1 exemptions for the
  eight links whose resolved semantics intentionally differ from the S1
  migration alias; `expedition_cruise_300` is not exempt because only its
  description changed.

## Status and blast radius

Status stays `open`: this entry records the landed authoring, native
measurements, and structural tests, not a campaign re-measurement. No
`flow_rate_m3h` value changed; no magnitude was re-derived; no engine or
exporter code changed; no epidemiological constant changed; frozen campaign,
readout, cache, and prior CONTAM ledgers are untouched. Any pre-change dose
figure resting on native downstream-map reachability through these galley
links is historical on that channel at baseline `ac5cec46`; the pathogen open
ledgers carry the withdrawal notes.
