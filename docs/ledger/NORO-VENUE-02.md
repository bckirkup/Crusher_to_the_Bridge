# NORO-VENUE-02
**Date:** 2026-09-28
**Commit:** c5f39ac950edc517836f72265fa86db9d95b8e05
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** c5f39ac950edc517836f72265fa86db9d95b8e05

First-emesis placement under a realistic confinement path: does an
order→admission escort delay re-open the compliant pre-confinement
window that NORO-VENUE-01 (27d818d8) found sealed shut, and do landings
through it convert?

Instrument merge PR #763 (`escort_delay_hours` knob + delay-armed
census). Cells ran on AWS Batch `picard-venue-census:2` (EC2) and
`picard-venue-census-fargate-pubip:1` (Fargate, k3 cells + mega k2 after
a us-east-1 EC2 capacity drought), image
`picard-campaign@sha256:a8b73432c44c0e492ae27e2c2a8d3e54d5f9410c9a2f4fcac64367b8ce01e222`
(tag `venue-census-v2`, `ENGINE_GIT_SHA=c5f39ac9`).

Emesis-vs-confinement placement census on the norovirus arm,
`dose_adjustment` 7.57 (withdrawn pending refit like every dose figure
in the repo; cell identity only, not an absolute dose claim).

## Mechanism

`fred_behavior.escort_delay_hours` (Grade-C declared in
`crusher_labs/config.yaml`, shipped default-ON at 1 h; `0` is the
labelled VENUE-01 baseline arm). On a compliance order the host is
queued `due = order_epoch + k` (`escort_order` event with
`escort_due_epoch`) and admitted by `step_escort_admissions` at the due
epoch (`escorted_admission`). Inside the window the host stays fully
mobile — emits, contacts, moves — so a first vomit can land wherever
the host actually is. Refusers bypass the queue as before; the FRED
draw is unchanged.

## Cells

Same three cells as NORO-VENUE-01 × 4 delay arms = 528 runs,
`{cell}_k<delay>` under `campaign/noro_venue_02/`:

| cell | runs/arm | ignited | seeds |
|---|---|---|---|
| fl_spr_12d (spirit_cruise_3000) | 12 | 10 | known-ignited set |
| classic_cruise_1900 (1910) | 60 | 13 | contiguous 8105–8164 |
| fl_mega_12d (mega_cruise_5000, 7000) | 60 | 41–43 | contiguous 8105–8164 |

## Validation gates

- **Attribution:** 854/854 emit events attributed across all 12
  cells; 0 unattributed.
- **Mechanism fires:** `escort_delay_epochs` matches the arm label in
  every zip; `escort_order`/`escorted_admission` pair counts balance
  (196/196, 191/191, 192/192) and `escort_pending_final = 0`
  everywhere. In-window mobile first-emit rows: k1 = 5, k2 = 8, k3 = 11
  (>0 asserted on every k>0 arm except fl_spr_12d_k1 = 0, where the
  1-epoch window is narrower than that cell's minimum
  onset→first-vomit gap).
- **Baseline reproduction:** the k=0 arm reproduces NORO-VENUE-01
  seed-for-seed — spirit 40 events (29 post / 11 never), classic 30
  (23 / 1 at_emit / 6 never), mega 154 (122 / 32), action mix
  194 immediate_compliance + 39 refused_quarantine + 1
  ordered-not-admitted edge row — identical to the VENUE-01 cells.
- Canaries before spend: local seed-8105 k=1 smoke
  (`escort_order`@0 → `escorted_admission`@1) and one Batch canary
  child inspected before the arrays.

## 1. First-emesis landing census (site class × arm × emitter class)

All first landings in every arm come from `symptomatic_onboard` hosts;
`never_symptomatic` emits zero first landings on all 12 cells.

| arm | own_stateroom | shared_venue | in-window mobile first-emits |
|---|---|---|---|
| k = 0 (baseline) | 91 | 13 | 0 |
| k = 1 | 91 | 12 | 5 |
| k = 2 | 89 | 14 | 8 |
| k = 3 | 85 | 14 | 11 |

Shared-venue first-landings split by emitter path (order_subclass):

| arm | refuser channel | compliant in-window |
|---|---|---|
| k = 0 | 13 | 0 |
| k = 1 | 11 | 1 — mega a402 @epoch 1, Waterpark |
| k = 2 | 13 | 1 — mega a402 @epoch 1, Waterpark |
| k = 3 | 12 | 2 — mega a402 @epoch 1, Waterpark; spirit a855 @epoch 3, MainTheater |

Every shared-venue first-landing (compliant and refuser alike) found
≥1 susceptible co-occupant.

## 2. Full emit table (all emesis events, confinement class, by arm)

Cross-cell event counts (site columns collapsed; shared_venue =
dining_pax + venue_free):

| arm | pre_confinement | post_confinement | never_at_emit | never_confined | total | shared-venue events |
|---|---|---|---|---|---|---|
| k = 0 | 0 | 174 | 1 | 49 | 224 | 31 (all never_confined) |
| k = 1 | 1 | 160 | 4 | 51 | 216 | 33 (32 never + 1 at_emit) |
| k = 2 | 5 | 154 | 3 | 49 | 211 | 32 (31 never + 1 pre) |
| k = 3 | 8 | 143 | 3 | 49 | 203 | 32 (30 never + 1 pre + 1 at_emit) |

Total emesis events fall with k (224 → 203): delaying admission shifts
emits out of `post_confinement` into `pre_confinement`, and the extra
mobile epochs land almost entirely in own stateroom — symptomatic
hosts are at home when the order fires, not in venues. The refuser
channel is flat at ~30–33 shared-venue events per arm regardless of k.

## 3. Conversion check (vs VENUE-01 baseline = k0 column)

| cell | metric | k = 0 | k = 1 | k = 2 | k = 3 |
|---|---|---|---|---|---|
| fl_spr_12d | acquisitions / ignited run | 0.60 | 1.00 | 1.40 | 0.60 |
| fl_spr_12d | attack pax / crew (mean) | .0030 / .0028 | .0032 / .0029 | .0033 / .0029 | .0029 / .0030 |
| classic_cruise_1900 | acquisitions / ignited run | 0.00 | 0.46 | 0.62 | 0.46 |
| classic_cruise_1900 | attack pax / crew (mean) | .0023 / .0022 | .0023 / .0023 | .0024 / .0022 | .0023 / .0023 |
| fl_mega_12d | acquisitions / ignited run | 0.79 | 0.73 | 0.43 | 0.67 |
| fl_mega_12d | attack pax / crew (mean) | .0024 / .0024 | .0024 / .0024 | .0024 / .0024 | .0024 / .0024 |

No monotone movement in any cell: attack-rate means sit inside the
k0 noise band everywhere, and the acquisitions means oscillate
(non-ignited-draw churn from the extra mobile epochs, not trend).

## 4. Verdict — (b): the compliant venue window re-opens but does not convert

- **The window is real, not hypothetical.** Four compliant
  `ordered_mobile`/`ordered_not_admitted` first-emesis events land in
  shared venues across the k≥1 arms (mega agent 402, Waterpark,
  epoch 1 — fires on all three k>0 arms of that seed; spirit agent
  855, MainTheater, epoch 3 at k=3), plus 24 in-window first-emits
  total, every shared-venue one susceptible-rich. Refused hosts stop
  being the *only* venue pathway — though they still carry ~90% of
  shared-venue first-landing events at k≥1.
- **It does not convert.** Acquisitions and attack rates stay inside
  baseline noise on all three cells; the downstream barrier measured
  in NORO-VENUE-01 (pickup/conversion starvation, not placement) is
  unaffected.
- **The schedule still starves the window, even at k = 3.** In-window
  first-emits occur in only ~8% of k=3 runs (11/132); onset→vomit
  gaps of 3–102 epochs rarely fit inside a 1–3-epoch escort. The
  compliant channel is open but thin — a second pathway, not the
  volume driver.

Design note (flagged per non-goals, not built): the ordering in which
the first vomit itself triggers the detection/order — "vomit as
detector" — would route many more first-emesis events through the
mobile window than escort latency alone does; the k≥1 arms show the
window is mechanically sound but nearly empty on this detection model.

## Caveats

- Emesis-mass figures are engine-internal units; relative comparisons
  only (dose ledger withdrawn).
- This is an open-ledger entry: conclusions here may be revised by
  subsequent ledgers.
- Mega ignition count drifts ±2 across arms (41–43/60) — the escort
  delay perturbs draw order, so a marginal seed can flip ignition
  class; comparisons are per-cell, not paired per-seed.
- Agent 402 fires on all three mega k>0 arms because the same seed
  family shares the initial-condition draws; treat it as one
  replicated event, not three independent findings.
- Cell capacity: k3 + mega-k2 ran on Fargate after an EC2 capacity
  drought stalled the On-Demand queue; the compute substrate does not
  touch RNG, so arms are comparable, but the drought's partial k0–k2
  EC2 runs are noted for provenance.

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_venue_02/{cell}_k{0..3}/*.zip`;
readout `telemetry_buffer/venue02/readout_full.json`;
array jobs on `picard-analysis-queue` (k0–k2) and
`picard-analysis-fargate-queue` (mega k2, all k3).
