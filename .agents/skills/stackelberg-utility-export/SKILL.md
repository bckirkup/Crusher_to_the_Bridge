---
name: stackelberg-utility-export
description: Export Stackelberg utility observation bundles for external optimization and import action envelopes. Use with Presidio/Picard social configuration enabled.
---

# Stackelberg Utility Export

## Prerequisites

- Picard/Presidio branch with `social` config on run specs
- Python 3.11+, `PYTHONPATH=.` at repo root

## Enable utility export on a cruise

Add to Picard run spec JSON (`social` block):

```json
{
  "social": {
    "export_utility_dir": "presidio/data/experiences/utility_bundles",
    "cruise_id": "0",
    "agent_profile_bundle": "picard_framework/data/agent_profiles/default_ship_population.json",
    "class_interactions": "presidio/data/social/class_interactions_default.json",
    "information_diffusion": "presidio/data/social/information_diffusion_default.json",
    "global_health_timeline": "presidio/data/intelligence/global_health_timeline.json"
  }
}
```

Each epoch writes: `cruise_{id}_epoch_{NNNN}_utility.json`

## Import actions (external optimizer output)

Place files at:

`{import_dir}/cruise_{id}_epoch_{NNNN}_actions.json`

```json
{
  "epoch": 3,
  "actions": {
    "command": [{"kind": "authorize_sop_subset", "protocol_ids": ["SOP-001"]}],
    "medical": [{"kind": "set_surveillance_cadence", "pcr_cadence": 2}]
  }
}
```

## Stackelberg order

1. Command → 2. Medical → 3. Population (noop default)

Optimization and weight fitting are **out of repo**; only feature vectors are exported.

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_stackelberg.py -v
```

Schema: `schemas/utility_observation_bundle.schema.json`
