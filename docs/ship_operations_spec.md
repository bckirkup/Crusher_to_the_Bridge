# Ship Operations Spec: Voyage Itinerary & Port Visit Layer

## Overview

This spec adds a voyage itinerary layer to the simulation that models the 
temporal structure of a cruise voyage: sea days, port days, embarkation, and 
disembarkation. The layer modifies onboard population density, dining patterns, 
and contact rates on a per-epoch basis.

The initial implementation provides the data model and configuration hooks.
Port visit effects are **flag-gated** via `voyage.effects_enabled` (default
`false`) so existing campaigns are unaffected. When the flag is off (or the
itinerary is empty), every epoch resolves to an identity sea-day state.

**v1 caveats**

- Config lives in `data/platforms/<platform_id>/voyage_config.json` (not in
  `spatial_layout.json`). Picard may deep-merge `config_overrides.voyage`.
- `shore_infection_probability` is config-only: it is **never** wired to
  pathogen introduction. Enabling effects applies ashore exclusion, contact /
  dining multipliers, and embarkation surge only — not off-ship exposure.

## Data Model

### Itinerary Configuration

Added to the platform spatial layout or a new `voyage_config.json`:

```json
{
  "voyage": {
    "total_epochs": 168,
    "epoch_duration_hours": 1,
    "itinerary": [
      {
        "day": 1,
        "type": "embarkation",
        "port": "Fort Lauderdale",
        "embarkation_window_epochs": [10, 14],
        "stateroom_available_epoch": 13,
        "buffet_surge_fraction": 0.80,
        "notes": "70-85% of pax forced into Lido buffet before staterooms open"
      },
      {
        "day": 2,
        "type": "sea_day"
      },
      {
        "day": 3,
        "type": "port_day",
        "port": "Cozumel",
        "disembark_fraction": 0.70,
        "disembark_window_epochs": [8, 10],
        "reembark_window_epochs": [16, 19],
        "shore_infection_probability": 0.0,
        "notes": "60-80% of passengers disembark (report data)"
      },
      {
        "day": 4,
        "type": "sea_day"
      },
      {
        "day": 5,
        "type": "port_day",
        "port": "Grand Cayman",
        "disembark_fraction": 0.65,
        "disembark_window_epochs": [8, 10],
        "reembark_window_epochs": [15, 18],
        "shore_infection_probability": 0.0
      },
      {
        "day": 6,
        "type": "sea_day"
      },
      {
        "day": 7,
        "type": "disembarkation",
        "port": "Fort Lauderdale",
        "disembark_window_epochs": [7, 12],
        "notes": "Passengers leave; crew remain for turnaround"
      }
    ],
    "defaults": {
      "sea_day": {
        "onboard_passenger_fraction": 1.0,
        "contact_rate_multiplier": 1.0,
        "dining_demand_multiplier": 1.0
      },
      "port_day": {
        "onboard_passenger_fraction": 0.30,
        "contact_rate_multiplier": 0.40,
        "dining_demand_multiplier": {
          "breakfast": 0.80,
          "lunch": 0.30,
          "dinner": 0.90
        },
        "notes": "From report: lunch demand drops 50-70% on port days"
      },
      "embarkation": {
        "onboard_passenger_fraction": 1.0,
        "embarkation_buffet_surge": true,
        "contact_rate_multiplier": 1.2,
        "notes": "Hyper-concentrated crowding during 3h embarkation window"
      }
    }
  }
}
```

### Per-Platform Dining Meal Weights

Added to each platform's spatial layout or agent behavior config.
Maps our 4 ship classes to the report's meal allocation data:

```json
{
  "dining_meal_weights": {
    "expedition": {
      "breakfast": {"buffet": 0.00, "mdr": 0.85, "specialty": 0.00, "crew_mess": 0.15},
      "lunch":     {"buffet": 0.00, "mdr": 0.70, "specialty": 0.00, "crew_mess": 0.30},
      "dinner":    {"buffet": 0.00, "mdr": 0.90, "specialty": 0.05, "crew_mess": 0.05}
    },
    "classic": {
      "breakfast": {"buffet": 0.75, "mdr": 0.20, "specialty": 0.05},
      "lunch":     {"buffet": 0.60, "mdr": 0.25, "specialty": 0.15},
      "dinner":    {"buffet": 0.20, "mdr": 0.60, "specialty": 0.20}
    },
    "spirit": {
      "breakfast": {"buffet": 0.80, "mdr": 0.18, "specialty": 0.02},
      "lunch":     {"buffet": 0.65, "mdr": 0.25, "specialty": 0.10},
      "dinner":    {"buffet": 0.25, "mdr": 0.65, "specialty": 0.10}
    },
    "mega": {
      "breakfast": {"buffet": 0.70, "mdr": 0.15, "specialty": 0.15},
      "lunch":     {"buffet": 0.50, "mdr": 0.20, "specialty": 0.30},
      "dinner":    {"buffet": 0.20, "mdr": 0.45, "specialty": 0.35}
    }
  }
}
```

Notes:
- Expedition has NO buffet service type — all "casual" meals are MDR 
  (crew-served table service). The 0.85/0.70 breakfast/lunch values
  route to MDR because the venue IS table service, not self-service.
- Classic maps to "Premium" in the report (1,500-3,000 pax).
- Spirit maps to "Contemporary" (2,000-4,000 pax).
- Mega maps to "Mega/Iconic" (4,000-7,000 pax).

## Engine Integration

### Epoch-Level State

The orchestrator reads the itinerary config and sets per-epoch state:

```python
class EpochState:
    day_type: str           # "sea_day", "port_day", "embarkation", "disembarkation"
    onboard_fraction: float # fraction of passengers currently onboard
    contact_multiplier: float
    dining_multiplier: dict[str, float]  # per-meal-type multipliers
```

### Agent Behavior Modification

During port day epochs within the disembark window:
1. A fraction of passenger agents are marked `ashore = True`
2. Ashore agents are excluded from zone mixing and contact calculations
3. Ashore agents cannot infect or be infected by onboard agents
4. Shore infection probability (stub, default 0.0) allows future 
   modeling of off-ship exposure

During reembark window:
1. Ashore agents return and resume normal behavior
2. Any shore-acquired infections become active

### Embarkation Surge

On embarkation day, during the embarkation window:
1. All passengers are assigned to dining zones simultaneously
2. Buffet/casual zones receive `buffet_surge_fraction` of traffic
3. Contact rate multiplier is elevated (1.2×)
4. This models the 3-hour crowding before staterooms open

### Dining Demand Modification

Port day lunch demand drops by 50-70%. The dining rotation probability
is scaled by the per-meal dining_demand_multiplier, reducing the number
of passengers who visit dining venues during port hours.

## Default Behavior (Stub)

When no `voyage` config is present, or when `itinerary` is empty:
- All epochs are treated as sea days
- `onboard_fraction = 1.0`
- `contact_multiplier = 1.0`  
- `dining_multiplier = 1.0` for all meals
- **No behavioral change from current model**

This ensures backward compatibility with all existing campaigns.

## Future Extensions

1. **Shore excursion mixing**: Model contact networks during organized 
   tours (bus, restaurant, attraction site). Requires off-ship zone model.
2. **Turnaround day**: Model crew-only period between voyages, including
   deep cleaning, re-provisioning, and crew infection carryover.
3. **Multi-voyage persistence**: Norovirus persistence across consecutive 
   voyages via environmental reservoir and asymptomatic crew shedding.
4. **Embarkation health screening**: Pre-boarding questionnaire and 
   temperature check with configurable sensitivity/specificity.
5. **Port-specific infection risk**: Different shore infection probabilities
   by destination (tropical vs. temperate, developing vs. developed).
