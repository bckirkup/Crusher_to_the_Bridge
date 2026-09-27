# COVID-RHYTHM-01
**Date:** 2026-09-27
**Commit:** fae3a49f (machinery SHA reported at readout)
**Pathogens:** sars_cov2_resp
**Status:** declared

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
