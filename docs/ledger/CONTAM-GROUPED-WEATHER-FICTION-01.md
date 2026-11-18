# CONTAM-GROUPED-WEATHER-FICTION-01
**Date:** 2026-11-18
**Commit:** 95b4974b
**Pathogens:** all
**Status:** closed

## Scope

Stage G4 fiction leg of [`../proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md) §6/§7. The plan's grouped OA>0 fleet table has one fiction row, `enterprise_galaxy_tng/AHU_Public` (`Holodeck1`, `Holodeck2`); the fiction roster also includes `enterprise_constitution_tos`, which has no grouped OA>0 weather row.

Owner ruling (Benjamin, 2026-11-18): "fiction G4 = NO ambient openings for Galaxy holodecks — they are interior force-field rooms, not weather-exposed decks; Enterprise hulls unchanged (non-load-bearing; calm-wind override #1267 already merged)."

Precedent: the stage-4 fiction ledger-only no-op [`CONTAM-AMBIENT-WEATHER-FICTION-01`](CONTAM-AMBIENT-WEATHER-FICTION-01.md). Related machinery: [`CONTAM-DEFAULT-WEATHER-ENTERPRISE-01`](CONTAM-DEFAULT-WEATHER-ENTERPRISE-01.md).

## Roster calls

| hull | plan fleet-table row | call |
|---|---|---|
| `enterprise_constitution_tos` | none | no-op: no grouped OA>0 weather zones; no `exposure`, `ambient_openings`, HVAC group, link, bundle or schema change |
| `enterprise_galaxy_tng` | `AHU_Public`: `Holodeck1`, `Holodeck2` | no-op by owner ruling: holodecks are interior force-field rooms, not weather-exposed decks; they remain grouped on `AHU_Public` with no `exposure: weather` and no `open_deck` `ambient_openings` |

The only fiction-adapted Enterprise platform bundles are `enterprise_constitution_tos` and `enterprise_galaxy_tng`; there are no other fiction rows to carry forward.

## Change (exactly)

None. This PR adds this ledger entry and its README registration only. No platform JSON, committed Contam bundle, `path_map.json`, `flow_rate_m3h`, leak area, exporter constant, engine code, schema, test, campaign artifact, or epidemiological constant changed. Existing stage-3 `makeup_louvre` records on `Mess_Hall` and the Enterprise calm-wind overrides are untouched.

## Validation

- `pre-commit run --files docs/ledger/CONTAM-GROUPED-WEATHER-FICTION-01.md docs/ledger/README.md`
- `python3 -m pytest tests/test_ledger_entries.py`
- `git diff --name-only origin/main...HEAD` shows only the two ledger docs.
