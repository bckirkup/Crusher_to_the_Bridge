# CONTAM-FORCED-EXHAUST-DUCTED-01
**Date:** 2026-11-14
**Commit:** e56172a8
**Pathogens:** all
**Status:** open
**Measured at:** e56172a8

Ducted relief/medical exhaust class of
`docs/proposals/forced_exhaust_audit_and_fix_plan.md` §5.5 row 5. This entry
authors `filtered` only: no `flow_rate_m3h`, `direction`, `mechanism`, path
string, or `is_hvac_ducted` alias changed. The branch commit carrying the
data/test changes is `e56172a8`; measurements below were taken on that tree
against baseline `d038bc3c`.

## Decisions

The live audit enumerates exactly 45 `forced_exhaust` links with
`is_hvac_ducted: true` across ten hulls, matching plan §5.5 with no count
drift: `mega_cruise_5000` 10, `spirit_cruise_3000` 8, `classic_cruise_1900` 6,
`enterprise_galaxy_tng` 6, `diamond_princess` 5, `messy_cruise_500` 3,
`enterprise_constitution_tos` 3, `san_antonio_class_lpd` 2,
`expedition_cruise_300` 1, and `legend_class_nsc` 1.

| Class | Links | Decision |
|---|---:|---|
| `medical_exhaust` | 2 | Flipped `filtered` to `false`: the links are declared medical exhaust streams, and the authoring basis is the independent-exhaust/negative-pressure regime of CDC VSP 2025 §33.2.1 by naval analogy (Grade C for these non-cruise hulls). No recirculation-filter credit. |
| `Cabin_Relief*` / `Corridor_Relief_Exhaust*` | 39 | Reviewed, no change, `filtered: true`. 28 links have empty descriptions; the rest describe cabin/corridor relief into the HVAC network but do not state a once-through/unfiltered regime, so the post-S1 alias behavior is kept. |
| `Galley_Exhaust_Return` | 1 | Reviewed, no change, `filtered: true`: the description explicitly keeps the remaining service return as a filtered prescribed-flow leg while the grease-hood exhaust is 100% overboard. |
| `galley_exhaust_to_mess` | 1 | Reviewed, no change, `filtered: false`: row 3 already removed filtration/recirculation credit. |
| `Dining_to_Galley_Transfer` | 2 | Reviewed, no change, `filtered: true`: explicitly parked by the tasking. Their descriptions mention exhausting odors overboard while the declared endpoints are AHU-to-AHU; reported as a possible follow-up defect candidate, not authored here. |

The two flipped links are `legend_class_nsc` `medical_exhaust`
(`HVAC_Medical` → `HVAC_Enlisted_Fwd`, 100 m³/h) and `san_antonio_class_lpd`
`medical_exhaust` (`HVAC_Medical` → `HVAC_Crew_Habitable`, 200 m³/h).

## Audit and flow-compare measurements

`tools/diag/forced_exhaust_audit.py audit` reconciles 82 platforms / 1,011
links before and after, and the row-5 class remains 45 links. The audit CSV's
`native_filtered` column is still the deprecated alias diagnostic
(`is_hvac_ducted`), so it reads `True` for the two medical links even though
the declared `filtered` field is now `false`; the native engine reads
`filtered`, and the exact-check below is the measurement of record.

Native flow-compare path counts (`tools.contam_flow_compare.native_links_report`)
are topology-only here and unchanged on both affected hulls:

| Hull | `n_paths` before → after | `cross_zone` before → after | `zone_degree` |
|---|---:|---:|---|
| `legend_class_nsc` | 171 → 171 | 87 → 87 | unchanged |
| `san_antonio_class_lpd` | 207 → 207 | 105 → 105 | unchanged |

## Exact-integral material-times

`tools/diag/forced_exhaust_audit.py exact-check`, native lane only
(`contamx_lane: false`), frozen Phase 1 tracer, horizon 12 h, sampling step
1 h, filter efficiency 0.5, natural decay 0. Sources are the link endpoints
plus `Engine_Room` where present. Values are exact retained-mass
material-time `exact_h` in hours, before → after; sanitary aggregate
`exact_h` is unchanged on both hulls.

| Hull | Source | Before | After | Δ |
|---|---|---:|---:|---:|
| `legend_class_nsc` | `Sickbay` | 0.195341 | 0.240702 | +0.045361 |
| `legend_class_nsc` | `CPO_Berthing` | 0.273972 | 0.274030 | +0.000058 |
| `legend_class_nsc` | `Crew_Mess` | 0.291018 | 0.291068 | +0.000050 |
| `legend_class_nsc` | `Enlisted_Berthing_Fwd` | 0.303672 | 0.303708 | +0.000036 |
| `legend_class_nsc` | `Engine_Room` | 0.099970 | 0.099974 | +0.000004 |
| `san_antonio_class_lpd` | `Medical_Ward` | 0.211200 | 0.229745 | +0.018545 |
| `san_antonio_class_lpd` | `Passageway_Main` | 0.268460 | 0.268594 | +0.000134 |
| `san_antonio_class_lpd` | `Crew_Mess` | 0.259543 | 0.259555 | +0.000012 |
| `san_antonio_class_lpd` | `Ship_Enlisted_Berthing` | 0.293339 | 0.293354 | +0.000015 |

The source-zone moves are the expected native consequence of removing the
recirculation-filter credit on the two medical legs: less arriving mass is
attenuated, and the linear network feeds the small moves back into adjacent
endpoint zones. They are not a flow-rate change.

## PRJ/exporter evidence

No byte-pinned committed PRJs are affected:
`tests/test_contamw34_commissioned.py::test_design_mode_is_byte_stable` pins
only `destroyer_baseline` and `expedition_cruise_450`, and neither carries a
row-5 ducted relief/medical link. Scratch
`tools.contam_prj_bridge.export_prj_with_path_map` before/after on the two
affected hulls is byte-identical for both PRJ text and `path_map.json`.

That is a reported exporter limitation, not a fix in this row: the X2 rule
emits a PRJ filter reference only when declared `filtered` is true and
differs from the `is_hvac_ducted` alias, and `path_map` carries only
`is_hvac_ducted` for these legs. A `filtered: false` declaration on a
ducted prescribed-flow link therefore changes native transport but is not
represented in the committed PRJ/path-map export. No ContamX commissioned
check was run because no PRJ was regenerated.

## Tests

- `tests/test_contam_forced_exhaust_ducted.py` pins the 45-link class, the
  per-platform counts, the exact `filtered: false` set, medical-exhaust
  description tokens, the filtered Galley return, and the San Antonio galley
  no-credit leg. It also adds native graded-response checks: the `filtered`
  bit moves downstream material-time while leaving the upstream zone
  unchanged, and scaling a one-way prescribed-flow leg changes downstream
  mass without moving mass upstream of that leg.
- `tests/test_contam_s1_migration.py` carries post-S1 exemptions for the two
  medical links whose resolved semantics intentionally differ from the S1
  migration alias; `legend_class_nsc` joins the operator-invariant skip set,
  while `san_antonio_class_lpd` was already skipped through the row-3 galley
  link.
- `schemas/air_flow_paths.schema.json` validation passed for both touched
  platform files, and `tools/sanity_checker.py --from-config` passed with only
  the pre-existing instrument-turnaround warnings.

## Status and blast radius

Status stays `open`: this entry records the landed authoring and native
measurements, not a campaign re-measurement. No `flow_rate_m3h` value
changed; no magnitude was re-derived; no direction/mechanism changed; no
engine/exporter code changed; no epidemiological constant changed; frozen
campaign, readout, cache, and prior CONTAM ledgers are untouched. Any
pre-change airborne/downstream-map dose figure resting on native filtration
through the two medical links is historical on that channel at baseline
`d038bc3c`; the pathogen open ledgers carry the withdrawal notes.
