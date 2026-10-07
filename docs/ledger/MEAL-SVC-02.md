# MEAL-SVC-02
**Date:** 2026-10-07
**Commit:** 679a6c1b
**Measured at:** `54086e4ca8e6d9af301b7249707fdab10437b38f`
(image `covid-meal-svc-02`, ECR `sha256:300b6437…`)
**Pathogens:** sars_cov2_resp
**Status:** measured

The door-drop attenuation sweep on `service_to_host`, the open decision
the MEAL-SVC-01 canary left: which factor on the steward→host direction
lands the confined-passenger mass in the bound region (~52–160) while
keeping crew share moving record-ward.

Grammar landed in `engines/transmission_core.py`:
`transmission.caregiver.roles.service.contact_factor_to_host` — absent →
the host direction takes the delivery's shared realized draw (status
quo, the CF_HOST_SHIPPED control); scalar/`[lo,hi]` → the host
direction's own declared corner/interval drawn per delivery on its own
spawn of the dedicated stream family
(`_SERVICE_HOST_CONTACT_STREAM_KEY`), steward side untouched. Seam at
`_credit_service_to_host`; witnesses echo the effective spec
(`contact_factor_to_host` + `contact_factor_to_host_mode`) in the
resolved block and `crew_window`, plus `service_host_factor_draws`
realized stats {n, mean, median, q05, q95, min, max}.

Frozen design `docs/covid/covid_meal_service_02_design.md` +
`picard_framework/runs/covid_meal_service_02_design.json`: 10 arms
(ZONE_NARROW × {SHIPPED, MID, LO, FLOOR, OFF} + D0 corner pair + SECT
sub-arm at LO + two `*_svc_base` drift rows) × 20 seeds @θ7.9e6 = 200
cells, verbatim CW-02 replay contract. Campaign
`campaigns/covid/meal_service_02/`; jobdef `picard-covid-meal-svc-02`;
image `covid-meal-svc-02`; S3 `campaign/covid_meal_service_02/`; queue
`picard-analysis-queue`.

**Execution state:** measured — full grid 200/200 cells, 0 failures, on
`picard-analysis-fargate-queue` (jobdef
`picard-covid-meal-service-02-fargate` rev 1; the EC2 queue was flooded
by sibling arrays and the LEDGER-named fallback carried every cell).
Canary `zone_narrow_svc_dir_cf_lo` (20/20) read STILL-HIGH; the
remaining 9 blocks ran on owner approval. Committed readout:
`docs/covid/covid_meal_service_02_readout.md`; runs + verdict:
`campaigns/covid/meal_service_02/LEDGER.md`.

**Verdict:** MAGNITUDE-LANDED on `zone_narrow_svc_dir_sect_cf_lo` —
confined-pax takeoff median **35** ∈ [26,160] at the same cf_lo factor
that read STILL-HIGH (289) on the uniform ladder (stewards/host 1.0 vs
44). The uniform ladder saturates ~289–759 over factor 0.010→0.175;
OFF ≡ BASE bit-identical. The bound was never a factor-magnitude
problem — it is a responder-structure problem. NONLINEAR-BREAK on
floor→lo (294→289) is draw jitter on the asymptote. Residuals: crew
share 0.841 vs record 0.29 on the landed arm (service channel carries
only 3.6% of crew pickups); the sect arm is a different voyage
realization (takeoff 11/20), so the landing is within-arm-conditional,
not seed-paired.
