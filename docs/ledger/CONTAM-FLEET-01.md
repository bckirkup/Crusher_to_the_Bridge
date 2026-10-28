# CONTAM-FLEET-01
**Date:** 2026-10-28
**Commit:** a35eb254
**Pathogens:** all
**Status:** measured
**Measured at:** a35eb254 (working tree + fleet-compare tool PR)

First fleet-wide native vs ContamX solver comparison: all 80 platforms ×
9 operational arms × 2 contamination scenarios (respiratory decay 0.10;
chemical tracer decay 0), 3 repeats × 12 epochs, via
`tools/contam_fleet_compare.py` + `data/config/contam_compare/fleet_arms.json`.
Readout: `docs/contam_fleet_compare.md`; generated per-hull table:
`docs/contam_fleet_compare_table.md`.

Measured:

- Propagation wall-clock is parity (ContamX traj/native traj ratio 0.96
  small hulls, 1.07 large); ContamX's real cost is the field solve —
  median 90 ms, max 588 ms per export+subprocess+SIM-read, once per arm.
- Baseline dose-L1 divergence vs native: export twin median 23.8
  (p10 4.9, p90 1590); committed authentic prj median 620 — the committed
  models diverge ~26× further, so most "native vs CONTAM" gap is
  authoring, not solver.
- Knob-response sign agreement (median across 79 hulls): ahu_casualty
  0.16 (native moved 0 zones on 5 hulls, opposite-signed retained on
  most of the rest); zone_isolation 0.61; hatches_closed 0.62;
  night_setback / ach_surge / outdoor_air / full_recirc / filter_merv13
  all 1.00 where both engines respond. ContamX moved 0 zones on 0 hulls
  for every arm.
- Expressibility gaps recorded: per-zone NBC citadel filtration feeds no
  code; committed prjs cannot see JSON-side knob mutations; non-hobbyist
  export hard-codes oa_frac=0.2/filter_nr=0; bridge oa_fraction is one
  global scalar; olympia_c6 (0 zones) is a degenerate platform whose
  ContamX export solve timed out.
