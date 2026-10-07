# MEAL-SVC-02 `contact_factor_to_host` attenuation sweep — MAGNITUDE-LANDED on the section-binding arm; the factor axis never was the lever

> **Status:** Findings (2026-10-07). Full grid measured — 200/200 cells,
> 0 failures — on image `covid-meal-svc-02` built at `54086e4ca8e6`
> (ECR `sha256:300b643733bb…`), jobdef
> `picard-covid-meal-service-02-fargate` rev 1, queue
> `picard-analysis-fargate-queue` (the EC2 queue was flooded by sibling
> arrays; the LEDGER-named fallback carried every cell), S3 prefix
> `campaign/covid_meal_service_02/`. Spec and readout under
> `campaigns/covid/meal_service_02/`, design
> `picard_framework/runs/covid_meal_service_02_design.json` (frozen
> pre-run). Canary `zone_narrow_svc_dir_cf_lo` (20/20) read STILL-HIGH;
> the remaining 9 blocks ran on owner approval.

MEAL-SVC-01's canary measured the steward→host direction real but ~15×
hot at the shared door-drop factor (confined-pax median 804 vs the
F13/F14 bound ≥52). MEAL-SVC-02 swept the open decision: an independent
per-delivery host-side factor `contact_factor_to_host`, plus the SECT
sub-arm (stewards bound to cabin sections of 10–15 cabins) at the LO
factor.

## Result (takeoff-conditional medians, θ7.9e6, 20 cells/arm)

| arm | factor med | takeoff | confined-pax med | bound [26,160] | during med (record band (150,350) beside) | crew share (record 0.29) | deliveries med | stewards/host | svc_to_host acq | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| d0_declared_svc_base | — | 19 | 1.0 | — | 729.0 | 0.999 | 137,341 | 47 | 0 | BASELINE |
| d0_svc_dir_cf_off | 0 | 19 | 1.0 | — | 729.0 | 0.999 | 137,341 | 47 | 0 | OVER-ATTENUATED (≡ base) |
| d0_svc_dir_cf_shipped | 0.175 | 19 | 563.0 | — | 1295.0 | 0.565 | 137,370 | 47 | 9,232 | STILL-HIGH |
| zone_narrow_svc_base | — | 19 | 1.0 | — | 299.0 | 0.996 | 166,221 | 44 | 0 | BASELINE |
| zone_narrow_svc_dir_cf_off | 0 | 19 | 1.0 | — | 299.0 | 0.996 | 166,221 | 44 | 0 | OVER-ATTENUATED (≡ base) |
| zone_narrow_svc_dir_cf_floor | 0.010 | 19 | 294.0 | — | 677.0 | 0.542 | 166,150 | 44 | 6,349 | STILL-HIGH |
| zone_narrow_svc_dir_cf_lo | ~0.012 | 19 | 289.0 | — | 686.0 | 0.536 | 166,113 | 44 | 5,570 | STILL-HIGH |
| zone_narrow_svc_dir_cf_mid | 0.050 | 19 | 570.0 | — | 990.0 | 0.423 | 166,227 | 44 | 11,291 | STILL-HIGH |
| zone_narrow_svc_dir_cf_shipped | 0.175 | 19 | 759.0 | — | 1214.0 | 0.376 | 166,165 | 44 | 14,689 | STILL-HIGH |
| **zone_narrow_svc_dir_sect_cf_lo** | ~0.012 | 11 | **35.0** | **in-band** | 238.0 | 0.841 | 162,447 | **1.0** | 490 | **MAGNITUDE-LANDED** |

## What was measured

- **The uniform-draw ladder saturates nowhere near the band.** Factors
  0.010→0.175 map confined-pax medians 289→759 — a ~2.6× response over
  a 17.5× factor range, and even the floor arm sits ~1.8× above the
  band top (200). Between OFF (1.0) and FLOOR (294) no declared value
  lands [26,160] — the bound is unreachable on the uniform-steward
  structure at *any* host-side factor.
- **The OFF arms are bit-identical to their BASE rows** (zone_narrow:
  1.0/299/0.996/166,221 deliveries; d0: 1.0/729/0.999/137,341) — a
  factor of 0 credits zero host dose while the uniform responder draw
  still consumes its voyage-RNG draw per delivery, so the realization
  is unchanged. Validates the shared-draw wiring end-to-end.
- **The ladder flag NONLINEAR-BREAK is trivial**: cf_floor=294 →
  cf_lo=289 is a 5-cell inversion across declared specs only ~1.25×
  apart (floor 0.01 fixed vs lo [0.005,0.02] realizing median 0.012) —
  draw jitter on 19-cell medians; both sit on the ladder's asymptote.
- **The section arm lands the band at the same cf_lo factor** —
  confined-pax median 35, in [26,160], with stewards/host 1.0 vs the
  uniform 44 and service_to_host acquisitions 490 vs 5,570. Section
  binding makes exposure *per-section binary*: a confined cabin is
  dosed only if its bound steward sheds, instead of every shedding
  steward eventually reaching every cabin under the uniform lottery.
  That is also the record's structure — Diamond Princess stewards
  served assigned cabin sections — and it produces the cabin-cluster
  signature the record shows.
- **Caveat — the section arm is a different voyage realization, not a
  seed-paired contrast.** Uniform responder draws consume the voyage
  RNG (~162k draws/cell); section draws ride the dedicated spawn
  stream, so the post-first-delivery stream re-rolls: sect before-med
  4.0 vs ~102.5 and takeoff 11/20 vs 19–20 are a different roll of the
  voyage, not a mechanism effect on the pre-window phase. The landing
  reads on the frozen grammar's within-arm takeoff-conditional median;
  seed-pairing across arms is not available by construction.
- **Crew share still misses the record even on the landed arm** —
  0.841 vs 0.29. Attenuating the host direction shrinks the passenger
  mass but leaves the during-window crew mass (~200 of a 238 median)
  hot ~2–4×: steward pickups are only 3.6% of crew acquisitions on the
  sect arm, so the crew side barely consumes this channel. The
  crew-share divergence lives on other routes (duty zones, mess,
  near-field), not in meal service.
- **Drift witnesses clean.** cf_shipped confined-pax 759 beside the
  MEAL-SVC-01 canary's 804 at `32b11ccf` (the svc-02 image adds the
  host-factor machinery — a re-rolled realization at the same
  magnitude). CW-02 base pairs: d0 during 727 vs 737.5 (median paired
  Δ +7), zone_narrow during 298.5 vs 334 (Δ −27.5); deliveries parity
  both (137k and 166k in the measured bands).

## Audit invariants

9 violations on 200 cells, all accounted for:

- 6× `D0 realized_exempt_share` 0.836–0.872 on the two big before-phase
  seeds (20200205, 20200221) across the d0 rows — the known CW-02
  pattern: symptomatic crew confine via the isolation path, not the
  order gate. Recorded as an open (unruled) item in the crew-window
  handoff; unchanged by this campaign.
- 3× `service_dose_to_host_credited = 0` on sect cells
  (20200207/09/24) — no shedding steward drawn for the bound section;
  a legitimate zero on a stochastic mechanism, not a wiring defect.

## Verdict grammar read

MAGNITUDE-LANDED on `zone_narrow_svc_dir_sect_cf_lo` (35 ∈ [26,160]);
every uniform-ladder arm reads OVER-ATTENUATED (OFF ≡ 1) or STILL-HIGH
(≥289); NONLINEAR-BREAK flagged and assessed as jitter on the
asymptote. **The confined-passenger bound was never a factor-magnitude
problem — it is a responder-structure problem**: the channel lands when
each cabin's deliveries come from its own bound steward, at the
declared LO factor.

## The single open decision

Two residuals remain against the DP record, now separable:

1. **Crew share** — the during-window is crew-dominated (~200/~238,
   share 0.841) vs the record's 0.29; steward pickups explain only
   ~3.6% of crew acquisitions. The suspect for crew exposure moves off
   the service channel entirely (duty-zone / mess / near-field routes).
2. **Takeoff-rate divergence on the sect realization** — 11/20 vs
   19/20 on the uniform realization; whether section binding still
   lands on a matched voyage is answerable only by a mechanism that
   keeps the uniform draw off the voyage RNG (dedicated-stream
   uniform) or by more seeds.

## Not measured this stage

- SECT at other factors (only cf_lo ran) — the ladder suggests factor
  is a weak axis, but sect×{floor, shipped} is unmeasured.
- Whether `service_responder_mode: "section"` should ship as the
  default responder structure (the record's actual arrangement) — an
  owner decision, not a measurement.
- Cross-pathogen behaviour of the service machinery — measured
  separately this session as a structural null on norovirus (isolated
  hosts deposit emesis nowhere), pending an owner call on the deposit
  gap.
