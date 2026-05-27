---
name: adding-new-pathogen
description: Add a new pathogen profile to Crusher-to-the-Bridge. Covers creating the profile entry, dose-response parameters, shedding curves, and validation. Use when extending the multi-pathogen simulation.
---

# Adding a New Pathogen

## Prerequisites

- Python 3.11+ with pydantic, numpy, and pyyaml installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)

## Devin Secrets Needed

None.

## Steps

### 1. Understand the pathogen profile structure

Profiles live in `data/pathogens/active_profiles.json`. Each pathogen entry requires:

```json
{
  "pathogen_id": "unique_snake_case_id",
  "name": "Human-readable name",
  "category": "enteric_viral",
  "transmission_routes": ["direct_contact", "fomite", "food"],
  "shedding_curve_log10": [2.0, 3.5, 4.0],
  "asymptomatic_shedding_log10": [1.0, 2.0, 2.5],
  "dose_response": {
    "model": "beta_poisson",
    "alpha": 0.04,
    "beta": 0.055
  },
  "illness_probability": {"eta": 0.6, "gamma": 0.4},
  "recovery_day": 5,
  "surface_deposition_fraction": 0.3,
  "base_susceptibility": 1.0,
  "introduction_epoch": 0,
  "initial_infected": 1,
  "microflora_disruption": {
    "causes_disruption": false,
    "disruption_type": "",
    "disruption_magnitude": 0.0,
    "affected_kingdoms": []
  }
}
```

Optional blocks for extended transmission pathways (PR #43):

```json
"food_contamination": {
  "enabled": true,
  "food_zones": ["Galley", "Mess_Hall"]
},
"environmental_contamination": {
  "enabled": true,
  "baseline_environmental_load": 0.01,
  "growth_rate_per_epoch": 0.05
}
```

### 2. Add the pathogen entry

Edit `data/pathogens/active_profiles.json` and add a new object to the `pathogens` array.

**Law 2 constraint:** The `pathogen_id` must be unique and not hardcoded anywhere in the Python source. The orchestrator iterates over all pathogens dynamically.

**Law 3 constraints:**
- `dose_response.alpha` and `dose_response.beta` must be > 0 (for `beta_poisson` model)
- For `exponential` model, `dose_response.k` must be > 0
- `shedding_curve_log10` must be non-empty
- `surface_deposition_fraction` must be in [0.0, 1.0]
- `base_susceptibility` must be >= 0
- `illness_probability.eta` and `gamma` must be in [0.0, 1.0]

### 3. Choose the dose-response model

| Model | Parameters | Formula |
|-------|-----------|---------|
| `beta_poisson` | `alpha`, `beta` | P = 1 - (1 + dose/beta)^(-alpha) |
| `exponential` | `k` | P = 1 - exp(-k * dose) |

Reference: `engines/infection_dynamics_bridge.py::infection_probability()`

### 4. Define transmission routes

Valid routes (used by `engines/transmission_core.py`):
- `direct_contact` — zone colocation
- `droplet` — short-range aerosolization
- `hvac_airborne` — long-range HVAC transport
- `fomite` — surface deposition and pickup
- `water_aerosol`, `food`, `water`, `bodily_fluids` — route-specific pathways

Pathways 5–6 are enabled per-profile via `food_contamination` and `environmental_contamination` blocks, not via `transmission_routes` alone.

### 5. Validate the new profile

```bash
python tools/sanity_checker.py --from-config
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json
python -m pytest tests/test_data_contracts.py::TestPathogenProfiles -v --tb=short
python -m pytest tests/test_transmission_pathways.py -v --tb=short
```

### 6. Run the orchestrator smoke test
```bash
python orchestrator.py --epochs 10
```
The orchestrator picks up the new pathogen automatically and simulates multi-pathogen dynamics.

## Reference Profiles

| Pathogen ID | Model | Notes |
|-------------|-------|-------|
| `norwalk_gi` | beta_poisson | GI Norovirus; food contamination enabled |
| `sars_cov2_resp` | beta_poisson | Respiratory SARS-CoV-2; HVAC airborne route |

For the extended 10-pathogen set, see `data/pathogens/edison_10pathogen_profiles.json`.

## Common Mistakes

- Empty `shedding_curve_log10` — fails data contract tests
- Setting `alpha` or `beta` to 0 — sanity checker reports ERROR
- Adding hardcoded `if pathogen_id == "my_new_pathogen"` logic — violates Law 2
- Duplicate `pathogen_id` — fails uniqueness validation
- Using `airborne` instead of `hvac_airborne` in `transmission_routes` — invalid route name
