# Outbreak Response Architecture: SOPs, Decision Latency, and Compliance
## Specification for Crusher to the Bridge

> **Status (2026-07):** Implemented in-tree. Escalation levels
> `BASELINE → ALERT → SUSPECTED → CONFIRMED → LOCKDOWN` use cumulative
> attack-rate thresholds; `escalation.decision_latency` queues pending
> transitions; FRED compliance is a sticky bimodal mixture
> (compliant / reluctant / defiant). SOP-009 requires `LOCKDOWN`.
> Campaign tiers T11 (decision latency), T15 (SOP thresholds), and T16
> (reluctant fraction) sweep the new knobs. See
> `tests/test_outbreak_response_architecture.py`.

### Motivation

Campaign v4 (4,156 runs) revealed that three distinct systems are currently 
collapsed into one, producing unrealistic behavior:

1. **SOP invocation** (policy): which response actions fire at which information state
2. **Decision latency** (organizational): how long between signal and action
3. **Compliance** (behavioral): whether individuals follow quarantine orders

Currently: 3 sick calls → 1 PCR → confine ALL in 1-3 epochs, with forced 
compliance after 1 epoch. This makes compliance, wearable sensitivity, 
sick-call detection rate, and intervention timing all irrelevant.

This spec separates the three systems so each can be independently parameterized 
and studied.

---

## System 1: SOP Invocation (Policy Layer)

### What it is
The decision rules that determine which Standing Operating Procedures activate 
at which information state. This is a *policy choice* — different ships, 
navies, or cruise lines may choose different rules.

### Current problem
SOP-009 (confine_all_to_quarters) fires on a single qPCR RED stoplight, 
which triggers within 1-3 epochs. The thresholds are too sensitive.

### Design

SOPs already exist in `protocols.json` with stoplight-level triggers. 
The fix is in the **stoplight thresholds**, not the SOP structure.

#### Escalation levels (in `config.yaml escalation:`)

```yaml
escalation:
  # Level 0 → Level 1 (ALERT): first signal of possible outbreak
  alert_sick_call_threshold: 3          # ≥3 sick calls in 24h (keep existing)

  # Level 1 → Level 2 (SUSPECTED): CDC VSP 2% reporting threshold
  suspect_attack_rate: 0.02             # 2% cumulative AR among passengers or crew

  # Level 2 → Level 3 (CONFIRMED): CDC VSP 3% outbreak threshold  
  confirm_attack_rate: 0.03             # 3% cumulative AR

  # Level 3 → Level 4 (LOCKDOWN): extreme measure, rarely used
  lockdown_attack_rate: 0.05            # 5% cumulative AR

  # Respiratory pathogen overrides (lower thresholds, per CDC/IHR)
  respiratory_overrides:
    alert_confirmed_cases: 1            # 1 confirmed case → ALERT
    suspect_attack_rate: 0.01           # 1% → SUSPECTED
```

#### SOP activation by level

| Level | Status | SOPs that activate | Confinement scope |
|-------|--------|-------------------|-------------------|
| 0 | BASELINE | None | None |
| 1 | ALERT | SOP-004 (PPE), SOP-006 (diagnostic cadence), SOP-008 (individual symptomatic confinement) | Symptomatic individuals only |
| 2 | SUSPECTED | + SOP-001 (enhanced ventilation), SOP-003 (surface decon), SOP-007 (galley closure), SOP-010 (VSP mass isolation of symptomatic) | Symptomatic + confirmed cases |
| 3 | CONFIRMED | + SOP-005 (N95), SOP-002 (HEPA), SOP-011 (Diamond Princess-style contact confinement) | Symptomatic + contacts |
| 4 | LOCKDOWN | + SOP-009 (confine all to quarters) | All passengers, non-essential crew |

#### Implementation

Modify `check_escalation()` to:
- Track cumulative confirmed cases in `SimulationState.cumulative_confirmed_cases`
- Use attack rate thresholds (not single PCR results) for SUSPECTED→CONFIRMED→LOCKDOWN
- Keep the existing BASELINE→ALERT transition (sick call count) as-is
- Add `respiratory_mode` flag read from pathogen profile's `clinical_presentation.syndromes`

Modify `step_quarantine_confinement()` to select confinement scope based on 
trigger level, mapping to the SOP table above.

### Parameters for campaign sweep

```
escalation.suspect_attack_rate: [0.01, 0.02, 0.03, 0.05]
escalation.lockdown_attack_rate: [0.03, 0.05, 0.10, never]
```

---

## System 2: Decision Latency (Organizational Layer)

### What it is
The delay between an instrument signaling a threshold breach and the 
corresponding SOP actually activating. This represents organizational 
decision-making time: meetings, risk assessment, communication up the 
chain of command, logistics of deploying the response.

### Current problem
Zero latency — SOPs activate in the same epoch as the signal. In reality, 
the Diamond Princess took days from first case to quarantine order. 
USS Theodore Roosevelt took weeks for full response.

### Design

Add `activation_delay_hours` to each SOP in `protocols.json`:

```json
{
  "protocol_id": "SOP-008",
  "name": "Individual Symptomatic Confinement",
  "activation_delay_hours": 2,
  ...
}
```

And an escalation-level delay in `config.yaml`:

```yaml
escalation:
  decision_latency:
    alert_delay_hours: 1               # 1 hour to start isolating individuals
    suspected_delay_hours: 6            # 6 hours for enhanced response
    confirmed_delay_hours: 24           # 1 day for outbreak-level response
    lockdown_delay_hours: 48             # 2 days for ship-wide lockdown decision
```

#### Implementation

When `check_escalation()` determines a new level is reached, record 
`state.escalation_pending = (new_level, epoch_triggered)`. The level 
doesn't take effect until `epoch >= epoch_triggered + delay`. During 
the delay, the previous level's SOPs remain active.

This is simple to implement: a pending-transition queue in SimulationState.

### Parameters for campaign sweep

```
decision_latency.alert_delay_hours: [0, 1, 2, 6]
decision_latency.confirmed_delay_hours: [6, 12, 24, 48, 72]
decision_latency.lockdown_delay_hours: [24, 48, 72, 168]
```

---

## System 3: Compliance (Behavioral Layer)

### What it is
Whether individual agents follow quarantine/isolation orders. This is 
human behavior, determined by psychology, sociology, and circumstance — 
not by policy.

### Current problem
`compliance_delay_hours: 1` forces all agents to comply after 1 hour
regardless of their compliance parameter. This eliminates compliance as 
a meaningful variable.

### Design

#### Agent compliance classes

Based on the literature (Webster et al. pre-COVID review, UK NHS app study, 
influenza ABM parameterizations), compliance is best modeled as a 
**bimodal mixture of agent types**, not a continuous distribution:

| Agent class | Fraction | Behavior | Basis |
|-------------|----------|----------|-------|
| **Compliant** | `compliance` param (e.g., 0.6) | Immediately follows quarantine orders. Stays quarantined for full duration. | ~45-75% in real outbreaks |
| **Reluctant** | `(1 - compliance) × reluctant_fraction` (e.g., 0.3) | Initially refuses. May comply after `reluctant_delay_hours` (e.g., 48-72 hours) if they develop symptoms or see others getting sick. | Intention-behavior gap population |
| **Defiant** | `(1 - compliance) × (1 - reluctant_fraction)` (e.g., 0.1) | Refuses quarantine for the duration. Does not comply regardless of delay or social pressure. | ~5-15% persistent non-compliers |

The `compliance` parameter (0.0 to 1.0) sets the fraction in the Compliant 
class. The remainder splits between Reluctant and Defiant.

#### Agent class modifiers

Different agent classes (crew vs. passenger) may have different baseline 
compliance. In `config.yaml`:

```yaml
fred_behavior:
  quarantine_compliance: 0.60          # population default
  reluctant_fraction: 0.75             # of non-compliers, 75% are reluctant (vs defiant)
  reluctant_delay_hours: 48            # reluctant agents may comply after 48 hours
  compliance_by_class:
    crew: 0.85                         # crew more compliant (military/employment)
    passenger_elderly: 0.70            # higher perceived risk → more compliant
    passenger_young: 0.45              # lower perceived risk → less compliant
```

#### Implementation

Modify `check_quarantine_compliance()`:

```python
def check_quarantine_compliance(self, agent_id, epochs_since_order, ...):
    # Determine agent's compliance class (assigned at first quarantine order)
    if agent_id not in self._compliance_class:
        draw = self.rng.random()
        effective = min(1.0, self.quarantine_compliance + chronic_boost)
        if draw < effective:
            self._compliance_class[agent_id] = "compliant"
        elif draw < effective + (1 - effective) * self.reluctant_fraction:
            self._compliance_class[agent_id] = "reluctant"
        else:
            self._compliance_class[agent_id] = "defiant"

    cls = self._compliance_class[agent_id]

    if cls == "compliant":
        return True
    elif cls == "defiant":
        return False
    elif cls == "reluctant":
        # May comply after delay, OR if they become symptomatic
        if hours_since_order >= self.reluctant_delay_hours:
            return True
        return False
```

Remove the old forced-compliance behavior entirely. The retired
`compliance_delay_epochs` spelling remains a loader fallback.

#### Structural non-compliance (physics, not behavior)

Even compliant agents in shared cabins are not fully isolated. This is 
already handled by the transmission engine's confinement isolation factor 
(`DEFAULT_CONFINEMENT_ISOLATION_FACTOR = 0.05` and 
`NON_MATE_CONFINEMENT_CONTACT_FACTOR = 0.01`). No change needed — the 
distinction between behavioral compliance (do you stay in your cabin?) 
and structural effectiveness (does staying in your cabin actually prevent 
exposure?) is already architecturally separated.

### Parameters for campaign sweep

```
quarantine_compliance: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
reluctant_fraction: [0.5, 0.75, 1.0]  # 1.0 = no defiants
reluctant_delay_hours: [24, 48, 72, 168]
```

---

## Interactions Between Systems

The three systems interact but are independently parameterizable:

1. **SOP thresholds** determine *when* quarantine is ordered
2. **Decision latency** determines *how fast* the order reaches agents
3. **Compliance** determines *whether* agents follow the order

A sweep that varies all three reveals which is the binding constraint:
- If raising SOP thresholds barely changes outcomes → the outbreak overwhelms 
  any reasonable response (norovirus)
- If decision latency dominates → early detection is the key investment
- If compliance dominates → behavioral interventions (communication, 
  compensation, enforcement) matter more than surveillance technology

---

## Campaign v5 Tier Design (after implementation)

| Tier | Runs | Question |
|------|------|----------|
| T1 Baselines | 200 | 10 pathogens × (none_true, syndromic) × 10 seeds |
| T3 Surveillance | 400 | 10 pathogens × 4 surveillance × 10 seeds |
| T7 Compliance | 1440 | 4 pathogens × 4 surveillance × 6 compliance × 3 immunity × 5 seeds |
| T9 Slow pathogens | 80 | 4 pathogens × 4 surveillance × 5 seeds (504 epochs) |
| T11 Timing (decision latency) | 400 | 4 pathogens × 5 latency levels × 2 surveillance × 2 compliance × 5 seeds |
| T12 Surveillance sensitivity | 200 | 4 pathogens × 5 sick-call probs × 2 surveillance × 5 seeds |
| T14 Immunity threshold | 800 | 10 pathogens × 8 immunity × 10 seeds |
| T15 SOP threshold sweep (NEW) | 320 | 4 pathogens × 4 suspect_AR × 4 lockdown_AR × 5 seeds |
| T16 Reluctant fraction sweep (NEW) | 240 | 4 pathogens × 3 reluctant_frac × 4 delay × 5 seeds |
| **Total** | **~4,100** | |

---

## Source Literature

- CDC VSP 2%/3% thresholds: [task:e8da2eaa-e847-4bec-85db-5df53cb2dec5]
- Quarantine compliance rates and behavioral models: [task:9a937b48-de80-4365-8c77-78b971034a33]
- Diamond Princess, USS Theodore Roosevelt response timelines: both tasks above
- Influenza ABM compliance parameterization (25/50/75/100%): compliance review
- UK NHS app study (45% actual vs 71% intended compliance): compliance review
- Webster et al. pre-COVID meta-review (0-93% adherence): compliance review
