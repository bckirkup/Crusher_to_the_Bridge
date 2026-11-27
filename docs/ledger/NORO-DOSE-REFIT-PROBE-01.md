# NORO-DOSE-REFIT-PROBE-01
**Date:** 2026-11-27
**Commit:** #1439
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 3fe48d8b1916e1c06cdc92cc2d9c757574f9c53b

Short local degeneracy probe for the frozen common-dose refit design. Engine
source was clean at `3fe48d8b1916e1c06cdc92cc2d9c757574f9c53b`; the
`-dirty` suffix in probe rows reflects the then-uncommitted probe manifest and
documentation files, not an engine or configuration deviation. The committed
probe manifest is `picard_framework/runs/mega_cruise_campaign/noro_common_dose_refit_probe_v1_manifest.json`;
evidence is `docs/norovirus/common_dose_refit_probe_v1_summary.csv` and
`docs/norovirus/common_dose_refit_probe_v1_degeneracy.txt`.

Measured result: five `dose_adjustment` rungs `7.14, 7.57, 8.00, 8.43, 8.86`,
`expedition_cruise_450`, 48 epochs, seeds 8105/8106, fixed `reportable`
boarding and `syndromic_comp65`. `sweep_degeneracy.py` reports one collapsed
group containing all five rungs (`resolved fraction: 0.200`) on infection,
ever-ill, reported-case, crew-infection, and peak-prevalence outputs. The
axis is therefore design-blocked as a transmission-dose control on the current
mechanism coordinate; see
`docs/norovirus/common_dose_refit_campaign_design_v1.md`. No fitting,
submission, parameter, mechanism, or engine change occurred.
