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
- **Local smoke:** one cell, machinery only; record below.
- **Before the canary:** declare θ and blocks; re-smoke through the
  registered path on the new scale (covers `timing`); `--dry-run` count
  against the design; pin the digest.

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
