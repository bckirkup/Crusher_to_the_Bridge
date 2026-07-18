# Issue 111 — Enhanced Wearables Model: Implementation Plan

> **Status:** Plan / partially superseded. Confounder-aware cascade scoring landed in
> [WEARABLE_ANOMALY_REDESIGN.md](WEARABLE_ANOMALY_REDESIGN.md) and
> `engines/wearable_anomaly_scorer.py`. Treat remaining sections as a backlog, not
> current operator guidance. See [docs/README.md](README.md).

## Summary

Replace the current binary "every agent in a class gets the same device" wearable system
with a richer, config-driven model supporting **multi-device per agent**,
**per-device sensitivity/specificity**, **confounders** (seasickness, alcohol, etc.),
**signal latency**, **partial coverage** (fraction of each class issued a device),
**visibility tiers** (medical-staff-observable vs. wearer-only), **configurable
chronic-disease → device assignment**, and **device-level economic costs**.

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
├─ AgentWearableState       per-agent baselines + drift (single device)
├─ WearableMonitor          fleet manager: initialize_agent → generate_epoch_data
└─ build_wearable_monitor_from_config()

crusher_labs/modalities/wearable.py
└─ WearableDataStream       observation-noise layer → fleet summary for stoplight

orchestrator_init.py → init_wearable_monitors()
orchestrator_epoch.py → step_wearable_monitoring() / step_diagnostic_cascade()
```

Currently **every** agent in a mapped class receives exactly **one** device.
There are no multi-device stacks, no sensitivity/specificity curves, no
confounder modelling, no partial coverage, no chronic-disease-based device
assignment, and no concept of who can see the wearable data (medical staff
vs. wearer only).

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

#### 1c. Multi-device per agent + coverage fraction

The `class_device_map` changes from a 1:1 mapping (agent_class → single
device_id) to a **list-of-device-assignments** per class.  Each entry
specifies a device, its coverage fraction, and its visibility tier.  An
agent in a given class independently rolls each device's coverage — so
an agent may end up wearing zero, one, or multiple devices.

```yaml
  class_device_map:
    # ── Default (fallback for unmapped classes) ────────────────
    - agent_class: "default"
      devices:
        - device_id: "oura_ring"
          coverage: 1.0
          visibility: "medical_staff"

    # ── Crew medical: watch + ring ────────────────────────────
    - agent_class: "crew_medical"
      devices:
        - device_id: "garmin_watch"
          coverage: 1.0
          visibility: "medical_staff"
        - device_id: "oura_ring"
          coverage: 0.50             # half also get a ring for sleep data
          visibility: "medical_staff"

    # ── Passengers: partial ring coverage ─────────────────────
    - agent_class: "passenger_general"
      devices:
        - device_id: "oura_ring"
          coverage: 0.60
          visibility: "wearer_only"

    # ── Elderly passengers: ring + insurance-incentivised CGM ─
    - agent_class: "passenger_elderly"
      devices:
        - device_id: "oura_ring"
          coverage: 0.40
          visibility: "both"
        - device_id: "cgm_patch"
          coverage: 0.30
          visibility: "both"
```

**How it works:**

- For each agent, `WearableMonitor.initialize_agent()` iterates over the
  device list for the agent's class (or the `"default"` entry).  For each
  device, it draws a Bernoulli sample with probability `coverage`.  Devices
  that pass are instantiated with their own `AgentWearableState`.
- An agent may have **zero or more** `AgentWearableState` objects, stored in
  a list rather than a single value.  Each state tracks its own baselines,
  drift, and visibility.
- `generate_epoch_data()` produces a list of per-device result dicts per
  agent.  The downstream modality and stoplight pipeline aggregate across
  devices — a fever flag on *any* device counts as a fever for that agent;
  anomaly channels are unioned across devices.

#### 1c-bis. Backward-compatible shorthand

For backward compatibility, the old single-device format is still accepted:

```yaml
    - agent_class: "default"
      device_id: "oura_ring"       # old format — implicitly coverage=1.0, visibility="medical_staff"
```

The parser detects the presence of `device_id` (singular) vs. `devices`
(list) and normalizes to the list form internally.

#### 1d-bis. Chronic disease → device assignment (configurable)

A new optional `chronic_disease_device_map` section allows devices to be
assigned based on an agent's chronic disease IDs, checked *after* class-based
assignment.  This is additive — chronic-disease devices are appended to
whatever the class-based map already assigned.

```yaml
  chronic_disease_device_map:
    - disease_id: "type2_diabetes"
      device_id: "cgm_patch"
      coverage: 0.80              # 80% of diabetics get a CGM
      visibility: "both"
    - disease_id: "copd"
      device_id: "pulse_ox_patch"
      coverage: 0.60
      visibility: "medical_staff"
```

**How it works:**

- After class-based device assignment, `initialize_agent()` checks the
  agent's `chronic_disease_ids` (already populated by orchestrator_chronic).
- For each matching `disease_id` entry, it rolls coverage and, if the agent
  doesn't already have that device, adds it to their device list.
- This lets the simulation model insurance-incentivized programs that issue
  CGMs specifically to diabetic passengers, pulse-ox patches to COPD
  patients, etc.

#### 1d. Visibility tiers

Visibility is now specified **per device per class** in the `devices` list
(see §1c above).  Valid values:

- `"medical_staff"` — data enters `WearableDataStream.query_ground_truth()`
  → protocol engine stoplights (current behavior).
- `"wearer_only"` — data is generated but excluded from fleet anomaly/fever
  counts and agent-level stoplights.  The wearer-only data still influences
  the agent's **behavioral** decisions — a wearer who sees their own fever
  flag may self-report via sick call (modelled as a boost to
  `sick_call_probability` for that agent that epoch).
- `"both"` — both pathways active.

Each `AgentWearableState` stores its own `visibility` field.  When an agent
has multiple devices with different visibility, each device's data is routed
independently — e.g., a `medical_staff` watch feeds stoplights while a
`wearer_only` ring only influences the agent's sick-call behavior.

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
| `WearableMonitor.__init__()` | Accept `class_device_assignments: dict[str, list[dict]]` (class → list of {device_id, coverage, visibility}) |
| `WearableMonitor._agent_states` | Change from `dict[int, AgentWearableState]` to `dict[int, list[AgentWearableState]]` (multi-device) |
| `WearableMonitor.initialize_agent()` | Iterate device list for agent's class, Bernoulli-sample each, then append chronic-disease devices; return list of states |
| `WearableMonitor.generate_epoch_data()` | Produce per-device results for each agent; aggregate anomaly/fever across devices |
| New: `_sample_confounders()` | Per-epoch confounder activation for each agent |
| New: `_apply_confounder_effects()` | Modify channel baseline/noise during hourly generation |
| `_generate_agent_epoch()` | Integrate confounder effects and detection-profile gating |
| New: `apply_detection_profile()` | Post-hoc sensitivity/specificity filter on anomaly + fever flags |
| `build_wearable_device_from_config()` | Parse new YAML fields |
| `build_wearable_monitor_from_config()` | Parse multi-device class_device_map + chronic_disease_device_map |

#### 2b. `crusher_labs/modalities/wearable.py` — `WearableDataStream`

| Change | Description |
|--------|-------------|
| `query_ground_truth()` | Accept `visibility_map: dict[int, list[str]]` (agent → list of visibilities, one per device); exclude `wearer_only`-only agents from fleet counts |
| Return payload | Add `wearer_only_agents: list[int]` and `staff_visible_agents: list[int]` |
| Multi-device aggregation | Union anomaly channels, OR fever flags across an agent's devices for fleet summary |

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
  - Old single-device `class_device_map` format (`device_id` key) is auto-
    normalized to the new `devices` list format (coverage=1.0,
    visibility="medical_staff") — existing configs work unchanged.
  - `coverage` defaults to `1.0` (all agents get device = current behavior)
  - `visibility` defaults to `"medical_staff"` (current behavior)
  - `detection_profile` defaults to `None` → no sensitivity/specificity gating
    (raw anomaly flags pass through = current behavior)
  - `confounders` defaults to `[]` (no confounders = current behavior)
  - `chronic_disease_device_map` defaults to `[]` (no disease-based devices)
- Existing `config.yaml` files will work without modification.
- The glucose channel is added to defaults but only used if a device includes it.
- `_agent_states` changes from `dict[int, AgentWearableState]` to
  `dict[int, list[AgentWearableState]]`.  All internal callers are updated.
  The public `agent_states` property and `to_dict()` methods are updated to
  expose the list form.

---

### 5. Implementation Order

| Phase | Scope | Risk |
|-------|-------|------|
| **Phase 1** | Multi-device per agent + coverage fraction + visibility tier | Medium — core data-structure change (single → list of states) |
| **Phase 2** | Chronic disease → device assignment (configurable) | Low — additive post-class device injection |
| **Phase 3** | Confounder model | Medium — new per-epoch sampling + bias injection |
| **Phase 4** | Detection profile (sensitivity/specificity + latency) | Medium — post-hoc probabilistic gating |
| **Phase 5** | Glucose channel + `cgm_patch` device | Low — new channel defaults + device config |
| **Phase 6** | Economic costs | Low — extend cost_ledger debits |
| **Phase 7** | Sanity checker + tests + docs | Low — validation + coverage |

Phase 1 is the most structurally invasive (single-device → multi-device
data structures).  Phases 2-4 are functional extensions.  Phases 5-7 are
add-ons.  Each phase passes CI independently.

---

### 6. Estimated Scope

- ~300-400 lines new/modified code in `wearable_monitor.py` (multi-device refactor + confounders + detection profile)
- ~80 lines in `wearable.py` (multi-device aggregation + visibility routing)
- ~60 lines in `orchestrator_init.py` / `orchestrator_epoch.py` (multi-device wiring + chronic-disease device map)
- ~80 lines in `sanity_checker.py` (Pydantic models + validation for multi-device + chronic-disease map)
- ~60 lines config additions (`config.yaml`, `resource_costs.json`)
- ~250 lines tests
- ~60 lines docs

Total: ~890-990 lines across ~12 files.

---

### 7. Design Decisions (Resolved)

1. **Multi-device per agent:** Yes — each agent can wear multiple devices.
   `class_device_map` entries specify a `devices` list; each device is
   independently coverage-sampled.  Old single-device format is auto-
   normalized for backward compatibility.

2. **Chronic disease → device assignment:** Configurable via a new
   `chronic_disease_device_map` section.  Devices are appended *after*
   class-based assignment, so a diabetic passenger may end up with an Oura
   ring (from class map) plus a CGM patch (from disease map).

3. **Confounder temporal patterns:** Simple per-epoch prevalence draw for v1.
   Hourly profiles may be added in a future iteration if needed.
