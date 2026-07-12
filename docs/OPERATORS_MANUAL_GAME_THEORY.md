# Crusher-to-the-Bridge — Game Theory & Fleet Operator's Manual (Presidio)

**Scope:** Stackelberg decisions, information diffusion, reputation, operational impact (OIS), and external utility optimization.

Single-ship Picard operations: [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md).

---

## Stackelberg move order (Picard `ShipSimulation`)

Picard splits decisions across the epoch so population behavior affects the same epoch's syndromic sick-call roster. See [docs/simulation_step_order.md](docs/simulation_step_order.md).

### Phase A — After ground truth, before syndromic

1. **Information diffusion** — Update per-agent `severity_belief`, `trust_medical`, etc.
2. **Population** — Per-agent or aggregate actions: `hide_symptoms`, `report_sick_call`, `refuse_quarantine` (via `ThresholdBeliefPolicy` when configured)

### Phase B — After stoplights, before protocol physics

3. **Command** — `authorize_sop_subset`, `activate_sop`, surveillance cadence, corporate stance, directives to medical; sees cumulative **OIS** in observation
4. **Medical** — `order_verification_test`, `request_sop_activation`, crew instructions, cadence overrides

Standing SOP **physics** remains stoplight-driven (**Law 1**). Command `authorize_sop_subset` filters which stoplight-triggered SOPs apply modifiers and which may debit costs. `activate_sop` forces a protocol active even without a stoplight (still subject to authorization for debits).

**Legacy `orchestrator.py`:** OIS only; no Stackelberg passes (flat syndromic).

---

## Policy configuration (`crusher_labs/config.yaml`)

```yaml
decision_engine:
  population_policy: threshold_belief   # rule_based → noop / flat syndromic
  command_policy: threshold
  medical_policy: threshold
  threshold_belief:
    severity_report_threshold: 0.35
    trust_report_floor: 0.4
    hide_trust_ceiling: 0.35
    hide_severity_ceiling: 0.25
  command_threshold:
    ois_escalation_threshold: 15.0
    infected_rate_threshold: 0.05
  medical_threshold:
    sick_call_threshold: 3
```

Classes: `decision_engine.policy.ThresholdBeliefPolicy`, `CommandThresholdPolicy`, `MedicalThresholdPolicy`, `RuleBasedPolicy`.

---

## Action envelope kinds

| Kind | Actor | Effect |
|------|-------|--------|
| `activate_sop` | command / medical | Force protocol ID into `forced_protocol_ids` |
| `deactivate_sop` | command | Remove forced protocol |
| `authorize_sop_subset` | command | Restrict auto-activated SOPs |
| `order_verification_test` | medical | Queue zone for PCR surface wipe |
| `hide_symptoms` | population | No sick-call this epoch |
| `report_sick_call` | population | Force sick-call if symptomatic |
| `refuse_quarantine` | population | Compliance bias toward refusal |
| `set_surveillance_cadence` | medical | `pcr_cadence`, `sequencing_cadence` overrides |
| `set_isolation_posture` | medical | Isolation threshold scale |
| `corporate_communication_stance` | command | Reputation / trust signal |
| `directive_to_medical` | command | Medical directives list |
| `issue_crew_instruction` | medical | Public SOP announcements |

Schema: `schemas/decision_action.schema.json`. Use **top-level** action fields (`protocol_id`, `zone`, `agent_id`) — not nested `parameters` wrappers.

---

## Operational Impact Score (OIS)

Configured in `data/config/resource_costs.json` → `operational_impact_weights`.

Reported in `simulation_history[].cost_accounting`:

- `operational_impact_epoch` — delta this epoch
- `operational_impact_cumulative` — run total
- `operational_impact_breakdown` — e.g. `passenger_quarantine`, `closed_galley_zones`, `fleet_ppe`

Command utility features include `operational_impact_epoch` and `operational_impact_cumulative` for external optimizers.

---

## Fleet reward economics (`_compute_rewards`)

The Presidio experience store records a scalar reward after each cruise.
This reward is a **reduced-order model (ROM)** — a lightweight linear
proxy, not a full multi-objective optimization target.  External
optimizers should consume the richer utility observation bundles exported
via `--export-utility-dir`.

**Reward formula:**

```
fleet_reward = w_bio  * (-(infected + symptomatic))
             + w_cost * (-0.001 * total_financial_usd)
             + w_rec  * recovered
             + w_ois  * (-operational_impact_cumulative)
```

**Configurable weights** (`presidio/data/economics/fleet_economics.json` → `incentives`):

| Weight | Key | Default | Signal |
|--------|-----|---------|--------|
| Biodefense | `biodefense_weight` | 1.0 | Penalizes active infections |
| Budget | `budget_weight` | 0.1 | Penalizes total USD spending |
| Recovery | `recovery_weight` | 0.05 | Rewards successful recoveries |
| OIS | `ois_weight` | 0.02 | Penalizes operational disruption |

The `commanding_officer` sub-reward is `fleet_reward * 0.5` (placeholder
for future role-specific utility splits).

---

## Presidio fleet runner

```bash
# Smoke (1 cruise × 2 epochs)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1

# Utility export / action import (external optimizer)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1 \
  --export-utility-dir presidio/data/experiences/utility_bundles \
  --import-actions-dir presidio/data/experiences/imported_actions
```

---

## Configuration

| Path | Purpose |
|------|---------|
| `presidio/data/social/information_diffusion_default.json` | Belief propagation |
| `presidio/data/social/class_interactions_default.json` | Crew/passenger contact weights |
| `presidio/data/intelligence/global_health_timeline.json` | Global health briefings |
| `picard_framework/data/agent_profiles/default_ship_population.json` | Agent profiles |
| `data/config/resource_costs.json` | Financial costs + **OIS weights** |
| `presidio/data/economics/fleet_economics.json` | External reward weight references |
| `crusher_labs/config.yaml` | `decision_engine` policy selection |

---

## External optimization workflow

1. Enable `social.export_utility_dir` on the Picard run spec.
2. Run simulation; each epoch writes `cruise_{id}_epoch_{NNNN}_utility.json`.
3. External tool optimizes and writes `cruise_{id}_epoch_{NNNN}_actions.json`.
4. Re-run with `import_actions_dir` — **replaces** in-repo policy output for that epoch when import succeeds.

Utility **features** and action **validation** are in-repo; **weights and optimization** are out-of-repo.

---

## Agent hooks & telemetry

| Hook | Module / field |
|------|----------------|
| Lived experience | `decision_engine/lived_experience.py` |
| Information state | `simulation_history[].information_state` |
| Behavioral overrides | `SimulationState.agent_behavioral_overrides` (Picard) |
| Forced SOPs | `SimulationState.forced_protocol_ids` |
| OIS | `cost_accounting.operational_impact_*` |
| SOP events | `reactive_protocols.sop_events` |

---

## JSON schemas

| Schema | Data file |
|--------|-----------|
| `decision_action.schema.json` | Imported / documented actions |
| `simulation_history.schema.json` | Includes OIS in `cost_accounting` |
| `resource_costs.schema.json` | Includes `operational_impact_weights` |
| `utility_observation_bundle.schema.json` | Exported utility JSON |
| `information_diffusion.schema.json` | Social diffusion config |
| `class_interactions.schema.json` | Class interaction matrix |
| `global_health_briefing.schema.json` | Intelligence timeline |
| `agent_profile.schema.json` | Agent profile bundle |

---

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_stackelberg.py tests/test_picard_framework.py \
  tests/test_decision_engine.py tests/test_presidio_runner.py \
  tests/test_operational_impact.py tests/test_action_applier.py \
  tests/test_behavioral_syndromic.py -v
```

Skills:

- `.agents/skills/operational-impact-behavioral-policies/SKILL.md`
- `.agents/skills/stackelberg-utility-export/SKILL.md`
- `.agents/skills/configuring-stackelberg-social/SKILL.md`
- `.agents/skills/presidio-fleet-run/SKILL.md`
- `.agents/skills/testing-picard-presidio/SKILL.md`

CI: `.github/workflows/ci.yml` and `.github/workflows/picard-presidio.yml`.
