# HEAT-V1
**Date:** 2026-09-30
**Commit:** 98d0edd2
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 98d0edd2

The HEAT-V1 conditioned array: the surviving suspect class after
COOP-V1 (dose law), Θ, ASCERTAIN-V1 (channel), and SEED-GEOM-V1
(index/seed geometry) — a declared sweep over the pooled-route
**delivery machinery**, all expressible under the shipped arm grammar
with zero engine changes:

- **Axis A — airborne persistence** (the RH proxy; no humidity field
  exists in the engine): `pathogen_overrides.airborne_half_life_hours`
  ∈ {0.5, 1.1, 2.0, 4.0}h. 0.5 = humidified corner (the cooling
  direction, marine-HVAC inference ~30–45% RH); 1.1 = shipped value
  written through the arm channel (seed-identical expectation); 2.0/4.0
  = dry corners (heating direction).
- **Axis B — pooled-route efficiency**:
  `profile_route_efficiency_multipliers` on droplet and hvac_airborne
  singly and jointly at {×0.5, ×0.25, ×0.1} of shipped (droplet
  0.3 → 0.15/0.075/0.03; absolute resolved values declared).
- **Axis C — per-shedder reach budgets**: `exposure_cap` corners —
  CAP_OFF (unbounded), CAP_POLY (legacy POLYMOD-uniform fallback via
  `activity_contacts.enabled: false`), CAP_ACT_HALF (structured table
  ×0.5), CAP_FR (`include_fixed_rings: true`, ring-first spend), and
  CAP_ACT_HALF_FR (both). The shipped cap is already contact-structured
  (config ships `activity_contacts.enabled: true` with the authored
  unit table) — settled input corrected at design time.
- **Axis D — pool transport law**: `pathogen_pool_transport`
  {airflow, none} — the only variants the grammar admits.
- **Axis E — interaction corner**: IX_HL0P5_JX0P1 = coldest declared
  persistence × joint efficiency (0.5h × joint ×0.1).

Lattice: 22 arms (19 delivery + D0_declared baseline + REF_M0P56
channel-matched reference, the ASCERTAIN-V1 M0P56 overrides verbatim) ×
θ {1e11, 2.37e11, 1e12} × seeds 20200205–14 = 660 cells. Design
`picard_framework/runs/covid_heat_v1_design.json` (PR #791,
admissibility frozen before any cell ran). Anchors: covid.T1 = 197
recorded onsets / before_share 0.173 (±0.10 declared window) and the
held-out serology band covid.H5 = infections_total ∈ [712, 960]. No
constants fitted.

## Execution (measured)

Two AWS Batch array jobs on `picard-campaign-queue` (Spot, no drought),
job-def `picard-covid-boarding-screen:37` digest-pinned to
`picard-campaign@sha256:4143ba7c…60d9` (image `covid-heat-v1-98d0edd2`
built at merged SHA `98d0edd2`, design inside image): canary
`d62e1cbe-aff1-49ed-a514-e01251200321` (cells 0–219, all 22 arms at the
anchor θ) then remainder `9db8d323-d0fd-480d-8b86-532d7d5e7d00` (cells
220–659). **660/660 cells SUCCEEDED, zero child failures, ~25–35
min/cell.** Payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_heat_v1/98d0edd2/cells/`;
readout `tools/covid_heat_readout.py` →
`campaign_results/covid_heat_v1/readout_full.json`.

Delivery audit on every cell: **0/660 failures** — `payload.delivery`
echoes the arm's declared resolved constants verbatim
(`airborne_half_life_hours`, the merged
`route_efficiency_multipliers` map, `pathogen_pool_transport`, the
`exposure_cap` block + `exposure_cap_active` flag, the resolved
`activity_contacts` table incl. the None-resolution on CAP_POLY), the
record's seed geometry is constant (count 1, onset −1.0, passenger),
and REF_M0P56 carries the M0P56 channel echoes verbatim. HL_1P1 is
seed-identical to D0 everywhere as declared (paired Δinf 0, Δbshr
0.000 at all three θ) — the arm channel writes shipped constants
exactly.

## Readout — both-legs test

Per (θ, arm): takeoff-seed (recorded_onsets ≥ 10) median and q05–q95 of
recorded_onsets, infections_total, and before_share. Rows with < 5
takeoff seeds are insufficient-mass, not failed. **Bold** = inside the
declared band/window.

| θ | arm | takeoff | rec med | inf med [q05–q95] | bshr med [q05–q95] |
|---|---|---|---|---|---|
| 1e+11 | CAP_ACT_HALF | 7/10 | 2,839 | 3,519 [1,617–3,550] | 0.438 [0.024–0.971] |
| 1e+11 | CAP_ACT_HALF_FR | 7/10 | 3,361 | 3,519 [1,129–3,544] | 0.487 [0.008–0.958] |
| 1e+11 | CAP_FR | 9/10 | 2,638 | 3,544 [932–3,571] | 0.767 [0.000–0.976] |
| 1e+11 | CAP_OFF | 10/10 | 3,509 | 3,547 [3,495–3,560] | 0.818 [0.596–0.984] |
| 1e+11 | CAP_POLY | 8/10 | 3,454 | 3,540 [3,062–3,545] | 0.685 [0.112–0.973] |
| 1e+11 | D0_declared | 8/10 | 2,882 | 3,547 [1,819–3,563] | 0.821 [0.013–0.977] |
| 1e+11 | DROP_X0P1 | 7/10 | 2,574 | 3,072 [22–3,476] | **0.236** [0.055–0.931] |
| 1e+11 | DROP_X0P25 | 6/10 | 2,440 | 3,476 [1,114–3,507] | 0.550 [0.005–0.959] |
| 1e+11 | DROP_X0P5 | 6/10 | 2,781 | 3,482 [1,077–3,567] | 0.376 [0.003–0.964] |
| 1e+11 | HL_0P5 | 8/10 | 2,872 | 3,545 [1,818–3,578] | 0.824 [0.013–0.977] |
| 1e+11 | HL_1P1 | 8/10 | 2,882 | 3,547 [1,819–3,563] | 0.821 [0.013–0.977] |
| 1e+11 | HL_2P0 | 8/10 | 2,894 | 3,539 [1,827–3,562] | 0.821 [0.013–0.977] |
| 1e+11 | HL_4P0 | 8/10 | 2,902 | 3,546 [1,827–3,570] | 0.822 [0.013–0.976] |
| 1e+11 | HVAC_X0P1 | 8/10 | 2,883 | 3,551 [1,807–3,554] | 0.820 [0.013–0.974] |
| 1e+11 | HVAC_X0P25 | 8/10 | 2,869 | 3,543 [1,815–3,557] | 0.818 [0.013–0.975] |
| 1e+11 | HVAC_X0P5 | 8/10 | 2,885 | 3,539 [1,821–3,564] | 0.821 [0.013–0.977] |
| 1e+11 | IX_HL0P5_JX0P1 | 7/10 | 2,666 | 3,044 [22–3,505] | **0.239** [0.062–0.944] |
| 1e+11 | JOINT_X0P1 | 7/10 | 2,664 | 3,066 [22–3,487] | **0.244** [0.060–0.950] |
| 1e+11 | JOINT_X0P25 | 6/10 | 2,448 | 3,489 [1,108–3,524] | 0.561 [0.005–0.968] |
| 1e+11 | JOINT_X0P5 | 6/10 | 2,797 | 3,471 [1,070–3,561] | 0.372 [0.003–0.966] |
| 1e+11 | POOL_NONE | 8/10 | 2,813 | 3,544 [17–3,572] | 0.754 [0.016–0.977] |
| 1e+11 | REF_M0P56 | 8/10 | 215 | 3,536 [1,819–3,563] | 0.888 [0.040–0.994] |
| 2.37e+11 | CAP_ACT_HALF | 8/10 | 3,321 | 3,537 [2,326–3,570] | 0.490 [0.017–0.976] |
| 2.37e+11 | CAP_ACT_HALF_FR | 8/10 | 3,347 | 3,560 [73–3,581] | 0.615 [0.049–0.978] |
| 2.37e+11 | CAP_FR | 9/10 | 2,417 | 3,461 [1,565–3,587] | **0.205** [0.008–0.981] |
| 2.37e+11 | CAP_OFF | 10/10 | 3,462 | 3,579 [3,570–3,599] | 0.933 [0.910–0.982] |
| 2.37e+11 | CAP_POLY | 10/10 | 3,368 | 3,557 [2,298–3,591] | 0.738 [0.016–0.978] |
| 2.37e+11 | D0_declared | 7/10 | 3,008 | 3,558 [2,877–3,589] | 0.606 [0.022–0.980] |
| 2.37e+11 | DROP_X0P1 | 5/10 | 2,926 | 3,464 [1,501–3,532] | 0.494 [0.083–0.967] |
| 2.37e+11 | DROP_X0P25 | 6/10 | 2,537 | 3,491 [1,094–3,560] | 0.406 [0.006–0.976] |
| 2.37e+11 | DROP_X0P5 | 6/10 | 3,161 | 3,570 [3,245–3,576] | 0.641 [0.098–0.978] |
| 2.37e+11 | HL_0P5 | 7/10 | 3,040 | 3,560 [2,889–3,585] | 0.606 [0.022–0.981] |
| 2.37e+11 | HL_1P1 | 7/10 | 3,008 | 3,558 [2,877–3,589] | 0.606 [0.022–0.980] |
| 2.37e+11 | HL_2P0 | 7/10 | 3,007 | 3,560 [2,900–3,589] | 0.612 [0.022–0.982] |
| 2.37e+11 | HL_4P0 | 7/10 | 3,001 | 3,556 [2,893–3,596] | 0.606 [0.022–0.981] |
| 2.37e+11 | HVAC_X0P1 | 7/10 | 3,041 | 3,549 [2,872–3,581] | 0.607 [0.022–0.981] |
| 2.37e+11 | HVAC_X0P25 | 7/10 | 3,068 | 3,553 [2,881–3,584] | 0.606 [0.022–0.983] |
| 2.37e+11 | HVAC_X0P5 | 7/10 | 3,067 | 3,562 [2,883–3,584] | 0.604 [0.022–0.982] |
| 2.37e+11 | IX_HL0P5_JX0P1 | 5/10 | 2,878 | 3,455 [1,567–3,517] | 0.468 [0.080–0.956] |
| 2.37e+11 | JOINT_X0P1 | 5/10 | 2,886 | 3,437 [1,577–3,523] | 0.468 [0.081–0.964] |
| 2.37e+11 | JOINT_X0P25 | 6/10 | 2,513 | 3,488 [1,040–3,554] | 0.401 [0.007–0.972] |
| 2.37e+11 | JOINT_X0P5 | 6/10 | 3,144 | 3,560 [3,231–3,574] | 0.641 [0.101–0.979] |
| 2.37e+11 | POOL_NONE | 7/10 | 3,413 | 3,552 [3,365–3,587] | 0.674 [0.129–0.982] |
| 2.37e+11 | REF_M0P56 | 7/10 | 234 | 3,558 [2,877–3,595] | 0.635 [0.040–0.975] |
| 1e+12 | CAP_ACT_HALF | 9/10 | 3,559 | 3,598 [3,337–3,614] | 0.915 [0.064–0.982] |
| 1e+12 | CAP_ACT_HALF_FR | 9/10 | 3,562 | 3,589 [3,352–3,615] | 0.819 [0.088–0.984] |
| 1e+12 | CAP_FR | 9/10 | 3,555 | 3,591 [3,568–3,614] | 0.814 [0.419–0.988] |
| 1e+12 | CAP_OFF | 10/10 | 2,509 | 3,610 [3,594–3,632] | 0.982 [0.972–0.987] |
| 1e+12 | CAP_POLY | 10/10 | 3,420 | 3,601 [3,591–3,610] | 0.933 [0.595–0.986] |
| 1e+12 | D0_declared | 9/10 | 3,542 | 3,599 [3,537–3,609] | 0.764 [0.385–0.987] |
| 1e+12 | DROP_X0P1 | 8/10 | 2,916 | 3,538 [1,873–3,574] | 0.785 [0.017–0.980] |
| 1e+12 | DROP_X0P25 | 7/10 | 2,608 | 3,573 [2,718–3,595] | 0.704 [0.017–0.985] |
| 1e+12 | DROP_X0P5 | 7/10 | 3,489 | 3,584 [3,296–3,598] | 0.899 [0.040–0.985] |
| 1e+12 | HL_0P5 | 9/10 | 3,534 | 3,599 [3,542–3,613] | 0.757 [0.386–0.985] |
| 1e+12 | HL_1P1 | 9/10 | 3,542 | 3,599 [3,537–3,609] | 0.764 [0.385–0.987] |
| 1e+12 | HL_2P0 | 9/10 | 3,550 | 3,599 [3,535–3,617] | 0.767 [0.386–0.987] |
| 1e+12 | HL_4P0 | 9/10 | 3,550 | 3,598 [3,537–3,615] | 0.762 [0.385–0.987] |
| 1e+12 | HVAC_X0P1 | 9/10 | 3,528 | 3,596 [3,535–3,617] | 0.758 [0.381–0.986] |
| 1e+12 | HVAC_X0P25 | 9/10 | 3,545 | 3,593 [3,540–3,622] | 0.757 [0.381–0.987] |
| 1e+12 | HVAC_X0P5 | 9/10 | 3,540 | 3,599 [3,534–3,612] | 0.757 [0.381–0.985] |
| 1e+12 | IX_HL0P5_JX0P1 | 8/10 | 2,953 | 3,545 [1,816–3,563] | 0.799 [0.013–0.976] |
| 1e+12 | JOINT_X0P1 | 8/10 | 2,945 | 3,539 [1,821–3,560] | 0.809 [0.013–0.976] |
| 1e+12 | JOINT_X0P25 | 7/10 | 2,571 | 3,561 [2,701–3,587] | 0.696 [0.018–0.982] |
| 1e+12 | JOINT_X0P5 | 7/10 | 3,482 | 3,584 [3,298–3,597] | 0.901 [0.040–0.984] |
| 1e+12 | POOL_NONE | 9/10 | 3,541 | 3,611 [3,554–3,623] | 0.842 [0.517–0.986] |
| 1e+12 | REF_M0P56 | 9/10 | 270 | 3,594 [3,537–3,609] | 0.836 [0.463–0.992] |

**Does any declared delivery arm move infections_total into [712,960]
AND before_share toward 0.173 ± 0.10 simultaneously? No — no row moves
both legs, and no row's median approaches the truth band at any θ.**

- **Truth leg (never close).** Every takeoff row medians
  infections_total 3,044–3,611 (~82–97% of the 3,710 aboard). The
  lowest row median is the deepest declared corner — IX_HL0P5_JX0P1
  and JOINT_X0P1 @1e11 at ~3,044–3,072, still ~3.2× the band ceiling.
  Seed-paired Δinf vs D0 (same takeoff seeds) is real but saturating:
  ≈ −230 @1e11, −66 @anchor, −68 @1e12 on the joint ×0.1 corner —
  ×0.1 pooled-route efficiency removes <7% of the ignited burn. The
  dry well is **not** θ-masked: the axis's best purchase is at the
  lowest θ and still lands >3× over the ceiling.
- **Timing leg (landings are takeoff-set composition).** Four row
  medians land in 0.173 ± 0.10: CAP_FR@anchor = 0.205 and
  DROP_X0P1 / JOINT_X0P1 / IX @1e11 ≈ 0.236–0.244. But seed-paired
  Δbshr ≈ 0 to −0.06 on those rows (CAP_FR@anchor +0.001 — the same
  include_fixed_rings mechanism and the same signature as
  SEED-GEOM-V1's FR_IN): the landing is which seeds clear the takeoff
  gate, not per-seed slowing. The largest paired per-seed timing
  shifts anywhere on the lattice (−0.24/−0.25 on DROP/JOINT_X0P25
  @1e11; −0.16 to −0.19 on the X0P1 corner @1e12) still leave row
  medians ≥ 0.40.
- **Count leg (observational).** Every non-channel takeoff row medians
  2,440–3,562 recorded onsets; REF_M0P56 reproduces its measured read
  exactly (215/234/270 by θ) — count-matched as designed, truth and
  timing unchanged.
- **Closest single cell** (not a row effect): CAP_FR@1e11 s20200207 —
  178 recorded / **932 infected, inside the H5 band** — the identical
  cell SEED-GEOM-V1's FR_IN produced (same mechanism), a suppressed
  late-start outbreak at before_share 0.000. Count and truth anchors
  are cell-reachable under deep cooling; timing is not, and nothing
  holds them systematically.

## Readout — route decomposition (the growth-rate mechanism test)

Pooled over takeoff seeds, `seed_ring.aboard_window_by_route` and
`during_quarantine_by_route` / `_by_zone_class` / `_by_role`:

- **The pooled-route carrier is droplet, nearly exclusively.** On D0,
  aboard-window acquisitions pool to droplet ~99.7% at every θ
  (5,760/5,777 @1e11; 5,931/5,947 @anchor; 8,330/8,337 @1e12), with
  hvac_airborne ~0.2% and direct_contact ~0.1%. The same split holds
  during quarantine (droplet ~99%). Measured consequence: every arm
  that only cools hvac or the pool is inert *by construction* —
  HVAC_X{0.5,0.25,0.1} rows are D0-identical at every depth and θ
  (seed-paired |Δinf| ≤ 5, |Δbshr| ≤ 0.001), HL_{0.5…4.0} are likewise
  dead (|Δinf| ≤ 1 — the airborne pool whose persistence the knob
  governs carries <1% of acquisitions), and POOL_NONE removes the
  zone-pool transport law outright for paired Δinf +4…+17. The deep
  joint arms' effect is entirely the droplet component: JOINT_X0P5
  ≈ DROP_X0P5 seed-for-seed (Δinf −44 vs −42 @1e11, −21 vs −1 @anchor,
  −14 vs −15 @1e12).
- **Cooling lands on droplet and *defers*, it does not shrink.** On
  the deep droplet/joint arms @1e11 the aboard-window droplet mass
  falls 5,760 → 3,396–3,456 (−41%) — but the suppressed mass
  re-burns during quarantine: during-stratum medians 100 → 773–779,
  during_share 0.028 → 0.375–0.381, day-16 onset kink 0.70 →
  2.56–2.74. Totals drop only ~7–14%. The deferred burn lands in the
  confinement channels: during-quarantine zone_class is cabin +
  crew_mess (JOINT_X0P1@1e11: cabin 2,139, crew_mess 1,795 of ~4,335),
  role split crew ~60% / passenger ~40% — the SOP-017 cabin-mate and
  crew-mess channels carrying the late wave.
- **Direction is suppression-shaped — the opposite of the record.**
  No arm shifts mass *earlier*; every effective arm shifts it *later*
  (across the quarantine boundary). The record's signature is the
  converse: mid-growth at confinement (incidence peaked ~Feb 2–4, at
  the SOP boundary) with a slower growth rate than the model's
  pre-quarantine burn. Delivery cooling postpones the model's burn
  into quarantine; it does not produce a slower pre-quarantine burn.
  The during-quarantine stratum never becomes dominant at row level
  (max median share 0.38 < 0.5 — the extended report trigger does not
  fire).

## Verdict

**`delivery_incapable` — measured, not merely unexpressed.** On the
declared lattice, every pooled-route heat axis was exercised to its
coldest corner and audited live: persistence 0.5–4.0h, route
efficiency to ×0.1 singly and jointly, reach budgets from unbounded
to ring-first, and the pool transport law deleted entirely. Cooling
lands on the droplet route and *reshapes* the curve (at θ ≤ anchor
the deep corners defer ~40% of droplet acquisitions across the
quarantine boundary), but no declared arm moves the truth leg toward
[712,960] — the minimum takeoff-seed median, ~3,044 at the coldest
declared corner, is ~3.2× the band ceiling — and every timing landing
is takeoff-set composition, not per-seed slowing. The record-side
bound (`dp_growth_cooling_bound.md`) estimated mid-growth truncation
would need pooled-route force ~×0.12–0.25 *sustained*: the measured
elasticity says even ×0.1 buys <7% truth change — the axis is roughly
an order of magnitude too weak at its deepest declared corner, and
what it does buy is delay, not scale.

Five suspect axes are now measured as unable to reach the truth band:
cooperative dose law (COOP-V1), Θ, ascertainment channel
(ASCERTAIN-V1), index/seed geometry (SEED-GEOM-V1), and pooled-route
delivery machinery (HEAT-V1). The residual is structural — on
ignition ~82–97% of aboard burns regardless of delivery constants.
The surviving suspect class is **susceptibility /
effective-population structure** (fraction susceptible, pre-existing
immunity, mixing saturation — the band ≈ 19–26% of 3,710 aboard) or
mid-voyage suppression *dynamics the model does not condition*
(behavior change after first detections), not further delivery tuning.

## What this cannot settle

Recorded in the design, unchanged: RH→evaporation→settling physics is
unmodeled — `airborne_half_life_hours` is the only RH proxy the
grammar admits, and it is measured here as governing a <1% channel;
per-route reach budgets are unmodeled (the cap is a single total
budget, not per-route); fomite/emesis routes were not conditioned
(near-zero share on this pathogen by construction); the
takeoff-set-composition caveat applies to every timing landing; and
the H5 band inherits ASCERTAIN-V1's reading of the serology record.
