---
name: operational-impact-behavioral-policies
description: Configure Operational Impact Score (OIS), executable action envelopes, and Layer-1 behavioral policies (ThresholdBeliefPolicy). Use when editing cost_ledger, resource_costs operational_impact_weights, syndromic sick-call wiring, or decision_engine policies.
---

# Operational Impact & Behavioral Policies

## Operational Impact Score (OIS)

OIS is a **tracker-only** fourth ledger dimension (like financial budget — never blocks actions).

### Configuration

[`data/config/resource_costs.json`](data/config/resource_costs.json) → `operational_impact_weights`:

| Key | Typical use |
|-----|-------------|
| `per_passenger_quarantined` | Each passenger in `quarantined_ids` |
| `per_essential_crew_quarantined` | Crew whose `agent_class` is in `essential_crew_classes` |
| `per_passenger_isolated` | Each passenger in `isolated_ids` |
| `per_closed_galley_zone` | Each closed zone whose `type` is in `galley_zone_types` |
| `per_fleet_ppe_active` | Once per epoch when PPE modifiers are active |

Galley detection uses **zone types** from `spatial_layout.json`, not hardcoded zone names (Law 2).

### Code paths

- Accumulation: `orchestrator_epoch.step_operational_impact_accounting()`
- Computation: `crusher_labs.cost_ledger.compute_operational_impact()`
- Telemetry: `cost_accounting.operational_impact_epoch`, `operational_impact_cumulative`, `operational_impact_breakdown`
- CO view: `decision_engine/views.py`, `decision_engine/observation/command.py`

### Verify after changes

```bash
python3 orchestrator.py --epochs 4
python3 -c "
import json
h = json.load(open('telemetry_buffer/simulation_history.json'))
c = h[-1]['cost_accounting']
assert 'operational_impact_cumulative' in c
print('OIS cumulative:', c['operational_impact_cumulative'])
"
```

## Executable action kinds

Schema: [`schemas/decision_action.schema.json`](schemas/decision_action.schema.json)

| Kind | Effect |
|------|--------|
| `activate_sop` / `request_sop_activation` | Add to `SimulationState.forced_protocol_ids` |
| `deactivate_sop` | Remove from forced set |
| `order_verification_test` | Queue zone for PCR surface wipe |
| `hide_symptoms` | Suppress sick-call for agent this epoch |
| `report_sick_call` | Force sick-call if symptomatic |
| `refuse_quarantine` | Bias quarantine compliance toward refusal |

Applier: [`picard_framework/simulation/action_applier.py`](picard_framework/simulation/action_applier.py)

## Behavioral policies (Picard only)

Configure in [`crusher_labs/config.yaml`](crusher_labs/config.yaml) → `decision_engine:`:

```yaml
decision_engine:
  population_policy: threshold_belief   # or rule_based for flat syndromic
  command_policy: threshold             # or rule_based
  medical_policy: threshold
```

Factory: `decision_engine.policy.build_policies_from_config()`

Population decisions run **before** syndromic via `StackelbergRound.solve_population()`.

## Tests

```bash
python3 -m pytest tests/test_operational_impact.py tests/test_action_applier.py \
  tests/test_behavioral_syndromic.py tests/test_cost_ledger.py \
  tests/test_decision_engine.py -v --tb=short
```

Related skills: `configuring-stackelberg-social`, `testing-picard-presidio`, `stackelberg-utility-export`
