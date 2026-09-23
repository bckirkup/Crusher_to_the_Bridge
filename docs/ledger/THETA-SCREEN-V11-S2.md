# THETA-SCREEN-V11-S2
**Date:** 2026-09-22
**Commit:** 8cda4c7
**Pathogens:** sars_cov2_resp
**Status:** measured

**Measured at:** 8cda4c7

Stage 2 of `covid_theta_screen_v11`: the declared Diamond Princess replay
scored only on takeoff seeds, at the Θ points enumerated by the v11
`stage_2.theta_points` clause from the refine stage-1 admissible set.
Declared in
`picard_framework/runs/covid_theta_screen_v11_stage2_design.json`
(frozen before any stage-2 cell ran); readout
`docs/covid/covid_theta_screen_v11_stage2_readout.md`.

## Declared (before any cell runs)

Refine stage 1 (THETA-SCREEN-V11-REFINE, `79a3ac3`) measured the admissible
set {3.16e10, 4.22e10, 5.62e10} on the eighth-decade lattice; the v11
decade rows admitted nothing, so the union admissible set is exactly those
three. Per the frozen `theta_points` clause the replay runs at those three
plus the nearest failing lattice points on each side — 2.37e10 and 7.5e10
— as boundary flanks (reported, never selected on). Cell shape verbatim
from v10: onset_day −1.0, departure_day 5.0, dwell_weighted, imports 1,
age 3.3 carried, 20 matched seeds at base 20200205, 768 epochs = 100
cells. Clause verbatim from v11: takeoff seeds' (recorded_onsets ≥ 10)
q05–q95 interval contains 197 AND median before_share within 0.10 of
0.173; ≥5 takeoff seeds required. Canary: the 3.16e10 20-seed row
(indices 40–59) audited before the remaining 80.

## Result

**The conditional clause fails at every row; the admissible set is
empty.** Arrays `e530602b` (canary, 20) + `c237e916-8000-4d28-80cd-192ed2daaed0`
(100), job def `picard-covid-boarding-screen:16`, image
`theta-v11-s2-8cda4c7` (`sha256:1eb7a018...`): 100/100 SUCCEEDED, zero
failures, index-geometry invariant 1.0 on every row.

- Takeoff is not the deficit: 18–19 of 20 seeds take off on the declared
  geometry at every Θ (vs 0.44–0.57 generic — a symptomatic-at-boarding
  index ignites far more reliably than a drawn incubation).
- Mass is: takeoff seeds' recorded_onsets median ~3,469–3,520 and
  q05–q95 ~2,088–3,564 against the record's 197 — **~17.7× over** — and
  `onset_mass_near_target` [98.5, 394] is 0.00 on every row: no seed is
  anywhere near the record; there is no interval-span structure to
  mistake for a pass.
- before_share 0.77–0.92 vs 0.173: onsets land essentially entirely
  before the day-17 split at every Θ — the burn completes before
  quarantine binds.
- Conditional mass is Θ-insensitive inside the takeoff class (~1% median
  range across the band) — the v9/v10 "Θ moves takeoff probability, not
  outbreak size" finding reproduced on the declared geometry at
  eighth-decade resolution.

The combined screen answer, per the frozen selection clause: a Θ that
reproduces the fleet's covid.H3 shape exists ({3.16, 4.22, 5.62}e10 on
generic voyages) but cannot keep a conditioned declared voyage near the
record — generic-voyage conditional medians at the same Θ were 129–247
(DP-order) while the replay gives ~3,500. The deficit is **conditional
outbreak size**, the during-quarantine arrest gap of COVID-VENT-AUDIT-01,
now localised inside the fleet-admissible band — the designed empty-set
result. No Θ is carried to the held-out stage 3, which does not run.
