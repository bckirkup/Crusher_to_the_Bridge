# Model Changes Required for Multi-Pathogen Cross-Platform Calibration
## For: Crusher to the Bridge

### Context

The A2 sensitivity campaign (16,830 runs) shows that the density-dependent contact 
model (α=0.75) produces realistic norovirus outbreak sizes on spirit and mega platforms 
but requires different dose_adj for expedition (16.5) vs mega (13.0). The pathogen 
calibration table identifies three distinct transmission architectures needed across 
the 10 pathogens. This spec covers the model changes needed to enable calibration.

---

## 1. Agent Schedule Improvements

### Problem
Currently each agent has ONE fixed dining zone and ONE fixed free zone for the 
entire voyage. This means the same 67 passengers eat at the Windjammer buffet 
every meal, every day. Real passengers rotate: buffet for breakfast, main dining 
for dinner, specialty restaurant one night.

On larger ships this matters more because there are more dining/free venues to 
rotate through. The fixed assignment artificially reduces mixing on large ships 
(always the same group in each zone), which may explain why mega needs lower 
dose_adj to achieve the same AR.

### Fix: Probabilistic zone selection

Replace fixed zone assignment with a per-epoch stochastic draw from available zones 
of the correct type, weighted by zone capacity and agent preferences.

In `engines/infection_dynamics_bridge.py`, modify `get_location_for_hour`:

```python
def get_location_for_hour(self, hour, randomness=0.0):
    activity = self.schedule[adjusted_hour]
    if activity == "Sleep":
        return self.home_zone       # always same cabin
    if activity.startswith("Meal"):
        return self._draw_dining_zone(hour)    # NEW: stochastic
    if activity == "Free":
        return self._draw_free_zone(hour)      # NEW: stochastic
    if activity == "Work":
        return self.work_zone       # crew stay at assigned station
    return self.home_zone

def _draw_dining_zone(self, hour):
    """Stochastic dining venue selection.

    Passengers have a 'home' dining venue (assigned seating for dinner)
    but rotate through available venues with probability p_rotate.
    Breakfast/lunch are more likely at buffet; dinner at MDR or specialty.
    """
    meal_type = self._meal_type_for_hour(hour)  # breakfast/lunch/dinner

    if self.rng.random() < self.dining_rotation_prob:
        # Choose from available dining zones weighted by capacity
        # Breakfast/lunch: bias toward buffet
        # Dinner: bias toward MDR and specialty
        weights = self._dining_weights(meal_type)
        return self.rng.choice(self.available_dining_zones, p=weights)
    return self.dining_zone  # default assigned venue
```

### Config

```yaml
agent_behavior:
  dining_rotation_probability: 0.3    # 30% chance of visiting a non-default venue
  dining_meal_weights:
    breakfast:
      buffet: 0.6
      mdr: 0.3
      specialty: 0.1
    lunch:
      buffet: 0.5
      mdr: 0.3
      specialty: 0.2
    dinner:
      buffet: 0.2
      mdr: 0.5
      specialty: 0.3
  free_zone_rotation_probability: 0.5   # higher rotation for free activities
```

### Impact
- More cross-group mixing on larger ships (more venues to rotate through)
- Should increase effective contacts on mega relative to expedition
- May reduce or eliminate the dose_adj platform difference

---

## 2. Pathogen-Specific Transmission Route Weights

### Problem
Currently all pathogens use the same transmission pathway weightings.
The calibration table shows different pathogens need different route dominance:
- Norovirus: fomite + close contact + vomit aerosol + food
- SARS-CoV-2: aerosol/respiratory + close contact
- C. difficile: environmental spore reservoir
- Legionella: plumbing/environmental source
- Campylobacter/Vibrio: food/water source

### Fix: Per-pathogen route weights in pathogen profiles

Add to each pathogen profile in `data/pathogens/`:

```json
{
  "pathogen_id": "norwalk_gi",
  "transmission_route_weights": {
    "direct_contact": 0.35,
    "droplet": 0.10,
    "hvac_airborne": 0.05,
    "fomite": 0.30,
    "food_contamination": 0.20,
    "environmental_source": 0.00
  },
  ...
}
```

For SARS-CoV-2:
```json
{
  "pathogen_id": "sars_cov2_resp",
  "transmission_route_weights": {
    "direct_contact": 0.25,
    "droplet": 0.30,
    "hvac_airborne": 0.30,
    "fomite": 0.10,
    "food_contamination": 0.00,
    "environmental_source": 0.05
  }
}
```

For Legionella:
```json
{
  "pathogen_id": "legionella_pneumophila",
  "transmission_route_weights": {
    "direct_contact": 0.00,
    "droplet": 0.00,
    "hvac_airborne": 0.00,
    "fomite": 0.00,
    "food_contamination": 0.00,
    "environmental_source": 1.00
  }
}
```

### Implementation

In `engines/transmission_core.py`, after computing each pathway dose, 
multiply by the pathogen-specific weight:

```python
def _execute_pathogen_pathways(self, ...):
    weights = profile.get("transmission_route_weights", DEFAULT_WEIGHTS)

    self._pathway_direct_contact(...) 
    # multiply agent_doses by weights["direct_contact"]

    self._pathway_droplet(...)
    # multiply by weights["droplet"]

    # etc.
```

The weights are normalized to sum to 1.0 and multiply the dose from each 
pathway. This does NOT change the total dose magnitude (controlled by 
dose_adjustment) — it changes the RELATIVE contribution of each route.

---

## 3. Environmental Source Model for Legionella and C. difficile

### Problem
Legionella and C. difficile transmit through environmental contamination,
not person-to-person contact. The current model has no mechanism for a 
zone to become contaminated from a non-human source (plumbing biofilm,
spore reservoir) and expose occupants.

### Fix: Zone contamination source

Add a `zone_contamination_sources` mechanism:

```json
{
  "pathogen_id": "legionella_pneumophila",
  "environmental_source": {
    "source_zones": ["Spa", "Pool_Deck", "Cabin_Corridor_*"],
    "source_type": "plumbing_aerosol",
    "base_emission_rate": 0.001,
    "exposure_activity": "shower_spa_use",
    "exposure_probability_per_epoch": 0.1
  }
}
```

For C. difficile:
```json
{
  "pathogen_id": "clostridioides_difficile",
  "environmental_source": {
    "source_zones": ["Medical_Center", "Cabin_Corridor_*"],
    "source_type": "spore_reservoir",
    "base_emission_rate": 0.0001,
    "amplification_by_antibiotic_use": 5.0,
    "spore_decay_rate_per_epoch": 0.001
  }
}
```

### Implementation

New pathway in `transmission_core.py`:

```python
def _pathway_environmental_source(self, epoch, zone_occupants, agent_doses, ...):
    """Dose from environmental contamination (not from infected agents)."""
    env_cfg = profile.get("environmental_source")
    if not env_cfg:
        return

    for zone_name, occupants in zone_occupants.items():
        if not self._zone_matches(zone_name, env_cfg["source_zones"]):
            continue

        # Zone contamination level (may accumulate over time)
        contamination = self.env_contamination.get(zone_name, 0.0)

        for agent in occupants:
            if self.rng.random() < env_cfg["exposure_probability_per_epoch"]:
                dose = contamination * env_cfg["base_emission_rate"]
                agent_doses[agent.agent_id] += dose
```

---

## 4. Food Contamination Pathway Enhancement

### Problem
The food_contamination pathway exists but isn't well-differentiated by 
dining zone type. A buffet with shared serving utensils should produce 
more food-borne transmission than a plated dinner with individual portions.

### Fix: Zone-type-specific food contamination

Add to dining zone definitions:
```json
{
  "id": "Windjammer",
  "type": "Dining",
  "dining_service_type": "buffet",
  "food_contamination_multiplier": 3.0
}
```

vs:
```json
{
  "id": "MainDining_L",
  "type": "Dining", 
  "dining_service_type": "table_service",
  "food_contamination_multiplier": 1.0
}
```

vs:
```json
{
  "id": "SpecRest_A",
  "type": "Dining",
  "dining_service_type": "specialty",
  "food_contamination_multiplier": 0.5
}
```

The multiplier scales the food_contamination pathway dose for that zone.
Buffets have higher risk due to shared serving utensils, open food exposure,
and self-service queuing.

---

## 5. Pathogen-Specific Dose Adjustment

### Problem
Currently dose_adjustment is a single global parameter. Different pathogens 
need different values (norovirus ~15, SARS-CoV-2 ~3-5). This is already 
partially supported via pathogen_overrides but needs to be the default 
architecture.

### Fix: Move dose_adjustment into pathogen profiles

Already partially implemented. Ensure each pathogen profile has:
```json
{
  "pathogen_id": "norwalk_gi",
  "dose_adjustment": 15.0,
  "dose_response_model": "beta_poisson",
  "dose_response_params": {
    "alpha": 0.111,
    "beta": 32.81
  }
}
```

Campaign sweeps override this via `pathogen_overrides.norwalk_gi.dose_adjustment`.

---

## 6. FUT2 Non-Susceptibility as Pathogen-Specific Trait

### Problem
Currently `immune_fraction` is used as a proxy for FUT2 non-secretor status,
but it applies to all pathogens equally. FUT2 only affects norovirus (and 
only certain genotypes). Other pathogens have their own susceptibility 
heterogeneity (e.g., HLA for measles, prior infection for influenza).

### Fix: Per-pathogen susceptibility fraction

Add to pathogen profiles:
```json
{
  "pathogen_id": "norwalk_gi",
  "innate_nonsusceptible_fraction": 0.20,
  "nonsusceptible_mechanism": "FUT2_nonsecretor"
}
```

```json
{
  "pathogen_id": "sars_cov2_resp",
  "innate_nonsusceptible_fraction": 0.0,
  "nonsusceptible_mechanism": "none"
}
```

At agent initialization, assign per-pathogen susceptibility:
```python
for pathogen_id, profile in pathogen_profiles.items():
    nonsus_frac = profile.get("innate_nonsusceptible_fraction", 0.0)
    if rng.random() < nonsus_frac:
        agent.set_susceptibility(pathogen_id, 0.0)  # immune
```

This replaces the blunt `immune_fraction` config override with 
pathogen-specific biology.

---

## Priority Order

1. **Route weights** (change #2) — minimal code, biggest impact on multi-pathogen calibration
2. **Per-pathogen dose_adjustment** (change #5) — already partially done, formalize
3. **Per-pathogen non-susceptibility** (change #6) — separates FUT2 from generic immunity
4. **Dining rotation** (change #1) — may resolve the platform calibration gap
5. **Food contamination enhancement** (change #4) — important for norovirus specifically
6. **Environmental source** (change #3) — needed for Legionella and C. diff but architecturally larger

Changes 1-3 should be sufficient for Tier 1+2 pathogen calibration.
Changes 4-6 are needed for the full 10-pathogen panel.
