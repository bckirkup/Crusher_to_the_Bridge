---
name: outbreak-response-architecture
description: Configure the three separated outbreak-response systems — SOP/policy escalation, organizational decision latency, and bimodal quarantine compliance. Use when editing check_escalation, fred_behavior, protocols.json min_escalation_status/activation_delay_epochs, or Campaign T11/T15/T16 sweeps.
---

# Outbreak Response Architecture

Spec: [`docs/tiered_escalation_spec.md`](docs/tiered_escalation_spec.md)
(Campaign v4 finding: SOP invocation, decision latency, and compliance were
collapsed — early confine-all + forced compliance made surveillance knobs irrelevant.)

## Three independent systems

| System | What it controls | Primary knobs |
|--------|------------------|---------------|
| **1. SOP / policy** | Which response fires at which information state | `escalation.*_attack_rate`, `min_escalation_status` on SOPs |
| **2. Decision latency** | Delay from signal → effective status / SOP | `escalation.decision_latency.*`, SOP `activation_delay_epochs` |
| **3. Compliance** | Whether agents follow quarantine orders | `fred_behavior.quarantine_compliance`, `reluctant_*`, `compliance_by_class` |

## System 1 — Escalation levels

```
BASELINE → ALERT → SUSPECTED → CONFIRMED → LOCKDOWN
```

| Transition | Default signal |
|------------|----------------|
| → ALERT | ≥ `alert_sick_call_threshold` (alias: `syndromic_suspect_threshold`) sick calls; respiratory: ≥ N confirmed cases |
| → SUSPECTED | max(passenger, crew) cumulative ever-ill AR ≥ `suspect_attack_rate` (0.02) |
| → CONFIRMED | AR ≥ `confirm_attack_rate` (0.03) |
| → LOCKDOWN | AR ≥ `lockdown_attack_rate` (campaign 0.05; default config `never` for n=20 smokes) |

Code: `orchestrator_init.check_escalation` / `propose_escalation_level` /
`apply_escalation_latency`. State fields: `ever_ill_ids`,
`cumulative_confirmed_case_ids`, `escalation_pending`.

Confinement scope (`step_quarantine_confinement`):

| Level | Scope |
|-------|-------|
| ALERT | Symptomatic |
| SUSPECTED | Symptomatic + clinically confirmed |
| CONFIRMED | Symptomatic + confirmed + cabin-mate contacts |
| LOCKDOWN | All non-exempt (same as SOP-009) |

SOP gates: `min_escalation_status` on protocols (SOP-009 = `LOCKDOWN`).
Stoplight triggers still required unless forced via `activate_sop`.

## System 2 — Decision latency

```yaml
escalation:
  decision_latency:
    alert_delay_epochs: 0
    suspected_delay_epochs: 0
    confirmed_delay_epochs: 0
    lockdown_delay_epochs: 0
```

When a higher level is proposed, `SimulationState.escalation_pending`
queues `{to, epoch_triggered}` until `epoch >= triggered + delay`.
Per-SOP `activation_delay_epochs` further defers modifier application after
stoplight + escalation gate eligibility (forced SOPs bypass SOP delay).

**Do not confuse** with surveillance `activation_delay_epochs` on
`syndromic` / `diagnostic_cascade` (Campaign legacy T11 / start-delay).

## System 3 — Bimodal compliance

```yaml
fred_behavior:
  quarantine_compliance: 0.85     # fraction Compliant
  reluctant_fraction: 0.75        # of non-compliers → Reluctant (rest Defiant)
  reluctant_delay_epochs: 48
  compliance_by_class:
    crew: 0.85
    passenger_elderly: 0.70
    passenger_young: 0.45
```

Class is sticky at first quarantine order (`SyndromicSurveillance._compliance_class`).
Reluctant complies after delay **or** if symptomatic; Defiant never complies.
`refuse_quarantine` action forces Defiant. Legacy `compliance_delay_epochs`
forced-compliance path is removed (key ignored if present).

## Campaign sweeps (v5)

| Tier | Question |
|------|----------|
| T11 `t11_intervention_timing` | Decision latency (`decision_latency_levels`) × surv × compliance |
| T15 `t15_sop_threshold_sweep` | `suspect_attack_rate` × `lockdown_attack_rate` (incl. `"never"`) |
| T16 `t16_reluctant_fraction_sweep` | `reluctant_fraction` × `reluctant_delay_epochs` |

Mega-cruise generator injects `_CAMPAIGN_ESCALATION_DEFAULTS`
(`lockdown_attack_rate: 0.05`) so large ships enable LOCKDOWN; smoke
`config.yaml` keeps `never`.

## Verify after changes

```bash
python3 -m pytest tests/test_outbreak_response_architecture.py \
  tests/test_orchestrator.py::TestCheckEscalation \
  tests/test_orchestrator.py::TestCascadeQuarantineCompliance \
  tests/test_protocol_engine.py -v --tb=short

python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_golden_orchestrator.py tests/test_golden_picard.py -v --tb=short
```

Related: `operational-impact-behavioral-policies`, `mega-cruise-campaign-local`,
`orchestrator-smoke-test`, `diagnostic-cascade`, `ci-test-design`.
