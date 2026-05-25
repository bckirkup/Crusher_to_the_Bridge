---
name: schema-validation
description: Validate all JSON configuration and output files against their schemas. Use before committing changes to any JSON data files in data/ or telemetry_buffer/.
---

# Schema Validation

## Prerequisites

- Python 3.11+ with pydantic installed
- `check-jsonschema` CLI tool (`pip install check-jsonschema`)
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None.

## Quick Commands

### Validate all config files at once
```bash
# Pathogen profiles
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json

# Spatial layout (per platform — repeat for each)
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/destroyer_baseline/spatial_layout.json

# Air flow paths (per platform)
check-jsonschema --schemafile schemas/air_flow_paths.schema.json data/platforms/destroyer_baseline/air_flow_paths.json

# Protocols
check-jsonschema --schemafile schemas/protocols.schema.json data/config/protocols.json

# Resource costs
check-jsonschema --schemafile schemas/resource_costs.schema.json data/config/resource_costs.json

# Logging profile
check-jsonschema --schemafile schemas/logging_profile.schema.json data/config/logging_profile.json
```

### Validate all platforms in a loop
```bash
for dir in data/platforms/*/; do
  platform=$(basename "$dir")
  echo "=== $platform ==="
  check-jsonschema --schemafile schemas/spatial_layout.schema.json "$dir/spatial_layout.json"
  check-jsonschema --schemafile schemas/air_flow_paths.schema.json "$dir/air_flow_paths.json"
done
```

### Validate output files (after an orchestrator run)
```bash
check-jsonschema --schemafile schemas/simulation_history.schema.json telemetry_buffer/simulation_history.json
check-jsonschema --schemafile schemas/lab_notebook.schema.json telemetry_buffer/artificial_lab_notebook.json
```

### Run pydantic-based deep validation (sanity checker)
```bash
python tools/sanity_checker.py
```
The sanity checker goes beyond JSON Schema to validate:
- Mathematical bounds (volumes > 0, probabilities in [0,1], etc.)
- Cross-file referential integrity (airflow rooms reference valid zones)
- Dose-response parameter validity

### Run data contract tests
```bash
python -m pytest tests/test_data_contracts.py -v --tb=short
```

## Schema File Map

| Schema | Validates | Data Path |
|--------|-----------|-----------|
| `pathogen_profiles.schema.json` | Pathogen definitions | `data/pathogens/active_profiles.json` |
| `spatial_layout.schema.json` | Zone/room structure | `data/platforms/*/spatial_layout.json` |
| `air_flow_paths.schema.json` | HVAC zones, links, adjacency | `data/platforms/*/air_flow_paths.json` |
| `protocols.schema.json` | SOP definitions | `data/config/protocols.json` |
| `resource_costs.schema.json` | Budget and inventory | `data/config/resource_costs.json` |
| `logging_profile.schema.json` | Fidelity tier config | `data/config/logging_profile.json` |
| `simulation_history.schema.json` | Per-epoch output | `telemetry_buffer/simulation_history.json` |
| `lab_notebook.schema.json` | Diagnostic records | `telemetry_buffer/artificial_lab_notebook.json` |

## When to Use

- Before every commit that touches files in `data/` or `schemas/`
- After generating output with the orchestrator
- When adding new platforms or pathogens
- As part of the CI-equivalent local validation
