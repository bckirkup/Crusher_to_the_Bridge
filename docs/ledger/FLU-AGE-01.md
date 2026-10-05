# FLU-AGE-01
**Date:** 2026-10-05
**Commit:** b4207e5f
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** b4207e5f

Canary-scoped re-census of the FLU-RHYTHM-01 conditioned cells on the
host-age engine: the frozen manifest (`flu_rhythm_01_manifest.json`,
isolated `influenza_a`, 2-passenger epoch-0 seed, declared SOP-017
day 1 → end, k = 0.0006, 288 epochs, seeds 8105–8204) run at `b4207e5f`
against the `flu_social_01` census at `8c03e9d7` as baseline. Engine
delta `8c03e9d7..b4207e5f` on the conditioned cells: HOST-AGE-02
(flu `symptomatic_fraction_by_age_band` — Hoy 2022, child 0.909–0.965 /
≥15 0.734 vs flat 0.669) and HOST-AGE-03 (flu
`severity_model.base_probabilities_by_age_band` — CDC 2023-24 severe
ratios), both default-ON; AGE-WITNESS-01 cell-payload fields; NORO-FOOD-01
mechanism present but `food_contamination.enabled: false` on influenza_a;
DP-BELIEF-01-D4 / HOST-AGE-01 covid-only. Scope: three smaller hulls
(expedition + spirit + classic — flat indices 0–299; mega excluded per
user request), canary = 20 on-arm expedition cells, seeds 8105–8124.

**Execution:** image `picard-campaign@sha256:056f7c83bf943fa4a469ac42fcb9c911286b5896e2569be06317f94f75e13a6a`
(tag `campaign-b4207e5f`, ENGINE_GIT_SHA `b4207e5f`, overlay
`deploy/aws/Dockerfile.flu_age_01` on `campaign-7e1b54bc`), jobdef
`picard-flu-rhythm-ab:6` (a duplicate `:5` registered with identical
content — first register call returned no query output; `:6` is the
submitted revision), queue `picard-campaign-queue` (Spot). Canary array
`558ee5dd-9047-4ad2-a146-4d923420d87b`: **20/20 SUCCEEDED, ~3 min wall.**
Prefix `campaign/flu_age_01/` (`on/flu_exp_12d/s8105–8124.zip` only).

## Measured verdict (canary only — full census declined)

**The confined endpoint did not move.** On the same 20 seeds / on arm,
confined cabinmate SAR is **6/66 = 9.1% [4.2–18.4] — identical to
`8c03e9d7`**, and **18/20 cells are bit-identical** (same
`telemetry_sha256`): the age terms are deterministic band lookups, so
the dose/delivery/conversion draw stream is untouched. The 2 diverging
cells sit outside the confined surface: s8113 shares its epoch-74
acquisition verbatim, then gained three `caregiver:influenza_a` crew
conversions (n_acquired 2 → 5) — a flipped presentation/severity outcome
propagating through crew service state; s8111 same counts, different
pedigree. Consistent with the mechanism: presentation/severity age
structure is post-infection — it can move reported/illness surfaces and
open-voyage acquisition, not confined-window delivery.

The user declined the 2×300-cell full census on this evidence
("satisfied we are doing as ok as before"). What remains unmeasured:
whether the larger hulls' crew scale amplifies the caregiver-pathway
divergence seen on s8113, and the reporting-side surfaces
(ever_ill/reported shares, severe mix by band) the age draws target
directly — conditioned-cell presentations are import-dominated and
mostly forced, so the free-draw flips are expected to be rare. The
canary zips remain in the prefix; a later census can resume by
submitting the off/on arrays (indices 0–299) against jobdef
`picard-flu-rhythm-ab:6` — completed cells skip via the entrypoint's
head-object check.
