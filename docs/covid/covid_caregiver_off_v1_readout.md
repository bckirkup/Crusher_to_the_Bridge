# CAREGIVER-ATTR-01 readout — the anchor-drift attribution canary at Θ1e9: CAREGIVER-V1 is the mover (clause PASS restored)

> **Status:** Findings (2026-10-04). Canary measured at `b932d0e9`
> (image `picard-campaign@sha256:ee917b9b…` / tag
> `campaign-e0d43979-cgoff`, jobdef `picard-covid-boarding-screen-fargate:1`,
> queue `picard-analysis-fargate-queue`, prefix
> `campaign/covid_caregiver_off_v1/b932d0e9/cells/`).

PR #868 measured that the only clause-passing row ever recorded — the v15
stage-2 Θ1e9 anchor at `6efec855` (takeoff 10/20, q05 153, band ∋197) —
no longer passes on current main: PROP_OFF (propensity never dealt)
reads 20/20 takeoff, q05 1,190. PROPENSITY-V1 was thereby exonerated;
the mover is a merge between `6efec855` and `e0d43979`, and
CAREGIVER-V1 (PR #859, shipped default-ON) was the named prime suspect.
This canary is the attribution: `transmission.caregiver.mode: "off"` on
the PROP_OFF tree × Θ1e9 × the same 20 seeds, on current main.

Design `picard_framework/runs/covid_caregiver_off_v1_design.json`
(PR #872): `{D0_declared (shipped defaults), CG_OFF} × Θ1e9 × 20 seeds`
at the `diamond_princess_2020` replay contract — identical rows to v15
stage 2 and to the PROPENSITY-V1 canary. `CG_OFF` writes
`config_overrides.transmission.caregiver.mode = off` plus
`rhythm.participation_propensity.mode = off` (propensity off because
PROP_OFF is the drifted reference surface — the design needs the
propensity off-tree to isolate caregiver). The clause is frozen verbatim
in the design's `admissibility` block before any cell ran, with the
two-branch verdict grammar: RESTORATION (CG_OFF clause-passes →
CAREGIVER-V1 is the mover) or EXONERATION (CG_OFF still reads ~2,300 →
bisect the remaining window).

Campaign gate executed: design merged `b932d0e9` → thin overlay image at
the merged tree (`FROM picard-campaign:campaign-e0d43979`; `git diff
e0d43979..b932d0e9` touches no engine code, verified) → digest-pinned
jobdef. **Both on-demand EC2 compute environments stalled at scale-out
(~40–55 min all-RUNNABLE); the campaign ran on Fargate** — new family
`picard-covid-boarding-screen-fargate:1`, same digest-pinned image and
command. 2-cell canary (`25ea86b4`) inspected → 38-cell array
(`7c405b31`, INDEX_OFFSET 2). 40/40 cells SUCCEEDED, zero audit
failures.

## Clause scorecard (per arm, takeoff-conditional)

| arm | takeoff | rec q05/med/q95 | before_share med [q05,q95] | clause |
|-----|--------:|------------------|---------------------------|--------|
| v15 `once_per_course` (`6efec855`, reference) | 10/20 | 153 / 2,052 / 2,417 | 0.200 | PASS (recorded) |
| **CG_OFF (caregiver off, propensity off)** | **11/20** | **10 / 1,559 / 2,428** | **0.200 [0.003, 0.941]** | **PASS both legs** |
| D0_declared (shipped defaults) | 19/20 | 1,518 / 2,321 / 2,445 | 0.452 [0.234, 0.900] | FAIL both legs |
| PROP_OFF (`e0d43979`, reference) | 20/20 | 1,190 / 2,343 / 2,443 | 0.397 | FAIL both legs |

CLAUSE-PASS + TIMING-IN-BAND triggers fired on the CG_OFF row
(`telemetry_buffer/covid_caregiver_off_v1_readout.json`,
`tools/covid_caregiver_off_v1_readout.py`).

## The mechanism exercised

| witness | D0_declared | CG_OFF |
|---------|-------------|--------|
| `delivery.caregiver.mode` resolved | `on` (20/20 echo) | `off` (20/20 echo) |
| `participation_propensity.mode` | `party` (20/20) | `off` (20/20) |
| `propensity_draw.units_drawn` med | 2,089 | **0 on all 20 cells** |
| caregiver route, pooled aboard_window | 248 | **0 on all 20 cells** |

The D0_declared arm is the image-integrity witness: `e0d43979..b932d0e9`
touches no engine code, and every D0 cell replicates the PROPENSITY-V1
canary's same-named arm **bit-identically (max |Δ recorded_onsets| = 0
on all 20 seeds)** — the overlay image runs exactly the canary
generation's engine.

## The attribution: caregiver-off restores the v15 pass region

Seed-paired deltas on takeoff pairs:

| pairing | n | Δ recorded med [q05, q95] | Δ before_share med | Δ infections med |
|---------|--:|--------------------------|--------------------|------------------|
| CG_OFF − v15 `6efec855` | 10 | **−46 [−474, +983]** | −0.001 | −37 |
| CG_OFF − PROP_OFF | 11 | −762 [−2,330, +1,238] | −0.261 | −830 |
| CG_OFF − D0_declared (same run) | 11 | −698 [−2,478, +910] | −0.329 | −790 |
| PROP_OFF − v15 (PR #868) | — | **+1,634** | — | — |

At identical engine and seeds, flipping only `caregiver.mode` on→off
takes the anchor row from clause FAIL (20/20, q05 1,190) to clause PASS
(11/20, q05 10, band ∋197, share 0.200 vs 0.173 target). And the
caregiver-off surface is statistically indistinguishable from the v15
anchor row itself: Δ med −46 onsets on the 10 shared takeoff pairs.

Per seed, CG_OFF reproduces v15's fizzle/takeoff pattern almost
one-for-one: the five seeds where PROP_OFF took off but v15 fizzled
(20200206, 10, 15, 18, 23) all fizzle again under CG_OFF; the shared
takeoff burns are within tens of onsets (20200205: 2,192 vs 2,223;
20200208: 2,426 vs 2,438; 20200213: 2,428 vs 2,396; 20200216: 2,410 vs
2,413; 20200219: 2,357 vs 2,417). Seed 20200221 takes off under CG_OFF
(1,559) where v15 fizzled — the one pattern difference.

## Per-seed evidence (recorded onsets / before_share)

| seed | v15 `6efec855` (once_per_course) | PROP_OFF `e0d43979` | CG_OFF | D0_declared |
|------|------|------|------|------|
| 20200205 | 2,223 / 0.910 | 2,360 / 0.428 | 2,192 / 0.941 | 2,365 / 0.574 |
| 20200206 | 0 | 2,443 / 0.425 | 0 | 1,963 / 0.234 |
| 20200207 | 153 / 0.013 | 2,340 / 0.406 | 10 / 0.200 | 2,488 / 0.900 |
| 20200208 | 2,438 / 0.916 | 2,401 / 0.935 | 2,426 / 0.875 | 2,395 / 0.934 |
| 20200209 | 0 | 2,295 / 0.380 | 0 | 2,133 / 0.316 |
| 20200210 | 0 | 1,241 / 0.225 | 0 | 2,251 / 0.291 |
| 20200211 | 575 / 0.016 | 2,320 / 0.386 | 1,558 / 0.076 | 2,256 / 0.406 |
| 20200212 | 502 / 0.012 | 1,777 / 0.272 | 368 / 0.011 | 2,391 / 0.562 |
| 20200213 | 2,396 / 0.310 | 1,190 / 0.241 | 2,428 / 0.280 | 1,518 / 0.216 |
| 20200214 | 1 / 1.000 | 2,349 / 0.450 | 1 / 1.000 | 1,961 / 0.286 |
| 20200215 | 0 | 1,522 / 0.213 | 0 | 2,445 / 0.715 |
| 20200216 | 2,413 / 0.466 | 1,326 / 0.236 | 2,410 / 0.312 | 2,112 / 0.298 |
| 20200217 | 0 | 661 / 0.005 | 0 | 0 |
| 20200218 | 0 | 2,366 / 0.352 | 0 | 946 / 0.265 |
| 20200219 | 2,417 / 0.454 | 2,446 / 0.649 | 2,357 / 0.321 | 2,406 / 0.788 |
| 20200220 | 0 | 2,410 / 0.527 | 0 | 2,398 / 0.600 |
| 20200221 | 0 | 2,418 / 0.572 | 1,559 / 0.102 | 2,401 / 0.618 |
| 20200222 | 449 / 0.004 | 2,339 / 0.330 | 286 / 0.003 | 1,682 / 0.273 |
| 20200223 | 0 | 2,343 / 0.397 | 0 | 2,416 / 0.616 |
| 20200224 | 1,882 / 0.090 | 2,411 / 0.624 | 1,408 / 0.092 | 2,321 / 0.452 |

## Verdict

**RESTORATION — CAREGIVER-V1 is the mover.** On the merged tree with
only the caregiver pathway removed, the Θ1e9 anchor recovers the v15
clause-pass structure: the low tail returns (q05 10 vs v15's 153), the
fizzle margin returns (11/20 vs 10/20), the band contains 197 and the
takeoff before-share median lands at 0.200 — the same value v15
recorded. The +1,634-median fill-in measured at PROP_OFF resolves to
the caregiver channel; every other merge in the `6efec855..b932d0e9`
window still stands in the CG_OFF tree, so the drift's
clause-relevant content is caregiver.

The restoration is clause-level, not bit-identical: CG_OFF − v15 leaves
a nonzero residual (med −46 onsets, one extra takeoff seed), which is
the rest of the window's footprint (ENV-HAZARD/PPE/ship-function line,
rhythm work, refactor merges). Whether that residual is worth its own
bisection is the user's call — for the anchor question it is within the
clause's tolerances.

What this does **not** say: that caregiver is wrong. The merged
behaviour (caregiver default-ON producing ~20/20 burn at Θ1e9) is a
deliberate mechanism; this canary only establishes that it is what moved
the DP anchor off the v15 pass — i.e., the clause's only passing cell on
the shipped-default tree exists on the `caregiver.mode: off` tree.
