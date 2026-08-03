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

# Protocols (min_escalation_status, activation_delay_epochs)
check-jsonschema --schemafile schemas/protocols.schema.json data/config/protocols.json

# Resource costs
check-jsonschema --schemafile schemas/resource_costs.schema.json data/config/resource_costs.json

# Logging profile
check-jsonschema --schemafile schemas/logging_profile.schema.json data/config/logging_profile.json
```

After editing outbreak-response protocol gates (`min_escalation_status`):

```bash
python3 -m pytest tests/test_data_contracts.py::TestProtocols \
  tests/test_outbreak_response_architecture.py -v --tb=short
```

### Validate all platforms in a loop

Skips catalog/metadata files (`class_photo_catalog.json`, `deck_provenance.json`) automatically — only directories with `spatial_layout.json` are checked.

```bash
for dir in data/platforms/*/; do
  platform=$(basename "$dir")
  [ -f "$dir/spatial_layout.json" ] || continue
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

### Validate Picard & Presidio configs
```bash
check-jsonschema --schemafile schemas/picard_run_spec.schema.json \
  picard_framework/runs/destroyer_baseline_default.json
check-jsonschema --schemafile schemas/presidio_fleet_config.schema.json \
  presidio/data/config/default_fleet.json
check-jsonschema --schemafile schemas/presidio_fleet_economics.schema.json \
  presidio/data/economics/fleet_economics.json
```

### Run pydantic-based deep validation (sanity checker)
```bash
python tools/sanity_checker.py --from-config
```
The sanity checker goes beyond JSON Schema to validate:
- Mathematical bounds (volumes > 0, probabilities in [0,1], etc.)
- Cross-file referential integrity (airflow rooms reference valid zones)
- Dose-response parameter validity
- `config.yaml` infection counters and `exempt_classes` in protocols

### Run data contract tests
```bash
python -m pytest tests/test_data_contracts.py -v --tb=short
```

## Schema File Map

| Schema | Validates | Data Path |
|--------|-----------|-----------|
| `pathogen_profiles.schema.json` | Pathogen definitions (route weights, dose_adjustment, nonsusceptibility, env source_zones) | `data/pathogens/active_profiles.json` |
| `spatial_layout.schema.json` | Zone/room structure (dining_service_type, food_contamination_multiplier, max_occupancy, cabin fields) | `data/platforms/*/spatial_layout.json` |
| `air_flow_paths.schema.json` | HVAC zones, links, adjacency | `data/platforms/*/air_flow_paths.json` |
| `protocols.schema.json` | SOP definitions | `data/config/protocols.json` |
| `resource_costs.schema.json` | Budget and inventory | `data/config/resource_costs.json` |
| `logging_profile.schema.json` | Fidelity tier config | `data/config/logging_profile.json` |
| `simulation_history.schema.json` | Per-epoch output | `telemetry_buffer/simulation_history.json` |
| `lab_notebook.schema.json` | Diagnostic records | `telemetry_buffer/artificial_lab_notebook.json` |

## When to Use

- Before every commit that touches files in `data/` or `schemas/`
- After generating output with the orchestrator
- When adding new platforms or pathogens (including Enterprise fiction-adapted bundles)
- As part of the CI-equivalent local validation

CI: `.github/workflows/picard-presidio.yml` validates all nine platforms plus Stackelberg social schemas on `main` and `cursor/**` branches.

## Picard / Presidio / Stackelberg schemas

```bash
check-jsonschema --schemafile schemas/picard_run_spec.schema.json \
  picard_framework/runs/destroyer_baseline_default.json
check-jsonschema --schemafile schemas/information_diffusion.schema.json \
  presidio/data/social/information_diffusion_default.json
check-jsonschema --schemafile schemas/class_interactions.schema.json \
  presidio/data/social/class_interactions_default.json
check-jsonschema --schemafile schemas/global_health_briefing.schema.json \
  presidio/data/intelligence/global_health_timeline.json
check-jsonschema --schemafile schemas/agent_profile.schema.json \
  picard_framework/data/agent_profiles/default_ship_population.json
check-jsonschema --schemafile schemas/resource_costs.schema.json \
  data/config/resource_costs.json
```
