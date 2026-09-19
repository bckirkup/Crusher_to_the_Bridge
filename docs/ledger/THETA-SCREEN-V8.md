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
