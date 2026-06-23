---
name: wearable-anomaly-scoring
description: Configure and test confounder-aware wearable infection scoring that gates diagnostic cascade Tier-0 entry. Use when editing engines/wearable_anomaly_scorer.py, wearable_monitoring.anomaly_detection in config.yaml, or cascade_entry infection_score fusion rules.
---

# Wearable Anomaly Scoring

## Problem Solved

Naive multi-channel anomaly counting (`anomaly_count >= 2`) floods Tier-0
when confounders (seasickness, alcohol, exercise) shift several correlated
channels at once. The scorer computes a weighted residual `infection_score`
after confounder template matching and fleet-wide downweighting.

## Key Files

| Path | Role |
|------|------|
| `engines/wearable_anomaly_scorer.py` | `WearableAnomalyScorer` — cosine template match, fleet rates, weighted sum |
| `engines/wearable_monitor.py` | Two-pass scoring in `generate_epoch_data()`; signed z-scores per channel |
| `crusher_labs/cascade_entry.py` | `evaluate_wearable_alert()` — supports `infection_score` fusion rules |
| `crusher_labs/config.yaml` | `wearable_monitoring.anomaly_detection` block |
| `data/config/diagnostic_cascade*.json` | `cascade_entry.wearable_alert_fusion` rules |

## Config (`wearable_monitoring.anomaly_detection`)

```yaml
anomaly_detection:
  enabled: true
  anomaly_z_threshold: 2.0
  infection_score_threshold: 1.5
  fleet_anomaly_floor: 0.15
  fleet_anomaly_downweight: 0.1
  confounder_match_threshold: 0.7
  channel_infection_weights:
    heart_rate: 0.3
    hrv: 0.3
    body_temp: 1.0
    spo2: 0.8
    sleep_score: 0.2
    activity_score: 0.4
    respiratory_rate: 0.6
    glucose: 1.0
```

Cascade entry default rule (in `diagnostic_cascade.json`):

```json
{"signal": "infection_score", "operator": ">", "value": 1.5}
```

Fever still triggers Tier-0 directly. Fleet stoplight SOPs (SOP-013/014) are
**unchanged** — they use shipwide `anomaly_rate`, not `infection_score`.

## Scoring Flow

1. Per-channel signed z-scores and anomaly flags (existing)
2. Per-device detection profile gating (existing)
3. Multi-device fusion (existing)
4. Fleet per-channel anomaly rates across monitored agents
5. Per-agent `infection_score` + `matched_confounders` via `WearableAnomalyScorer`
6. `evaluate_wearable_alert()` in `step_diagnostic_cascade()` for Tier-0 entry

## Quick Commands

```bash
python3 -m pytest tests/test_wearable_anomaly_scorer.py tests/test_cascade_entry.py -v --tb=short
python3 tools/sanity_checker.py --from-config
```

### Smoke: measure Tier-0 entry rate

```bash
python3 -c "
from picard_framework import PicardRunSpec, ShipSimulation
spec = PicardRunSpec.from_legacy_yaml(repo_root='.', num_epochs=6)
result = ShipSimulation(spec, display=False, repo_root='.').run(n_epochs=6)
n = sum(len(r.get('diagnostic_cascade', {}).get('new_tier0_agents', [])) for r in result.history)
agents = len(result.history[0].get('agents', []))
print(f'Tier-0 entries: {n} over {len(result.history)} epochs, {agents} agents')
"
```

Expected: low single-digit % per agent-epoch on clean cruise (not ~66%).

## Confounder Templates

Built-in defaults in `DEFAULT_CONFOUNDER_TEMPLATES` (seasickness, alcohol,
exercise, meal_glucose_spike, wrist_motion). Override per device via
`template_z_vector` on confounder definitions, or globally via
`anomaly_detection.confounder_templates`.

## What Does NOT Change

- Per-channel z-score computation and device noise models
- Detection profile sensitivity/specificity gating (per-device, before fusion)
- Cascade tier structure, SOP gating, fleet escalation rules
- `stoplight_from_wearable_agent()` still uses `anomaly_count` for per-agent RED/AMBER
