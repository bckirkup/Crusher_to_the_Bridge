---
name: testing-data-contracts
description: Test and validate Crusher to the Bridge data contracts (JSON configs, schemas, referential integrity). Use when modifying or adding config files, platforms, pathogens, protocols, or resource costs.
---

# Testing Data Contracts

## Prerequisites

- Python 3.11+ with pydantic installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None — all data contract tests run locally against JSON files in the repo.

## Quick Commands

### Run all data contract tests
```bash
python -m pytest tests/test_data_contracts.py -v --tb=short
```
Expected: 25+ tests pass. Validates pathogen profiles, spatial layout, air flow paths, protocols, resource costs, long-read params, and instrument TAT.

### Run sanity checker tests
```bash
python -m pytest tests/test_sanity_checker.py -v --tb=short
```
Expected: 40 tests pass. Runs the full sanity checker programmatically against default configs.

### Run sanity checker directly (CLI)
```bash
python tools/sanity_checker.py
```
Or with custom paths:
```bash
python tools/sanity_checker.py --config-dir data/config \
    --platform-dir data/platforms/destroyer_baseline \
    --pathogen-dir data/pathogens
```
Expected: All checks pass with no ERROR findings.

### Run both together
```bash
python -m pytest tests/test_data_contracts.py tests/test_sanity_checker.py -v --tb=short
```
Expected: 67 tests pass in ~0.5s.

## Data File Locations

| Category | Path | Description |
|----------|------|-------------|
| Pathogens | `data/pathogens/active_profiles.json` | Active pathogen profiles (norwalk_gi, sars_cov2_resp) |
| Pathogens (Edison) | `data/pathogens/edison_10pathogen_profiles.json` | Extended 10-pathogen profiles |
| Spatial Layout | `data/platforms/<platform>/spatial_layout.json` | Zone definitions per platform |
| Air Flow Paths | `data/platforms/<platform>/air_flow_paths.json` | HVAC zones, cross-zone links, adjacency |
| Protocols | `data/config/protocols.json` | SOP definitions (SOP-001 through SOP-016) |
| Diagnostic cascade | `data/config/diagnostic_cascade.json`, `diagnostic_cascade_multiplex.json` | Tier definitions, `cascade_entry` (sick-call Tier 1, wearable `infection_score` Tier 0) |
| Resource Costs | `data/config/resource_costs.json` | Budget, labor, material inventory |
| Logging Profile | `data/config/logging_profile.json` | Observation engine logging config |
| Instrument TAT | `data/config/instrument_turnaround.json` | Per-instrument delivery delay (epochs) |
| Long-read params | `data/config/long_read_sequencing_params.json` | Nanopore deployment profiles & detection |
| Microbiome | `data/microbiome_profiles/*.json` | Coastal/ocean profiles, zone type modifiers |

### Available Platforms

- `mega_cruise_5000` — Default platform used by orchestrator (`config.yaml`)
- `destroyer_baseline` — Gleaves-class destroyer (6 zones)
- `enterprise_constitution_tos` — Constitution-class (fiction-adapted, 13 zones)
- `enterprise_galaxy_tng` — Galaxy-class (fiction-adapted, 17 zones)
- `expedition_cruise_300` (legacy)
- `expedition_cruise_450`
- `classic_cruise_1900`
- `spirit_cruise_3000`
- `mega_cruise_5000`
- `fletcher_class_destroyer`
- `legend_class_nsc`
- `mega_cruise_5000`
- `messy_cruise_500` (legacy archived berthing)
- `san_antonio_class_lpd`

Enterprise scenario bundles: `data/templates/enterprise_constitution_tos.json`, `data/templates/enterprise_galaxy_tng.json`.
Run `python3 -m pytest tests/test_enterprise_platforms.py -v` after editing Enterprise platforms or templates.

## Schema Files

JSON schemas live in `schemas/`:

| Schema | Validates |
|--------|-----------|
| `spatial_layout.schema.json` | Zone structure, volumes, display coords, `graywater_zones`, `cabin_size`, `cabin_ventilation_type`, `dining_service_type`, `food_contamination_multiplier`, `max_occupancy` |
| `air_flow_paths.schema.json` | HVAC zones, cross-zone links, adjacency |
| `protocols.schema.json` | SOP trigger/modifier/cost structure |
| `resource_costs.schema.json` | Budget and material inventory |
| `pathogen_profiles.schema.json` | Pathogen profiles (incl. `shedding_variance_log10`, `transmission_route_weights`, `dose_adjustment`, `innate_nonsusceptible_fraction`, env `source_zones`) |
| `simulation_history.schema.json` | Output epoch record structure |
| `lab_notebook.schema.json` | Observation engine log records |
| `logging_profile.schema.json` | Logging configuration |

## What Each Test Class Validates

### `test_data_contracts.py`

| Test Class | Tests | What It Checks |
|------------|-------|-----------------|
| `TestPathogenProfiles` | 6 | Has pathogens key, required fields present, unique IDs, dose_response alpha/beta > 0, shedding_curve non-empty, transmission routes valid |
| `TestSpatialLayout` | 4 | Has zones, unique zone IDs, positive volumes, display coordinates present |
| `TestAirFlowPaths` | 4 | HVAC zone rooms reference valid zones, cross-zone links reference valid HVAC zones, adjacency edges reference valid zones, flow rates non-negative |
| `TestProtocols` | 3 | Has protocols key, unique protocol IDs, valid stoplight levels (GREEN/AMBER/RED) |
| `TestResourceCosts` | 4 | Positive starting budget, positive labor capacity, material inventory non-empty, non-negative unit costs and starting counts |
| `TestLongReadSequencingParams` | 2 | Deployment profiles present, detection and turnaround blocks |
| `TestInstrumentTurnaroundConfig` | 2 | Instrument keys present, non-negative delay_epochs |

### `test_sanity_checker.py`

| Test | What It Checks |
|------|-----------------|
| `test_default_configs_pass_sanity_checks` | Runs `tools/sanity_checker.run_checks()` programmatically against default config/platform/pathogen dirs. Fails if any ERROR-severity finding is reported. |

## Sanity Checker (`tools/sanity_checker.py`)

The sanity checker uses **pydantic models** for strict structural validation beyond what JSON Schema alone catches:

- **Mathematical bounds**: `volume_m3 > 0`, `ach >= 0`, `flow_rate_m3h >= 0`, `financial_usd >= 0`, `surface_deposition_fraction in [0,1]`, `base_susceptibility >= 0`
- **Graph referential integrity**: HVAC zone rooms must reference valid spatial zones, cross-zone links must reference valid HVAC zones, adjacency edges must reference valid spatial zones
- **Logical contradictions**: Dose-response model parameters validated (beta_poisson requires alpha+beta > 0, exponential requires k > 0)
- **Protocol structure**: Valid stoplight levels, non-negative costs and labor

## Testing Tips

- **When adding a new platform**: Create `spatial_layout.json` and `air_flow_paths.json` under `data/platforms/<new_platform>/`. Run `python tools/sanity_checker.py --platform-dir data/platforms/<new_platform>` to validate. Also add targeted data contract tests if the platform has unusual properties.
- **When adding a new pathogen**: Add to `data/pathogens/active_profiles.json`. Required fields: `pathogen_id`, `name`, `transmission_routes`. Optional: `shedding_variance_log10`, `transmission_route_weights`, `dose_adjustment` (log10 shedding offset), `innate_nonsusceptible_fraction`, env `source_zones` (see `docs/SHEDDING_AND_CABINMATES.md`, `docs/multi_pathogen_model_changes_spec.md`). Run `pytest tests/test_data_contracts.py::TestPathogenProfiles -v` and Phase A/B tests as needed.
- **When modifying protocols**: After editing `data/config/protocols.json`, run `pytest tests/test_data_contracts.py::TestProtocols -v` and `pytest tests/test_law_compliance.py::TestLaw5ReferentialIntegrity -v` to verify protocol instrument classes and stoplight levels are valid. For `min_escalation_status` / `activation_delay_epochs` changes, also run `pytest tests/test_outbreak_response_architecture.py -v`.
- **Valid escalation statuses** (SOP `min_escalation_status`): `BASELINE`, `ALERT`, `SUSPECTED`, `CONFIRMED`, `LOCKDOWN`.
- **Cross-file referential integrity** is critical: air_flow_paths references zone IDs from spatial_layout, protocols reference instrument classes from the observation engine, resource_costs materials are referenced by protocol costs. The sanity checker catches most of these.
- **Valid transmission routes**: `direct_contact`, `fomite`, `droplet`, `hvac_airborne`, `water_aerosol`, `food`, `water`, `bodily_fluids`.
- **Valid stoplight levels**: `GREEN`, `AMBER`, `RED`.
- **The sanity checker is the most comprehensive validator** — it uses pydantic models that go beyond the JSON schema checks. Always run it after config changes.
