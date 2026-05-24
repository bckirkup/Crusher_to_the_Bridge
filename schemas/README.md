# Crusher-to-the-Bridge — JSON Schema Definitions

This folder contains [JSON Schema](https://json-schema.org/draft/2020-12/schema)
definitions for all data contracts used in the Crusher-to-the-Bridge platform.

## Configuration Schemas

| File | Validates | Path |
|------|-----------|------|
| `pathogen_profiles.schema.json` | Multi-pathogen definitions | `data/pathogens/active_profiles.json` |
| `spatial_layout.schema.json` | Room/zone node graph | `data/platforms/*/spatial_layout.json` |
| `air_flow_paths.schema.json` | HVAC zones & airflow edges | `data/platforms/*/air_flow_paths.json` |
| `protocols.schema.json` | Standing operating protocols | `data/config/protocols.json` |
| `resource_costs.schema.json` | Budget, inventory, costs | `data/config/resource_costs.json` |
| `logging_profile.schema.json` | Fidelity tier configuration | `data/config/logging_profile.json` |

## Output Schemas

| File | Validates | Path |
|------|-----------|------|
| `simulation_history.schema.json` | Per-epoch simulation state | `telemetry_buffer/simulation_history.json` |
| `lab_notebook.schema.json` | Diagnostic records & audit | `telemetry_buffer/artificial_lab_notebook.json` |

## Usage

Validate a config file against its schema (requires `jsonschema` or `check-jsonschema`):

```bash
pip install check-jsonschema

# Validate pathogen profiles
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json

# Validate spatial layout
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/destroyer_baseline/spatial_layout.json
```

For pre-run validation with pydantic models and cross-file referential integrity
checking, use the sanity checker instead:

```bash
python tools/sanity_checker.py
```
