> **Status:** Evidence data note — supporting files for the ROOM-AIR-01 ambient-exchange audit; not a specification of engine behaviour.

# Evidence files

Generated from `data/platforms/*/air_flow_paths.json` `ambient_openings` records and the matching `spatial_layout.json` zone volumes at `95b4974b`.

- `ambient_opening_records.csv`: one row per ambient-opening record, including current/pre-change ACH-map values, implied ACH, occupancy class, and ROOM-AIR-01 residence factors.
- `ambient_opening_zones.csv`: the same rows aggregated to one row per `(platform, zone)`; `olympia_c6/MD_Forecastle_Open` is the single zone with two records.
- `class_summary.json`: fleet counts and dose-factor ranges by occupancy/opening class.
- `material_zones.json`: all zones with implied ACH > 1 h⁻¹ (283 `open_deck` zones).
- `occupied_material_zones.json`: the 257-zone subset with a declared occupancy path.
- `crew_work_fallback_material_zones.json`: the 26 `open_deck` zones reachable only through the crew work fallback.
