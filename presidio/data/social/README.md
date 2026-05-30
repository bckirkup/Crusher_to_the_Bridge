# Social & Decision Engine Configuration Data

Parameter files for the `decision_engine` multi-agent framework.
Each file has a default plus boundary variants for parameter sweeps.

## Files

### Agent Population Profiles
- `default_ship_population.json` — Balanced cruise demographics
- `ship_population_mega_cruise.json` — Older, higher comorbidity (Royal Caribbean/Carnival demographic)
- `ship_population_expedition.json` — Younger, fitter (Hurtigruten/Ponant demographic)

Demographics sourced from CLIA 2023 State of the Industry, CDC NHIS 2022, CDC NIS 2023.

### Information Diffusion
- `information_diffusion_default.json` — Moderate trust, moderate rumor spread
- `information_diffusion_high_trust.json` — Compliant population, slow rumor spread. Boundary: best case for interventions.
- `information_diffusion_low_trust.json` — Skeptical population, fast rumors, rapid trust erosion. Boundary: worst case for compliance.
- `information_diffusion_rapid_rumor.json` — Social-media-connected passengers, viral information spread. Tests: how does fast information flow affect outbreak dynamics?

Key parameters:
| Parameter | Default | High Trust | Low Trust | Rapid Rumor |
|-----------|---------|------------|-----------|-------------|
| initial_severity_belief | 0.10 | 0.15 | 0.05 | 0.08 |
| initial_trust_command | 0.70 | 0.85 | 0.45 | 0.60 |
| trust_decay_per_confinement | -0.04 | -0.02 | -0.08 | -0.05 |
| rumor_amplification_rate | 2.0 | 1.2 | 3.5 | 4.0 |

### Class Interactions
- `class_interactions_default.json` — Baseline contact weights
- `class_interactions_mega_cruise.json` — 0.7× scaling (more segregation)
- `class_interactions_expedition.json` — 1.3× scaling (more mixing)

### Operational Impact Score (OIS) Weights
- `ois_weights_default.json` — Balanced cruise
- `ois_weights_mega_cruise_business.json` — Revenue-weighted, high false-positive penalty
- `ois_weights_expedition_premium.json` — Premium product, small crew = critical
- `ois_weights_military_readiness.json` — Readiness-weighted, engine closure catastrophic

Key OIS comparison:
| Weight | Default | Mega | Expedition | Military |
|--------|---------|------|------------|----------|
| per_passenger_quarantined | 1.0 | 1.5 | 2.5 | N/A |
| per_essential_crew_quarantined | 3.0 | 2.5 | 5.0 | 8.0 |
| per_closed_engine_zone | 5.0 | 4.0 | 6.0 | 15.0 |
| per_general_confinement_epoch | 10.0 | 15.0 | 20.0 | 25.0 |
| false_positive_multiplier | 2.0 | 3.0 | 2.5 | 1.5 |

## Usage

Point to these files in `config.yaml`:
```yaml
social:
  agent_profile_bundle: "presidio/data/social/default_ship_population.json"
  information_diffusion: "presidio/data/social/information_diffusion_default.json"
  class_interactions: "presidio/data/social/class_interactions_default.json"
```

For parameter sweeps, swap to boundary variants:
```yaml
social:
  information_diffusion: "presidio/data/social/information_diffusion_low_trust.json"
```

## Validation Targets

These parameters should be validated against:
- Observed sick-call rates: 30-50% for cruise passengers, 60-80% for military
- VSP outbreak reporting patterns: 2-3% threshold crossing times
- Diamond Princess quarantine compliance patterns
- Holland et al. 2021 post-outbreak cruising intentions (17% "never again")
