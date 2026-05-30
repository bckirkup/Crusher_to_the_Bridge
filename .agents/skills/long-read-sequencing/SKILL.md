---
name: long-read-sequencing
description: Configure and test Oxford Nanopore long-read verification, instrument turnaround (TAT), and escalation from routine modalities. Use when editing long_read_sequencing config, long_read_sequencing_params.json, instrument_turnaround.json, or crusher_labs/modalities/long_read_sequencing.py.
---

# Long-Read Sequencing & Instrument TAT

## Prerequisites

- Python 3.11+ with `requirements.txt` installed
- Working directory: repo root

## Config files

| File | Role |
|------|------|
| `crusher_labs/config.yaml` | `long_read_sequencing.enabled`, `params_path`, `default_profile`, escalation triggers |
| `data/config/long_read_sequencing_params.json` | Flongle/MinION profiles, detection limits, error injection, turnaround |
| `data/config/instrument_turnaround.json` | Per-instrument delay epochs (WW +1, microbio +3, long-read uses profile) |
| `data/config/long_read_sequencing_notes.md` | Assay assumptions and references |

## Enable long-read verification

```yaml
long_read_sequencing:
  enabled: true
  params_path: "data/config/long_read_sequencing_params.json"
  default_profile: "flongle_rapid"   # or minion_standard
  specimen_sources:
    - wastewater_metagenomics
    - clinical_specimen
    - clinical_culture
    - surveillance_swab
  escalation_triggers:
    mixed_infection_suspected: true
    unexpected_pathogen: true
    discordant_modalities: true
```

`init_observation_engine()` wires `ObservationEngine.long_read` and loads TAT from the Nanopore profile when `long_read_verification.use_profile` is true.

## Turnaround (TAT) behavior

1. Instruments sample ground truth each epoch (raw).
2. `InstrumentTurnaroundQueue` submits results with configured delay.
3. **Delivered** results only feed stoplights, `observation_engine` telemetry, Medical Officer views, and long-read escalation.

Pending assays appear with `status: "pending"`, `ordered_epoch`, and `available_epoch`.

## Quick tests

```bash
python3 -m pytest tests/test_long_read_sequencing.py tests/test_instrument_turnaround.py -v --tb=short
```

```bash
python3 tools/sanity_checker.py --from-config
```

## Smoke with long-read enabled

```bash
PYTHONPATH=. python3 -c "
import copy
from crusher_labs import load_config
from orchestrator_init import init_observation_engine
cfg = copy.deepcopy(load_config())
cfg['long_read_sequencing']['enabled'] = True
obs = init_observation_engine(cfg, seed=0)
assert obs.long_read is not None
assert obs.turnaround is not None
print('long-read + TAT init OK')
"
```

## Escalation

`crusher_labs/long_read_escalation.py` queues runs when **delivered** upstream results flag mixed infection, discordant modalities, or unexpected pathogens. Costs debit on **order** (`long_read_ordered_count`), not delivery.

## Related skills

- `testing-data-contracts` — validate JSON configs and sanity checker
- `orchestrator-smoke-test` — full 24-epoch loop
- `run-full-test-suite` — CI-equivalent pytest
