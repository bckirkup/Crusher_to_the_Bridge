# DP-UNION-02 — cross-decade pilot readout

> **Status:** measured pilot, execution stopped. No decade reaches the frozen
> median-P31 threshold, so the frozen selection rule declares no scored grid
> and no post-pilot canary cell. No contract leg is scored here.

**Measured at:** f585f710299040c374a02e94fe1afa563cb90f74, image
`picard-campaign@sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`.
Readout hygiene repair: b63f76ee. Machine-readable readout:
`docs/covid/dp_union_02_pilot_readout.json`; the theta-`1e8` canary readout
`docs/covid/dp_union_02_union_t1e8_canary_readout.json` has also been
regenerated from the same artifacts so its pilot section carries the repaired
null-`dead` and pilot-cohort saturation fields. Cells:
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_dp_union_02/`.
Design: `docs/covid/covid_dp_union_02_design.md`; design review:
`docs/ledger/DP-UNION-02-DESIGN-REVIEW-01.md`.

## Scope and execution

The pilot cohort is exactly the frozen first five conditioned seeds
`20200208`, `20200213`, `20200302`, `20200320`, `20200321` at each decade
theta `1e5`, `1e6`, `1e7`, `1e8`, `1e9`, `1e10`, arm `union_niid`: 30 cells.
The theta-`1e8` pilot slice is the first five artifacts of the existing
20-seed canary; the other 15 theta-`1e8` artifacts remain in the prefix but
do not enter pilot P31 or the pilot saturation diagnostic.

The 25 previously unrun cells were submitted as five size-5 arrays on
2026-11-28. Parent jobs and job definitions:

| theta block | parent job | job definition |
|---|---|---|
| `union_t1e5_canary` | `be658370-0725-4253-9dcf-0669922a2a8f` | `picard-covid-dp-union-02:4` |
| `union_t1e6_canary` | `db3fe57c-3efa-41b3-bb83-eab3a5b103b7` | `picard-covid-dp-union-02:5` |
| `union_t1e7_canary` | `5bd24373-05c4-4ec9-91f8-4864ef92b415` | `picard-covid-dp-union-02:6` |
| `union_t1e9_canary` | `14293a2c-7149-45dc-923d-25620b963a05` | `picard-covid-dp-union-02:7` |
| `union_t1e10_canary` | `6e57b897-f48a-483a-95d9-44c5d73f139f` | `picard-covid-dp-union-02:8` |

All 25 new children succeeded in one attempt each; failure classification is
25 `ok`, zero Spot reclaim, OOM, timeout, or other. First child start was
2026-11-28T13:34:27Z and last child stop 2026-11-28T14:07:48Z. The exact S3
prefix contains 45 objects: those 25 new artifacts plus the 20 prior
theta-`1e8` artifacts, and nothing else. The ordered concatenated sha256 of
the exact 30 pilot artifacts is
`1aafb66e4593dd24c3628ebc2661c5e6e1efcbb1dfdd17feaee8319495c03cb8`.

Every artifact entering the pilot is audit-clean under the frozen invariants.
The pilot readout has `dead: null` at every theta because the 20-of-24 dead
rule cannot be measured on five pilot cells. Saturation below is a
provisional diagnostic recomputed on the same five pilot seeds, with the
frozen threshold 3524.5 secondaries.

## Frozen pilot result

| theta | P31 per frozen seed | median P31 vs 634 | median secondaries | provisional saturated |
|---:|---|---:|---:|---|
| 1e5 | 0, 2, 0, 0, 0 | 0, below | 0 | false |
| 1e6 | 0, 339, 223, 5, 0 | 5, below | 164 | false |
| 1e7 | 215, 215, 192, 380, 278 | 215, below | 2,992 | false |
| 1e8 | 183, 186, 172, 189, 191 | 186, below | 3,269 | false |
| 1e9 | 165, 174, 151, 151, 185 | 165, below | 3,412 | false |
| 1e10 | 125, 148, 134, 130, 138 | 134, below | 3,505 | false |

P31 is nonmonotone exactly as measured: it rises from 0 at `1e5` to 5 at
`1e6` and 215 at `1e7`, then falls to 186 at `1e8`, 165 at `1e9`, and 134 at
`1e10`. No median reaches 634. Therefore the frozen edge case is
**no pilot decade reaches T3**. The selection rule declares no `theta_lo`,
no `theta_hi`, no scored grid, and no canary theta. The grid is not extended
and theta is not interpolated.

Median specimens through day 31 are exactly 3063 at every pilot theta, so
the frozen testing volume ran. `machinery_gap_seeds` is reported only, not
scored: four seeds at `1e5` and two at `1e6`. Five of those six are extinct
cells where the only reachable infection is the index; the sixth
(`1e6` seed `20200321`) has one secondary infection and no positive. This
does not change the frozen audit-clean status and is not used in selection.

## Interpretation by evidence class

- **Measured:** under the post-shape source-law denomination, the frozen
  six-decade theta ladder does not contain a pilot decade whose five-seed
  median P31 reaches 634.
- **Measured:** the outcome direction reverses within the lattice. Low
  decades mostly fail to ignite or sustain enough incidence; high decades
  reach large secondary counts but their positives through day 31 decline
  monotonically from the `1e7` peak.
- **Measured:** no pilot decade is saturated by the provisional five-cell
  diagnostic, although `1e10` is close to the threshold (median 3505 vs
  3524.5).
- **Inference, not mechanism attribution:** the joint rise-and-fall shape is
  consistent with a timing/window problem rather than a simple dose-volume
  shortage, because total secondaries increase across the high decades while
  P31 falls. The pilot does not identify which structural feature produces
  that timing shape.
- **Not established:** no contract leg, representativeness verdict, dead-row
  verdict, or consistent/ inconsistent row verdict is established here.
  Those are post-pilot scored-row questions and remain unrun.

## Stop state and next decision

Execution stops at this pilot readout. No `_rest` block, half-decade cell,
20-seed canary, scored row, full array, GM/H5 validation, or further lattice
cell ran or is authorized by this readout.

Because the frozen pilot declares no grid, the next decision is Benjamin's
design decision: whether the post-shape union arm now needs structural
design review of the timing/observation window, or a different explicitly
re-scoped experiment. Before any future selected scored row or post-pilot
20-seed canary is interpreted, the design review's three scored-row gates
still must be resolved: the full-row dead implementation must match the
frozen aboard-window-acquisition rule, the specimen-count side-rule counts
and result must be reported as frozen, and Benjamin must explicitly choose
the representativeness correction.
