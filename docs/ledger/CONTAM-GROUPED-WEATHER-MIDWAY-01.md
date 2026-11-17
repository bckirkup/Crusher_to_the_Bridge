# CONTAM-GROUPED-WEATHER-MIDWAY-01
**Date:** 2026-11-17
**Commit:** 0229916a
**Pathogens:** all
**Status:** measured
**Measured at:** 52d7733c

## Scope

Stage G1 of [`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
§3: the first **grouped** weather zone to receive an `ambient_openings` record,
on `midway_cv41` only. Owner rulings of 2026-11-17, verbatim:

- fleet rule — "Grouped zones may receive ambient_openings; the opening
  REPLACES the group's OA leg for that zone (no double-count)";
- staging — "Approve G1–G3 staging: Midway representation (after Q2), Pope
  evidence table, Aeolus capacity controls — no fleet rollout".

Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md)
and [`CONTAM-AMBIENT-WEATHER-OLYMPIA-01`](CONTAM-AMBIENT-WEATHER-OLYMPIA-01.md).
Steady ContamX solves used the local official NIST binary
`third_party/contamx/contamx3`; no seeds, no AWS. All numbers below are
measured on the data committed at `52d7733c`, on top of `origin/main`
`0229916a`; "before" is `0229916a` itself.

## Change (exactly)

`data/platforms/midway_cv41/spatial_layout.json`

- `Flight_Deck`: `exposure: "weather"` added (D7(b)). It had no `exposure`
  field on `0229916a`.

`data/platforms/midway_cv41/air_flow_paths.json`

1. `hvac_zones[VENT_Weather].rooms`: `["Flight_Deck", "Island_Upper"]` →
   `["Island_Upper"]`, description updated. `ach` 1.0, `oa_fraction` 1.0,
   `vent_mode` `nat_supply` and `evidence` are untouched. **Why:** both the
   native builder and the ContamW exporter emit a group's supply/return/OA
   legs per entry of `rooms`; room membership is the only declaration that
   makes the group count a zone's outdoor exchange. Removing `Flight_Deck`
   from `rooms` is therefore the minimal way to make `VENT_Weather` stop
   counting the flight deck's outdoor exchange as HVAC OA. The removed leg was
   `ach × V × hvac_duty = 1.0 × 28,293.69 × 0.5 = 14,146.845 m³/h` at
   `oa_fraction` 1.0.
2. One `ambient_openings` record (D1(a)): `zone` `Flight_Deck`, `type`
   `open_deck`, `area_m2` 582.687, `wind_speed_m_s` 1.0, `schedule`
   `always_open`, `exchange_m3h` 381,200.9.
3. `cross_zone_links` record `VENT_Weather → VENT_Hangar`, `ladder_well_1`,
   50 m³/h, bidirectional, was split into two records of 25 m³/h each:
   `VENT_Weather → VENT_Hangar` and `Flight_Deck → VENT_Hangar`. **Why:** the
   record addressed `Flight_Deck` through the group id and is expanded over
   every (from-room, to-room) pair. Left alone after edit 1 it would have
   doubled `Island_Upper`'s three hangar pairs from 8.33 to 16.67 m³/h each
   and dropped `Flight_Deck`'s three (measured on the working tree before the
   split). The split keeps the declared total at 50 m³/h and every room pair
   at 50/6 m³/h. This is a re-addressing of an unchanged reference flow, not a
   magnitude change — but it does edit a `flow_rate_m3h` field, so it is
   called out here for owner review.

`data/platforms/midway_cv41/contam/{platform.prj,path_map.json}` regenerated
with `scripts/generate_platform_contam_prj.py --platform midway_cv41
--ahs-terminal-mode commissioned`.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES["midway_cv41"]`
added; `tests/test_contam_ambient_opening_boundary.py` committed-leg census
gains `"midway_cv41": 2`. Both moves are the two opening legs / the one
exposure tag of this change.

No engine, exporter or schema code changed.

## Area witness (Grade C)

`area_m2` = ASSUMED-OPEN-DECK-FACE-AREA, Grade C: `2 × sqrt(V / 3) × 3` with
V = 28,293.69 m³ → 582.687 m² (recomputed: 582.6867). Owner-approved through
the staging ruling. It is the stage-4 square-plan deck-face rule, not a
measured area, and was not adjusted against any pressure result.

Geometry cross-check (reported, not applied): the layout carries
`floor_area_m2` 10,882.19 and `ceiling_height_m` 2.6. A square plan of that
floor area has side 104.3 m, so two opposite faces at the declared 2.6 m
height are 542.5 m², and at the exporter's 3 m zone height 625.9 m². The
approved 582.687 m² sits between the two (−7 % / +7 %), so the witness is
consistent with the hull's declared geometry at the precision of a Grade C
square-plan rule. A real CV-41 flight deck is not square and is open on all
edges and above; the rule understates the true open perimeter, as it does on
every stage-4 hull.

## D5 exchange

`exchange_m3h` is the commissioned-lane ContamX-solved **outward** flow of the
opening at `wind_speed_m_s` 1.0, measured after edits 1–3
(`tools/contam_flow_compare.py --platform midway_cv41 --run-contamx`):

| leg | path nr | ΔP, Pa | flow, m³/h |
|---|---:|---:|---:|
| outward (`Flight_Deck → ambient`) | 644 | +0.2165 | 381,200.9 |
| inward (`ambient → Flight_Deck`) | 643 | −0.2411 | 402,302.2 |
| net inward | | | 21,101.3 |

The audit scenario's 21,100.28 m³/h is the **net inward** flow and was not
used. The bundle is byte-identical with `exchange_m3h` 0.0 and 381,200.9
(sha256 of `platform.prj` and `path_map.json` checked), so the measurement
does not depend on the value written back.

## No double-count, both lanes

Before/after diff of the full native path list (1,233 paths) and of the
exported `path_map.json` (802 rows, path/AHS numbering ignored):

| lane | removed | added |
|---|---|---|
| native | `VENT_Weather_ret_Flight_Deck`, `Flight_Deck → _plenum_VENT_Weather`, 14,146.845 m³/h, `hvac_return` | `ambopen_0_Flight_Deck_open_deck`, `Flight_Deck → ambient`, `ambient_exchange_open_deck`, sink, exchange |
| ContamX export | `ahs_return` `Flight_Deck → ahs1(Ret)` 14,146.845; `ahs_supply` `ahs1(Sup) → Flight_Deck` 14,146.845 | two `ambient_opening` rows `Flight_Deck → ambient` |

Nothing else differs in either lane. After the change `Flight_Deck` has no
HVAC group leg in either lane and exactly one outdoor exchange representation
(one native exchange sink; one orifice pair). Row counts are unchanged
(1,233 / 802) because one native path and two exported rows were swapped
one-for-one.

## Island_Upper supply (not stranded)

`Island_Upper` (390.0 m³) is the only other `VENT_Weather` room.

| witness | before | after |
|---|---:|---:|
| native + exported `VENT_Weather` rows for `Island_Upper` | present | identical (no diff) |
| commissioned terminal supply, declared / solved, m³/h | 195.00 / 196.997 | 195.00 / 196.997 (ratio 1.010) |
| commissioned terminal return, declared / solved, m³/h | 195.00 / 196.997 | 195.00 / 196.997 (ratio 1.010) |
| design-lane terminal supply = return, solved, m³/h | 7,244.364 | 196.997 |
| native outflow rate k, 1/h | 0.6026 | 0.6026 |
| `ladder_well_1` per hangar pair, native, m³/h | 8.333 | 8.333 |

`tools/contam_commissioned_check.py --platform midway_cv41` passed before and
after (every commissioned terminal inside 5 % of declared). The design-lane
solved terminal flow for `Island_Upper` fell from 7,244.364 to 196.997 m³/h
(declared 195.00) when `Flight_Deck` left the group; this is measured, and is
the source of the design-lane field/native move in the paired table below
(30.8 → 0.84). The mechanism — the design lane sharing one group fan flow
between a 28,294 m³ and a 390 m³ terminal — is an inference, not traced here.

## Pressure diagnostic rows

`tools/diag/contam_pressure_balance_diagnostic.py --hull midway_cv41`, sources
`Flight_Deck` and `Island_Upper`, 3 rows each, 0 unsolved, before and after.
The hull-level columns are identical for both sources.

| lane | | max \|ΔP\|, Pa | envelope max \|ΔP\|, Pa | flowing interior max \|ΔP\|, Pa | opening max \|ΔP\|, Pa | makeup demand, m³/h | envelope net inward, m³/h | opening net inward, m³/h | balance residual, m³/h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| authored / commissioned | before | 1,343,796.0 | 1,343,796.0 | 14.637 | — | 21,176.163 | 21,176.163 | 0 | −5.1e-11 |
| authored / commissioned | after | 353.585 | 32.678 | 27.884 | 0.2411 | 21,176.163 | 74.814 | 21,101.331 | 0.0176 |
| design | before | 353.585 | 2.731 | 7.6e-05 | — | 0.0 | 0.0 | 0 | −0.0 |
| design | after | 353.585 | 4.607 | 1.06e-04 | 0.2288 | 0.0 | 23.966 | −23.966 | −0.0007 |

The authored and commissioned lanes solve identically on this hull, before and
after. The 353.585 Pa maximum is the AHS OA/exhaust system paths, as in the
audit. Envelope leaks after: 64 inward / 1 outward, median \|ΔP\| 19.51 Pa,
44 of 65 over 10 Pa, none over 100 Pa.

Against the plan's §3.2 audit scenario (`all_explicit_weather_open`: envelope
33.038 Pa, flowing interior 27.883 Pa, opening net inward 21,100.28 m³/h,
makeup demand unchanged): this change measures 32.678 Pa, 27.884 Pa,
21,101.33 m³/h, makeup demand unchanged. The plan's framing holds. The small
envelope difference is expected — the audit scenario kept the group OA leg;
this change removes it. Nothing was tuned toward 33.04 Pa.

The flowing-interior rise from 14.64 to 27.88 Pa is the makeup demand now
entering at one place (the flight-deck opening, top of the hull) and being
drawn down through the interior openings, instead of entering through 65
distributed envelope leaks at an unphysical 1.34 MPa.

## Paired native / field rows

The standalone `tools/diag/contam_paired_diagnostic.py` accepts only the nine
bundled hulls (`--hull` choices do not include `midway_cv41`); the same paired
NATIVE-vs-field cells are produced for any hull by the pressure diagnostic's
`--source` option, which is what was run (`pulse_t0`, `split_t0_t1`).

Source-zone outflow rate k, 1/h:

| source | lane | native before | field before | native after | field after | field/native after |
|---|---|---:|---:|---:|---:|---:|
| `Flight_Deck` | commissioned | 0.5025 | 0.5365 | 13.4755 | 14.2188 | 1.055 |
| `Flight_Deck` | design | 0.5025 | 0.2561 | 13.4755 | 13.8513 | 1.028 |
| `Island_Upper` | commissioned | 0.6026 | 1.3397 | 0.6026 | 0.6990 | 1.160 |
| `Island_Upper` | design | 0.6026 | 18.5765 | 0.6026 | 0.5056 | 0.839 |

Paired cells closed at machine precision (`closure_error` ≤ 1.7e-15). Native
`Flight_Deck` `pulse_t0` after: local material time 0.07366 h, whole-hull
0.07375 h, transport loss 0.99262.

**Consequence the owner should see.** Under D5 the native `Flight_Deck`
outdoor exchange rises from 0.50 to 13.47 1/h (27×): the removed group leg was
14,146.845 m³/h and the replacing opening is 381,200.9 m³/h. This is the D5
rule applied as on every stage-4 hull (Olympia's openings are 137–325 1/h on
their zones) and brings native and field lanes into agreement on
`Flight_Deck` (field/native 1.03–1.06) and on `Island_Upper` (design-lane
field/native 30.8 → 0.84). It is nonetheless a large change in the native
ventilation of a 300-occupant zone, measured on one steady solve at one wind
point.

## Validation

- Byte-pin: every committed `data/platforms/*/contam/platform.prj` bundle
  regenerated with `--ahs-terminal-mode commissioned`; `git status` shows only
  `midway_cv41` paths under `data/platforms`.
- `python3 -m pytest tests/ -m 'not slow' -n auto`.
- `tests/test_ledger_entries.py`; schema check of the edited JSON;
  `pre-commit` on changed files.
- `tools/contam_commissioned_check.py --platform midway_cv41`: PASS.

## Reproduction

```bash
.venv/bin/python scripts/generate_platform_contam_prj.py --platform midway_cv41 \
  --ahs-terminal-mode commissioned
.venv/bin/python tools/contam_flow_compare.py --platform midway_cv41 \
  --run-contamx --inject Flight_Deck
for s in Flight_Deck Island_Upper; do
  .venv/bin/python -m tools.diag.contam_pressure_balance_diagnostic \
    --hull midway_cv41 --lane authored --lane commissioned --lane design \
    --source "$s" --timing pulse_t0 --timing split_t0_t1 --all-paths \
    --timeout-s 1800 --out "telemetry_buffer/midway_gw/after_$s.json"
done
.venv/bin/python tools/contam_commissioned_check.py --platform midway_cv41
```

## Non-goals observed

No other hull; no Pope/Aeolus work; no schema, engine or exporter change; no
`envelope_leak.area_m2` change; no Phase-1/Phase-2 design repin (none was
required, `_01`/`_v1` untouched); no campaign work; no epidemiological
constant; no magnitude fitting. The one `flow_rate_m3h` field edit is the
`ladder_well_1` split in Change item 3.

## Open

- G4 pattern witnesses on other grouped weather hulls: not started, by ruling.
- Whether a grouped zone's `cross_zone_links` addressed by group id should
  follow the zone automatically when an opening replaces its OA leg is a fleet
  authoring question for G4; here it was resolved by an explicit split.
