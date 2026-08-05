# Per-Platform Medical Response Parameters Spec

## Overview

Adds a `medical_response` block to each platform's `voyage_config.json` that
configures how aggressively and effectively the shipboard medical team detects
and responds to infectious disease cases. These parameters modify the syndromic
surveillance and cascade systems already in the model.

## Rationale

Cruise ship medical care varies structurally by ship class:
- Expedition (50-200 pax): 1 doctor ± 1 nurse, knows passengers personally,
  remote setting incentivizes early conservative isolation
- Luxury/Classic (300-2,000 pax): 1-2 doctors, 2-3 nurses, high service ratio,
  personalized care expectations
- Contemporary/Spirit (2,000-4,000 pax): 2 doctors, 4-6 nurses, protocolized
  high-volume care
- Mega (4,000-7,000+ pax): 2 doctors, 4-6 nurses + paramedics + HCAs,
  high volume, more anonymity, slower per-capita signal detection

VSP outbreak data (~5-6% AR flat across ship sizes) already includes these
real-world medical responses. Calibrating model(none_true) against VSP data
was incorrect — we should calibrate model(syndromic + medical_response) against
VSP observed AR.

## Data Model

Added to each platform's `voyage_config.json`:

```json
{
  "medical_response": {
    "sick_call_probability": 0.7,
    "isolation_compliance": 0.90,
    "detection_delay_epochs": 2,
    "crew_screening_interval_epochs": null,
    "notes": "Classic/premium: moderate attentiveness, structured clinic hours"
  }
}
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sick_call_probability` | float [0,1] | Probability a symptomatic agent reports to medical per epoch. Higher = faster detection. | 0.5 (current global default) |
| `isolation_compliance` | float [0,1] | Probability an agent complies with cabin isolation order. | 0.85 |
| `detection_delay_epochs` | int >= 0 | Minimum epochs after symptom onset before sick call is possible (models patient denial / "push through it" behavior). | 2 |
| `crew_screening_interval_epochs` | int or null | If set, crew are proactively screened at this interval even without symptoms. null = no proactive screening. | null |

### Per-Platform Defaults

| Parameter | Expedition | Classic | Spirit | Mega |
|-----------|-----------|---------|--------|------|
| `sick_call_probability` | 0.9 | 0.7 | 0.5 | 0.4 |
| `isolation_compliance` | 0.95 | 0.90 | 0.85 | 0.80 |
| `detection_delay_epochs` | 1 | 2 | 2 | 3 |
| `crew_screening_interval_epochs` | null | null | null | null |

Rationale for gradient:
- Expedition passengers are older, more health-conscious, in closer contact
  with medical staff, and aware of remote evacuation risk. They report early.
- Mega passengers are more anonymous, may resist cabin isolation to protect
  vacation investment, and the higher clinic volume means longer waits.
- Detection delay on expedition is 1 epoch (1 hour) because the doctor may
  notice symptoms at dinner. On mega it's 3 epochs because passengers have
  to actively seek out the medical center.
- Isolation compliance is highest on expedition (nowhere to go, staff
  monitor compliance) and lowest on mega (large ship, harder to enforce).

## Engine Integration

### Reading the config

The orchestrator reads `medical_response` from `voyage_config.json` at
initialization (same pattern as `dining_meal_weights`):

```python
def apply_medical_response_config(cfg, voyage_cfg):
    med = voyage_cfg.get("medical_response")
    if not med:
        return cfg
    syndromic = dict(cfg.get("syndromic", {}))
    syndromic["sick_call_probability"] = med.get(
        "sick_call_probability",
        syndromic.get("sick_call_probability", 0.5)
    )
    # ... other params ...
    cfg = dict(cfg)
    cfg["syndromic"] = syndromic
    return cfg
```

### Interaction with surveillance strategies

- `none_true`: medical_response params are ignored (no detection)
- `syndromic`: sick_call_probability and detection_delay from medical_response
  override the global syndromic config
- `cascade` / `cascade_mpx`: sick_call feeds into cascade entry point;
  medical_response modifies the entry probability and compliance

### Backward compatibility

When no `medical_response` block is present, all parameters fall back to
existing global defaults. No change to existing campaigns.

## Campaign Override

For the calibration sweep, `sick_call_probability` can be overridden via
campaign config_overrides without modifying the voyage_config files:

```json
{
  "config_overrides": {
    "syndromic": {
      "sick_call_probability": 0.7
    }
  }
}
```

This allows sweeping sick_call_probability as a campaign factor.
