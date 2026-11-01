# CONTAM-DUTY0-01
**Date:** 2026-11-01
**Commit:** c6fc3a79
**Pathogens:** all
**Status:** measured
**Measured at:** c6fc3a79

Implements ranked fix #1 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): the native engine's duty-0 terminal asymmetry. A
duty-0 HVAC group declared `oa_fraction: 1.0` — the fleet-wide exhaust-
only sanitary branch signature (`AHU_HD_*`, 535 groups, ach ≈ 19.1) —
now emits return/exhaust legs at `ach · V_room` into a plenum with no
supply legs, so airborne mass drains overboard. This mirrors the
commissioned-export convention (`tools/contamw34_prj.py`
`_commissioned_flows`: `exhaust_only` → supply 0, return `ach · V`).

Semantics:

- `hvac.duty0_terminal_mode: extract` (default) — exhaust legs as
  above. The gate is `hvac_duty <= 0` AND declared `oa_fraction >= 1.0`:
  every authored duty-0 group fleet-wide is an `AHU_HD_*` extract branch
  (zero exceptions, all oa 1.0). The declared `oa_fraction` gates, not
  the runtime `outdoor_air_fraction_override` — the override rescales
  supply composition only and cannot retype a terminal.
- `hvac.duty0_terminal_mode: sealed` — the labelled pre-change
  baseline (zero legs; mass trapped in the room forever). Every artifact
  that measured the trap — `docs/contam_engine_divergence.md` §3,
  `docs/contam_museum_hull_audit.md`, `tools/hull_state_audit.py`'s
  `hvac casualty` state — pins this baseline where it re-measures.
- A duty-0 group below declared `oa_fraction` 1.0 is sealed under both
  modes: it reads as a disabled AHU, which moves no air. This keeps the
  `hvac casualty` declared state (`hvac_duty: 0` on a supply group)
  meaning "fan offline" instead of silently turning the casualty group
  into an extractor.

Measured post-change (`tools/museum_hull_audit.py` re-run, fleet of 80):

- Fleet-wide native sinks collapse 535 → 8. The residual eight are
  open-air deck zones fed by one-way links (Top_Of_House,
  Forecastle_Working, Gun_Platform, Boat_Deck_Aft, Wheelhouse_Top on
  aeolus/alexander_henry/liberty_cargo/savannah) — fix item 4's directed-
  link class, not duty-0 terminals.
- Native dead_frac = 0.0 on every divergence-tail hull that carried the
  trap: gordon_gunter_r338, fletcher_class_destroyer, spirit_cruise_3000,
  enterprise_galaxy_tng, castle_class_corvette, pt_564, cannon_de701 —
  all previously sink-dominated, now clean.
- Remaining native dead mass is `unreachable` (803 zones) + `orphans`
  (104): the one-way-link class (item 4 — battleships still 96–99%
  unreachable, divergence L1 ≈ 12) and the lexington_cv2/saratoga_cv3
  disconnected blocks (item 3 — 78/92 zones).
- `zone_specific_outflow_rate` on `AHU_HD_01L_M` (legend_class_nsc) =
  19.2 /h — the declared ach, matching the commissioned terminal.

Attributed test moves (each verified pre/post):

- `test_museum_hull_audit` fixture expectations: the toy hull's duty-0
  head now exfils (makeup link in, exhaust leg out) — native sinks [] ,
  dead {ghost, void} only.
- `test_contam_flow_compare` destroyer_baseline: +3 exhaust return legs
  → n_paths 42 → 45, hvac_return 6 → 9.
- `test_route_attribution` short-run fixture went sterile under the new
  default (shifted realized dose); pinned `duty0_terminal_mode: sealed`
  on the fixture config, the same baseline-pin pattern the file already
  uses for `hand_reservoir_mode` and `caregiver`.
- `test_hvac_outdoor_air_override` identity test: kept exact by gating
  on declared `oa_fraction`, not the override.
