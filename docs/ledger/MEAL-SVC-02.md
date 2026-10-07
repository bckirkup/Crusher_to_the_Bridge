# MEAL-SVC-02
**Date:** 2026-10-07
**Commit:** 679a6c1b
**Pathogens:** sars_cov2_resp
**Status:** declared

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

**Execution state:** declared and frozen pre-run; implementation merged
to main (grammar + seam + witnesses + campaign registration +
readout). The Batch legs (image build at the merged SHA, jobdef
registration, manifest, canary `zone_narrow_svc_dir_cf_lo` 20 seeds →
STOP and report → remaining 180 cells) are handed to the next session —
see `docs/covid/covid_meal_service_02_handoff_2026_10_07.md`. No cell
has run; nothing below is a measurement.
