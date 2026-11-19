# ROOM-AIR-PAIRED-VALIDATION-01
**Date:** 2026-11-19
**Commit:** 74a6eff3ec45734b377acb07afe287ca6298f02f
**Pathogens:** sars_cov2_resp
**Status:** declared

Frozen design: [`docs/covid/room_air_paired_validation_01_design.md`](../covid/room_air_paired_validation_01_design.md).
Design only. No cell has run, no campaign is registered or authorized, and
nothing here may be quoted as a result.

## Declared

- **Contrast:** `ambient_on` minus `ambient_off` room-air map, matched seeds,
  `greg_mortimer_2020` on `expedition_cruise_450`, one pinned revision.
- **Endpoint and direction:** whole-hull `cumulative_ever_infected` at voyage
  end; protective means a negative mean paired difference.
- **Seeds:** stage 1 `20261901`–`20261920`; stage 2 reserve
  `20261921`–`20261960` by separate owner decision. Twenty complete pairs is
  a diagnostic floor, not a power guarantee.
- **Rule:** exact paired sign-flip test on the summed differences with ties
  retained; one-sided 0.0125 per stage and direction; at least seven nonzero pairs; exact
  sign test must agree in direction. PASS, FAIL (adverse), INCONCLUSIVE,
  INCOMPLETE and STOP are defined in the design, §7.
- **No-change control:** the same toggle under `room_air_removal.mode: sealed`
  must give identical outputs in all 20 pairs; any difference is a STOP.
- **Witness:** whole-hull scalars only: changed-zone count, susceptible
  person-hours and airborne dose share in changed zones, and the number of
  diverged pairs.

## Blockers before any execution

Arm selection by config (B1), the primary endpoint in the paired reader (B2)
and the encounter witness scalars (B3) do not exist at the pinned revision.
A destroyer respiratory scenario (B4) is absent and blocks only naval or
cross-hull statements. Details: design §10.

- **B1:** implemented and unit-tested in PR #1329
  (`transmission.room_air_removal.map_arm`). Synthetic-fixture neutrality
  only; no voyage was run and K0/K1 remain unmeasured.

## Scope

A verdict describes this model at one revision, hull and profile. It is not
as-built ventilation validation or evidence of a real-world outbreak effect.
