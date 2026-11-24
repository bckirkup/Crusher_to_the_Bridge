# covid_dp_union_01 — campaign ledger

Declared 2026-11-24 (ledger `docs/ledger/DP-UNION-01.md`, design doc
`docs/covid/covid_dp_union_01_design.md`).

- **State:** grid declared on the post-fine-share scale; pilot (30 cells)
  and canary (20 cells at θ=3.16e8) read out. **Array not submitted —
  Benjamin's decision.** Details in the last section.
- **Matrix:** 1 arm (`union_niid`) × 24 seeds (20200205–20200228) × the
  scored grid {1e8, 3.16e8, 1e9, 3.16e9}; full declared voyage (840
  epochs), no horizon arg. The lattice has 11 runnable θ (264 cells).
- **Jobdef rev / image digest:** `picard-covid-dp-union-01` revisions 1–7,
  all on `sha256:0d01dae0f057770933b610346604875f05bf0fcd62b6f06145e5c19efeb049aa`.

## Local smoke through the registered path (one seed, old units, not scored)

**Measured at:** d5273582 with the `SOP-017-DEDQUARTER` rename applied
uncommitted (committed in fecb44c0, which also removed the block under the
hold).

`scripts/campaign run covid/dp_union_01 --block union_t3e9_canary --index
0`, θ=3.16e9, seed 20200205, full voyage. This is a machinery check in the
emission units being retired; **no contract leg is read from it.**

Every audit invariant of the design held on this cell:

- resolved platform `diamond_princess`, quarantine activated at epoch 391,
  no `close_zones`, susceptibility scale = θ·(α+β)/α;
- only `SOP-017-DEDQUARTER` fired; `exempt_fraction` echoed
  {`crew_general`: 0.25}; 261 of 1,045 crew drawn (= round(0.25 × 1,045));
  no zone echo;
- `crew_duty_exclusion.resolved.enabled` true, 732 hosts excluded;
- `retest_negatives_on_sweep` true, `campaign_waves` [`crew_wave`];
- 3,063 specimens through day 31; every later specimen is on day 34 and
  wave-tagged; day-34 positives agree with `observables.campaign_positives`.

Observed on this one cell (hypothesis-grade, one seed, old units):

- The armed crew wave drew **133 specimens**, not the declared 831: 3,196
  specimens through day 34 against the record's 3,894. Confirmed hosts are
  never re-swabbed, and this cell had confirmed 2,351 hosts. Whether the
  wave fills at a record-like attack rate is unmeasured; if it does not,
  the onboard-table denominator is not reproduced and that leg's reading
  needs the caveat.
- Realized exempt share at activation was 0.209 against the 0.25 drawn
  (261 drawn; fewer working at the snapshot). Not investigated.
- Founder yield 11; 2,561 secondaries (attack 0.69); 912 infections during
  the window; 754 positives through day 31, 767 through day 34;
  conditioned capture 0.947 (2,346 / 2,477).
- The artifact predates the worker's `timing` block (unit-tested only
  until the re-smoke) and is not readable by `readout.py`; it was not
  uploaded.

## Grid declaration, re-smoke, pilot and canary (2026-11-24, new emission scale)

**Measured at:** c7f7f927 — image
`picard-campaign@sha256:0d01dae0f057770933b610346604875f05bf0fcd62b6f06145e5c19efeb049aa`
(tag `dp-union-01`, `ENGINE_GIT_SHA` c7f7f927, contains COVID-EMIT-FINE-01).
The digest was pinned in 18663828 and the grid selected in b4d4ad88; neither
changes a file the worker reads.

- **Dry-run count:** 22 blocks, 264 union-arm cells = 11 lattice θ × 24
  seeds, matching the design.
- **Re-smoke (local, registered path, one seed):** `scripts/campaign run
  covid/dp_union_01 --block union_t1e8_canary --index 0`, seed 20200205,
  23 min 40 s. No audit deviation; the `timing` block is present and read
  by the readout. P31 716, 3,051 secondaries, ignition day 11, 6 founders.
  The Batch cell for the same θ and seed reproduces P31 716.
- **Pilot:** `scripts/campaign submit --size 5` on the canary block of
  each decade. Job definition revisions 1–6.

  | Block | Batch job |
  |---|---|
  | `union_t1e5_canary` | 360a3fb3-ff69-45a9-a1c6-6aff57a69b47 |
  | `union_t1e6_canary` | 535e2622-5823-4dcd-90b8-bcaea13340dd |
  | `union_t1e7_canary` | 658aba44-857d-4375-9994-390bfa1ce862 |
  | `union_t1e8_canary` | 9a663f7e-68d8-4f2b-aeb3-a5f8ce597027 |
  | `union_t1e9_canary` | 74d562fc-7665-4967-9704-7261a4cf1f09 |
  | `union_t1e10_canary` | 636c8dab-7ad6-4fa9-be4a-c97c6dab2e76 |

  Median P31 over seeds 20200205–20200209: 0, 0, 0, 494, 879, 625. Rule
  output: θ_lo 1e8, θ_hi 1e9, grid {1e8, 3.16e8, 1e9, 3.16e9}.
- **Canary:** `union_t3e8_canary`, 20 seeds, job
  d6ccc695-32a4-464f-a6fa-114e706a3755, revision 7, 20 of 20 succeeded.
- **S3:** `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_dp_union_01/<block>/cell_<seed>.json`,
  50 objects.
- **Readout:** `docs/covid/covid_dp_union_01_readout.md` and
  `docs/covid/dp_union_01_readout.json`. Founder class 1 of 20 at the
  canary, so no leg is scored.

Not run: every `_rest` block, and the canary blocks at 1e8, 1e9 (seeds
6–20) and 3.16e9. Pilot blocks at 1e5, 1e6, 1e7 and 1e10 are outside the
scored grid and need no further seeds. A resubmitted block skips cells
already in S3.

Known readout wart: `machinery_gap_seeds` counts the index as a reachable
infection, so it lists every extinct seed.
