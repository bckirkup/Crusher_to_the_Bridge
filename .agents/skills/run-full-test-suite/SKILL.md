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
python -m pytest tests/ -v --tb=short
```
Expected: All tests pass (~337). Coverage includes data contracts, sanity checker, orchestrator, protocol engine, stoplight, cost ledger, OIS, action applier, behavioral syndromic, long-read sequencing, instrument TAT, telemetry seams, schema module, law compliance, infection counters, transmission pathways (food/environmental), agent axes, enterprise platforms, sequencing config, cost accounting, and dashboard helpers.

### Run individual test modules
```bash
# Data contract validation (pathogen profiles, spatial layout, airflow, protocols, resource costs)
python -m pytest tests/test_data_contracts.py -v --tb=short

# Sanity checker (pydantic model validation + referential integrity)
python -m pytest tests/test_sanity_checker.py -v --tb=short

# Orchestrator integration tests (quarantine, SOP confinement, zone closures)
python -m pytest tests/test_orchestrator.py -v --tb=short

# Infection counters and exempt_classes confinement (PR #45, #44)
python -m pytest tests/test_infection_counters.py -v --tb=short

# Food/environmental transmission pools (PR #43)
python -m pytest tests/test_transmission_pathways.py -v --tb=short

# Dashboard import and pathway aggregation (PR #46)
python -m pytest tests/test_dashboard.py -v --tb=short

# Protocol engine (stoplight evaluation, SOP activation)
python -m pytest tests/test_protocol_engine.py -v --tb=short

# Stoplight logic
python -m pytest tests/test_stoplight.py -v --tb=short

# Cost ledger (budget, labor, materials, OIS)
python -m pytest tests/test_cost_ledger.py tests/test_operational_impact.py -v --tb=short

# Action envelopes & behavioral syndromic (Picard / Stackelberg)
python -m pytest tests/test_action_applier.py tests/test_behavioral_syndromic.py -v --tb=short

# Law compliance (architectural invariants enforcement)
python -m pytest tests/test_law_compliance.py -v --tb=short

# Picard / Presidio / Stackelberg
python -m pytest tests/test_picard_framework.py tests/test_decision_engine.py \
  tests/test_presidio_runner.py tests/test_stackelberg.py tests/test_golden_orchestrator.py -v --tb=short

# Telemetry seams (ground truth read/write)
python -m pytest tests/test_telemetry_seams.py -v --tb=short

# Agent axes (orthogonal infection/presentation/compliance)
python -m pytest tests/test_agent_axes.py -v --tb=short

# Enterprise platform referential integrity
python -m pytest tests/test_enterprise_platforms.py -v --tb=short

# Sequencing config wiring (read_depth from config.yaml)
python -m pytest tests/test_sequencing_config.py -v --tb=short

# Per-test cost accounting telemetry
python -m pytest tests/test_cost_accounting.py -v --tb=short

# Schema module (JSON schema validation)
python -m pytest tests/test_schema_module.py -v --tb=short
```

### Run the sanity checker directly (CLI)
```bash
python tools/sanity_checker.py --from-config
```
Expected: All checks pass with no ERROR findings.

### Run the orchestrator smoke test
```bash
PYTHONPATH=. python -c "
from picard_framework import PicardRunSpec, ShipSimulation
from decision_engine import StackelbergRound, DecisionRuntime
import presidio_runner
print('Picard/Presidio OK')
" && \
python presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1 && \
python orchestrator.py && \
python -c "import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c"
```
Expected: 24-epoch run completes with no exceptions; final epoch includes OIS fields.

## CI Pipeline Equivalence

The full CI pipeline (`.github/workflows/ci.yml`) runs these steps in order:
1. `pip install -r requirements.txt`
2. `python tools/sanity_checker.py --from-config` — config validation from `crusher_labs/config.yaml`
3. `pytest tests/ -v --tb=short` — full test suite (~337 tests)
4. Picard/Presidio/Stackelberg import hygiene
5. Presidio smoke (`presidio_runner.py` smoke fleet)
6. Long-read / TAT targeted tests — `test_long_read_sequencing`, `test_instrument_turnaround`, observation init
7. Orchestrator import hygiene — split modules, stoplights, long-read/TAT imports
8. Dashboard import check — LCARS package, pathway aggregation, `apply_lcars_layout`
9. `python orchestrator.py` — 24-epoch smoke test
10. OIS fields present in final `cost_accounting`

Framework-focused CI (`.github/workflows/picard-presidio.yml`) additionally runs a pytest slice, Stackelberg schema checks, and all-platform JSON schema validation on `cursor/**` branches.

To replicate main CI locally:
```bash
pip install -r requirements.txt && \
python tools/sanity_checker.py --from-config && \
python -m pytest tests/ -v --tb=short && \
PYTHONPATH=. python -c "
from picard_framework import PicardRunSpec, ShipSimulation
from presidio import PresidioRunSpec
from decision_engine import DecisionRound, ExperienceStore, StackelbergRound, DecisionRuntime
from decision_engine.policy import ThresholdBeliefPolicy, CommandThresholdPolicy, build_policies_from_config
from crusher_labs.cost_ledger import compute_operational_impact
import presidio_runner
print('Picard/Presidio/Stackelberg import hygiene OK')
" && \
python presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1 && \
python -m pytest tests/test_long_read_sequencing.py tests/test_instrument_turnaround.py \
  tests/test_sequencing_config.py::test_init_observation_engine_turnaround_and_long_read -v --tb=short && \
PYTHONPATH=. python -c "
from crusher_labs.stoplight import stoplight_from_ct, meets_threshold, stoplight_from_long_read_verification
from crusher_labs.protocol_engine import compute_stoplights
from crusher_labs.lab_notebook import _stoplight_from_ct
from crusher_labs.instrument_turnaround import InstrumentTurnaroundQueue, InstrumentTurnaroundRegistry
from crusher_labs.modalities.long_read_sequencing import LongReadNanoporeSequencing
from crusher_labs.long_read_escalation import collect_long_read_escalation_requests, is_long_read_enabled
from orchestrator_types import SimulationState, ObservationEngine, ProtocolContext
from orchestrator_init import initialize_ship_graph, build_engine, init_observation_engine
from orchestrator_epoch import sync_vsp_isolation, step_fred_compliance, run_observation_sampling, confine_all_agents, apply_surface_decontamination, apply_zone_closures
from orchestrator_record import record_epoch, finalize_simulation
from orchestrator_display import print_executive_summary
print('Import hygiene OK')
" && \
PYTHONPATH=. python -c "
import plotly.graph_objects as go
import dashboard
from dashboard import aggregate_transmission_pathway_totals
from dashboard.theme import apply_lcars_layout
fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
apply_lcars_layout(fig, plot_bgcolor='rgba(0,0,0,0.85)', height=200)
print('Dashboard import OK')
" && \
python orchestrator.py && \
python -c \"import json; c=json.load(open('telemetry_buffer/simulation_history.json'))[-1]['cost_accounting']; assert 'operational_impact_cumulative' in c\"
```

## Test Coverage Map

| Test File | Module(s) Tested | Focus |
|-----------|-----------------|-------|
| `test_data_contracts.py` | JSON config files | Schema conformance, uniqueness, bounds |
| `test_sanity_checker.py` | `tools/sanity_checker.py` | Pydantic validation, referential integrity |
| `test_orchestrator.py` | `orchestrator*.py` | End-to-end simulation flow, quarantine/SOP |
| `test_infection_counters.py` | `orchestrator_epoch.py` | Attack-rate counters, thresholds, exempt_classes |
| `test_transmission_pathways.py` | `engines/transmission_core.py` | Food/environmental pool initialization |
| `test_dashboard.py` | `dashboard.py` | LCARS dashboard imports, pathway aggregation |
| `test_protocol_engine.py` | `crusher_labs/protocol_engine.py` | Stoplight triggers, SOP activation, modifiers |
| `test_stoplight.py` | `crusher_labs/stoplight.py` | Ct-to-stoplight mapping, threshold logic |
| `test_cost_ledger.py` | `crusher_labs/cost_ledger.py` | Budget tracking, material deductions, OIS |
| `test_operational_impact.py` | `crusher_labs/cost_ledger.py` | OIS weight computation |
| `test_action_applier.py` | `action_applier.py` | Executable action kinds |
| `test_behavioral_syndromic.py` | `syndromic.py` | Layer-1 sick-call / compliance |
| `test_law_compliance.py` | All modules | Architectural law invariants (Laws 1-6) |
| `test_telemetry_seams.py` | `telemetry_buffer/schema.py` | Ground truth serialization round-trip |
| `test_cost_accounting.py` | `orchestrator_record.py` | Per-test debits and materials telemetry |
| `test_agent_axes.py` | `telemetry_buffer/agent_axes.py` | Orthogonal infection/presentation/compliance |
| `test_enterprise_platforms.py` | `data/platforms/enterprise_*` | Enterprise HVAC referential integrity |
| `test_sequencing_config.py` | `crusher_labs/__init__.py` | Read-depth wiring from config.yaml |
| `test_schema_module.py` | `telemetry_buffer/schema.py` | JSON schema output validation |
