# SEED-GEOM-V1
**Date:** 2026-09-30
**Commit:** 1dfac0e4
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 1dfac0e4

The SEED-GEOM-V1 conditioned array: the fourth and surviving suspect
axis after COOP-V1, Θ, and ASCERTAIN-V1 — a declared sweep over
index/seed structure on three axes, all expressible under the shipped
`seed_patch`/`transmission_overrides` grammar with zero engine changes:

- **Axis A — index onset epoch** vs boarding day-0: `seed_patch.onset_day`
  ∈ {−6, −4, −2, 0, +2, +4, +6} (D0 baseline is onset −1.0; ONSET_P6 is
  the silent-aboard corner — onset lands one epoch after the day-5
  departure).
- **Axis B — ring/placement membership**: ROLE_CREW (index seeded into a
  crew role), ROLE_ANY (role filter removed — any aboard host), FR_IN
  (`exposure_cap.include_fixed_rings: true`, the RING-CAP-V1 shape —
  fixed rings count toward the exposure cap), CREW_FR_IN (both).
- **Axis C — co-primary count / day-0 exposure breadth**:
  `seed_patch.count` ∈ {2, 8, 30} distinct hosts.

Lattice: 16 arms (13 geometry + D0_declared baseline + REF_M0P56
channel-matched reference, the ASCERTAIN-V1 M0P56 overrides verbatim) ×
θ {1e11, 2.37e11, 1e12} × seeds 20200205–14 = 480 cells. Design
`picard_framework/runs/covid_seed_geom_v1_design.json` (PR #786,
admissibility frozen before any cell ran). Anchors: covid.T1 = 197
recorded onsets / before_share 0.173 (±0.10 declared window) and the
held-out serology band covid.H5 = infections_total ∈ [712, 960]. No
constants fitted.

## Execution (measured)

Two AWS Batch array jobs on `picard-campaign-queue` (Spot, no drought),
job-def `picard-covid-boarding-screen:34` digest-pinned to
`picard-campaign@sha256:976993cd…` (image `seed-geom-v1-1dfac0e4` built
at merged SHA `1dfac0e4`, design inside image): canary
`9e8e6b2c-b0c3-402b-9eb6-77f68a2b9075` (cells 0–159, all 16 arms at the
anchor θ) then remainder `29b5cc3e-1038-4f64-9519-a5dfb92faf16` (cells
160–479). **480/480 cells SUCCEEDED, zero child failures, ~7–12
min/cell.** Payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_seed_geom_v1/1dfac0e4/cells/`.

Index-geometry audit on every cell (tools/covid_seed_geom_readout.py):
**0/480 failures** — `seed_spec` echoes the declared patch verbatim
(onset_day/count/role incl. the removed-role arm), `seeded_count` ==
declared count, `seeded_hosts` placement readout matches the role
filter (all crew hosts in `CC_` zones on ROLE_CREW/CREW_FR_IN),
`exposure_cap_include_fixed_rings` echoes true on FR_IN/CREW_FR_IN only,
REF_M0P56 carries the M0P56 `onset_recording` + eligibility echoes
verbatim, and `index_onset_day` ≈ declared on all arms.

Two frozen secondary expectations were corrected at readout (readout
expectations only; payload echoes matched declarations throughout —
no design or engine change):

1. `index_onset_day` was expected null on ONSET_P6; measured ~6.0.
   `ever_presented` covers post-departure illness — the index departs
   day 5 and still presents at day 6, so the stamp lands. The aboard
   restriction lives in the shedding/window reads, not the onset stamp.
2. `index_shedding_at_day0` was expected true on ONSET_P2 (declared
   onset == the 2.0 presymptomatic boundary); measured False — a
   float-epsilon boundary (`6.8 − 8.8 = −2.0000000000000018 < −2.0`).
   Readback consistent: all P2/P4/P6 rows report shed fraction 0.

## Readout — both-legs test

Per (θ, arm): takeoff-seed (recorded_onsets ≥ 10) median and q05–q95 of
recorded_onsets, infections_total, and before_share. Rows with < 5
takeoff seeds are insufficient-mass, not failed.

| θ | arm | takeoff | rec med | inf med [q05–q95] | bshr med [q05–q95] |
|---|---|---|---|---|---|
| 1e+11 | D0_declared | 8/10 | 2,882 | 3,547 [1,819–3,563] | 0.821 [0.013–0.977] |
| 1e+11 | REF_M0P56 | 8/10 | 215 | 3,536 [1,819–3,563] | 0.888 [0.040–0.994] |
| 1e+11 | ONSET_M6 | 7/10 | 3,351 | 3,552 [3,394–3,577] | 0.845 [0.189–0.978] |
| 1e+11 | ONSET_M4 | 7/10 | 3,213 | 3,567 [3,276–3,591] | 0.934 [0.134–0.984] |
| 1e+11 | ONSET_M2 | 8/10 | 3,432 | 3,549 [1,665–3,576] | 0.735 [0.009–0.978] |
| 1e+11 | ONSET_P0 | 8/10 | 3,339 | 3,525 [1,053–3,573] | 0.671 [0.001–0.970] |
| 1e+11 | ONSET_P2 | 10/10 | 3,509 | 3,545 [3,435–3,571] | 0.666 [0.279–0.951] |
| 1e+11 | ONSET_P4 | 10/10 | 3,480 | 3,523 [3,407–3,572] | 0.675 [0.158–0.878] |
| 1e+11 | ONSET_P6 | 10/10 | 3,470 | 3,489 [1,511–3,524] | 0.395 [0.010–0.614] |
| 1e+11 | ROLE_CREW | 10/10 | 3,462 | 3,534 [1,841–3,562] | 0.744 [0.028–0.975] |
| 1e+11 | ROLE_ANY | 9/10 | 3,381 | 3,550 [3,388–3,570] | 0.667 [0.125–0.975] |
| 1e+11 | FR_IN | 9/10 | 2,638 | 3,544 [932–3,571] | 0.767 [0.000–0.976] |
| 1e+11 | CREW_FR_IN | 10/10 | 3,423 | 3,502 [1,008–3,572] | 0.673 [0.002–0.968] |
| 1e+11 | CP2 | 10/10 | 3,464 | 3,539 [3,116–3,575] | 0.814 [0.123–0.966] |
| 1e+11 | CP8 | 10/10 | 2,973 | 3,544 [3,527–3,574] | 0.963 [0.897–0.977] |
| 1e+11 | CP30 | 10/10 | 2,197 | 3,531 [3,512–3,544] | 0.974 [0.969–0.981] |
| 2.37e+11 | D0_declared | 7/10 | 3,008 | 3,558 [2,877–3,589] | 0.606 [0.022–0.980] |
| 2.37e+11 | REF_M0P56 | 7/10 | 234 | 3,558 [2,877–3,595] | 0.635 [0.040–0.975] |
| 2.37e+11 | ONSET_M6 | 7/10 | 3,102 | 3,580 [3,475–3,599] | 0.967 [0.203–0.985] |
| 2.37e+11 | ONSET_M4 | 8/10 | 3,461 | 3,576 [3,539–3,591] | 0.952 [0.570–0.982] |
| 2.37e+11 | ONSET_M2 | 8/10 | 3,470 | 3,575 [3,440–3,596] | 0.920 [0.198–0.985] |
| 2.37e+11 | ONSET_P0 | 8/10 | 3,502 | 3,577 [2,215–3,585] | 0.921 [0.014–0.977] |
| 2.37e+11 | ONSET_P2 | 10/10 | 3,399 | 3,564 [3,547–3,588] | 0.901 [0.592–0.961] |
| 2.37e+11 | ONSET_P4 | 10/10 | 3,521 | 3,566 [3,536–3,591] | 0.806 [0.423–0.935] |
| 2.37e+11 | ONSET_P6 | 10/10 | 3,544 | 3,553 [3,504–3,580] | 0.609 [0.333–0.829] |
| 2.37e+11 | ROLE_CREW | 10/10 | 3,426 | 3,568 [3,434–3,593] | 0.867 [0.250–0.972] |
| 2.37e+11 | ROLE_ANY | 9/10 | 3,514 | 3,572 [3,515–3,604] | 0.864 [0.448–0.980] |
| 2.37e+11 | FR_IN | 9/10 | 2,417 | 3,461 [1,565–3,587] | **0.205** [0.008–0.981] |
| 2.37e+11 | CREW_FR_IN | 10/10 | 3,485 | 3,581 [3,381–3,598] | 0.799 [0.177–0.981] |
| 2.37e+11 | CP2 | 10/10 | 3,396 | 3,573 [3,522–3,601] | 0.927 [0.432–0.972] |
| 2.37e+11 | CP8 | 10/10 | 2,683 | 3,560 [3,556–3,578] | 0.972 [0.900–0.985] |
| 2.37e+11 | CP30 | 10/10 | 1,900 | 3,546 [3,540–3,564] | 0.980 [0.976–0.984] |
| 1e+12 | D0_declared | 9/10 | 3,542 | 3,599 [3,537–3,609] | 0.764 [0.385–0.987] |
| 1e+12 | REF_M0P56 | 9/10 | 270 | 3,594 [3,537–3,609] | 0.836 [0.463–0.992] |
| 1e+12 | ONSET_M6 | 8/10 | 3,565 | 3,608 [3,597–3,614] | 0.977 [0.801–0.993] |
| 1e+12 | ONSET_M4 | 10/10 | 3,034 | 3,604 [3,592–3,625] | 0.942 [0.875–0.991] |
| 1e+12 | ONSET_M2 | 9/10 | 3,004 | 3,608 [3,594–3,618] | 0.976 [0.741–0.994] |
| 1e+12 | ONSET_P0 | 8/10 | 3,510 | 3,603 [3,592–3,625] | 0.960 [0.514–0.990] |
| 1e+12 | ONSET_P2 | 10/10 | 2,809 | 3,606 [3,591–3,631] | 0.979 [0.963–0.983] |
| 1e+12 | ONSET_P4 | 10/10 | 3,514 | 3,612 [3,591–3,619] | 0.946 [0.896–0.969] |
| 1e+12 | ONSET_P6 | 10/10 | 3,590 | 3,603 [3,598–3,630] | 0.823 [0.650–0.934] |
| 1e+12 | ROLE_CREW | 10/10 | 3,033 | 3,605 [3,595–3,622] | 0.971 [0.811–0.986] |
| 1e+12 | ROLE_ANY | 10/10 | 3,486 | 3,605 [3,504–3,640] | 0.946 [0.345–0.988] |
| 1e+12 | FR_IN | 9/10 | 3,555 | 3,591 [3,568–3,614] | 0.814 [0.419–0.988] |
| 1e+12 | CREW_FR_IN | 10/10 | 3,268 | 3,598 [3,596–3,627] | 0.963 [0.824–0.989] |
| 1e+12 | CP2 | 10/10 | 2,801 | 3,604 [3,556–3,620] | 0.981 [0.241–0.986] |
| 1e+12 | CP8 | 10/10 | 2,017 | 3,603 [3,593–3,620] | 0.985 [0.980–0.990] |
| 1e+12 | CP30 | 10/10 | 1,523 | 3,575 [3,567–3,596] | 0.985 [0.980–0.991] |

**Does any declared geometry move infections_total into [712,960] AND
before_share toward 0.173 ± 0.10 simultaneously? No — and no row moves
the truth leg at all.**

- **Truth leg (immovable).** Every takeoff row at every θ medians
  infections_total 3,461–3,612 (~93–97% of the 3,710 aboard) — q05–q95
  intersects the band on only two rows (FR_IN@1e11 q05 932,
  CREW_FR_IN@1e11 q05 1,008), and no row's median approaches it. The
  once-ignited burn is θ-invariant and geometry-invariant.
- **Timing leg (seed-correlated, not geometric).** Exactly one row
  median lands in the declared window: FR_IN@2.37e11 = 0.205. But its
  q05–q95 spans 0.008–0.981 and the seed-paired Δ vs D0 medians ≈ 0 —
  the landing is takeoff-set composition (FR_IN ignites two seeds D0
  fizzled, both late-start outbreaks at bshr 0.008–0.073), not a
  per-seed timing shift. The record's 0.173 sits inside D0's own
  cross-seed spread (s20200209 0.022, s20200212 0.057, s20200214 0.098
  — the lower tail, not a distinct geometry class).
- **Count leg (observational).** Every non-channel takeoff row medians
  1,523–3,590 recorded onsets — never inside [98.5, 394]; REF_M0P56
  reproduces its measured read exactly (215/234/270 by θ — count is
  count-matched as designed; truth and timing legs unchanged: the
  channel records a fraction of the same ~3.5e3 outbreak).

Direction of the legs per axis (paired-seed Δ medians vs D0 at anchor):

- **Onset epoch (A):** row-medians drift 0.967 (M6) → 0.609 (P6) — a
  later onset does shift recorded mass later — but paired Δs are
  noisy-signed (+0.28 on P2, −0.003 on P0, +0.035 on P6), so the drift
  is again mostly takeoff-set composition. Truth flat at every point.
- **Placement (B):** ROLE_CREW Δbshr +0.19, ROLE_ANY +0.34 — placement
  moves the timing leg away from the record. FR_IN's day-0 window is
  untouched (aboard_window_acquisitions median 3, identical to D0) yet
  it flips which seeds ignite late — the cap acts on secondary
  amplification, not on the index's own exposure.
- **Breadth (C):** aboard_window_acquisitions scales 3 → 516 (CP2) →
  2,270 (CP8) → 2,991 (CP30) while Δbshr +0.30/+0.37/+0.37 (earlier
  mass, further from 0.173) and infections flat — the ~1,000× day-0
  breadth change buys ~0× truth change: saturation, the same shape
  NORO-GENO-02 measured on imports (~6.5× introductions → ~1.4×
  aboard mass).
- **The closest single cell** (not a row effect): FR_IN@1e11
  s20200207 — 178 recorded (vs 197), 932 infections (**inside the
  H5 band**, first cell ever there) — but before_share 0.000: a
  suppressed, late-start outbreak. Count and truth anchors are
  cell-level reachable under θ-suppression + ring cap; timing is not,
  and nothing holds it systematically.

## Verdict

**`geometry_incapable` — measured, not merely unexpressed.** On the
declared lattice, index/seed geometry moves which seeds ignite and how
early the recorded mass piles up, but it cannot shrink the ignited
outbreak: the truth leg sits ~3.7× over the H5 band on every takeoff
row at every θ, and the timing anchor lies inside the baseline's own
cross-seed spread rather than on any arm. All four prior suspect axes
(dose law, Θ, ascertainment channel, seed/index structure) are now
measured as unable to reach the truth band: the residual is
truth-level and structural — on ignition, ~96% of aboard burns.

The record [712,960] ≈ 19–26% of the 3,710 aboard: reaching it needs a
mechanism that leaves most of the aboard population uninfected on an
ignited voyage — i.e. **susceptibility/effective-population structure**
(fraction susceptible, mixing saturation, pre-existing immunity), or
**mid-voyage suppression dynamics** the model does not currently
condition (behavior change, masking, voluntary isolation after the
first detected onsets), not further seed tuning. Seed/index structure
retires as the truth-gap suspect.

## What this cannot settle

Recorded in the design, unchanged: per-agent index placement (roles are
coarse), a ring-excluded index (no seed field deletes ring membership),
staggered/multi-epoch seeding (seed_patch touches seeds[0], no epoch
key), and the H5 subgroup caveat (band inherited from ASCERTAIN-V1's
reading). infection_age_days remains a null axis (COVID-SEED-GEOM-01).
