# CREW-MESS-01 crew-dining attenuation — canary `sect_mess_boxed` measured STILL-HIGH: the mess channel closes and the crew-share residual rides on

> **Status:** Findings (2026-10-07). Canary measured — 20/20 cells,
> 0 failures, 0 audit-invariant violations — on image `covid-crew-mess-01`
> built at `cca98cdc` (ECR `sha256:9a3787a7…`), jobdef
> `picard-covid-crew-mess-01-fargate` rev 1, queue
> `picard-analysis-fargate-queue` (the EC2 `picard-analysis-queue` was
> still scale-from-zero at +10 min; the fallback named in the design
> carried the canary), S3 prefix `campaign/covid_crew_mess_01/`.
> Design frozen pre-run at `docs/covid/covid_crew_mess_01_design.md`
> (`picard_framework/runs/covid_crew_mess_01_design.json`); mechanism,
> spec and this readout under `campaigns/covid/crew_mess_01/`.
> **Stopped after the canary per the gate — the remaining 4 blocks
> (80 cells) are the owner's call.**

The residual under test: MEAL-SVC-02's landed config holds the
confined-passenger bound (median 35) but leaves during-window crew share
0.841 vs the record's 0.29, with the `crew_mess` zone class carrying
44–59% of during-window mass — the ~25–31% exempt crew dining in an open
mess through the 16-day order. CREW-MESS-01 arms the documented DP
response: boxed/staggered crew meals via the `crew_meal_service`
protocol modifier (placement-level directive; passenger dining
untouched by construction).

## Result (canary arm, θ7.9e6, 20 seeds)

| theta | arm | n | takeoff | confined-pax med (takeoff) | crew share med | mess share med | galley share med | during med | deliveries med | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 7.9e+06 | sect_mess_boxed | 20 | 9 | 28.000 | 0.727 | 0.000 | 0.000 | 22.000 | 162184.500 | STILL-HIGH (crew share 0.727 > 0.4; residual rides another venue) |

Crew-share target band (0.2, 0.4) (record 0.29); confined-pax guard [26,160] (MEAL-SVC-02 landed median 35, crew share 0.841); deliveries parity 138080-186814 vs the landed 162447; during-window total reported beside (150.0, 350.0) — not gating. UNARMED witness echoes audited before the share read.

## Audit-invariant violations

- none

## Report flags

- none

## MEAL-SVC-02 drift witness

- (skipped)


## What was measured

- **The boxed-meals corner fires and holds the guards.** Every cell
  echoes `crew_meal_service.mode: "boxed"` with 360 active epochs
  (the verbatim [16,30] window), 11.7k–14.9k `diner_redirects`, and
  verbatim exempt machinery (4 classes, 11 zones, section-bound
  stewards, stewards/host 1.0). `service_deliveries` median 162,184.5
  — parity with the landed row's 162,447; the steward channel never
  moved (the meal policy is read downstream of R3 cadence by
  construction).
- **The mess channel as a transmission venue collapsed.** During-window
  `crew_mess` zone-class mass reads 0 on the median cell; the pooled
  residual is 135 of 1,179 during-window acquisitions, and it sits only
  on five takeoff cells (17–40 each). That residual is the declared
  carve-out — mess-posted kitchen staff keep working the zone (boxed
  production still runs) — plus far-field pool exposure, not dining
  co-presence: every crew diner placement was diverted (the redirect
  tally proves the venues never seated).
- **Crew share moves 0.841 → 0.727 median** (takeoff-conditioned
  median 0.68, range 0.44–0.96 on the 9 takeoff cells) — measurably
  moved but above the declared (0.2, 0.4) band: **STILL-HIGH** by the
  frozen grammar. The residual rides cabin (603 pooled during-mass),
  galley (215), `other` work zones (171) and corridor (55) — once
  dine-in is closed the crew channel is not mess-dominated; it is
  berth-adjacent co-presence, the galley production line, and posted
  work zones.
- **Confined-pax guard holds**: takeoff-conditional median 28 ∈
  [26,160] — the crew-venue intervention leaves the passenger-side
  bound intact (no PAX-COLLATERAL).
- **During-window total fell hard on this realization** — median 22
  vs the landed row's 238 (reported beside the [150,350] context
  band, not gating; takeoff 9/20 vs the landed arm's 11/20 — the sect
  draws ride a dedicated stream, so the read is within-arm, not
  seed-paired). Boxed meals attenuate the window mass by an order of
  magnitude while barely moving its crew share — the during-window
  survivors concentrate in cabin/corridor adjacency and the galley
  chain, not the dining hall.
- **Takeoff-conditioned during-window composition** (the 9 takeoff
  cells): cabin dominates every hot cell; `crew_mess` appears only
  where kitchen staff carry it; where `galley` appears it runs
  15–55 per cell — consistent with boxed production keeping the
  galley crew posted.

## Audit invariants

0 violations across all 20 cells: quarantine window [16,30] activated,
4 shipped exempt classes, 11-zone essential list, index terms
(-1.0 / shedding at day 0), caregiver/droplet echoes (partition 0.175/0.0),
crew complement 1,045, section responder mode with section draws >0,
`crew_meal_service` echo present and mode-correct, `diner_redirects` >0
on every armed cell, deliveries positive.

## Verdict grammar read

`sect_mess_boxed` → **STILL-HIGH**. The mechanism provably reached the
mess zones (redirects + collapsed mess mass), the confined-pax guard
held, and crew share moved ~0.11 but lands >0.4 — under the frozen
grammar the mess was a real but minor share of the during-window crew
channel; the residual rides the cabin/galley/work-zone venues the meal
policy never touched.

## The open decision (owner's call)

The remaining 4 blocks — `d0_svc_base` (widest corner + pairing base),
`sect_mess_open` (landed-corner drift witness), `sect_mess_stag4`,
`sect_mess_cap10` — 80 cells, are frozen and registered but not
submitted. Of note for that call: the canary already bounds the
family's top end (boxed is the strongest arm); `stag4`/`cap10` measure
whether a milder declared intervention lands the same or worse —
useful for the "what did DP minimally need" read, not for reaching
the (0.2,0.4) band, which boxed alone cannot.

## Not measured this stage

- The `sect_mess_open` pairing row — the MS2 drift witness — ran no
  cells this stage (one arm × 20 seeds per the gate). The canary
  single's contract check (deliveries parity, section structure,
  exempt echo) witnessed the scaffold reproducing on this merge.
- Passenger-side mess occupancy is ~zero by construction (the redirect
  reads crew placements only); no PAX-COLLATERAL signal appeared.
