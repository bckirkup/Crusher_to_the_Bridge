# CONTAM-AMBIENT-WEATHER-FICTION-01
**Date:** 2026-11-17
**Commit:** 81a57eba
**Pathogens:** all
**Status:** measured
**Measured at:** 81a57eba

## Scope

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **fiction class**: `enterprise_constitution_tos` and
`enterprise_galaxy_tng` only. The roster was enumerated with the audit
classifier (`tools.hull_audit._is_exterior`: authored `exposure` when present,
else the lexical id match for `type == "Free"`) and the HVAC grouping/outdoor
exchange rules from `data/platforms/<hull>/air_flow_paths.json`.

Owner rulings recorded verbatim (Benjamin, 2026-11-16):

- `"we can do enterprises separately"` — implemented as the calm-wind override
  in `CONTAM-DEFAULT-WEATHER-ENTERPRISE-01` (#1267); the Enterprises' wind
  treatment stays calm (`relative_wind_speed_m_s: 0`).
- `"the Grade C deck-face area rule and its large solved rates are ACCEPTED as
  declared assumptions — record, do not tune."`

Result: **no ungrouped or zero-outdoor-exchange weather zone qualifies on either
fiction hull**, so no `exposure` field, `ambient_openings` record, bundle
payload, engine/exporter constant, `flow_rate_m3h`, `envelope_leak.area_m2`,
wind override, hatch, balcony, cache, or campaign artifact changed. The only
lexical weather zones on the roster are grouped with nonzero outdoor exchange
and are recorded below as the known grouped-zone open item.

Because no weather opening was authored, the calm-wind consequence did not
produce a measurable field-lane weather exchange here: there is no weather
`open_deck` leg whose outward flow could be ~0 under resolved wind 0 m/s while
the native lane applied a declared axis. That D2 parity caveat remains the
recipe constraint for any future fiction weather opening; it is not triggered
by this class result.

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-ENTERPRISE-01`](CONTAM-DEFAULT-WEATHER-ENTERPRISE-01.md),
[`CONTAM-LIFE-SUPPORT-PLENUM-01`](CONTAM-LIFE-SUPPORT-PLENUM-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-AMBIENT-WEATHER-DESTROYER-01`](CONTAM-AMBIENT-WEATHER-DESTROYER-01.md),
[`CONTAM-AMBIENT-WEATHER-CARRIER-01`](CONTAM-AMBIENT-WEATHER-CARRIER-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Roster calls

| hull | weather zones (lexical/authored) | HVAC group | outdoor exchange 1/h | call |
|---|---|---|---:|---|
| `enterprise_constitution_tos` | none | — | — | no `_is_exterior` weather zones; no ungrouped Free zones |
| `enterprise_galaxy_tng` | `Holodeck1` (`spatial_layout.json:81`), `Holodeck2` (`spatial_layout.json:94`) | `AHU_Public` (`air_flow_paths.json:129`, `ach` 9.0, `hvac_duty` 0.5, default `oa_fraction` 0.15) | 0.675 | skip: grouped with OA exchange; lexical `deck` match inside `Holodeck`, descriptions are "Holodeck complex A/B", not an authored open/semi-open deck |

The two Galaxy holodecks are the only `_is_exterior` zones on the fiction
roster. They stay untouched under the scope rule; whether they should instead
be declared `exposure: enclosed` (or remain grouped weather rooms) is the
known grouped-zone open item, not a stage-4 opening authoring decision.

## Exposure and opening calls

- **Weather records: 0.** No `exposure: weather` was authored and no
  `open_deck` `ambient_openings` record was added on either Enterprise hull.
- **Enclosed corrections: 0.** No lexical-miss enclosed zone was found on the
  two hulls.
- **Existing openings unchanged.** The only declared `ambient_openings` remain
  the stage-3 `makeup_louvre` records on `Mess_Hall` (`exchange_m3h` 0.0). The
  committed field-lane `ambient_opening` legs are the exporter-only
  `LS_Plenum` boundary from `CONTAM-LIFE-SUPPORT-PLENUM-01`; they solve
  inward-only on every lane (outward 0 m³/h).

## Bundles and design pins

Regenerated both committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`
and verified byte-identity with
`git diff --exit-code -- data/platforms/enterprise_constitution_tos/contam data/platforms/enterprise_galaxy_tng/contam`.
Path counts are unchanged (Constitution 570, Galaxy 1,432), so no frozen
Phase 1/2 design pin can move and no `_v2` succession was needed; `_01`/`_v1`
artifacts are byte-untouched. No cache was produced or uploaded.

## Openings and D5

No new weather opening means no new D5 `exchange_m3h` value. For completeness,
the existing declared/plenum boundary solves as follows:

| hull | declared `ambient_openings` record(s) | field legs | solved outward m³/h design / commissioned / authored | declared `exchange_m3h` |
|---|---|---:|---:|---:|
| `enterprise_constitution_tos` | `Mess_Hall` `makeup_louvre` | 2 `LS_Plenum` | 0 / 0 / 0 | 0.0 |
| `enterprise_galaxy_tng` | `Mess_Hall` `makeup_louvre` | 2 `LS_Plenum` | 0 / 0 / 0 | 0.0 |

The native lane still reports the declared `Mess_Hall` `makeup_louvre` exchange
link at 0.0 m³/h; the field lane's inward makeup is sized by the life-support
plenum export (9,411.593 / 14,557.775 m³/h commissioned) rather than by a
weather-axis wind.

## Witnesses

`tools/diag/ambient_makeup_witness.py` (which runs
`tools/diag/contam_pressure_balance_diagnostic.py`,
`tools/contam_flow_compare.py --run-contamx`,
`tools/diag/contam_paired_diagnostic.py`, and the forced-exhaust exact check)
was run at `81a57eba` for both hulls. Because this PR changes no platform or
exporter input, before and after are the same tree; the compare was generated
from the same labelled run twice. Steady ContamX solves used the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

`tools/contam_commissioned_check.py --platform enterprise_constitution_tos --platform enterprise_galaxy_tng`:
**PASS** — 570 / 1,432 emitted paths against 63 / 127 declared room branches,
every commissioned terminal inside 5% of declared.

### Pressure balance (before -> after)

| hull | lane | paths | max dP Pa | interior flowing max dP Pa | exhaust sinks m3/h | envelope net in m3/h | opening in m3/h | opening out m3/h | opening max dP Pa | balance residual m3/h | k field/native median |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| enterprise_constitution_tos | design | 570 -> 570 | 10.47 -> 10.47 | 8.705 -> 8.705 | 5000 -> 5000 | 0 -> 0 | 5000 | 0 | 10.45 | 0.0001782 -> 0.0001782 | 0.9205 -> 0.9205 |
| enterprise_constitution_tos | commissioned | 570 -> 570 | 10.48 -> 10.48 | 8.721 -> 8.721 | 5000 -> 5000 | 0 -> 0 | 9412 | 0 | 10.45 | -4.455e-05 -> -4.455e-05 | 1 -> 1 |
| enterprise_constitution_tos | authored | 570 -> 570 | 10.48 -> 10.48 | 8.721 -> 8.721 | 5000 -> 5000 | 0 -> 0 | 9412 | 0 | 10.45 | -4.455e-05 -> -4.455e-05 | 1 -> 1 |
| enterprise_galaxy_tng | design | 1432 -> 1432 | 35.54 -> 35.54 | 35.54 -> 35.54 | 8000 -> 8000 | 0 -> 0 | 8000 | 0 | 10.45 | -0.0003564 -> -0.0003564 | 0.995 -> 0.995 |
| enterprise_galaxy_tng | commissioned | 1432 -> 1432 | 35.54 -> 35.54 | 35.54 -> 35.54 | 8000 -> 8000 | 0 -> 0 | 1.456e+04 | 0 | 10.45 | -0.0005123 -> -0.0005123 | 0.9968 -> 0.9968 |
| enterprise_galaxy_tng | authored | 1432 -> 1432 | 35.54 -> 35.54 | 35.54 -> 35.54 | 8000 -> 8000 | 0 -> 0 | 1.456e+04 | 0 | 10.45 | -0.0005123 -> -0.0005123 | 0.9968 -> 0.9968 |

Design-lane max |ΔP| is 10.47 Pa on Constitution and 35.54 Pa on Galaxy, both
inside the stage-1 naval design range 0.5–374 Pa. Balance residuals are
unchanged and at solver-noise level (largest magnitude 5.123e-4 m³/h).

### Flow compare (before -> after)

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | native ambient_exchange links / total m3/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| enterprise_constitution_tos | 570 -> 570 | 466 -> 466 | 286 -> 286 | 107 -> 107 | 2 -> 2 | 9411.59 -> 9411.59 | 0 -> 0 | 1 / 0 |
| enterprise_galaxy_tng | 1432 -> 1432 | 1216 -> 1216 | 866 -> 866 | 217 -> 217 | 2 -> 2 | 14557.8 -> 14557.8 | 0 -> 0 | 1 / 0 |

### Paired diagnostic matrix (before -> after)

| hull | source | lane | timing | whole-hull material time h | transport loss | closure error |
|---|---|---|---|---|---|---|
| enterprise_constitution_tos | Mess_Hall | native | pulse_t0 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Mess_Hall | native | split_t0_t1 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 1.11e-16 -> 1.11e-16 |
| enterprise_constitution_tos | Galley | native | pulse_t0 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Galley | native | split_t0_t1 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 3.331e-16 -> 3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | commissioned | pulse_t0 | 0.1117 -> 0.1117 | 0.9888 -> 0.9888 | 0 -> 0 |
| enterprise_constitution_tos | Mess_Hall | commissioned | split_t0_t1 | 0.1117 -> 0.1117 | 0.9888 -> 0.9888 | 0 -> 0 |
| enterprise_constitution_tos | Galley | commissioned | pulse_t0 | 0.04935 -> 0.04935 | 0.9951 -> 0.9951 | 0 -> 0 |
| enterprise_constitution_tos | Galley | commissioned | split_t0_t1 | 0.04935 -> 0.04935 | 0.9951 -> 0.9951 | 0 -> 0 |
| enterprise_constitution_tos | Mess_Hall | authored | pulse_t0 | 0.1117 -> 0.1117 | 0.9888 -> 0.9888 | 0 -> 0 |
| enterprise_constitution_tos | Mess_Hall | authored | split_t0_t1 | 0.1117 -> 0.1117 | 0.9888 -> 0.9888 | 0 -> 0 |
| enterprise_constitution_tos | Galley | authored | pulse_t0 | 0.04935 -> 0.04935 | 0.9951 -> 0.9951 | 0 -> 0 |
| enterprise_constitution_tos | Galley | authored | split_t0_t1 | 0.04935 -> 0.04935 | 0.9951 -> 0.9951 | 0 -> 0 |
| enterprise_galaxy_tng | Mess_Hall | native | pulse_t0 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Mess_Hall | native | split_t0_t1 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Galley | native | pulse_t0 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 4.441e-16 -> 4.441e-16 |
| enterprise_galaxy_tng | Galley | native | split_t0_t1 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 3.331e-16 -> 3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | pulse_t0 | 0.08111 -> 0.08111 | 0.9919 -> 0.9919 | -3.331e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | split_t0_t1 | 0.08111 -> 0.08111 | 0.9919 -> 0.9919 | -3.331e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Galley | commissioned | pulse_t0 | 0.03793 -> 0.03793 | 0.9962 -> 0.9962 | 1.11e-16 -> 1.11e-16 |
| enterprise_galaxy_tng | Galley | commissioned | split_t0_t1 | 0.03793 -> 0.03793 | 0.9962 -> 0.9962 | 1.11e-16 -> 1.11e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | pulse_t0 | 0.08111 -> 0.08111 | 0.9919 -> 0.9919 | -3.331e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | split_t0_t1 | 0.08111 -> 0.08111 | 0.9919 -> 0.9919 | -3.331e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Galley | authored | pulse_t0 | 0.03793 -> 0.03793 | 0.9962 -> 0.9962 | 1.11e-16 -> 1.11e-16 |
| enterprise_galaxy_tng | Galley | authored | split_t0_t1 | 0.03793 -> 0.03793 | 0.9962 -> 0.9962 | 1.11e-16 -> 1.11e-16 |

The same run also wrote the `split_t0_t1` cells and the pressure diagnostic's
whole-hull source-cell material times; all values are identical before/after
and closure errors stay at solver roundoff (max printed 4.441e-16).

## Reproduction

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from tools.hull_audit import _is_exterior, load_platform

for hull in ("enterprise_constitution_tos", "enterprise_galaxy_tng"):
    root = Path("data/platforms") / hull
    layout = load_platform(root / "spatial_layout.json")
    flows = json.loads((root / "air_flow_paths.json").read_text())
    zones = {z["id"]: z for z in layout["zones"]}
    grouped = {
        room for group in flows["hvac_zones"] for room in group.get("rooms", [])
    }
    weather = [z for z in layout["zones"] if _is_exterior(z)]
    print(hull, "weather", [(z["id"], z["id"] in grouped) for z in weather])
    print(hull, "ungrouped_free", [
        z["id"] for z in layout["zones"]
        if z.get("type") == "Free" and z["id"] not in grouped
    ])
PY

for h in enterprise_constitution_tos enterprise_galaxy_tng; do
  .venv/bin/python scripts/generate_platform_contam_prj.py --platform "$h" \
    --ahs-terminal-mode commissioned
done
git diff --exit-code -- \
  data/platforms/enterprise_constitution_tos/contam \
  data/platforms/enterprise_galaxy_tng/contam

.venv/bin/python tools/diag/ambient_makeup_witness.py \
  --label fiction_weather_scope \
  --hull enterprise_constitution_tos --hull enterprise_galaxy_tng
.venv/bin/python tools/diag/ambient_makeup_witness.py \
  --compare fiction_weather_scope fiction_weather_scope
.venv/bin/python tools/contam_commissioned_check.py \
  --platform enterprise_constitution_tos --platform enterprise_galaxy_tng
```
