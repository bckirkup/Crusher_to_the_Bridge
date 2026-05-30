---
name: testing-picard-presidio
description: Test Picard_Framework, decision_engine, and Presidio fleet runner. Use before PRs touching picard_framework/, decision_engine/, presidio/, or presidio_runner.py.
---

# Testing Picard & Presidio

## Full framework test slice

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_picard_framework.py \
  tests/test_decision_engine.py \
  tests/test_presidio_runner.py \
  tests/test_golden_orchestrator.py \
  tests/test_law_compliance.py -v --tb=short
```

## JSON schema validation (optional)

```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/picard_run_spec.schema.json \
  picard_framework/runs/destroyer_baseline_default.json
check-jsonschema --schemafile schemas/presidio_fleet_config.schema.json \
  presidio/data/config/default_fleet.json
check-jsonschema --schemafile schemas/presidio_fleet_economics.schema.json \
  presidio/data/economics/fleet_economics.json
```

## Law compliance

`tests/test_law_compliance.py` scans `picard_framework/simulation/ship_simulation.py` for hardcoded epoch schedules and zone names.

## CI

Workflow `.github/workflows/picard-presidio.yml` runs on `cursor/**` and `main`.
