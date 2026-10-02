# FLU-RHYTHM-01
**Date:** 2026-09-27
**Commit:** 6e60918c
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 07d9856c

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

**Execution (as run):** Spot capacity on `picard-campaign-queue` was a
drought (~75 min, zero cells dispatched; sibling noro/covid arrays were
equally starved). The two Spot arrays were terminated and re-submitted
on `picard-analysis-queue` (On-Demand EC2, same job definition rev 2 and
image digest): off `13bd928c-03ad-41ec-91be-8624697cd92d`, on
`f666ea1d-2a84-4125-a266-3970ec9fd6c9` — 800/800 SUCCEEDED, 0 FAILED.
Zips under `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_rhythm_01/{off,on}/`;
readout `tools/flu_rhythm_ab_readout.py --root telemetry_buffer/flu_rhythm_ab/runs`
(800 zips, synced but not committed — full JSON at
`telemetry_buffer/flu_rhythm_ab/readout_full.json` locally).

## Results

### 1. Confined cabinmate floor (n=100 cells/class/arm; declared SOP-017, k=0.0006)

| class | off attack [Wilson] | on attack [Wilson] | paired Δ mean | floor 15–25% |
|---|---|---|---|---|
| classic_cruise_1900 | 197/1575 = 12.5% [11.0–14.2] | 227/1664 = 13.6% [12.1–15.4] | +0.3 pp | both below |
| expedition_cruise_450 | 44/368 = 12.0% [9.0–15.7] | 43/381 = 11.3% [8.5–14.9] | +0.7 pp | both below |
| mega_cruise_5000 | 481/4575 = 10.5% [9.7–11.4] | 715/5603 = 12.8% [11.9–13.7] | +1.6 pp | both below |
| spirit_cruise_3000 | 369/2529 = 14.6% [13.3–16.0] | 399/2783 = 14.3% [13.1–15.7] | −0.1 pp | both below |

**Comparability check:** on the FLU-DELIVERY-01 seeds verbatim
(classic, s8105+s8106, declared SOP-017) the off arm reproduces
**7/34 = 20.6% exactly** (6/28 + 1/6) — conditioning confirmed
in-band; the on arm on those same seeds lands 3/32.

Rhythm does not move flu out of band; the paired move is ≤1.6 pp on
every class and changes sign by class. The trigger condition ("flu exits
the 15–25% band **under rhythm**") is not a rhythm break: the labelled
baseline sits below the floor too — see verdict.

### 2. Delivered confined dose + mechanism metrics

| class | arm | delivered dose (Σ) | per-slot dose p50 | slots | implied SAR p50 | dosed-set med | challenged share | commitments |
|---|---|---|---|---|---|---|---|---|
| cls | off→on | 3.57e5 → 4.44e5 (+24%) | 14.9 → 16.3 | 1575 → 1664 | 0.011 → 0.015 | 1130 → 1100 | 0.795 → 0.797 | 0 → 8914 |
| exp | off→on | 8.7e4 → 8.7e4 (≈0) | 11.9 → 12.1 | 368 → 381 | 0.009 → 0.009 | 188 → 193 | 0.718 → 0.756 | 0 → 1656 |
| mega | off→on | 8.2e5 → 1.36e6 (+66%) | 6.6 → 14.7 (×2.2) | 4575 → 5603 | 0.005 → 0.012 | 4934 → 4988 | 0.800 → 0.800 | 0 → 29187 |
| spr | off→on | 6.8e5 → 7.9e5 (+16%) | 17.8 → 24.7 | 2529 → 2783 | 0.015 → 0.018 | 1842 → 1788 | 0.800 → 0.800 | 0 → 13761 |

The sleep-window cabin curve **raises** pair exposure on the big ships:
rhythm delivers 16–66% more confined-window dose and grows the confined
slot count (+4% exp to +22% mega — more mates co-confined with index
cases). Capture ratio is flat at ~5–8e-6 both arms (the ~9e-6 DELIVERY
figure holds). Dosed-set medians and challenged share are unmoved —
rhythm repartitions *when* agents co-locate, not the size of the exposed
set.

**Corridor-front correlation: emitted but degenerate for flu.** On-arm
cells record 400–1000 corridor-egress epochs per class, but egress
occupancy is 0.0 against a 0.0 baseline — flu produces no
emesis/post-prandial surge events, so the covid-facing corridor fields
carry no signal on this pathogen (off arm emits no egress rows at all).
Reported as emitted-null, not a readout gap.

### 3. Stage decomposition of the move

No band exit occurred, but the largest paired move (mega +2.3 pp point)
decomposes as **delivery-shaped, not conversion-shaped**:

- **Emission:** `emitted_post_confinement` +40% on mega (+7–11%
  elsewhere) — rhythm's sleep-window schedule holds index cases in the
  cabin during the confinement window, emitting more post-confinement
  copies into the cabin compartment.
- **Delivery:** delivered dose +66% on mega; per-slot dose p50 ×2.2 —
  the cabin curve concentrates dose into confined slots.
- **Conversion:** implied SAR p50 rises with dose (0.005 → 0.012 mega)
  but the confined **denominator grows faster** (+22% slots), and the
  added slots are the lower-dose marginal pairs — attack fraction moves
  ≪ the dose move. `sum_hazard` scales with delivered dose; no
  conversion-stage break.

### 4. Verdict

**The clean arm stays clean.** Under realistic daily-program
partitioning, confined cabinmate attack moves ≤1.6 pp paired on every
class and the arm's level is unchanged in kind: rhythm re-times
co-presence (commitments 16.5k–29k per class) but does not touch the
challenged share or dosed-set size.

The residual is **floor-shaped, not mechanism-shaped.** Both arms sit
below the 15–25% floor band at n=100/class — but FLU-DELIVERY-01's own
k-implied expectation for confined SAR was **13.4%**, and the measured
baseline (10.5–14.6%) brackets it. The 20.6% in-band reading was the
upper tail of a 34-slot sample (Wilson ~9.5–38%). The floor band was
drawn around the noisy point estimate, not the expectation: **the band
itself needs re-calibration** (recommend the floor spec owner re-draw it
around the delivered-dose-derived SAR expectation, or widen n before
treating 15% as a hard edge). This is a floor-spec finding for the audit
session, not a rhythm defect and not a flu delivery defect — filed here,
not fixed. **Resolved by `CABIN-FLOOR-03` / `docs/confined_attack_floor_spec.md`:
the 15–25% band is withdrawn (it was the norovirus Wikswo/Chimonas pair,
not a flu quantity); the corrected band is the declared-k expected SAR,
3.7–12.1% pooled, and both arms sit inside it.**

## Measured verdict — 800-cell re-census at `1ab8dd98`

Measured at `1ab8dd98` (merge of #823 — flu/noro/smalln probe wrappers
forwarded for the revised engine call signatures: `shedder_ctx` +
`agent_coop_doses`) on the **same frozen 800 cells** — same manifest
(`flu_rhythm_01_manifest.json`, seeds 8105–8204, declared SOP-017, 288
epochs, isolated `influenza_a`, k=0.0006), read-only census into the
fresh prefix `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_rhythm_02/`.

**Execution:** image `picard-campaign@sha256:f13ef26a4a68a68b051c2db3469331fc3c97c1911f9f618b5a99cbbae41a74ae`
(tag `flu-rhythm-02-1ab8dd98`, ENGINE_GIT_SHA `1ab8dd98`), jobdef
`picard-flu-rhythm-ab:3`. Canary index 0 both arms inspected clean
(contract intact; off commitments 0/attached false, on 1654/true).
Arrays on `picard-campaign-queue` (Spot — capacity held throughout, ~50
min wall): off `feef57be-931d-470e-ab18-8dab6d829e73`, on
`e8655f68-53e9-402b-9d70-9d1135c0ca45` — **800/800 SUCCEEDED, 0 FAILED**.
Readout `tools/flu_rhythm_ab_readout.py --root telemetry_buffer/flu_rhythm_ab/runs_02`
(full JSON `telemetry_buffer/flu_rhythm_ab/readout_02_full.json`, local).

### Re-censused confined cabinmate floor (n=100/class/arm; prior at `07d9856c`)

| class | off attack [Wilson] | on attack [Wilson] | paired Δ mean | floor |
|---|---|---|---|---|
| classic_cruise_1900 | 63/854 = **7.4%** [5.8–9.3] (was 12.5%) | 64/853 = **7.5%** [5.9–9.5] (was 13.6%) | +0.2 pp | both in |
| expedition_cruise_450 | 37/314 = **11.8%** [8.7–15.8] (was 12.0%) | 39/311 = **12.5%** [9.3–16.7] (was 11.3%) | +1.4 pp | both in |
| mega_cruise_5000 | 143/2612 = **5.5%** [4.7–6.4] (was 10.5%) | 146/2602 = **5.6%** [4.8–6.6] (was 12.8%) | +0.0 pp | both in |
| spirit_cruise_3000 | 93/1204 = **7.7%** [6.3–9.4] (was 14.6%) | 87/1207 = **7.2%** [5.9–8.8] (was 14.3%) | −0.2 pp | both in |

**The level changed — dose-shaped, not conversion-shaped.** Between
`07d9856c` and `1ab8dd98` the model revisions (hand-carriage rebuild,
cabin compartment, near-field two-box, droplet field split,
per-partner contact, coop dosing — per-component attribution not run,
inference pending on the diff) cut **per-slot delivered confined dose
~5–8×** on the three larger hulls (p50: cls 14.9→2.6, spr 17.8→2.1,
mega 6.6→1.5 copies; expedition held 11.9→13.3) and shrank the confined
slot count ~2× (cls 1575→854, mega 4575→2612, spr 2529→1204; exp
368→314). Attack tracked dose down through implied SAR (p50 cls
0.011→0.0014, mega 0.005→0.0008, spr 0.015→0.0010; exp 0.009→0.0070).
Measured attack now reads ~1.2–1.4× the declared-k expected SAR pooled
(e.g. mega 5.5% vs E[SAR] 4.0%) — every class still inside the
CABIN-FLOOR-03 band on the Wilson-overlap rule.

**Rhythm is now a pure scheduling effect — the dose amplification is
gone.** Paired Δ median 0.000 on every class (was +0.3–1.6 pp); on-arm
delivered confined dose ≈ off (+16% cls, ≈flat elsewhere — was +24–66%);
per-slot dose p50 slightly *lower* on (sleep-window mates share the same
slot pool). Wiring unchanged: attached 100/100 cells on, commitments
1.7k–29k medians, challenged share 0.35–0.39 (was ~0.80 — the dosed-set
medians also fell, cls 1130→5, spr 1842→7, mega 4934→15, exp 188→2 —
the per-partner contact mode draws partner-bounded sets, not zone
pools). `hvac_dose_copies = 0` to confined slots in both arms — the
delivered confined dose is entirely contact/plume/droplet-stage now.
Capture ratio holds ~6–11e-6 both arms.

**Verdict: the clean arm stays clean; the floor statement needs
re-reading against the new level.** Confined flu cabinmate SAR at
`1ab8dd98` is **5.5–12.5%** pooled across classes both arms (was
10.5–14.6%), expedition unchanged — the revisions moved the big-hull
cabin dose structure, not the small-hull one. The prior section-4
verdict ("residual is floor-shaped") is superseded on level but
unchanged in kind: no band exit, no mechanism-shaped move, rhythm
inert on this arm. No anchor fit, no retune; the per-revision dose
attribution is the open question, filed for a follow-up session.
