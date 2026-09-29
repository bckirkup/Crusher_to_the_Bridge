# NORO-DETECT-01
**Date:** 2026-09-28
**Commit:** c09a34cc2a4cbe8a23a2e690ebe2ee90541257d4
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** c09a34cc2a4cbe8a23a2e690ebe2ee90541257d4

Presenting-sign detection: the first emesis triggers attention and a
clinic-path latency (`clinic_wait_hours`) separates the observed sign
from the confinement order. Hypothesis under test: making the first
emesis the detection event re-opens the whole compliant venue window —
every vomiting host's first emesis lands wherever it stands and the host
stays mobile through clinic wait + escort — then the question is whether
conversion follows at all, or the downstream barrier (L3 pickup -> L4
frailty) still starves every expanded window.

## Mechanism (merged PR #765, measured-SHA c09a34cc)

- `observation_model.presenting_sign` on `norwalk_gi` = `"emesis"`
  (schema enum is the wired vocabulary; `_SIGN_OBSERVERS` in
  orchestrator_epoch.py carries the observer pair per sign name).
- `fred_behavior.symptomatic_order_trigger: presenting_sign` default-ON;
  `onset` = labelled baseline arm (`_onset` cells).
- `fred_behavior.clinic_wait_hours: 6` default — Grade-C declared
  constant, emesis-to-being-seen band 1-24 h (ship-clinic hours; De
  Bellis 2025 47 h upper bound); order lands at
  `presenting_sign_epoch + clinic_wait_epochs`; escort k=1 then governs
  order->admission.
- Symptomatics that can never present the declared sign (non-vomiting
  axis, empty episode draw, non-sign pathogen, co-infection) keep the
  onset-order channel; `detection_channel` is stamped on every order /
  admission / refusal log entry (`onset` | `sign`).
- Emit landings resolve to `emitter_channel` per the host's
  whole-voyage timeline: compliant_in_window / refuser / confined /
  never_ordered.

## Campaign arms

5 arms x 132 children = 660 runs, escort k = 1 everywhere, S3 prefix
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_detect_01/`,
queue `picard-analysis-queue`, jobdef `picard-venue-census:3`, image
`picard-campaign@sha256:ae23af43eed9baddd92e7b49a30f07a456307167b0635e79bd1c0e1e8b4a9e77`
(tag `venue-census-v3`, built at c09a34cc as a verified overlay on
venue-census-v2 — docker.io rate-limited the base pull).

| arm | label | cells |
|---|---|---|
| onset baseline | `_onset` | fl_spr_12d (12 ignited), classic_cruise_1900 (8105-8164), fl_mega_12d (8105-8164) |
| clinic wait 1 h | `_w1` | same |
| clinic wait 6 h | `_w6` | same |
| clinic wait 12 h | `_w12` | same |
| clinic wait 24 h | `_w24` | same |

## Batch job map (submitted 2026-09-28 ~21:49 UTC)

| cell | parent job id | size |
|---|---|---|
| fl_spr_12d_onset | 16daecf6-b2a3-469d-b5ed-6844692bfce9 | 12 |
| classic_cruise_1900_onset | 05798d85-54b8-4ee3-9892-8ae7411385f8 | 60 |
| fl_mega_12d_onset | 58b0302f-5179-4019-bf3b-f162ddeb6bb4 | 60 |
| fl_spr_12d_w1 | 8453433c-d7fd-4561-9f6c-53dac2fb9bc2 | 12 |
| classic_cruise_1900_w1 | 3755a1c7-8061-4982-a0db-7a3180b9cbe3 | 60 |
| fl_mega_12d_w1 | 91637e61-4cc0-4c26-8cac-c49704fef5c2 | 60 |
| fl_spr_12d_w6 | 63df283e-811b-49cb-99b3-ebd53e5b19a8 | 12 |
| classic_cruise_1900_w6 | 15713085-d676-4a9a-9b42-2916c2a7ec02 | 60 |
| fl_mega_12d_w6 | 69003dd6-da58-4f17-84e9-fa437041bf3b | 60 |
| fl_spr_12d_w12 | bd2c9547-7384-4764-ab7a-6a7ab43185f2 | 12 |
| classic_cruise_1900_w12 | e31d571e-738b-45ed-9853-a60ec1f26d62 | 60 |
| fl_mega_12d_w12 | c48bbb2a-0227-4623-8e1f-66da7a731103 | 60 |
| fl_spr_12d_w24 | d65aa8c9-7e30-4cf3-b9bb-48fc06ab843a | 12 |
| classic_cruise_1900_w24 | a7c6c768-f6ae-415d-8219-7c8904db4934 | 60 |
| fl_mega_12d_w24 | f38b3a91-7dec-4cfe-a2ae-098a4e2eee45 | 60 |

## Local canary (gate passed before spend)

Ignited spirit seed 8105, w = 6, k = 1: first emesis epoch 0 ->
`presenting_sign_epoch` 0 -> `escort_order` epoch 6 stamped
`detection_channel="sign"` (exactly w); `escorted_admission` at 7;
`escort_pending_final = 0`. First emit landed mobile (own_stateroom,
pre_confinement). Host 119 (symptomatic, non-vomiting axis) ordered
epoch 0 via `detection_channel="onset"`. 0 unattributed joins.

## Baseline-arm gate (measured at c09a34cc)

`tools/noro_diag/arm_seed_compare.py` diffs every `_onset` seed against
the VENUE-02 `_k1` payload (emit rows, host order/confined epochs,
confinement event stream, acquisitions, ignition — all bit-exact):

- fl_spr_12d_onset: 12/12 seeds IDENTICAL to fl_spr_12d_k1.
- classic_cruise_1900_onset: 60/60 seeds IDENTICAL.
- fl_mega_12d_onset: 60/60 seeds IDENTICAL.

The presenting-sign path draws nothing under `symptomatic_order_trigger
= "onset"`: baseline behavior preserved seed-for-seed on all three
cells.

## Results (measured at c09a34cc, all 660 children)

Completeness: 15/15 cells landed, 660/660 children SUCCEEDED, 0
unattributed joins (>=99% requirement met outright), 0
`escort_pending_final` everywhere. Per-run stamps resolve
`clinic_wait_epochs` to the arm label (1/6/12/24) and
`symptomatic_order_trigger` to `presenting_sign`; `n_sign_observed`
16-82 hosts per sign-arm cell — the mechanism fires at scale, not in
a corner. `sign_gated_final` <= 8 run-ends (voyage ended before a
late sign order landed). Onset-channel confinement orders persist on
every sign arm (non-vomiting symptomatics keep confinement — the
channel-preservation check).

### Placement — the compliant window re-opens

Pre-confinement emit events (was ~0 under omniscient onset detection):

| cell | onset | w1 | w6 | w12 | w24 |
|---|---|---|---|---|---|
| fl_spr_12d | 0 | 17 | 20 | 21 | 23 |
| classic_cruise_1900 | 1 | 12 | 15 | 24 | 26 |
| fl_mega_12d | 0 | 63 | 72 | 80 | 75 |

First-emit shared-venue landings by emitter channel
(compliant_in_window / refuser):

| cell | onset | w1 | w6 | w12 | w24 |
|---|---|---|---|---|---|
| fl_spr_12d | 0 / 2 | 8 / 0 | 9 / 0 | 7 / 3 | 9 / 0 |
| classic_cruise_1900 | 0 / 1 | 4 / 2 | 6 / 0 | 7 / 1 | 7 / 0 |
| fl_mega_12d | 1 / 8 | 42 / 8 | 39 / 8 | 51 / 1 | 51 / 4 |

Subsequent-emit shared-venue landings (same split):

| cell | onset | w1 | w6 | w12 | w24 |
|---|---|---|---|---|---|
| fl_spr_12d | 0 / 6 | 1 / 1 | 2 / 0 | 4 / 0 | 10 / 0 |
| classic_cruise_1900 | 0 / 3 | 0 / 6 | 2 / 1 | 6 / 0 | 14 / 1 |
| fl_mega_12d | 0 / 12 | 1 / 5 | 10 / 6 | 13 / 13 | 28 / 7 |

Every compliant shared-venue landing carried >=1 susceptible occupant
(100% on all sign arms). Refuser first-landings shrink on sign arms
(mega 8 -> 1-4) because the compliance draw re-seats at the shifted
order epoch — a different set of hosts draws refusal, not a lost
channel.

### Conversion check (vs VENUE-02 k1 same-seed baseline)

Acquisitions attributed to shared-venue landings by location +
epoch-persistence (an acquisition counts when its location saw a
shared landing at any epoch <= the acquisition epoch), split by the
landing channel present at that location (`@other` = no shared landing
at that site). Counts are over ignited runs (VENUE-02 ignited
criterion); the single non-ignited spirit onset seed (8159) carried 2
unattributed-by-venue acquisitions not shown here:

| cell | arm | acq | @comp-only | @ref-only | @mixed | @other |
|---|---|---|---|---|---|---|
| fl_spr_12d | onset | 10 | 0 | 6 | 0 | 4 |
| fl_spr_12d | w1 | 9 | 3 | 1 | 0 | 5 |
| fl_spr_12d | w6 | 6 | 3 | 0 | 0 | 3 |
| fl_spr_12d | w12 | 10 | 6 | 0 | 0 | 4 |
| fl_spr_12d | w24 | 11 | 7 | 0 | 0 | 4 |
| classic_cruise_1900 | onset | 6 | 0 | 2 | 0 | 4 |
| classic_cruise_1900 | w1 | 18 | 1 | 6 | 3 | 8 |
| classic_cruise_1900 | w6 | 6 | 2 | 0 | 0 | 4 |
| classic_cruise_1900 | w12 | 21 | 6 | 0 | 0 | 15 |
| classic_cruise_1900 | w24 | 19 | 11 | 0 | 0 | 8 |
| fl_mega_12d | onset | 30 | 0 | 14 | 0 | 16 |
| fl_mega_12d | w1 | 38 | 8 | 1 | 0 | 29 |
| fl_mega_12d | w6 | 40 | 17 | 4 | 0 | 19 |
| fl_mega_12d | w12 | 67 | 17 | 5 | 4 | 41 |
| fl_mega_12d | w24 | 72 | 42 | 1 | 1 | 28 |

`source_agent_id` attribution: 0 anywhere (aerosol/patch pathway
carries no source). Attack rates stay at baseline (~0.0023-0.0032)
because absolute counts are small — the acquisition count is the
sensitive metric.

Compliant-only-attributed acquisitions: onset 0/0/0 -> w24 7/11/42
(spirit/classic/mega) — conversions from the reopened channel are real
on every cell, not a venue-geometry artifact. Per-landing yield ~0.4-0.5
acq/compliant-landing, tracking the refuser-channel rate (~0.7 on
mega baseline) — conversion per landing does NOT collapse as the
window expands, and on mega it rises monotonically with w (8/17/17/42
at w1/6/12/24 on 42 ignited runs): longer exposure per landing, not
just more landings.

### Verdict: (a)

Emesis-first detection restores the compliant venue channel AND it
converts. The compliant-in-window shared-venue first-landing mass goes
from ~0-1 to 7/9/51 (classic/spirit/mega at w24), all with susceptible
occupants, and acquisitions at compliant-only landing sites go from
0 to 7/11/42 — the downstream L3 pickup -> L4 frailty barrier bounds
each landing to ~half a conversion but does not starve the expanded
window. The barrier's signature survives only in the per-landing yield
(sub-linear: mega landings x6 buy acq x3, not x6).

Caveats: window attribution is location + epoch-persistence (patch
pickups land at the venue for many epochs; the strict same-epoch
matcher undercounts — e.g. mega w24 26 strict vs 44 window); the
`@other` bucket also grows on mega (16 -> 28-41), so the mobile
window adds exposure outside shared venues too; w-dose-response is
monotone on mega, noisy-flat on classic (6/6/21/19 over 13 ignited
runs) and flat on spirit (12 seeds).

## Artifacts

- Census zips: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_detect_01/<cell>_<arm>/`
- Aggregates: `results/noro_detect_01/{aggregate,conversion}.json` (local)
- Tools: `tools/noro_diag/arm_seed_compare.py` (baseline gate),
  `tools/noro_diag/venue_conversion_check.py` (attribution),
  `venue_census_readout.py --runs results/noro_detect_01` (full tables)
