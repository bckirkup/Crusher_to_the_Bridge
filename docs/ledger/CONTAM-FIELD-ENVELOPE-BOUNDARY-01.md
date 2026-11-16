# CONTAM-FIELD-ENVELOPE-BOUNDARY-01
**Date:** 2026-11-15
**Commit:** dbb12dba
**Pathogens:** all
**Status:** open
**Measured at:** dbb12dba

## Scope

Stage 5 of
[`../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../proposals/contam_field_adjudication_audit_and_fix_plan.md)
(verdict (e)): lane semantics on boundary paths only. Base `origin/main`
`5f323c05`; measurements use local ContamX `third_party/contamx/contamx3` at
the code commit `dbb12dba`. Evidence base:
[`CONTAM-FIELD-ADJUDICATION-01`](CONTAM-FIELD-ADJUDICATION-01.md).

## Owner decision

Benjamin, 2026-11-15 19:07 EST, verbatim:

> yes, outward leakage is a contaminant sink

This resolves the owner-decision dependency of proposal §5 stage 5.

## Change

- `engines/contamx_transport.py`: an `envelope_leak` (authored `zone -> ambient`)
  whose solved `Flow0` is positive becomes a contaminant sink on its zone at the
  solved magnitude. Negative `Flow0` (ambient -> zone) still adds no path. One
  shared predicate, `is_outward_envelope_leak`.
- `tools/contam_flow_compare.py`: the same predicate gives fate `boundary_sink`;
  the report adds `n_boundary_sink_paths`, `boundary_sink_out_m3h`,
  `boundary_sink_links`. Sink flow counts toward the zone's outgoing degree only.
- Mode switch `hvac.contamx.envelope_leak_mode` / `--envelope-leak-mode`:
  `boundary_sink` (default) or `pressure_only` (labelled pre-change baseline,
  every envelope leak skipped).
- `tools/diag/contam_paired_diagnostic.py`: `--envelope-leak-mode`, and an
  opt-in `design` lane (fresh `ahs_terminal_mode="design"` export) so the
  verdict-(e) destroyer flows can be reproduced now that the committed bundles
  are commissioned (#1245).
- `tools/diag/contam_envelope_leak_enumeration.py`: fleet enumeration below.

Not changed: `path_map.json` schema and every committed `path_map.json` /
`platform.prj` (every `envelope_leak` stays `crusher_transfer: false`; the lane
reads the solved direction), `air_flow_paths.json`, declared inter-zone airflow,
any `flow_rate_m3h`, epidemiology constants, frozen campaign directories, S3
prefixes, `_v1` caches, committed readouts, existing ledgers. No bundle was
re-synced, so `tools/contam_commissioned_check.py` was not required.

## Destroyer witnesses (measured)

`tools/diag/contam_paired_diagnostic.py --hull destroyer_baseline --lane design
--lane authored --source Engine_Room --source Berthing --source Bridge
--source Mess_Hall --source HD_MAIN_M --timing pulse_t0`, run once per
`--envelope-leak-mode`. Deterministic, no seeds. Whole-hull material time in h.

| Lane | Source | Before (`pressure_only`) | After (`boundary_sink`) | Relative change | Transport loss before | Transport loss after |
|---|---|---|---|---|---|---|
| design | `Engine_Room` | 0.4659457798 | 0.4656534820 | -6.273e-04 | 0.9534054218 | 0.9534346515 |
| design | `Berthing` | 0.4098995056 | 0.4096185713 | -6.854e-04 | 0.9590100493 | 0.9590381427 |
| design | `Bridge` | 0.6432333355 | 0.6432032529 | -4.677e-05 | 0.9356766637 | 0.9356796720 |
| design | `Mess_Hall` | 0.6699371413 | 0.6699369414 | -2.983e-07 | 0.9330062828 | 0.9330063028 |
| design | `HD_MAIN_M` | 0.2307136302 | 0.2307136302 | +0.000e+00 | 0.9769286370 | 0.9769286370 |
| authored | `Engine_Room` | 0.4227757529 | 0.4227757529 | +0.000e+00 | 0.9577224247 | 0.9577224247 |
| authored | `Berthing` | 0.4079542824 | 0.4079542824 | +0.000e+00 | 0.9592045718 | 0.9592045718 |
| authored | `Bridge` | 0.4165951917 | 0.4165951917 | +0.000e+00 | 0.9583404808 | 0.9583404808 |
| authored | `Mess_Hall` | 0.3252110941 | 0.3252110941 | +0.000e+00 | 0.9674788906 | 0.9674788906 |
| authored | `HD_MAIN_M` | 0.0516871431 | 0.0516871431 | +0.000e+00 | 0.9948312857 | 0.9948312857 |

- `design` lane reproduces verdict (e): 2 of 9 leaks outward, `Engine_Room`
  and `Berthing`, total 0.540 m³/h. The sink lowers whole-hull material time
  by at most 6.9e-4 relative, largest for the two leaking rooms.
- `authored` lane (committed commissioned bundle): no outward leak, so before
  and after are identical. `tools/contam_flow_compare.py --platform
  destroyer_baseline --run-contamx` reports `boundary_sink=0`, 0 m³/h.

## Fleet enumeration (measured)

`tools/diag/contam_envelope_leak_enumeration.py`, 77 bundled hulls x 2 lanes.
`olympia_c6` timed out in ContamX on both lanes (the solver-performance outlier
already recorded in
[`CONTAM-FIELD-AHS-COMMISSIONED-01`](CONTAM-FIELD-AHS-COMMISSIONED-01.md)), so
76 hulls are solved per lane.

**Committed bundles (`authored` lane, commissioned since #1245).** 1 of 76 hulls
has outward leaks: `south_dakota_bb49`, 2 paths (`Emergency_Cabin_Platform`,
`Landing_Platform`) at 9.9e-5 m³/h each, total 2.0e-4 m³/h, against 6047 m³/h
inward on the same hull. Every other solved hull has zero outward leaks. On the
committed lane the sink is a near-null.

**Fresh `design`-mode export.** 69 of 76 hulls have outward leaks, fleet
total 458.2 m³/h. Zero outward: `classic_cruise_1900`, `diamond_princess`,
`enterprise_constitution_tos`, `enterprise_galaxy_tng`, `expedition_cruise_450`,
`mega_cruise_5000`, `spirit_cruise_3000`.

| Hull | Outward / all leaks | Outward total m³/h | Largest leak m³/h | Inward total m³/h |
|---|---|---|---|---|
| `greg_mortimer` | 8/50 | 67.455 | 8.445 | 5011.0 |
| `west_virginia_bb48` | 89/198 | 21.937 | 0.584 | 21.9 |
| `puncher_cve53` | 42/88 | 14.310 | 0.390 | 14.3 |
| `saratoga_cv3` | 57/108 | 14.305 | 0.462 | 14.3 |
| `lexington_cv2` | 44/97 | 12.256 | 0.450 | 12.3 |
| `montana_acr13` | 54/146 | 12.135 | 0.317 | 12.1 |
| `idaho_bb42` | 56/114 | 12.010 | 0.427 | 12.0 |
| `thetis_bay_cve90` | 39/74 | 10.895 | 0.309 | 10.9 |
| `antietam_cvs36` | 36/66 | 10.757 | 0.300 | 10.8 |
| `yorktown_cv5` | 35/71 | 10.180 | 0.376 | 10.2 |
| `new_york_bb34` | 40/83 | 9.532 | 0.294 | 9.5 |
| `texas_bb35` | 41/92 | 9.399 | 0.310 | 9.4 |
| `pope_ap110` | 42/88 | 9.396 | 0.401 | 9.4 |
| `saratoga_cv60` | 31/82 | 9.313 | 0.449 | 9.3 |
| `missouri_bb63` | 47/103 | 8.848 | 0.369 | 8.8 |
| `new_jersey_bb62` | 47/103 | 8.848 | 0.369 | 8.8 |
| `wisconsin_bb64` | 47/103 | 8.848 | 0.369 | 8.8 |
| `wasp_cv7` | 26/62 | 8.196 | 0.369 | 8.2 |
| `midway_cv41` | 31/65 | 7.994 | 0.449 | 8.0 |
| `chicago_cg11` | 45/87 | 7.861 | 0.175 | 7.9 |
| `ranger_cv4` | 39/74 | 7.643 | 0.320 | 7.6 |
| `wright_cc2` | 40/68 | 7.450 | 0.189 | 7.5 |
| `erie_pg50` | 27/54 | 7.439 | 0.276 | 7.4 |
| `savannah_ns` | 36/73 | 7.439 | 0.366 | 7.4 |
| `miami_cl89` | 20/81 | 7.384 | 0.370 | 7.4 |
| `gosper_apa170` | 32/71 | 7.325 | 0.366 | 7.3 |
| `battler_acv6` | 22/55 | 6.595 | 0.487 | 6.6 |
| `fort_mandan_lsd21` | 20/51 | 6.551 | 0.328 | 6.6 |
| `keppler_dd765` | 44/79 | 6.440 | 0.365 | 6.4 |
| `luzon_arg2` | 28/69 | 6.217 | 0.357 | 6.2 |
| `assistance_ar17` | 28/57 | 6.158 | 0.332 | 6.2 |
| `independence_cvl26` | 27/46 | 5.926 | 0.220 | 5.9 |
| `lyon_ap71` | 26/59 | 5.221 | 0.251 | 5.2 |
| `mercury_aks20` | 37/61 | 5.215 | 0.317 | 5.2 |
| `squier_ap130` | 29/52 | 4.897 | 0.264 | 4.9 |
| `south_dakota_bb49` | 26/55 | 4.784 | 0.288 | 4.8 |
| `jupiter_ac3` | 26/50 | 4.707 | 0.213 | 4.7 |
| `aeolus_arc3` | 19/40 | 3.986 | 0.286 | 4.0 |
| `middlesex_lst983` | 19/40 | 3.922 | 0.207 | 3.9 |
| `liberty_cargo_ec2` | 16/54 | 3.518 | 0.253 | 3.5 |
| `eagle_pe60` | 21/41 | 3.495 | 0.166 | 3.5 |
| `hunter_killer_dd692` | 17/60 | 3.447 | 0.256 | 3.4 |
| `ruchamkin_apd89` | 16/32 | 3.407 | 0.213 | 3.4 |
| `cannon_de701` | 16/32 | 3.407 | 0.213 | 3.4 |
| `nields_dd616` | 15/39 | 3.318 | 0.338 | 3.3 |
| `sigsbee_dd502` | 24/41 | 3.188 | 0.315 | 3.2 |
| `davison_dd618` | 14/39 | 3.095 | 0.342 | 3.1 |
| `alexander_henry_cgs119` | 15/28 | 2.821 | 0.241 | 2.8 |
| `esteem_mso438` | 9/39 | 2.806 | 0.312 | 2.8 |
| `river_class_frigate` | 19/37 | 2.750 | 0.323 | 2.8 |
| `passumpsic_ao106` | 15/27 | 2.678 | 0.324 | 2.7 |
| `cushing_dd376` | 33/41 | 2.583 | 0.078 | 2.6 |
| `winnipeg_j337` | 14/31 | 2.575 | 0.329 | 2.6 |
| `bolster_ars38` | 13/24 | 2.575 | 0.198 | 2.6 |
| `gordon_gunter_r338` | 11/35 | 2.538 | 0.304 | 2.5 |
| `cobalt_k124` | 11/29 | 2.221 | 0.336 | 2.2 |
| `lsm_354` | 23/40 | 2.220 | 0.225 | 2.2 |
| `palmer_dms5` | 30/39 | 2.182 | 0.074 | 2.2 |
| `fort_william_j311` | 11/25 | 2.162 | 0.325 | 2.2 |
| `fletcher_dde_dd445` | 22/35 | 2.154 | 0.187 | 2.2 |
| `castle_class_corvette` | 11/19 | 1.807 | 0.164 | 1.8 |
| `rolla_pc483` | 16/30 | 1.709 | 0.175 | 1.7 |
| `bainbridge_dd1` | 8/27 | 1.264 | 0.158 | 1.3 |
| `pce_874` | 12/20 | 1.263 | 0.235 | 1.3 |
| `raven_am55` | 10/21 | 1.082 | 0.196 | 1.1 |
| `astoria_ca34` | 22/65 | 1.063 | 0.232 | 1.1 |
| `pt_564` | 5/13 | 0.574 | 0.115 | 0.6 |
| `destroyer_baseline` | 2/9 | 0.540 | 0.270 | 0.5 |
| `apl_24` | 15/34 | 0.001 | 0.000 | 0.0 |

On every design-mode hull except `greg_mortimer` the outward total equals the
inward total: the leaks circulate ambient air through the hull with no net
make-up. `greg_mortimer` (67.5 m³/h over 8 paths) is the only hull where the
magnitude is more than a few tenths of a m³/h per leak.

## Reading

- **Measured:** the semantic matters only where terminals are in `design` mode.
  Commissioned terminals pull essentially every envelope leak inward.
- **Inferred, not measured:** the frozen Phase 1/2 `_v1` field caches live on S3
  and were not read. Phase 2 hulls (the four cruise hulls) have zero outward
  leaks in both lanes here. Phase 1 includes `missouri_bb63`, which has 47
  outward leaks totalling 8.8 m³/h in a fresh design-mode solve; if its cached
  fields include a design-mode arm, re-running those cells through the default
  engine would differ slightly from the frozen readout. The frozen campaign
  directories are untouched; a re-run that must reproduce them should pass
  `envelope_leak_mode="pressure_only"`.
- No measurement recorded in the norovirus, covid or flu open ledgers is
  invalidated: none of them is scored on the ContamX field lane.

## Validation

Structural tests in `tests/test_contam_envelope_boundary.py`: default mode,
outward leak becomes a sink at unchanged magnitude, inward leak adds no path,
`pressure_only` conserves mass, inter-zone paths identical across modes,
retained mass strictly decreasing in outward flow, compare fates equal the
engine filter.
