# Crusher-to-the-Bridge — Game Theory & Fleet Operator's Manual (Presidio)

**Scope:** Multi-cruise fleet meta-simulation, hierarchical decisions, incomplete information, and cross-cruise experience.  
**Single-ship operations:** see [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md).

---

## Architecture

```text
presidio_runner.py
  └── decision_engine.DecisionRound (per epoch, per actor)
  └── picard_framework.ShipSimulation (physics + diagnostics)
  └── decision_engine.ExperienceStore (between cruises)
```

**Law 1:** Standing SOPs remain stoplight-driven. Strategic actors augment surveillance cadence and related hooks; they do not use hardcoded epoch schedules.

## Presidio configuration directories

| Directory | Files | Role |
|-----------|-------|------|
| `presidio/data/catalog/` | `libraries.json` | Index of fleet configs, economics, Picard run specs |
| `presidio/data/config/` | `default_fleet.json`, `smoke_fleet.json` | Fleet run specifications |
| `presidio/data/economics/` | `fleet_economics.json` | Reward weights and penalties |
| `presidio/data/experiences/` | `fleet_experience.json`, `runs/` | Cross-cruise memory and per-cruise telemetry |

## Fleet quick start

```bash
python3 tools/sanity_checker.py --from-config

# Smoke (1 cruise × 2 epochs)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1

# Default fleet profile
python3 presidio_runner.py
```

## Actor roles and information

| Role | Typical observation |
|------|---------------------|
| `crew_agent` | Own location and health axes |
| `medical_officer` | Instrument summaries, sick calls |
| `commanding_officer` | Fleet aggregates, costs, escalation status |

Observations are built by `decision_engine.ObservationModel` from a public epoch snapshot — not full ground truth.

## Incentives

Fleet-level weights live in:

- `presidio/data/config/*.json` → `incentives` block
- `presidio/data/economics/fleet_economics.json` → `reward_weights`, `penalties`

## Schemas

- `schemas/presidio_fleet_config.schema.json`
- `schemas/presidio_fleet_economics.schema.json`
- `schemas/decision_action.schema.json`

## Reusing decision_engine elsewhere

`decision_engine` has **no** imports from `engines.*`. Provide your own host loop, public snapshot builder, and action applier.

## Validation

```bash
python3 -m pytest tests/test_decision_engine.py tests/test_presidio_runner.py -v
```

See skill: `.agents/skills/testing-picard-presidio/SKILL.md`
