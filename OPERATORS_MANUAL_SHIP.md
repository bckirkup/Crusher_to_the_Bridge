# Crusher-to-the-Bridge — Ship Operator's Manual (Picard)

**Scope:** Single-ship biodefense simulation, diagnostics, protocols, and telemetry.  
**Fleet / game-theory operations:** see [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md).

---

## Quick Start

```bash
pip install -r requirements.txt
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py              # 24 epochs (config.yaml default)
python3 orchestrator.py --epochs 250
```

The legacy `orchestrator.py` CLI delegates to **Picard_Framework** `ShipSimulation`.

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
  "legacy_yaml": "crusher_labs/config.yaml"
}
```

Validate: `schemas/picard_run_spec.schema.json`

## Programmatic API

```python
from picard_framework import PicardRunSpec, ShipSimulation

spec = PicardRunSpec.from_legacy_yaml("/path/to/repo")
sim = ShipSimulation(spec, display=False)
sim.run()
sim.finalize(display=False)
```

## Outputs

| File | Description |
|------|-------------|
| `telemetry_buffer/simulation_history.json` | Per-epoch full state |
| `telemetry_buffer/artificial_lab_notebook.json` | Instrument records |
| `telemetry_buffer/ground_truth.json` | Per-epoch broker (Crusher Labs seam) |

## Further reading

The complete ship configuration reference (config.yaml, SOPs, instruments, GIS bridge, sanity checker, lab notebook fidelity) remains in the main manual sections. For the full table of contents and historical sections 1–11, open [OPERATORS_MANUAL.md](OPERATORS_MANUAL.md) — ship-specific content is authoritative here for Picard entry points and run specs.
