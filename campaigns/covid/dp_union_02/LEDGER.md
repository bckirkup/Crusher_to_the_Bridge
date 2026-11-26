# covid_dp_union_02 — campaign ledger

Declared 2026-11-26. Design doc `docs/covid/covid_dp_union_02_design.md`;
machine-readable design `picard_framework/runs/covid_dp_union_02_design.json`.

## State

**Design frozen and locally canary-ready through smoke/dry-run; no scored cell,
pilot, canary, array, image build, jobdef registration, or AWS submission has
run.**

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

## Preflight already measured

- Generated blocks: 22; total cells 264 = 11 lattice theta values x 24 seeds.
- `scripts/campaign describe covid/dp_union_02` resolves the blocks and the
  shared DP union worker/readout paths.
- Dry-run shape measured for `union_t1e8_canary` with `--size 20`, bucket and
  account pinned: 20 array children over the frozen first-20 seed order. The
  jobdef JSON rendered locally but was not registered; no AWS call or submission
  occurred.
- Per-block dry-run count measured across all 22 blocks with bucket/account
  pinned: 264 array children total, matching the design. Every invocation used
  `--dry-run`; no jobdef registration or submission occurred.

## Execution prerequisites still outstanding

Before any AWS submission, a successor session must:

1. build/push the post-shape image and pin both image digest and registered
   job-definition revision in this ledger;
2. confirm the manifest/S3 state required by the campaign-preflight gate;
3. submit exactly one Batch child or pilot only after those gates pass;
4. read a 20-seed canary at one selected cell, then stop and report.

No image digest or job-definition revision exists yet. `campaign.json`
therefore intentionally carries no stale digest.
