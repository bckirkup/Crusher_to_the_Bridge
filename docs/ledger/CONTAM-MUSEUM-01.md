# CONTAM-MUSEUM-01
**Date:** 2026-11-01
**Commit:** d74365ba
**Pathogens:** all
**Status:** measured
**Measured at:** d74365ba

Museum/GA hull divergence audit: mechanical classification of all 80
platforms' committed `spatial_layout.json` + `air_flow_paths.json` (and
`contam/platform.prj` where present) against three questions —
missing-geometry mistakes (Q1), dead-end topology vs twin-lane
divergence (Q2), HVAC declaration coverage vs the tuned cruise-hull
convention (Q3). Computed by `tools/museum_hull_audit.py` on the working
tree at d74365ba plus this change's tool; divergence inputs are the
committed `docs/contam_fleet_compare_table.md` (`mean L1`, export twin)
and the CONTAM-FLEET-01 committed-lane dose-L1 values. Readout:
`docs/contam_museum_hull_audit.md`. No geometry was changed.

Measured:

- Zero hard modeling errors on all 80 hulls in all three lanes: no
  missing referenced zone ids, no dangling cross-zone endpoints, no
  all-rooms-missing hvac groups, no dead injection zone.
- Dead-zone vs divergence correlation is weak and flat inside the museum
  population: Spearman(native dead_frac, mean_l1) = 0.30 fleet-wide
  (n=80), 0.17 within the 68 GA-imported hulls; committed-lane
  correlations negative (n=11). The near-totally-dead-in-native
  battleships (missouri/new_jersey/wisconsin/idaho, 96–99% unreachable)
  diverge barely (mean_l1 ≈ 12) — dead-zone placement drives divergence,
  not dead-zone mass. The Q2 "dead-end fraction explains the tail"
  hypothesis is not supported as stated.
- The tail's one shared mechanism: native sinks ≡ duty-0 hvac groups on
  76/80 hulls (HD_* sanitary/extract zones whose native star emits zero
  legs while the ContamX commissioned terminal drains them). Every hull
  in the divergence tail carries it.
- lexington_cv2 / saratoga_cv3 carry 38/39 volume-bearing zones with
  zero airflow incidence and ~78/92 zones unreachable in both engines —
  real compartments missing connectivity, not buoyancy voids.
- Native silently drops cross-zone links whose endpoints are bare room
  ids: 10 hulls, ~45 links (astoria 9; chicago/miami/wright 10 each;
  spirit_cruise_3000 and enterprise_galaxy_tng included).
- Committed GA prjs strip underscores and truncate zone names at
  CONTAMW's 15-char field; after normalization all residual diffs are
  1:1 rename pairs. Zone-count, volume, and `ach=` annotation drift vs
  JSON: zero fleet-wide.
- The no-top-level-`hvac_duty` set is exactly the authored hulls
  (expedition_cruise_300, fletcher_class_destroyer, legend_class_nsc,
  messy_cruise_500, san_antonio_class_lpd — engine default 1.0 vs the
  {0.0, 0.5} tuned convention). `filter_efficiency`/`nbc_filter_*` are
  present-but-inert on fletcher/legend/san_antonio only.

Fix list (ranked by expected divergence collapse) is in the readout:
duty-0 terminal asymmetry → room-id xzone resolver → lexington/saratoga
connectivity → directed-vs-bidirectional links → authored-hull
declarations → prj name normalization.
