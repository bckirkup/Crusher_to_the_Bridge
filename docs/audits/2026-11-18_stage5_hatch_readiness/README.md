> **Status:** Readiness evidence note for ambient-exposure stage 5. This note authors no openings, platform data, schema fields, engine/exporter behavior, schedules, constants, or campaign artifacts.

# Stage 5 hatch/door readiness — 2026-11-18

Measured on `origin/main` `95b4974bfd980ddc1051ac11fd018ecbf9e3b8b1` after the G4 grouped-weather legs (#1302–#1308), the stage-6 ruling (#1300), and the fiction G4 no-op ruling. Sources: [`../../proposals/ambient_exposure_audit_and_fix_plan.md`](../../proposals/ambient_exposure_audit_and_fix_plan.md), [`../../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../../proposals/contam_field_adjudication_audit_and_fix_plan.md), [`../../ledger/CONTAM-AMBIENT-EXPOSURE-01.md`](../../ledger/CONTAM-AMBIENT-EXPOSURE-01.md), [`../../ledger/CONTAM-AMBIENT-OPENING-SCHEMA-01.md`](../../ledger/CONTAM-AMBIENT-OPENING-SCHEMA-01.md), the stage-4/G4 ledgers under [`../../ledger/README.md`](../../ledger/README.md), `schemas/air_flow_paths.schema.json`, and the committed `data/platforms/*/air_flow_paths.json` / `spatial_layout.json` trees.

## Verdict

**NO-GO for authoring stage-5 legs now.** The gate named by the plan is still open: the governing plan's stage-3 `service_hatch` mechanism decision is an owner decision, and no `CONTAM-FIELD-SERVICE-HATCH-01` ledger entry exists. This note is therefore owner-decision material. A conditional path exists: after the service-hatch ruling and the recipe rulings below, stage 5 can be decomposed into class legs mirroring G4.

## 1. Governing stage-3 service-hatch decision

The ambient plan defers stage 5 "after the stage-3 service-hatch decision of the governing plan" and states that decision is untouched. In [`../../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../../proposals/contam_field_adjudication_audit_and_fix_plan.md) §5, the exact stage row is:

> `| 3 | Service-hatch mechanism decision: keep pressure opening, or declare a fixed/prescribed exchange for service_hatch adjacency on affected hulls | CONTAM-FIELD-SERVICE-HATCH-01 | 1, owner decision | Yes only if owner chooses fixed exchange |`

The same plan's open-decision list asks:

> `4. Should service_hatch remain a pressure opening, or be a declared one-way/fixed exchange? (Stage 3)`

A class-(a) verdict elsewhere in that plan says the choice is "a data/mechanism decision (§5, stage P3), not a transport-kernel fix." As of this note there is no `docs/ledger/CONTAM-FIELD-SERVICE-HATCH-01.md`, so the decision is **unresolved/open**. Stage-5 authoring stays gated on it.

## 2. `ambient_opening_duty`

`ambient_opening_duty` is **not implemented**. The only repository hit is the proposal axis in [`../../proposals/ambient_exposure_audit_and_fix_plan.md`](../../proposals/ambient_exposure_audit_and_fix_plan.md) (~line 283); `schemas/air_flow_paths.schema.json` has no such field, and there is no schema/engine/exporter use under `schemas/`, `engines/`, or `tools/`. The shipped `AmbientOpening` record has `zone`, `type`, `area_m2`, optional `exchange_m3h`, `azimuth_deg`, `wind_speed_m_s`, `schedule`, and `description`; `type` may be `open_deck`, `balcony_door`, `weather_hatch`, `weather_door`, `hangar_door`, or `makeup_louvre`. Native and export lanes currently consume `exchange_m3h`/per-type exchange axis and, on the export lane, `schedule`. If stage 5 wants a duty axis, it needs schema plus both-lane authoring before any platform data leg.

## 3. Fleet inventory

### Active ambient hatch/door openings

Active `ambient_openings` records of type `weather_hatch`, `weather_door`, or `hangar_door` are **zero fleet-wide**. Current active records are `open_deck` and `makeup_louvre` only. The GA-import `contam/openings_draft.json` files are draft ContamW checklists, not active schema records: `astoria_ca34` and `miami_cl89` contain draft `hangar_door` entries with hobbyist `area_m2` 2.0 and `schedule: null`, `status: "draft"`.

### Candidate adjacency edges

The audit's opening-edge definition counts `adjacency` types `hatch`, `service_hatch`, and `hangar_door`. Reproduced on the current tree, those edges remain zone-to-zone. Counts by naval class (cruise and fiction shown separately because stage 5 is naval-by-class):

| class | hulls | `hatch` | `service_hatch` | `hangar_door` | hulls with any candidate edge |
|---|---:|---:|---:|---:|---:|
| battleship | 8 | 0 | 0 | 0 | 0 |
| carrier | 13 | 0 | 0 | 0 | 0 |
| cruiser | 4 | 0 | 0 | 3 | 2 |
| destroyer | 12 | 0 | 3 | 0 | 2 |
| amphibious | 5 | 4 | 2 | 0 | 3 |
| auxiliary | 17 | 4 | 3 | 0 | 5 |
| olympia | 1 | 5 | 0 | 0 | 1 |
| misc | 12 | 20 | 0 | 0 | 1 |
| **naval total** | **72** | **33** | **8** | **3** | **14** |
| cruise | 8 | 0 | 18 | 0 | 8 |
| fiction | 2 | 2 | 2 | 0 | 2 |
| **all platforms** | **82** | **35** | **28** | **3** | **24** |

Per-hull candidate edges: cruiser `astoria_ca34` 2 and `miami_cl89` 1 `hangar_door`; destroyer `destroyer_baseline` 1 and `fletcher_class_destroyer` 2 `service_hatch`; amphibious `lsm_354` 2 `hatch`, `middlesex_lst983` 2 `hatch`, `san_antonio_class_lpd` 2 `service_hatch`; auxiliary `apl_24` 2 `service_hatch`, `legend_class_nsc` 1 `service_hatch`, `gosper_apa170` 1 `hatch`, `jupiter_ac3` 1 `hatch`, `lyon_ap71` 2 `hatch`; olympia `olympia_c6` 5 `hatch`; misc `montana_acr13` 20 `hatch`. The audit totals `hatch` 35 on 9 hulls, `service_hatch` 28 on 15 hulls, and `hangar_door` 3 on 2 hulls reproduce when cruise/fiction are included.

### Ambient-reaching subset

Using the readiness predicate "the hatch/door edge touches a zone that is weather/open and already has an active `ambient_openings` record after stage 4/G4," the current ambient-reaching candidate set is **9 edges on 6 hulls in 4 naval classes**:

| class | hull | type | from → to | ambient-reached endpoint |
|---|---|---|---|---|
| cruiser | `astoria_ca34` | `hangar_door` | `Catapult_Deck` → `Hangar` | `Catapult_Deck` |
| cruiser | `astoria_ca34` | `hangar_door` | `Boat_Deck` → `Hangar` | `Boat_Deck` |
| cruiser | `miami_cl89` | `hangar_door` | `Catapult_Deck` → `Hangar` | `Catapult_Deck` |
| amphibious | `lsm_354` | `hatch` | `Weather_Aft_Super` → `Tank_Well` | `Weather_Aft_Super` |
| amphibious | `middlesex_lst983` | `hatch` | `Tank_Deck` → `Weather_Deck_Amids` | both endpoints have openings |
| amphibious | `middlesex_lst983` | `hatch` | `Tank_Deck_Port` → `Forecastle_Bow` | both endpoints have openings |
| auxiliary | `lyon_ap71` | `hatch` | `Hatch_4_Weather` → `Cargo_Hold_4_Fwd` | `Hatch_4_Weather` |
| auxiliary | `lyon_ap71` | `hatch` | `Hatch_3_Weather` → `Cargo_Hold_3` | `Hatch_3_Weather` |
| misc | `montana_acr13` | `hatch` | `MD_Forecastle_Open` → `GD_Windlass_Engine` | `MD_Forecastle_Open` |

Battleship, carrier, destroyer, and olympia have **no** ambient-reaching `hatch`/`service_hatch`/`hangar_door` edge under this predicate. Most remaining `hatch` edges are interior cargo/machinery/ammunition hatches (notably `montana_acr13` and `olympia_c6`), and all 28 `service_hatch` edges are galley/mess/service-room adjacency edges, not weather-deck doors.

## 4. Proposed class-leg decomposition and owner rulings

Mirroring G4, do **not** author one fleet-wide PR. If the owner rules GO, the natural ledger decomposition is `CONTAM-AMBIENT-HATCH-<CLASS>-01`, naval by class, staged small-to-large:

1. `CONTAM-AMBIENT-HATCH-CRUISER-01` — 3 `hangar_door` edges on `astoria_ca34`/`miami_cl89`; smallest and already has draft GA openings to reconcile.
2. `CONTAM-AMBIENT-HATCH-AMPHIBIOUS-01` — 3 ambient-reaching `hatch` edges on `lsm_354`/`middlesex_lst983`; the 2 `san_antonio_class_lpd` `service_hatch` edges stay with the governing stage-3 decision.
3. `CONTAM-AMBIENT-HATCH-AUXILIARY-01` — 2 ambient-reaching `hatch` edges on `lyon_ap71`; `apl_24`/`legend_class_nsc` `service_hatch` edges and the non-ambient-reaching `gosper_apa170`/`jupiter_ac3` cargo hatches need scope rulings.
4. `CONTAM-AMBIENT-HATCH-MISC-01` — 1 ambient-reaching `hatch` edge on `montana_acr13`; the other 19 `montana_acr13` hatches are interior unless the owner broadens scope.
5. No-op/census-only classes: battleship and carrier have no candidate edges; destroyer has only `service_hatch` edges on `destroyer_baseline`/`fletcher_class_destroyer` (the stage-4 skipped/no-bundle hulls); olympia's 5 hatches do not touch an ambient-opened weather zone under the predicate.

Owner rulings needed before any leg:

- **Gate:** resolve governing stage 3 — keep `service_hatch` as a pressure opening, or declare a fixed/prescribed exchange. This decides whether the 28 `service_hatch` edges are in stage-5 scope at all.
- **Edge-type scope:** count only `hatch` + `hangar_door` (38 edges fleet-wide; 36 naval) or also `service_hatch` (28) and/or the other opening types (`open_deck`, `deck_walkway`, `open_front`, `open_area`)? Recommendation: stage 5 should cover weather `hatch`/`weather_door`/`hangar_door`; leave `service_hatch` to the governing decision and leave deck/walkway/open-front edges to the completed stage-4/G4 weather-opening work unless the owner says otherwise.
- **Ambient-reaching predicate:** author only edges touching an ambient-exposed weather zone with an active opening (9 edges), or all 66 `hatch`/`service_hatch`/`hangar_door` edges? Recommendation: ambient-reaching predicate; interior cargo/machinery hatches stay zone-to-zone.
- **Record-type mapping:** map adjacency `hatch` to schema `weather_hatch` or `weather_door`; map `hangar_door` to `hangar_door`; decide whether `service_hatch` has any ambient representation (schema has no `service_hatch` ambient type).
- **Duty axis:** whether to author `ambient_opening_duty` (schema + native/export lanes) or use only the existing `schedule`/`exchange_m3h` fields. It does not exist today.
- **Duty values and schedules:** if duty/schedule is used, approve values/templates per type. The exporter already has type defaults (doors `DoorTrafficW`, hatches/hangar `HatchOccasionalW`, open deck/louvre always open); owner must say reuse vs author.
- **Area source:** the Grade C deck-face rule was an open-deck assumption. Hatches/doors need clear-opening areas; the only in-tree draft areas are hobbyist 2.0 m² `hangar_door` checklist entries for `astoria_ca34`/`miami_cl89`, not a fleet rule.
- **Exchange magnitude:** choose D5-style ContamX-solved outward flow per opening at declared wind vs a native swept axis; do not fit to an anchor.
- **Directionality:** one-way vs two-way for weather doors/hatches, coordinated with the service-hatch mechanism ruling.
- **No-double-count:** where a hatch/door touches a zone that already has an `open_deck` ambient opening, rule whether the new opening replaces, supplements, or remains a zone-to-zone pressure path.
- **Roster edge cases:** include/exclude `destroyer_baseline` and `fletcher_class_destroyer` (service-hatch edges but no stage-4 openings/committed bundles), `olympia_c6`/`montana_acr13` interior hatches, and confirm cruise/fiction `service_hatch`/`hatch` edges are out of naval stage-5 scope.

## Validation

- Doc-only change: `git diff --name-only origin/main -- data/platforms engines` is empty; `data/platforms/**` and `engines/**` are byte-unchanged.
- Docs convention: this file opens with `> **Status:**` and cites tree evidence rather than proposal-only claims.
- `pre-commit run --files docs/audits/2026-11-18_stage5_hatch_readiness/README.md`.
