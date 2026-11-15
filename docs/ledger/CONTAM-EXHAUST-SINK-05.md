# CONTAM-EXHAUST-SINK-05
**Date:** 2026-11-15
**Commit:** ecb7616d
**Pathogens:** all
**Status:** open
**Measured at:** ecb7616d

Stage 6 row 2 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §3.2 galley make-up gap, §6.1). This authors the missing galley hood/once-through exhaust boundary for the seven hulls whose #1219 galley make-up links push 5,000–18,000 m³/h into galleys served by recirculating HVAC. Each affected hull gets one new `cross_zone_links` entry, `path: "Galley_Hood_Exhaust"`, using the stage-3 `"to": "ambient"` sink endpoint (`direction: "oneway"`, `mechanism: "prescribed_flow"`, `filtered: false`, `is_hvac_ducted: true`). The existing make-up links are unchanged; no make-up companion is authored because the make-up side already exists. No engine, exporter, schema, recipe, or generator code changed; no `flow_rate_m3h` value changed.

Standards basis is clause-citation only: ISO 9943:2009 §4.1 (separate supply/exhaust, no recirculation), §5.2 (exhaust greater than supply, but no magnitude formula), A.2.1 (hoods/grease), and A.2.3 (galley lower pressure than accommodation); CDC VSP 2025 §33.2.1–§33.2.2; Diamond Princess as-built Grade-C leads corroborate the once-through mechanism only and supply no magnitudes.

Magnitude decision: the sink `flow_rate_m3h` equals the paired make-up-transfer magnitude on each hull and remains Grade C. No retrieved source gives a separate galley exhaust magnitude and ISO 9943 §5.2 gives no formula, so no margin was invented; if a later source forces a distinct exhaust magnitude, that is a STOP/re-port condition, not a silent edit.

| Hull | Existing make-up link (unchanged) | New sink | From | m³/h |
|---|---|---|---|---:|
| `classic_cruise_1900` | `Dining_Galley_Exhaust` `MainDining_L` → `MainGalley` | `Galley_Hood_Exhaust` `MainGalley` → `ambient` | `MainGalley` | 12000 |
| `diamond_princess` | `Dining_Galley_Exhaust` `International` → `MainGalley` | `Galley_Hood_Exhaust` `MainGalley` → `ambient` | `MainGalley` | 18000 |
| `expedition_cruise_450` | `Dining_Galley_Exhaust` `MainDining` → `MainGalley` | `Galley_Hood_Exhaust` `MainGalley` → `ambient` | `MainGalley` | 8000 |
| `greg_mortimer` | `Dining_Galley_Exhaust` `DiningRoom` → `MainGalley` | `Galley_Hood_Exhaust` `MainGalley` → `ambient` | `MainGalley` | 5000 |
| `spirit_cruise_3000` | `Dining_Galley_Exhaust` `MainDining_L` → `MainGalley` | `Galley_Hood_Exhaust` `MainGalley` → `ambient` | `MainGalley` | 15000 |
| `enterprise_constitution_tos` | `Galley_Service_Exhaust` `Mess_Hall` → `Galley` | `Galley_Hood_Exhaust` `Galley` → `ambient` | `Galley` | 5000 |
| `enterprise_galaxy_tng` | `Galley_Service_Exhaust` `Mess_Hall` → `Galley` | `Galley_Hood_Exhaust` `Galley` → `ambient` | `Galley` | 8000 |

## Exact-integral material-times

Native `ContamTransportEngine` material-time under the frozen Phase 1 tracer conditions (12 h horizon, 1 h sampling step, filter efficiency 0.5, natural decay 0), before → after, for a unit pulse in the galley boundary room. Values are exact retained-mass material-time hours per unit release; the change column is after/before − 1.

| Hull | Boundary room | Whole-hull before → after | Change |
|---|---|---:|---:|
| `classic_cruise_1900` | `MainGalley` | 0.221505318 → 0.074861503 | -66.20% |
| `diamond_princess` | `MainGalley` | 0.219613241 → 0.066081688 | -69.91% |
| `expedition_cruise_450` | `MainGalley` | 0.216494362 → 0.068781177 | -68.23% |
| `greg_mortimer` | `MainGalley` | 0.194185065 → 0.047160166 | -75.71% |
| `spirit_cruise_3000` | `MainGalley` | 0.221286238 → 0.073499015 | -66.79% |
| `enterprise_constitution_tos` | `Galley` | 0.205550270 → 0.038269925 | -81.38% |
| `enterprise_galaxy_tng` | `Galley` | 0.213539016 → 0.031548325 | -85.23% |

Measured vs expected: the audit row's regime claim is that the galley boundary needs an independent once-through exhaust sink, not merely a make-up transfer into a recirculating HVAC group. The new sink preserves the declared make-up magnitude as the exhaust boundary while removing retained mass from the ship domain: whole-hull material-time fell 66–85% on the seven affected hulls. `tools/diag/forced_exhaust_audit.py exact-check --no-contamx` was run before and after for all seven hulls (`telemetry_buffer/forced_exhaust_audit/forced_exhaust_exact_integral_check_{pre,post}_galley_hood.json` locally; not committed). Fleet audit re-run after the data change reports 82 platforms / 1,018 `cross_zone_links`, `direction_present=1018`, `reconciled=True` (1,011 links before the seven new sink links).

## PRJ/path_map/export checks

All seven affected hulls have committed Contam bundles, so each was re-synced with `scripts/generate_platform_contam_prj.py --platform <hull>`; `contam/platform.prj` and `contam/path_map.json` were regenerated together from committed hull JSON. Path-map counts move by exactly one sink entry per hull:

| Hull | path_map entries before → after |
|---|---:|
| `classic_cruise_1900` | 835 → 836 |
| `diamond_princess` | 1770 → 1771 |
| `expedition_cruise_450` | 343 → 344 |
| `greg_mortimer` | 355 → 356 |
| `spirit_cruise_3000` | 1302 → 1303 |
| `enterprise_constitution_tos` | 567 → 568 |
| `enterprise_galaxy_tng` | 1429 → 1430 |

Each added path-map entry is the single-room expansion of `Galley_Hood_Exhaust`: `sink: true`, `to_zone: "ambient"`, `filtered: false`, `is_hvac_ducted: true`, and flow equal to the link magnitude. `tests/test_json_schema_validation.py` passes (220 tests). `tools/contam_commissioned_check.py --platform <hull>` passes with the local ContamX binary for all seven regenerated bundles: every commissioned terminal solved inside 5% of declared.

## Phase 2 cruise-contrasts versioning

The cruise path-map regenerations move the Phase 2 `_02` hull panel facts that `design/build.py` recomputes from live platform JSON: `expedition_cruise_450` 343 → 344, `classic_cruise_1900` 835 → 836, and `spirit_cruise_3000` 1302 → 1303 entries; the `_02` panel total is now 5,056 (`mega_cruise_5000` remains 2,573). Per the versioning pattern, the frozen `_01` artifacts (`design/phase2_cruise_contrasts_design.json`, `source_pools.json`, `campaign.json`, `_v1` caches, committed readouts, prior ledgers) are untouched; only `design/phase2_cruise_contrasts_design_v2.json` was rebuilt in place. `source_pools_v2.json` and `campaign_v2.json` are unchanged, no `_v2` field cache is produced, nothing is uploaded to S3, and no Batch campaign is submitted in this PR.

## Tests

- `tests/test_contam_exhaust_sink.py` now pins seven committed-platform `Galley_Hood_Exhaust` ambient sinks at the paired make-up magnitudes.
- `tests/test_contam_forced_exhaust_galley.py` adds `test_galley_hood_sinks_are_once_through_ambient_companions`, asserting the ambient endpoint, one-way prescribed-flow/no-filtration contract, unchanged flow equality with the paired make-up link, and the clause-only description tokens.
- `tests/test_contam_pathmap_filtered.py` expects one divergent filtered/path-map entry per affected hull for `Galley_Hood_Exhaust`.
- `tests/test_contam_s1_migration.py` classifies the seven links as post-S1 authored exhaust sinks.
- `tests/test_enterprise_platforms.py` endpoint referential-integrity now accepts the reserved `ambient` token only as a `to` endpoint (never as `from`) for the two Enterprise hulls.
- Targeted CONTAM/audit tests pass: `tests/test_contam_exhaust_sink.py`, `tests/test_contam_pathmap_filtered.py`, `tests/test_contam_forced_exhaust_galley.py`, and `tests/test_forced_exhaust_audit.py` — 51 passed.
- `tests/test_contam_phase2_cruise_contrasts_campaign.py` passes with `_01` frozen and `_02` pinned to the rebuilt builder output — 57 passed.
- `tests/test_enterprise_platforms.py` — 27 passed; `tests/test_json_schema_validation.py` — 220 passed.
- Full fast tier `python -m pytest tests/ -m 'not slow' -n auto -q` — 8,510 passed, 9 skipped.
- `ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311` on the changed Python tests passes; `scripts/sonar_guard.py` on the changed Python tests passes; pre-commit on the changed files passes.
- `tools/sanity_checker.py --from-config` passes with two pre-existing TAT warnings for unknown instrument keys `clinical_multiplex_panel` and `clinical_impression`.

## Status and blast radius

Status stays `open`: this entry records the landed authoring and native/export measurements, not a campaign re-measurement. No `flow_rate_m3h` value changed; no magnitude was re-derived; no make-up link was authored; no engine/exporter/schema code changed; no epidemiological constant changed; frozen campaign directories, S3 prefixes, `_v1` caches, committed readouts, and prior CONTAM ledgers are untouched. Behavior does change for future runs on the seven affected hulls; the matching open-ledger notes are added in the pathogen homes.
