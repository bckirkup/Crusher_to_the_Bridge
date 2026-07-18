# CTB Wearable Anomaly Detection Redesign: Confounder-Aware Scoring

> **Status:** Implemented. Living operator notes live under wearable / cascade skills
> (`.agents/skills/wearable-anomaly-scoring/`). This file is the design record.

## Problem

The current anomaly detector fires a z-score threshold on each channel independently,
then counts how many channels are anomalous. With confounders (seasickness 15%,
alcohol 8%, exercise 20%) affecting multiple correlated channels simultaneously,
66% of agents enter the diagnostic cascade on a typical cruise — overwhelming the
medical system with false referrals that cost $45/test and erode passenger tolerance.

## Current Flow

```
Per agent, per epoch:
  For each channel:
    z = (observed - baseline_mean) / baseline_std
    if |z| > anomaly_z_threshold (2.0): mark anomaly

  anomaly_count = number of anomalous channels

  if fever OR anomaly_count >= 2:
    enter cascade Tier 0
```

No consideration of which channels are anomalous, whether the pattern matches a
known confounder, or what the rest of the ship looks like that epoch.

## Proposed Flow

```
Per agent, per epoch:
  1. Compute per-channel z-scores (same as now)

  2. Confounder template matching:
     For each active confounder template (seasickness, alcohol, exercise, ...):
       score = cosine similarity between agent's z-vector and template
       if score > confounder_match_threshold:
         flag channels explained by this confounder

  3. Fleet context adjustment:
     Compute fleet-wide anomaly rate per channel this epoch
     If a channel's fleet anomaly rate > fleet_anomaly_floor (e.g., 0.15):
       downweight that channel (it's a ship-wide event, not individual)

  4. Residual infection score:
     Weight each channel by its infection_signal_weight (config-driven)
     Zero out channels explained by confounders (step 2)
     Downweight channels flagged by fleet context (step 3)
     infection_score = weighted sum of residual anomalous channels

  5. Alert decision:
     if fever: enter cascade (fever is hard to fake with confounders)
     elif infection_score > infection_score_threshold: enter cascade
     else: no alert
```

## New Config Parameters

### In wearable_monitoring section of config.yaml:

```yaml
wearable_monitoring:
  anomaly_detection:
    anomaly_z_threshold: 2.0  # legacy, still used for per-channel flag

    # Infection signal weights per channel.
    # Higher = more informative for infection vs confounder.
    # Temp and glucose are least confounded.
    channel_infection_weights:
      heart_rate: 0.3
      hrv: 0.3
      body_temp: 1.0
      spo2: 0.8
      sleep_score: 0.2
      activity_score: 0.4
      respiratory_rate: 0.6
      glucose: 1.0

    # Weighted residual score threshold to trigger alert
    infection_score_threshold: 1.5

    # Fleet context: if this fraction of monitored agents show anomaly
    # on a channel, downweight it (ship-wide event like rough seas)
    fleet_anomaly_floor: 0.15
    fleet_anomaly_downweight: 0.1

    # Cosine similarity threshold for confounder template matching
    confounder_match_threshold: 0.7
```

### Confounder templates (extend existing confounder definitions):

Existing configs already define which channels are affected and bias direction.
Add a normalized template vector for matching:

```yaml
confounders:
  - confounder_id: "seasickness"
    # ...existing fields...
    template_z_vector:
      heart_rate: 2.0       # elevated
      hrv: -2.5             # depressed
      body_temp: 0.0        # unaffected
      spo2: 0.0             # unaffected
      activity_score: 0.5   # slightly elevated (moving around)
      glucose: 0.0          # unaffected

  - confounder_id: "alcohol"
    template_z_vector:
      heart_rate: 1.5
      hrv: -2.0
      body_temp: 0.0
      sleep_score: -2.0
      activity_score: 0.0
      glucose: 1.5          # transient spike

  - confounder_id: "exercise"
    template_z_vector:
      heart_rate: 4.0
      hrv: -1.0
      activity_score: 3.0
      body_temp: 0.3
      spo2: 0.0
      glucose: -0.5
```

## Implementation

### New module: engines/wearable_anomaly_scorer.py

A WearableAnomalyScorer class that:

1. Takes config (channel weights, thresholds, confounder templates) at init
2. score_agent(agent_z_scores, fleet_anomaly_rates) returns:
   - infection_score (float): weighted residual after confounder removal
   - matched_confounders (list[str]): which confounders explain the pattern

Logic:
- For each confounder template, compute cosine similarity with agent's z-vector
- If similarity > threshold, mark those channels as confounder-explained
- For each anomalous channel: multiply z-score by channel weight, zero if
  confounder-explained, downweight if fleet-wide anomaly rate is high
- Sum = infection_score

### Integration: WearableMonitor.generate_epoch_data()

After per-agent per-channel z-score computation (existing), add a second pass:

1. Compute fleet-wide anomaly rates per channel (how many agents have anomaly
   on each channel this epoch)
2. For each agent, call scorer to get infection_score
3. Add infection_score and matched_confounders to the agent's result dict

### Integration: cascade entry evaluation (orchestrator_epoch.py)

Replace:
  if data.get("fever") or data.get("anomaly_count", 0) >= 3:
      wearable_red_ids.append(agent_id)

With:
  if data.get("fever") or data.get("infection_score", 0) > threshold:
      wearable_red_ids.append(agent_id)

The threshold comes from cascade_entry.wearable_alert_fusion config, which
already supports configurable rules. Add "infection_score" as a supported
signal type alongside "fever" and "anomaly_count".

### Fleet context computation

WearableMonitor already loops over all agents in generate_epoch_data().
After the first pass (generate readings), compute fleet stats:

  fleet_anomaly_rates[channel] = n_anomalous_on_channel / n_monitored

Pass into the second pass (scoring). This is O(agents * channels) — trivial.

## What Does NOT Change

- Per-channel z-score computation
- Device noise models, infection response profiles, phase boundaries
- Detection profile sensitivity/specificity gating (applied after scoring)
- Cascade tier structure, SOP gating, fleet escalation rules
- Clinical test correlation matrix
- Chronic disease modifiers

## Expected Outcome

- Cascade entry drops from ~66% to roughly true infection rate + small margin
  (30-40% in outbreak cruise, 5-10% in clean cruise)
- Sensitivity parameter starts mattering (noise floor is lower)
- Temp and glucose anomalies drive most alerts (highest weights, least confounded)
- Ship-wide seasickness does NOT trigger mass cascade entry
- Passengers are not told to report to medical for seasickness patterns

## Testing

1. Clean cruise (no pathogen): cascade entry should be <10% of agents
2. Outbreak (dose_adj=7.0): cascade entry should correlate with infection
3. Confounder storm (seasickness prevalence 0.50): entry should not scale
4. Sensitivity sweep: repeat 4x3 grid, sensitivity should produce a gradient
