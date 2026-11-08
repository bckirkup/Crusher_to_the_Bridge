# PLATFORM-FIDELITY-02
**Date:** 2026-11-08
**Commit:** 0ea71038
**Pathogens:** sars_cov2_resp
**Status:** declared

Diamond Princess larger-seed platform-fidelity follow-up, pre-registered
before any PF-02 cell runs. Criterion of record:
`docs/covid/covid_platform_fidelity_02_prereg.md`; design
`picard_framework/runs/covid_platform_fidelity_02_dp_design.json`; campaign
`campaigns/covid/platform_fidelity_02/`; analysis-only power calculation
`campaigns/covid/platform_fidelity_02/power_analysis.py` +
`power_analysis.json`.

The paired-seed power calculation on the PLATFORM-FIDELITY-01/01b cells fixes
200 seeds/arm (400 cells, full rerun of proxy `mega_cruise_5000` and dedicated
`diamond_princess`) under the frozen operating point (Θ 7.9e6, infection_age_days
6.8, imports 1, dwell_weighted, union `exempt_work_zones` protocols file
`data/config/protocols_covid_pf_dp_01b.json`). Primary endpoints are P(takeoff)
via exact two-sided McNemar and both-takeoff paired outbreak size via
one-sample t; unconditional burden, asymptomatic share, and CRN are reported,
never selected. No GM cells, no Theta refit, no platform selection.
