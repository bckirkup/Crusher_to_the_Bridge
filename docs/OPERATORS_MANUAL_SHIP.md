# Crusher-to-the-Bridge — Ship Operator's Manual (Picard)

**Scope:** Single-ship biodefense simulation, diagnostics, protocols, and telemetry.  
**Fleet / Stackelberg:** see [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md).  
**Docs index:** [README.md](README.md).

---

## Quick Start

```bash
pip install -r requirements.txt
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py              # 24 epochs (config.yaml default)
python3 orchestrator.py --epochs 250
```

The legacy `orchestrator.py` CLI runs its own epoch loop (see `orchestrator_epoch.py`).
For the equivalent **Picard_Framework** programmatic API, use `ShipSimulation` below.

## Picard configuration layers

| Layer | Location | Purpose |
|-------|----------|---------|
| **Catalog library** | `data/platforms/`, `data/pathogens/`, `data/config/` | Shared ship definitions |
| **Run spec** | `picard_framework/runs/*.json` or `PicardRunSpec.from_legacy_yaml()` | Immutable cruise snapshot |
| **World state** | In-memory `SimulationState` + engines | Mutable per-epoch state |

## Picard run spec example

```json
{
  "catalog": {
    "platform_id": "destroyer_baseline",
    "pathogen_bundle_id": "active_profiles"
  },
  "run": { "random_seed": 42, "num_epochs": 24 },
  "legacy_yaml": "crusher_labs/config.yaml",
  "social": {
    "agent_profile_bundle": "picard_framework/data/agent_profiles/default_ship_population.json",
    "class_interactions": "presidio/data/social/class_interactions_default.json",
    "information_diffusion": "presidio/data/social/information_diffusion_default.json",
    "global_health_timeline": "presidio/data/intelligence/global_health_timeline.json"
  }
}
```

The optional `social` block enables Stackelberg hooks (lived experience, diffusion, utility export). See `picard_framework/runs/destroyer_baseline_default.json`.

Validate: `schemas/picard_run_spec.schema.json`

## Programmatic API

```python
from picard_framework import PicardRunSpec, ShipSimulation

spec = PicardRunSpec.from_legacy_yaml("/path/to/repo")
sim = ShipSimulation(spec, display=False)
sim.run()
sim.finalize(display=False)
```

Smoke run spec (2 epochs): `picard_framework/runs/smoke_2epoch.json`

Diagnostic cascade smoke (6 epochs, cascade enabled):

| Spec | Cascade config |
|------|----------------|
| `picard_framework/runs/smoke_cascade_6epoch.json` | `data/config/diagnostic_cascade.json` |
| `picard_framework/runs/smoke_cascade_multiplex_6epoch.json` | `data/config/diagnostic_cascade_multiplex.json` |

```bash
python3 -m pytest tests/test_smoke_diagnostic_cascade.py -v
```

Run specs use `config_overrides.diagnostic_cascade.enabled: true` so the default
`crusher_labs/config.yaml` can keep cascade disabled for golden regression.

Design references: `docs/SHEDDING_AND_CABINMATES.md` (host shedding variance +
cabin-mate pairing), `docs/PLATFORM_CABIN_REVISION.md` (mega-cruise spatial model),
`docs/density_contact_spec.md` (contact modes), `docs/multi_pathogen_model_changes_spec.md`
(route weights, dining rotation, zone food multipliers, scoped environmental load).

## Transmission and agent behavior

Key knobs in `crusher_labs/config.yaml` (overridable via Picard `config_overrides`):

| Knob | Default | Notes |
|------|---------|-------|
| `transmission.contact_mode` | `density_dependent` | Also `legacy` or opt-in `heterogeneous_zone_dose` |
| `agent_behavior.dining_rotation_probability` | `0.0` | Keep 0 for golden stability; raise in campaigns for venue mixing |
| `agent_behavior.free_zone_rotation_probability` | `0.0` | Same pattern for Free zones; the underlying draw is capacity-weighted over passenger-accessible venues |
| `voyage.effects_enabled` | `false` | Flag-gated port/embarkation effects; see [ship_operations_spec.md](ship_operations_spec.md) |

Pathogen profiles (`data/pathogens/`): `dose_adjustment` (log10 shedding offset),
`transmission_route_weights`, `innate_nonsusceptible_fraction`, and optional
`environmental_contamination.source_zones`. Dining zones may set
`dining_service_type` and `food_contamination_multiplier` in `spatial_layout.json`.

### Voyage itinerary (ship operations)

Cruise platforms ship `data/platforms/<id>/voyage_config.json` with
`voyage.effects_enabled: false` (identity sea-day), class-specific
`dining_meal_weights`, and stock-equivalent `medical_response` knobs
(see [`medical_response_spec.md`](medical_response_spec.md)). Enable effects only via Picard
`config_overrides.voyage` when intentionally testing port/embarkation density
changes. **Shore infection is not implemented** — `shore_infection_probability`
is config-only and never introduces pathogens. Enabling effects changes
onboard mixing (ashore exclusion, contact/dining multipliers, embarkation
surge) but does not model off-ship exposure.

## Outputs

| File | Description |
|------|-------------|
| `telemetry_buffer/simulation_history.json` | Per-epoch full state |
| `telemetry_buffer/artificial_lab_notebook.json` | Instrument records |
| `telemetry_buffer/ground_truth.json` | Per-epoch broker (Crusher Labs seam) |

Optional telemetry when `social.telemetry.decision_detail: true`:

- `simulation_history[].information_state` — belief diffusion summary
- `simulation_history[].decisions` — role actions per epoch
- `simulation_history[].wearable_agent_snapshot` — per-agent multi-device wearable slice (devices, visibility, confounders, detection profiles, `infection_score`, `matched_confounders`)
- `simulation_history[].voyage_epoch` — day_type, onboard_fraction, contact/dining multipliers, `effects_active` (always present when voyage config is loaded)

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_picard_framework.py tests/test_golden_orchestrator.py \
  tests/test_density_contact.py tests/test_multi_pathogen_model_phase_a.py \
  tests/test_multi_pathogen_model_phase_b.py -v
```

Skill: `.agents/skills/picard-ship-simulation/SKILL.md`

## Further reading

Full config.yaml, SOP, instrument, and GIS reference: [OPERATORS_MANUAL.md](OPERATORS_MANUAL.md). Fleet and external optimization: [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md).

Mega-cruise factorial campaign (~17,780 Picard runs):
[`picard_framework/runs/mega_cruise_campaign/README.md`](../picard_framework/runs/mega_cruise_campaign/README.md)
(`run_campaign.bat` / `run_campaign.sh` from the repo root).
