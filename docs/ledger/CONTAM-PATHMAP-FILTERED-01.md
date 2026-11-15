# CONTAM-PATHMAP-FILTERED-01
**Date:** 2026-11-15
**Commit:** 893cc54d3dcc91b6a8dd7df8054b1c0e77c01f9e
**Pathogens:** all
**Status:** open

Stage 2 of the exhaust-sink rollout (`docs/proposals/exhaust_sink_audit_and_fix_plan.md` §6.1). This is the P-min path, proposal §4.2: the ContamX-field interface now carries link filtration without rewriting every committed path_map.

What changed:

- `tools/contamw34_prj.py` writes `filtered` on a cross-zone path_map entry only when the resolved link semantics diverge from the deprecated `is_hvac_ducted` alias. Absent `filtered` keeps the old alias meaning, so existing caches and committed path_maps read identically.
- The same exporter now raises `ValueError` for an unresolved cross-zone endpoint instead of skipping the link, matching the native engine's fail-loud endpoint resolution.
- `engines/contamx_transport.py` resolves lane filtration as `entry.get("filtered", is_hvac_ducted)` and passes it into `ContamAirflowPath`, so the ContamX lane agrees with native transport on divergent links.
- `tools/museum_hull_audit.py` treats a fresh-export `ValueError` like the native engine failure: `contamx_export` is null with `contamx_export_error`, and correlation/table formatting skips unavailable export metrics.
- `schemas/contam_path_map.schema.json` pins the path_map contract: the seven existing keys are required; `filtered`, `sink`, and commissioned-mode `declared_flow_m3h` are optional.

Verification: fresh exports for `legend_class_nsc` and `san_antonio_class_lpd` emit nine divergent rows total (`medical_exhaust` ×3 on legend; `medical_exhaust` ×3 and `galley_exhaust_to_mess` ×3 on San Antonio), each with `is_hvac_ducted: true` and `filtered: false`, in both hobbyist modes. `tests/test_contam_pathmap_filtered.py` proves JSON round-trip, native-vs-lane filtration agreement on those rows, absent-key alias compatibility, the schema contract, and the unresolved-endpoint raise. No committed `path_map.json` was regenerated: proposal §4.2 records 0 of 77 committed path_maps carrying a divergent link, and this change has no `data/` diff.

Field-cache versioning follows §4.4: `_v1` caches stay frozen, `_v2` schema/design ids remain reserved and unproduced, and `filtered` joins the `_v2` definition. No campaign hull set in the frozen Phase 1/2 designs contains a divergent link or sink, so no `_v1` cache is rewritten here.

This does not re-point the three authored links (stage 4), add sink endpoints (stage 3), or resync stale bundles (stage 5). No existing ledger or frozen artifact is edited, and no recorded measurement is invalidated.
