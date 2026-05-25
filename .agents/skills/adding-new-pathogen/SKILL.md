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
  "pathogens": [
    {
      "pathogen_id": "unique_snake_case_id",
      "name": "Human-readable name",
      "transmission_routes": ["direct_contact", "droplet", "airborne", "fomite"],
      "dose_response": {
        "model": "beta_poisson",
        "alpha": 0.04,
        "beta": 0.055
      },
      "shedding_curve": [
        {"epoch_offset": 0, "rate": 10.0},
        {"epoch_offset": 1, "rate": 50.0},
        {"epoch_offset": 2, "rate": 80.0},
        {"epoch_offset": 3, "rate": 40.0},
        {"epoch_offset": 4, "rate": 10.0}
      ],
      "incubation_epochs": 2,
      "recovery_epochs": 8,
      "base_susceptibility": 1.0,
      "microflora_disruption": true
    }
  ]
}
```

### 2. Add the pathogen entry

Edit `data/pathogens/active_profiles.json` and add a new object to the `pathogens` array.

**Law 2 constraint:** The `pathogen_id` must be unique and not hardcoded anywhere in the Python source. The orchestrator iterates over all pathogens dynamically.

**Law 3 constraints:**
- `dose_response.alpha` and `dose_response.beta` must be > 0 (for `beta_poisson` model)
- For `exponential` model, `dose_response.k` must be > 0
- `shedding_curve` must be non-empty
- `base_susceptibility` must be >= 0
- All shedding `rate` values should be >= 0

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
- `airborne` — long-range HVAC transport
- `fomite` — surface deposition and pickup

### 5. Validate the new profile

```bash
# Sanity checker validates dose-response bounds and shedding curves
python tools/sanity_checker.py

# JSON schema validation
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json

# Data contract tests
python -m pytest tests/test_data_contracts.py::TestPathogenProfiles -v --tb=short
```

### 6. Run the orchestrator smoke test
```bash
python orchestrator.py --epochs 10
```
The orchestrator should pick up the new pathogen automatically and simulate multi-pathogen dynamics.

## Reference Profiles

| Pathogen ID | Model | Notes |
|-------------|-------|-------|
| `norwalk_gi` | beta_poisson | GI-tract Norovirus; high fomite route |
| `sars_cov2_resp` | beta_poisson | Respiratory SARS-CoV-2; high airborne route |

For the extended 10-pathogen set, see `data/pathogens/edison_10pathogen_profiles.json`.

## Common Mistakes

- Forgetting `shedding_curve` — test will fail on empty check
- Setting `alpha` or `beta` to 0 — sanity checker will report ERROR
- Adding hardcoded `if pathogen_id == "my_new_pathogen"` logic — violates Law 2
- Duplicate `pathogen_id` — fails uniqueness validation
