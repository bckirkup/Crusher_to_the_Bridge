# CREW-BERTH-01 readout

- source: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_berth_01/`
- design: `picard_framework/runs/covid_crew_berth_01_design.json`
- coverage: 20/120 cells (partial: True)
- audit invariants: 0 violation(s)

| theta | arm | n | takeoff | confined-pax med (takeoff) | crew share med | cabin share med | galley share med | during med | deliveries med | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 7.9e+06 | combined | 20 | 8 | 32.500 | 0.662 | 0.435 | 0.000 | 16.000 | 162182.500 | CEILING-SHORT (crew share 0.662 > 0.4; the family is exhausted — residual rides a channel outside berthing+occupational) |

Crew-share target band (0.2, 0.4) (record 0.29); confined-pax guard [26,160] (CREW-MESS-01 boxed medians: confined-pax 28, crew share 0.727); deliveries parity 137857-186512 vs the boxed row's 162184; during-window total reported beside (150.0, 350.0) — not gating. UNARMED witness echoes audited before the share read. The verdict grammar binds on `combined` (the family ceiling); other arms read with the same machinery for the decomposition.

## Audit-invariant violations

- none

## Report flags

- none

## CREW-MESS-01 drift witness

- mess_boxed_base vs CREW-MESS-01 sect_mess_boxed: n=0 paired — crew share median new n/a vs n/a; confined-pax median new n/a vs n/a; deliveries median new n/a vs n/a (same arm definition — departures beyond seed-paired noise report DRIFT)

## Post-canary: berth attribution of the `combined` residual

Same method as CREW-MESS-01's post-canary pass — the three hot canary
seeds (20200223 / 20200218 / 20200220) re-run locally at the campaign
SHA with the sim retained (`tools/covid_berth_attribution.py`); the
crew-event counts reproduce the Batch cells exactly (148/134/80), so
these are the same voyage realizations. 362 during-window crew
acquisitions decomposed by venue × confined-at-event × co-berth:

| venue | n | share | vs boxed baseline (400) |
|---|---|---|---|
| corridor | 162 | 45% | was 12% — now the dominant block; working crew in non-home corridors |
| cabin (own berth zone) | 68 | 19% | was 27% — status-pure re-deal holds: only 3 co_berth-confined |
| galley | 68 | 19% | was 29% — 2-pod shift_split roughly halves galley exposure, not zeroes it |
| other work zones | 35 | 10% | was 16% |
| crew_mess | 29 | 8% | was 16% |

Inside the cabin block, **36 of 362 are confined crew infected in
their own berth** — but only 3 via a berth-mate infected during the
window (the carry-home channel the re-deal targets); **33 arrive with
no prior-infected mate at all** — pathway split: 17 `service_to_host`
door-drops (the delivery channel reaching a confined host), 15
`droplet` on the declared 0.05 confinement leak, 1 `caregiver`
(pathway-corrected 2026-10-08, was misread as corridor-pool). Routes
pooled: droplet 200 /
caregiver 138 / service_to_host 24 — the section-bound steward share
fell to ~7% of pickups (was ~10%).

Reads: the mechanism did what it was declared to do (status-pure
cabins, off-watch pods, galley share halved) and the residual still
sits at 0.662 because it was never primarily berth-mate-borne — it is
**corridor-venue occupational exposure of the working roster** plus
the steward door-drop channel and the declared 5% confinement leak
reaching confined berths, channels this arm family leaves
structurally untouched. Reaching (0.2,0.4) would need a
mechanism outside berthing+occupational placement — and the record
shows the documented DP response deployed neither.
