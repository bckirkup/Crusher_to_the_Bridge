---
name: picard-ship-simulation
description: Run and develop Picard_Framework ship-level steppable simulations. Use after modifying picard_framework/, ShipSimulation, PicardRunSpec, or orchestrator integration.
---

# Picard Ship Simulation

## Prerequisites

- Python 3.11+, repo root on `PYTHONPATH`
- `pip install -r requirements.txt`

## Quick commands

```bash
# Legacy CLI (uses Picard ShipSimulation internally)
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py --epochs 24

# Programmatic steppable API
python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_legacy_yaml('.')
sim = ShipSimulation(spec, display=False)
sim.run(n_epochs=2)
sim.finalize(display=False)
"

# Picard run spec JSON
python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_picard_json('.', 'picard_framework/runs/smoke_2epoch.json')
ShipSimulation(spec).run()
"
```

## Layout

| Path | Role |
|------|------|
| `picard_framework/run_spec.py` | Immutable `PicardRunSpec` |
| `picard_framework/catalog/` | Platform/pathogen library index |
| `picard_framework/simulation/ship_simulation.py` | `ShipSimulation.step()` / `run()` (split Stackelberg when `social` enabled) |
| `picard_framework/simulation/action_applier.py` | Maps `ActionEnvelope` → `SimulationState` |
| `picard_framework/runs/*.json` | Ship run specifications |
| `data/` | Shared platform, pathogen, protocol libraries |

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_picard_framework.py tests/test_golden_orchestrator.py \
  tests/test_action_applier.py -v
```

Epoch order: [docs/simulation_step_order.md](../../docs/simulation_step_order.md)
