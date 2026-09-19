# THETA-SCREEN-V9
**Date:** 2026-09-19
**Commit:** b113517
**Pathogens:** sars_cov2_resp
**Status:** open

## Declared, not yet run

`covid_theta_screen_v9`
(`picard_framework/runs/covid_theta_screen_v9_design.json`) is the stage-1
**recentring** screen: ten decade Θ from 1e1 to 1e10 × three index infection
ages (3.3 / 6.8 / 12.8 d — implied incubation = age + `onset_day` = age − 1.0 d,
placing the `sars_cov2_resp` authored incubation distribution at its median and
near both 95% endpoints) × 20 matched seeds at base 20200205 = **600 cells** on
`diamond_princess_2020`. Like v8 it is authored as a refinement (explicit
`points`, `parent_design: covid_theta_screen_v8`), because a declared
`onset_day = -1.0` makes the v7 root grid's infection-age-0 baseline a load-time
contradiction.

**It supersedes `covid_theta_screen_v8`, which was never submitted.** The reason
is measured and recorded in `docs/ledger/THETA-SCREEN-V8.md` (#613), before this
design was written: v8's three smoke-probe cells confirmed the declared-onset
invariant and *burned the ship at every cell including the Θ 1e7 floor*
(2,843–3,099 recorded onsets of 3,711 against `covid.T1`'s 197), and v7's own
40-seed cells agree wherever its index was in fact symptomatic aboard (median
attack 0.709 at Θ 1e7, age 11 d, rising monotonically to 0.98 at 1e12). The
quiet region of the v7 surface was quiet because the index usually never became
infectious before disembarking on day 5 — not because Θ was small. So the band
that could reproduce Diamond Princess at 712/3,711 = 0.19 and the `covid.H3`
fleet median at 0.002 lies **below** 1e7, where no screen has been.

**What changed from v8, and what did not.** Changed: the Θ range is widened
downward by six decades and coarsened to decade steps (600 cells instead of
1,680 — this is a locator, not a fit), the incubation axis drops to three points,
and seeds drop to 20; a half-decade, 40-seed, six-age refinement of whatever band
this finds is **stage 1b**, declared in its own file after this surface exists
and before its own cells run. Unchanged: `covid.T1` is the sole selection
criterion, verbatim from v7 and v8, thresholds included; the index-geometry
invariant (`index_onset_day == -1.0`, `index_shedding_at_day0` true in every
seed — any deviation is a seeding-path defect, not a failed criterion) is
verbatim; `covid.T3` stays a diagnostic on v7's own saturation evidence; and
bimodality is neither a failure nor a success criterion, because `covid.H3` says
the real fleet is near-critical.

Widening a grid downward is not a loosened criterion and not a fitted constant:
it screens Θ space the earlier grids never visited, for a reason recorded before
this design existed. The 1e10 ceiling is retained deliberately so this surface
contains the whole region v7 and v8 declared, readable against them at 1e7–1e10
on the shared lattice. The 1e1 floor is **expected to be inert**: an inert floor
is the evidence that the sweep brackets the band rather than sitting above it,
which is exactly the mistake v8 would have made. If the admissible set lands on
either boundary, that is a boundary result and must be reported as one, with the
sweep extended in that direction — never selected on.

**New diagnostic, declared as a diagnostic:**
`onset_mass_near_target` — the fraction of a cell's seeds whose
`recorded_onsets` falls within a factor of two of the observed 197 (in
[98, 394]), reported with the full per-seed `recorded_onsets` vector. It exists
because THETA-SCREEN-V8 measured that all eleven v7 T1-passing cells passed by
their p10–p90 interval *spanning* 197 from an extinction floor (p10 = 0) to a
burn ceiling (p90 316–3,405), with attack q50 = 0.0000 in seven of them — T1 as
declared is satisfiable by a cell with no mass anywhere near the observed
trajectory. The criterion is deliberately **not** rewritten here; the diagnostic
is reported alongside it so a pass can be read as mass-near-197 or as
interval-spanning-197, and any tightening must be declared in the stage-1b design
before its cells run, with this measurement as the stated reason.

No result exists yet. The surface will be merged into this entry, with the
per-seed distributions beside the T1 intervals, when the array completes.
