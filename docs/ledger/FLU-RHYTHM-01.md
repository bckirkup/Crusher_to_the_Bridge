# FLU-RHYTHM-01
**Date:** 2026-09-27
**Commit:** 6e60918c
**Pathogens:** influenza_a
**Status:** declared

Paired A/B of the rhythm layer (SHIP-RHYTHM-01 spec + SHIP-RHYTHM-02
engine, PRs #741/#742) on the influenza arm — the campaign's only clean
arm. FLU-DELIVERY-01 moved `k` to the sourced bound (0.0006, midpoint of
the converted [2e-4, 1e-3]) and measured confined cabinmate attack 7/34 =
20.6%, inside the 15–25% floor, with stage-resolved capture ~9e-6 fully
explained by declared constants. Rhythm changes co-presence everywhere —
the question is whether the clean arm survives the mechanism change, and
what the layer does to its delivery chain. No scored anchor exists for
flu, so this A/B is floor-behaviour + mechanism metrics, not anchor
verdicts.

## Declared before running

**k:** 0.0006 — shipped in the active_profiles bundle; fixed, no retune.

**Conditioning:** the FLU-DELIVERY-01 spec verbatim — isolated arm (the
other bundle pathogens removed, flu's own `initial_infected` nulled), a
2-passenger seed party at epoch 0 via `initiation.explicit_seeds`, and
SOP-017 held by the replay calendar from day 1 to voyage end
(`confinement: declared` in
`picard_framework/runs/mega_cruise_campaign/flu_rhythm_01_manifest.json`).
The `flu_cls_12d` tier (classic_cruise_1900, 288 epochs, seeds
8105/8106 off-arm) is directly comparable to FLU-DELIVERY-01's 7/34.

**Arms:** `off` writes `config_overrides.rhythm.enabled = false` (the
labelled baseline — `RhythmLayer.from_platform` returns before any RNG
construction, so flag-off claims byte-identical draws); `on` writes
`enabled = true`. Same seeds, same spec body otherwise.

**Cells:** 800 = 4 cruise classes × 2 arms × 100 seeds (8105–8204):
expedition_cruise_450, spirit_cruise_3000, classic_cruise_1900,
mega_cruise_5000. ≥100/arm per class suffices for a floor readout — this
is not a rare-event arm.

**Byte-identity gate (first, before any AWS spend):** the flu-conditioned
spec replayed on the pre-rhythm tree (ef81d2d3) and flag-off at the A/B
SHA — telemetry digests must be bitwise identical. **PASS** on two cells:
expedition s8105 168ep `1267250630d1f27444b09624f04784fa4c4cbf9fcc78b5cf5f894c1b283adbbf`
acquired=1, and classic s8105 96ep `4c865642c212996296629a47942ee183f91b05e55df359ed3841377c66b1520d`
acquired=17 — identical on both trees (witness specs committed under
`telemetry_buffer/flu_rhythm_ab/`). Re-verified after the Sonar dedup
refactor — digest unchanged.

**Attribution criterion (stochastic-attribution):** an effect counts only
if |on − off| exceeds the off arm's paired-seed spread on the same class;
effects reported per class on all paired seeds.

**Canary:** index 0 (flu_exp_12d, s8105) off and on. Stop and report if
emitted metrics do not move (flag inert). **PASS — flag live:** off cell
reproduces the witness digest and records confined 1/4, commitments 0,
attached false; on cell `4fbd0927…`, confined 2/5, commitments_total 1440,
attached true (zips committed under `telemetry_buffer/flu_rhythm_ab/canary/`).

**Report-immediately triggers:** byte-identity failure or inert flag; flu
leaving the 15–25% band under rhythm on any class — the clean arm
breaking is a scope-changing measurement.

**Read sections at readout:**
1. Confined cabinmate floor — pooled attack fraction vs 15–25% per class;
   delivered confined dose via the stage probe (does the sleep-window
   cabin curve raise or lower pair exposure).
2. Mechanism metrics — median per-epoch dosed-set size + challenged
   share (the fields the covid probe reads); corridor-front correlation.
3. Floor-hit decomposition — if flu moves out of band, name which stage
   (emission, delivery, conversion) carries the move; no retuning.
4. Verdict — whether the clean arm stays clean under realistic
   partitioning, and if not whether the residual is mechanism-shaped or
   floor-shaped.

**Execution:** AWS Batch EC2 Spot, `picard-campaign-queue`. Image
`picard-campaign@sha256:8d91bc589a0d473fb5a897d53161c735f55608982e96d6826eea3707465df62b`
(tag `flu-rhythm-ab-v2-a3e69e0`, ENGINE_GIT_SHA `3d9d59c`, built atop
`rhythm-ab-v1-3d9d59c`; the earlier `flu-rhythm-ab-v1` image was
superseded by the Sonar dedup — byte-identical telemetry re-verified on
the refactored code before rebuild). Job definition
`picard-flu-rhythm-ab:2`. Arrays: off `39d584e0-37e6-48f9-be4b-e9ad14ef9666`,
on `3ce302df-bd15-493f-849d-f8564c6252cb`, 400 cells each; manifest at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_rhythm_01/flu_rhythm_01_manifest.json`.
A single rev-1 canary (index 0, off) stayed queued on the superseded
image; it targets the same S3 key as the rev-2 array child and is
byte-identical, so whichever lands first wins by design.

## Results

_— pending the four-class block —_
