---
name: configuring-stackelberg-social
description: Configure Stackelberg social layer (diffusion, class interactions, agent profiles, global health) on Picard/Presidio runs. Use when editing presidio/data/social/, agent profiles, or Picard run spec social blocks.
---

# Configuring Stackelberg Social Layer

## Prerequisites

- Python 3.11+, repo root on `PYTHONPATH`
- Platform spatial layout validated (zone IDs for class interaction pairs)

## Picard run spec `social` block

Reference in `picard_framework/runs/destroyer_baseline_default.json`:

```json
{
  "social": {
    "agent_profile_bundle": "picard_framework/data/agent_profiles/default_ship_population.json",
    "class_interactions": "presidio/data/social/class_interactions_default.json",
    "information_diffusion": "presidio/data/social/information_diffusion_default.json",
    "global_health_timeline": "presidio/data/intelligence/global_health_timeline.json",
    "agent_granularity": "per_agent",
    "telemetry": { "decision_detail": false },
    "export_utility_dir": null,
    "import_actions_dir": null
  }
}
```

## Parameter bounds (Law 3)

`information_diffusion_default.json`:

- `alpha`, `homophily_strength`, `message_decay` ∈ [0, 1]

`class_interactions_default.json`:

- Each `pairs[].weight` ≥ 0
- Each `context_zones[]` entry must exist in the platform `spatial_layout.json`

## Fleet override

`presidio/data/config/default_fleet.json` may set fleet-level `social` merged into each cruise in `presidio_runner.py`.

## Validation

```bash
python3 tools/sanity_checker.py --from-config
pip install check-jsonschema
check-jsonschema --schemafile schemas/information_diffusion.schema.json \
  presidio/data/social/information_diffusion_default.json
check-jsonschema --schemafile schemas/class_interactions.schema.json \
  presidio/data/social/class_interactions_default.json
python3 -m pytest tests/test_stackelberg.py -v
```

Related: `.agents/skills/stackelberg-utility-export/SKILL.md`
