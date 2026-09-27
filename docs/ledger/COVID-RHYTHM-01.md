# COVID-RHYTHM-01
**Date:** 2026-09-27
**Commit:** e256e8cb
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** e256e8cb

Paired A/B of the rhythm layer (SHIP-RHYTHM-01 spec + SHIP-RHYTHM-02 engine,
PRs #741/#742) on the sars_cov2 arm: does partitioning the ship's exposure
set into successive event cohorts — venue-bounded, class-scoped,
clock-correlated — pull the ~17× takeoff burn toward the Diamond Princess
record without touching Θ? The measured failure state this is read against
(THETA-SCREEN-V12 + COVID-TAKEOFF-ATTR-01): takeoff cells at the admissible
band midpoint burn ~2,400–3,580 recorded onsets vs ~197; median per-epoch
dosed set ~705 hosts (q95 ~3,548); `challenged_share_of_aboard` = 1.0 on all
seeds; route split zone_pool 43% / dining_ring 24% / near_field 22% /
cabin_mate 8% / hvac 3%.

## Declared before running

**Θ:** 2.37e11 — the v12 admissible-band midpoint; fixed, no re-screen.

**Cells:** 160 = 4 cruise classes × 2 arms × 20 seeds. Legs:
mega_cruise (platform mega_cruise_5000, scenario diamond_princess_2020,
declared replay, seeds 20200205–24); contemporary_cruise (platform
spirit_cruise_3000, generic leg at 2100 pax + 900 crew carrying the DP
index geometry verbatim, same seeds); classic_cruise (platform
classic_cruise_1900, generic at 1332 pax + 560 crew — all passenger
berths — same seeds); expedition_cruise (platform expedition_cruise_450,
scenario greg_mortimer_2020, generic boarding axis per the v12 stage-3
convention — the held-out seed declares no onset day, so its incubation is
drawn — seeds 20200315–34). Design:
`picard_framework/runs/covid_rhythm_ab_v1_design.json`; cell machinery:
`picard_framework/covid_rhythm_cells.py`; instrument: the
`covid_takeoff_attribution` ledger plus the `rhythm_ab` block (transit-zone
occupancy, crew-zone emptiness) read-only on the same cell path.

**Arms:** `off` writes `config_overrides.rhythm.enabled = false` (the
labelled baseline — `RhythmLayer.from_platform` returns before any RNG
construction, so flag-off claims byte-identical draws); `on` writes
`enabled = true`. Same seeds, same spec body otherwise.

**Byte-identity gate (first, before any AWS spend):** same spec run under
the same interpreter on the pre-#742 tree (bcf2ac95) and flag-off at the
A/B SHA — payload observables, onset curve, sanitary telemetry and agent
locations must be bitwise identical; on AWS the off-arm canary must
reproduce the stored stage-2 record of record for the same (Θ, seed).
PASS at the local tier: 48-epoch expedition cell, identical bytes on both
trees (fae3a49f flag-off vs bcf2ac95 pre-layer). The AWS tier runs as the
canary.

**Attribution criterion (stochastic-attribution):** an effect counts only
if |on − off| exceeds the off arm's paired-seed spread on the same class;
effects reported per class on all seeds.

**Canary:** indices 0 (mega/off/20200205) and 20 (mega/on/20200205) via
`--index` container-override command. Stop and report if metrics do not
move (flag inert) or if the off canary diverges from the stage-2 record.

**Report-immediately triggers:** byte-identity failure or inert flag;
`challenged_share_of_aboard` staying 1.0 under on (co-presence partition
broken); passenger exposure epochs in crew-only zones under on (class
scoping broken); takeoff collapsing to zero everywhere (over-partitioning).

**Read sections at readout:**
1. Exposure-set metrics — median + q95 per-epoch dosed-set size;
   challenged_share_of_aboard; per-route re-split (does zone_pool
   dominance fall once sets are event-bounded).
2. Takeoff burn — onset distribution, clause ratio vs ~197, before_share.
3. Clock correlation — transit-zone occupancy vs catalog synchronized-end
   epochs, scored as `occupancy_sync_corr` (point-biserial r) and
   `occupancy_lift_at_sync_end`; the off arm is the no-clock null.
4. Anchor readout — takeoff gate (seeds ≥10 recorded onsets), H1–H3 hull
   placements, MIDRS/A8 where in scope; scored, not shaped.
5. Class-scoping check — engine-room/galley/crew-mess zones: epochs with
   passenger occupants and epochs with a passenger challenge, counted.
6. Verdict — whether the residual is still mechanism-shaped, and which
   mechanism.

**Execution:** AWS Batch EC2 Spot, `picard-campaign-queue`, image
`picard-campaign:covid-rhythm-ab-<merged-SHA>`, job definition
`picard-covid-rhythm-ab` (revision pinned in the manifest), results under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_rhythm_ab_v1/<sha>/cells/`.

**Non-goals:** no Θ re-screen; no participation-fraction sweeps; no §3.6
register edits; no mechanism fixes — filed, not fixed. Naval/starship
hulls out of scope.

## Result

Measured on image `picard-campaign:covid-rhythm-ab-e256e8cb` (digest
`sha256:5d174df6835f8721880543a279c47b45bb881068fffb4040bd3dc025c348cb17`,
jobdef `picard-covid-rhythm-ab:2`, array `99e6390f-faac-4606-8524-a21160521f62`):
160/160 cells, 0 failures, manifest at
`s3://…/campaign/covid_rhythm_ab_v1/e256e8cb/manifest.json`. Two gate events
preceded the array: the canary pair at `3db82366` (mega/DP seed 20200205,
byte-identity PASS bitwise vs the stage-2 record) fired the
`challenged_share = 1.0` report trigger, and the run was stopped; the
proximity instrument (`accrued_hazard` Λ = Σ susc·p_dose·(1−protection) per
challenged host, counterfactual P(infection) = 1−exp(−Λ)) was added under
#748, and the array ran at the merged SHA. All cells below carry the Λ block.

### 1. Exposure-set metrics

| class | arm | dosed-set median | q95 max | challenged_share | Λ med (uninf.) | mean P(inf) | share P≥0.5 | share P≥0.1 | never challenged |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| classic | off | 440 | 1,858 | 1.000 | 0.0143 | 0.122 | 0.091 | 0.329 | 0.000 |
| classic | on  | 398 | 1,862 | 1.000 | 0.0158 | 0.109 | 0.066 | 0.308 | 0.000 |
| contemporary | off | 606 | 2,940 | 1.000 | 0.0138 | 0.112 | 0.074 | 0.286 | 0.000 |
| contemporary | on  | 569 | 2,960 | 1.000 | 0.0124 | 0.115 | 0.073 | 0.281 | 0.000 |
| expedition | off | 47  | 207   | 1.000 | 0.0098 | 0.086 | 0.000 | 0.250 | 0.000 |
| expedition | on  | 40  | 208   | 1.000 | 0.0248 | 0.113 | 0.045 | 0.333 | 0.000 |
| mega | off | 705 | 3,621 | 1.000 | 0.0135 | 0.118 | 0.086 | 0.273 | 0.000 |
| mega | on  | 676 | 3,650 | 1.000 | 0.0108 | 0.108 | 0.068 | 0.280 | 0.000 |

`challenged_share_of_aboard` stays 1.000 on every class, both arms — the
declared spec claim (line 193: crew-only venues + class-scoped eligibility
→ structurally < 1) does **not** materialise. The saturating route is the
ship-wide reach outside event-cohort partitioning (hvac_airborne plus
hull-scale venue pools), not a class-scoping failure — §5's emptiness
measurement is clean. What the Λ instrument adds: the challenged set is
saturated **shallowly** — challenged-uninfected hosts sit at median Λ
~0.010–0.025 (counterfactual P(infection) ≈ 1–2.5%), mean P ≈ 0.09–0.12,
and only ~5–9% of them ever reach P ≥ 0.5. Everyone is grazed; few are
near threshold.

Per-epoch dosed-set sizes barely move (medians −5…−15% under on; q95 max
unchanged) — partitioning does not bound the pools the engine actually
doses. The route re-split is real and in the predicted direction:
zone_pool onset share *rises* under rhythm on every class (mega
0.433→0.538, contemporary 0.612→0.658, classic 0.625→0.639, expedition
0.360→0.460) while near_field (−26…−35% share on mega/classic) and
cabin_mate/hvac fall — exposure concentrates into the scheduled-event
cohort venues exactly as the spec predicts; the residual mass just lives
there rather than shrinking.

### 2. Takeoff burn

| class | arm | rec. onsets q05/med/q95 | clause ratio vs ~197 | before_share med | verdict |
|---|---|---|---:|---:|:---:|
| classic | off | 947 / 1,314 / 1,798 | 6.67 | 0.975 | fail |
| classic | on  | 825 / 1,264 / 1,818 | 6.42 | 0.979 | fail |
| contemporary | off | 1,733 / 2,520 / 2,878 | 12.79 | 0.968 | fail |
| contemporary | on  | 1,377 / 2,424 / 2,892 | 12.30 | 0.969 | fail |
| expedition | off | 72 / 86 / 100 | 0.44 | 0.943 | fail* |
| expedition | on  | 71 / 85 / 104 | 0.43 | 0.976 | fail* |
| mega | off | 2,575 / 3,475 / 3,556 | 17.64 | 0.908 | fail |
| mega | on  | 1,911 / 3,402 / 3,579 | 17.27 | 0.938 | fail |

*Expedition burns far *under* the record on both arms — it fails the
clause from below, a different defect family, not an over-burn.
No class approaches ~197 under rhythm; onset_mass_near_197 = 0 on the
three large hulls. The flag is not inert — per-seed |on−off| medians
(68 / 79 / 7 / 134) exceed the off-arm neighbour-seed spread medians
(31 / 69 / 1 / 15) on every class — but the *signed* effect is small and
sign-mixed: median on−off −62 / −7 / +2 / −7, with 40–45% of seeds
burning *more* under rhythm. Partitioning reorders the burn; it does not
suppress it.

### 3. Clock correlation

| class | arm | occupancy_sync_corr med (q05,q95) | lift at sync-end med |
|---|---|---|---|
| classic | off | −0.367 (−0.65, −0.06) | 0.605 |
| classic | on  | −0.336 (−0.63, +0.02) | 0.676 |
| contemporary | off | −0.379 (−0.66, −0.10) | 0.593 |
| contemporary | on  | −0.366 (−0.66, −0.06) | 0.641 |
| expedition | off | −0.467 (−0.74, −0.17) | 0.135 |
| expedition | on  | −0.416 (−0.73, −0.08) | 0.307 |
| mega | off | −0.585 (−0.68, −0.49) | 0.549 |
| mega | on  | −0.554 (−0.66, −0.44) | 0.612 |

The numbers split the claim. Lift is real and rhythm raises it — transit
zones carry ~55–68% more occupancy at catalog synchronized-end epochs
than off-peak on the three large hulls (expedition: 0.135→0.307). But the
per-epoch series correlation stays **negative** in both arms on every
class: mean corridor occupancy is lower when synchronized ends are
frequent, because sync-end epochs cluster inside peak-programme blocks
while transit occupancy is dominated by the board-and-drift background.
"Corridor fronts correlated with the program clock" is supported as a
*lift* measurement, not as the claimed correlation; the mechanism moves
WHERE the mass sits at event boundaries, not a sustained positive
co-movement.

### 4. Anchor readout (scored, not shaped)

- **Takeoff gate (recorded onsets ≥ 10):** takeoff_probability = 1.000 on
  all eight class×arm pools — 160/160 cells in gate.
- **covid.H3 fleet shape:** no placement on any class or arm
  (h3_placement = false ×8): replay-conditioned attack-rate medians
  0.38–0.94 lie far above the generic-voyage H3 window by construction;
  rhythm does not change that (off/on medians within ±0.03 per class).
- **covid.H1/H2 (expedition held-out):** miss on both arms — positive_share
  observed 0.065 off / 0.071 on vs target 0.5899; asymptomatic_share 1.0
  both arms vs target 0.8125. The held-out misses are baseline misses,
  not a rhythm regression (arm medians within ±0.006).
- **MIDRS A8/A9:** out of scope — these legs carry no reporting channel,
  so the cells are report-free and A8/A9 are undefined by construction
  (same convention as TAKEOFF-ATTR-01).

### 5. Class-scoping emptiness

Measured, not assumed: `passenger_challenge_epochs_in_crew_zones` =
{seeds_with_any: 0, total_epochs: 0} and `passenger_epochs_in_crew_zones`
= 0 on every class × arm × seed — 160/160 clean. Passengers never occupy
crew zones in either arm (the emptiness is a hull-layout invariant the
rhythm scoping inherits, not a behaviour rhythm introduced) and so never
challenge there. The spec's class-scoping mechanism is verified at the
measured level; the challenged-share saturation in §1 therefore cannot
come from passenger scoping leaks.

### 6. Verdict

The residual is still mechanism-shaped, and the mechanism is now named:
**ship-wide dose channels outside event-cohort partitioning**.
Rhythm delivered its machinery faithfully — the A/B effect exceeds the
paired-seed spread on all four classes, route mass re-concentrates into
scheduled-event cohorts exactly as specced, crew-zone emptiness holds
under measurement — and the takeoff burn did not move: 17.3× the record
on mega under on vs 17.6× off, clause fail on every admissible row.

The Λ readout pins the shape. Challenged share saturates because hvac and
hull-scale venue pools graze essentially every host every voyage; but the
challenged-uninfected population sits at median counterfactual
P(infection) ≈ 1–2.5% with only ~5–9% of them crossing P ≥ 0.5. The ~3,400
cell is not produced by a near-threshold majority — it is produced by
thousands of shallowly-dosed hosts piling up enough compounded hazard
that the pre-quarantine burn runs ~17× hot regardless of who a shedder's
direct-contact cohort contains. Event-cohort partitioning bounds the
short-range ring; it cannot bound an airway or a venue pool that already
reaches hull scale, and it cannot help where the clause needs ~5–10%
challenged share with per-host hazard near the deep tail.

Filed, not fixed: candidates that follow — hvac reach partitioning
(zone-duct scoping), per-epoch venue-pool caps, or a Θ-dose trade where
the pool size is the tunable — are new mechanisms/params and out of this
entry's scope.
