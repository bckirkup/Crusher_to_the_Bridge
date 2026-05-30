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
    "medical": [{"kind": "order_verification_test", "zone": "Galley"}],
    "population": [{"kind": "report_sick_call", "agent_id": 4}]
  }
}
```

Use top-level fields (`protocol_id`, `zone`, `agent_id`) — not nested `parameters` objects.

## Stackelberg order (Picard)

1. **Population** (pre-syndromic) → 2. Instruments / stoplights → 3. **Command** → 4. **Medical**

Utility bundles include `operational_impact_cumulative` when OIS is enabled.

Optimization and weight fitting are **out of repo**; only feature vectors are exported.

## Validation

```bash
python3 tools/sanity_checker.py --from-config
python3 -m pytest tests/test_stackelberg.py -v
```

Schema: `schemas/utility_observation_bundle.schema.json`

## Presidio CLI shortcuts

```bash
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1 \
  --export-utility-dir presidio/data/experiences/utility_bundles \
  --import-actions-dir presidio/data/experiences/imported_actions
```
