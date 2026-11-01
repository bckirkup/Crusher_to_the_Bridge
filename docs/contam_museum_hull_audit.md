# Museum/GA hull divergence audit

**Status:** measured — audit run 2026-11-01 on the working tree at
`d74365ba` plus this change's tool, by `tools/museum_hull_audit.py`
(mechanical; no eyeballing). Inputs: the committed
`data/platforms/<id>/{spatial_layout,air_flow_paths}.json`, committed
`contam/platform.prj` where present, `systems_notes.json` /
`import_provenance.json` provenance, and the committed sweep readout
[contam_fleet_compare_table.md](contam_fleet_compare_table.md) (`mean L1`).
Ledger entry: `docs/ledger/CONTAM-MUSEUM-01.md`. This document classifies
only — no geometry was changed.

## What this is

The fleet-compare sweep (CONTAM-FLEET-01) left a divergence tail dominated
by GA-imported museum hulls. This audit decomposes each hull into three
mechanical checks:

- **Q1 — missing-geometry mistakes**: hvac `rooms` / adjacency /
  cross-zone references to zone ids that do not exist; zones with volume
  but zero airflow incidence; hvac groups whose rooms are all missing;
  systems-notes and import-digest drift; committed-prj zone/volume drift
  vs the JSON.
- **Q2 — dead-end topology**: per-engine directed zone graphs (native
  star+link topology vs the commissioned export path map vs the committed
  prj path map), classifying each real zone as `sink` (inflow, no
  outflow), `orphan` (no edges), `unreachable` (from the sweep injection
  zone = largest HVAC-served zone), `dead` = union. Passive orifice paths
  count as bidirectional (their physical model); fan/AHS legs and
  ambient/envelope links are directed.
- **Q3 — HVAC declaration coverage**: top-level `hvac_duty` /
  `oa_fraction`, per-group duty/ACH distributions, `oa_fraction` /
  `filter_efficiency` / `nbc_filter_*` coverage, and committed-prj `ach=`
  annotations vs JSON.

## Headline results (measured)

1. **No hard modeling errors anywhere.** Zero missing referenced zone
   ids, zero dangling cross-zone endpoints, zero all-rooms-missing hvac
   groups, and the sweep injection zone is never dead — on all 80 hulls,
   in all three lanes. Museum hulls are reference-clean; the GA import
   pass got referential integrity right.
2. **The dead-zone hypothesis is weak — and flat inside the museum
   population.** Spearman rank correlation of native `dead_frac` vs
   export-twin `mean_l1`: fleet-wide (n=80) **ρ = 0.30**
   (duty-0-room fraction 0.33); within the 68 GA-imported hulls alone it
   collapses to **ρ = 0.17** (sinks 0.09, duty-0 0.08, unreachable 0.06).
   Committed-lane correlations are negative (n=11: −0.08 native,
   −0.27 committed). Dead-zone *count* does not rank-order divergence —
   the four near-totally-dead-in-native battleships (missouri_bb63,
   new_jersey_bb62, wisconsin_bb64, idaho_bb42: 96–99% unreachable)
   diverge barely (mean_l1 ≈ 12). Divergence lives in dead-zone
   *placement* (sinks adjacent to the served network), not mass.
3. **The tail's shared mechanism is the duty-0 sanitary-group sink.**
   Native sinks ≡ duty-0 hvac groups on 76/80 hulls (the `HD_*` heads /
   washrooms / holds): `hvac_duty ≤ 0` makes the native star emit *zero*
   legs, so the zone can receive tracer through one-way links but never
   outflow. The commissioned ContamX terminal mode drains the same zones
   through their return AHS. Every hull in the divergence tail carries
   this signature (see table). ContamX structurally cannot form sinks or
   orphans — per-zone envelope leaks always give outflow — so every
   native dead zone is definitionally a native-vs-ContamX asymmetry.
4. **lexington_cv2 / saratoga_cv3 have whole-deck disconnects, not
   buoyancy voids.** 38 and 39 volume-bearing zones respectively are
   referenced by *nothing* (not hvac, adjacency, or links), and ~80/92
   zones are unreachable in **both** engines — berthing, galleys,
   machinery holds, magazines. These are habitable compartments missing
   connectivity, not the "void" class. Their high mean_l1 comes from a
   ~20%-of-hull connected core plus 5 duty-0 sinks each.
5. **Native silently drops cross-zone links whose endpoints are room
   ids** (it resolves hvac group ids only; export resolves rooms too).
   10 hulls, ~45 links: astoria_ca34 9, chicago_cg11 / miami_cl89 /
   wright_cc2 10 each, expedition_cruise_300 5, classic_cruise_1900 /
   expedition_450 / spirit_cruise_3000 2 each, both enterprises 1.
6. **Committed-prj name drift is systematic, not missing rooms.** GA
   prjs strip underscores and truncate zone names at CONTAMW's 15-char
   field (erie_pg50 17 renamed, lexington 41, saratoga 37, olympia 55).
   After normalization the residual diffs are 1:1 rename pairs from a
   post-tracing JSON rename pass (erie 1, lexington 5, saratoga 3,
   olympia 3). Zone-count and volume drift: **zero** fleet-wide; all
   committed-prj `ach=` annotations match their JSON declarations.
7. **Q3 untuned set = the authored (non-GA) hulls.** Only five hulls lack
   top-level `hvac_duty` (engine default 1.0 instead of the tuned
   {0.0, 0.5} convention): expedition_cruise_300,
   fletcher_class_destroyer, legend_class_nsc, messy_cruise_500,
   san_antonio_class_lpd. Per-group `filter_efficiency` is declared only
   on fletcher (7), legend (9), san_antonio (10); `nbc_filter_*` only on
   legend (6 groups) — present-but-inert: `filter_efficiency` is a single
   global scalar in both lanes (per-zone citadel is inexpressible —
   CONTAM-FLEET-01's recorded gap). GA hulls uniformly carry the tuned
   {0.0, 0.5} duty + ~100% per-group `oa_fraction` convention, so their
   Q3 exposure is the duty-0 sink asymmetry itself, not missing
   declarations.

## Per-hull classification (audit set)

Native dead = sinks / orphans / unreachable counts on the directed native
graph; `cx` = commissioned-export dead count (always ≈ unreachable-only);
`drop` = cross-zone links native ignores (room-id endpoints). L1 =
committed sweep `mean L1` (export twin). `·` = none.

| platform | zones | L1 | native dead (s/o/u) | cx dead | duty-0 rooms | drop | Q1 / Q3 flags |
|---|---|---|---|---|---|---|---|
| gordon_gunter_r338 | 35 | 2669 | 4/0/0 | 0 | 4 | · | · |
| enterprise_galaxy_tng | 127 | 2470 | 37/0/13 | 0 | 37 | 1 | oa-cov 0.69 |
| castle_class_corvette | 19 | 2318 | 2/0/0 | 0 | 2 | · | · |
| fletcher_class_destroyer | 33 | 2306 | 13/0/0 | 0 | 13 | · | no top duty; filt×7 |
| pt_564 | 13 | 1829 | 1/0/0 | 0 | 1 | · | duty {0,0.3} |
| cannon_de701 | 32 | 1721 | 1/0/0 | 0 | 1 | · | · |
| lexington_cv2 | 97 | 1678 | 5/38/78 | 78 | 5 | · | 38 orphan zones; 5 rename pairs |
| saratoga_cv3 | 108 | 1589 | 5/39/92 | 92 | 5 | · | 39 orphan zones; 3 rename pairs |
| legend_class_nsc | 27 | 1446 | 9/0/0 | 0 | 9 | · | no top duty; filt×9; nbc×6 |
| spirit_cruise_3000 | 115 | 1076 | 28/0/0 | 0 | 28 | 2 | oa-cov 0.62 |
| apl_24 | 34 | 919 | 6/0/0 | 0 | 6 | · | · |
| river_class_frigate | 37 | 831 | 3/0/1 | 0 | 3 | · | · |
| winnipeg_j337 | 31 | 804 | 2/0/0 | 0 | 2 | · | · |
| expedition_cruise_300 | 36 | 477 | 11/0/0 | 0 | 11 | 5 | no top duty; no prj |
| messy_cruise_500 | 130 | 199 | 63/0/0 | 0 | 63 | · | no top duty; no prj |
| olympia_c6 | 104 | — | 4/5/8 | 8 | 4 | · | 5 orphan zones; export degenerate (sweep gap); 3 rename pairs |
| erie_pg50 | 54 | 6.5 | 3/0/3 | 0 | 3 | · | counterexample; 1 rename pair |
| san_antonio_class_lpd | 29 | 3.1 | 7/0/0 | 0 | 7 | · | counterexample; no top duty; filt×10; no prj |

(esteem_mso438 sits between rows at L1 56.9 — 3 sinks, otherwise
unremarkable; included for completeness of the committed-dose tail.)

The divergence tail shares exactly one signature: duty-0 sanitary sinks
adjacent to the served network, plus (on the two CVs) a dead-in-both
orphan mass. `erie_pg50` and `san_antonio_class_lpd` barely diverge
despite the same duty-0 convention — sinks are necessary-but-not-
sufficient; their count and position relative to the injection corridor
set the size of the trap.

## Ranked fix list (by expected divergence collapse)

Ordered by how much of the measured tail each item plausibly removes.

1. **Duty-0 sanitary-group terminal asymmetry** — **SHIPPED
   (CONTAM-DUTY0-01)** as `hvac.duty0_terminal_mode: extract` (default;
   `sealed` is the labelled pre-change baseline this audit measured):
   duty-0 groups declared `oa_fraction` 1.0 emit return/exhaust legs at
   `ach · V_room`. Post-fix fleet re-audit: native sinks 535 → 8 (the
   residual 8 are one-way-link deck zones, item 4's class); dead_frac
   0.0 on every divergence-tail hull. Original fix text: give the native engine
   the commissioned-terminal convention the export lane already uses:
   a duty-0 group emits a return/exhaust leg (drain) instead of zero
   legs (trap), matching `vent_mode: extract` semantics and the ContamX
   exhaust AHS. Hulls affected: every GA hull + enterprise_galaxy_tng
   (37 sinks), spirit_cruise_3000 (28), messy_cruise_500 (63), fletcher
   (13), expedition_300 (11), legend/san_antonio (9/7). The single
   mechanism shared by the entire divergence tail.
2. **Native room-id cross-zone endpoints silently dropped** — extend
   `ContamTransportEngine._get_zone_rooms` to resolve bare room ids (as
   the export lane does) or fail loudly at import/validation. 10 hulls,
   ~45 links; includes tail hulls spirit_cruise_3000 and
   enterprise_galaxy_tng.
3. **lexington_cv2 / saratoga_cv3 disconnected-compartment blocks** —
   restore the missing deck-to-deck / room-to-network connectivity from
   the GA source record (38/39 zones have zero incidence; ~78/92
   unreachable in both engines). These zones currently cannot receive
   dose in *either* engine; the fix restores ~80% of each hull to the
   network rather than collapsing divergence directly — the divergence
   they do carry comes from their 5 duty-0 sinks (item 1).
4. **Directed vs bidirectional passive links** — native treats
   `cross_zone_links` as one-way; ContamX orifices are bidirectional.
   Drives the battleship near-total-unreachable class (96–99% native
   dead, L1 ≈ 12 — low measured divergence but mechanically wrong).
   Declare direction per link; default passive links bidirectional.
5. **Q3 declaration hygiene on the five authored hulls** — declare
   top-level `hvac_duty` + complete per-group `oa_fraction` on
   expedition_cruise_300, fletcher_class_destroyer, legend_class_nsc,
   messy_cruise_500, san_antonio_class_lpd; mark `filter_efficiency` /
   `nbc_filter_*` as advisory-only in schema docs until per-zone
   filtration is expressible.
6. **Committed-prj zone-name normalization** — the 15-char/underscore
   name drift means any per-zone committed-vs-JSON check silently
   aliases; normalize names at prj parse (now done in
   `tools/museum_hull_audit.py`). Cosmetic for dose, real for provenance.

## Keep-vs-remove verdict for dead-in-both zones (Q2 follow-through)

- **lexington_cv2 / saratoga_cv3 orphan blocks: neither.** They are real
  compartments missing connectivity (Q1 fix class, item 3) — not
  buoyancy voids to keep-as-isolated, and removing them would silently
  shrink the declared hull. olympia_c6's 5 orphans (barbette, boat deck,
  coal bunker, wardroom pantry) are the same class at smaller scale on a
  degenerate platform.
- **duty-0 HD_*/sanitary sinks: keep, honest dead ends —** but only
  after item 1 gives them an honest *extract* leg; today they are
  modeling errors (a room that cannot exhale), not voids.
- **Battleship unreachable masses (missouri/idaho/palmer et al.):
  keep** — they are reachable through passive openings in ContamX;
  merging/removing would erase real compartments for a directed-graph
  artifact (item 4).

## Reproduce

```bash
.venv/bin/python tools/museum_hull_audit.py \
  --out telemetry_buffer/museum_hull_audit \
  --md-out telemetry_buffer/museum_hull_audit/audit_table.md
```

Per-hull JSON: `telemetry_buffer/museum_hull_audit/museum_hull_audit_latest.json`
(untracked — this document is the durable readout). Tests:
`tests/test_museum_hull_audit.py` (synthetic hulls with known dead/sink/
orphan/drift classes).
