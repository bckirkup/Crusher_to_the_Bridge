# PLATFORM-FIDELITY-02
**Date:** 2026-11-08
**Commit:** db95a4f2
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** db95a4f2

Cells ran on image
`picard-campaign:covid-platform-fidelity-02@sha256:d641a0d69e54b4e054b2f59b9237ddb7d689d75413aaba2760c8f9cf8f0060c6705`,
built at `db95a4f2` (root `Dockerfile` + `deploy/aws/Dockerfile.campaign`
overlay).

PLATFORM-FIDELITY-02 is the pre-registered larger-seed Diamond Princess
platform-fidelity follow-up. Criterion of record:
`docs/covid/covid_platform_fidelity_02_prereg.md`; design
`picard_framework/runs/covid_platform_fidelity_02_dp_design.json`; campaign
`campaigns/covid/platform_fidelity_02/`; power calculation
`campaigns/covid/platform_fidelity_02/power_analysis.py` +
`power_analysis.json`; readout
`docs/covid/covid_platform_fidelity_02_readout.md` +
`campaigns/covid/platform_fidelity_02/readout.json`.

The paired-seed power calculation on the PLATFORM-FIDELITY-01/01b cells fixed
200 seeds/arm (400 cells, full rerun of proxy `mega_cruise_5000` and dedicated
`diamond_princess`) under the frozen operating point (Θ 7.9e6, infection_age_days
6.8, imports 1, dwell_weighted, union `exempt_work_zones` protocols file
`data/config/protocols_covid_pf_dp_01b.json`). Campaign completed 400/400
cells with 0 technical failures, 0 missing cells/echoes, and 0 `close_zones`
failed comparisons.

Measured result: P(takeoff) proxy 0.535 vs dedicated 0.510 (discordant
proxy-only 49 vs dedicated-only 44; exact two-sided McNemar p = 0.678532 — not
rejected). Both-takeoff outbreak size (n = 58) dedicated − proxy mean +92.672
onsets, 95% t CI [+15.033, +170.311], two-sided p = 0.020167 — a measured
platform-fidelity effect, not a platform selection. Report-only: unconditional
onset totals 17,123 proxy vs 22,534 dedicated (Welch p = 0.168304), medians
15.5 vs 12.5; takeoff-conditional asymptomatic share 0.395225 vs 0.497643;
CRN ρ = 0.441203. Audit caveat: 16 dedicated rest seeds exceed the inherited
PF-01b working-crew band (95–140); inspection shows the frozen
echo/hash/posted-zone/meal-service contract is clean and the misses are
extended-seed pre-activation confinement variation, diagnosed in the readout.
No GM cells, no Theta refit, no platform selected.
