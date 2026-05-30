---
name: presidio-fleet-run
description: Run Presidio fleet meta-simulations across multiple Picard cruises with experience storage and optional Stackelberg utility export/import. Use after modifying presidio/, presidio_runner.py, or fleet config under presidio/data/.
---

# Presidio Fleet Run

## Prerequisites

- Python 3.11+, repo root on `PYTHONPATH`
- Valid Picard run spec referenced by fleet config

## Configuration directories

| Directory | Contents |
|-----------|----------|
| `presidio/data/catalog/` | Fleet library index (`libraries.json`) |
| `presidio/data/config/` | Fleet run specs (`default_fleet.json`, `smoke_fleet.json`) |
| `presidio/data/economics/` | Fleet reward/penalty weights |
| `presidio/data/social/` | Information diffusion, class interactions |
| `presidio/data/intelligence/` | Global health timeline |
| `presidio/data/experiences/` | Experience store + per-cruise outputs |

## Quick commands

```bash
python3 tools/sanity_checker.py --from-config

# Smoke test fleet (1 cruise × 2 epochs)
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1

# Default fleet (multiple cruises — slower)
python3 presidio_runner.py

# External optimizer I/O
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1 \
  --export-utility-dir presidio/data/experiences/utility_bundles \
  --import-actions-dir presidio/data/experiences/imported_actions
```

## Outputs

- `presidio/data/experiences/fleet_experience.json` — rolling policy statistics (default path)
- `presidio/data/experiences/runs/cruise_NNN/` — per-cruise telemetry when configured

## Validation

```bash
python3 -m pytest tests/test_presidio_runner.py tests/test_stackelberg.py -v
```

Related: `.agents/skills/stackelberg-utility-export/SKILL.md`
