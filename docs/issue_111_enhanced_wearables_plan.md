# Issue 111 — Enhanced Wearables Model: Implementation Plan

## Summary

Replace the current binary "every agent in a class gets the same device" wearable system
with a richer, config-driven model supporting **per-device sensitivity/specificity**,
**confounders** (seasickness, alcohol, etc.), **signal latency**, **partial coverage**
(fraction of each class issued a device), **visibility tiers** (medical-staff-observable
vs. wearer-only), and **device-level economic costs**.

The existing `WearableDevice` / `WearableMonitor` / `WearableDataStream` architecture
is already device-registry-driven — the enhancement extends each device definition and
adds new routing logic without replacing the core flow.

---

## Current Architecture (for context)

```
config.yaml
└─ wearable_monitoring:
    ├─ devices: [oura_ring, garmin_watch]   ← channel list, noise, infection_responses
    ├─ class_device_map:                    ← agent_class → device_id  (1:1 per class)
    └─ observation layer params             ← obs noise σ, sync dropout, anomaly z

engines/wearable_monitor.py
├─ WearableDevice           device type definition
├─ AgentWearableState       per-agent baselines + drift
├─ WearableMonitor          fleet manager: initialize_agent → generate_epoch_data
└─ build_wearable_monitor_from_config()

crusher_labs/modalities/wearable.py
└─ WearableDataStream       observation-noise layer → fleet summary for stoplight

orchestrator_init.py → init_wearable_monitors()
orchestrator_epoch.py → step_wearable_monitoring() / step_diagnostic_cascade()
```

Currently **every** agent in a mapped class receives a device. There are no
sensitivity/specificity curves, no confounder modelling, no partial coverage,
and no concept of who can see the wearable data (medical staff vs. wearer only).

---

## Proposed Changes

### 1. Config Schema Additions (`config.yaml` wearable_monitoring block)

#### 1a. Per-device sensitivity / specificity / latency

Add to each device entry:

```yaml
devices:
  - device_id: "oura_ring"
    channels: [...]
    # NEW ──────────────────────────────────────────────────
    detection_profile:
      sensitivity: 0.78          # P(alert | true infection)
      specificity: 0.92          # P(no alert | no infection)
      alert_latency_hours: 6     # hours post-infection before device CAN alert
      fever_sensitivity: 0.85    # P(fever flag | true fever ≥ 37.8°C)
      fever_specificity: 0.94    # P(no fever flag | no true fever)
    # ──────────────────────────────────────────────────────
```

**How it works in the simulation:**

- After `WearableMonitor.generate_epoch_data()` produces raw readings, a new
  `apply_detection_profile()` step probabilistically suppresses/injects anomaly
  and fever flags according to the device's sensitivity/specificity.
- `alert_latency_hours` delays the first epoch in which a true positive *can*
  fire (analogous to TAT for lab modalities).

#### 1b. Confounder definitions (per device)

```yaml
    confounders:
      - confounder_id: "seasickness"
        prevalence: 0.15                # fraction of agents affected per epoch (sampled)
        affected_channels:
          heart_rate:   { bias: 8.0, noise_mult: 1.5 }
          hrv:          { bias: -12.0, noise_mult: 1.8 }
          activity_score: { bias: -10.0, noise_mult: 1.3 }
        unaffected_channels: [body_temp, spo2, sleep_score]
        # triggers: who is susceptible?
        susceptible_classes: ["passenger_general", "passenger_family", "passenger_elderly"]
        susceptible_role_group: "passenger"   # shorthand

      - confounder_id: "alcohol"
        prevalence: 0.08
        affected_channels:
          hrv:          { bias: -10.0, noise_mult: 2.0 }
          heart_rate:   { bias: 6.0, noise_mult: 1.4 }
          sleep_score:  { bias: -8.0, noise_mult: 1.5 }
        unaffected_channels: [body_temp, spo2]
        susceptible_classes: ["passenger_general", "passenger_family"]

      - confounder_id: "exercise"
        prevalence: 0.20
        affected_channels:
          heart_rate:   { bias: 15.0, noise_mult: 1.2 }
          activity_score: { bias: 20.0, noise_mult: 1.0 }
        unaffected_channels: [body_temp, spo2, sleep_score, hrv]
        susceptible_classes: []  # all classes
```

**How it works:**

- Each epoch, for each agent, each confounder is activated with probability
  `prevalence` (only if agent is in a susceptible class).
- Active confounders add `bias` to the channel baseline during hourly reading
  generation and multiply `sigma` by `noise_mult`.
- This directly increases false-positive anomaly rates on some channels while
  leaving others unaffected — exactly matching the issue's example ("seasickness
  confounds HR but not glucose; alcohol confounds HRV but not temp").

#### 1c. Coverage fraction (per class-device assignment)

```yaml
  class_device_map:
    - agent_class: "default"
      device_id: "oura_ring"
      coverage: 1.0                # all agents in unmapped classes
    - agent_class: "crew_medical"
      device_id: "garmin_watch"
      coverage: 1.0                # all medical crew
    - agent_class: "passenger_general"
      device_id: "oura_ring"
      coverage: 0.60               # 60% of general passengers
    - agent_class: "passenger_elderly"
      device_id: "cgm_patch"       # (new device — glucose + temp)
      coverage: 0.30               # only 30% — insurance-incentivised subset
```

**How it works:**

- `WearableMonitor.initialize_agent()` draws a Bernoulli sample with
  probability `coverage` to decide whether each agent actually receives the
  device.  Agents that fail the draw get no wearable (return `None`).
- The class_device_map entry gains the optional field `coverage` (default 1.0
  = current behavior).

#### 1d. Visibility tiers

```yaml
    visibility: "medical_staff"    # or "wearer_only" or "both"
```

Add per class-device-map entry:

```yaml
  class_device_map:
    - agent_class: "crew_medical"
      device_id: "garmin_watch"
      coverage: 1.0
      visibility: "medical_staff"      # data flows into stoplight system
    - agent_class: "passenger_general"
      device_id: "oura_ring"
      coverage: 0.60
      visibility: "wearer_only"        # data does NOT flow into surveillance
    - agent_class: "passenger_elderly"
      device_id: "cgm_patch"
      coverage: 0.30
      visibility: "both"               # patient sees + medical staff sees
```

**How it works:**

- `medical_staff`: data enters `WearableDataStream.query_ground_truth()` →
  protocol engine stoplights (current behavior).
- `wearer_only`: data is generated (wearable produces readings) but is
  excluded from fleet anomaly/fever counts and from the agent-level stoplights.
  The wearer-only data still influences the agent's **behavioral** decisions —
  a wearer who sees their own fever flag may self-report via sick call (modelled
  as a boost to `sick_call_probability` for that agent that epoch).
- `both`: both pathways active.
- A new field on `AgentWearableState.visibility` stores this.

#### 1e. Device economic costs

Add to `resource_costs.json`:

```json
"wearable_device_costs": {
  "oura_ring": {
    "unit_cost_usd": 299.00,
    "monthly_subscription_usd": 5.99,
    "description": "Oura Ring Gen3 with health monitoring subscription"
  },
  "garmin_watch": {
    "unit_cost_usd": 349.00,
    "monthly_subscription_usd": 0.00,
    "description": "Garmin Venu 3 fitness watch, no subscription"
  },
  "cgm_patch": {
    "unit_cost_usd": 75.00,
    "monthly_subscription_usd": 0.00,
    "replacement_days": 14,
    "description": "Continuous glucose monitor patch (Abbott FreeStyle Libre)"
  }
}
```

The `CostLedger` will debit device procurement costs at initialization and
per-epoch subscription/replacement costs during the simulation.

---

### 2. Code Changes

#### 2a. `engines/wearable_monitor.py`

| Change | Description |
|--------|-------------|
| `WearableDevice` | Add `detection_profile: dict`, `confounders: list[dict]` fields |
| `AgentWearableState` | Add `visibility: str`, `active_confounders: dict[str, bool]` |
| `WearableMonitor.__init__()` | Accept `class_coverage_map: dict[str, float]` and `class_visibility_map: dict[str, str]` |
| `WearableMonitor.initialize_agent()` | Bernoulli-sample coverage; store visibility on state |
| New: `_sample_confounders()` | Per-epoch confounder activation for each agent |
| New: `_apply_confounder_effects()` | Modify channel baseline/noise during hourly generation |
| `_generate_agent_epoch()` | Integrate confounder effects and detection-profile gating |
| New: `apply_detection_profile()` | Post-hoc sensitivity/specificity filter on anomaly + fever flags |
| `build_wearable_device_from_config()` | Parse new YAML fields |
| `build_wearable_monitor_from_config()` | Parse coverage + visibility from class_device_map |

#### 2b. `crusher_labs/modalities/wearable.py` — `WearableDataStream`

| Change | Description |
|--------|-------------|
| `query_ground_truth()` | Accept `visibility_map: dict[int, str]`; exclude `wearer_only` agents from fleet counts |
| Return payload | Add `wearer_only_agents: list[int]` and `staff_visible_agents: list[int]` |

#### 2c. `orchestrator_init.py` — `init_wearable_monitors()`

| Change | Description |
|--------|-------------|
| Pass coverage/visibility maps | Forward from parsed config to `WearableMonitor` |
| Debit initial device costs | Query `resource_costs.json` for per-device procurement |

#### 2d. `orchestrator_epoch.py` — `step_wearable_monitoring()`

| Change | Description |
|--------|-------------|
| Forward visibility map | From monitor to modality |
| Debit per-epoch device costs | Subscription / replacement costs via `CostLedger` |

#### 2e. `orchestrator_epoch.py` — `step_diagnostic_cascade()`

| Change | Description |
|--------|-------------|
| Wearer-only sick-call boost | When an agent has `wearer_only` visibility and their device flags fever/anomaly, boost their `sick_call_probability` for that epoch |

#### 2f. `crusher_labs/protocol_engine.py`

| Change | Description |
|--------|-------------|
| No structural changes | Stoplights already key on agent/fleet instruments; visibility filtering happens upstream in `WearableDataStream` |

#### 2g. `tools/sanity_checker.py`

| Change | Description |
|--------|-------------|
| `WearableDeviceEntry` | Add optional `detection_profile` and `confounders` Pydantic models |
| `ClassDeviceMapEntry` | Add optional `coverage: float` ([0,1]) and `visibility: str` |
| `_check_wearable_monitoring()` | Validate new fields, cross-ref confounder channels ⊆ device channels |

#### 2h. `data/config/resource_costs.json`

| Change | Description |
|--------|-------------|
| Add `wearable_device_costs` block | Per-device procurement + subscription costs |

#### 2i. `crusher_labs/config.yaml`

| Change | Description |
|--------|-------------|
| Extend device entries | Add `detection_profile`, `confounders` |
| Extend `class_device_map` entries | Add `coverage`, `visibility` |

#### 2j. New device: `cgm_patch` (continuous glucose monitor)

Add a third device to the default config to demonstrate the glucose channel
referenced in the issue ("seasickness confounds HR but not glucose"):

```yaml
- device_id: "cgm_patch"
  channels:
    - body_temp
    - glucose
  detection_profile:
    sensitivity: 0.72
    specificity: 0.88
    alert_latency_hours: 12
  confounders: []        # glucose not confounded by seasickness or alcohol
```

This requires adding `"glucose"` to `DEFAULT_CHANNEL_BASELINES`,
`DEFAULT_NOISE`, and `DEFAULT_INFECTION_RESPONSES` in `wearable_monitor.py`.

#### 2k. Tests

| File | New / Modified |
|------|----------------|
| `tests/test_orchestrator.py` | Extend existing wearable tests for coverage < 1.0, visibility filtering, confounder injection |
| `tests/test_sanity_checker.py` | Add validation tests for new config fields |
| New: `tests/test_wearable_enhanced.py` | Dedicated test file for detection profile math (sensitivity/specificity sampling), confounder bias application, coverage Bernoulli, visibility routing, and economic cost debits |

#### 2l. Telemetry / recording

| File | Change |
|------|--------|
| `orchestrator_record.py` | Add `coverage_fraction`, `visibility_breakdown`, `confounder_summary` to epoch wearable_monitoring record |
| `schemas/simulation_history.schema.json` | Extend `wearable_monitoring` object |

#### 2m. Documentation

| File | Change |
|------|--------|
| `OPERATORS_MANUAL.md` | Section on enhanced wearable configuration |
| `README.md` | Update wearable feature description |

---

### 3. New data type: glucose channel

| Location | Addition |
|----------|----------|
| `DEFAULT_CHANNEL_BASELINES` | `"glucose": {"mean": 95.0, "std": 12.0, "unit_label": "mg/dL"}` |
| `DEFAULT_NOISE` | `"glucose": {"sigma": 8.0, "drift_rate": 0.5, "dropout_prob": 0.01}` |
| `DEFAULT_INFECTION_RESPONSES` | Infection causes mild hyperglycemia (stress response) |
| `_clamp_channel()` | `"glucose": (40.0, 400.0)` |
| Chronic disease `wearable_baseline_offsets` | `type2_diabetes` adds `"glucose": 35.0` |

---

### 4. Backward Compatibility

- All new config fields are **optional with backward-compatible defaults**:
  - `coverage` defaults to `1.0` (all agents get device = current behavior)
  - `visibility` defaults to `"medical_staff"` (current behavior)
  - `detection_profile` defaults to `None` → no sensitivity/specificity gating
    (raw anomaly flags pass through = current behavior)
  - `confounders` defaults to `[]` (no confounders = current behavior)
- Existing `config.yaml` files will work without modification.
- The glucose channel is added to defaults but only used if a device includes it.

---

### 5. Implementation Order

| Phase | Scope | Risk |
|-------|-------|------|
| **Phase 1** | Coverage fraction + visibility tier | Low — config extension + Bernoulli + routing |
| **Phase 2** | Confounder model | Medium — new per-epoch sampling + bias injection |
| **Phase 3** | Detection profile (sensitivity/specificity + latency) | Medium — post-hoc probabilistic gating |
| **Phase 4** | Glucose channel + `cgm_patch` device | Low — new channel defaults + device config |
| **Phase 5** | Economic costs | Low — extend cost_ledger debits |
| **Phase 6** | Sanity checker + tests + docs | Low — validation + coverage |

Phases 1-3 are the core functional changes. Phases 4-6 are extensions that
round out the feature.  Each phase passes CI independently.

---

### 6. Estimated Scope

- ~200-300 lines new code in `wearable_monitor.py`
- ~50 lines in `wearable.py` (modality visibility routing)
- ~30 lines in `orchestrator_init.py` / `orchestrator_epoch.py`
- ~60 lines in `sanity_checker.py` (Pydantic models + validation)
- ~40 lines config additions (`config.yaml`, `resource_costs.json`)
- ~200 lines tests
- ~50 lines docs

Total: ~650-730 lines across ~12 files.

---

### 7. Open Design Questions

1. **Multi-device per agent?** The issue says "one or more" — do we support an
   agent wearing *both* an Oura ring and a CGM patch? Current architecture
   maps class → single device. Multi-device would require changing
   `class_device_map` to a list-of-devices per class. Recommend deferring
   multi-device to a follow-up issue and keeping 1 device per agent for now.

2. **Chronic disease → device assignment?** The issue mentions issuing devices
   "including chronic disease" as a class. The current chronic disease system
   tags agents with disease IDs *after* class assignment. Options:
   - (A) Add `chronic_disease_override` entries to `class_device_map` that
     match on `disease_id` (e.g., `type2_diabetes` → `cgm_patch`), checked
     after class-based assignment. **Recommended.**
   - (B) Treat chronic disease as a virtual agent class. More invasive.

3. **Confounder temporal patterns?** Should confounders have time-of-day
   profiles (e.g., alcohol only in evening hours)? Adds realism but
   complexity. Recommend a simple per-epoch prevalence draw for v1 and adding
   hourly profiles later if needed.
