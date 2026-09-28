# NORO-DETECT-01
**Date:** 2026-09-28
**Commit:** c09a34cc2a4cbe8a23a2e690ebe2ee90541257d4
**Pathogens:** norwalk_gi
**Status:** open

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

## Interim: baseline-arm gate (measured at c09a34cc, jobs running)

`tools/noro_diag/arm_seed_compare.py` diffs every completed `_onset`
seed against the VENUE-02 `_k1` payload (emit rows, host order/confined
epochs, confinement event stream, acquisitions, ignition, all
bit-exact):

- fl_spr_12d_onset: 12/12 seeds IDENTICAL to fl_spr_12d_k1.
- classic_cruise_1900_onset: 60/60 seeds IDENTICAL.
- fl_mega_12d_onset: pending at time of check.

The presenting-sign path draws nothing under `symptomatic_order_trigger
= "onset"`: baseline behavior preserved seed-for-seed (per the
validation gate, a move here is a defect, not a finding).

## Results

(Array in flight — placement tables, conversion check, and verdict
land here on completion.)
