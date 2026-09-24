# covid_partner_rate_assay_v1 — canary readout

Head commit of record: `37dc215` (merged main the campaign image was built
from). Design: `picard_framework/runs/covid_partner_rate_assay_v1_design.json`
(frozen before any assay cell ran). Ledger: `docs/ledger/PARTNER-RATE-V1.md`.

This is a **partial** readout: the canary arm `R1_rate_0p25` is measured end
to end; the other eight arms were stood down by decision after this read.
Nothing below is fitted to 197.

## Execution record

- Platform: AWS Batch EC2 Spot, job definition `picard-covid-boarding-screen`
  **revision 19**, image
  `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:7528dcd150a1c7fe12b33e0870095e189aec2f779b1ee5aa574528c9e38100bc`
  (built from `37dc215`, `Dockerfile` + `deploy/aws/Dockerfile.covid_hull`).
- Canary submission: array job `partner-rate-assay-canary-r1`
  (`0a5c9e7f-7203-4b7c-939f-7601c40c7be1`), size 20, stride 1,
  `INDEX_OFFSET 20` → cell indices 20–39 = arm `R1_rate_0p25`, all 20 seeds.
- Results:
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_partner_rate_assay_v1/37dc215/cells/cells/`
  (20 objects, one per cell; `_already_complete` makes re-runs idempotent).
- All 20 children SUCCEEDED on the first attempt; no retries, no Spot
  reclaim losses.
- Local preflight (before submission): `tools/covid_partner_rate_smoke.py` —
  180 cells in declared arm blocks, the override lands in the run spec on all
  nine arms, the engine parses the scaled table, ring-path partner draws scale
  ~4× down at ×0.25 (pooled draw-ratio 0.254 vs expected 0.25), the `off`
  witness draws zero partners (bit-identical baseline claim executed), and the
  cell payload contract holds.

## §1 Canary arm `R1_rate_0p25` (multiplier 0.25, n = 20)

Declared replay: Diamond Princess, Θ 4.22e10, index onset_day −1.0,
dwell_weighted sanitary visits, imports 1, infection_age 3.3, seeds
20200205–20200224, full 32-day voyage, `droplet_field_split: partition`.

Audit invariant: `index_onset_day` = −1.0 and `index_shedding_at_day0` = true
on 20/20 cells — the index-geometry gate holds.

Recorded onsets per seed:

| seed | recorded | | seed | recorded |
|------|---------:|--|------|---------:|
| 20200205 | 2519 | | 20200215 | 3398 |
| 20200206 | 3370 | | 20200216 | 3504 |
| 20200207 | 3255 | | 20200217 | 1275 |
| 20200208 | 3095 | | 20200218 | 3525 |
| 20200209 | 3515 | | 20200219 | 2846 |
| 20200210 | 3483 | | 20200220 | 3484 |
| 20200211 | 3461 | | 20200221 | 3499 |
| 20200212 | 3481 | | 20200222 | 3251 |
| 20200213 | 3518 | | 20200223 | 3507 |
| 20200214 | 3466 | | 20200224 | 3502 |

Scoring against the frozen clause:

- **Takeoff gate** (recorded_onsets ≥ 10): **20/20** — no collapse.
- **Conditional recorded mass vs 197**: q05 **2,456.8**, median **3,473.5**,
  q95 **3,518.3** (range 1,275–3,525). The q05–q95 interval does **not**
  contain 197.
- **Near-target share** (150–250): **0/20**.
- **before_share** (onsets before the quarantine split day, pooled over
  takeoff seeds): **0.588** — far above the declared 0.173 ± 0.10 band.
- Seed `20200217` is the low outlier at 1,275; the other 19 seeds sit in
  2,519–3,525.

Route attribution during quarantine (seed 20200217 shown, typical of the
row): droplet 1,139, HVAC-airborne 678, everything else 0 — the droplet
carrier still dominates after the rate cut.

## §2 What the canary decides (declared counterfactual)

The design froze this in advance: *if even 0.25× over-produces, the next
suspect is per-partner plume dose (β) or the ring definition, not reach.*

**That trigger fired.** At a quarter of the shipped partner rate the
conditional mass sits at ~3,474 median — inside the ~3,470–3,520 band the
partition tree produced at the shipped rate (cross-campaign contrast at
`e20008d`/`37dc215`, distribution-level per the declared RNG caveat; the
in-campaign R0 baseline was stood down, so the flatness contrast is
cross-campaign, not paired). The ring is not reach-limited: four times fewer
partner draws still leaves every takeoff seed producing ~2.5k–3.5k recorded
onsets. Per-partner plume dose keeps each ring infection near-certain, so the
gap is bounded by dose concentration and/or the ring's definition (who counts
as a partner, for how long), not by how many partners are drawn.

## §3 Stood-down cells

Arms `R0_declared`, `R2`–`R7`, and `R8_pool_witness` (160 cells) were stood
down after this read — the response-curve reads the design declared
(monotonicity, log-log elasticity, the elbow, the witness delta) are
**unmeasured** and the design's scoring table is only partially answerable.
Reopening them is a new decision: either to complete the curve (declared
INDEX_OFFSET blocks: cells 0–19 baseline, 40–159 multipliers, 160–179
witness, all idempotent under the same S3 prefix), or to pivot to the
β/ring-definition axis the counterfactual names.
