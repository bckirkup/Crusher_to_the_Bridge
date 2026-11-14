# CONTAM-SANITARY-DIR-01
**Date:** 2026-11-14
**Commit:** a4a12227
**Pathogens:** all
**Status:** open
**Measured at:** fc858d1c5f55d800a77c7524be60f9dfb0756d4c

D1 of `docs/proposals/forced_exhaust_audit_and_fix_plan.md`: restore the
authored one-way guarantee on sanitary make-up air. `CONTAM-BIDIR-01` (#1141)
made undeclared passive links bidirectional by default; the sanitary links had
been authored one-directional on 2026-09-15 (`5b365345`) but carried no
`direction` key, so the new default silently reversed them. The introducing
change is `CONTAM-BIDIR-01` (`899e4ca0`); that entry is annotated, not rewritten.

## Change

- `data/platforms/*/air_flow_paths.json`: all 585 `Sanitary_Makeup` links on 82
  platforms now declare `"direction": "oneway"` by targeted text edit. No flow
  rate changed.
- `scripts/derive_sanitary_provisioning.py` emits the same key, so future hulls
  are born with the direction the generator's docstring already states.
- `tools/sanity_checker.py` rejects any cross-zone link sourced from an
  exhaust-only terminal (`hvac_duty <= 0`, `oa_fraction >= 1.0`, with the
  native top-level defaults 1.0 / 0.2), and any link into one unless
  `direction == "oneway"`; HVAC group ids and their room endpoints both count.
- `DEFAULT_PASSIVE_LINK_MODE` is unchanged: undeclared passive openings remain
  bidirectional, preserving the unreachable-zone repair `CONTAM-BIDIR-01`
  measured.

Value source: the generator's stated intent, CDC VSP §33.2.1–33.2.2, and ISO
9943 A.2.3, as recorded in the plan. This is a defect repair, not a new
constant.

## Audit extent and after-state

Before D1 (`a4a12227`), `tools/diag/forced_exhaust_audit.py audit` reconciled
82 platforms / 1,011 links and reported 599 links with
`native_reverse_on_stated_oneway`, carrying 6,131 reverse room paths. 585 of
those links were `Sanitary_Makeup` (6,071 paths); the other 14 are the
pre-existing non-sanitary stated-one-way rows left for the plan's authoring
rows.

After D1 (`fc858d1c`), the same audit reconciles and reports `direction_present`
on all 585 sanitary links, zero `native_reverse_on_stated_oneway` flags on
`Sanitary_Makeup`, and zero sanitary reverse paths. The 14 non-sanitary flags
remain, unchanged by this entry's scope. The destroyer flow-compare diagnostics
moved `n_paths` 61 → 54 and `cross_zone` 34 → 27, exactly the 7 reverse
sanitary room paths removed on that hull.

## Exact-integral material-times

`tools/diag/forced_exhaust_audit.py exact-check --source Mess_Hall`, horizon
12 h, native lane. Values are sanitary-source exact material-time in hours,
mean (min–max), from the before/after check JSONs. Baseline tree: `a4a12227`;
fixed tree: `fc858d1c`.

| Hull | Before | After |
|---|---:|---:|
| `classic_cruise_1900` | 0.2139 (0.146–0.299) | 0.0521 (0.052–0.052) |
| `destroyer_baseline` | 0.1841 (0.172–0.208) | 0.0521 (0.052–0.052) |
| `expedition_cruise_450` | 0.2324 (0.123–0.316) | 0.0521 (0.052–0.052) |
| `fletcher_class_destroyer` | 0.1310 (0.068–0.197) | 0.0521 (0.052–0.052) |
| `greg_mortimer` | 0.1872 (0.145–0.238) | 0.0521 (0.052–0.052) |
| `lexington_cv2` | 0.1994 (0.196–0.201) | 0.0524 (0.052–0.052) |
| `mega_cruise_5000` | 0.1865 (0.128–0.273) | 0.0521 (0.052–0.052) |
| `missouri_bb63` | 0.2650 (0.255–0.278) | 0.0524 (0.052–0.052) |
| `saratoga_cv3` | 0.1974 (0.196–0.199) | 0.0524 (0.052–0.052) |
| `spirit_cruise_3000` | 0.2109 (0.147–0.270) | 0.0521 (0.052–0.052) |

The after values are the exhaust-only identity `1 / ach` to solver tolerance
(0.0521 h at ach 19.2; 0.0524 h on the rounded museum-hull ach). The ContamX
lane is unchanged by the pin because the exporter does not read `direction`;
that exporter gap is X1 in the plan, not this entry.

## Status and blast radius

Status stays `open`: this entry records the landed data/guard fix and the
structural exact-integral check, not a campaign re-measurement. Any
pre-D1 figure that rests on native downstream-map reachability through a
sanitary head is historical on that channel at baseline `a4a12227`; the
pathogen open ledgers carry the withdrawal notes. No epidemiology constant,
flow rate, schema, exporter, or engine default changed.
