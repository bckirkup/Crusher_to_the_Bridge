# CONTAM-EXHAUST-SINK-02
**Date:** 2026-11-15
**Commit:** c11dbe66c20a0d4b9aadb209e0570e714fc5a572
**Pathogens:** all
**Status:** open
**Measured at:** c11dbe66c20a0d4b9aadb209e0570e714fc5a572

Stage 3 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §3.4, Path S). This lands the explicit sink-endpoint machinery only: no platform link is re-pointed, no make-up link is authored, and no runtime baseline switch is added. Stage 4 owns the three data changes.

What changed:

- `schemas/air_flow_paths.schema.json` accepts the reserved cross-zone destination `"ambient"` only with explicit `direction: "oneway"`, `mechanism: "prescribed_flow"`, and `filtered: false`; `"ambient"` is not a valid source.
- `tools/sanity_checker.py` carries the S1 `mechanism`/`filtered` fields on `CrossZoneLink`, exempts `to: "ambient"` from ordinary endpoint resolution, and rejects sink links whose resolved semantics are not one-way, prescribed-flow, and unfiltered.
- `engines/py_contam_bridge.py` expands a sink link to one path per source room at `flow / n_source_rooms`; the native operator adds source outflow and no destination arrival, so mass leaves the ship/domain instead of entering a berthing or mess room.
- `tools/contamw34_prj.py` exports each sink source room as a `fan_cvf` path to ContamW ambient node `-1`, records `sink: true` in `path_map`, rejects invalid sink semantics and `from: "ambient"`, and `path_map_from_prj` classifies fan-to-ambient paths as `exhaust_sink` rather than ordinary `envelope_leak`.
- `engines/contamx_transport.py` treats a positive solved flow on a `sink` / `exhaust_sink` path_map entry as outflow-only from the source zone.
- `schemas/contam_path_map.schema.json` documents the now-active `sink` marker.
- `tests/test_contam_exhaust_sink.py` covers schema and sanity fail-loud behavior, per-source-room native expansion, mass removal without arrival, graded flow response, operator column behavior, exporter/path_map round-trip in both hobbyist modes, ContamX-lane parity, nonpositive lane-flow rejection, and committed-platform inertness.

Inertness verification, measured against base `c11dbe66` with no `data/` diff:

- `tools/diag/forced_exhaust_audit.py exact-check --no-contamx` produced identical pre/post JSON documents for all 82 platforms.
- A fresh audit re-run reconciles 82 platforms and 1,011 `cross_zone_links`.
- Fresh `export_prj_with_path_map` comparison covered all 82 platforms in four modes (default, commissioned, hobbyist, hobbyist+commissioned): 328 records, with identical PRJ and canonical path_map SHA-256 hashes and zero export errors.
- `path_map_from_prj` comparison covered all 77 committed `contam/platform.prj` bundles: canonical path_map SHA-256 hashes are identical, with zero sink entries before or after.
- `tests/test_contam_exhaust_sink.py`: 31 passed; neighboring CONTAM/sanity suites: 193 passed.

Make-up-link finding (analysis only; no link changed):

The present sense of the three stage-4 links contradicts their stated negative-pressure / once-through regime, so this is physically incoherent rather than a description-only fix:

- `legend_class_nsc` `medical_exhaust`: `HVAC_Medical` (`Sickbay`) → `HVAC_Enlisted_Fwd` (`CPO_Berthing`, `Enlisted_Berthing_Fwd`, `Crew_Mess`), 100 m³/h, description says sickbay remains negative-pressure and the stream is once-through independent exhaust.
- `san_antonio_class_lpd` `medical_exhaust`: `HVAC_Medical` (`Medical_Ward`) → `HVAC_Crew_Habitable` (`Ship_Enlisted_Berthing`, `Crew_Mess`, `Passageway_Main`), 200 m³/h, same once-through / negative-pressure description.
- `san_antonio_class_lpd` `galley_exhaust_to_mess`: `HVAC_Galley` (`Galley`) → `HVAC_Crew_Habitable`, 400 m³/h, description says the recirculation is unintended and hood exhaust remains topside.

The proposal also records a related make-up-side gap for later work: seven galley make-up links push 5,000–18,000 m³/h into galley HVAC groups that still recirculate (OA 0.15–0.2 on the three hulls checked), while their descriptions claim independent exhaust to atmosphere. No make-up link is authored in this stage.

No frozen artifact is touched: campaign directories, S3 prefixes, `_v1` caches, committed readouts, and existing ledgers are unchanged. No recorded measurement is invalidated because the machinery is inert until a link declares `"to": "ambient"`.
