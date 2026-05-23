# Simulation Engines

This directory provides path mapping and references to the five sibling
simulation repositories.  The `engine_paths` module registers their
Python-importable directories on `sys.path` so that
`crusher_to_the_bridge` can seamlessly import their modules.

## Usage

```python
from engines import register_engine_paths

status = register_engine_paths(verbose=True)
# Now you can import py-contam and GRUMB modules directly:
#   from contam_input import ...
#   from simulation_blending_isme_perspectives import ...
```

## Linked Repositories

| Engine | Repository | Language | Role | Python Importable |
|---|---|---|---|---|
| **infection-dynamics** | `bckirkup/infection-dynamics` | Java / R | Korkin Lab agent-based outbreak model | No (subprocess / JSON) |
| **py-contam** | `bckirkup/py-contam` | Python | NIST CONTAM airflow automation wrapper | Yes (`python/`) |
| **EMOD-Generic** | `bckirkup/EMOD-Generic` | C++ / Python | IDM reference architecture for clinical diagnostics | Yes (`Scripts/`, `Regression/`) |
| **FRED** | `bckirkup/FRED` | C++ / R | CMU reference architecture for human compliance | No (subprocess / JSON) |
| **GRUMB** | `bckirkup/GRUMB` | Python / R | Genome-resolved metagenomics (CLR, blending, MDC) | Yes (`04_Machine_Learning/`, `perspective_simulations/`) |

> **Note:** These engines are consumed through their JSON output interface
> and/or direct Python imports.  They are *not* compiled into this
> repository.  See `telemetry_buffer/` for the neutral exchange schema.
