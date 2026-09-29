# COVID-COOP-02
**Date:** 2026-09-29
**Commit:** b44aa416
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** b44aa416

The cooperative (non-independent-action) dose-law arm — COVID-COOP-01's
candidate mechanism made executable — plus its first paired A/B canary.
Opt-in per pathogen via `dose_response.model = "cooperative_packet"`;
beta-Poisson stays the labelled baseline and every default.

## Mechanism

Each channel's dose is weighted by the share of its copies that arrive
in carriers holding ≥ n* virions — `w_c = P(K ≥ n*) / μ_c` over the
COVID-COOP-01 Poisson-occupancy packet model, `K ~ Poisson(μ_class)`,
with `n_star` and `carrier_loading {dry, wet}` as the arm's declared
parameters inside the COVID-COOP-01 occupancy envelopes. The
contact/bolus family is unchanged (w = 1: one carrier delivers its
whole transfer as a single packet). Host frailty (beta draw,
`susceptibility_scale`), RNG order, emission, and pathway bookkeeping
are untouched — the A/B isolates the law alone. Hazard
`-expm1(-s · Σ_c w_c · D_c)`; copies_per_dose cancels inside `w_c`.

`engines/cooperative_packet.py` holds the arm math and the channel →
class map (bolus: direct_contact/fomite/food/environmental; dry:
hvac_airborne/emesis_aerosol/flush_aerosol; unknown → dry). The
droplet pathway records its per-unit-dose components into dry
(non-compartment pool) and wet (compartment pool + cabin addback +
near-field) at the point dose accrues, scaled by the same
route-efficiency/NPI/susceptibility factors as the pathway dose.
Driver: `tools/covid_coop_arm_canary.py`.

## Canary (takeoff-conditioned anchor cell — covid.H3 declared replay,
Θ 2.37e11, seed 20200205, epochs 0–40; paired baseline on the same
SHA and window; `carrier_loading {dry: 0.05, wet: 20.0}` interior
declared points)

| arm | infections | zone_pool dominant | wet rings dominant |
|---|---|---|---|
| beta_poisson | 386 | 77 | 309 |
| n* = 2 | 167 | 35 | 132 |
| n* = 3 | 129 | 9 | 120 |

## Read

1. **The mechanism fires as designed.** At n* = 3 the zone pool's
   dominant-channel count collapses 77 → 9 — the far field's PCR-load
   stays bookkept while its infection conversion nearly vanishes; wet
   rings (cabin/dining/plume) carry 93% of arm infections vs 80% at
   baseline. This is the measured realization of "load without
   infectivity" that the packet analytic (COVID-PACKET-01) predicted:
   a strict n* ≥ 3 law makes the far field nearly inert.
2. **Suppression is n*-graded, matching the packet-structure read.**
   n* = 2 keeps the pool partially live (35 dominant) — the
   COVID-PACKET-01 branch point survives into infection counts, so the
   n* = 2 vs n* ≥ 3 choice is real modelling terrain, not a detail.
3. **Infections do not go to zero.** 129–167 remain: wet carriers at
   μ_wet = 20 genuinely qualify as ≥ n* packets (share ≈ 4.5% of wet
   copies at n* = 3), and the bolus family is untouched by
   construction. The arm suppresses the far field, not the close
   rings — whether that residual lands inside the ~197-onset takeoff
   record is a full-voyage question, not decidable in 40 epochs
   (onsets = 0 on both arms inside the window; incubation lags).
4. **One cell, one seed, one μ corner, 40 epochs.** Interior loading
   points, not corners; the n* = 2 interior is still sensitive to the
   unbounded complete-virion fraction (COVID-COOP-01 `?nr-term`) since
   every packet count is a copy-count upper bound. Fleet claims need
   the conditioned array; this cell's job was proving the law
   executes and moves the residual the right direction.

## What this buys

The A/B substrate now exists: same cell, same RNG stream, one
declared override flips the dose law. Next decisions are (a) the
n* / μ points at which a full-voyage single-cell read is worthwhile,
and (b) whether the complete-virion fraction needs its own bound
before the n* = 2 interior is quoted anywhere.
