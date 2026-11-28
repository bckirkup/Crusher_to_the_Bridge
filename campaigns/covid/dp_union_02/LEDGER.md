# covid_dp_union_02 — campaign ledger

Declared 2026-11-26. Design doc `docs/covid/covid_dp_union_02_design.md`;
machine-readable design `picard_framework/runs/covid_dp_union_02_design.json`.

## State

**AWS preflight and the authorized `union_t1e8_canary` stage are complete:
one inspected single Batch child, then one 20-seed canary array. No other
theta block, `_rest` block, pilot, lattice array, GM/H5 validation, or further
AWS submission has run.** The 20-seed row is provisional by design (the frozen
row is 24 seeds), but every measured seed fails the same contract legs on the
same side; see the readout below.

DP-UNION-02 is the post-`COVID-SHED-SHAPE-01` refit of the DP-UNION-01 union
arm. DP-UNION-01's numerical theta rows are historical provenance only; none
is evidence on the replacement zero-inflated source law.

## Matrix

- 1 arm: `union_niid`
- 11 lattice theta values: `1e5` through `1e10` by half-decades
- 24 explicit ascertainment-conditioned seeds in `seed_values`
- 264 declared cells total, generated as 11 pairs of 20-seed `canary` and
  4-seed `rest` blocks
- full declared voyage horizon; no epoch override in AWS execution

## Ascertainment probe

The seed cohort is selected by `campaigns/covid/dp_union_02/probe.py` from a
predeclared 360-candidate calendar-date sequence beginning `20200205`. The
probe uses zero-epoch initialization-only cells at theta `1e8` and reads only
`index_shedding_at_day0`; it reads no outcome observable. The frozen selection
is the first 24 positive candidates in candidate order.

The committed probe record is `ascertainment_probe.json` in this directory.
Measured after the `COVID-PRESHED-GATE-01` correction: 42 of 360 candidates
positive; the frozen first-24 cohort is the `seed_values` list in the design.
Before correction the same predeclared probe shape was structurally silent
(360/360 false); see `docs/ledger/COVID-PRESHED-GATE-01.md`.

## Local smoke through the registered path

Measured 2026-11-26 on one declared full-voyage cell:

```bash
scripts/campaign run covid/dp_union_02 --block union_t1e8_canary --index 0
```

The run selected theta `1e8`, seed `20200208`, arm `union_niid`, wrote
`out/dp_union02_smoke/cell_20200208.json` locally, and made no AWS call. This
is a machinery smoke only; no contract leg is scored from it.

Audit result: clean. The artifact resolves platform `diamond_princess`,
quarantine activation epoch 391, the theta-derived susceptibility scale,
`index_onset_day` within 1e-9 of 3.0, and `index_shedding_at_day0=True`. The
downstream `dp_union` block is present with `timing`, `t3`, `onboard_table`,
`capture`, theta, seed, arm, and null `smoke_num_epochs`; the specimen and
funnel echoes are compacted out. The DP-UNION-02 readout shim reads the
artifact and reports no audit deviations. One smoke output is provisional by
construction and is not evidence for or against any theta.

## Preflight measured before submission

- Generated blocks: 22; total cells 264 = 11 lattice theta values x 24 seeds.
- `scripts/campaign describe covid/dp_union_02` resolves the blocks and the
  shared DP union worker/readout paths.
- Dry-run shape measured for `union_t1e8_canary`, bucket and account pinned:
  20 array children over the frozen first-20 seed order. Per-block dry-run
  count across all 22 blocks: 264 array children total, matching the design.
- Branch source SHA: `f585f710299040c374a02e94fe1afa563cb90f74` (current
  `origin/main` at branch time). The post-PR-#1435 diff was inspected before
  execution; it touched no COVID-relevant physics or frozen-design file.
- The image was built literally through the root `Dockerfile` base and
  `deploy/aws/Dockerfile.campaign`. In-image `ENGINE_GIT_SHA` is
  `f585f710299040c374a02e94fe1afa563cb90f74`; in-image frozen design sha256 is
  `f4ad9e8bd60648f9e32b9749480b8bb8b7c974adeb2c34a9a57da96854b3b46c`.
- Before push, one in-container full-voyage registered-path smoke completed in
  about 31m53s, wrote the expected compact artifact under `/app`, and was
  audit-clean under the DP-UNION-02 readout. Its local artifact sha256 was
  `aa658fe74c3fe25f51bda522df55913b67bcf6f5eef49d0566da357ab67484c3`.
- ECR image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:dp-union-02`,
  pushed 2026-11-26T20:33:58.929000+00:00. Immutable digest pinned in
  `campaign.json` before registration:
  `sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`.
- Immediately before the first submission the exact prefix
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_dp_union_02/`
  was empty (`Total Objects: 0`).

## Batch registrations and submissions

The registered-path submit command minted one job-definition revision per
non-dry invocation. All active revisions were read back and use the pinned
digest, never a bare tag:

| revision | invocation | image |
|---|---|---|
| `picard-covid-dp-union-02:1` | `--register-only` | `picard-campaign@sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9` |
| `picard-covid-dp-union-02:2` | single-child canary | same digest |
| `picard-covid-dp-union-02:3` | 20-seed array | same digest |

Queue: `picard-analysis-queue`. Region: `us-east-1`. Compute environment read
back as enabled/valid before submission: `picard-analysis-compute-ondemand`,
EC2, maximum 256 vCPU.

### Inspected single child

- Job: `3550df34-1f0c-4715-9e77-a67f515e480a`
- Name: `picard-covid-dp-union-02-union_t1e8_canary-20261126-203508-canary`
- Revision: `picard-covid-dp-union-02:2`
- Created: 2026-11-26T20:35:09.811000+00:00
- Started: 2026-11-26T20:37:00.334000+00:00
- Stopped: 2026-11-26T21:06:30.962000+00:00
- Wall clock: 31m21s submit-to-complete; 29m31s container runtime
- Status: `SUCCEEDED`, one attempt, exit code 0
- Landed artifact:
  `campaign/covid_dp_union_02/union_t1e8_canary/cell_20200208.json`
- Artifact sha256:
  `d58cda623df370e8a3fb782c9c70748807c7d76110b2c1d50d745f06737dac12`

Artifact inspection passed before the array was authorized. It resolves theta
`1e8`, seed `20200208`, arm `union_niid`, design `covid-dp-union-02`, platform
`diamond_princess`, activated quarantine epoch 391, onset day
2.9999999999999996, and `index_shedding_at_day0=True`. `dp_union` contains the
required timing/T3/onboard-table/capture contract, `smoke_num_epochs` is null,
close zones did not fire, required echo blocks are present, and the canonical
readout reports no audit deviations. Its inspected key outcomes matched the
in-image smoke exactly: 3,269 secondaries, one during-window infection, P31 =
P34 = 183, conditioned capture 0.5871559633027523, ignition day 1.

### Twenty-seed canary array

- Parent array job: `9f129293-4457-4f1f-bcd9-7e5e068ddca1`
- Name: `picard-covid-dp-union-02-union_t1e8_canary-20261126-210832`
- Revision: `picard-covid-dp-union-02:3`
- Array size: 20, indexes 0–19, exact frozen seed order in `campaign.json`
- Created: 2026-11-26T21:08:33.769000+00:00
- First child started: 2026-11-26T21:10:47.086000+00:00
- Last child stopped: 2026-11-26T21:43:35.023000+00:00
- Wall clock: 35m01s submit-to-last-child-stop; 32m48s first-child-start to
  last-child-stop
- Status: parent `SUCCEEDED`; all 20 children `SUCCEEDED` in one attempt each
- Failure classification: 20 `ok`; 0 Spot reclaim, 0 OOM, 0 timeout, 0 other
- Child index 0 found the inspected single-child artifact already uploaded and
  exited in 1.247s (`SKIP ... already uploaded` in its Batch log), as designed.
- Excluding that skip, child container runtimes ranged 30m26s–32m48s, median
  32m13s, mean 31m54s.

The exact prefix now contains exactly the 20 authorized canary artifacts under
`union_t1e8_canary/`, total 540.6 KiB; no other object exists under
`campaign/covid_dp_union_02/`. The sha256 of the ordered concatenation of the
20 local artifact sha256 values is
`0fb82039d00c25d9475fbc7bc9b0257cc5b578cfe1806302a2e06479097566a4`.

## Canary readout

Canonical machine-readable readout:
`docs/covid/dp_union_02_union_t1e8_canary_readout.json`, produced with:

```bash
python3 campaigns/covid/dp_union_02/readout.py \
  --cells-dir out/dp_union02_canary_sync \
  --out docs/covid/dp_union_02_union_t1e8_canary_readout.json
```

Measured at theta `1e8`, arm `union_niid`, seeds `20200208` through
`20200721` in the frozen first-20 order. The row has 20 of the frozen 24
seeds and is therefore formally provisional (`consistent: null` in the
readout). All 20 artifacts are audit-clean. No artifact is missing,
duplicated, degenerate, or contract-inconsistent. No seed is extinct; all 20
seeds are in both the founder and takeoff classes.

| leg | frozen target/band | measured 20-seed canary | result |
|---|---:|---:|---|
| ignition day | <= 9 | median 1; never ignited 0 | pass |
| before-share | 0.173 +/- 0.10 | median 0.9833114203981133; per-seed range 0.974–0.988 | fail high |
| attack secondaries | 712–960 | median 3255.5; per-seed range 3218–3302 | fail high |
| during-quarantine | 150–350 | median 1.5; per-seed range 0–5 | fail low |
| conditioned capture | >= 0.80 | median 0.6047256797732786; per-seed range 0.429–0.732 | fail low |
| T3 positives through day 31 | 634 | median 188.5; 20/20 below; per-seed range 156–229 | fail below |
| onboard positives through day 34 | 691 | median 188.5; 20/20 below; per-seed range 156–229 | fail below |

Reported-only medians: attack rate 0.877256804095931; specimens through day
31 exactly 3063; specimens through day 34 3586; recorded onsets 1755.5;
lab-confirmed total 1959; infections before quarantine 3253; infections during
the quarantine window 1.5; infections after quarantine 0; founder yield
3080.5; reachable infections 3256.5; unconditioned capture equals conditioned
capture at 0.6047256797732786. `machinery_gap_seeds` is empty.

Interpretation, separated by evidence class:

- **Measured:** at this theta and seed cohort, the epidemic ignites almost
  immediately and reaches a near-saturating secondary count before the
  quarantine window. Median pre-quarantine infections are 3253 while median
  during-window infections are 1.5.
- **Measured:** the testing denominator is not missing at T3 (median 3063
  specimens, matching the frozen test count), yet positives through day 31 are
  far below the record on every seed.
- **Measured:** because all 20 measured seeds are already on the same failing
  side of the before-share/attack/during/capture medians and below both
  testing targets, the four unrun `_rest` seeds cannot reverse those median or
  side failures under the frozen readout arithmetic. The canonical row remains
  formally provisional because it is 20/24 seeds, but theta `1e8` cannot become
  a consistent 24-seed row by adding those four seeds.
- **Inference, not a separately proven mechanism:** the joint pattern is an
  early burn-out shape: ignition before the recorded onset geometry, most
  incidence before quarantine, few incident infections left during the
  quarantine window, and consequently too few ascertainable positives and too
  little conditioned capture. This explains the correlation of the failing
  legs but does not by itself identify which structural feature of the
  post-shape source law produced it.

## Canary stop state and design-review recommendation

Execution stopped exactly after the authorized single child plus 20-seed
canary. No further campaign cell is authorized or running. The design-level
review requested after that stop is
`docs/ledger/DP-UNION-02-DESIGN-REVIEW-01.md`. It recommends the single
weakest-assumption next experiment: complete the already declared 30-cell
cross-decade pilot (first five frozen seeds at each of the six decade theta
values; the theta-`1e8` slice already exists, so 25 cells remain unrun) and
stop at its readout. No `_rest`, 20-seed canary, lattice expansion, or
mechanism variant is part of that recommendation. The scored-row dead,
specimen-report, and representativeness repairs must be resolved before any
post-pilot scored row, but not before the pilot because the pilot scores no
contract leg.

## Cross-decade pilot execution

Owner authorization on 2026-11-28 was exactly the 25 missing frozen pilot
cells: the first five conditioned seeds (`20200208`, `20200213`, `20200302`,
`20200320`, `20200321`) at each unrun decade block `union_t1e5_canary`,
`union_t1e6_canary`, `union_t1e7_canary`, `union_t1e9_canary`, and
`union_t1e10_canary`. Theta `1e8` was not rerun; its first five existing
artifacts are that decade's pilot slice. No `_rest`, half-decade, 20-seed,
scored-row, or full-array block ran.

Preflight for this exact pilot:

- The pinned image digest was re-verified in ECR and in job-definition
  revisions 4–8:
  `sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`.
  Runtime inputs used by the campaign were unchanged since image source SHA
  `f585f710299040c374a02e94fe1afa563cb90f74`; the design sha256 read inside
  the image remains the current design sha256
  `f4ad9e8bd60648f9e32b9749480b8bb8b7c974adeb2c34a9a57da96854b3b46c`.
- `scripts/campaign describe covid/dp_union_02` resolved 264 cells across
  the 22 frozen blocks. Dry-runs for the five pilot submissions each had
  array size 5 and exactly the frozen first five seeds.
- A full-voyage local theta-`1e5` index-0 smoke reached the engine with
  resolved theta `100000.0`, correct susceptibility scale
  `32322222.222222224`, the union arm, day-0 index emission, epoch-391
  quarantine arming, and the compact `dp_union` artifact contract. It was
  audit-clean; artifact sha256
  `0f5adf5482b8eceecee316add23bd28ae60f4101ed78e34aa2b0d24a864166d9`.
- The previously inspected theta-`1e8` AWS child
  `3550df34-1f0c-4715-9e77-a67f515e480a` is the same design/image/cell
  family and remained the inspected-canary evidence; no gate was skipped on
  the basis of the array alone.

Submitted 2026-11-28T13:30Z as five size-5 arrays; AWS job names carry the
`-first5` suffix:

| theta block | parent job | job definition | array size |
|---|---|---|---:|
| `union_t1e5_canary` | `be658370-0725-4253-9dcf-0669922a2a8f` | `picard-covid-dp-union-02:4` | 5 |
| `union_t1e6_canary` | `db3fe57c-3efa-41b3-bb83-eab3a5b103b7` | `picard-covid-dp-union-02:5` | 5 |
| `union_t1e7_canary` | `5bd24373-05c4-4ec9-91f8-4864ef92b415` | `picard-covid-dp-union-02:6` | 5 |
| `union_t1e9_canary` | `14293a2c-7149-45dc-923d-25620b963a05` | `picard-covid-dp-union-02:7` | 5 |
| `union_t1e10_canary` | `6e57b897-f48a-483a-95d9-44c5d73f139f` | `picard-covid-dp-union-02:8` | 5 |

All 25 children succeeded in one attempt each. Failure classification is 25
`ok`; zero Spot reclaim, zero OOM, zero timeout, zero other. First child
started 2026-11-28T13:34:27Z and the last stopped 2026-11-28T14:07:48Z
(37m08s submit-to-last-stop across the five parents). Child runtime ranges:
`1e5` 16.9–17.5 min, `1e6` 17.2–32.0 min, `1e7` 30.5–31.7 min, `1e9`
32.9–33.2 min, and `1e10` 32.5–33.1 min.

The exact prefix now contains 45 objects and nothing else: the 20 prior
theta-`1e8` artifacts plus five artifacts in each of the five newly run
blocks. Total size is 1,251,759 bytes. The sha256 of the ordered
concatenation of the sha256 values of the exact 30 pilot artifacts (six
decades in ascending theta order, five frozen seeds in frozen order within
each decade) is
`1aafb66e4593dd24c3628ebc2661c5e6e1efcbb1dfdd17feaee8319495c03cb8`.

## Cross-decade pilot readout

Canonical machine-readable pilot readout:
`docs/covid/dp_union_02_pilot_readout.json`; human readout:
`docs/covid/covid_dp_union_02_pilot_readout.md`, produced with:

```bash
python3 campaigns/covid/dp_union_02/readout.py \
  --cells-dir out/dp_union02_pilot_sync \
  --out docs/covid/dp_union_02_pilot_readout.json
```

The readout hygiene repair is commit `b63f76ee`. The prior theta-`1e8`
canonical canary JSON was regenerated from the same 20 canary artifacts so
its pilot section carries null pilot `dead` and the five-pilot-cell
saturation diagnostic; its measured canary values did not change.

All artifacts entering the 30-cell pilot are audit-clean under the frozen
invariants. Pilot rows use exactly the frozen first five seeds at every
decade even though 20 theta-`1e8` artifacts exist. Pilot `dead` is null at
every theta because the 20-of-24 dead rule cannot be measured on five cells.
Saturation is only a provisional diagnostic over the same five pilot cells;
threshold 3524.5 secondaries. No contract leg is scored.

| theta | P31 per frozen seed | median P31 | median secondaries | provisional saturated |
|---:|---|---:|---:|---|
| 1e5 | 0, 2, 0, 0, 0 | 0 | 0 | false |
| 1e6 | 0, 339, 223, 5, 0 | 5 | 164 | false |
| 1e7 | 215, 215, 192, 380, 278 | 215 | 2,992 | false |
| 1e8 | 183, 186, 172, 189, 191 | 186 | 3,269 | false |
| 1e9 | 165, 174, 151, 151, 185 | 165 | 3,412 | false |
| 1e10 | 125, 148, 134, 130, 138 | 134 | 3,505 | false |

The pilot edge case is measured: no decade reaches the frozen median-P31
threshold 634. P31 is nonmonotone exactly as measured: 0, 5, 215, 186, 165,
134 across ascending theta. Under the frozen selection rule there is no
`theta_lo`, no `theta_hi`, no scored grid, and no canary theta; the grid is
not extended and theta is not interpolated.

Median specimens through day 31 are exactly 3063 at every pilot theta, so
the frozen testing volume ran. `machinery_gap_seeds` is report-only: four
seeds at `1e5` and two at `1e6`; five of those six are extinct cells whose
only reachable infection is the index, while `1e6` seed `20200321` has one
secondary and no positive. This is not an audit failure and is not used in
selection.

## Pilot stop state and next decision

Execution stops at the pilot readout. No further campaign cell is authorized
or running. Measured, not mechanism attribution: the post-shape frozen
six-decade ladder contains no decade whose five-seed median P31 reaches 634,
and the rise-then-fall pattern means the missing T3 count is not a simple
monotone dose-volume shortage. The pilot does not identify which structural
feature produces the timing shape.

The next decision is Benjamin's design decision: structural design review of
the timing/observation window or a different explicitly re-scoped
experiment. Before any future selected scored row or post-pilot 20-seed
canary is interpreted, the scored-row gates frozen in
`docs/ledger/DP-UNION-02-DESIGN-REVIEW-01.md` remain unresolved: repair the
full-row dead implementation to match the aboard-window-acquisition rule,
report the frozen specimen-count side rule, and have Benjamin explicitly
choose the representativeness correction.
