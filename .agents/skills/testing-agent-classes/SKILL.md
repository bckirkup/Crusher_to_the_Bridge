---
name: testing-agent-classes
description: End-to-end test the agent class diversification system. Use after modifying agent initialization, class config, gender distribution, duty zones, or schedule assignments.
---

# Testing Agent Class Diversification

## Prerequisites

- Python 3.11+ with numpy, pyyaml, pydantic installed
- `check-jsonschema` CLI tool (`pip install check-jsonschema`)
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None — all tests run locally.

## Quick Test Commands

### 1. Run orchestrator and verify class/gender initialization
```bash
PYTHONIOENCODING=utf-8 python orchestrator.py --epochs 5
```
Expected: Initialization banner shows all configured agent classes with correct counts and gender split.

**Note:** On Windows, set `PYTHONIOENCODING=utf-8` to avoid Unicode encoding errors with box-drawing characters in the console output.

### 2. Verify agent class counts from output
```bash
python -c "
import json
with open('telemetry_buffer/simulation_history.json') as f:
    history = json.load(f)
agents = history[0]['agents']
class_counts = {}
for a in agents:
    cls = a.get('agent_class', 'MISSING')
    class_counts[cls] = class_counts.get(cls, 0) + 1
for cls in sorted(class_counts):
    print(f'  {cls}: {class_counts[cls]}')
print(f'Total: {sum(class_counts.values())} agents, {len(class_counts)} classes')
"
```
Expected with default config (20 agents): passenger_general=10, passenger_family=2, passenger_elderly=2, crew_general=2, crew_medical=1, crew_engineering=2, crew_galley=1.

### 3. Verify duty zones
```bash
python -c "
import sys; sys.path.insert(0,'.')
from engines.infection_dynamics_bridge import KorkinShipEngine
import yaml
with open('crusher_labs/config.yaml') as f:
    cfg = yaml.safe_load(f)
g = cfg['ship_graph']
n = g['num_agents']
np_ = int(n * g['agent_roles']['passenger_fraction'])
zones = [{'name':'Bridge','type':'Free','capacity':'low'},{'name':'MedBay','type':'Free','capacity':'low'},{'name':'Mess_Hall','type':'Dining','capacity':'high'},{'name':'Engine_Room','type':'Free','capacity':'medium'},{'name':'Galley','type':'Dining','capacity':'high'},{'name':'Berthing','type':'Room','capacity':'medium'}]
engine = KorkinShipEngine(num_passengers=np_, num_crew=n-np_, initial_infected=1, zones=zones, seed=42, agent_classes=g['agent_classes'], gender_distribution=g['gender_distribution'])
for c, s in [('crew_medical','MedBay'),('crew_engineering','Engine'),('crew_galley','Galley')]:
    for a in engine.agents:
        if a.agent_class == c:
            print(f'{c} (agent {a.agent_id}): work_zone={a.work_zone} [{"PASS" if s in a.work_zone else "FAIL"}]')
"
```

### 4. Test SOP exempt_classes (PR #44)
```bash
python -m pytest tests/test_infection_counters.py::TestExemptClassesConfinement -v --tb=short
```

### 5. Schema validation
```bash
check-jsonschema --schemafile schemas/simulation_history.schema.json telemetry_buffer/simulation_history.json
```
Expected: `ok -- validation done`

### 6. Full test suite
```bash
python -m pytest tests/ -v --tb=short
```
Expected: All tests pass (~629). Agent-class behavior is covered in `test_orchestrator.py`, `test_infection_counters.py`, and `test_agent_axes.py`.

## Key Implementation Details

- `simulation_history.json` is a **list** of epoch records (not a dict with an `epochs` key)
- Agent class fractions are in `crusher_labs/config.yaml` under `ship_graph.agent_classes`
- Remainder from fraction rounding is assigned to the first class
- In legacy mode (no agent_classes config), `agent_class` defaults to `passenger_general`/`crew_general`
- `_resolve_zone()` uses **substring matching** (case-insensitive) against available zone names
- Zone names come from `data/platforms/destroyer_baseline/spatial_layout.json` (field `id`, not `name`)
- `exempt_classes` in protocols and infection counters skip confinement for listed agent classes

## Troubleshooting

- **ModuleNotFoundError for engines**: Set `PYTHONPATH=.` or use `sys.path.insert(0, '.')` when running scripts from repo root
- **UnicodeEncodeError on Windows**: Set `PYTHONIOENCODING=utf-8` before running orchestrator
- **check-jsonschema not found**: Install with `pip install check-jsonschema`
