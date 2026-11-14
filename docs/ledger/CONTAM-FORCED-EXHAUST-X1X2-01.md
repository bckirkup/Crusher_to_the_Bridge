# CONTAM-FORCED-EXHAUST-X1X2-01
**Date:** 2026-11-14
**Commit:** 4119dd79
**Pathogens:** all
**Status:** open

Stage X1/X2 of `docs/proposals/forced_exhaust_audit_and_fix_plan.md` (§5.4,
§5.6). The exporter now resolves cross-zone links with explicit-wins
`direction`/`mechanism`/`filtered` semantics identical to
`engines.py_contam_bridge.cross_zone_link_semantics`.

## Element verification

NIST TN 1887r1 Appendix A names `plr_bdq` the volume-flow powerlaw backdraft
damper; the user guide says backdraft dampers have different flow resistances
by pressure-drop direction with greatly reduced or zero flow in one direction.
X1 exports declared `direction: oneway` + `mechanism: pressure_opening` links as
`plr_bdq` with a zero negative branch; bidirectional pressure openings remain
`plr_orfc`. `mechanism: prescribed_flow` exports as `fan_cvf` regardless of
`filtered`; `filtered` selects the PRJ filter element in hobbyist exports.

## Cache convention

X1 changes solved airflow fields. The frozen `_v1` caches and prefixes are
untouched. `campaigns/contam/phase1_hvac_tracer_01/design/build.py` and
`campaigns/contam/phase2_cruise_contrasts_01/design/build.py` now carry the
v2 constants only: `..._field_cache_v2` schemas with design ids
`contam_phase1_hvac_tracer_02` and `contam_phase2_cruise_contrasts_02` and new
S3 URIs. No cache is produced by this change.

## Export-diff evidence

Element-selection diff over the ten §4.1 hulls (link counts, old alias rule →
new semantics): every `plr_orfc -> plr_bdq` entry is a declared one-way passive
opening; every `fan_cvf -> fan_cvf` entry is `prescribed_flow`; no prescribed
flow changed element. Totals: `plr_orfc->plr_bdq` = 3+13+5+5+13+17+63+28+11+5
= 163 links across the ten hulls; `fan_cvf->fan_cvf` = 67 links; remaining
passive links stay `plr_orfc`. The two byte-pinned committed PRJs
(`destroyer_baseline`, `expedition_cruise_450`) were regenerated for the
change-detector; other committed P-lane PRJs were not regenerated.
