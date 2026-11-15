# CONTAM-EXHAUST-SINK-03
**Date:** 2026-11-15
**Commit:** a0dad9ec
**Pathogens:** all
**Status:** open
**Measured at:** a0dad9ec

Stage 4 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §3.4 Path S, §6.1). This re-points the three audited links to the stage-3 `"to": "ambient"` sink endpoint using the existing schema/native/exporter/lane machinery. `flow_rate_m3h` and every other magnitude are unchanged; no make-up link is authored; no engine, exporter, or schema code changed. The branch commit carrying the data/test changes is `a0dad9ec`; measurements below were taken on that tree against baseline `0b58f78d`.

Links re-pointed:

| Hull | `path` | Before | After | m³/h |
|---|---|---|---|---:|
| `legend_class_nsc` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Enlisted_Fwd` | `HVAC_Medical` → `ambient` | 100 |
| `san_antonio_class_lpd` | `medical_exhaust` | `HVAC_Medical` → `HVAC_Crew_Habitable` | `HVAC_Medical` → `ambient` | 200 |
| `san_antonio_class_lpd` | `galley_exhaust_to_mess` | `HVAC_Galley` → `HVAC_Crew_Habitable` | `HVAC_Galley` → `ambient` | 400 |

Descriptions now state the ambient sink / material leaving the ship-domain; the galley description still records that the former crew-habitable recirculation was judged unintended and that hood exhaust remains topside.

## Exact-integral material-times

`tools/diag/forced_exhaust_audit.py exact-check --no-contamx`, frozen Phase 1 tracer conditions (12 h horizon, 1 h sampling step, filter efficiency 0.5, natural decay 0), native lane, before → after. Destination rooms are the former HVAC-group room sets from plan §2.1. Values are exact retained-mass material-time hours per unit release; ratios are before/after.

| Hull | Link | Source room before → after | Destination rooms before → after | Whole hull before → after | Destination reduction |
|---|---|---:|---:|---:|---:|
| `legend_class_nsc` | `medical_exhaust` | 0.140994 → 0.140947 | 0.073125 → 0.001303 | 0.240702 → 0.149994 | 56.1× |
| `san_antonio_class_lpd` | `medical_exhaust` | 0.189663 → 0.189589 | 0.032918 → 0.002461 | 0.229745 → 0.192657 | 13.4× |
| `san_antonio_class_lpd` | `galley_exhaust_to_mess` | 0.114029 → 0.113923 | 0.055105 → 0.003865 | 0.225209 → 0.162814 | 14.3× |

Measured vs predicted: the audit's sink rows predicted destination material-times of 0.001304 / 0.002465 / 0.003868 and whole-hull values of 0.149994 / 0.192662 / 0.162817 (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §2.1). The measured values match those predictions to the reported precision, and the destination-room reductions (56.1×, 13.4×, 14.3×) sit inside the predicted 13–56× band. Source-room material-time is essentially unchanged (≤0.001×), as expected for an outflow-only endpoint.

Fleet audit re-run after the data change reconciles 82 platforms / 1,011 `cross_zone_links` (`reconciled=True`).

## PRJ/path_map/export checks

Fresh `tools.contam_prj_bridge.export_platform_to_prj` exports for both hulls in four modes (default, commissioned, hobbyist, hobbyist+commissioned) all succeed. Path counts are unchanged at 223 (`legend_class_nsc`) and 252 (`san_antonio_class_lpd`); each export carries exactly the expected authored sink entries with `sink: true`, `to_zone: "ambient"`, `filtered: false`, and `is_hvac_ducted: true` — one for Legend (`medical_exhaust` `Sickbay` → `ambient`) and two for San Antonio (`galley_exhaust_to_mess` `Galley` → `ambient`, `medical_exhaust` `Medical_Ward` → `ambient`). `path_map_from_prj` round-trips those fan-to-ambient paths as `exhaust_sink` in all four modes.

`tools/contam_commissioned_check.py --platform legend_class_nsc --platform san_antonio_class_lpd` passes with the local ContamX binary. The commissioned solve reproduces the new sink legs at the declared magnitudes: Legend `medical_exhaust` solved 100.000001 m³/h, San Antonio `galley_exhaust_to_mess` solved 400.000005 m³/h, and San Antonio `medical_exhaust` solved 200.000002 m³/h.

## Tests

- `tests/test_contam_exhaust_sink.py` now pins the committed-platform contract as exactly the three authored ambient sinks (platform, path, source HVAC group, and unchanged flow), replacing the stage-3 zero-ambient inertness check.
- `tests/test_contam_pathmap_filtered.py` expected counts move from three destination-room expansions per re-pointed link to one source-room sink expansion per link; the absent-`filtered` ducted-alias check now targets a non-sink `galley_supply` entry because sink entries intentionally carry `filtered: false`.
- `schemas/air_flow_paths.schema.json` validation passed for both touched platform files; targeted CONTAM/path-map tests pass (39 passed).

## Status and blast radius

Status stays `open`: this entry records the landed authoring and native/export measurements, not a campaign re-measurement. No `flow_rate_m3h` value changed; no magnitude was re-derived; no make-up link was authored; no engine/exporter/schema code changed; no epidemiological constant changed; frozen campaign directories, S3 prefixes, `_v1` caches, committed readouts, and prior CONTAM ledgers are untouched. Neither affected hull has a committed contam bundle, and no frozen study hull is affected, but behavior does change for future runs on `legend_class_nsc` and `san_antonio_class_lpd`; the matching open-ledger notes are added in the pathogen homes.
