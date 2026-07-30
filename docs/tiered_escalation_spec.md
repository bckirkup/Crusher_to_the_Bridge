# Tiered Escalation Implementation Spec
## For: Crusher to the Bridge — PR for Devin

### Overview
Replace the current 2-level escalation (BASELINE → SUSPECTED → CONFIRMED) with a 
5-level system based on CDC VSP, WHO IHR, and Navy outbreak response protocols.
The current system fires full-ship lockdown within 1-3 epochs, making compliance, 
wearable sensitivity, and surveillance sensitivity parameters irrelevant.

### Current Architecture (to replace)

`orchestrator_init.py::check_escalation()` (line 382):
- BASELINE → SUSPECTED: sick_call_count ≥ 3
- SUSPECTED → CONFIRMED: any zone PCR Ct ≤ 35

`orchestrator_epoch.py::step_quarantine_confinement()` (line 567):
- SOP-009 confine_all_to_quarters: confines ALL agents (no compliance check)
- SOP-008/010: confines symptomatic only
- Legacy fallback: CONFIRMED → confine symptomatic + shedding

### New Architecture

#### 1. New trigger levels in `orchestrator_types.py`

```python
STATUS_BASELINE = "BASELINE"
STATUS_ALERT = "ALERT"           # NEW
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_LOCKDOWN = "LOCKDOWN"     # NEW
```

#### 2. New `check_escalation()` in `orchestrator_init.py`

Replace the existing function. The new version needs access to cumulative case 
counts, not just current-epoch sick calls.

```python
def check_escalation(
    trigger_status: str,
    syndromic_result: dict[str, Any],
    pcr_result: dict[str, Any] | None,
    cfg: dict[str, Any],
    state: SimulationState,  # NEW — needs cumulative tracking
) -> str:
    esc_cfg = cfg.get("escalation", {})
    num_agents = cfg.get("ship_graph", {}).get("num_agents", 7000)

    # Pathogen syndrome type affects thresholds
    # Default to GI thresholds; respiratory overrides from pathogen profile
    is_respiratory = esc_cfg.get("respiratory_mode", False)

    # Track cumulative confirmed cases in state
    cumulative_cases = state.cumulative_confirmed_cases  # NEW field
    attack_rate = cumulative_cases / num_agents

    # BASELINE → ALERT
    if trigger_status == STATUS_BASELINE:
        alert_threshold = esc_cfg.get("alert_sick_call_threshold", 3)
        if is_respiratory:
            # 1 confirmed case for respiratory
            if cumulative_cases >= esc_cfg.get("respiratory_alert_cases", 1):
                return STATUS_ALERT
        if syndromic_result["sick_call_count"] >= alert_threshold:
            return STATUS_ALERT

    # ALERT → SUSPECTED
    if trigger_status == STATUS_ALERT:
        suspect_pct = esc_cfg.get("suspect_attack_rate", 0.02)  # 2%
        if is_respiratory:
            suspect_cases = esc_cfg.get("respiratory_suspect_cases", 3)
            if cumulative_cases >= suspect_cases and pcr_result_positive(pcr_result):
                return STATUS_SUSPECTED
        if attack_rate >= suspect_pct:
            return STATUS_SUSPECTED

    # SUSPECTED → CONFIRMED
    if trigger_status == STATUS_SUSPECTED:
        confirm_pct = esc_cfg.get("confirm_attack_rate", 0.03)  # 3%
        if attack_rate >= confirm_pct:
            return STATUS_CONFIRMED

    # CONFIRMED → LOCKDOWN
    if trigger_status == STATUS_CONFIRMED:
        lockdown_pct = esc_cfg.get("lockdown_attack_rate", 0.05)  # 5%
        if attack_rate >= lockdown_pct:
            return STATUS_LOCKDOWN

    return trigger_status
```

#### 3. New `step_quarantine_confinement()` in `orchestrator_epoch.py`

Replace the existing function. Confinement actions depend on trigger level:

```python
def step_quarantine_confinement(
    epoch, agents, merged_mods, trigger_status, state, syndromic,
):
    exempt_classes = set(merged_mods.get("exempt_classes", []))

    if trigger_status == STATUS_LOCKDOWN:
        # Level 4: Full lockdown — mandatory, no compliance check
        confine_all_agents(epoch, agents, state, syndromic, exempt_classes)
        return

    if trigger_status == STATUS_CONFIRMED:
        # Level 3: Symptomatic + close contacts, compliance-gated
        confine_agents(epoch, agents, state, syndromic,
                      include_shedding=True, exempt_classes=exempt_classes)
        # Also confine traced contacts (compliance-gated)
        confine_contacts(epoch, agents, state, syndromic, exempt_classes)
        return

    if trigger_status == STATUS_SUSPECTED:
        # Level 2: Confirmed/suspected cases mandatory, contacts compliance-gated
        confine_agents(epoch, agents, state, syndromic,
                      include_shedding=True, exempt_classes=exempt_classes)
        return

    if trigger_status == STATUS_ALERT:
        # Level 1: Symptomatic individuals only, compliance-gated
        confine_agents(epoch, agents, state, syndromic,
                      include_shedding=False, exempt_classes=exempt_classes)
        return

    # BASELINE: no confinement
```

#### 4. State changes in `SimulationState`

Add to `orchestrator_types.py`:
```python
cumulative_confirmed_cases: int = 0
escalation_log: list[dict] = field(default_factory=list)
```

Update cumulative case tracking each epoch in the simulation loop:
```python
# In ship_simulation.py epoch loop, after syndromic results:
state.cumulative_confirmed_cases = sum(
    1 for a in agents 
    if a.get("infection_state") in ("symptomatic", "recovered")
)
```

#### 5. Config changes

Update `crusher_labs/config.yaml`:
```yaml
escalation:
  alert_sick_call_threshold: 3
  respiratory_alert_cases: 1
  suspect_attack_rate: 0.02        # 2% — CDC VSP reporting threshold
  confirm_attack_rate: 0.03        # 3% — CDC VSP outbreak threshold
  lockdown_attack_rate: 0.05       # 5% — extreme measure
  respiratory_mode: false          # set per-pathogen via overrides
  pcr_confirm_ct_threshold: 35.0
```

#### 6. Campaign manifest surveillance config additions

Add pathogen-type escalation overrides:
```json
"escalation_overrides": {
  "respiratory": {
    "escalation": {
      "respiratory_mode": true,
      "respiratory_alert_cases": 1,
      "suspect_attack_rate": 0.01
    }
  }
}
```

#### 7. Ship simulation loop changes

`picard_framework/simulation/ship_simulation.py`:
- Pass `state` to `check_escalation()` (currently only passes cfg)
- Update `state.cumulative_confirmed_cases` each epoch
- PCR sampling cadence should vary by level:
  - BASELINE: cadence 4
  - ALERT: cadence 2  
  - SUSPECTED+: cadence 1

#### 8. Tests needed

- `test_escalation_levels.py`:
  - BASELINE → ALERT at 3 sick calls
  - ALERT → SUSPECTED at 2% AR  
  - SUSPECTED → CONFIRMED at 3%
  - CONFIRMED → LOCKDOWN at 5%
  - Respiratory mode: ALERT at 1 confirmed case
  - No backward transitions
  - Full lockdown only at LOCKDOWN level (not CONFIRMED)

- Update `test_orchestrator.py`:
  - Compliance gate applies at ALERT, SUSPECTED, CONFIRMED
  - Compliance gate does NOT apply at LOCKDOWN
  - confine_all only fires at LOCKDOWN

- Verify T7 compliance now produces refusers at ALERT/SUSPECTED/CONFIRMED levels

#### 9. Backward compatibility

- Old manifests with 2-level escalation should still work
- If config has no `suspect_attack_rate` etc., fall back to old behavior
- `SUSPECTED` and `CONFIRMED` status strings preserved for telemetry compatibility
