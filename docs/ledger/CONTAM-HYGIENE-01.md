# CONTAM-HYGIENE-01
**Date:** 2026-11-01
**Commit:** 899e4ca0
**Pathogens:** all
**Status:** measured
**Measured at:** 899e4ca0

Implements ranked fix #5 of `docs/contam_museum_hull_audit.md`
(CONTAM-MUSEUM-01): Q3 declaration hygiene on the five authored hulls.

## Defect

The five authored (non-GA) hulls ran on engine defaults rather than the
tuned declaration convention every GA-imported hull carries: no
top-level `hvac_duty` (implicit 1.0 vs the tuned {0.0, 0.5} convention),
no top-level `oa_fraction`, and zero `oa_fraction` declarations on the
supply groups. `filter_efficiency` (fletcher ×7, legend ×9, san_antonio
×10) and `nbc_filter_*` (legend ×6) were declared per-group but are
inert — filtration is a single global `hvac.filter_efficiency` scalar
in both lanes (per-zone citadel is CONTAM-FLEET-01's recorded
inexpressibility gap), so the fields read as live knobs that do nothing.

## Fix

1. **Declarations** — each hull declares top-level `hvac_duty: 0.5`
   (the full-size-hull convention; small boats like pt_564 carry 0.3)
   and a top-level `oa_fraction`, and every supply group declares its
   own `oa_fraction`, purpose-graded on the GA convention
   (accommodation/public 0.2–0.3, mess/galley 0.3, medical/labs 0.5,
   machinery/vehicle/weather ventilation 0.8–1.0), refined by each
   hull's own declared character:
   - `fletcher_class_destroyer`: "forced-draft supply, no recirculation"
     → `oa_fraction 1.0` on every group (top-level 1.0).
   - `expedition_cruise_300`: own "~30% fresh air" declaration →
     0.3 on served groups; MedBay dedicated exhaust/negative pressure →
     1.0.
   - `legend_class_nsc` / `san_antonio_class_lpd` / `messy_cruise_500`:
     standard gradient; independent machinery/well-deck ventilation
     0.8–1.0.

   Chosen to declare the same convention the GA hulls encode — not
   fitted to any anchor; the change shifts realized HVAC throughput on
   these hulls toward the fleet convention.

2. **Schema honesty** — `filter_efficiency`, `nbc_filter_efficiency`,
   `nbc_filter_type` on HVACZone now carry explicit *advisory-only*
   descriptions (not consumed by either lane) instead of passing as
   undocumented extra fields.

## Measured

Post-fix re-audit (`tools/museum_hull_audit.py` Q3): all five hulls
`top_hvac_duty` 0.5, `duty_values` {0.0, 0.5} (the tuned convention),
`oa_group_coverage` 1.0. New `TestFleetDeclarationHygiene` tests lock
top-level defaults on all 80 platforms and complete group-oa on the
five hulls.

Residual (out of scope): ~89 supply groups on older cruise hulls still
inherit top-level `oa_fraction` rather than declaring per-group; the
invariant test documents this and only enforces the five audit hulls.
