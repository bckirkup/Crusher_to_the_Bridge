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

Copy from an existing platform and adapt:
```bash
cp data/platforms/destroyer_baseline/spatial_layout.json data/platforms/<platform_name>/spatial_layout.json
```

Required structure per zone (matches `schemas/spatial_layout.schema.json`):
```json
{
  "zones": [
    {
      "id": "unique_zone_name",
      "type": "Free",
      "traffic": "low",
      "volume_m3": 150.0,
      "deck": "main",
      "display": {"x": 100, "y": 12}
    }
  ]
}
```

Zone `type` values include `Free`, `Dining`, `Room`, etc. **Dining** zones enable food-contamination pathway pools.

**Law 3 constraints:**
- `volume_m3` must be > 0
- `display.x` and `display.y` must be present (used by LCARS dashboard tactical deck)
- All `id` values must be unique

### 3. Create `air_flow_paths.json`

Required structure (matches `schemas/air_flow_paths.schema.json`):
```json
{
  "hvac_zones": [
    {
      "id": "zone_main",
      "rooms": ["MedBay", "Galley"],
      "ach": 6.0
    }
  ],
  "cross_zone_links": [
    {
      "from": "zone_main",
      "to": "zone_upper",
      "flow_rate_m3h": 50.0,
      "is_hvac_ducted": false,
      "path": "ladder_well"
    }
  ],
  "adjacency": [
    {
      "from": "Bridge",
      "to": "MedBay",
      "type": "door"
    }
  ]
}
```

**Law 4 referential integrity constraints:**
- Every room in `hvac_zones[].rooms` must reference a valid zone `id` from `spatial_layout.json`
- Every `from` / `to` in `cross_zone_links` must reference a valid `hvac_zones[].id`
- Every `from` / `to` in `adjacency` must reference a valid spatial zone `id`
- `ach` and `flow_rate_m3h` must be >= 0

### 4. Validate with the sanity checker
```bash
python tools/sanity_checker.py --platform-dir data/platforms/<platform_name>
```
Expected: No ERROR findings.

### 5. Validate against JSON schemas
```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/<platform_name>/spatial_layout.json
check-jsonschema --schemafile schemas/air_flow_paths.schema.json data/platforms/<platform_name>/air_flow_paths.json
```

### 6. Run data contract tests
```bash
python -m pytest tests/test_data_contracts.py -v --tb=short
```

### 7. Test with the orchestrator (optional)

Update `crusher_labs/config.yaml` to point to the new platform paths, then run:
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

- Using `zone_id` instead of `id` — fails schema and sanity checker
- Forgetting `display` coordinates — LCARS tactical deck map will misplace zones
- Referencing zone names in `air_flow_paths.json` that don't exist in `spatial_layout.json` — fails Law 4
- Setting `volume_m3` to 0 — fails Law 3 (must be > 0)
- Duplicate zone `id` values — fails uniqueness check
