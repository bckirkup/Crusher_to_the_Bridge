# THETA-SCREEN-V9
**Date:** 2026-09-19
**Commit:** b113517
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 0fb186b

## Declared (before any cell ran)

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

## Result (measured at `main` = `0fb186b`, 2026-09-19)

Run on AWS Batch as array `913e36b9-bad2-4f65-a1c6-9ea450bb395e`
(`picard-covid-boarding-screen:7`, image digest `sha256:85936b12…`, 600/600
SUCCEEDED, 0 failed, 51 min; cells at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v9/cells/`).
Full reading: `docs/covid/covid_theta_screen_v9_readout.md`; surface with
per-seed vectors: `docs/covid/covid_theta_screen_v9_surface.csv`. Criterion
unchanged from the declaration above.

1. **Invariant holds in all 600 cells** (`index_onset_day == -1.0`,
   `index_shedding_at_day0` true, departure epoch 120). No seeding defect.
2. **The infection-age axis is inert.** All 200 (Θ, seed) triples are
   byte-identical across 3.3 / 6.8 / 12.8 d outside the `cell` block. Cause,
   read in `engines/initiation.py::_apply_one_seed`: with `onset_day` declared
   the incubation is set to `age + onset_day − seed_day` and the history is
   stamped from `elapsed_since_onset` = 1.0 d, so `time_infected` and the
   incubation shift together and the age cancels. The scenario's own
   provenance note already said the age "no longer states an independent
   fact". v9 is therefore a 10-Θ × 20-seed locator (200 distinct cells); the
   age axis of v8 (never run) and v9 is void, and the "three ages" framing in
   this entry's declaration is withdrawn.
3. **`covid.T1` admissible set = {Θ = 1e9}, interior, vacuous.** Per-seed
   `recorded_onsets` at 1e9: `0 0 0 1 1 1 1 2 969 982 1034 1474 2330 3103 3103
   3187 3277 3318 3368 3379` — p10 = 0, p90 = 3,323 contain 197 by spanning
   it; median `before_share` 0.21 is within 0.10 of 0.173.
   `onset_mass_near_target` at 1e9 = **0.00**; the surface maximum is 0.10
   (Θ 1e5, seeds at 277 and 356). No Θ has more than two of 20 seeds within
   [98.5, 394]. This is the failure mode THETA-SCREEN-V8 pre-registered, now
   measured on the surface it was declared for.
4. **Θ moves the takeoff probability, not the outbreak size.** P(attack >
   0.10): 0 at Θ ≤ 1e3; 0.10 / 0.15 / 0.10 / 0.20 at 1e4–1e7; 0.35 at 1e8;
   0.60 at 1e9; 0.85 at 1e10. Conditional on takeoff the median recorded
   onsets is 1,582–3,391 from 1e6 upward against 197 observed. The 1e1 floor is
   inert as predicted, so the sweep brackets Θ space: there is no near-critical
   band in [1e1, 1e10] where a typical single-import declared-geometry voyage
   yields ~200 onsets.
5. Diagnostics: `covid.T3` fails at every Θ (specimens saturate ~3,030–3,060
   for Θ ≤ 1e9); VSP crossing fraction tracks takeoff probability.

**Stage 1b as pre-committed above (half-decade, 40-seed, six-age refinement of
"the band") should not be run**: two of its axes are now known to be wrong
(no band; age inert). The one open decision, recorded in the readout §6 and
owed to Benjamin before any further cell runs, is whether the calibration
target is (a) the DP trajectory under `covid.T1` — in which case import
geometry, not Θ, is the next axis — or (b) single-voyage takeoff probability
against `covid.H3` with onsets scored conditional on takeoff, declared in a
`covid_theta_screen_v10` design with this entry as the stated reason.
