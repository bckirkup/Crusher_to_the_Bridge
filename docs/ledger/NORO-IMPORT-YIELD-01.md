# NORO-IMPORT-YIELD-01
**Date:** 2026-09-26
**Commit:** f09ebb1b
**Pathogens:** norwalk_gi
**Status:** declared

## What is being measured

The introduction realism ladder
(`docs/norovirus/realism_ladder_v1_readout.md`) reports ~5–20 onboard
secondaries per infectious import on the shipped boarding channel (spirit
7 d: 52.0 mean secondary / 6.91 mean imports ≈ 7.5; classic 7 d ≈ 6.6;
12-d rungs ≈ 17–20). That pooled ratio conflates import classes that are
mechanistically different hosts — a symptomatic course boarding
mid-illness (emesis events aboard), an incubating/presymptomatic draw,
and a convalescent tail-shedder — with a generation cascade that charges
every onboard-acquired infection to the import line. This entry measures
the decomposition:

1. **Baseline arm** — the frozen NORO-COINCIDENCE cell
   (spirit_cruise_3000 × norwalk_only × 168 epochs, seeds 8000–8019) run
   as shipped. Per seed: drawn imports by `boarding_state`
   (symptomatic / presymptomatic / convalescent / never_symptomatic /
   cleared), onboard-acquired infections by acquisition day and dominant
   route (`acquired_particles_by_route` argmax), and the pooled
   secondaries-per-import ratio.
2. **Single arms** — the same cell with the boarding draw off
   (`initiation.boarding.norwalk_gi.enabled: false`) and exactly one
   explicit seed at a stated geometry, so the voyage's secondary count
   is the per-import yield distribution for that state:
   - `single_symptomatic`: `onset_day −1.0`, `age 2.2` (mid-illness
     boarder; the stream's own elapsed is U(0,T), E[T] = 2.5715 d).
   - `single_presymptomatic`: `onset_day +0.5`, `age 0.4`.
   - `single_convalescent`: `onset_day −4.0`, `age 5.2` (illness over,
     still RNA-positive).
   Ten seeds each (8000–8009): a mechanism-scale read, not the 20-seed
   canary standard — flagged here before the runs.

## Declared statistics

Per arm: per-seed secondaries distribution (median/IQR), P(≥1
secondary), dominant-route split. On baseline: composition shares and
the pooled yield ratio. A class-level contribution estimate falls out as
baseline composition × single-arm yield — stated as inference, since the
classes interact (an emesis patch or pool raised by one class is walked
through by another's susceptibles).

## Fidelity gaps, declared before the runs

- An explicit seed's illness duration is the profile `recovery_day`
  (3 d), not the symptomatic stream's length-biased illness draw
  (E[T] = 2.5715 d). Emesis schedule and axis draws go through the same
  `_stamp_symptomatic_history` path.
- The seeded host stays aboard the whole voyage; real symptomatic
  boarders may isolate once symptomatic onboard (the sick-call channel
  still applies to both).
- Local CPython 3.12.13 vs Batch 3.11: local numbers are mechanism
  reads, never cross-comparable to campaign numbers.

## What would change scope

- Pooled yield far outside 4.5–7 on the baseline arm means the ladder
  numbers no longer reproduce at HEAD — report immediately rather than
  reconciling silently.
- A near-zero yield on `single_symptomatic` would falsify the working
  hypothesis that symptomatic boarders carry the ratio.
