# CONTAM-DEFAULT-WEATHER-ENTERPRISE-01
**Date:** 2026-11-17
**Commit:** 6716ba07
**Pathogens:** all
**Status:** measured
**Measured at:** 6716ba07

## Scope

Owner ruling (Benjamin, 2026-11-16), verbatim: "ok. we can do enterprises separately."

`CONTAM-DEFAULT-WEATHER-01` (PR #1266) gave every committed ContamX bundle the same fleet default relative wind — 1 m/s from ahead — through `DEFAULT_RELATIVE_WIND_SPEED_M_S` / `resolve_relative_wind`, overridable per hull by `relative_wind_speed_m_s` / `relative_wind_direction_deg` in `contam/hobbyist_overrides.json`. The two Enterprise fiction hulls were flagged in that entry as taking the same 1 m/s; the owner ruled they are handled separately.

This entry carves out only `enterprise_constitution_tos` and `enterprise_galaxy_tng` by setting `relative_wind_speed_m_s: 0` in their per-hull `contam/hobbyist_overrides.json`. No other hull, no other override key, no `flow_rate_m3h`, no `envelope_leak.area_m2`, no native-lane, campaign/cache, or committed-readout change. Fiction weather-zone exposure (stage 4, `CONTAM-AMBIENT-WEATHER-FICTION-01`, still proposed) will author their weather openings separately.

## Byte pin

Regenerated only the two committed bundles with the commissioned AHS terminal mode (`scripts/generate_platform_contam_prj.py --ahs-terminal-mode commissioned`). Each `platform.prj` is byte-identical to the pre-#1266 bundle at `605f9841` (`cmp` clean), and both `path_map.json` files are unchanged — no diff against `605f9841` or `origin/main`.

Against the #1266 `main` bundles, the only movement on these two hulls is the reverse of the fleet weather change: the steady weather line goes `Ws 1.000 -> 0.000` (`Wd` stays `0.000`), profile-carrying paths clear the ContamX wind flag, and the wind modifier/profile columns are unchanged. `tests/test_contam_default_weather.py` now expects the wind flag exactly when the resolved hull speed is nonzero, which is the calm-override case this entry adds; no other hull's expectation moved.

## Witnesses

Before/after witnesses used `tools/diag/ambient_makeup_witness.py` (`--label pre1266` in a `605f9841` worktree, `--label calm` on this branch) with the local `third_party/contamx/contamx3` binary, then `--compare pre1266 calm`. The `hulls` payload of the two `summary.json` files compares exactly equal (`==`) for both hulls, so the tables below show before -> after with no movement at full precision, not only at displayed precision.

### Pressure balance

| hull | lane | paths | max dP Pa | interior flowing max dP Pa | exhaust sinks m3/h | envelope net in m3/h | opening in m3/h | opening out m3/h | opening max dP Pa | balance residual m3/h | k field/native median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| enterprise_constitution_tos | design | 570 -> 570 | 13.71 -> 13.71 | 2.605 -> 2.605 | 5000 -> 5000 | 43.85 -> 43.85 | 4956 | 0 | 10.25 | 0.0001158 -> 0.0001158 | 0.9295 -> 0.9295 |
| enterprise_constitution_tos | commissioned | 570 -> 570 | 106.1 -> 106.1 | 63.59 -> 63.59 | 5000 -> 5000 | 168.9 -> 168.9 | 9243 | 0 | 35.66 | 0.0001015 -> 0.0001015 | 1 -> 1 |
| enterprise_constitution_tos | authored | 570 -> 570 | 106.1 -> 106.1 | 63.59 -> 63.59 | 5000 -> 5000 | 168.9 -> 168.9 | 9243 | 0 | 35.66 | 0.0001015 -> 0.0001015 | 1 -> 1 |
| enterprise_galaxy_tng | design | 1432 -> 1432 | 3.246e+04 -> 3.246e+04 | 79.88 -> 79.88 | 8000 -> 8000 | 421 -> 421 | 7579 | 0 | 9.379 | -7.464e-05 -> -7.464e-05 | 0.9952 -> 0.9952 |
| enterprise_galaxy_tng | commissioned | 1432 -> 1432 | 1.65e+05 -> 1.65e+05 | 219.5 -> 219.5 | 8000 -> 8000 | 1948 -> 1948 | 1.261e+04 | 0 | 25.96 | -0.000143 -> -0.000143 | 1 -> 1 |
| enterprise_galaxy_tng | authored | 1432 -> 1432 | 1.65e+05 -> 1.65e+05 | 219.5 -> 219.5 | 8000 -> 8000 | 1948 -> 1948 | 1.261e+04 | 0 | 25.96 | -0.000143 -> -0.000143 | 1 -> 1 |

### Pressure-diagnostic source-cell material time, h

`pulse_t0` and `split_t0_t1` are identical for every row; values are before -> after.

| hull | source | design | native | commissioned | authored |
|---|---|---|---|---|---|
| enterprise_constitution_tos | Galley | 0.0553 -> 0.0553 | 0.04599 -> 0.04599 | 0.06072 -> 0.06072 | 0.06072 -> 0.06072 |
| enterprise_constitution_tos | Mess_Hall | 0.1559 -> 0.1559 | 0.1087 -> 0.1087 | 0.2286 -> 0.2286 | 0.2286 -> 0.2286 |
| enterprise_galaxy_tng | Galley | 0.03737 -> 0.03737 | 0.03602 -> 0.03602 | 0.04606 -> 0.04606 | 0.04606 -> 0.04606 |
| enterprise_galaxy_tng | Mess_Hall | 0.08273 -> 0.08273 | 0.07985 -> 0.07985 | 0.2159 -> 0.2159 | 0.2159 -> 0.2159 |

### Flow compare

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | native ambient_exchange links / total m3/h |
|---|---|---|---|---|---|---|---|---|
| enterprise_constitution_tos | 570 -> 570 | 466 -> 466 | 289 -> 289 | 107 -> 107 | 2 -> 2 | 9242.68 -> 9242.68 | 0 -> 0 | 1 / 0 |
| enterprise_galaxy_tng | 1432 -> 1432 | 1216 -> 1216 | 886 -> 886 | 217 -> 217 | 2 -> 2 | 12610 -> 12610 | 0 -> 0 | 1 / 0 |

### Paired diagnostic matrix

| hull | source | lane | timing | whole-hull material time h | transport loss | closure error |
|---|---|---|---|---|---|---|
| enterprise_constitution_tos | Mess_Hall | native | pulse_t0 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Mess_Hall | native | split_t0_t1 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 1.11e-16 -> 1.11e-16 |
| enterprise_constitution_tos | Galley | native | pulse_t0 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Galley | native | split_t0_t1 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 3.331e-16 -> 3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | commissioned | pulse_t0 | 0.2286 -> 0.2286 | 0.9771 -> 0.9771 | -3.331e-16 -> -3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | commissioned | split_t0_t1 | 0.2286 -> 0.2286 | 0.9771 -> 0.9771 | -4.441e-16 -> -4.441e-16 |
| enterprise_constitution_tos | Galley | commissioned | pulse_t0 | 0.06072 -> 0.06072 | 0.9939 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Galley | commissioned | split_t0_t1 | 0.06072 -> 0.06072 | 0.9939 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Mess_Hall | authored | pulse_t0 | 0.2286 -> 0.2286 | 0.9771 -> 0.9771 | -3.331e-16 -> -3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | authored | split_t0_t1 | 0.2286 -> 0.2286 | 0.9771 -> 0.9771 | -4.441e-16 -> -4.441e-16 |
| enterprise_constitution_tos | Galley | authored | pulse_t0 | 0.06072 -> 0.06072 | 0.9939 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Galley | authored | split_t0_t1 | 0.06072 -> 0.06072 | 0.9939 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | native | pulse_t0 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Mess_Hall | native | split_t0_t1 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Galley | native | pulse_t0 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 4.441e-16 -> 4.441e-16 |
| enterprise_galaxy_tng | Galley | native | split_t0_t1 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 3.331e-16 -> 3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | pulse_t0 | 0.2159 -> 0.2159 | 0.9784 -> 0.9784 | -4.441e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | split_t0_t1 | 0.2159 -> 0.2159 | 0.9784 -> 0.9784 | 3.331e-16 -> 3.331e-16 |
| enterprise_galaxy_tng | Galley | commissioned | pulse_t0 | 0.04606 -> 0.04606 | 0.9954 -> 0.9954 | -4.441e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Galley | commissioned | split_t0_t1 | 0.04606 -> 0.04606 | 0.9954 -> 0.9954 | -3.331e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | pulse_t0 | 0.2159 -> 0.2159 | 0.9784 -> 0.9784 | -4.441e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | split_t0_t1 | 0.2159 -> 0.2159 | 0.9784 -> 0.9784 | 3.331e-16 -> 3.331e-16 |
| enterprise_galaxy_tng | Galley | authored | pulse_t0 | 0.04606 -> 0.04606 | 0.9954 -> 0.9954 | -4.441e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Galley | authored | split_t0_t1 | 0.04606 -> 0.04606 | 0.9954 -> 0.9954 | -3.331e-16 -> -3.331e-16 |
