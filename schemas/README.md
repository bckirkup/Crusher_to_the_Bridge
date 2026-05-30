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


## Picard / Presidio / Stackelberg Schemas

| File | Validates | Path |
|------|-----------|------|
| `picard_run_spec.schema.json` | Picard cruise run spec | `picard_framework/runs/*.json` |
| `presidio_fleet_config.schema.json` | Presidio fleet config | `presidio/data/config/*.json` |
| `presidio_fleet_economics.schema.json` | Fleet reward weights | `presidio/data/economics/fleet_economics.json` |
| `information_diffusion.schema.json` | Belief propagation params | `presidio/data/social/information_diffusion_default.json` |
| `class_interactions.schema.json` | Class-pair zone weights | `presidio/data/social/class_interactions_default.json` |
| `global_health_briefing.schema.json` | Epoch briefings | `presidio/data/intelligence/global_health_timeline.json` |
| `agent_profile.schema.json` | Agent profile bundle | `picard_framework/data/agent_profiles/*.json` |
| `utility_observation_bundle.schema.json` | Exported utility JSON | External optimizer input |
| `decision_action.schema.json` | Action envelopes | External optimizer output |

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
