# DP-UNION-02
**Date:** 2026-11-26
**Commit:** #1437
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** f585f710299040c374a02e94fe1afa563cb90f74

First post-`COVID-SHED-SHAPE-01` Diamond Princess union-arm measurement.
Design `docs/covid/covid_dp_union_02_design.md`, machine design
`picard_framework/runs/covid_dp_union_02_design.json`, campaign
`campaigns/covid/dp_union_02/`, execution ledger
`campaigns/covid/dp_union_02/LEDGER.md`, canonical canary readout
`docs/covid/dp_union_02_union_t1e8_canary_readout.json`, canonical pilot
readouts `docs/covid/dp_union_02_pilot_readout.json` and
`docs/covid/covid_dp_union_02_pilot_readout.md`.

## Canary stage: what ran

The first owner-authorized stage was exactly one inspected single Batch
child and one 20-seed canary array for `union_t1e8_canary` at theta `1e8`,
arm `union_niid`, using the first 20 frozen ascertainment-conditioned seeds.
No `_rest` block or other lattice cell ran in that stage.

Image digest
`sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`;
job-definition revisions 1–3 all read back on that digest. Single child
`3550df34-1f0c-4715-9e77-a67f515e480a` succeeded and was inspected before
the array. Array parent `9f129293-4457-4f1f-bcd9-7e5e068ddca1` succeeded
with all 20 children `SUCCEEDED` in one attempt each; failure classification
was 20 `ok`, zero Spot reclaim/OOM/timeout/other. The exact S3 prefix then
contained exactly the 20 authorized artifacts.

## Canary measurement

All 20 artifacts are audit-clean. The row is formally provisional because
the frozen row is 24 seeds; the canonical readout therefore leaves
`consistent` null. Every measured seed is in both the founder and takeoff
classes, no seed is extinct, and the row is neither dead nor saturated.

| leg | frozen target/band | measured canary | result |
|---|---:|---:|---|
| ignition day | <= 9 | median 1 | pass |
| before-share | 0.173 +/- 0.10 | median 0.9833114203981133 | fail high |
| attack secondaries | 712–960 | median 3255.5 | fail high |
| during-quarantine | 150–350 | median 1.5 | fail low |
| conditioned capture | >= 0.80 | median 0.6047256797732786 | fail low |
| T3 positives through day 31 | 634 | median 188.5; 20/20 below | fail below |
| onboard positives through day 34 | 691 | median 188.5; 20/20 below | fail below |

Per-seed ranges are narrow and one-sided: attack 3218–3302,
during-quarantine 0–5, capture 0.429–0.732, before-share 0.974–0.988, and
P31/P34 156–229. Median specimens through day 31 are exactly the frozen
3063, so the low T3 positive count is not a missing-test artifact. Median
infections are 3253 before quarantine, 1.5 during the quarantine window,
and 0 after quarantine.

Because all 20 measured seeds are already on the same failing side of the
median legs and below both testing targets, the four unrun `_rest` seeds
cannot reverse those median or side failures under the frozen readout
arithmetic. Theta `1e8` therefore cannot become a consistent 24-seed row
even though the canary remains formally provisional.

## Design review and frozen pilot scope

The design-level review is recorded in
`docs/ledger/DP-UNION-02-DESIGN-REVIEW-01.md`. Its recommendation
superseded the open-ended post-canary decision list: complete the already
frozen 30-cell cross-decade pilot and stop. The scored-row dead,
specimen-report, and representativeness repairs remain post-pilot gates and
were not redesigned for the pilot.

The frozen pilot is exactly the first five frozen conditioned seeds at each
decade theta `1e5`, `1e6`, `1e7`, `1e8`, `1e9`, and `1e10`, arm
`union_niid`: seeds `20200208`, `20200213`, `20200302`, `20200320`, and
`20200321`. The first five theta-`1e8` artifacts are exactly that decade's
pilot slice. Pilot output scores no contract leg; it reports only median
P31 against 634 and a provisional same-cohort saturation diagnostic.

## Cross-decade pilot execution

The remaining 25 cells ran on 2026-11-28 as five size-5 arrays, with no
theta-`1e8` rerun, no `_rest` block, no half-decade block, no 20-seed
canary, no scored row, and no full array. The same image digest was pinned
in job-definition revisions 4–8.

| theta block | parent job | job definition |
|---|---|---|
| `union_t1e5_canary` | `be658370-0725-4253-9dcf-0669922a2a8f` | `picard-covid-dp-union-02:4` |
| `union_t1e6_canary` | `db3fe57c-3efa-41b3-bb83-eab3a5b103b7` | `picard-covid-dp-union-02:5` |
| `union_t1e7_canary` | `5bd24373-05c4-4ec9-91f8-4864ef92b415` | `picard-covid-dp-union-02:6` |
| `union_t1e9_canary` | `14293a2c-7149-45dc-923d-25620b963a05` | `picard-covid-dp-union-02:7` |
| `union_t1e10_canary` | `6e57b897-f48a-483a-95d9-44c5d73f139f` | `picard-covid-dp-union-02:8` |

All 25 new children succeeded in one attempt each; classification is 25
`ok`, zero Spot reclaim/OOM/timeout/other. The exact S3 prefix now contains
45 objects: those 25 plus the prior 20 theta-`1e8` artifacts. The ordered
concatenated sha256 of the exact 30 pilot artifacts is
`1aafb66e4593dd24c3628ebc2661c5e6e1efcbb1dfdd17feaee8319495c03cb8`. Every
artifact entering the pilot is audit-clean under the frozen invariants.

The pilot readout repair is commit `b63f76ee`: pilot `dead` is null rather
than copied from the row, and saturation is recomputed over the same five
pilot seeds as an explicitly provisional diagnostic. The prior theta-`1e8`
canary JSON was regenerated with that hygiene repair; measured canary
values did not change.

## Cross-decade pilot measurement

Median specimens through day 31 are exactly 3063 at every pilot theta. The
saturated threshold is 3524.5 secondaries; no pilot decade is saturated by
the provisional five-cell diagnostic.

| theta | P31 per frozen seed | median P31 vs 634 | median secondaries | provisional saturated |
|---:|---|---:|---:|---|
| 1e5 | 0, 2, 0, 0, 0 | 0, below | 0 | false |
| 1e6 | 0, 339, 223, 5, 0 | 5, below | 164 | false |
| 1e7 | 215, 215, 192, 380, 278 | 215, below | 2,992 | false |
| 1e8 | 183, 186, 172, 189, 191 | 186, below | 3,269 | false |
| 1e9 | 165, 174, 151, 151, 185 | 165, below | 3,412 | false |
| 1e10 | 125, 148, 134, 130, 138 | 134, below | 3,505 | false |

P31 is nonmonotone exactly as measured: 0, 5, 215, 186, 165, 134 across
ascending theta. No decade reaches 634. Under the frozen selection rule,
the result is the explicit edge case **no pilot decade reaches T3**: no
`theta_lo`, no `theta_hi`, no scored grid, and no canary theta. The grid is
not extended and theta is not interpolated.

`machinery_gap_seeds` is report-only: four seeds at `1e5` and two at `1e6`.
Five of those six are extinct cells whose only reachable infection is the
index; the sixth (`1e6` seed `20200321`) has one secondary infection and no
positive. This is not an audit failure and is not used in selection.

## Interpretation and stop state

Measured, not mechanism attribution: under the post-shape source-law
denomination, the frozen six-decade theta ladder contains no pilot decade
whose five-seed median P31 reaches 634. Low decades mostly fail to ignite
or sustain enough incidence; high decades reach large secondary counts but
their positives through day 31 decline monotonically from the `1e7` peak.
The joint rise-and-fall shape is consistent with a timing/window problem
rather than a simple monotone dose-volume shortage, but the pilot does not
identify which structural feature produces that shape.

Execution stops at the pilot readout. No further lattice execution, scored
row, or canary is authorized by this measurement. The next decision is
Benjamin's design decision: structural design review of the
timing/observation window, or a different explicitly re-scoped experiment.
Before any future selected scored row or post-pilot 20-seed canary is
interpreted, the full-row dead implementation must match the frozen
aboard-window-acquisition rule, the specimen-count side-rule counts and
result must be reported as frozen, and Benjamin must explicitly choose the
representativeness correction.
