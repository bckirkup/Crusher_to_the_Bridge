# FLU-SOCIAL-01: influenza on the social-mechanics engine — the FLU-RHYTHM-01 conditioned cells re-censused

**Measured at:** `8c03e9d7` (ENGINE_GIT_SHA of the campaign image `campaign-8c03e9d7`, `picard-campaign@sha256:825a52e8e80c8f9f048a55b346761b88ce3dd69d633587425b4b671728b0720e`; merge of #862).

Baseline: the `flu_rhythm_02` census at `1ab8dd98` (recorded in `docs/ledger/FLU-RHYTHM-01.md`), the **same frozen 800 cells** — identical manifest (`picard_framework/runs/mega_cruise_campaign/flu_rhythm_01_manifest.json`: isolated `influenza_a`, 2-passenger explicit seed at epoch 0, SOP-017 declared day 1 → voyage end, k = 0.0006, 288 epochs, seeds 8105–8204, 4 classes × 2 arms × 100 seeds), read into the fresh prefix `campaign/flu_social_01/`. Between the two SHAs the engine gained CAREGIVER-V1 (#859 — three-role caregiver grammar, R2 tending / R3 service declared for influenza_a, default-ON) and PROPENSITY-V1 (#860 — persistent per-party contact-propensity heterogeneity, default `party`, rhythm-gated), plus the shared campaign-stack image (#861) and the `_emit_emesis` wrapper-drift fix (#862).

Arm semantics (unchanged from the frozen design): `off` writes `rhythm.enabled = false`, `on` writes `true`. PROPENSITY-V1 is rhythm-gated, so **off-arm propensity is inert; caregiver is live in both arms** (its `transmission.caregiver.mode` sits on `tx_core`, independent of rhythm). Therefore:

- `flu_social_01` off-arm vs `flu_rhythm_02` off-arm ≈ caregiver + the other engine commits in `1ab8dd98..8c03e9d7` (not a clean single-mechanism isolation);
- `flu_social_01` on − `flu_social_01` off isolates PROPENSITY-V1's marginal effect on this arm;
- `flu_social_01` on-arm vs `flu_rhythm_02` on-arm = propensity + caregiver together (the headline "flu under social mechanics" delta).

Execution: jobdef `picard-flu-rhythm-ab:4`, queue `picard-campaign-queue` (Spot, ~55 min wall for both arrays). Canary gate (20 on-arm cells, expedition s8105–8124) passed before the arrays. Arrays `48f04534-650d-4c5a-b197-167c28c15111` (off) and `800a0cc7-a111-4593-9dbe-f2690d560a17` (on): **800/800 SUCCEEDED, 0 FAILED**. Readout `tools/flu_rhythm_ab_readout.py`; zips at `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_social_01/`.

## Confined cabinmate SAR (n = 100 cells/class/arm)

| class | off @1ab8dd98 | off @8c03e9d7 | on @1ab8dd98 | on @8c03e9d7 |
|---|---|---|---|---|
| expedition_cruise_450 | 37/314 = 11.8% [8.7–15.8] | 42/315 = **13.3%** [10.0–17.5] | 39/311 = 12.5% [9.3–16.7] | 38/315 = **12.1%** [8.9–16.1] |
| spirit_cruise_3000 | 93/1204 = 7.7% [6.3–9.4] | 87/1208 = **7.2%** [5.9–8.8] | 87/1207 = 7.2% [5.9–8.8] | 89/1209 = **7.4%** [6.0–9.0] |
| classic_cruise_1900 | 63/854 = 7.4% [5.8–9.3] | 63/856 = **7.4%** [5.8–9.3] | 64/853 = 7.5% [5.9–9.5] | 56/856 = **6.5%** [5.1–8.4] |
| mega_cruise_5000 | 143/2612 = 5.5% [4.7–6.4] | 134/2608 = **5.1%** [4.4–6.1] | 146/2602 = 5.6% [4.8–6.6] | 141/2597 = **5.4%** [4.6–6.4] |

Every new point estimate sits inside its `1ab8dd98` Wilson band and inside the CABIN-FLOOR-03 corrected band (declared-k expected SAR 3.7–12.1% pooled); the expedition off-arm is again the reading above the pooled top, as it was at `1ab8dd98`. **No confined-SAR move on any class in either arm.**

## Challenged share (n_challenged / n_aboard_end — the dosed population)

| class | off @1ab8dd98 | off @8c03e9d7 | on @1ab8dd98 | on @8c03e9d7 |
|---|---|---|---|---|
| expedition_cruise_450 | 0.337 | 0.422 | 0.392 | 0.473 |
| spirit_cruise_3000 | 0.310 | 0.359 | 0.349 | 0.389 |
| classic_cruise_1900 | 0.328 | 0.371 | 0.361 | 0.405 |
| mega_cruise_5000 | 0.324 | 0.364 | 0.358 | 0.395 |

Both lifts resolve: `flu_social_01` off − `flu_rhythm_02` off = **+3.5 to +8.5 pp** (caregiver side, plus the inter-census engine commits); `flu_social_01` on − off (paired seeds, propensity marginal) = **+3.0 to +5.2 pp**, mean ≈ median on every class. The social layer measurably enlarges the dosed population.

## Voyage attack (community endpoint, unscored)

| class | off @1ab8dd98 | off @8c03e9d7 | on @1ab8dd98 | on @8c03e9d7 |
|---|---|---|---|---|
| expedition_cruise_450 | 0.0131 | 0.0144 | 0.0125 | 0.0136 |
| spirit_cruise_3000 | 0.0070 | 0.0077 | 0.0070 | 0.0076 |
| classic_cruise_1900 | 0.0081 | 0.0082 | 0.0076 | 0.0082 |
| mega_cruise_5000 | 0.0064 | 0.0068 | 0.0066 | 0.0068 |

Small uniform lift old → new in both arms; the propensity-marginal component is ≈ 0 (on − off ≤ +0.001 everywhere).

## Per-slot delivered confined dose and caregiver witness

Per-slot `effective_dose` p50 (cell median, then median across cells): exp 28.5 → 29.9 off / 29.4 → 30.9 on; spr 2.35 → 2.09 / 2.11 → 1.85; cls 3.61 → 3.25 / 2.95 → 3.11; mega 1.56 → 1.51 / 1.27 → 1.26 copies — flat old → new in both arms.

`caregiver:influenza_a` appears in the confined `slot_rows[].pathway_dose` attribution — the first in-cell witness of caregiver dose on this pathogen:

| class | cells with ≥1 caregiver-touched slot (off / on, per 100) | summed caregiver dose per cell, mean copies (off / on) |
|---|---|---|
| expedition_cruise_450 | 15 / 14 | 0.0007 / 0.0019 |
| spirit_cruise_3000 | 54 / 54 | 0.097 / 0.160 |
| classic_cruise_1900 | 52 / 44 | 0.021 / 0.037 |
| mega_cruise_5000 | 86 / 82 | 0.179 / 0.408 |

Reach tracks crew/service scale (largest on mega, smallest on expedition). Magnitude is 2–4 orders below the delivered slot dose: ~0.001–0.4 copies/cell against ~1.3–30 copies per slot. Caregiver is a real but marginal delivery channel on this pathogen at these constants.
