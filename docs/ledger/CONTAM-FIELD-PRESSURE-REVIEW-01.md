# CONTAM-FIELD-PRESSURE-REVIEW-01
**Date:** 2026-11-16
**Commit:** f3da6a52
**Pathogens:** all
**Status:** measured
**Measured at:** f3da6a52

## Scope

Stage 1 of
[`../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../proposals/contam_field_adjudication_audit_and_fix_plan.md)
§5: the pressure/balance diagnostic, "before any data change". Changes
behaviour: **no**. This entry adds a tool and a table; no data, engine,
exporter, schema or constant is touched. Base `origin/main` `7d0eb006`
(#1245, #1247, #1248 merged). Evidence base:
[`CONTAM-FIELD-ADJUDICATION-01`](CONTAM-FIELD-ADJUDICATION-01.md),
[`CONTAM-FIELD-ENVELOPE-BOUNDARY-01`](CONTAM-FIELD-ENVELOPE-BOUNDARY-01.md),
[`CONTAM-FIELD-POOLDECK-OPENINGS-01`](CONTAM-FIELD-POOLDECK-OPENINGS-01.md).

The fleet table below is the measured input to stage 6
(`CONTAM-FIELD-ENVELOPE-MAKEUP-01`) and to the stage-3 service-hatch owner
decision (`CONTAM-FIELD-SERVICE-HATCH-01`). Neither is decided here.

## Tool

`tools/diag/contam_pressure_balance_diagnostic.py` (tests:
`tests/test_contam_pressure_balance_diagnostic.py`). Local ContamX
`third_party/contamx/contamx3`, steady state, no seeds, no AWS.

```bash
python3 tools/diag/contam_pressure_balance_diagnostic.py \
  --lane authored --lane commissioned --lane design \
  --out telemetry_buffer/contam_pressure_balance_diagnostic/fleet.json \
  --markdown telemetry_buffer/contam_pressure_balance_diagnostic/fleet.md
```

About 16 minutes on 2 cores, of which 15 are the three `olympia_c6` timeouts.
`--hull` restricts the fleet; `--source` / `--timing` add the paired
diagnostic's material-time cells; `--all-paths` writes every path row;
`--from-json` re-renders the Markdown without solving.

Definitions:

- **dP** is the `.sim` path-record pressure difference, joined to the path map
  by the path number embedded in the record. Sign follows the authored
  direction: negative dP on an `envelope_leak` (`zone -> ambient`) means the
  zone is below ambient.
- **Path classes:** `envelope_leak`; `ahs_terminal` / `ahs_system`;
  `exhaust_sink` (non-AHS path to ambient); `prescribed_link` (kinds the hull
  airflow declaration marks `mechanism: prescribed_flow`); `ducted_transfer`;
  `passive_opening` (everything else). The path map carries no mechanism, so
  the split is by kind; a kind declared with both mechanisms on one hull would
  be counted as prescribed.
- **Interior** = `passive_opening` + `ducted_transfer`. **Blocked** = an
  interior path whose solved flow is exactly zero; **flowing** = the rest. A
  blocked path's dP is the pressure difference a shut one-way opening holds, not
  a drop across moving air.
- **Make-up demand** = AHS return minus supply, plus exhaust sinks. **Balance
  residual** = envelope net inflow minus that demand.
- **k field/native** = per-zone specific outflow coefficient (1/h) of the
  solved field over the native declaration.

## Results (measured)

77 bundled hulls x 3 lanes = 231 rows, 228 solved. Envelope mode
`boundary_sink`, filter efficiency 0.3, ContamX timeout 300 s.

1. **`authored` equals `commissioned`.** All 76 solved hulls give identical
   reports on the two lanes (0 of 76 differ in any field), so the committed
   bundles are the commissioned export. The tables below omit `authored`.
2. **Commissioned lane: every solved hull is depressurised beyond any
   physical building pressure.** Per-hull max |dP| is at least 1.19 kPa on all
   76 hulls; 60 exceed 10 kPa and 32 exceed 100 kPa. The largest path is an envelope leak
   on 73 hulls and an exhaust sink at the same zone pressure on 3.
3. **The cause is a boundary balance, and it closes.** Make-up demand is drawn
   entirely through the envelope leaks: 580,223 m³/h inward fleet-wide, balance
   residual below 1e-3 m³/h on every hull. Naval hulls: 381,675 m³/h, all from
   exhaust-only AHS groups (return with no supply), no exhaust sinks.
   Cruise: 101,618 m³/h AHS imbalance plus 72,961 m³/h exhaust sinks. Fiction:
   10,969 plus 13,000 m³/h.
4. **Envelope dP follows make-up demand per leak.** Across the 76 commissioned
   hulls, log median envelope |dP| against log make-up demand per leak has
   slope 2.017, R² 0.994, with demand per leak from 9.6 to 326 m³/h. This is a
   descriptive fit, not a fitted parameter.
5. **Design lane, naval: plausible.** AHS imbalance is zero; max |dP| is
   0.49–374 Pa (median 152 Pa; the largest path is an AHS system path on 63 of 68 hulls), interior max 2.4 Pa.
6. **Design lane, cruise and fiction: still implausible.** With zero AHS
   imbalance the exhaust sinks alone give 1.8e5–7.2e5 Pa (cruise) and
   1.25e5–1.67e5 Pa (fiction). This class does not depend on the commissioned
   encoding.
7. **Cruise/fiction one-way `Sanitary_Makeup` openings are held shut.** These
   are declared `pressure_opening`, one-way. Commissioned: 411 interior paths
   on 7 of 8 hulls carry zero flow against more than 1 kPa (up to 1.05e6 Pa);
   design: 1,471 on 8 of 8, including every `Sanitary_Makeup` path on seven
   hulls. The heads they are meant to feed receive no transfer air through
   them. `greg_mortimer` commissioned is the exception (0 blocked above 1 kPa).
   No naval hull has a blocked path above 1 kPa on any lane.
8. **Flowing interior openings.** Cruise/fiction flowing interior max is
   21–934 Pa except `spirit_cruise_3000` (1.24e4 Pa commissioned, `corridor`).
   Naval commissioned: median hull 76 Pa; 15 hulls exceed 1 kPa, all on
   `ladder_well_*` kinds, led by `pope_ap110` 5.86e4 Pa, `gosper_apa170`
   1.6e4 Pa, `saratoga_cv60` 8.0e3 Pa, `texas_bb35` 7.6e3 Pa.
9. **Envelope direction agrees with the #1247 enumeration.** Commissioned: 1
   of 76 hulls outward (`south_dakota_bb49`, 2.0e-4 m³/h). Design: 69 of 76
   hulls, 458.2 m³/h outward.
10. **Service hatches (stage-3 input).** `service_hatch` dP, commissioned /
    design: `spirit_cruise_3000` 809 / 767 Pa, `expedition_cruise_450`
    613 / 446 Pa, `classic_cruise_1900` 458 / 266 Pa,
    `enterprise_constitution_tos` 51 / 47 Pa, `diamond_princess` 22 / 24 Pa;
    `mega_cruise_5000`, `greg_mortimer`, `enterprise_galaxy_tng`, `apl_24`,
    `destroyer_baseline` below 5 Pa. Naval `hatch` kinds are below 6 Pa
    commissioned except `montana_acr13` (107 Pa max over 20 paths).
11. **Native vs field outflow coefficient.** Commissioned per-hull median
    ratio: naval 1.03 (0.83–6.67; `lexington_cv2` 4.1, `saratoga_cv3` 6.7),
    cruise 1.01, fiction 1.00; 507 of 4,803 zones are above double native and
    19 below half. Design, naval: 820 of 3,971 zones below half native, 672
    above double.
12. **`olympia_c6` timed out at 300 s on all three lanes**, design included.
    This is the solver-performance outlier already recorded in
    [`CONTAM-FIELD-AHS-COMMISSIONED-01`](CONTAM-FIELD-AHS-COMMISSIONED-01.md);
    not fixed here. No other hull failed and none needed a data change to
    solve.

## Stage-6 scope this defines (inferred, not tested here)

- **Fleet-wide, commissioned lane (76/76 solved hulls):** exhaust-only AHS
  groups have no authored make-up path, so the fixed-area envelope leaks carry
  it. Severity is ordered by make-up demand per leak (table below).
- **Cruise + fiction (8 hulls), both lanes:** prescribed exhaust sinks with no
  matching make-up; one-way sanitary make-up openings blocked.
- **Naval `ladder_well_*` openings on 15 hulls** carry 1–59 kPa while flowing
  on the commissioned lane; whether that resolves once the make-up is authored
  is untested.

Class-(d) evidence already on record, not re-measured here: a
`prescribed_flow` `Sanitary_Makeup` at the current leak area worsens
Expedition to about −1.75e6 Pa; leak area 0.0001 → ~0.1 m² gives Expedition
20–26 Pa and destroyer below 1 Pa; a per-hull area needs an exporter override
([`CONTAM-FIELD-POOLDECK-OPENINGS-01`](CONTAM-FIELD-POOLDECK-OPENINGS-01.md)).

## Limitations

- Steady-state field only; no transport or epidemiology was run.
- "Blocked" is exact zero flow in the `.sim` single-precision record. On the
  naval design lane 4,134 interior paths are zero-flow at under 2.4 Pa; those
  are idle openings, not adverse-pressure blocks. Read the ">1 kPa" count.
- `olympia_c6` contributes no row.

## Commissioned lane by hull type

| hull type | hulls | max dP Pa (median) | flowing interior max dP Pa (median) | make-up per leak m3/h (median) | exhaust-only AHS share (median) |
|---|---|---|---|---|---|
| cruise | 6 | 9.85e+05 | 340 | 264.5 | 0.61 |
| cvl | 1 | 8.85e+05 | 1.89e+03 | 262.9 | 0.30 |
| cg | 1 | 4.6e+05 | 400 | 161.2 | 0.50 |
| cc | 1 | 4.54e+05 | 5.15e+03 | 174.1 | 0.38 |
| cl | 1 | 3.5e+05 | 1.52e+03 | 118.5 | 0.36 |
| apa | 1 | 3.35e+05 | 1.6e+04 | 162.3 | 0.67 |
| lsd | 1 | 2.94e+05 | 3.8 | 151.8 | 0.56 |
| ap | 3 | 2.78e+05 | 4.92 | 147.8 | 0.53 |
| fiction | 2 | 2.46e+05 | 493 | 132.0 | 0.67 |
| ao | 1 | 1.93e+05 | 172 | 123.3 | 0.20 |
| bb | 8 | 1.61e+05 | 2.17e+03 | 104.0 | 0.45 |
| cv | 7 | 1.52e+05 | 584 | 109.4 | 0.36 |
| acr | 1 | 1.32e+05 | 2.6e+03 | 102.0 | 0.65 |
| r | 1 | 1.14e+05 | 1.23 | 94.9 | 0.50 |
| ca | 1 | 9.48e+04 | 228 | 55.6 | 0.36 |
| cve | 2 | 7.67e+04 | 284 | 77.5 | 0.37 |
| cvs | 1 | 7.32e+04 | 512 | 75.6 | 0.30 |
| arg | 1 | 7.01e+04 | 3.41 | 74.5 | 0.57 |
| ars | 1 | 6.77e+04 | 2.31 | 69.7 | 0.33 |
| other | 8 | 4.54e+04 | 1.75 | 53.3 | 0.50 |
| j | 2 | 4.38e+04 | 120 | 58.6 | 0.50 |
| ar | 1 | 3.95e+04 | 1.85 | 55.8 | 0.50 |
| lst | 1 | 2.97e+04 | 1.37 | 48.2 | 0.40 |
| acv | 1 | 2.86e+04 | 78.4 | 47.3 | 0.27 |
| k | 1 | 2.18e+04 | 136 | 41.5 | 0.60 |
| apd | 1 | 2.03e+04 | 106 | 39.8 | 0.25 |
| cgs | 1 | 1.9e+04 | 13.5 | 38.6 | 0.40 |
| de | 1 | 1.73e+04 | 126 | 36.7 | 0.25 |
| dd | 8 | 1.3e+04 | 5.92 | 28.5 | 0.40 |
| aks | 1 | 1.2e+04 | 1.39 | 30.8 | 0.50 |
| pg | 1 | 1.18e+04 | 61.3 | 30.3 | 0.43 |
| arc | 1 | 9.64e+03 | 101 | 26.7 | 0.36 |
| am | 1 | 9.38e+03 | 1.45 | 23.3 | 0.33 |
| ec | 1 | 6.98e+03 | 58.3 | 23.0 | 0.38 |
| dms | 1 | 6.35e+03 | 4.08 | 22.2 | 0.50 |
| ac | 1 | 5.1e+03 | 74.1 | 20.0 | 0.50 |
| pe | 1 | 2.1e+03 | 2.44 | 12.8 | 0.50 |
| pc | 1 | 2.08e+03 | 3.4 | 12.8 | 0.50 |
| mso | 1 | 1.47e+03 | 1.62 | 10.8 | 0.43 |

### Hull-class summary

| metric | commissioned / naval | design / naval | commissioned / cruise | design / cruise | commissioned / fiction | design / fiction |
|---|---|---|---|---|---|---|
| unsolved | 1 | 1 | 0 | 0 | 0 | 0 |
| hulls | 68 | 68 | 6 | 6 | 2 | 2 |
| max_abs_dp_pa | 1.19e+03 / 5.85e+04 / 1.36e+06 | 0.492 / 152 / 374 | 8.74e+05 / 9.85e+05 / 1.24e+06 | 1.76e+05 / 3.66e+05 / 7.16e+05 | 1.9e+05 / 2.46e+05 / 3.01e+05 | 1.25e+05 / 1.46e+05 / 1.67e+05 |
| hulls_over_1kpa | 68 | 0 | 6 | 6 | 2 | 2 |
| hulls_over_10kpa | 52 | 0 | 6 | 6 | 2 | 2 |
| hulls_over_100kpa | 24 | 0 | 6 | 6 | 2 | 2 |
| interior_max_abs_dp_pa | 0.845 / 76.2 / 5.86e+04 | 1.24e-06 / 0.579 / 2.38 | 221 / 8.01e+05 / 1.05e+06 | 1.76e+05 / 3.66e+05 / 7.16e+05 | 5.48e+03 / 6.14e+04 / 1.17e+05 | 1.25e+05 / 1.46e+05 / 1.67e+05 |
| hulls_interior_over_1kpa | 15 | 0 | 5 | 6 | 2 | 2 |
| interior_flowing_max_abs_dp_pa | 0.845 / 76.2 / 5.86e+04 | 1.73e-08 / 0.0106 / 0.147 | 21.5 / 340 / 1.24e+04 | 17.5 / 284 / 8.12e+03 | 51.1 / 493 / 934 | 46.8 / 453 / 860 |
| hulls_interior_flowing_over_1kpa | 15 | 0 | 1 | 1 | 0 | 0 |
| interior_blocked_paths | 303 | 4134 | 557 | 1176 | 163 | 318 |
| interior_blocked_paths_over_1kpa | 0 | 0 | 272 | 1153 | 139 | 318 |
| hulls_with_blocked_over_1kpa | 0 | 0 | 5 | 6 | 2 | 2 |
| makeup_per_leak_m3h | 9.64 / 65.3 / 326 | 0 / 0 / 0 | 228 / 265 / 299 | 78.1 / 122 / 170 | 115 / 132 / 149 | 63 / 71.2 / 79.4 |
| ahs_return_minus_supply_m3h | 3.817e+05 | 0 | 1.016e+05 | 0 | 1.097e+04 | 0 |
| exhaust_sink_out_m3h | 0 | 0 | 7.296e+04 | 7.296e+04 | 1.3e+04 | 1.3e+04 |
| envelope_inward_m3h | 3.817e+05 | 390.8 | 1.746e+05 | 7.303e+04 | 2.397e+04 | 1.3e+04 |
| envelope_outward_m3h | 0.0001988 | 390.8 | 0 | 67.45 | 0 | 0 |
| hulls_with_outward_leak | 1 | 68 | 0 | 1 | 0 | 0 |
| max_abs_balance_residual_m3h | 0.0001118 | 1.046e-05 | 0.0008689 | 0.0008578 | 0.0002896 | 0.0003146 |
| median_field_over_native | 0.83 / 1.03 / 6.67 | 0.0167 / 0.897 / 1.52 | 1 / 1.01 / 1.08 | 0.977 / 0.997 / 1.08 | 1 / 1 / 1 | 0.998 / 1.01 / 1.02 |
| zones | 3971 | 3971 | 642 | 642 | 190 | 190 |
| zones_below_half_native | 19 | 820 | 0 | 15 | 0 | 0 |
| zones_above_double_native | 441 | 672 | 56 | 112 | 10 | 12 |

### Fleet table

| hull | class | lane | zones | max dP Pa | envelope median dP Pa | interior max dP Pa | interior flowing max dP Pa | blocked interior n (>1 kPa) | leaks in/out | envelope in m3/h | envelope out m3/h | AHS return-supply m3/h | exhaust sinks m3/h | make-up per leak m3/h | exhaust-only AHS | k field/native median (min-max) | zones <0.5x / >2x |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | cruise | commissioned | 79 | 9.89e+05 | 9.86e+05 | 8.05e+05 | 458 | 48 (30) | 79/0 | 20709.2 | 0 | 8706.1 | 12003.0 | 262.1 | 17/30 | 1.01 (0.85-2.78) | 0/5 |
| classic_cruise_1900 | cruise | design | 79 | 4.85e+05 | 4.83e+05 | 4.85e+05 | 266 | 63 (63) | 62/0 | 12003.0 | 0 | 0.0 | 12003.0 | 151.9 | 0/30 | 1.00 (0.45-6.76) | 2/9 |
| diamond_princess | cruise | commissioned | 159 | 1.04e+06 | 1.04e+06 | 8.59e+05 | 21.5 | 170 (96) | 159/0 | 43873.4 | 0 | 25873.4 | 18000.0 | 275.9 | 39/57 | 1.02 (0.69-39.82) | 0/17 |
| diamond_princess | cruise | design | 159 | 2.91e+05 | 2.9e+05 | 2.91e+05 | 25 | 400 (400) | 120/0 | 18000.0 | 0 | 0.0 | 18000.0 | 113.2 | 0/57 | 1.07 (0.24-42.75) | 4/48 |
| expedition_cruise_450 | cruise | commissioned | 47 | 9.82e+05 | 9.81e+05 | 7.98e+05 | 613 | 31 (25) | 47/0 | 12544.7 | 0 | 4535.8 | 8008.8 | 266.9 | 13/22 | 1.08 (0.63-3.19) | 0/2 |
| expedition_cruise_450 | cruise | design | 47 | 7.16e+05 | 7.14e+05 | 7.16e+05 | 446 | 53 (53) | 34/0 | 8008.8 | 0 | 0.0 | 8008.8 | 170.4 | 0/22 | 1.08 (0.42-4.91) | 1/6 |
| greg_mortimer | cruise | commissioned | 50 | 9.77e+05 | 9.75e+05 | 221 | 221 | 12 (0) | 50/0 | 11396.4 | 0 | 6452.8 | 4943.6 | 227.9 | 11/22 | 1.01 (0.69-27.57) | 0/7 |
| greg_mortimer | cruise | design | 50 | 3.37e+05 | 3.36e+05 | 3.36e+05 | 303 | 61 (52) | 31/8 | 5011.0 | 67.45 | 0.0 | 4943.6 | 98.9 | 0/22 | 0.98 (0.42-16.18) | 1/14 |
| mega_cruise_5000 | cruise | commissioned | 192 | 1.24e+06 | 1.22e+06 | 1.05e+06 | 123 | 195 (70) | 192/0 | 57338.2 | 0 | 42335.4 | 15002.8 | 298.6 | 63/83 | 1.01 (0.61-65.92) | 0/8 |
| mega_cruise_5000 | cruise | design | 192 | 1.76e+05 | 1.74e+05 | 1.76e+05 | 17.5 | 446 (432) | 129/0 | 15002.8 | 0 | 0.0 | 15002.8 | 78.1 | 0/83 | 1.00 (0.33-35.22) | 5/16 |
| spirit_cruise_3000 | cruise | commissioned | 115 | 8.74e+05 | 8.53e+05 | 6.89e+05 | 1.24e+04 | 101 (51) | 115/0 | 28716.7 | 0 | 13714.1 | 15002.6 | 249.7 | 28/45 | 1.00 (0.62-25.70) | 0/17 |
| spirit_cruise_3000 | cruise | design | 115 | 3.95e+05 | 3.81e+05 | 3.95e+05 | 8.12e+03 | 153 (153) | 87/0 | 15002.6 | 0 | 0.0 | 15002.6 | 130.5 | 0/45 | 1.00 (0.43-17.19) | 2/19 |
| enterprise_constitution_tos | fiction | commissioned | 63 | 3.01e+05 | 3e+05 | 1.17e+05 | 51.1 | 37 (29) | 63/0 | 9411.6 | 0 | 4411.6 | 5000.0 | 149.4 | 19/29 | 1.00 (0.84-2.30) | 0/4 |
| enterprise_constitution_tos | fiction | design | 63 | 1.67e+05 | 1.67e+05 | 1.67e+05 | 46.8 | 93 (93) | 44/0 | 5000.0 | 0 | 0.0 | 5000.0 | 79.4 | 0/29 | 1.02 (0.50-2.55) | 0/5 |
| enterprise_galaxy_tng | fiction | commissioned | 127 | 1.9e+05 | 1.89e+05 | 5.48e+03 | 934 | 126 (110) | 127/0 | 14557.8 | 0 | 6557.8 | 8000.0 | 114.6 | 37/54 | 1.00 (0.71-4.70) | 0/6 |
| enterprise_galaxy_tng | fiction | design | 127 | 1.25e+05 | 1.24e+05 | 1.25e+05 | 860 | 225 (225) | 90/0 | 8000.0 | 0 | 0.0 | 8000.0 | 63.0 | 0/54 | 1.00 (0.50-4.53) | 0/7 |
| jupiter_ac3 | ac | commissioned | 50 | 5.1e+03 | 5.1e+03 | 74.1 | 74.1 | 0 (0) | 50/0 | 1000.8 | 0 | 1000.8 | 0.0 | 20.0 | 4/8 | 1.02 (0.90-1.08) | 0/0 |
| jupiter_ac3 | ac | design | 50 | 137 | 0.569 | 0.575 | 0.0138 | 60 (0) | 20/26 | 4.7 | 4.707 | 0.0 | 0.0 | 0.0 | 0/8 | 1.52 (0.17-16.89) | 6/20 |
| montana_acr13 | acr | commissioned | 146 | 1.32e+05 | 1.32e+05 | 2.6e+03 | 2.6e+03 | 4 (0) | 146/0 | 14888.3 | 0 | 14888.3 | 0.0 | 102.0 | 11/17 | 1.33 (0.50-49.60) | 1/53 |
| montana_acr13 | acr | design | 146 | 156 | 0.456 | 0.847 | 0.147 | 609 (0) | 81/54 | 12.1 | 12.13 | 0.0 | 0.0 | 0.0 | 0/17 | 0.57 (0.00-33.79) | 46/20 |
| battler_acv6 | acv | commissioned | 55 | 2.86e+04 | 2.85e+04 | 78.4 | 78.4 | 2 (0) | 55/0 | 2599.5 | 0 | 2599.5 | 0.0 | 47.3 | 3/11 | 1.02 (0.94-1.33) | 0/0 |
| battler_acv6 | acv | design | 55 | 7.08 | 0.617 | 0.625 | 0.0073 | 45 (0) | 30/22 | 6.6 | 6.595 | 0.0 | 0.0 | 0.0 | 0/11 | 1.15 (0.27-18.15) | 4/14 |
| mercury_aks20 | aks | commissioned | 61 | 1.2e+04 | 1.2e+04 | 1.39 | 1.39 | 0 (0) | 61/0 | 1876.2 | 0 | 1876.2 | 0.0 | 30.8 | 3/6 | 1.03 (0.86-1.32) | 0/0 |
| mercury_aks20 | aks | design | 61 | 205 | 0.443 | 0.443 | 4.62e-05 | 72 (0) | 21/37 | 5.2 | 5.215 | 0.0 | 0.0 | 0.0 | 0/6 | 1.47 (0.19-7.06) | 9/22 |
| raven_am55 | am | commissioned | 21 | 9.38e+03 | 9.38e+03 | 1.45 | 1.45 | 2 (0) | 18/0 | 490.2 | 0 | 490.2 | 0.0 | 23.3 | 1/3 | 1.01 (0.76-2.72) | 0/2 |
| raven_am55 | am | design | 21 | 0.492 | 0.0953 | 0.0953 | 0.000335 | 11 (0) | 7/10 | 1.1 | 1.082 | 0.0 | 0.0 | 0.0 | 0/3 | 1.38 (0.01-4.10) | 5/6 |
| passumpsic_ao106 | ao | commissioned | 27 | 1.93e+05 | 1.93e+05 | 172 | 172 | 0 (0) | 27/0 | 3330.2 | 0 | 3330.2 | 0.0 | 123.3 | 1/5 | 1.15 (0.76-34.26) | 0/4 |
| passumpsic_ao106 | ao | design | 27 | 165 | 0.38 | 0.144 | 0.0014 | 4 (0) | 11/15 | 2.7 | 2.678 | 0.0 | 0.0 | 0.0 | 0/5 | 0.89 (0.00-2.23) | 6/1 |
| lyon_ap71 | ap | commissioned | 59 | 2.78e+05 | 2.78e+05 | 4.92 | 4.92 | 2 (0) | 59/0 | 8720.2 | 0 | 8720.2 | 0.0 | 147.8 | 8/15 | 1.16 (0.81-17.90) | 0/11 |
| lyon_ap71 | ap | design | 59 | 151 | 0.323 | 0.799 | 0.000397 | 48 (0) | 25/26 | 5.2 | 5.221 | 0.0 | 0.0 | 0.0 | 0/15 | 0.72 (0.01-4.14) | 13/4 |
| pope_ap110 | ap | commissioned | 88 | 1.36e+06 | 1.35e+06 | 5.86e+04 | 5.86e+04 | 17 (0) | 88/0 | 28574.9 | 0 | 28574.9 | 0.0 | 324.7 | 7/13 | 1.25 (0.56-4.36) | 0/10 |
| pope_ap110 | ap | design | 88 | 215 | 0.421 | 2.03 | 0.0753 | 77 (0) | 39/42 | 9.4 | 9.396 | 0.0 | 0.0 | 0.0 | 0/13 | 0.99 (0.31-4.97) | 8/13 |
| squier_ap130 | ap | commissioned | 52 | 1.33e+05 | 1.33e+05 | 4.38 | 4.38 | 0 (0) | 52/0 | 5326.1 | 0 | 5326.1 | 0.0 | 102.4 | 3/8 | 1.07 (0.95-1.33) | 0/0 |
| squier_ap130 | ap | design | 52 | 126 | 0.465 | 0.467 | 0.00224 | 54 (0) | 20/29 | 4.9 | 4.897 | 0.0 | 0.0 | 0.0 | 0/8 | 1.03 (0.42-3.12) | 6/9 |
| gosper_apa170 | apa | commissioned | 71 | 3.35e+05 | 3.34e+05 | 1.6e+04 | 1.6e+04 | 1 (0) | 71/0 | 11525.1 | 0 | 11525.1 | 0.0 | 162.3 | 6/9 | 1.06 (0.88-2.27) | 0/1 |
| gosper_apa170 | apa | design | 71 | 107 | 0.581 | 0.61 | 0.029 | 105 (0) | 33/32 | 7.3 | 7.325 | 0.0 | 0.0 | 0.0 | 0/9 | 1.01 (0.16-6.61) | 11/19 |
| ruchamkin_apd89 | apd | commissioned | 32 | 2.03e+04 | 2.02e+04 | 106 | 106 | 1 (0) | 32/0 | 1273.9 | 0 | 1273.9 | 0.0 | 39.8 | 1/4 | 1.03 (0.86-4.00) | 0/4 |
| ruchamkin_apd89 | apd | design | 32 | 111 | 0.579 | 0.579 | 0.00521 | 9 (0) | 15/16 | 3.4 | 3.407 | 0.0 | 0.0 | 0.0 | 0/4 | 0.76 (0.01-3.02) | 4/3 |
| assistance_ar17 | ar | commissioned | 57 | 3.95e+04 | 3.95e+04 | 1.85 | 1.85 | 3 (0) | 57/0 | 3180.4 | 0 | 3180.4 | 0.0 | 55.8 | 3/6 | 1.04 (0.79-1.51) | 0/0 |
| assistance_ar17 | ar | design | 57 | 226 | 0.68 | 1.4 | 0.04 | 81 (0) | 26/28 | 6.2 | 6.158 | 0.0 | 0.0 | 0.0 | 0/6 | 1.22 (0.21-6.85) | 9/19 |
| aeolus_arc3 | arc | commissioned | 40 | 9.64e+03 | 9.49e+03 | 101 | 101 | 3 (0) | 39/0 | 1066.0 | 0 | 1066.0 | 0.0 | 26.7 | 4/11 | 1.01 (0.86-1.64) | 0/0 |
| aeolus_arc3 | arc | design | 40 | 1.83 | 0.436 | 1.83 | 0.00281 | 24 (0) | 16/19 | 4.0 | 3.986 | 0.0 | 0.0 | 0.0 | 0/11 | 0.93 (0.01-6.37) | 6/8 |
| luzon_arg2 | arg | commissioned | 69 | 7.01e+04 | 7.01e+04 | 3.41 | 3.41 | 1 (0) | 69/0 | 5138.3 | 0 | 5138.3 | 0.0 | 74.5 | 4/7 | 1.12 (0.77-1.81) | 0/0 |
| luzon_arg2 | arg | design | 69 | 224 | 0.408 | 1.61 | 0.0532 | 113 (0) | 37/28 | 6.2 | 6.217 | 0.0 | 0.0 | 0.0 | 0/7 | 1.10 (0.21-6.73) | 6/10 |
| bolster_ars38 | ars | commissioned | 24 | 6.77e+04 | 6.77e+04 | 2.31 | 2.31 | 1 (0) | 23/0 | 1672.7 | 0 | 1672.7 | 0.0 | 69.7 | 1/3 | 1.12 (0.86-7.67) | 0/5 |
| bolster_ars38 | ars | design | 24 | 106 | 0.502 | 0.502 | 7.77e-05 | 12 (0) | 9/13 | 2.6 | 2.575 | 0.0 | 0.0 | 0.0 | 0/3 | 0.54 (0.01-2.32) | 9/1 |
| idaho_bb42 | bb | commissioned | 114 | 6.13e+04 | 6.07e+04 | 888 | 888 | 15 (0) | 114/0 | 7902.8 | 0 | 7902.8 | 0.0 | 69.3 | 5/13 | 1.03 (0.74-5.67) | 0/2 |
| idaho_bb42 | bb | design | 114 | 283 | 0.472 | 0.486 | 0.0524 | 84 (0) | 53/56 | 12.0 | 12.01 | 0.0 | 0.0 | 0.0 | 0/13 | 1.09 (0.01-7.39) | 10/18 |
| missouri_bb63 | bb | commissioned | 103 | 3.56e+05 | 3.56e+05 | 2.17e+03 | 2.17e+03 | 9 (0) | 103/0 | 17264.0 | 0 | 17264.0 | 0.0 | 167.6 | 5/11 | 1.06 (0.81-2.00) | 0/2 |
| missouri_bb63 | bb | design | 103 | 224 | 0.418 | 1.72 | 0.0131 | 115 (0) | 51/47 | 8.8 | 8.848 | 0.0 | 0.0 | 0.0 | 0/11 | 1.13 (0.26-8.19) | 15/20 |
| new_jersey_bb62 | bb | commissioned | 103 | 3.57e+05 | 3.56e+05 | 2.17e+03 | 2.17e+03 | 9 (0) | 103/0 | 17273.4 | 0 | 17273.4 | 0.0 | 167.7 | 5/11 | 1.06 (0.81-2.01) | 0/2 |
| new_jersey_bb62 | bb | design | 103 | 224 | 0.418 | 1.72 | 0.0131 | 115 (0) | 51/47 | 8.8 | 8.848 | 0.0 | 0.0 | 0.0 | 0/11 | 1.13 (0.26-8.20) | 15/20 |
| new_york_bb34 | bb | commissioned | 83 | 3.27e+04 | 3.26e+04 | 1.14e+03 | 1.14e+03 | 7 (0) | 82/0 | 4135.6 | 0 | 4135.6 | 0.0 | 49.8 | 5/10 | 1.02 (0.87-5.38) | 0/5 |
| new_york_bb34 | bb | design | 83 | 97.9 | 0.689 | 0.704 | 0.0337 | 62 (0) | 37/40 | 9.5 | 9.532 | 0.0 | 0.0 | 0.0 | 0/10 | 1.10 (0.01-4.91) | 13/16 |
| south_dakota_bb49 | bb | commissioned | 55 | 1.93e+05 | 1.93e+05 | 1.01e+03 | 1.01e+03 | 2 (0) | 52/2 | 6047.5 | 0.0001988 | 6047.5 | 0.0 | 110.0 | 3/8 | 1.04 (0.00-12.34) | 5/6 |
| south_dakota_bb49 | bb | design | 55 | 183 | 0.581 | 0.658 | 0.0112 | 32 (0) | 25/26 | 4.8 | 4.784 | 0.0 | 0.0 | 0.0 | 0/8 | 0.86 (0.00-5.10) | 14/8 |
| texas_bb35 | bb | commissioned | 92 | 1.28e+05 | 1.28e+05 | 7.59e+03 | 7.59e+03 | 5 (0) | 90/0 | 9022.0 | 0 | 9022.0 | 0.0 | 98.1 | 5/10 | 1.10 (0.86-10.07) | 0/5 |
| texas_bb35 | bb | design | 92 | 130 | 0.434 | 1.23 | 0.102 | 56 (0) | 44/41 | 9.4 | 9.399 | 0.0 | 0.0 | 0.0 | 0/10 | 1.26 (0.01-13.19) | 16/26 |
| west_virginia_bb48 | bb | commissioned | 198 | 8.43e+04 | 8.43e+04 | 3.37e+03 | 3.37e+03 | 16 (0) | 197/0 | 16060.6 | 0 | 16060.6 | 0.0 | 81.1 | 9/19 | 1.45 (0.29-12.33) | 3/46 |
| west_virginia_bb48 | bb | design | 198 | 312 | 0.579 | 0.578 | 0.0591 | 124 (0) | 99/89 | 21.9 | 21.94 | 0.0 | 0.0 | 0.0 | 0/19 | 0.75 (0.01-5.45) | 46/33 |
| wisconsin_bb64 | bb | commissioned | 103 | 3.56e+05 | 3.56e+05 | 2.17e+03 | 2.17e+03 | 9 (0) | 103/0 | 17263.6 | 0 | 17263.6 | 0.0 | 167.6 | 5/11 | 1.06 (0.81-2.00) | 0/2 |
| wisconsin_bb64 | bb | design | 103 | 224 | 0.418 | 1.72 | 0.0131 | 115 (0) | 51/47 | 8.8 | 8.848 | 0.0 | 0.0 | 0.0 | 0/11 | 1.13 (0.26-8.18) | 15/20 |
| olympia_c6 | c | commissioned | 104 | unsolved |  |  |  |  |  |  |  |  |  |  |  |  |  |
| olympia_c6 | c | design | 104 | unsolved |  |  |  |  |  |  |  |  |  |  |  |  |  |
| astoria_ca34 | ca | commissioned | 65 | 9.48e+04 | 9.47e+04 | 228 | 228 | 15 (0) | 42/0 | 3611.8 | 0 | 3611.8 | 0.0 | 55.6 | 4/11 | 1.00 (0.61-3.30) | 0/1 |
| astoria_ca34 | ca | design | 65 | 11.8 | 3.69e-07 | 0.686 | 0.000267 | 63 (0) | 11/22 | 1.1 | 1.063 | 0.0 | 0.0 | 0.0 | 0/11 | 0.88 (0.00-10.51) | 8/13 |
| wright_cc2 | cc | commissioned | 68 | 4.54e+05 | 4.53e+05 | 5.15e+03 | 5.15e+03 | 7 (0) | 63/0 | 11838.4 | 0 | 11838.4 | 0.0 | 174.1 | 5/13 | 1.06 (0.86-3.94) | 0/3 |
| wright_cc2 | cc | design | 68 | 206 | 0.442 | 1.8 | 0.0272 | 70 (0) | 18/40 | 7.5 | 7.45 | 0.0 | 0.0 | 0.0 | 0/13 | 0.87 (0.32-7.25) | 3/11 |
| chicago_cg11 | cg | commissioned | 87 | 4.6e+05 | 4.6e+05 | 400 | 400 | 14 (0) | 74/0 | 14025.8 | 0 | 14025.8 | 0.0 | 161.2 | 7/14 | 1.18 (0.72-13.14) | 0/9 |
| chicago_cg11 | cg | design | 87 | 165 | 0.391 | 0.391 | 0.0021 | 95 (0) | 19/45 | 7.9 | 7.861 | 0.0 | 0.0 | 0.0 | 0/14 | 0.97 (0.01-6.00) | 13/12 |
| alexander_henry_cgs119 | cgs | commissioned | 28 | 1.9e+04 | 1.9e+04 | 13.5 | 13.5 | 0 (0) | 28/0 | 1080.0 | 0 | 1080.0 | 0.0 | 38.6 | 4/10 | 1.03 (0.87-3.09) | 0/4 |
| alexander_henry_cgs119 | cgs | design | 28 | 1.54 | 0.369 | 1.54 | 0.00128 | 20 (0) | 9/15 | 2.8 | 2.821 | 0.0 | 0.0 | 0.0 | 0/10 | 0.71 (0.01-3.86) | 6/3 |
| miami_cl89 | cl | commissioned | 81 | 3.5e+05 | 3.5e+05 | 1.52e+03 | 1.52e+03 | 13 (0) | 58/0 | 9600.0 | 0 | 9600.0 | 0.0 | 118.5 | 4/11 | 1.14 (0.00-5.76) | 4/8 |
| miami_cl89 | cl | design | 81 | 189 | 0.636 | 2.38 | 0.0118 | 61 (0) | 28/20 | 7.4 | 7.384 | 0.0 | 0.0 | 0.0 | 0/11 | 0.89 (0.00-6.18) | 14/18 |
| lexington_cv2 | cv | commissioned | 97 | 5.21e+04 | 5.2e+04 | 2.23 | 2.23 | 6 (0) | 97/0 | 6232.5 | 0 | 6232.5 | 0.0 | 64.3 | 5/6 | 4.12 (0.98-26.74) | 0/83 |
| lexington_cv2 | cv | design | 97 | 315 | 1.22 | 1.22 | 3.15e-05 | 21 (0) | 48/44 | 12.3 | 12.26 | 0.0 | 0.0 | 0.0 | 0/6 | 0.02 (0.00-0.93) | 89/0 |
| midway_cv41 | cv | commissioned | 65 | 1.34e+06 | 1.34e+06 | 14.6 | 14.6 | 3 (0) | 65/0 | 21176.2 | 0 | 21176.2 | 0.0 | 325.8 | 3/10 | 1.05 (0.90-2.22) | 0/1 |
| midway_cv41 | cv | design | 65 | 354 | 0.69 | 1.46 | 7.55e-05 | 47 (0) | 31/31 | 8.0 | 7.994 | 0.0 | 0.0 | 0.0 | 0/10 | 0.99 (0.25-30.83) | 4/11 |
| ranger_cv4 | cv | commissioned | 74 | 1.52e+05 | 1.52e+05 | 584 | 584 | 3 (0) | 74/0 | 8093.6 | 0 | 8093.6 | 0.0 | 109.4 | 5/12 | 1.02 (0.85-7.29) | 0/1 |
| ranger_cv4 | cv | design | 74 | 209 | 0.614 | 0.445 | 0.0337 | 129 (0) | 30/39 | 7.6 | 7.643 | 0.0 | 0.0 | 0.0 | 0/12 | 0.93 (0.02-5.34) | 5/12 |
| saratoga_cv3 | cv | commissioned | 108 | 5.58e+04 | 5.57e+04 | 4.05 | 4.05 | 7 (0) | 108/0 | 7173.3 | 0 | 7173.3 | 0.0 | 66.4 | 5/6 | 6.67 (0.97-42.29) | 0/95 |
| saratoga_cv3 | cv | design | 108 | 317 | 0.849 | 2.21 | 5.06e-05 | 22 (0) | 46/57 | 14.3 | 14.31 | 0.0 | 0.0 | 0.0 | 0/6 | 0.02 (0.00-0.89) | 100/0 |
| saratoga_cv60 | cv | commissioned | 82 | 2.56e+05 | 2.55e+05 | 8.02e+03 | 8.02e+03 | 3 (0) | 82/0 | 11603.3 | 0 | 11603.3 | 0.0 | 141.5 | 5/14 | 1.06 (0.79-9.33) | 0/3 |
| saratoga_cv60 | cv | design | 82 | 354 | 0.75 | 1.54 | 0.0268 | 68 (0) | 46/31 | 9.3 | 9.313 | 0.0 | 0.0 | 0.0 | 0/14 | 1.10 (0.02-52.14) | 10/25 |
| wasp_cv7 | cv | commissioned | 62 | 3.66e+05 | 3.65e+05 | 1.41e+03 | 1.41e+03 | 0 (0) | 62/0 | 10507.0 | 0 | 10507.0 | 0.0 | 169.5 | 3/10 | 1.02 (0.88-2.83) | 0/5 |
| wasp_cv7 | cv | design | 62 | 254 | 1.02 | 1.73 | 0.0105 | 50 (0) | 33/26 | 8.2 | 8.196 | 0.0 | 0.0 | 0.0 | 0/10 | 1.25 (0.15-42.82) | 8/17 |
| yorktown_cv5 | cv | commissioned | 71 | 1.39e+05 | 1.38e+05 | 862 | 862 | 5 (0) | 71/0 | 7408.3 | 0 | 7408.3 | 0.0 | 104.3 | 2/9 | 1.08 (0.77-3.45) | 0/2 |
| yorktown_cv5 | cv | design | 71 | 245 | 1.44 | 1.8 | 0.0177 | 45 (0) | 34/35 | 10.2 | 10.18 | 0.0 | 0.0 | 0.0 | 0/9 | 1.07 (0.23-52.95) | 5/12 |
| puncher_cve53 | cve | commissioned | 88 | 8.42e+04 | 8.41e+04 | 298 | 298 | 23 (0) | 88/0 | 7152.4 | 0 | 7152.4 | 0.0 | 81.3 | 5/13 | 1.02 (0.67-2.50) | 0/1 |
| puncher_cve53 | cve | design | 88 | 305 | 1.75 | 1.95 | 0.0321 | 141 (0) | 41/42 | 14.3 | 14.31 | 0.0 | 0.0 | 0.0 | 0/13 | 1.07 (0.24-11.15) | 11/15 |
| thetis_bay_cve90 | cve | commissioned | 74 | 6.93e+04 | 6.93e+04 | 270 | 270 | 24 (0) | 74/0 | 5455.2 | 0 | 5455.2 | 0.0 | 73.7 | 4/11 | 1.05 (0.81-2.02) | 0/1 |
| thetis_bay_cve90 | cve | design | 74 | 248 | 1.21 | 1.22 | 0.0213 | 76 (0) | 31/39 | 10.9 | 10.9 | 0.0 | 0.0 | 0.0 | 0/11 | 1.17 (0.24-18.23) | 9/15 |
| independence_cvl26 | cvl | commissioned | 46 | 8.85e+05 | 8.85e+05 | 1.89e+03 | 1.89e+03 | 2 (0) | 46/0 | 12092.3 | 0 | 12092.3 | 0.0 | 262.9 | 3/10 | 1.09 (0.89-3.02) | 0/1 |
| independence_cvl26 | cvl | design | 46 | 269 | 0.618 | 1.11 | 0.00604 | 34 (0) | 16/27 | 5.9 | 5.926 | 0.0 | 0.0 | 0.0 | 0/10 | 0.94 (0.31-66.72) | 6/11 |
| antietam_cvs36 | cvs | commissioned | 66 | 7.32e+04 | 7.3e+04 | 512 | 512 | 8 (0) | 66/0 | 4987.1 | 0 | 4987.1 | 0.0 | 75.6 | 3/10 | 1.01 (0.95-1.23) | 0/0 |
| antietam_cvs36 | cvs | design | 66 | 374 | 1.15 | 1.16 | 0.0248 | 65 (0) | 27/36 | 10.8 | 10.76 | 0.0 | 0.0 | 0.0 | 0/10 | 1.05 (0.33-8.48) | 5/14 |
| bainbridge_dd1 | dd | commissioned | 27 | 3.53e+03 | 3.53e+03 | 1.15 | 1.15 | 2 (0) | 27/0 | 449.9 | 0 | 449.9 | 0.0 | 16.7 | 1/3 | 0.88 (0.57-1.01) | 0/0 |
| bainbridge_dd1 | dd | design | 27 | 66.1 | 0.317 | 0.000367 | 2.07e-05 | 24 (0) | 18/8 | 1.3 | 1.264 | 0.0 | 0.0 | 0.0 | 0/3 | 0.88 (0.35-2.09) | 4/1 |
| cushing_dd376 | dd | commissioned | 41 | 4.25e+03 | 4.24e+03 | 1.1 | 1.1 | 1 (0) | 41/0 | 744.4 | 0 | 744.4 | 0.0 | 18.2 | 2/4 | 0.91 (0.78-1.28) | 0/0 |
| cushing_dd376 | dd | design | 41 | 184 | 0.0788 | 0.181 | 0.102 | 65 (0) | 6/33 | 2.6 | 2.583 | 0.0 | 0.0 | 0.0 | 0/4 | 0.91 (0.01-2.73) | 8/1 |
| davison_dd618 | dd | commissioned | 39 | 2.01e+04 | 2.01e+04 | 5.07 | 5.07 | 1 (0) | 35/0 | 1393.0 | 0 | 1393.0 | 0.0 | 35.7 | 2/5 | 1.02 (0.88-2.65) | 0/2 |
| davison_dd618 | dd | design | 39 | 158 | 0.387 | 0.396 | 0.0134 | 37 (0) | 19/14 | 3.1 | 3.095 | 0.0 | 0.0 | 0.0 | 0/5 | 0.83 (0.01-11.92) | 5/5 |
| fletcher_dde_dd445 | dd | commissioned | 35 | 3.42e+03 | 3.41e+03 | 15.4 | 15.4 | 2 (0) | 35/0 | 574.9 | 0 | 574.9 | 0.0 | 16.4 | 2/5 | 0.99 (0.78-1.10) | 0/0 |
| fletcher_dde_dd445 | dd | design | 35 | 77.9 | 0.35 | 0.0313 | 0.00628 | 22 (0) | 11/22 | 2.2 | 2.154 | 0.0 | 0.0 | 0.0 | 0/5 | 1.13 (0.01-6.64) | 7/10 |
| hunter_killer_dd692 | dd | commissioned | 60 | 5.16e+04 | 5.16e+04 | 716 | 716 | 3 (0) | 57/0 | 3634.7 | 0 | 3634.7 | 0.0 | 60.6 | 4/7 | 1.01 (0.00-4.25) | 2/5 |
| hunter_killer_dd692 | dd | design | 60 | 47.2 | 0.365 | 0.409 | 0.0429 | 80 (0) | 36/17 | 3.4 | 3.447 | 0.0 | 0.0 | 0.0 | 0/7 | 0.80 (0.00-4.75) | 13/4 |
| keppler_dd765 | dd | commissioned | 79 | 5.83e+03 | 5.82e+03 | 80.9 | 80.9 | 16 (0) | 78/0 | 1674.1 | 0 | 1674.1 | 0.0 | 21.2 | 4/7 | 1.03 (0.70-2.31) | 0/1 |
| keppler_dd765 | dd | design | 79 | 172 | 0.413 | 0.447 | 0.0466 | 85 (0) | 30/44 | 6.4 | 6.44 | 0.0 | 0.0 | 0.0 | 0/7 | 0.97 (0.00-24.21) | 20/24 |
| nields_dd616 | dd | commissioned | 39 | 2.44e+04 | 2.44e+04 | 4.59 | 4.59 | 1 (0) | 36/0 | 1579.1 | 0 | 1579.1 | 0.0 | 40.5 | 2/5 | 1.02 (0.86-2.92) | 0/3 |
| nields_dd616 | dd | design | 39 | 158 | 0.347 | 0.357 | 0.0491 | 37 (0) | 19/15 | 3.3 | 3.318 | 0.0 | 0.0 | 0.0 | 0/5 | 0.80 (0.01-11.79) | 6/6 |
| sigsbee_dd502 | dd | commissioned | 41 | 3.67e+04 | 3.67e+04 | 6.76 | 6.76 | 1 (0) | 40/0 | 2152.0 | 0 | 2152.0 | 0.0 | 52.5 | 2/6 | 1.02 (0.80-3.59) | 0/3 |
| sigsbee_dd502 | dd | design | 41 | 142 | 0.416 | 0.42 | 0.0543 | 33 (0) | 14/24 | 3.2 | 3.188 | 0.0 | 0.0 | 0.0 | 0/6 | 0.80 (0.01-7.40) | 6/6 |
| cannon_de701 | de | commissioned | 32 | 1.73e+04 | 1.73e+04 | 126 | 126 | 1 (0) | 32/0 | 1175.8 | 0 | 1175.8 | 0.0 | 36.7 | 1/4 | 1.04 (0.85-3.71) | 0/4 |
| cannon_de701 | de | design | 32 | 111 | 0.579 | 0.579 | 0.00726 | 6 (0) | 15/16 | 3.4 | 3.407 | 0.0 | 0.0 | 0.0 | 0/4 | 0.89 (0.01-2.94) | 6/3 |
| palmer_dms5 | dms | commissioned | 39 | 6.35e+03 | 6.35e+03 | 4.08 | 4.08 | 8 (0) | 39/0 | 866.8 | 0 | 866.8 | 0.0 | 22.2 | 2/4 | 0.92 (0.74-1.01) | 0/0 |
| palmer_dms5 | dms | design | 39 | 103 | 0.0677 | 0.126 | 0.0546 | 72 (0) | 7/30 | 2.2 | 2.182 | 0.0 | 0.0 | 0.0 | 0/4 | 0.84 (0.00-2.50) | 4/1 |
| liberty_cargo_ec2 | ec | commissioned | 54 | 6.98e+03 | 6.94e+03 | 58.3 | 58.3 | 3 (0) | 53/0 | 1240.1 | 0 | 1240.1 | 0.0 | 23.0 | 5/13 | 1.01 (0.77-3.23) | 0/4 |
| liberty_cargo_ec2 | ec | design | 54 | 1.66 | 0.407 | 0.83 | 0.00345 | 22 (0) | 32/16 | 3.5 | 3.518 | 0.0 | 0.0 | 0.0 | 0/13 | 0.75 (0.00-10.44) | 13/12 |
| fort_william_j311 | j | commissioned | 25 | 3.82e+04 | 3.82e+04 | 238 | 238 | 0 (0) | 25/0 | 1370.7 | 0 | 1370.7 | 0.0 | 54.8 | 2/4 | 1.03 (0.84-1.63) | 0/0 |
| fort_william_j311 | j | design | 25 | 151 | 0.31 | 0.31 | 0.00364 | 22 (0) | 12/11 | 2.2 | 2.162 | 0.0 | 0.0 | 0.0 | 0/4 | 0.72 (0.33-8.55) | 4/4 |
| winnipeg_j337 | j | commissioned | 31 | 4.95e+04 | 4.94e+04 | 1.44 | 1.44 | 1 (0) | 31/0 | 1936.2 | 0 | 1936.2 | 0.0 | 62.5 | 2/4 | 1.04 (0.90-1.42) | 0/0 |
| winnipeg_j337 | j | design | 31 | 152 | 0.276 | 0.137 | 6.43e-05 | 31 (0) | 15/14 | 2.6 | 2.575 | 0.0 | 0.0 | 0.0 | 0/4 | 1.04 (0.25-9.12) | 4/3 |
| cobalt_k124 | k | commissioned | 29 | 2.18e+04 | 2.18e+04 | 136 | 136 | 4 (0) | 29/0 | 1202.2 | 0 | 1202.2 | 0.0 | 41.5 | 3/5 | 1.04 (0.79-4.15) | 0/3 |
| cobalt_k124 | k | design | 29 | 151 | 0.205 | 0.208 | 0.0134 | 37 (0) | 15/11 | 2.2 | 2.221 | 0.0 | 0.0 | 0.0 | 0/5 | 0.69 (0.02-5.32) | 7/4 |
| fort_mandan_lsd21 | lsd | commissioned | 51 | 2.94e+05 | 2.94e+05 | 3.8 | 3.8 | 2 (0) | 51/0 | 7742.5 | 0 | 7742.5 | 0.0 | 151.8 | 5/9 | 1.06 (0.66-1.80) | 0/0 |
| fort_mandan_lsd21 | lsd | design | 51 | 101 | 1.26 | 1.37 | 0.00909 | 46 (0) | 26/20 | 6.6 | 6.551 | 0.0 | 0.0 | 0.0 | 0/9 | 0.90 (0.33-6.08) | 6/10 |
| middlesex_lst983 | lst | commissioned | 40 | 2.97e+04 | 2.97e+04 | 1.37 | 1.37 | 4 (0) | 40/0 | 1926.5 | 0 | 1926.5 | 0.0 | 48.2 | 4/10 | 1.05 (0.84-5.82) | 0/9 |
| middlesex_lst983 | lst | design | 40 | 130 | 0.545 | 0.566 | 3.36e-05 | 24 (0) | 17/19 | 3.9 | 3.922 | 0.0 | 0.0 | 0.0 | 0/10 | 0.59 (0.01-4.94) | 14/5 |
| esteem_mso438 | mso | commissioned | 39 | 1.47e+03 | 1.47e+03 | 1.62 | 1.62 | 0 (0) | 39/0 | 419.6 | 0 | 419.6 | 0.0 | 10.8 | 3/7 | 0.93 (0.68-1.01) | 0/0 |
| esteem_mso438 | mso | design | 39 | 164 | 0.415 | 0.00736 | 0.00539 | 60 (0) | 27/9 | 2.8 | 2.806 | 0.0 | 0.0 | 0.0 | 0/7 | 0.87 (0.01-5.65) | 6/3 |
| apl_24 | other | commissioned | 34 | 9.55e+05 | 9.55e+05 | 3.65 | 3.65 | 0 (0) | 34/0 | 9249.8 | 0 | 9249.8 | 0.0 | 272.1 | 6/10 | 1.62 (0.68-18.14) | 0/15 |
| apl_24 | other | design | 34 | 23.6 | 1.07e-06 | 1.24e-06 | 1.73e-08 | 30 (0) | 13/15 | 0.0 | 0.0008558 | 0.0 | 0.0 | 0.0 | 0/10 | 0.50 (0.00-2.38) | 12/2 |
| castle_class_corvette | other | commissioned | 19 | 1.42e+05 | 1.42e+05 | 1.29 | 1.29 | 0 (0) | 19/0 | 1996.0 | 0 | 1996.0 | 0.0 | 105.1 | 2/4 | 1.05 (0.85-4.49) | 0/2 |
| castle_class_corvette | other | design | 19 | 112 | 0.346 | 0.346 | 3.68e-05 | 20 (0) | 6/11 | 1.8 | 1.807 | 0.0 | 0.0 | 0.0 | 0/4 | 0.75 (0.00-2.05) | 3/1 |
| destroyer_baseline | other | commissioned | 9 | 8.16e+04 | 8.15e+04 | 0.845 | 0.845 | 0 (0) | 9/0 | 717.1 | 0 | 717.1 | 0.0 | 79.7 | 3/6 | 1.00 (0.78-1.03) | 0/0 |
| destroyer_baseline | other | design | 9 | 0.953 | 0.234 | 0.234 | 0.000253 | 7 (0) | 4/2 | 0.5 | 0.5403 | 0.0 | 0.0 | 0.0 | 0/6 | 0.57 (0.41-1.08) | 1/0 |
| lsm_354 | other | commissioned | 40 | 2.66e+03 | 2.66e+03 | 1.94 | 1.94 | 0 (0) | 39/0 | 564.2 | 0 | 564.2 | 0.0 | 14.1 | 4/8 | 1.00 (0.83-2.95) | 0/1 |
| lsm_354 | other | design | 40 | 89.7 | 0.222 | 0.435 | 0.000215 | 20 (0) | 12/23 | 2.2 | 2.22 | 0.0 | 0.0 | 0.0 | 0/8 | 0.61 (0.00-3.41) | 13/7 |
| pce_874 | other | commissioned | 20 | 6.86e+03 | 6.85e+03 | 1.22 | 1.22 | 1 (0) | 20/0 | 465.2 | 0 | 465.2 | 0.0 | 23.3 | 1/3 | 1.01 (0.65-1.22) | 0/0 |
| pce_874 | other | design | 20 | 100 | 0.0807 | 0.0806 | 1.85e-05 | 11 (0) | 7/12 | 1.3 | 1.263 | 0.0 | 0.0 | 0.0 | 0/3 | 1.13 (0.00-1.77) | 5/0 |
| pt_564 | other | commissioned | 13 | 1.19e+03 | 1.19e+03 | 1.56 | 1.56 | 0 (0) | 13/0 | 125.4 | 0 | 125.4 | 0.0 | 9.6 | 1/4 | 0.85 (0.57-1.01) | 0/0 |
| pt_564 | other | design | 13 | 28.3 | 0.0859 | 0.0859 | 1.97e-05 | 3 (0) | 7/5 | 0.6 | 0.574 | 0.0 | 0.0 | 0.0 | 0/4 | 1.16 (0.38-2.16) | 3/2 |
| river_class_frigate | other | commissioned | 37 | 8.2e+04 | 8.2e+04 | 904 | 904 | 0 (0) | 37/0 | 2975.7 | 0 | 2975.7 | 0.0 | 80.4 | 3/5 | 1.11 (0.79-8.10) | 0/2 |
| river_class_frigate | other | design | 37 | 152 | 0.329 | 0.0924 | 0.0081 | 48 (0) | 15/19 | 2.8 | 2.75 | 0.0 | 0.0 | 0.0 | 0/5 | 1.11 (0.01-6.73) | 8/10 |
| savannah_ns | other | commissioned | 73 | 9.18e+03 | 9.15e+03 | 82.5 | 82.5 | 6 (0) | 73/0 | 1962.8 | 0 | 1962.8 | 0.0 | 26.9 | 5/14 | 1.01 (0.94-7.50) | 0/5 |
| savannah_ns | other | design | 73 | 92.1 | 0.481 | 1.16 | 0.0117 | 30 (0) | 32/36 | 7.4 | 7.439 | 0.0 | 0.0 | 0.0 | 0/14 | 0.84 (0.01-12.05) | 19/17 |
| rolla_pc483 | pc | commissioned | 30 | 2.08e+03 | 2.08e+03 | 3.4 | 3.4 | 1 (0) | 30/0 | 383.7 | 0 | 383.7 | 0.0 | 12.8 | 2/4 | 0.83 (0.32-1.28) | 3/0 |
| rolla_pc483 | pc | design | 30 | 82.6 | 0.296 | 0.0153 | 0.0153 | 43 (0) | 12/16 | 1.7 | 1.709 | 0.0 | 0.0 | 0.0 | 0/4 | 0.74 (0.00-1.81) | 8/0 |
| eagle_pe60 | pe | commissioned | 41 | 2.1e+03 | 2.1e+03 | 2.44 | 2.44 | 2 (0) | 41/0 | 525.7 | 0 | 525.7 | 0.0 | 12.8 | 2/4 | 0.92 (0.43-1.28) | 1/0 |
| eagle_pe60 | pe | design | 41 | 94.4 | 0.354 | 0.372 | 0.0184 | 48 (0) | 18/21 | 3.5 | 3.495 | 0.0 | 0.0 | 0.0 | 0/4 | 0.63 (0.01-1.54) | 14/0 |
| erie_pg50 | pg | commissioned | 54 | 1.18e+04 | 1.17e+04 | 61.3 | 61.3 | 1 (0) | 54/0 | 1637.1 | 0 | 1637.1 | 0.0 | 30.3 | 3/7 | 0.99 (0.79-1.16) | 0/0 |
| erie_pg50 | pg | design | 54 | 202 | 0.972 | 0.971 | 0.0106 | 91 (0) | 24/27 | 7.4 | 7.439 | 0.0 | 0.0 | 0.0 | 0/7 | 0.90 (0.41-3.30) | 5/7 |
| gordon_gunter_r338 | r | commissioned | 35 | 1.14e+05 | 1.14e+05 | 1.23 | 1.23 | 0 (0) | 35/0 | 3320.4 | 0 | 3320.4 | 0.0 | 94.9 | 4/8 | 1.01 (0.81-9.36) | 0/4 |
| gordon_gunter_r338 | r | design | 35 | 131 | 0.37 | 1.18 | 2.68e-05 | 46 (0) | 20/11 | 2.5 | 2.538 | 0.0 | 0.0 | 0.0 | 0/8 | 0.75 (0.01-3.81) | 8/5 |
