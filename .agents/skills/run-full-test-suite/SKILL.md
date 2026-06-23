---
name: run-full-test-suite
description: Run the complete Crusher-to-the-Bridge pytest suite including data contracts, sanity checks, orchestrator tests, law compliance, and all module tests. Use before creating PRs or after any code change.
---

# Run Full Test Suite

## Prerequisites

- Python 3.11+ with dependencies from `requirements.txt` installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None — all tests run locally.

## Quick Commands

### Run the entire test suite
```bash
python3 -m pytest tests/ -v --tb=short
```
Expected: ~574 tests pass in ~9s.

### Run with coverage reporting
```bash
python3 -m pytest tests/ -v --tb=short --cov --cov-report=term-missing
```
Coverage sources: `engines/`, `crusher_labs/`, `picard_framework/`, `decision_engine/`, `orchestrator_*.py`.

### Run ruff lint (advisory, non-blocking)
```bash
ruff check --select E,F,W,I --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ orchestrator*.py presidio_runner.py
```
Expected: ~65 findings (mostly import ordering). This is advisory — `continue-on-error: true` in CI.

### Run individual test modules
```bash
# Data contract validation (pathogen profiles, spatial layout, airflow, protocols, resource costs)
python3 -m pytest tests/test_data_contracts.py -v --tb=short

# JSON schema validation (all platforms, social configs, fleet configs)
python3 -m pytest tests/test_json_schema_validation.py -v --tb=short

# Sanity checker (pydantic model validation + referential integrity)
python3 -m pytest tests/test_sanity_checker.py -v --tb=short

# Orchestrator integration tests (quarantine, SOP confinement, zone closures)
python3 -m pytest tests/test_orchestrator.py -v --tb=short

# Infection counters and exempt_classes confinement
python3 -m pytest tests/test_infection_counters.py -v --tb=short

# CONTAM physics (HVAC mass-balance, ACH, filter efficiency, natural decay)
python3 -m pytest tests/test_py_contam_bridge.py -v --tb=short

# Golden Picard parity (ShipSimulation vs orchestrator SIR comparison)
python3 -m pytest tests/test_golden_picard.py -v --tb=short

# Transmission core + infection dynamics (dose-response, shedding, multi-pathway)
python3 -m pytest tests/test_transmission_infection_expanded.py -v --tb=short

# Food/environmental transmission pools
python3 -m pytest tests/test_transmission_pathways.py -v --tb=short

# Dashboard extended (spatial_viz, deck_geometry, pydeck, fleet_viz, theme)
python3 -m pytest tests/test_dashboard_extended.py -v --tb=short

# Dashboard import and pathway aggregation
python3 -m pytest tests/test_dashboard.py -v --tb=short

# Scripts and GIS tools (blueprint, resolve_column, group_hvac_zones)
python3 -m pytest tests/test_scripts_tools.py -v --tb=short

# Crusher Labs modalities (fidelity, lab_notebook, RDT, sequencing, PCR)
python3 -m pytest tests/test_crusher_labs_modalities.py -v --tb=short

# Protocol engine (stoplight evaluation, SOP activation)
python3 -m pytest tests/test_protocol_engine.py -v --tb=short

# Cost ledger (budget, labor, materials, OIS)
python3 -m pytest tests/test_cost_ledger.py tests/test_operational_impact.py -v --tb=short

# Action envelopes & behavioral syndromic (Picard / Stackelberg)
python3 -m pytest tests/test_action_applier.py tests/test_behavioral_syndromic.py -v --tb=short

# Law compliance (architectural invariants, extended to picard_framework/crusher_labs/decision_engine)
python3 -m pytest tests/test_law_compliance.py -v --tb=short

# Picard / Presidio / Stackelberg
python3 -m pytest tests/test_picard_framework.py tests/test_decision_engine.py \
  tests/test_presidio_runner.py tests/test_stackelberg.py tests/test_golden_orchestrator.py -v --tb=short

# Telemetry seams (ground truth read/write)
python3 -m pytest tests/test_telemetry_seams.py -v --tb=short

# Agent axes (orthogonal infection/presentation/compliance)
python3 -m pytest tests/test_agent_axes.py -v --tb=short

# Enterprise platform referential integrity
python3 -m pytest tests/test_enterprise_platforms.py -v --tb=short

# Sequencing config wiring (read_depth from config.yaml)
python3 -m pytest tests/test_sequencing_config.py -v --tb=short

# Per-test cost accounting telemetry
python3 -m pytest tests/test_cost_accounting.py -v --tb=short

# Schema module (JSON schema validation)
python3 -m pytest tests/test_schema_module.py -v --tb=short
```

### Run the sanity checker directly (CLI)
```bash
python3 tools/sanity_checker.py --from-config
```
Expected: All checks pass with no ERROR findings.

### Run the orchestrator smoke test
```bash
python3 orchestrator.py && \
python3 -c "import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c; print(f'OIS cumulative: {c[\"operational_impact_cumulative\"]}')"
```
Expected: 24-epoch run completes; final epoch includes OIS fields.

## CI Pipeline Equivalence

The full CI pipeline (`.github/workflows/ci.yml`) runs these steps in order:
1. `pip install -r requirements.txt`
2. `python3 tools/sanity_checker.py --from-config` — config validation
3. `ruff check ...` — static analysis (advisory, `continue-on-error: true`)
4. `pytest tests/test_json_schema_validation.py -v --tb=short` — JSON schema validation
5. `pytest tests/ -v --tb=short --cov --cov-report=term-missing` — full suite with coverage (~574 tests)
6. Picard/Presidio/Stackelberg import hygiene
7. Presidio smoke (`presidio_runner.py` smoke fleet)
8. Long-read / TAT targeted tests
9. Orchestrator import hygiene (split modules, stoplights, long-read/TAT)
10. Dashboard import check (LCARS package, `apply_lcars_layout`)
11. `python3 orchestrator.py` — 24-epoch smoke test
12. OIS fields present in final `cost_accounting`

Framework-focused CI (`.github/workflows/picard-presidio.yml`) additionally runs a pytest slice, Stackelberg schema checks, and all-platform JSON schema validation.

To replicate main CI locally:
```bash
pip install -r requirements.txt && \
python3 tools/sanity_checker.py --from-config && \
ruff check --select E,F,W,I --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ orchestrator*.py || true && \
python3 -m pytest tests/ -v --tb=short --cov --cov-report=term-missing && \
python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1 && \
python3 orchestrator.py && \
python3 -c "import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c"
```

## Test Coverage Map

| Test File | Tests | Module(s) Tested | Focus |
|-----------|-------|-----------------|-------|
| `test_py_contam_bridge.py` | 19 | `engines/py_contam_bridge.py` | HVAC mass conservation, ACH, filter efficiency, decay, path construction |
| `test_json_schema_validation.py` | 28 | `schemas/*.schema.json` | All platform, social, fleet JSON files validated against schemas |
| `test_golden_picard.py` | 3 | `picard_framework/`, `orchestrator.py` | Golden SIR parity, cost accounting, Picard vs orchestrator |
| `test_dashboard_extended.py` | 20 | `dashboard/` | zone_metric, color_scale, lcars_rgba, theme, fleet_viz, spatial_viz |
| `test_scripts_tools.py` | 14 | `scripts/`, `tools/gis_spatial_bridge.py` | Blueprint shapes, resolve_column, group_hvac_zones, imports |
| `test_crusher_labs_modalities.py` | 19 | `crusher_labs/modalities/` | Fidelity tiers, lab_notebook, RDT, sequencing CLR, PCR Ct |
| `test_transmission_infection_expanded.py` | 27 | `engines/transmission_core.py`, `engines/infection_dynamics_bridge.py` | Dose-response, shedding, KorkinAgent lifecycle, multi-pathway |
| `test_law_compliance.py` | 20 | All modules | Laws 1-6, extended to picard_framework/, crusher_labs/, decision_engine/ |
| `test_data_contracts.py` | 25 | JSON config files | Schema conformance, uniqueness, bounds |
| `test_sanity_checker.py` | 1 | `tools/sanity_checker.py` | Pydantic validation, referential integrity |
| `test_orchestrator.py` | varies | `orchestrator*.py` | End-to-end simulation flow, quarantine/SOP |
| `test_infection_counters.py` | varies | `orchestrator_epoch.py` | Attack-rate counters, thresholds, exempt_classes |
| `test_transmission_pathways.py` | varies | `engines/transmission_core.py` | Food/environmental pool initialization |
| `test_dashboard.py` | varies | `dashboard.py` | LCARS dashboard imports, pathway aggregation |
| `test_protocol_engine.py` | varies | `crusher_labs/protocol_engine.py` | Stoplight triggers, SOP activation, modifiers |
| `test_stoplight.py` | varies | `crusher_labs/stoplight.py` | Ct-to-stoplight mapping, threshold logic |
| `test_cost_ledger.py` | varies | `crusher_labs/cost_ledger.py` | Budget tracking, material deductions, OIS |
| `test_operational_impact.py` | varies | `crusher_labs/cost_ledger.py` | OIS weight computation |
| `test_action_applier.py` | varies | `action_applier.py` | Executable action kinds |
| `test_behavioral_syndromic.py` | varies | `syndromic.py` | Layer-1 sick-call / compliance |
| `test_telemetry_seams.py` | varies | `telemetry_buffer/schema.py` | Ground truth serialization round-trip |
| `test_cost_accounting.py` | varies | `orchestrator_record.py` | Per-test debits and materials telemetry |
| `test_agent_axes.py` | varies | `telemetry_buffer/agent_axes.py` | Orthogonal infection/presentation/compliance |
| `test_enterprise_platforms.py` | varies | `data/platforms/enterprise_*` | Enterprise HVAC referential integrity |
| `test_sequencing_config.py` | varies | `crusher_labs/__init__.py` | Read-depth wiring from config.yaml |
| `test_schema_module.py` | varies | `telemetry_buffer/schema.py` | JSON schema output validation |
| `test_wearable_enhanced.py` | 38 | `engines/wearable_monitor.py`, `crusher_labs/modalities/wearable.py` | Multi-device, coverage, visibility, confounders, detection profiles, chronic disease devices, glucose channel, config parsing |
| `test_wearable_anomaly_scorer.py` | 8 | `engines/wearable_anomaly_scorer.py`, `crusher_labs/cascade_entry.py` | Confounder template matching, fleet downweighting, `infection_score`, cascade entry fusion |
| `test_cascade_entry.py` | 6 | `crusher_labs/cascade_entry.py`, `crusher_labs/diagnostic_cascade.py` | Sick-call Tier 1 vs wearable Tier 0, `infection_score` alert rules, device fusion |

## Golden Test Values

Seed-42 / 24-epoch destroyer baseline (epoch 23), current `main` lineage
(cascade entry + clinical correlation + pathogen overrides):

| Metric | Expected (epoch 23) |
|--------|-------------------|
| Susceptible | 6 |
| Infected | 0 |
| Symptomatic | 0 |
| Recovered | 10 |
| Immune | 4 |
| Trigger status | CONFIRMED |
| Total financial USD | 2035.0 |
| OIS cumulative | ~313.4 |

Golden totals can shift when observation, cascade, or pathogen wiring changes;
update `tests/test_golden_orchestrator.py` and `tests/test_golden_picard.py`
after intentional epidemiological changes.
