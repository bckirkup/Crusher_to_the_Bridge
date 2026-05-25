---
name: run-full-test-suite
description: Run the complete Crusher-to-the-Bridge pytest suite including data contracts, sanity checks, orchestrator tests, law compliance, and all module tests. Use before creating PRs or after any code change.
---

# Run Full Test Suite

## Prerequisites

- Python 3.11+ with pydantic, numpy, pyyaml, and pytest installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None — all tests run locally.

## Quick Commands

### Run the entire test suite
```bash
python -m pytest tests/ -v --tb=short
```
Expected: All tests pass. Current test files cover data contracts, sanity checker, orchestrator, protocol engine, stoplight, cost ledger, telemetry seams, schema module, and law compliance.

### Run individual test modules
```bash
# Data contract validation (pathogen profiles, spatial layout, airflow, protocols, resource costs)
python -m pytest tests/test_data_contracts.py -v --tb=short

# Sanity checker (pydantic model validation + referential integrity)
python -m pytest tests/test_sanity_checker.py -v --tb=short

# Orchestrator integration tests
python -m pytest tests/test_orchestrator.py -v --tb=short

# Protocol engine (stoplight evaluation, SOP activation)
python -m pytest tests/test_protocol_engine.py -v --tb=short

# Stoplight logic
python -m pytest tests/test_stoplight.py -v --tb=short

# Cost ledger (budget, labor, materials)
python -m pytest tests/test_cost_ledger.py -v --tb=short

# Law compliance (architectural invariants enforcement)
python -m pytest tests/test_law_compliance.py -v --tb=short

# Telemetry seams (ground truth read/write)
python -m pytest tests/test_telemetry_seams.py -v --tb=short

# Schema module (JSON schema validation)
python -m pytest tests/test_schema_module.py -v --tb=short
```

### Run the sanity checker directly (CLI)
```bash
python tools/sanity_checker.py
```
Expected: All checks pass with no ERROR findings.

### Run the orchestrator smoke test
```bash
python orchestrator.py
```
Expected: 24-epoch run completes with no exceptions.

## CI Pipeline Equivalence

The full CI pipeline (`.github/workflows/ci.yml`) runs these steps in order:
1. `python tools/sanity_checker.py` — config validation
2. `pytest tests/ -v --tb=short` — full test suite
3. Import hygiene check — verifies module split
4. `python orchestrator.py` — 24-epoch smoke test

To replicate CI locally:
```bash
python tools/sanity_checker.py && \
python -m pytest tests/ -v --tb=short && \
PYTHONPATH=. python -c "
from crusher_labs.stoplight import stoplight_from_ct, meets_threshold
from crusher_labs.protocol_engine import compute_stoplights
from crusher_labs.lab_notebook import _stoplight_from_ct
from orchestrator_types import SimulationState, ObservationEngine, ProtocolContext
from orchestrator_init import initialize_ship_graph, build_engine
from orchestrator_epoch import sync_vsp_isolation, step_fred_compliance, run_observation_sampling
from orchestrator_record import record_epoch, finalize_simulation
from orchestrator_display import print_executive_summary
print('Import hygiene OK')
" && \
python orchestrator.py
```

## Test Coverage Map

| Test File | Module(s) Tested | Focus |
|-----------|-----------------|-------|
| `test_data_contracts.py` | JSON config files | Schema conformance, uniqueness, bounds |
| `test_sanity_checker.py` | `tools/sanity_checker.py` | Pydantic validation, referential integrity |
| `test_orchestrator.py` | `orchestrator*.py` | End-to-end simulation flow |
| `test_protocol_engine.py` | `crusher_labs/protocol_engine.py` | Stoplight triggers, SOP activation, modifiers |
| `test_stoplight.py` | `crusher_labs/stoplight.py` | Ct-to-stoplight mapping, threshold logic |
| `test_cost_ledger.py` | `crusher_labs/cost_ledger.py` | Budget tracking, material deductions |
| `test_law_compliance.py` | All modules | Architectural law invariants (Laws 1-6) |
| `test_telemetry_seams.py` | `telemetry_buffer/schema.py` | Ground truth serialization round-trip |
| `test_schema_module.py` | `telemetry_buffer/schema.py` | JSON schema output validation |
