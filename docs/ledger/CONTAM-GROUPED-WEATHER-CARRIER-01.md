# CONTAM-GROUPED-WEATHER-CARRIER-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** 767a575d

## Scope

Stage G4 of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
§3/§7: per-hull **opening-replaces-OA** authoring for carrier-class hulls with
grouped OA>0 weather zones, following merged G1
[`CONTAM-GROUPED-WEATHER-MIDWAY-01`](CONTAM-GROUPED-WEATHER-MIDWAY-01.md)
(PR #1299). Owner rulings of 2026-11-17, verbatim:

- grouped weather zones MAY receive `ambient_openings`;
- the opening REPLACES the HVAC group's OA leg for that zone (NO double-count);
- G4 fleet rollout authorized, staged by class, not as one fleet-wide PR.

Carrier roster from `CONTAM-AMBIENT-WEATHER-CARRIER-01` ∩ the plan's grouped
OA>0 weather table: `yorktown_cv5`, `wasp_cv7`, `saratoga_cv60`, `ranger_cv4`,
`independence_cvl26`, `antietam_cvs36`, `wright_cc2`, `thetis_bay_cve90`,
`puncher_cve53`, `battler_acv6`. No-op rows: `lexington_cv2` and
`saratoga_cv3` already carry stage-4 ungrouped `open_deck` openings;
`midway_cv41` is already G1-complete; `legend_class_nsc` is a National Security
Cutter (WMSL-750), not carrier-class; `san_antonio_class_lpd` is amphibious and
excluded. Pope/Aeolus/fiction hulls were not touched. Steady ContamX solves
used the local official NIST binary `third_party/contamx/contamx3`; no seeds,
no AWS. Measurements are on the data committed at `767a575d`, on top of
`origin/main` `4a3d7a55`; "before" is a clean `4a3d7a55` worktree.

## Change (exactly)

For every zone below, `spatial_layout.json` gained `exposure: "weather"`
(D7(b)) and `air_flow_paths.json` gained one D1(a) `ambient_openings` record:
`type: open_deck`, Grade C deck-face `area_m2 = 2 × sqrt(V / 3) × 3`,
`wind_speed_m_s: 1.0`, `schedule: always_open`. `hvac_zones[].rooms` was
re-declared so the opening replaces that group's OA leg for the zone; emptied
groups were dropped. `ach`, `oa_fraction`, `vent_mode` and `evidence` on
remaining groups are unchanged. `cross_zone_links` addressed by a changed
group id were split into remaining-group and removed-room records preserving
the per-room-pair reference flow `old_flow / (len(old_from) × len(old_to))`;
this edits `flow_rate_m3h` fields only by re-addressing unchanged per-pair
flows, and is called out for owner review exactly as in G1. Regenerated
`data/platforms/<hull>/contam/{platform.prj,path_map.json}` with
`scripts/generate_platform_contam_prj.py --platform <hull>
--ahs-terminal-mode commissioned`. No engine, exporter or schema code changed.

- `antietam_cvs36`: openings `Gallery_Deck` (former `VENT_Hangar`) 458.258 m², `Flight_Deck` (former `VENT_Weather`) 547.723 m², `Forecastle_Deck` (former `VENT_Weather`) 289.828 m². Groups: `VENT_Weather` dropped after removing `Flight_Deck`, `Forecastle_Deck` (was 2 rooms); `VENT_Hangar` rooms 4→3 (removed `Gallery_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 8 room pairs → `Flight_Deck`→`VENT_Hangar` 18.75 m³/h; `Flight_Deck`→`Gallery_Deck` 6.25 m³/h; `Forecastle_Deck`→`VENT_Hangar` 18.75 m³/h; `Forecastle_Deck`→`Gallery_Deck` 6.25 m³/h; `ladder_well_2` `VENT_Hangar`→`HVAC_Accom` 50 m³/h over 60 room pairs → `VENT_Hangar`→`HVAC_Accom` 37.5 m³/h; `Gallery_Deck`→`HVAC_Accom` 12.5 m³/h.  
- `battler_acv6`: openings `Walkways_Focsle` (former `VENT_Weather`) 158.841 m², `Flight_Deck` (former `VENT_Weather`) 308.352 m². Groups: `VENT_Weather` rooms 6→4 (removed `Walkways_Focsle`, `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 18 room pairs → `VENT_Weather`→`VENT_Hangar` 33.3333 m³/h; `Flight_Deck`→`VENT_Hangar` 8.33333 m³/h; `Walkways_Focsle`→`VENT_Hangar` 8.33333 m³/h.  
- `independence_cvl26`: openings `Gallery_Deck` (former `VENT_Hangar`) 181.819 m², `Flight_Deck` (former `VENT_Weather`) 345.626 m², `Poop_Deck` (former `VENT_Weather`) 92.222 m², `Forecastle_Deck` (former `VENT_Weather`) 118.182 m². Groups: `VENT_Weather` dropped after removing `Flight_Deck`, `Poop_Deck`, `Forecastle_Deck` (was 3 rooms); `VENT_Hangar` rooms 4→3 (removed `Gallery_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 12 room pairs → `Flight_Deck`→`VENT_Hangar` 12.5 m³/h; `Flight_Deck`→`Gallery_Deck` 4.16667 m³/h; `Forecastle_Deck`→`VENT_Hangar` 12.5 m³/h; `Forecastle_Deck`→`Gallery_Deck` 4.16667 m³/h; `Poop_Deck`→`VENT_Hangar` 12.5 m³/h; `Poop_Deck`→`Gallery_Deck` 4.16667 m³/h; `ladder_well_2` `VENT_Hangar`→`HVAC_Accom` 50 m³/h over 36 room pairs → `VENT_Hangar`→`HVAC_Accom` 37.5 m³/h; `Gallery_Deck`→`HVAC_Accom` 12.5 m³/h.  
- `puncher_cve53`: openings `Flight_Deck` (former `VENT_Weather`) 320.537 m². Groups: `VENT_Weather` rooms 7→6 (removed `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 21 room pairs → `VENT_Weather`→`VENT_Hangar` 42.8571 m³/h; `Flight_Deck`→`VENT_Hangar` 7.14286 m³/h.  
- `ranger_cv4`: openings `Flight_Deck` (former `VENT_Weather`) 445.253 m², `Poop_Deck` (former `VENT_Weather`) 132.029 m². Groups: `VENT_Weather` rooms 5→3 (removed `Flight_Deck`, `Poop_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 15 room pairs → `VENT_Weather`→`VENT_Hangar` 30 m³/h; `Flight_Deck`→`VENT_Hangar` 10 m³/h; `Poop_Deck`→`VENT_Hangar` 10 m³/h.  
- `saratoga_cv60`: openings `Flight_Deck` (former `VENT_Weather`) 759.737 m². Groups: `VENT_Weather` rooms 2→1 (removed `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 6 room pairs → `VENT_Weather`→`VENT_Hangar` 25 m³/h; `Flight_Deck`→`VENT_Hangar` 25 m³/h.  
- `thetis_bay_cve90`: openings `Flight_Deck` (former `VENT_Weather`) 325.726 m². Groups: `VENT_Weather` rooms 9→8 (removed `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 54 room pairs → `VENT_Weather`→`VENT_Hangar` 44.4444 m³/h; `Flight_Deck`→`VENT_Hangar` 5.55556 m³/h.  
- `wasp_cv7`: openings `Flight_Deck` (former `VENT_Weather`) 448.331 m². Groups: `VENT_Weather` rooms 2→1 (removed `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 4 room pairs → `VENT_Weather`→`VENT_Hangar` 25 m³/h; `Flight_Deck`→`VENT_Hangar` 25 m³/h.  
- `wright_cc2`: openings `Flight_Deck_Aft` (former `VENT_Weather`) 227.217 m², `Flight_Deck_Mid` (former `VENT_Weather`) 254.037 m², `Flight_Deck_Fwd` (former `VENT_Weather`) 262.368 m². Groups: `VENT_Weather` rooms 6→3 (removed `Flight_Deck_Aft`, `Flight_Deck_Mid`, `Flight_Deck_Fwd`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: none.  
- `yorktown_cv5`: openings `Flight_Deck` (former `VENT_Weather`) 439.987 m². Groups: `VENT_Weather` rooms 2→1 (removed `Flight_Deck`; `ach`/`oa_fraction`/`vent_mode` unchanged). Links: `ladder_well_1` `VENT_Weather`→`VENT_Hangar` 50 m³/h over 6 room pairs → `VENT_Weather`→`VENT_Hangar` 25 m³/h; `Flight_Deck`→`VENT_Hangar` 25 m³/h.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES` gained the ten
hulls' opening zones; `tests/test_contam_ambient_opening_boundary.py`
committed-leg census gained two `ambient_opening` legs per opening.

## D5 exchange

`exchange_m3h` is the commissioned-lane ContamX-solved **outward** flow of each
opening at `wind_speed_m_s` 1.0, measured after the edits
(`tools/contam_flow_compare.py --platform <hull> --run-contamx --inject
<Zone>`). The audit/net inward value was not used. For all ten hulls the
committed bundle was re-checked byte-identical with `exchange_m3h` 0.0 and
with the measured value written (sha256 of `platform.prj` and `path_map.json`),
so the export does not depend on this native-only field.

| hull | zone | former HVAC group | volume m³ | area_m2 | exchange_m3h | air changes /h |
|---|---|---|---:|---:|---:|---:|
| `antietam_cvs36` | `Gallery_Deck` | `VENT_Hangar` | 17,500.00 | 458.258 | 304,247.9 | 17.39 |
| `antietam_cvs36` | `Flight_Deck` | `VENT_Weather` | 25,000.00 | 547.723 | 366,301.8 | 14.65 |
| `antietam_cvs36` | `Forecastle_Deck` | `VENT_Weather` | 7,000.00 | 289.828 | 232,701.6 | 33.24 |
| `battler_acv6` | `Walkways_Focsle` | `VENT_Weather` | 2,102.53 | 158.841 | 127,594.3 | 60.69 |
| `battler_acv6` | `Flight_Deck` | `VENT_Weather` | 7,923.41 | 308.352 | 205,180.4 | 25.90 |
| `independence_cvl26` | `Gallery_Deck` | `VENT_Hangar` | 2,754.85 | 181.819 | 120,801.8 | 43.85 |
| `independence_cvl26` | `Flight_Deck` | `VENT_Weather` | 9,954.80 | 345.626 | 226,379.6 | 22.74 |
| `independence_cvl26` | `Poop_Deck` | `VENT_Weather` | 708.74 | 92.222 | 61,453.7 | 86.71 |
| `independence_cvl26` | `Forecastle_Deck` | `VENT_Weather` | 1,163.92 | 118.182 | 78,583.1 | 67.52 |
| `puncher_cve53` | `Flight_Deck` | `VENT_Weather` | 8,561.99 | 320.537 | 211,500.0 | 24.70 |
| `ranger_cv4` | `Flight_Deck` | `VENT_Weather` | 16,520.85 | 445.253 | 294,853.7 | 17.85 |
| `ranger_cv4` | `Poop_Deck` | `VENT_Weather` | 1,452.63 | 132.029 | 88,589.5 | 60.99 |
| `saratoga_cv60` | `Flight_Deck` | `VENT_Weather` | 48,100.00 | 759.737 | 505,376.8 | 10.51 |
| `thetis_bay_cve90` | `Flight_Deck` | `VENT_Weather` | 8,841.45 | 325.726 | 215,638.7 | 24.39 |
| `wasp_cv7` | `Flight_Deck` | `VENT_Weather` | 16,750.07 | 448.331 | 295,415.8 | 17.64 |
| `wright_cc2` | `Flight_Deck_Aft` | `VENT_Weather` | 4,302.31 | 227.217 | 150,003.2 | 34.87 |
| `wright_cc2` | `Flight_Deck_Mid` | `VENT_Weather` | 5,377.89 | 254.037 | 166,378.3 | 30.94 |
| `wright_cc2` | `Flight_Deck_Fwd` | `VENT_Weather` | 5,736.42 | 262.368 | 174,582.8 | 30.43 |
| `yorktown_cv5` | `Flight_Deck` | `VENT_Weather` | 16,132.41 | 439.987 | 291,768.3 | 18.09 |

Per-opening outward exchange spans 61,453.7–505,376.8 m³/h (10.51–86.71 air
changes/h on the zone volume).

## No double-count, both lanes

Before/after native `ContamTransportEngine.airflow_paths` comparison against
the clean `4a3d7a55` worktree:

| hull | native paths before→after | non-ambient removed | non-ambient added | non-ambient flow changed | ambient legs added |
|---|---:|---:|---:|---:|---:|
| `antietam_cvs36` | 1330→1329 | 4 | 0 | 0 | 3 |
| `battler_acv6` | 697→697 | 2 | 0 | 0 | 2 |
| `independence_cvl26` | 661→660 | 5 | 0 | 0 | 4 |
| `puncher_cve53` | 1275→1275 | 1 | 0 | 0 | 1 |
| `ranger_cv4` | 1267→1267 | 2 | 0 | 0 | 2 |
| `saratoga_cv60` | 1616→1616 | 1 | 0 | 0 | 1 |
| `thetis_bay_cve90` | 1267→1267 | 1 | 0 | 0 | 1 |
| `wasp_cv7` | 1175→1175 | 1 | 0 | 0 | 1 |
| `wright_cc2` | 334→334 | 3 | 0 | 0 | 3 |
| `yorktown_cv5` | 1574→1574 | 1 | 0 | 0 | 1 |

Non-ambient removals are exactly the HVAC supply/return legs for zones removed
from their groups; there are zero non-ambient additions and zero non-ambient
flow-rate changes. Ambient additions are one `ambopen_*_open_deck` sink per
authored opening. In the ContamX export each opening adds exactly two
`ambient_opening` path-map legs (the inward/outward orifice pair); the
committed-leg census in `tests/test_contam_ambient_opening_boundary.py` was
moved accordingly. Nothing else differs in either lane.

## Remaining group members not stranded

Groups with remaining rooms (`VENT_Weather` on `yorktown_cv5`, `wasp_cv7`,
`saratoga_cv60`, `ranger_cv4`, `wright_cc2`, `puncher_cve53`, `thetis_bay_cve90`,
`battler_acv6`; `VENT_Hangar` on `antietam_cvs36` and `independence_cvl26`)
keep `ach`/`oa_fraction`/`vent_mode`/`evidence` unchanged, and the native/export
HVAC rows for remaining rooms are unchanged (non-ambient flow changed = 0 above).
Groups dropped on `antietam_cvs36`/`independence_cvl26` (`VENT_Weather`) had no
remaining rooms. `tools/contam_commissioned_check.py` emitted all ten PRJs and
reported PASS (every commissioned terminal inside 5% of declared).

## Pressure diagnostic rows

`tools/diag/contam_pressure_balance_diagnostic.py --hull <ten hulls> --lane
authored --lane commissioned --lane design --timeout-s 1800`, before on the
clean `4a3d7a55` worktree and after on this change: 30 rows per side, 0
unsolved. Authored and commissioned lanes solve identically on these hulls, so
the table carries them as one lane; design is separate. "opening net inward" is
the boundary `ambient_opening_net_inward_m3h` (positive = net inflow to the
hull); before is 0 because no openings existed.

| hull | lane | before/after | envelope max \|ΔP\|, Pa | flowing interior max \|ΔP\|, Pa | make-up demand, m³/h | opening net inward, m³/h | balance residual, m³/h |
|---|---|---|---:|---:|---:|---:|---:|
| `antietam_cvs36` | authored / commissioned | before | 73,158.8 | 512.178 | 4,987.14 | 0 | -5.59519e-06 |
| `antietam_cvs36` | authored / commissioned | after | 106.053 | 101.127 | 4,987.7 | 4,836.34 | 0.00741835 |
| `antietam_cvs36` | design | before | 3.62583 | 0.0241345 | 0 | 0 | 0 |
| `antietam_cvs36` | design | after | 4.55763 | 1.83902 | 0 | -9.512 | -0.0145324 |
| `battler_acv6` | authored / commissioned | before | 28,584.6 | 78.3519 | 2,599.47 | 0 | -2.23971e-05 |
| `battler_acv6` | authored / commissioned | after | 142.796 | 141.767 | 2,599.47 | 2,497.6 | 0.000191562 |
| `battler_acv6` | design | before | 2.76799 | 0.00840351 | 0 | 0 | 4.37443e-08 |
| `battler_acv6` | design | after | 3.45868 | 2.71518 | 0 | 7.78629 | 0.00497291 |
| `independence_cvl26` | authored / commissioned | before | 885,348 | 1,891.49 | 12,092.3 | 0 | 6.71007e-05 |
| `independence_cvl26` | authored / commissioned | after | 21.7118 | 21.4357 | 12,093.8 | 12,051.9 | 0.00218143 |
| `independence_cvl26` | design | before | 3.21254 | 0.00591647 | 0 | 0 | -3.2764e-08 |
| `independence_cvl26` | design | after | 3.66086 | 0.00688416 | 0 | -4.33509 | -0.0096517 |
| `puncher_cve53` | authored / commissioned | before | 84,181.8 | 298.211 | 7,152.37 | 0 | -2.804e-05 |
| `puncher_cve53` | authored / commissioned | after | 689.731 | 687.201 | 7,152.37 | 6,733.5 | -0.00431335 |
| `puncher_cve53` | design | before | 2.4064 | 0.0366019 | 0 | 0 | -6.57186e-08 |
| `puncher_cve53` | design | after | 4.18419 | 0.062396 | 0 | -22.5798 | -0.00684771 |
| `ranger_cv4` | authored / commissioned | before | 152,094 | 583.669 | 8,093.56 | 0 | 3.63798e-12 |
| `ranger_cv4` | authored / commissioned | after | 132.696 | 129.377 | 8,093.56 | 7,880.22 | -0.00767601 |
| `ranger_cv4` | design | before | 1.76479 | 0.0250626 | 0 | 0 | 2.19283e-08 |
| `ranger_cv4` | design | after | 2.90118 | 0.0606767 | 0 | -17.9292 | 0.0059654 |
| `saratoga_cv60` | authored / commissioned | before | 255,740 | 8,016.61 | 11,603.3 | 0 | -1.12493e-05 |
| `saratoga_cv60` | authored / commissioned | after | 1,513.55 | 1,507.06 | 11,603.3 | 10,898.4 | 0.0175236 |
| `saratoga_cv60` | design | before | 2.71151 | 0.0303338 | 0 | 0 | 5.56151e-08 |
| `saratoga_cv60` | design | after | 4.51722 | 0.164524 | 0 | -29.4895 | 0.00847417 |
| `thetis_bay_cve90` | authored / commissioned | before | 69,313.2 | 269.794 | 5,455.21 | 0 | 4.48406e-05 |
| `thetis_bay_cve90` | authored / commissioned | after | 467.388 | 465.569 | 5,455.21 | 5,208.27 | 0.0141347 |
| `thetis_bay_cve90` | design | before | 2.27778 | 0.0252191 | 0 | 0 | -2.18948e-08 |
| `thetis_bay_cve90` | design | after | 3.31933 | 0.0279115 | 0 | -13.4307 | -0.00933713 |
| `wasp_cv7` | authored / commissioned | before | 365,629 | 1,410.88 | 10,507 | 0 | 0.000100987 |
| `wasp_cv7` | authored / commissioned | after | 12.7614 | 9.30361 | 10,507 | 10,463.5 | -0.0126262 |
| `wasp_cv7` | design | before | 1.92591 | 0.0100698 | 0 | 0 | 1.64366e-08 |
| `wasp_cv7` | design | after | 3.45439 | 0.0147638 | 0 | -14.6153 | -0.0180511 |
| `wright_cc2` | authored / commissioned | before | 453,783 | 5,147.78 | 11,838.4 | 0 | -2.23448e-05 |
| `wright_cc2` | authored / commissioned | after | 144.468 | 78.4444 | 11,838.4 | 11,665.3 | 0.00395446 |
| `wright_cc2` | design | before | 2.85041 | 0.0267935 | 0 | 0 | 4.36635e-08 |
| `wright_cc2` | design | after | 3.17276 | 0.0305152 | 0 | -5.15076 | 0.00695788 |
| `yorktown_cv5` | authored / commissioned | before | 138,518 | 862.027 | 7,408.29 | 0 | -2.24591e-05 |
| `yorktown_cv5` | authored / commissioned | after | 511.725 | 507.478 | 7,408.29 | 7,083.72 | -0.0050499 |
| `yorktown_cv5` | design | before | 2.68114 | 0.0178012 | 0 | 0 | -1.0418e-07 |
| `yorktown_cv5` | design | after | 4.26613 | 0.0357302 | 0 | -18.0075 | 0.00123259 |

## Paired diagnostic

The standalone `tools/diag/contam_paired_diagnostic.py` `--hull` choices do not
include carrier hulls, so no standalone paired cells were produced. The
pressure diagnostic was run fleet-wide without `--source`; G1's per-source
paired cells remain the only grouped-weather paired witness.

## Validation

- Byte-pin: all ten target `platform.prj`/`path_map.json` regenerated with
  `--ahs-terminal-mode commissioned`; non-target hull data byte-identical
  (`git diff --name-only` shows only the ten target hulls under
  `data/platforms/`; hash comparison reported `non_target_diffs 0`).
- Schema/data contracts: `check-jsonschema` for the ten edited
  `spatial_layout.json`/`air_flow_paths.json` PASS;
  `tools/sanity_checker.py --from-config` PASS (2 pre-existing warnings);
  `pytest tests/test_data_contracts.py tests/test_sanity_checker.py -q` 125
  passed; `pytest tests/test_contam_ambient_opening.py
  tests/test_contam_ambient_opening_boundary.py -q` 84 passed.
- `python3 scripts/sonar_guard.py tests/test_contam_ambient_opening.py
  tests/test_contam_ambient_opening_boundary.py` PASS.
- `python3 tools/contam_commissioned_check.py --platform <ten hulls>`: 10 PRJs
  emitted, PASS.
- ContamX witnesses: ten `tools/contam_flow_compare.py --run-contamx` runs
  wrote `telemetry_buffer/grouped_weather_carrier/flow_<hull>.json`; pressure
  diagnostic before/after 30 rows each, 0 unsolved.
- Fast tier: `python3 -m pytest tests/ -m 'not slow' -n auto` passed: 8765 passed, 9 skipped, 7886 warnings in 317.51s.
- `python3 -m pytest tests/test_ledger_entries.py` and `pre-commit run --files
  <changed files>` run before commit.

## Reproduction

```bash
for h in antietam_cvs36 battler_acv6 independence_cvl26 puncher_cve53 ranger_cv4          saratoga_cv60 thetis_bay_cve90 wasp_cv7 wright_cc2 yorktown_cv5; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform "$h"     --ahs-terminal-mode commissioned
  .venv/bin/python tools/contam_flow_compare.py --platform "$h" --run-contamx     --inject <Zone> --output "telemetry_buffer/grouped_weather_carrier/flow_$h.json"
done
.venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic   --hull <ten hulls> --lane design --lane commissioned --lane authored   --timeout-s 1800 --out telemetry_buffer/grouped_weather_carrier/after_pressure.json
.venv/bin/python tools/contam_commissioned_check.py --platform <ten hulls>
```

## Non-goals observed

No Pope/Aeolus work; no fiction hulls; no schema, engine or exporter change; no
`envelope_leak.area_m2` change; no `flow_rate_m3h` magnitude fitting (only the
re-addressed cross-zone link splits above); no stage-5 hatches or stage-6
balcony; no readout annotation; no AWS/S3; no frozen campaign dirs; no
epidemiological constants.

## Open

- G5+ classes remain staged by class; fiction hulls stay held for the owner
  question. `legend_class_nsc` was classified as a National Security Cutter, not
  carrier-class, and was not authored.
