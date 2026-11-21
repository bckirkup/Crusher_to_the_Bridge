# QUAR-TAIL-SEAM-01 — full-campaign readout

> **Status:** measured. Full campaign (80 cells) completed and read out at
> merged main `b45911709e277bd51bf09de8ba73a742add314d9`. Design frozen in
> `picard_framework/runs/covid_quar_tail_01_design.json` (PR #1374, merged at
> `43e45aed`); submission record PR #1377. Nothing here refits a constant.

Measured at `b45911709e277bd51bf09de8ba73a742add314d9`, seeds
20200205–20200224, θ=3.162e8, image digest
`sha256:39eb3d53b9f6310f7047a6db66eafe0d716ccc6d77e6885b6fdf1e156cf28a34`
(jobdef `picard-covid-quar-tail-01:1`–`:5`), S3
`campaign/covid_quar_tail_01/`. Array jobs: canary
`a1b8ffb5-a014-4b2d-83f0-d27306bcc65a` (t8p50_mb_duty); full blocks
`41ec8037` (t8p50_d0), `9f102ca2` (t8p50_fraqmb), `cbcd3f60`
(t8p50_fraqmb_duty).

## Frozen-grammar verdict table (80/80 cells, 0 audit violations)

| arm | n | takeoff | during med (all) | during med (takeoff) | capture med | before med | crew share | realized exempt | duty excl med | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| D0_declared | 20 | 16 | 308.0 | 415.5 | 0.525 | 65.0 | 0.631 | 0.317 | n/a | BASELINE |
| FRAQMB | 20 | 17 | 344.0 | 394.0 | 0.516 | 65.0 | 0.562 | 0.248 | n/a | UNDER-DAMPED |
| FRAQMB_DUTY | 20 | 17 | 196.0 | 257.0 | 0.534 | 53.5 | 0.571 | 0.248 | 131.0 | HALF-LANDED-MASS (uncond. capture < 0.80; before-window moved — expected, standing duty policy) |
| MB_DUTY | 20 | 15 | 302.5 | 425.0 | 0.519 | 53.5 | 0.669 | 0.316 | 168.0 | UNDER-DAMPED |

Drift witness: D0_declared pairs seed-for-seed against committed
`dp_theta_8p50` cells — n=16 takeoff-paired, during-median delta **0.0**
(415.5 vs 415.5). The verbatim replay reproduces the committed tail exactly;
no in-campaign drift.

## What the arms measured

**The confined tail is crew-service-fed, but only jointly.** Neither lever
damps alone — FRAQMB (exempt share 0.317→0.248, the CW-02 band-landing point)
runs 394, MB_DUTY runs 425 — while together they land the mass: FRAQMB_DUTY
257, inside the record-informed [150,350] band. Seed-paired vs committed:

- FRAQMB: median delta -10.5 (range -208…+135), 12/16 negative
- FRAQMB_DUTY: median delta **-62.5** (range -484…+227), 13/16 negative
- MB_DUTY (canary): median 0, symmetric scatter, 4/20 bit-identical

The interaction is non-additive — removing symptomatic crew only bites when
the exempt pool is quartered. Single-lever confinement changes are falsified
at this θ.

**The capture half of the dual prediction is a metric artifact, not a
defect.** Conditioned on reachable infections — CAPTURE-01's declared basis:
`funnel_hosts.infection_day ≤ 29`, i.e. infected ≥5 d before the last
campaign day 34; numerator `confirmed_day` non-null; takeoff-conditional
medians per arm (supplemental computation over the cell payloads — the
campaign readout and CAPTURE-01 tool do not emit this statistic) —
confirmed-per-infection is **0.811–0.845 on every arm, D0 included** — the
specimen machinery already meets the ≥0.80 criterion everywhere. The
unconditioned ~0.52 median fails only because ~18% of infections postdate the
swabbable window (CAPTURE-01's structural bound). On the conditioned basis
FRAQMB_DUTY is effectively SEAM-LANDED. Per-arm medians (takeoff cells):
D0_declared 0.819, MB_DUTY 0.845, FRAQMB 0.811, FRAQMB_DUTY 0.843.

## What remains blocking Θ

The **baseline trajectory clause is still outside** and untouched by every
arm: D0 recorded_onsets q05–q95 34–2282 vs record 197; before_share median
0.059 vs record 0.173. Quarantine levers cannot move pre-quarantine ignition —
the ~10-day-late exponential-phase ignition at right-sized truth is now the
clean residual defect for the Θ question (QUAR-TAIL-01's named hypothesis:
seed-ring/early-cabin structure vs intrinsic dose timing).

## Open items (owner calls, declared non-goals)

- Whether `confirmed / infections_reachable` becomes the scored capture basis.
- Whether FRAQMB_DUTY (boxed + quarter-exempt + duty exclusion) becomes the
  boxed_s1s2 replay default — it is the only arm that lands the during-band,
  and on the conditioned basis it satisfies the whole seam prediction.
