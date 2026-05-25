---
name: adding-new-platform
description: Add a new ship/vessel platform to Crusher-to-the-Bridge. Covers creating spatial layout, air flow paths, and validating referential integrity. Use when adding a new vessel type.
---

# Adding a New Platform

## Prerequisites

- Python 3.11+ with pydantic, numpy, and pyyaml installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)
- Familiarity with the existing platform structure (see `data/platforms/destroyer_baseline/`)

## Devin Secrets Needed

None.

## Steps

### 1. Create the platform directory
```bash
mkdir -p data/platforms/<platform_name>
```
Use snake_case for the directory name (e.g., `arleigh_burke_ddg`, `freedom_class_lcs`).

### 2. Create `spatial_layout.json`

Copy the schema structure from an existing platform and adapt:
```bash
cp data/platforms/destroyer_baseline/spatial_layout.json data/platforms/<platform_name>/spatial_layout.json
```

Required structure per zone:
```json
{
  "zones": [
    {
      "zone_id": "unique_zone_name",
      "zone_type": "Free|Dining|Room|Engineering|Medical|Weather",
      "volume_m3": 150.0,
      "display_x": 0.5,
      "display_y": 0.3
    }
  ]
}
```

**Law 3 constraints:**
- `volume_m3` must be > 0
- `display_x` and `display_y` must be present (used by dashboard)
- All `zone_id` values must be unique

### 3. Create `air_flow_paths.json`

Required structure:
```json
{
  "hvac_zones": [
    {
      "hvac_zone_id": "HVAC_Zone_1",
      "rooms": ["zone_id_1", "zone_id_2"],
      "ach": 6.0
    }
  ],
  "cross_zone_links": [
    {
      "from_hvac_zone": "HVAC_Zone_1",
      "to_hvac_zone": "HVAC_Zone_2",
      "flow_rate_m3h": 50.0
    }
  ],
  "adjacency": [
    {
      "zone_a": "zone_id_1",
      "zone_b": "zone_id_2",
      "flow_rate_m3h": 10.0
    }
  ]
}
```

**Law 4 referential integrity constraints:**
- Every room in `hvac_zones[].rooms` must reference a valid `zone_id` from `spatial_layout.json`
- Every `from_hvac_zone` / `to_hvac_zone` must reference a valid `hvac_zone_id`
- Every `zone_a` / `zone_b` in adjacency must reference a valid `zone_id`
- `ach` and `flow_rate_m3h` must be >= 0

### 4. Validate with the sanity checker
```bash
python tools/sanity_checker.py --platform-dir data/platforms/<platform_name>
```
Expected: No ERROR findings.

### 5. Validate against JSON schemas
```bash
pip install check-jsonschema  # if not installed
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/<platform_name>/spatial_layout.json
check-jsonschema --schemafile schemas/air_flow_paths.schema.json data/platforms/<platform_name>/air_flow_paths.json
```

### 6. Run data contract tests
```bash
python -m pytest tests/test_data_contracts.py -v --tb=short
```

### 7. Test with the orchestrator (optional)

Update `crusher_labs/config.yaml` to point to the new platform:
```yaml
ship_graph:
  spatial_layout: "data/platforms/<platform_name>/spatial_layout.json"
  air_flow_paths: "data/platforms/<platform_name>/air_flow_paths.json"
```
Then run:
```bash
python orchestrator.py --epochs 10
```

## Available Platforms for Reference

| Platform | Directory |
|----------|-----------|
| Destroyer Baseline | `data/platforms/destroyer_baseline` |
| Expedition Cruise 300 | `data/platforms/expedition_cruise_300` |
| Fletcher-class Destroyer | `data/platforms/fletcher_class_destroyer` |
| Legend-class NSC | `data/platforms/legend_class_nsc` |
| Mega Cruise 5000 | `data/platforms/mega_cruise_5000` |
| San Antonio-class LPD | `data/platforms/san_antonio_class_lpd` |

## Common Mistakes

- Forgetting to add display coordinates (`display_x`, `display_y`) — dashboard will error
- Using zone names in `air_flow_paths.json` that don't exist in `spatial_layout.json` — fails Law 4
- Setting `volume_m3` to 0 — fails Law 3 (must be > 0)
- Duplicate `zone_id` values — fails uniqueness check
