---
name: orchestrator-smoke-test
description: Run the Crusher-to-the-Bridge orchestrator for a quick 24-epoch smoke test to verify the full simulation loop. Use after modifying orchestrator modules, engines, transmission core, or config.yaml.
---

# Orchestrator Smoke Test

## Prerequisites

- Python 3.11+ with numpy, pyyaml, and pydantic installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None — the orchestrator runs locally against bundled config and data files.

## Quick Commands

### Run the default 24-epoch smoke test
```bash
python orchestrator.py
```
Expected: Completes 24 epochs with no exceptions. Prints `CRUSHER TO THE BRIDGE` banner, per-epoch progress, and an executive summary at the end.

### Run with a custom epoch count
```bash
python orchestrator.py --epochs 10
```
Expected: Completes 10 epochs. Useful for faster iteration during development.

### Verify import hygiene after module changes
```bash
PYTHONPATH=. python -c "
from crusher_labs.stoplight import stoplight_from_ct, meets_threshold
from crusher_labs.protocol_engine import compute_stoplights
from crusher_labs.lab_notebook import _stoplight_from_ct
from orchestrator_types import SimulationState, ObservationEngine, ProtocolContext
from orchestrator_init import initialize_ship_graph, build_engine
from orchestrator_epoch import sync_vsp_isolation, step_fred_compliance, run_observation_sampling
from orchestrator_record import record_epoch, finalize_simulation
from orchestrator_display import print_executive_summary
print('Import hygiene OK: modules split correctly, stoplight canonical')
"
```
Expected: Prints success message with no ImportError.

## What the Smoke Test Validates

| Area | What It Checks |
|------|----------------|
| Initialization | Ship graph loads from `spatial_layout.json`, engine builds from config, pathogen profiles parsed |
| CONTAM Bridge | `py_contam_bridge.build_transport_engine()` succeeds (or gracefully returns None) |
| Multi-Pathogen | All pathogens in `active_profiles.json` initialize with valid dose-response params |
| Epoch Loop | Transmission core, observation sampling, protocol evaluation, cost accounting all execute |
| Finalization | `simulation_history.json` and `artificial_lab_notebook.json` written to `telemetry_buffer/` |

## Output Files

| File | Location |
|------|----------|
| Simulation History | `telemetry_buffer/simulation_history.json` |
| Lab Notebook | `telemetry_buffer/artificial_lab_notebook.json` |

## Troubleshooting

- **ModuleNotFoundError**: Ensure `PYTHONPATH` includes the repo root, or run from the repo root.
- **FileNotFoundError on spatial_layout.json**: Verify `data/platforms/destroyer_baseline/` exists and contains `spatial_layout.json`.
- **numpy/pydantic not found**: Run `pip install numpy pyyaml pydantic`.
