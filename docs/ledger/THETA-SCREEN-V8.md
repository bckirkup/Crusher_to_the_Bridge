# THETA-SCREEN-V8
**Date:** 2026-09-19
**Commit:** 2e7f826
**Pathogens:** sars_cov2_resp
**Status:** open

## Declared, not yet run

`covid_theta_screen_v8`
(`picard_framework/runs/covid_theta_screen_v8_design.json`) is the stage-1
re-screen of the v7 near-critical corner now that SEED-ONSET-01 makes the
index geometry true by construction: seven half-decade Θ from 1e7 to 1e10
× six index infection ages (3.3/4.8/6.8/9.8/12.8/15.6 d — implied
incubation = age + onset_day = age − 1.0 d, placing the profile's authored
incubation distribution at its median, its 95% endpoints, and three
interior points) × 40 matched seeds at base 20200205 = 1,680 cells on
`diamond_princess_2020`.

It is authored as a refinement (explicit `points`, `parent_design:
covid_theta_screen_v7`) because the declared `onset_day = -1.0` turns the
v7 root grid's paired baseline (infection age 0 d) into a load-time
contradiction — onset cannot precede acquisition — rather than a silent
nonsense cell. The admissibility block is declared before any cell ran and
differs from v7 in two declared ways: index geometry becomes an audit
invariant (`index_onset_day == -1.0`, `index_shedding_at_day0` true in
every seed — any deviation is a seeding-path defect, not a failed
criterion), and covid.T3 is demoted to a diagnostic on v7's own evidence
(the campaign saturates on assay capacity). covid.T1 is the selection
criterion, verbatim. No result exists yet; the surface will be merged into
this entry when the array completes.

**Verification status at commit:** the design loads and enumerates (1,680
distinct cells) and the declared-age refusal is under test, but the three
local end-to-end probe cells — (Θ 1e7, age 3.3), (Θ 1e10, age 15.6),
(Θ 3.16e8, age 6.8), one seed each through `simulate_screen_cell` — were
launched and had not returned at the time of writing. The design is
declared-and-tested, not yet smoke-confirmed end-to-end: confirming
`index_onset_day == -1.0` on a real cell is the first thing to do before
submitting the 1,680-cell array.

**Smoke confirmation, added at `4721b5b` (post-merge).** The three probe cells
were rerun at `main` = `4721b5b` and all completed. The invariant holds exactly
in every one: `index_onset_day == -1.0`, `index_shedding_at_day0` true,
`index_departed_epoch` 120 (= day 5). SEED-ONSET-01 stamps the record's onset
rather than drawing it, and the geometry gate that emptied v7 cannot recur. Each
cell ran 67–68 min three-up locally (~9 min on a Spot worker). Payloads:
`/home/ubuntu/campaign_results/v8_probe_{low,high,mid}.json`; driver
`v8_probe.py` in the same directory, reproduced verbatim in
`docs/covid/covid_theta_handoff_2026_09_19.md` §7.

| cell | onset_day | shedding@0 | recorded_onsets | attack_rate |
|---|---|---|---|---|
| Θ 1e7, age 3.3 | −1.0 | true | 2843 | 0.815 |
| Θ 3.16e8, age 6.8 | −1.0 | true | 3099 | 0.913 |
| Θ 1e10, age 15.6 | −1.0 | true | 2966 | 0.950 |

**The array is unblocked on the invariant and blocked on the grid.** All three
cells burn the ship — 2,843–3,099 recorded onsets of 3,711 hosts against
`covid.T1`'s 197 — *including* the (Θ 1e7, age 3.3) floor, where v7's nearest
cell (Θ 1e7, age 3.0, incubation drawn) had attack q90 = 0.0014 and effectively
always extinguished. One seed (20200205) drives all three cells, so they are
three points, not a distribution — but v7's own 40-seed evidence says the same
thing wherever the index was in fact symptomatic aboard: at age 11 d
(`index_geometry_pass_fraction` 0.9) the median attack rate is **0.709 at
Θ 1e7** and rises monotonically to 0.98 at 1e12. The quiet cells on the v7
surface were quiet because the index usually never became infectious aboard,
not because Θ was small.

Read together, that places the v8 grid's **floor above the near-critical band
rather than below it**: with the record's geometry enforced, Θ ≥ 1e7 appears to
burn Diamond Princess past its observed 712/3,711 = 0.19, and an admissible Θ,
if one exists, lies below 1e7 — a region no screen has visited. Submitting the
1,680-cell array as declared would spend a campaign inside saturation. The
recommendation to the successor is therefore: **do not submit v8 as declared.**
Declare a downward recentring screen first (coarse, wide, e.g. decade steps from
1e2 or lower to 1e10 at three ages, ~20 seeds) to locate the band under enforced
geometry, then refine. Widening a grid downward is not a loosened criterion and
not a fitted constant: `covid.T1` and the invariant stay verbatim, and the
reason is on the record here, before any cell of the successor runs.

One methodological concern the probes surfaced, recorded for the readout and
deliberately **not** acted on: `covid.T1`'s interval form (the seed 10th-to-90th
percentile of `recorded_onsets` containing 197) is weak against a bimodal arm,
because an interval running 0 → 2,800 contains 197 while no seed lands anywhere
near it. **This is what happened in v7**, read off the committed surface: all
eleven T1-passing cells have `recorded_onsets_p10` = 0 (one has 2) with p90
between 316 and 3,405, so each passed by spanning 197 from an extinction floor to
a burn ceiling, and the accompanying attack q50 is 0.0000 in seven of them. T1 as
declared is therefore satisfiable by a cell with no mass anywhere near the
observed trajectory, which is most of why "eleven cells passed T1" was worth so
little. The criterion is **not** rewritten here after seeing a surface: what the
v8/v9 readout must add is the per-seed distribution alongside the interval, so a
pass can be read as mass-near-197 or as interval-spanning-197. A successor that
wants T1 tightened must declare the tightening before the cells run, in the
design file, with this measurement as its stated reason.
