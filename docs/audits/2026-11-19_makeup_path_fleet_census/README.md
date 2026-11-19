> **Status:** Evidence census for the fleet-wide exhaust-only AHS make-up carriage defect class. This note authors no openings, platform data, schema, exporter, constants, or behaviour change, and ran no ContamX solves.

# Makeup-path fleet census — 2026-11-19

Question: `pope_ap110` was the worst member of the residual class "exhaust-only AHS groups have no authored make-up path" (`docs/ledger/CONTAM-FIELD-PRESSURE-REVIEW-01.md`; Pope boundary evidence `docs/audits/2026-11-18_pope_ap110_envelope_makeup_boundary/README.md`; fix `docs/ledger/CONTAM-POPE-MAKEUP-01.md`, PR #1314). Which other committed hulls carry the same class, and does it matter for campaign hulls?

## Method

Static census over every committed Contam bundle: 77 of 82 `data/platforms/` directories have `air_flow_paths.json` + `contam/platform.prj` + `contam/path_map.json`. Pressure maxima are cited only from committed diagnostics/ledgers; the fleet-wide table is `docs/ledger/CONTAM-FIELD-PRESSURE-REVIEW-01.md`, superseded for individual hulls by newer committed weather/makeup ledgers named in `current_commissioned_pressure.source`. No ContamX solves were run: static evidence plus existing witnesses were sufficient, so no solve is named.

`declared_makeup_demand_m3h` is the committed `path_map.json` AHS return-minus-supply sum for `hvac_duty <= 0` groups. It is a static declared-flow census; solved diagnostic values can differ by solver density/rounding and are recorded separately where a ledger gives them.

## Census result

- All 77 committed bundles have at least one duty-0 / `oa_fraction` 1.0 exhaust-only AHS branch. Counts range from 1 (eight hulls, including `passumpsic_ao106`) to 63 (`mega_cruise_5000`); declared exhaust-only make-up demand ranges from 124.723 m³/h (`pt_564`) to 42,327.36 m³/h (`mega_cruise_5000`).
- Every bundle already has `Sanitary_Makeup` cross-zone links/paths; envelope leaks are present on 75 of 77 bundles, with the two Enterprise fiction hulls using the life-support plenum boundary instead. Those are necessary topology, not a sufficient fix. Committed ledgers show the cruise/fiction `Sanitary_Makeup` legs can solve zero flow while envelope leaks carry the deficit.
- Only 10 hulls have authored `makeup_louvre` `ambient_openings` records, 26 records total: `pope_ap110` 7, `mega_cruise_5000` 10, `diamond_princess` 1, `classic_cruise_1900` 1, `expedition_cruise_450` 1, `greg_mortimer` 2, `spirit_cruise_3000` 1, `enterprise_constitution_tos` 1, `enterprise_galaxy_tng` 1, `olympia_c6` 1.
- Ranking by the committed fleet-review commissioned max |ΔP| is in `evidence/fleet_census.csv` / `evidence/fleet_census.json`. Those rows are the pre-weather/makeup fleet snapshot; use `current_commissioned_pressure` where a newer ledger exists before acting on a rank.

## Campaign-relevant hulls

Phase-1 hvac-tracer bundled hulls plus mega-cruise campaign platforms (`picard_framework/runs/mega_cruise_campaign/`). `fletcher_class_destroyer` is a phase-1 HULL but has no committed Contam bundle, so it is outside this census.

| hull | campaign | exhaust-only groups | declared demand m³/h | `makeup_louvre` | current commissioned envelope max \|ΔP\| Pa | current commissioned interior flowing max \|ΔP\| Pa | current source |
|---|---|---:|---:|---:|---:|---:|---|
| `destroyer_baseline` | phase1 | 3 | 715.392 | 0 | 81,561.180 | 0.845 | `CONTAM-DUCT-EXCLUDE-01`; `CONTAM-FIELD-PRESSURE-REVIEW-01` |
| `expedition_cruise_450` | phase1 + mega | 13 | 4,530.816 | 1 | 89.188 | 64.1 | `CONTAM-DUCT-EXCLUDE-01`; `CONTAM-AMBIENT-WEATHER-CRUISE-01` |
| `lexington_cv2` | phase1 | 5 | 6,159.368 | 0 | 4.61 | 1.771 | `CONTAM-AMBIENT-WEATHER-CARRIER-01` |
| `saratoga_cv3` | phase1 | 5 | 7,096.796 | 0 | 4.952 | 1.746 | `CONTAM-AMBIENT-WEATHER-CARRIER-01` |
| `missouri_bb63` | phase1 | 5 | 17,104.05 | 0 | 59.163 | 58.027 | `CONTAM-GROUPED-WEATHER-BATTLESHIP-01` |
| `classic_cruise_1900` | mega | 17 | 8,703.936 | 1 | 68.74 | 99.48 | `CONTAM-AMBIENT-WEATHER-CRUISE-01`; `CONTAM-DUCT-EXCLUDE-01` |
| `enterprise_constitution_tos` | mega | 19 | 4,411.584 | 1 | n/a | 8.721 | `CONTAM-AMBIENT-WEATHER-FICTION-01` |
| `enterprise_galaxy_tng` | mega | 37 | 6,557.76 | 1 | n/a | 35.54 | `CONTAM-AMBIENT-WEATHER-FICTION-01` |
| `mega_cruise_5000` | mega | 63 | 42,327.36 | 10 | 290.365 | 284.9 | `CONTAM-DUCT-EXCLUDE-01`; `CONTAM-AMBIENT-WEATHER-CRUISE-01` |
| `spirit_cruise_3000` | mega | 28 | 13,711.68 | 1 | not reported | 22.147 | `CONTAM-SPIRIT-CABIN-RELIEF-01` |

Enterprise rows have `envelope` n/a because the committed life-support-plenum export makes the plenum the hull ambient boundary and reports envelope net inward 0; their boundary flow is the plenum opening, not envelope-leak make-up.

## Does it matter for campaign hulls?

Only one campaign hull remains in the Pope-class state by the stated trigger (commissioned envelope max |ΔP| ≫ 1 kPa attributable to make-up carriage): `destroyer_baseline` at 81,561 Pa. It has only three exhaust-only groups and 715.392 m³/h declared demand, but it was skipped by the destroyer weather-opening pass (`CONTAM-AMBIENT-WEATHER-DESTROYER-01.md` records no qualifying ungrouped weather zone), so the deficit still crosses the envelope. The other campaign hulls are at 4.61–290.365 Pa envelope max where envelope is reported (`spirit_cruise_3000` reports commissioned all-path/interior 24.167/22.147 Pa instead), or use an authored plenum boundary; `classic_cruise_1900`’s larger `CONTAM-DUCT-EXCLUDE-01` maximum is a `prescribed_link` class, not envelope make-up carriage.

## Recommendation and class boundary

Class boundary: the defect is not "has exhaust-only AHS" or "has `Sanitary_Makeup`" — that is all 77 bundles. It is the commissioned state where AHS return-minus-supply demand has no reachable authored ambient make-up route, so envelope leaks become the make-up path and the pressure field records envelope max |ΔP| ≫ 1 kPa with envelope net inward ≈ make-up demand.

- Author make-up legs now: `destroyer_baseline` only, among campaign hulls. It is the sole campaign member still showing an envelope make-up residual above the 1 kPa class boundary.
- Accept-and-document for campaign hulls: `expedition_cruise_450`, `lexington_cv2`, `saratoga_cv3`, `missouri_bb63`, `classic_cruise_1900`, `enterprise_constitution_tos`, `enterprise_galaxy_tng`, `mega_cruise_5000`, `spirit_cruise_3000`; their committed witnesses are below the class boundary or already have authored make-up/plenum carriage.
- Fleet beyond campaigns: do not launch a fleet-wide authoring pass from this static census. For the non-campaign hulls, first use the newest committed per-hull witness; author only where that witness still shows commissioned envelope make-up carriage above the boundary. The fleet-review rank is a lead list, not a current measurement after the weather/makeup ledgers.

## Evidence

- `evidence/fleet_census.json` — full per-hull static census, carriage counts, cited pressure witnesses, campaign tags, severity rank.
- `evidence/fleet_census.csv` — same hull set in tabular form.
