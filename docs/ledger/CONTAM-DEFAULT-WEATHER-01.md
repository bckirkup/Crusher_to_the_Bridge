# CONTAM-DEFAULT-WEATHER-01
**Date:** 2026-11-16
**Commit:** 956ffc31
**Pathogens:** all
**Status:** measured
**Measured at:** 956ffc31

## Scope

Owner ruling (Benjamin, 2026-11-16): "I think the default weather should be a
reasonable constant; if modelers need to change it, they can, but it should be
internally consistent."

After-witnesses measured on the tree of `956ffc31`; before-witnesses on
`origin/main` `605f9841`. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS, no campaign, no cache.

Before this entry the exported steady weather had `Ws = 0`, no envelope leak
set the ContamX wind flag, and the 23 weather-deck `open_deck` records of
`CONTAM-AMBIENT-WEATHER-CRUISE-01` carried an imposed constant `wPset` instead
of the hull's Cp profile (that ledger, "Residuals and open items" item 6). The
Cp profiles and wall azimuths on every other path did nothing.

## The constant

`tools/contam_hobbyist.py`:

- `DEFAULT_RELATIVE_WIND_SPEED_M_S = 1.0`
- `DEFAULT_RELATIVE_WIND_DIRECTION_DEG = 0.0` (from ahead: a wall with azimuth 0
  is windward)

`ASSUMED-RELATIVE-WIND`, Grade C, declared assumption, no source read; Origin:
none. 1 m/s is the committed point of the declared 0-10 m/s axis of
`CONTAM-AMBIENT-WEATHER-CRUISE-01`, the speed at which the weather-deck native
exchange rates were derived, so the fleet default and those 23 records are one
constant and not two. It is not a measured wind, and a ship under way sees more;
it was not chosen against any witness below. With the `ship_hull` profile
(Cp 0.7 at 0 deg, -0.25 at 180 deg) and modifier 0.8 it is +0.34 / -0.12 Pa.

Override per hull in `contam/hobbyist_overrides.json`:
`relative_wind_speed_m_s` (finite, >= 0) and `relative_wind_direction_deg`
([0, 360)); `resolve_relative_wind` rejects anything else.

## What the exporter does now

One wind per hull, in three places that cannot disagree:

1. The steady weather line carries `Ws` / `Wd` from `resolve_relative_wind`.
2. Every path that carries the hull's Cp profile sets the ContamX wind flag:
   all envelope leaks and all ambient-opening legs. ContamX applies
   `0.8 * Cp(wazm - Wd) * rho * Ws^2 / 2`.
3. A record that declares `wind_speed_m_s` (the 23 `open_deck` records) is
   cross-ventilated: leg 1 at `wazm = Wd`, leg 2 at `Wd + 180`, on the same
   profile and modifier. No committed path carries a `wPset` any more.

The speed lives in the weather line only. An override changes that line (and,
for direction, the cross-ventilated leg azimuths) and no per-path number:
`test_override_sets_the_header_and_nothing_per_path`. A record's own
`wind_speed_m_s` is not a second ContamX wind
(`test_record_speed_is_not_a_second_contamx_wind`); it remains the native
lane's exchange axis, which this entry does not touch.
`test_committed_bundle_weather_is_internally_consistent` holds all 77 bundles
to: header = resolved wind, every profile path flagged at modifier 0.8, no
`wPset`, no declared record speed other than the hull's.

Speed 0 is the labelled pre-change baseline: no profile path is flagged, and a
declared-wind record falls back to the imposed `wPset` at its own speed. With
`relative_wind_speed_m_s: 0` the exporter reproduces all 77 pre-change bundles
byte-for-byte. The skeleton export (no wind section) is unchanged.

## What moved

- 77 `data/platforms/*/contam/platform.prj` regenerated
  (`scripts/generate_platform_contam_prj.py --ahs-terminal-mode commissioned`).
  The base tree reproduced all 77 byte-for-byte first. Every one moves: the
  weather line, the flag column of every envelope leak and louvre leg, and on
  the six cruise hulls the 46 deck legs (`wPset` -> profile + azimuth).
- All 77 `path_map.json` are byte-identical. Path numbering, kinds and flows
  declared are untouched.
- 82 platform directories exist; five (`expedition_cruise_300`,
  `fletcher_class_destroyer`, `legend_class_nsc`, `messy_cruise_500`,
  `san_antonio_class_lpd`) have never had a committed bundle and get none here.
- Design pins: `campaigns/contam/phase1_hvac_tracer_01` and
  `phase2_cruise_contrasts_01` pin path-map counts, not PRJ bytes. Both `_02`
  designs rebuild with zero diff, so no further successor exists; `_01`/`_v1`
  are byte-untouched. No cache produced.
- No `flow_rate_m3h`, `envelope_leak.area_m2` or native-lane change.

## Witnesses

### Equivalence of the deck legs

Profile legs against the former imposed `wPset`, envelope flags held clear,
commissioned export: largest per-path flow difference 4.5e-5 m3/h
(`expedition_cruise_450`, largest flow 76 221 m3/h) and 2.9e-3 m3/h
(`greg_mortimer`, 40 703 m3/h). The deck exchange of
`CONTAM-AMBIENT-WEATHER-CRUISE-01` is preserved at the default.

### Fleet pressure balance, 77 hulls x 3 lanes

`tools/diag/contam_pressure_balance_diagnostic.py --lane design --lane
commissioned --lane authored`: 231 rows, 3 unsolved before and after (all
`olympia_c6`, the pre-existing 300 s timeout). No hull lost convergence.

**design** (76 solved hulls)

| metric | fleet sum before | fleet sum after | largest per-hull move | hull |
|---|---|---|---|---|
| max abs dP Pa | 44937.7 | 44939.3 | +0.5254 | `expedition_cruise_450` |
| envelope inward m3/h | 1140.21 | 1170.19 | +5.839 | `mega_cruise_5000` |
| envelope net inward m3/h | 447.089 | 463.002 | +7.382 | `mega_cruise_5000` |
| ambient-opening net inward m3/h | 85513.8 | 85497.9 | -7.391 | `mega_cruise_5000` |
| abs balance residual m3/h | 0.0515264 | 0.0365736 | -0.01412 | `diamond_princess` |
| field k total 1/h | 33810.2 | 33809.4 | -1.448 | `diamond_princess` |
| median field/native k | 69.5369 | 69.5354 | -0.002347 | `cushing_dd376` |
| zones below half native | 841 | 841 | +0 | `aeolus_arc3` |
| zones above double native | 748 | 748 | +0 | `aeolus_arc3` |
| field-dead zones | 27 | 25 | -1 | `apl_24` |

**commissioned** (76 solved hulls)

| metric | fleet sum before | fleet sum after | largest per-hull move | hull |
|---|---|---|---|---|
| max abs dP Pa | 1.13479e+07 | 1.1348e+07 | +0.5625 | `enterprise_galaxy_tng` |
| envelope inward m3/h | 385004 | 385015 | +4.362 | `mega_cruise_5000` |
| envelope net inward m3/h | 384845 | 384855 | +4.675 | `mega_cruise_5000` |
| ambient-opening net inward m3/h | 195378 | 195369 | -4.706 | `mega_cruise_5000` |
| abs balance residual m3/h | 0.0546346 | 0.0197907 | -0.03052 | `mega_cruise_5000` |
| field k total 1/h | 29743.5 | 29742.2 | -1.247 | `diamond_princess` |
| median field/native k | 88.301 | 88.2996 | -0.001169 | `diamond_princess` |
| zones below half native | 19 | 19 | +0 | `aeolus_arc3` |
| zones above double native | 468 | 468 | +0 | `aeolus_arc3` |
| field-dead zones | 25 | 25 | +0 | `aeolus_arc3` |

**authored** (76 solved hulls)

| metric | fleet sum before | fleet sum after | largest per-hull move | hull |
|---|---|---|---|---|
| max abs dP Pa | 1.13479e+07 | 1.1348e+07 | +0.5625 | `enterprise_galaxy_tng` |
| envelope inward m3/h | 385004 | 385015 | +4.362 | `mega_cruise_5000` |
| envelope net inward m3/h | 384845 | 384855 | +4.675 | `mega_cruise_5000` |
| ambient-opening net inward m3/h | 195378 | 195369 | -4.706 | `mega_cruise_5000` |
| abs balance residual m3/h | 0.0546346 | 0.0197907 | -0.03052 | `mega_cruise_5000` |
| field k total 1/h | 29743.5 | 29742.2 | -1.247 | `diamond_princess` |
| median field/native k | 88.301 | 88.2996 | -0.001169 | `diamond_princess` |
| zones below half native | 19 | 19 | +0 | `aeolus_arc3` |
| zones above double native | 468 | 468 | +0 | `aeolus_arc3` |
| field-dead zones | 25 | 25 | +0 | `aeolus_arc3` |

### Cruise and fiction hulls (before -> after)

| hull | lane | max dP Pa | envelope inward m3/h | envelope outward m3/h | balance residual m3/h | zones below half native | median field/native k |
|---|---|---|---|---|---|---|---|
| `classic_cruise_1900` | design | 126.46 -> 126.31 | 73.82 -> 74.34 | 25.81 -> 25.34 | 0.0011 -> 0.0063 | 2 -> 2 | 0.9968 -> 0.9968 |
| `classic_cruise_1900` | commissioned | 102.19 -> 102.05 | 116.47 -> 117.33 | 16.84 -> 16.63 | -0.0064 -> -0.00059 | 0 -> 0 | 1.0095 -> 1.0093 |
| `diamond_princess` | design | 13.055 -> 13.009 | 30.14 -> 34.33 | 10.10 -> 8.91 | -0.014 -> 0.00034 | 4 -> 4 | 1.0119 -> 1.0116 |
| `diamond_princess` | commissioned | 12.679 -> 12.914 | 117.53 -> 119.96 | 0.83 -> 0.34 | -0.008 -> -0.0089 | 0 -> 0 | 1.0022 -> 1.0010 |
| `expedition_cruise_450` | design | 6.7314 -> 7.2568 | 22.36 -> 23.10 | 0.09 -> 0.00 | -0.0029 -> -0.0028 | 3 -> 3 | 0.9890 -> 0.9891 |
| `expedition_cruise_450` | commissioned | 80.802 -> 81.343 | 71.28 -> 71.84 | 0.09 -> 0.00 | -0.0042 -> -0.002 | 0 -> 0 | 1.0011 -> 1.0011 |
| `greg_mortimer` | design | 934.35 -> 934.37 | 1.59 -> 2.23 | 69.93 -> 71.17 | 0.0047 -> -0.0028 | 4 -> 4 | 0.8782 -> 0.8782 |
| `greg_mortimer` | commissioned | 44878 -> 44878 | 655.90 -> 655.64 | 1.26 -> 2.60 | 0.00061 -> 8.3e-05 | 0 -> 0 | 1.0022 -> 1.0022 |
| `mega_cruise_5000` | design | 14.343 -> 14.45 | 52.93 -> 58.77 | 4.68 -> 3.14 | -0.026 -> -0.017 | 5 -> 5 | 0.9951 -> 0.9951 |
| `mega_cruise_5000` | commissioned | 289.38 -> 289.66 | 146.76 -> 151.13 | 3.58 -> 3.27 | -0.034 -> -0.0033 | 0 -> 0 | 1.0002 -> 1.0002 |
| `spirit_cruise_3000` | design | 756.94 -> 756.88 | 38.29 -> 40.10 | 126.33 -> 125.83 | 0.002 -> 0.0059 | 2 -> 2 | 0.9970 -> 0.9970 |
| `spirit_cruise_3000` | commissioned | 550.27 -> 550.2 | 104.32 -> 105.87 | 136.60 -> 136.13 | -0.00026 -> 0.0032 | 0 -> 0 | 1.0134 -> 1.0133 |
| `enterprise_constitution_tos` | design | 13.707 -> 13.708 | 43.85 -> 43.69 | 0.00 -> 0.00 | 0.00012 -> 0.00014 | 0 -> 0 | 0.9295 -> 0.9295 |
| `enterprise_constitution_tos` | commissioned | 106.07 -> 106.02 | 168.91 -> 168.80 | 0.00 -> 0.00 | 0.0001 -> 0.00031 | 0 -> 0 | 1.0000 -> 1.0000 |
| `enterprise_galaxy_tng` | design | 32461 -> 32461 | 486.46 -> 486.24 | 65.41 -> 65.41 | -7.5e-05 -> -0.0005 | 1 -> 1 | 0.9952 -> 0.9952 |
| `enterprise_galaxy_tng` | commissioned | 1.6503e+05 -> 1.6503e+05 | 1947.78 -> 1947.72 | 0.00 -> 0.00 | -0.00014 -> -0.0002 | 0 -> 0 | 1.0000 -> 1.0000 |

The authored lane equals the commissioned lane on every row.

### Flow compare and paired cells, eight hulls

`tools/diag/ambient_makeup_witness.py` (pressure, `contam_flow_compare
--run-contamx`, `contam_paired_diagnostic`, exact check). Native-lane cells are
identical before and after on every hull.

| hull | paired cells | largest move in whole-hull material time (cell: before -> after h) | opening inward m3/h | opening outward sink m3/h | boundary-sink paths |
|---|---|---|---|---|---|
| `classic_cruise_1900` | 12 | MainGalley/commissioned/pulse_t0: 0.10710 -> 0.10709 | 122412.9 -> 122410.7 | 101803.4 -> 101802.3 | 15 -> 14 |
| `diamond_princess` | 12 | International/commissioned/split_t0_t1: 0.22547 -> 0.22543 | 621776.2 -> 621862.8 | 578019.5 -> 578109.1 | 18 -> 10 |
| `enterprise_constitution_tos` | 12 | Mess_Hall/commissioned/split_t0_t1: 0.22863 -> 0.22863 | 9242.7 -> 9242.8 | 0.0 -> 0.0 | 0 -> 0 |
| `enterprise_galaxy_tng` | 12 | Mess_Hall/commissioned/split_t0_t1: 0.21590 -> 0.21591 | 12610.0 -> 12610.1 | 0.0 -> 0.0 | 0 -> 0 |
| `expedition_cruise_450` | 24 | MainDining/commissioned/pulse_t0: 0.20571 -> 0.20548 | 85849.5 -> 85840.3 | 73376.0 -> 73367.5 | 2 -> 1 |
| `greg_mortimer` | 12 | DiningRoom/commissioned/pulse_t0: 0.13293 -> 0.13293 | 178385.3 -> 178376.6 | 167643.6 -> 167633.3 | 22 -> 23 |
| `mega_cruise_5000` | 12 | Windjammer/commissioned/split_t0_t1: 0.36179 -> 0.36190 | 1234098.2 -> 1234388.2 | 1176903.1 -> 1177197.9 | 17 -> 10 |
| `spirit_cruise_3000` | 12 | MainDining_L/commissioned/split_t0_t1: 0.18936 -> 0.18936 | 315158.4 -> 315157.0 | 286409.4 -> 286410.0 | 37 -> 33 |

Boundary-sink path counts move because envelope leaks that leaked outward by
less than 1 m3/h change sign under +0.34 / -0.12 Pa; the sink total moves by
less than 0.03 %.

### Commissioned check

`tools/contam_commissioned_check.py` on the six cruise hulls, the two fiction
hulls and `destroyer_baseline`: PASS, all 1636 terminal rows inside 5 % of declared.

### Speed axis

Commissioned export with the per-hull override; every solve converged.

| hull | U m/s | envelope inward m3/h | envelope outward m3/h | deck-opening outward m3/h |
|---|---|---|---|---|
| `classic_cruise_1900` | 0 / 1 / 5 / 10 | 116.47 / 117.33 / 129.54 / 171.65 | 16.84 / 16.63 / 12.67 / 11.40 | 101 803 / 101 802 / 524 653 / 1 053 066 |
| `spirit_cruise_3000` | 0 / 1 / 5 / 10 | 104.32 / 105.87 / 123.35 / 164.30 | 136.60 / 136.13 / 133.12 / 115.01 | 286 409 / 286 410 / 1 449 489 / 2 903 302 |
| `greg_mortimer` | 0 / 1 / 5 / 10 | 655.90 / 655.64 / 654.83 / 658.87 | 1.26 / 2.60 / 25.34 / 52.25 | 167 644 / 167 633 / 851 831 / 1 706 787 |
| `destroyer_baseline` | 0 / 1 / 5 / 10 | 717.15 at every speed | 0 at every speed | no openings |

The U = 0 column is the pre-change export, in which the deck legs keep their
imposed 1 m/s pressure. Deck exchange scales close to linearly with speed, as an orifice
pair under a `U^2` pressure must.

## Findings

1. Measured: the default is internally consistent and solves on every hull that
   solved before. Pressure residuals do not worsen: the largest move in any
   hull's maximum |dP| is 0.56 Pa, and summed |balance residual| falls in all
   three lanes.
2. Measured, against expectation: the leak-limited stage-3 zones do not
   improve. Zones below half the native removal rate are unchanged on every
   hull and lane (design: 841 -> 841 fleet; classic / spirit / greg 2 / 2 / 4
   before and after). 1 m/s is +0.34 / -0.12 Pa against fan-driven pressures of
   10 Pa to 100 kPa; the largest envelope-inflow move is +5.8 m3/h
   (`mega_cruise_5000`, design).
3. Measured: even 10 m/s moves envelope inflow by tens of m3/h on the three
   hulls swept, and nothing on `destroyer_baseline`. Inferred: on these hulls
   leak-limited zones are limited by leak area and the declared exhaust, not by
   the weather, so no admissible wind closes them.

## Residuals and open items

1. The two Enterprise hulls take the same 1 m/s as every other hull. A starship
   has no relative wind; the effect is at most 0.23 m3/h of envelope inflow.
   Setting `relative_wind_speed_m_s: 0` in their overrides is the available
   switch. Owner decision; not taken here.
2. Overriding a hull's wind moves the ContamX deck exchange but not the native
   `open_deck` rate, which is derived at the record's `wind_speed_m_s`. A
   modeler who overrides the hull must move those records too, or the two lanes
   describe different weather.
3. The calm override is the pre-change export and not a physically calm hull:
   declared-wind deck legs keep an imposed pressure at the record's speed.
4. Direction is one constant (from ahead). Wall azimuths come from
   `wall_azimuth_deg` overrides or the exporter's geometric default; they were
   never exercised before this entry and are not validated.
5. `olympia_c6` still times out at 300 s in every lane, before and after.

## Reproduce

```bash
python3 scripts/generate_platform_contam_prj.py --ahs-terminal-mode commissioned \
  $(ls data/platforms/*/contam/platform.prj | cut -d/ -f3 | sed 's/^/--platform /')
python3 -m tools.diag.contam_pressure_balance_diagnostic \
  --lane design --lane commissioned --lane authored --out <out.json> --markdown <out.md>
python3 -m tools.diag.ambient_makeup_witness --label <before|after>
python3 -m tools.diag.ambient_makeup_witness --compare <before> <after>
python3 tools/contam_commissioned_check.py --platform <hull> ...
python3 -m pytest tests/test_contam_default_weather.py tests/test_contam_ambient_opening.py
```
