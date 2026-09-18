# QUAR-ORDER-01
**Date:** 2026-09-17
**Commit:** 71a5aae
**Pathogens:** all
**Status:** measured
**Measured at:** 29e87e0

## Defect

Scheduled SOP-017 is an authority-issued whole-passenger cabin quarantine,
but it previously used the voluntary FRED compliance draw. Defiant passengers
therefore remained outside cabin confinement, and reluctant passengers could
remain outside during their voluntary delay window.

## Declaration-based fix

SOP-017 now declares `confinement_enforced: true`. The orchestrator admits
every non-exempt agent directly under that declaration, preserves any assigned
FRED class for telemetry, clears refuser bookkeeping, and records the distinct
`enforced_confinement` action. SOP-009 and reactive lockdowns retain voluntary
FRED behavior.

## Measurement

The post-fix burning and intermediate cells were measured at `29e87e0`.
Probe outputs are
`/home/ubuntu/phase0/out/upt_20200206_3.16e7_quar01.json` and
`/home/ubuntu/phase0/out/upt_20200210_1e9_quar01.json`.

| Cell | Total infections | Post-quarantine unconfined passenger infections | Final passenger refusers | Quarantined passengers |
|---|---:|---:|---:|---:|
| Burning (`20200206`, Θ=`3.16e7`) | 2,182 | 5 (`not_ordered`) | 0 | 2,666 |
| Intermediate (`20200210`, Θ=`1e9`) | 10 | 0 | 0 | 2,666 |

The five burning-cell unconfined passenger infections were all
`not_ordered`, in `Cabin_Corridor`, on day 16. The intermediate cell had no
post-quarantine unconfined passenger infections. The run-end refuser set
included 26 defiant agents in the burning probe, but none were passengers;
all passengers were quarantined.

Daily infection counts for days 15–31:

| Day | Burning | Intermediate |
|---:|---:|---:|
| 15 | 25 | 2 |
| 16 | 8 | 0 |
| 17 | 14 | 0 |
| 18 | 39 | 0 |
| 19 | 154 | 0 |
| 20 | 232 | 2 |
| 21 | 95 | 1 |
| 22 | 96 | 0 |
| 23 | 117 | 0 |
| 24 | 119 | 0 |
| 25 | 130 | 0 |
| 26 | 127 | 0 |
| 27 | 201 | 1 |
| 28 | 75 | 0 |
| 29 | 47 | 1 |
| 30 | 54 | 0 |
| 31 | 24 | 1 |
