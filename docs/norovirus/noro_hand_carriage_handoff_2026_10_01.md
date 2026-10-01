# Handoff: hand-reservoir rebuild + Diamond Princess re-approach (2026-10-01)

> **Status:** Handoff record. Reports no new numbers — every figure is
> quoted from the ledger entry or readout that measured it, at that
> entry's `Measured at` SHA. Written at the close of the
> NORO-HAND-CARRIAGE-01 stage (mechanism merged, re-census measured, DP
> replay resumed) so the next session starts from this file, not the
> conversation.

## 1. The question

Whether the contaminated-hand reservoir can carry Liu 2013's measured
rinse occupancy (18/71 = 25.4% of infected subjects positive at
10^2.15 GEC LOD, post-bathroom positives *lower* than routine-day
positives) — and, with hands no longer unnaturally clean, what the
repaired line does to the Diamond Princess replay: `covid_hand_ab_v1`,
60 cells at Θ 2.37e11 × 3 `hand_reservoir_mode` arms (hygiene_cycle /
wash_reuptake / spike_decay) × 20 seeds @20200205, scored on per-seed
recorded_onsets / infections_total / before_share and takeoff q05–q95
against the 197/0.173 record. Success = occupancy R ∈ [1/3, 3] with the
ordering flipped honestly (event < routine by structure, not by tuning).

## 2. Current hypothesis

The reservoir now stands on two structures the Liu measurement itself
bounds: a wash-resistant protected compartment (subungual/crease
carriage; the wash floors at it instead of zero) and a per-host
own-environment pool (the host's own deposits, bookkept, decayed at
surface survival, drawn back onto the accessible hand at measured
surface→hand fractions). At `1c94de2d` the census reads `partial`:
occupancy repaired into the restored band (R = 0.737), both secondary
windows pass, and the lone residual miss — ordering — is a sampling-lens
question, not a mechanism deficit: the readout's post-defecation rows
are pre-wash row-time loads while Liu's post-bathroom arm is post-wash.

## 3. Evidence for

- **Occupancy restored:** pooled 42-cell census at `1c94de2d` —
  positive share 0.187 vs Liu 0.254 → R = 0.737, inside [1/3, 3]
  (`docs/ledger/NORO-HAND-CARRIAGE-01.md`, measured-verdict section;
  merged cell table
  `docs/norovirus/noro_hand_carriage01/hand_occupancy_cells.json`;
  records S3 `campaign/noro_hand_carriage01/`). Was 0.111
  (`still_starved`) at #808, 0.132 at `55cb6b61`, 0.026 at `063e9978`.
- **Secondaries pass:** positive-mean 2.743 log10 ∈ [2.30, 5.45];
  never-positive 0.362 ∈ (0.05, 0.80) — same entry.
- **Structure fired as declared:** protected compartment mean 154 GEC
  per shedding row (771 on positive rows), own pool 43–56 GEC live on
  100% of shedding rows, underflowed rows 41% (was 87%), `at_target`
  20.5% — the carriage-witness block of the same readout.
- **Attribution clean:** every arm-baseline reproduces its pre-change
  tuple exactly (`wash_reuptake` replays the flag-off stream
  bit-identically — verified on the greg_mortimer and DP detector cells,
  ledger entry + PR #813).

## 4. Evidence against / unexplained

- **Ordering still `event_higher`** (event 35.3% / post-defecation
  35.9% / routine 17.6%) — the flip the mechanism was built to produce
  did not appear in the row-time lens. Resolved or confirmed by the §8
  decision.
- **`reservoir_delivered_gec = 0` persists** — the witness counter
  reads only the `wash_reuptake` channel; under `hygiene_cycle` it is
  an instrument hole, not a zero term. Same caveat as the PRACTICE-01
  census; uninstrumented.
- **`first_seen` rows = 178 across 42 cells** — the pool's first-credit
  path is rare; not gated, noted for the record.
- The drying blend keeps deposit transfer at mean 0.046 with the wet
  window open 4.6% of rows — physically right (Sharps 2012 wet/dry
  split) and worth remembering if a *future* starvation verdict appears:
  it caps how fast the own pool stocks.

## 5. PRs landed this session

In dependency order:

- **#804** `d0466064` — `hygiene_cycle` arm v1 (practice variability,
  compliance-gated washes, drying blend). `NORO-HAND-PRACTICE-01`.
- **#805** `ebf571b9` — COVID-HAND-AB-01 + v14 designs, arm-aware CSV,
  `tools/covid_hand_ab_readout.py`, `delivery.hand_reservoir_mode` echo.
- **#807** — readout dedup (`standard_row_stats`, data-driven triggers).
- **#808** `772bdd61` — PRACTICE-01 census verdict: `still_starved`
  (R = 0.111) + decomposition naming the two structural absences.
- **#811** `1c94de2d` — `NORO-HAND-CARRIAGE-01`: protected compartment
  + own-environment pool; `SELF_CONTACT_INCREMENT_GEC_RANGE` superseded.
- Sibling **#810** `dbae9099` — harness/readout only (no engine stream).

## 6. Running jobs

- **DP replay (running):** Batch array `e503114d-9164-4bbb-a1f1-248156ca64b3`,
  58 children (cells 2–59 via `--index-offset 2`), queue
  `picard-campaign-queue` (EC2 Spot), jobdef
  `picard-covid-boarding-screen:43` pinned to image
  `picard-campaign:covid-hand-carriage-1c94de2d` digest
  `sha256:5f4485e5b83be018ede011e440d4da02015a3b83483aaa232ab2d4cadbde1c38`.
  Cells → S3 `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_hand_carriage01/cells/`.
  ~30 min/cell nominal; Spot droughts have parked arrays ~1 h before —
  if stalled >1 h the proven escape is the Fargate queue
  `picard-analysis-fargate-queue` (jobdef must set
  `networkConfiguration.assignPublicIp: ENABLED`).
- **Census (complete):** `fl_spr_12d` array `8112df83-3d6e-4649-8cc5-e4196171b8b4`
  (22) + `classic_cruise_1900` `a9c2d7be-37d9-4c99-9552-0143e31d62ce`
  (20) + canary `9ee17004` — all SUCCEEDED; records under
  `campaign/noro_hand_carriage01/`, readout committed at this PR.
- **DP canary (complete):** `778a5433-5608-4516-b016-5e61a580654c`,
  cells 0–1 SUCCEEDED; both records inspected (arm echo
  `hygiene_cycle`, contract unchanged — one burning cell 0.967, one
  extinction 0.0003 at Θ 2.37e11).

## 7. What is now void

- Every **hand-scaled figure measured before `1c94de2d`** describes the
  superseded reservoir — `docs/norovirus/norovirus_open_ledger.md` §4
  carries the withdrawal line on the CARRIAGE-01 entry.
- The two prior-mechanism `covid_hand_ab_v1` canary cells under
  `campaign/covid_hand_ab_v1/` are **recorded baseline, not void** —
  labelled by their `delivery.hand_reservoir_mode` echo.
- No dose figures were ever in scope: the noro dose ledger stays
  withdrawn in its own right.

## 8. The single open decision

**Whether to add the post-wash-conditioned comparator to the occupancy
readout.** The frozen census samples hand load at *row time*: event-end
and post-defecation rows read fresh contamination before the
compliance-gated wash completes; Liu's post-bathroom arm was measured
*after* the bathroom episode — post-wash. Conditioning the comparator on
wash-completed rows (or emitting a post-wash row type) is the honest
version of Liu's arm: event rows then carry protected-only load vs
routine rows' protected + rebuilt accessible — the structural flip the
mechanism already produces, currently invisible to the lens. Options:
(a) readout-only change — condition the ordering block on
wash-completed event rows (cheap, no engine diff, but not the shipped
frozen criteria); (b) instrument + re-census a post-wash row type on
the same 42 cells (~1 h of Spot); (c) accept `partial` and carry the
miss forward. The census already records wash events per row, so (a)
may be answerable from the S3 dumps without a re-run — check
`hand_occupancy` row fields first.

## 9. Do not reopen

- The Liu frozen criteria: occupancy R ∈ [1/3, 3] restored / [0.2, 5]
  defect / <0.2 `still_starved` / >5 `over_supplied`; ordering
  event < routine; never-positive (0.05, 0.80); positive-mean
  [2.30, 5.45]. Frozen before any cell ran; changed only by a new
  declared criterion, never retro-fit.
- `HAND_PROTECTED_SEQUESTER_GEC_RANGE = (50, 3200)` is bounded by Liu's
  post-bathroom positive arm (Grade B); `HAND_PROTECTED_INACTIVATION_
  PER_HOUR_RANGE = (0.01, 0.06)` is Grade C with mechanism Grade B —
  neither may be tuned toward an anchor.
- The 42 census cells (fl_spr_12d 22 seeds + classic 8000–8019) are
  frozen: same hulls, same seeds, same 288 epochs on every re-census.
- `hygiene_cycle` stays default-ON; `wash_reuptake`/`spike_decay` are
  the labelled baselines and must keep replaying their recorded
  streams bit-identically (the detector pins in
  `tests/test_covid_hull_change_detector.py` guard this).
