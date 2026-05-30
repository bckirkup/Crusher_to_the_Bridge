---
name: presidio-fleet-run
description: Run Presidio fleet meta-simulations across multiple Picard cruises with experience storage. Use after modifying presidio/, presidio_runner.py, or fleet config under presidio/data/.
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
| `presidio/data/experiences/` | Experience store + per-cruise outputs |

## Quick commands

```bash
python3 tools/sanity_checker.py --from-config

# Default fleet (2 cruises × 24 epochs — slow)
python3 presidio_runner.py

# Smoke test fleet (1 cruise × 2 epochs)
python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1
```

## Outputs

- `presidio/data/experiences/fleet_experience.json` — rolling policy statistics
- `presidio/data/experiences/runs/cruise_NNN/` — per-cruise telemetry (when using default fleet)

## Validation

```bash
python3 -m pytest tests/test_presidio_runner.py -v
```
