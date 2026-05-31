---
name: testing-picard-presidio
description: Test Picard_Framework, decision_engine, Presidio fleet runner, and Stackelberg social layer. Use before PRs touching picard_framework/, decision_engine/, presidio/, presidio_runner.py, or Stackelberg configs.
---

# Testing Picard & Presidio

## Full framework test slice

```bash
python3 tools/sanity_checker.py --from-config
PYTHONPATH=. python3 -m pytest \
  tests/test_picard_framework.py \
  tests/test_decision_engine.py \
  tests/test_presidio_runner.py \
  tests/test_golden_orchestrator.py \
  tests/test_stackelberg.py \
  tests/test_law_compliance.py \
  tests/test_operational_impact.py \
  tests/test_action_applier.py \
  tests/test_behavioral_syndromic.py \
  tests/test_enterprise_platforms.py \
  tests/test_agent_axes.py \
  tests/test_sequencing_config.py -v --tb=short
```

## Presidio CLI smoke

```bash
PYTHONPATH=. python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

## JSON schema validation (optional)

```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/picard_run_spec.schema.json \
  picard_framework/runs/destroyer_baseline_default.json
check-jsonschema --schemafile schemas/presidio_fleet_config.schema.json \
  presidio/data/config/default_fleet.json
check-jsonschema --schemafile schemas/information_diffusion.schema.json \
  presidio/data/social/information_diffusion_default.json
check-jsonschema --schemafile schemas/utility_observation_bundle.schema.json \
  schemas/utility_observation_bundle.schema.json
```

## Law compliance

`tests/test_law_compliance.py` scans `picard_framework/simulation/ship_simulation.py` for hardcoded epoch schedules and zone names.

## CI equivalence

| Workflow | When |
|----------|------|
| `.github/workflows/ci.yml` | All `main` PRs — full pytest (~337) + Presidio smoke + import hygiene + OIS verify |
| `.github/workflows/picard-presidio.yml` | `main` and `cursor/**` — framework slice + Stackelberg/platform schema checks |

Replicate main CI framework steps:

```bash
PYTHONPATH=. python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
from presidio import PresidioRunSpec
from decision_engine import DecisionRound, StackelbergRound, DecisionRuntime
from decision_engine.policy import ThresholdBeliefPolicy, build_policies_from_config
import presidio_runner
assert hasattr(StackelbergRound, 'solve_population')
print('OK')
"
```
