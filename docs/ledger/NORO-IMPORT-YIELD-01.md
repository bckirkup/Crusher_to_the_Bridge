# NORO-IMPORT-YIELD-01
**Date:** 2026-09-26
**Commit:** f09ebb1b
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 4e0032a0

Measurement provenance: probe tool + Batch entrypoint on top of f09ebb1b;
engine/data tree identical to f09ebb1b.

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

## Measured (AWS Batch, CPython 3.11 image)

Array `afdfe648-875c-466c-98e0-5057dfd49167` (job def `picard-init-probes:1`,
image `picard-campaign:init-probes-v1` digest
`sha256:acb63327f45460026a34cb1e5260f55b8650f21657e1f4c590a9e740d53230ba`),
per-seed `.json.gz` under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/init_probes_01/`,
pooled locally with the probe's own `build_readout`.

**The ladder's 4.5–7 does not reproduce at HEAD — pooled yield is 0.11.**
Baseline arm, 20 seeds @168ep: imports/voyage mean 6.4 (q25 5, q75 7.25,
range 2–11) — import *pressure* matches the ladder's ~6.9, so the draw is
working. But secondaries/voyage mean 0.7 (median 0, max 14), pooled
secondaries/imports = 14/128 = **0.109**, P(zero secondaries) = 0.95.
Onboard-acquired routes split evenly: emesis_aerosol 7, fomite 7.

Import composition across the 20 voyages (196 draws): convalescent 80,
cleared 68 (non-infectious, excluded from the import count — consistent:
196−68 = 128 = 6.4/voyage), never_symptomatic 34, symptomatic 9,
presymptomatic 5, incubating 0. The stream overwhelmingly boards hosts
that transmit weakly or not at all.

**Single-import arms (10 seeds each, one import per voyage — the
secondary count is that class's yield):**

- `single_symptomatic` (onset −1.0, age 2.2): mean 1.5 secondaries, P(0)
  0.7, max 13; routes emesis_aerosol 11 / fomite 4.
- `single_presymptomatic` (onset +0.5, age 0.4): mean 0.5, P(0) 0.9,
  max 5; emesis_aerosol 3 / fomite 2.
- `single_convalescent` (onset −4.0, age 5.2): 0 secondaries on all 10
  seeds — a convalescent tail-shedder is a dead import at HEAD.

Class contribution as an inference (classes interact; no dedicated
`never_symptomatic` arm was run): symptomatics are ~7% of infectious
imports × yield ~1.5 ≈ 0.1 expected per voyage, presymptomatics add
~0.1 — together ~0.2 of the observed 0.7. The remainder is consistent
with the never_symptomatic class (27% of infectious imports) contributing
at sub-symptomatic yield; that attribution is a hypothesis, not measured.

## Interpretation

The scope-change trigger fired: pooled yield 0.11 vs the declared
4.5–7 range means the ladder numbers no longer describe HEAD. The ladder
readout (`realism_ladder_v1_readout.md`) was measured at ~49dbf18e
(2026-09-15); 82 commits to `engines/` + `data/pathogens/norwalk_only.json`
have landed since, including the sub-copy fomite pickup gate
(NORO-GATE-FLOOR-01), capped/shared fomite pools, TOUCH-SHARE-01/02,
AERO-SPLIT-01, REINFECT-01 and NORO-CHANNEL-02. Which of those collapsed
the yield is a hypothesis, not yet attributed — the natural instrument is
a bisection over that window on this same frozen cell.

Consequence for the open question: per-import secondary yield is **not**
the current over-count suspect on this cell — at HEAD imports barely
transmit at all (and the pending susceptibility repair pushes further in
the same direction). The initiation excess the VSP comparison sees must
live elsewhere: onset/reporting amplification, repeated imports stacking,
or the channels the susceptibility session owns.
