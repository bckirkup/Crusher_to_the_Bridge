# THETA-REFIT-01
**Date:** 2026-10-04
**Commit:** 78f52a58
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 78f52a58

## Question

CAREGIVER-ATTR-01 measured that the Θ1e9 clause pass survives only on
the `caregiver.mode: off` tree; the shipped-default tree fails at the
old anchor. With the mechanism default-ON by standing rule, is there a
Θ on the admissible range where the Diamond Princess clause passes
under shipped defaults?

## Declaration

`picard_framework/runs/covid_theta_refit_v1_design.json` (PR #876):
9-row quarter-decade Θ lattice on [1e7, 1e9] × 20 seeds = 180 cells,
single `D0_declared` arm at the verbatim `diamond_princess_2020` replay
contract; v11 conditional clause and index-geometry invariant carried
verbatim; four-branch verdict grammar frozen pre-run — LOCATED /
STRADDLE / NO-ADMISSIBLE / BOUNDARY-HIT. The Θ1e9 row doubles as the
engine-integrity witness against the attribution D0 row (engine
unchanged since `b932d0e9`).

## Measured

180/180 cells, 0 audit failures
(`docs/covid/covid_theta_refit_v1_readout.md`); image
`picard-campaign@sha256:a6797429…`, jobdef
`picard-covid-boarding-screen:50`, `picard-analysis-queue`, prefix
`campaign/covid_theta_refit_v1/78f52a58/cells/`.

**NO-ADMISSIBLE — the residual is mechanism-shaped, not Θ-shaped.**
Every row fails the count leg on the same side: takeoff q05 ≥ 523 at
every Θ, so the [q05, q95] band never reaches 197 — recorded onsets are
too high across the whole lattice, persisting through the 1e7 floor.
Recorded medians plateau at ~700–930 across 1e7–5.62e7 (704 / 793 /
931 / 867) before rising to 2,321 at Θ1e9 — a caregiver-floor the
clause's count band cannot undercut at any reachable Θ. The timing leg
passes at Θ ≤ 1.78e8 (before_share med 0.097–0.255 against 0.173±0.10)
and fails above it (0.279–0.452). `mass_near_t1` = 0 on all nine rows.
Witnesses: caregiver-route pooled aboard_window 141→248 monotone in Θ,
during_quarantine 0 — the mechanism runs pre-quarantine. The Θ1e9 row
is bit-identical to the attribution `D0_declared` row (Δ med +0 [+0,
+0], 19 takeoff pairs), and vs CG_OFF reproduces the +698/+0.329
CAREGIVER-V1 fill-in exactly.

No admissible Θ exists for the v11 clause on the shipped-default tree.
The open follow-up is the clause/anchor itself under the mechanism —
whether the 197 figure needs re-derivation under CAREGIVER-V1 or the
mechanism's pre-quarantine delivery is over-strong. No constants
changed.

## Addendum (2026-10-04, floor falsifier + bracket refine)

Two bounded follow-on campaigns closed the lattice downward, measured at
design SHAs `8f49652f` (floor) and `8f926382` (bracket):
`docs/covid/covid_theta_refit_floor_v1_readout.md` and
`docs/covid/covid_theta_refit_bracket_v1_readout.md`.

**Floor falsifier (`covid_theta_refit_floor_v1`, 20 cells):** Θ1e6, one
decade below the floor — the projection of a mechanism-shaped count
floor was **falsified**: the count leg PASSES ([149, 760] ∋ 197, med
331, 19/20 takeoff, `mass_near_197` = 0.474) while the timing leg fails
below-side (before_share med 0.051 < the 0.073 floor). Caregiver
aboard-window pooled 105 — the mechanism is exercised; the band reaches
197 because it is wide, not because the route went quiet.

**Bracket refine (`covid_theta_refit_bracket_v1`, 100 cells):** five
interior rows {1.4e6, 2e6, 3.16e6, 5.62e6, 7.9e6} — every row fails at
least one leg. **WINDOW-EMPTY-ORDERED, certified:** the count leg fails
on all five interior rows (θ_c ∈ (1e6, 1.4e6) — q05 climbs 149 → 366
immediately) and the timing leg recovers only at 7.9e6 (θ_t ∈ (5.62e6,
7.9e6)). Since θ_c < θ_t, the legs' admissible half-planes are disjoint
— no θ in (1e6, 1e7) can satisfy both.

**Amended verdict:** the v11 clause passes nowhere on [1e6, 1e9] under
shipped defaults — 15 measured rows across ~3 decades, every one
failing at least one leg, with the two legs demanding mutually
exclusive transmission rates (count wants θ ≲ 1.4e6, timing wants
θ ≳ 5.6e6). Below 1e6 the timing leg only worsens toward fizzle. The
residual is **clause-shaped**, not θ-shaped — refined from the
boundary projection (mechanism-shaped) rather than confirmed by it. The
open question stays on the anchor itself under CAREGIVER-V1: the 197
count figure, the 0.173 before-split share, and the takeoff-conditional
scoring. No constants changed.
