# COVID sensitivity assay v1 — readout: every transmission-layer arm is inert on the frozen conditional metric; only the all-shared-air bound moves anything, and it kills takeoff

> **Status:** Findings (2026-09-23), assay complete. Campaign
> `covid_sensitivity_assay_v1`, declared in
> `picard_framework/runs/covid_sensitivity_assay_v1_design.json` (frozen
> before any assay cell ran). **All 240 cells have run** on AWS Batch at
> `main` = `b88e0ad`, image `picard-campaign:sens-assay-b88e0ad`
> (`sha256:60d9d664…a166`), job definition
> `picard-covid-boarding-screen:18`. Canary rows: A0 witness (cells
> 0–19, job `7422ea5c`) + A11 arrest bound (cells 220–239, job
> `a327700c`), both read before the array; array
> `f3065d9e-a605-456d-86b6-b097bbb7ac43` (size 200, INDEX_OFFSET 20).
> 240 of 240 children SUCCEEDED, zero failures. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_sensitivity_assay_v1/b88e0ad/cells/`.
> Flat surface: `docs/covid/covid_sensitivity_assay_v1_surface.csv`.
> No fitted configuration is claimed — the arms are declared
> counterfactuals; the deliverable is a mechanism map.

Every figure below is measured at `b88e0ad` inside the campaign image on
the declared Diamond Princess replay at Θ 4.22e10 (v11 admissible-band
centre), the same 20 matched seeds at base 20200205 as v10/v11/stage 2,
768 epochs (32 days). Scoring follows the frozen `scoring` block
verbatim: paired seeds that took off in BOTH the arm and A0
(`recorded_onsets ≥ 10` under each).

## 0. Canary

Both declared canary rows were read before the array:

- **A0 witness** reproduced the stage-2 Θ 4.22e10 row within PR #660
  engine drift: 19/20 takeoff, conditional median 3,483 vs stage-2's
  3,486, attack 0.96 vs 0.958, before_share 0.888 vs 0.854.
- **A11 wiring proof**: all five levers confirmed in the cell spec dump
  (SOP-017-ALLHANDS retimed to the day-12→30 window,
  confinement_isolation_factor 0.0, pool `none`, direct_contact ×0.25,
  crew confined); paired seeds moved hard (e.g. 20200206:
  3,527 → 1,806 recorded onsets). The arm-override grammar binds.

## 1. Arm surface — frozen verdict bands

| arm | takeoff | paired | rec med | q05–q95 | Δmed vs A0 | near-target [98.5,394] | verdict |
|-----|--------:|-------:|--------:|--------------:|-----------:|-----------------:|:----------------:|
| A0_declared | 19/20 | 19 | 3,483 | 2,307–3,552 | — | 0.00 | witness |
| A1_crew_confined | 19/20 | 19 | 3,481 | 2,311–3,552 | −0.1% | 0.00 | inert |
| A2_pool_transport_off | 16/20 | 16 | 3,440 | 2,161–3,540 | −0.9% | 0.00 | inert |
| A3_near_field_off | 19/20 | 19 | 3,504 | 2,460–3,539 | +0.6% | 0.00 | inert |
| A4_crew_confined_and_pool_off | 16/20 | 16 | 3,419 | 2,102–3,528 | −1.5% | 0.00 | inert |
| A5_all_shared_air_off | 3/20 | 3 | 262 | 44–1,389 | −91.0% | 0.33 | **takeoff_collapse** |
| A6_contact_dose_half | 19/20 | 19 | 3,483 | 2,307–3,553 | +0.0% | 0.00 | inert |
| A7_contact_dose_quarter | 19/20 | 19 | 3,483 | 2,307–3,552 | +0.0% | 0.00 | inert |
| A8_confinement_day12 | 19/20 | 19 | 3,386 | 2,329–3,481 | −2.8% | 0.00 | inert |
| A9_perfect_confinement | 14/20 | 14 | 3,440 | 1,505–3,550 | −1.3% | 0.00 | inert |
| A10_first_report_confinement | 19/20 | 19 | 3,483 | 2,307–3,552 | +0.0% | 0.00 | inert (vacuous — §3) |
| A11_arrest_bound | 16/20 | 16 | 2,868 | 1,363–3,422 | −17.4% | 0.00 | inert (largest mover) |

No arm's conditional q05–q95 contains 197. No takeoff seed in any arm
lands inside the near-target band except one of A5's three survivors —
and A5's verdict is `takeoff_collapse`, a killed-outbreak bound, not a
resized one.

## 2. Verdict: the ~18× gap is unreachable inside the transmission layer

The designed trigger fired: **A11 — every suppression lever the model
owns bound simultaneously (crew confined + airborne pool off +
quarantine retimed to day 12 + perfect confinement + contact dose ×0.25)
— still over-produces ~14.6×** (median 2,868 vs the record's 197). Every
smaller arm is inert within ±3%. The gap does not live in the
quarantine/intervention machinery the arms can reach; by the frozen
declaration it lives in the observational channel or natural history —
exactly what `covid_sensitivity_assay_v2` (already declared, PR #662)
assays next.

Why no confinement lever can move the total: the burn is already
committed before any intervention binds. A0's median
`infections_before_quarantine` is 3,509 against 53 during — ~89% of
recorded mass lands before the day-17 split, and the epidemic is ~96%
complete by the time the SOP order activates. Retiming to day 12 (−2.8%)
or perfect confinement (−1.3%) cannot erase a finished burn. A11 slows
the burn enough to push 594 median infections into the during window —
**all cabin droplet** — yet the total stays ~16× over.

A5 is the mechanism map's carrier identification: with droplet +
HVAC + pool shared-air terms off, takeoff collapses to 3/20 and the
surviving contact-only outbreaks carry ~296 infections — record-order
size but epidemiologically dead (a campaign that cannot take off is not
a DP replay). Direct contact alone cannot sustain a shipwide burn;
shared-air terms are the load-bearing carrier of the over-production.

### 2a. Exposure attribution: a day-0–5 public-zone droplet explosion

A whole-voyage event-level probe at the A0 witness seed (480 epochs,
`QuarantineAttributionLedger` per-event zone + dominant-dose route)
shows the exposure is even more front-loaded than the onset curve
suggests — onsets spread days ~5–20 only because incubation smears
them. Of 3,575 transmission events, ~68% land in days 0–2 and ~88% by
day 5 (859/1,051/521/258/180/226 events on days 0–5). The venues are
public, not cabins: Royal_Promenade 14%, Windjammer 12%, MainDining_L
11%, Crew_Mess_Main 10%, CentralPark 7%, MainDining_U 6%, pool deck and
theater in the tail. Pathway attribution: 99% droplet, 1% HVAC; only
6% of targets were already confined when hit. The during-quarantine
cabin-droplet residual is the tail of the same wave. So the deficit's
shape is not "reach over time" but "the first five days of normal
public-zone mixing expose essentially everyone" — which is what
assay-2's contact-rate/saturation (B7–B9) and effective-pool (B5/B6)
arms are declared to cut.

## 3. A10 is a vacuous arm, not a defect

A10's payloads are **bit-identical to A0's on all 19 paired seeds**
(only `arm_id`/`cell` fields differ). Bit-identity requires identical
confinement trajectories, so both counter thresholds must trip on the
same schedule. A 12-day instrumented probe at seed 20200205 confirms the
mechanism: by epoch 288 the declared run already holds 3,271
ever-reported passengers and 3,250 quarantined agents (~87% of the
ship) — the baseline 3% VSP `passenger_reported_case_rate` counter fires
on the first reporting epoch and confines every symptomatic agent it
finds, well before the SOP-017 mass order. On a report stream this
dense, 0.0004 and 0.03 sweep the same symptomatic roster at the same
moment: an epoch-level confinement trace shows the two arms'
quarantined counts identical at every one of the 288 probed epochs,
both first confining at epoch 44 (~day 1.8) — the first sick-call
batch alone already crosses the 3% passenger threshold, so no lower
threshold can bind earlier. The counter machinery works — the arm was
always degenerate.

The probe's second measurement is the more consequential one: **the
model's reactive confinement is near-saturating early** — ~87% of the
ship in cabins by day 12 — and the burn still completes. Confinement in
the model pins agents to their home zone, but three unconfineable
channels remain: the cabin-mate droplet addback (full unattenuated dose
between cabin-mates by construction), shared-corridor air between
confined co-occupants, and presymptomatic shedding already delivered
before each agent's onset triggers confinement. That is why A9's perfect
confinement factor buys −1.3% and why A11's entire stack buys −17.4%.

## 4. Where the gap is now measured to live

Declared decomposition of 17.7× ≈ ~4.7× biological over-burn × ~3.5×
observational bookkeeping. After this assay the intervention-side
accounting is closed:

- **Observational channel** (~3.5× declared share): `recorded_onsets`
  counts every specimen-confirmed symptomatic onset; the record's 197 is
  dated-onset bookkeeping ≈ 31% of 634 confirmed positives.
  `covid_sensitivity_assay_v2` carries the bookkeeping-aligned annex and
  the B1 subclinical-datable arm.
- **Natural history / mixing** (~4.7× declared share): attack ~0.96 vs
  the record's ~712/3,711 ≈ 0.19. No transmission lever reaches it —
  suspects are the effective susceptible pool (B5/B6 secretor arms),
  symptomatic share (B2), shedding duration/variance (B3/B4), and
  contact-network reach (B7–B9 rate/saturation arms) — the v2 arm set.
- **Unconfineable residual** (new this assay): cabin-mate full-dose
  addback + shared corridor air + presymptomatic shedding bound what any
  cabin lockdown can do — a structural floor on every confinement arm.

## 5. Provenance and next decision

`covid_sensitivity_assay_v2` is declared on main (PR #662): 220 cells,
B0 witness + B10 canary rows, the observational annex, and the
natural-history/reach arm set above. Execution is the next session's
deliverable: image → pinned job-def → canary rows 0 and 200 → 220-cell
array.
