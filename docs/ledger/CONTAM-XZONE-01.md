# CONTAM-XZONE-01
**Date:** 2026-11-01
**Commit:** ec3036d9
**Pathogens:** all
**Status:** measured
**Measured at:** ec3036d9

Implements ranked fix #2 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): native room-id cross-zone endpoints silently
dropped.

## Defect

`ContamTransportEngine._get_zone_rooms` resolved a `cross_zone_links`
endpoint by HVAC group id only. An endpoint naming a bare room resolved
to `[]`, so the whole link was silently skipped. The export lane
resolves the same token verbatim — a ContamX zone *is* a room — so the
declared link existed in ContamX and not in the native engine. The same
drop existed in `build_hvac_downstream_map`
(`engines/transmission_core.py`), which resolved endpoints through the
group map alone.

## Fix

- `_get_zone_rooms`: group id → its declared rooms (unchanged); a token
  in `zone_nodes` → `[token]`; anything else raises `ValueError` — the
  fail-loudly leg of the fix, matching the hull_audit / sanity_checker
  contract where an unresolvable endpoint is already an error.
- `_build_cross_zone_paths` unchanged: a known group resolving to zero
  real rooms still degenerates quietly (an empty group is a separate
  declared-data class, `hvac_groups_all_rooms_missing`).
- `build_hvac_downstream_map`: `zone_rooms.get(endpoint, [endpoint])` —
  a non-group endpoint resolves as itself, same convention.

## Measured

Fleet re-audit (`tools/museum_hull_audit.py`, all 80 platforms, no
construction errors): **52 room-id links on 10 hulls** now emit paths —
astoria_ca34 9, chicago_cg11 10, miami_cl89 10, wright_cc2 10,
expedition_cruise_300 5, classic_cruise_1900 2, expedition_cruise_450 2,
spirit_cruise_3000 2, enterprise_constitution_tos 1,
enterprise_galaxy_tng 1. Zero dangling endpoints fleet-wide; the raise
fires nowhere in committed data.

The audit tool's `native_dropped_xzone` classifier is superseded by
`room_id_xzone_endpoints` (links whose endpoints are real rooms, not
groups — the class the fix targets). `audit_q2` catches the engine's
`ValueError` and reports `native_error` + `native: null` so a hard
dangling endpoint is enumerated, not crashed on; `fleet_correlations`
skips such hulls for native-graph metrics.

## Test attribution

- `test_museum_hull_audit.py`: `native_dropped_xzone` →
  `room_id_xzone_endpoints`; toy_broken's `hv_a->phantom_zone` leaves
  the list (phantom is neither group nor room — it is the raise class)
  and makes its `q2["native"]` lane `None` with `native_error`; toy_hull's
  `void` moves from orphan-dead to *reachable* sink (one-way in-link,
  no out leg — the residual class fix #4 targets), sinks `[]`→`["void"]`,
  unreachable `["ghost","void"]`→`["ghost"]`; dead set, dead_frac (0.4),
  and volume share (45/205) unchanged.
- New `TestXzoneEndpointResolution` in `test_py_contam_bridge.py`:
  room-id endpoints emit paths and deliver mass; group↔room mixed
  links expand correctly; an unresolvable endpoint raises `ValueError`.
