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
  "dose_adjustment": 4.0,
  "dose_response": {
    "model": "beta_poisson",
    "alpha": 0.04,
    "beta": 0.055
  },
  "surface_decay_per_day": 0.25,
  "airborne_half_life_hours": 1.1,
  "food_contamination": {
    "enabled": true,
    "growth_rate_per_day": 0.0,
    "decay_rate_per_day": 0.1
  },
  "illness_probability": {"eta": 0.6, "gamma": 0.4},
  "recovery_day": 5,
  "surface_deposition_fraction": 0.3,
  "base_susceptibility": 1.0,
  "introduction_epoch": 0,
  "initial_infected": 1,
  "initial_time_infected": 0,
  "shedding_variance_log10": 0.0,
  "transmission_route_weights": {
    "direct_contact": 0.4,
    "droplet": 0.1,
    "hvac_airborne": 0.0,
    "fomite": 0.3,
    "food_contamination": 0.2,
    "environmental_source": 0.0
  },
  "innate_nonsusceptible_fraction": 0.0,
  "nonsusceptible_mechanism": "none",
  "microflora_disruption": {
    "causes_disruption": false,
    "disruption_type": "",
    "disruption_magnitude": 0.0,
    "affected_kingdoms": []
  }
}
```

**`dose_adjustment`** is a **log10 shedding offset**
(`shedding = 10^(curve[dpi] − dose_adjustment) * shedding_multiplier`),
not a dose-response α/β scaler. Campaigns calibrate infectivity via
`pathogen_overrides.<id>.dose_adjustment`.

**`transmission_route_weights`** (optional; default all 1.0) scale each
pathway's dose contribution. Prefer weights that sum to ≈1.0.

**`innate_nonsusceptible_fraction`** draws per-agent zero susceptibility for
this pathogen only (e.g. FUT2 for norovirus). Orthogonal to
`ship_graph.immune_fraction`.

Optional blocks for extended transmission pathways (PR #43):

```json
"food_contamination": {
  "enabled": true,
  "food_zones": ["Galley", "Mess_Hall"],
  "growth_rate_per_day": 0.0,
  "decay_rate_per_day": 0.1
},
"environmental_contamination": {
  "enabled": true,
  "baseline_environmental_load": 0.01,
  "colonization_rate_per_day": 0.05,
  "source_zones": ["Spa", "Pool_*"]
}
```

For norovirus, `growth_rate_per_day` is `0.0`: viruses cannot replicate in
food. The worked kinetics above use the literature-anchored surface loss and
airborne half-life values for the shipped norovirus profile.

**`source_zones`** (optional): when present, environmental load is updated
only in matching zones (exact id or `*` prefix/suffix glob). Absent → legacy
ship-wide environmental pool. See `docs/multi_pathogen_model_changes_spec.md`.

### 2. Add the pathogen entry

Edit `data/pathogens/active_profiles.json` and add a new object to the `pathogens` array.

**Law 2 constraint:** The `pathogen_id` must be unique and not hardcoded anywhere in the Python source. The orchestrator iterates over all pathogens dynamically.

**Law 3 constraints:**
- `dose_response.alpha` and `dose_response.beta` must be > 0 (for `beta_poisson` model)
- For `exponential` model, `dose_response.k` must be > 0
- `shedding_curve_log10` must be non-empty
- `shedding_variance_log10` (optional, default 0.0) — σ of log-normal host shedding multiplier; 0.0 = no variance
- `surface_deposition_fraction` must be in [0.0, 1.0]
- `base_susceptibility` must be >= 0
- `illness_probability.eta` and `gamma` must be in [0.0, 1.0]

### 3. Choose the dose-response model

| Model | Parameters | Formula |
|-------|-----------|---------|
| `beta_poisson` | `alpha`, `beta` | P = 1 - (1 + dose/beta)^(-alpha) |
| `exponential` | `k` | P = 1 - exp(-k * dose) |

Reference: `engines/infection_dynamics_bridge.py::infection_probability()`

### 3b. Host shedding variance (optional)

Per-agent shedding multipliers are drawn at infection time from a log-normal:

```
multiplier = 10^(normal(0, shedding_variance_log10))
```

Set `shedding_variance_log10` on the profile (literature values in
`edison_10pathogen_profiles.json`). Default `0.0` yields multiplier = 1.0.
See `docs/SHEDDING_AND_CABINMATES.md`.

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
python -m pytest tests/test_shedding_variance_cabin_mates.py -v --tb=short
python -m pytest tests/test_transmission_pathways.py -v --tb=short
python -m pytest tests/test_multi_pathogen_model_phase_a.py \
  tests/test_multi_pathogen_model_phase_b.py -v --tb=short
```

### 6. Run the orchestrator smoke test
```bash
python orchestrator.py --epochs 10
```
The orchestrator picks up the new pathogen automatically and simulates multi-pathogen dynamics.

## Reference Profiles

| Pathogen ID | Model | Notes |
|-------------|-------|-------|
| `norwalk_gi` | beta_poisson | GI Norovirus; `shedding_variance_log10`: 1.5; food contamination enabled |
| `sars_cov2_resp` | beta_poisson | Respiratory SARS-CoV-2; `shedding_variance_log10`: 1.2; HVAC airborne route |

For the extended 10-pathogen set, see `data/pathogens/edison_10pathogen_profiles.json`.
For fiction-adapted Enterprise scenarios, see `enterprise_tos_profiles.json` and `enterprise_tng_profiles.json` with templates under `data/templates/`.

## Common Mistakes

- Empty `shedding_curve_log10` — fails data contract tests
- Setting `alpha` or `beta` to 0 — sanity checker reports ERROR
- Adding hardcoded `if pathogen_id == "my_new_pathogen"` logic — violates Law 2
- Duplicate `pathogen_id` — fails uniqueness validation
- Using `airborne` instead of `hvac_airborne` in `transmission_routes` — invalid route name
