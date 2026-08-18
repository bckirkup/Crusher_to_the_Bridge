---
name: picard-ship-simulation
description: Run and develop Picard_Framework ship-level steppable simulations. Use after modifying picard_framework/, ShipSimulation, PicardRunSpec, or orchestrator integration.
---

# Picard Ship Simulation

## Prerequisites

- Python 3.11+, repo root on `PYTHONPATH`
- `pip install --only-binary=:all: --require-hashes -r requirements.lock.txt` (or `requirements.txt` for editable local work)

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
| `picard_framework/simulation/ship_simulation.py` | `ShipSimulation.step()` orchestrates `_begin_epoch` plus `_step_*` phases on `_EpochWork` (split Stackelberg when `social` enabled) |
| `picard_framework/simulation/action_applier.py` | Maps `ActionEnvelope` → `SimulationState` via `_ACTION_HANDLERS` / `_NEEDS_CTX` |
| `picard_framework/runs/*.json` | Ship run specifications |
| `data/` | Shared platform, pathogen, protocol libraries |

## Transmission / behavior knobs (`crusher_labs/config.yaml`)

| Block | Role |
|-------|------|
| `transmission.contact_mode` | `density_dependent` (default), `legacy`, or opt-in `heterogeneous_zone_dose` — see `docs/density_contact_spec.md` |
| `agent_behavior` | Dining/free rotation probabilities (default `0.0` for golden stability) — see `docs/multi_pathogen_model_changes_spec.md` |

Pathogen profiles may include `transmission_route_weights`, formal `dose_adjustment`
(log10 shedding offset), `innate_nonsusceptible_fraction`, and zone-scoped
`environmental_contamination.source_zones`.

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_picard_framework.py tests/test_golden_orchestrator.py \
  tests/test_golden_picard.py tests/test_ship_epoch_helpers.py \
  tests/test_shedding_variance_cabin_mates.py tests/test_action_applier.py \
  tests/test_density_contact.py tests/test_multi_pathogen_model_phase_a.py \
  tests/test_multi_pathogen_model_phase_b.py -v
```

Epoch **semantic** order: [docs/simulation_step_order.md](../../../docs/simulation_step_order.md).
Do not reorder phases when extracting; golden Picard is the behavior lock.
`tests/test_ship_epoch_helpers.py` grades `_merge_applied` and belief
clamping. Unknown action kinds and `_NEEDS_CTX` kinds with `ctx is None`
are no-ops.
