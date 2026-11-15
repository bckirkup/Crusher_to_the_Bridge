# CONTAM-EXHAUST-SINK-04
**Date:** 2026-11-15
**Commit:** 2ef624db
**Pathogens:** all
**Status:** open
**Measured at:** 2ef624db

Stage 6 row 1 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §3.2 `Dining_to_Galley_Transfer`, §6.1). This re-points the two audited dining-to-galley transfer links to the stage-3 `"to": "ambient"` sink endpoint using the existing schema/native/exporter/lane machinery. `flow_rate_m3h` and every other magnitude are unchanged; no make-up link is authored; no engine, exporter, or schema code changed. The branch commit carrying the data/test/bundle changes is `2ef624db`; measurements below were taken on that tree against baseline `c5640031`.

Links re-pointed:

| Hull | `path` | Before | After | m³/h |
|---|---|---|---|---:|
| `mega_cruise_5000` | `Dining_to_Galley_Transfer` | `AHU_Network_Aft_Dining_Rec` → `AHU_Dedicated_Service_Exhaust` | `AHU_Network_Aft_Dining_Rec` → `ambient` | 15000 |
| `messy_cruise_500` | `Dining_to_Galley_Transfer` | `AHU_Network_Aft_Dining_Rec` → `AHU_Dedicated_Service_Exhaust` | `AHU_Network_Aft_Dining_Rec` → `ambient` | 15000 |

Descriptions now state the ambient sink / material leaving the ship-domain while preserving the overboard-odor regime the prior text already claimed. Galley hood sinks remain a separate later row and were not touched.

## Exact-integral material-times

Native `ContamTransportEngine` material-time under the frozen Phase 1 tracer conditions (12 h horizon, 1 h sampling step, filter efficiency 0.5, natural decay 0), before → after. Because the declared source is a 10-room HVAC group, the release was distributed uniformly across the ten declared source rooms and material-time was summed over the ten source rooms, the six former `AHU_Dedicated_Service_Exhaust` destination rooms, and the whole hull. Values are exact retained-mass material-time hours per unit release; ratios are before/after.

| Hull | Source rooms before → after | Destination rooms before → after | Whole hull before → after | Destination reduction |
|---|---:|---:|---:|---:|
| `mega_cruise_5000` | 0.245666514 → 0.245661229 | 0.011681271 → 0.000044918 | 0.268666196 → 0.256901371 | 260.1× |
| `messy_cruise_500` | 0.229791189 → 0.229786717 | 0.010396646 → 0.000039166 | 0.251050611 → 0.240579078 | 265.5× |

Measured vs expected: the audit row's regime claim is that this leg is an overboard exhaust, not a filtered transfer into `AHU_Dedicated_Service_Exhaust`. The re-point preserves the declared 15,000 m³/h out of the source group while removing arrival in the former destination rooms: destination material-time fell by ~260×/~266×, source-room material-time moved only in the fifth decimal (~0.002%), and whole-hull retained mass fell ~4.4%/~4.2% because the former destination no longer receives the leg. `tools/diag/forced_exhaust_audit.py exact-check --no-contamx` was run for both hulls before and after with the ten declared source rooms per hull (`telemetry_buffer/forced_exhaust_audit/forced_exhaust_exact_integral_check_dining_sink_{baseline,after}.json` locally; not committed). Fleet audit re-run after the data change reconciles 82 platforms / 1,011 `cross_zone_links` (`reconciled=True`).

## PRJ/path_map/export checks

`messy_cruise_500` has no committed Contam bundle, so only `mega_cruise_5000` was re-synced. `scripts/generate_platform_contam_prj.py --platform mega_cruise_5000` regenerated `data/platforms/mega_cruise_5000/contam/platform.prj` and `path_map.json` together from committed hull JSON. The path map moves from 2,623 to 2,573 entries: the former 60 room×room Dining_to_Galley_Transfer expansions are replaced by 10 source-room ambient-sink entries (`sink: true`, `to_zone: "ambient"`, `filtered: false`, `is_hvac_ducted: true`, 1,500 m³/h per source room). `check-jsonschema` passed for both touched `air_flow_paths.json` files and the regenerated `path_map.json`.

`tools/contam_commissioned_check.py --platform mega_cruise_5000` passes with the local ContamX binary: 2,573 paths, 187 declared rooms, every commissioned terminal solved inside 5% of declared.

## Phase 2 cruise-contrasts versioning

The mega path-map regeneration moves `mega_cruise_5000` from 2,623 to 2,573 entries, a hull-panel fact the frozen Phase 2 `_01` builder recomputes from live platform JSON. Per the owner decision, `_01` remains the byte-frozen as-run record: `design/phase2_cruise_contrasts_design.json`, `source_pools.json`, `campaign.json`, the `_v1` field caches, committed readouts, and prior ledgers are untouched. This change adds the `_v2` successor artifacts `design/phase2_cruise_contrasts_design_v2.json`, `source_pools_v2.json`, and `campaign_v2.json` with design id `contam_phase2_cruise_contrasts_02`, field-cache schema `contam_phase2_cruise_contrasts_field_cache_v2`, S3 prefix `campaign/contam_phase2_cruise_contrasts_02/`, and `mega_cruise_5000.path_map_entries = 2573` (panel total 5,053 versus the frozen 5,103). `campaign_v2.json` is the successor spec payload only: no `_v2` field cache is produced, nothing is uploaded to S3, and no Batch campaign is submitted in this PR. `tests/test_contam_phase2_cruise_contrasts_campaign.py` keeps the `_01` fixtures frozen and pins the `_v2` artifacts to the current builder output.

## Tests

- `tests/test_contam_exhaust_sink.py` now pins five committed-platform ambient sinks, adding `mega_cruise_5000` and `messy_cruise_500` `Dining_to_Galley_Transfer` at unchanged 15,000 m³/h.
- `tests/test_contam_pathmap_filtered.py` expects ten divergent filtered/path-map entries per affected hull for `Dining_to_Galley_Transfer`.
- `tests/test_contam_forced_exhaust_ducted.py` adds both links to the `filtered: false` row-5 table and pins the ambient-sink endpoint, unchanged magnitude, and overboard/no-credit description tokens.
- Targeted CONTAM/audit tests pass: `tests/test_contam_exhaust_sink.py`, `tests/test_contam_pathmap_filtered.py`, `tests/test_contam_forced_exhaust_ducted.py`, and `tests/test_forced_exhaust_audit.py` — 51 passed.
- `tests/test_contam_phase2_cruise_contrasts_campaign.py` passes with the `_01` design frozen and the `_v2` successor pinned to the regenerated builder output — 57 passed.

## Status and blast radius

Status stays `open`: this entry records the landed authoring and native/export measurements, not a campaign re-measurement. No `flow_rate_m3h` value changed; no magnitude was re-derived; no make-up link was authored; no engine/exporter/schema code changed; no epidemiological constant changed; frozen campaign directories, S3 prefixes, `_v1` caches, committed readouts, and prior CONTAM ledgers are untouched. `mega_cruise_5000` has a committed Contam bundle and it was regenerated in this change; `messy_cruise_500` has no committed bundle. Behavior does change for future runs on both hulls; the matching open-ledger notes are added in the pathogen homes.
