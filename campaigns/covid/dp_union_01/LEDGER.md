# covid_dp_union_01 — campaign ledger

Declared 2026-11-24 (ledger `docs/ledger/DP-UNION-01.md`, design doc
`docs/covid/covid_dp_union_01_design.md`).

- **State:** machinery registered; **θ grid held, no block declared, nothing
  submitted to Batch.** Owner decision 2026-11-23: the grid is declared on
  the post-fine-share emission scale after that leg merges.
- **Matrix when declared:** 1 arm (`union_niid`) × 24 seeds
  (20200205–20200228) × 3–4 θ; full declared voyage (840 epochs), no
  horizon arg. Canary: 20 seeds at one θ.
- **Jobdef rev / image digest:** none. Build the image from a `main`
  containing the fine-share leg and this campaign, pin `image_digest` in
  `campaign.json`, then record the revision here.
- **Local smoke (machinery only, old emission units, not scored):**
  `scripts/campaign run covid/dp_union_01 --block union_t3e9_canary
  --index 0` at the first freeze (`d5273582` + the order rename), θ=3.16e9,
  seed 20200205, 27 min wall. All audit invariants held; see the ledger
  entry. That block no longer exists. The worker's `timing` block was
  added after this smoke and is unit-tested only.
- **Before the canary:** declare θ and blocks; re-smoke through the
  registered path on the new scale (covers `timing`); `--dry-run` count
  against the design; pin the digest.
