# ROUTE-ATTR-V1 — whole-voyage route attribution + ascertainment funnel

**Measured at:** `be121a0` (branch `devin/1790362431-route-attribution-instrument-fix`;
the dose-split instrumentation and the datable-course funnel read live there —
PR #680 carried the route/window tables).
**Tool:** `tools/covid_route_attribution.py`
**Cells:** arm `D0_declared` of `covid_plume_dose_assay_v1`, seeds
20200205 / 20200217 / 20200222, full 768-epoch voyage, run locally under
CPython 3.12 — **not cross-comparable with the Batch (3.11) numbers**;
reads below are structural, not the campaign's exact counts.

## What was instrumented

- `route_attribution`: every infection event (the
  `QuarantineAttributionLedger` already records the whole voyage; the
  cell payload only aggregated the during-quarantine slice), tallied by
  dominant acquired-dose route × {before, during, after} quarantine
  (days 16–30), by zone class, and by passenger/crew role.
- `near_field`: per-infected-agent droplet dose split from the
  engine's **unrounded** dose functions — `_near_field_droplet_dose`
  (near share's plume dose: fixed cabin/table pairs + the sampled
  proximity ring), `_cabin_mate_droplet_addback` (confinement channel),
  and `_accumulate("droplet")` (total; the residual is the far-field
  pool). `matrix.droplet_exposures` was tried first and is unusable for
  this: it rounds each exposure to 4 decimals and the per-epoch drip
  underflows to 0.0.
- `ascertainment`: infected (truth) → eligible-severity course →
  lab-confirmed → onset dated, with severity histograms; `illness ==
  SYMPTOMATIC` is an end-of-voyage flag (recovered cases flip it) so the
  datable rung is read off the severity state instead.

## Routes

### seed 20200205 — the saturating burn (3,531 infections)

| window | droplet | hvac_airborne |
|---|---|---|
| before (day <16) | 3,185 | 339 |
| during (16–30) | 7 | — |
| after | — | — |

Zone class before: `other` 2,490 / crew_mess 515 / cabin 499 / galley 20.
Roles before: passenger 2,518 / crew 1,006.

### seeds 20200217 / 20200222 — the slow burns (2,699 / 2,830 infections)

| window | droplet | hvac_airborne |
|---|---|---|
| before | 617 / 412 | 17 / 7 |
| during | 1,212 / 1,473 | 768 / 871 |
| after | 36 / 47 | 49 / 20 |

Zone class during: cabin 1,318 / 1,517 · crew_mess 559 / 640 ·
other 93 / 173 · galley 10 / 14. The during-quarantine mass is
cabin-zone + crew-mess — the confinement channel the PARTNER-RATE probe
already suspected.

## Droplet dose decomposition (ring vs pool)

| seed | infected w/ droplet dose | dose-weighted ring share | near-field | cabin-mate addback | per-agent ring share median / q05 / q95 | share majority-ring |
|---|---|---|---|---|---|---|
| 20200205 | 3,522 | **0.981** | 0.683 | 0.298 | 0.648 / 0.0 / 0.999 | 0.563 |
| 20200217 | 2,687 | **0.995** | 0.686 | 0.309 | 0.370 / 0.0 / 0.999 | 0.456 |
| 20200222 | 2,764 | **0.994** | 0.598 | 0.395 | 0.279 / 0.0 / 0.999 | 0.441 |

Read: dose mass to infected agents is ~98% ring-side (near-field plume
60–69% + cabin-mate addback 30–40%; the far-field pool carries ~2%).
Per-agent the share is bimodal — q05 = 0, q95 ≈ 1: rings deliver
near-total dose to roughly half the infected while the other half is
infected on a pool-dominated drip. This is the mechanism of the flat
assays, resolved: at Θ 4.22e10 **both** channels sit far above the
infection threshold for almost every host — removing any ring arm drops
that host's dose from "huge" to "still sufficient", so the infection
count does not move. The epidemic is threshold-saturated, not
channel-limited; nothing below the dose axis can move recorded mass.

The cabin-mate addback carries 30–40% of droplet dose weight — the
fixed-ring channel PARTNER-RATE-V1/PLUME-DOSE-V1 could not touch is the
single largest identified dose mass after the plume rings, and it is
the dominant during-quarantine carrier (cabin zones 1,318–1,517 of the
during mass on the slow seeds).

## Observation channel — does it record what the real investigation missed?

| seed | infected (truth) | lab-confirmed | confirmed datable | dated onsets | dating rate (confirmed) | dating rate (datable) | mild share of dated |
|---|---|---|---|---|---|---|---|
| 20200205 | 3,531 | 2,639 | 2,639 | 2,460 | 0.93 | 0.93 | 85% |
| 20200217 | 2,699 | 2,055 | 1,973 | 1,971 | 0.96 | 1.00 | 89% |
| 20200222 | 2,830 | 2,152 | 2,088 | 2,088 | 0.97 | 1.00 | 88% |

Record (covid.T1 anchor): ~712 confirmed cases, 197 dated onsets —
**0.28** of confirmed, and the published dated subset was
disproportionately moderate/severe (presentation-driven).

**Answer: yes, decisively.** The channel confirms ~76% of all infected
(the record confirmed ~19% of the hull) and then dates 93–100% of
confirmed datable-course cases with the *true* onset day back-dated
exactly (`_presentation_onset_epoch` = true onset − drawn lag). The
published investigation dated 28% of its confirmed cases. Two
measured multipliers decompose the ~18× conditional gap:

- ascertainment-of-cases: ~2,100–2,640 confirmed vs 712 → ~3.0–3.7×;
- ascertainment-of-dates: 0.93–1.00 vs 0.28 → ~3.4×;
- product ≈ 10–13×, on top of the truth-level over-infection the
  transmission side owns.

And the dated mass is 85–89% **mild** — exactly the stratum whose
onsets a shipboard investigation loses to recall and non-presentation.
The channel has no dating-failure mode at all: every confirmed
symptomatic-course case gets a dated onset, at 100% fidelity on the two
slow seeds.

Measured anomaly worth its own look: on seed 20200205 every infected
agent's `symptom_severity` resolved to mild-or-worse (no `none` /
`asymptomatic` entries) while the profile's base probabilities put
asymptomatic at 0.31; the slow seeds do show 549/491 `none` + 36/68
`asymptomatic`. Either severity escalation is running hot on saturated
burns or the `none` bucket is bookkeeping — unresolved, flagged.

## What is now measured vs still open

Measured (this run): the burn rides droplet (90%+) and is pre-quarantine
on saturating seeds; the during-quarantine tail is cabin + crew-mess +
addback; the dose reaching infected agents is ~98% ring-side with the
cabin-mate addback alone at 30–40%; the observation channel dates
93–100% of confirmed datable cases, dominated by milds.

Still open (declared, unmeasured): whether deleting the cabin-mate
addback or the day-0 exposure geometry moves recorded mass (the ring
grammar still cannot express either); a `far_field_share` sweep
(declared range [0.05, 0.30], never run) — though with the pool
carrying only ~2% of droplet dose weight, its sweep is a bounded
probe; and an onset-dating ascertainment arm (e.g. record-consistent
dating probability) that would map how much of the ~18× is channel vs
transmission — the funnel says roughly one third.
