# CONTAM-BIDIR-01
**Date:** 2026-11-01
**Commit:** 338b5634
**Pathogens:** all
**Status:** measured
**Measured at:** ec3036d9

Implements ranked fix #4 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): directed vs bidirectional passive links.

## Defect

Native treated every `cross_zone_links` entry as strictly one-way
(from→to). The ContamX export emits a non-ducted link as a `plr_orfc`
orifice — inherently bidirectional, pressure-driven both ways — so the
two engines disagreed on the direction of every passive link. Measured
pre-fix: the battleship class (missouri_bb63, wisconsin_bb64,
new_jersey_bb62, idaho_bb42) ran 96–99% native-unreachable because their
deck networks were authored as one-way chains; fleet native unreachable
zone count was ~600+.

## Fix

New `hvac.passive_link_mode` config key:

- `bidirectional` (default): a passive (non-ducted) `cross_zone_links`
  entry emits paths in both senses at the declared `flow_rate_m3h` —
  the same symmetric convention adjacency edges already used. Matches
  the orifice the link exports as.
- `oneway`: the labelled pre-change baseline (all links from→to only),
  pinned on `docs/contam_engine_divergence.md` §3 whose measured
  battleship/dead-zone numbers were taken under it.

Per-link `direction` (`oneway` | `bidirectional`, new optional field in
`schemas/air_flow_paths.schema.json`) overrides the default for a
genuinely directed link; absent a declaration, `is_hvac_ducted` links
(fan legs) stay one-way — a ducted fan pushes one direction in both
engines.

Applied to `ContamTransportEngine._build_cross_zone_paths` (emits the
reverse room×room pairs) and `build_hvac_downstream_map` in
`transmission_core` (adds reverse edges), sharing the
`cross_zone_link_bidirectional` resolver.

## Measured

Post-fix re-audit (`tools/museum_hull_audit.py`):

| hull | native unreachable before | after |
|---|---|---|
| missouri_bb63 | ~99% of zones | 0 |
| wisconsin_bb64 | ~99% | 0 |
| new_jersey_bb62 | ~99% | 0 |
| idaho_bb42 | ~99% | 0 |
| lexington_cv2 | 0 (post-CONNECT-01) | 0 |
| saratoga_cv3 | 0 (post-CONNECT-01) | 0 |

Fleet total native unreachable: ~600+ → **52**. The residual (galaxy_tng
13, olympia_c6 8, south_dakota 6, davison 4, raven/nields/hunter_killer
3 each, texas/miami 2, west_virginia 1) is the Q1 orphan class —
compartments no declared link reaches in either sense — not a
direction defect.

## Test attribution

`tests/test_py_contam_bridge.py::TestXzoneEndpointResolution::
test_group_endpoint_still_expands` — the passive link under test gained
reverse paths under the new default, so its `direction` is now pinned
`oneway` with a comment attributing the pin to CONTAM-BIDIR-01; the test
continues to assert forward-only group expansion. New
`TestPassiveLinkMode` covers the default-bidirectional pair set,
two-way mass movement, graded flow response, declared-oneway and ducted
honouring, the `oneway` baseline, parser/ctor rejection, and
engine↔downstream-map parity.
