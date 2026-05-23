# Simulation Engines

This directory contains links and references to the upstream simulation
engines that produce ground-truth state for the Crusher-to-the-Bridge
digital twin.

## Linked Repositories

| Engine | Repository | Role |
|---|---|---|
| **infection-dynamics** | `bckirkup/infection-dynamics` | Korkin Lab agent-based outbreak model (Norwalk / COVID-19 on cruise ships) |
| **py-contam** | `bckirkup/py-contam` | NIST CONTAM airflow automation wrapper for zone-level pathogen transport |

> **Note:** These engines are consumed through their JSON output interface.
> They are *not* compiled into this repository.  See `telemetry_buffer/`
> for the neutral exchange schema.
