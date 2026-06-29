# Shedding Variance and Cabin-Mate Parameterization

**Status:** Implemented (PR #141, June 2026). See `engines/infection_dynamics_bridge.py`,
`engines/transmission_core.py`, `orchestrator_init.py::assign_cabin_mates`, and
`tests/test_shedding_variance_cabin_mates.py`.

Related: `docs/PLATFORM_CABIN_REVISION.md` (cabin-corridor spatial model).

---

## 1. Per-Agent Shedding Variance

### Mechanism

At infection time, each agent draws a shedding multiplier from a log-normal distribution:

```
agent.shedding_multiplier = 10^(rng.normal(0, shedding_variance_log10))
```

This multiplier persists for the duration of infection and scales all shedding output.
A multiplier of 1.0 (the median) gives the baseline curve value. A multiplier of 10
means 10× higher shedding. A multiplier of 0.1 means 10× lower.

The shedding function becomes:

```
shedding = 10^(curve[dpi] - dose_adjustment) * agent.shedding_multiplier
```

### Parameters per pathogen (pathogen profile JSON)

Based on published QMRA and epidemiological data:

| Pathogen | shedding_variance_log10 | Source / Rationale |
|---|---|---|
| norovirus_gii4 / norwalk_gi | 1.5 | Teunis et al 2015; Atmar et al 2008 (~3 log10 IQR) |
| sars_cov2_resp | 1.2 | Kissler et al 2021; Chen et al 2021 (superspreading) |
| influenza_a | 1.0 | Ip et al 2017; Leung et al 2020 |
| measles_virus | 0.8 | Moderate variation expected |
| legionella_pneumophila | 0.5 | Environmental source — low person-to-person variance |
| vibrio_cholerae_parahaemolyticus | 1.0 | Foodborne point-source |
| campylobacter_jejuni | 1.0 | Foodborne, moderate shedding variation |
| clostridioides_difficile | 1.5 | Curry et al 2013 carrier shedding >3 log10 |
| andes_hantavirus | 1.0 | Limited data |
| ebola_virus | 1.5 | Towner et al 2004 peak viremia 10^5–10^10 |

Schema field: `schemas/pathogen_profiles.schema.json` → `shedding_variance_log10`.

Default `shedding_variance_log10 = 0.0` preserves backward compatibility (multiplier = 1.0).

### Implementation

In `KorkinAgent.infect_with_pathogen(..., rng=..., profile=...)`:

- Draw `shedding_multiplier = draw_shedding_multiplier(rng, profile)`
- Store in `inf['shedding_multiplier']`
- In `get_pathogen_shedding()`: multiply baseline curve value by `inf.get('shedding_multiplier', 1.0)`
- Legacy single-pathogen `current_shedding` uses `agent.shedding_multiplier`

Seeding (`orchestrator_init.py`, `orchestrator_epoch.py`) and transmission-acquired
infections (`TransmissionCore`) pass `rng` and the pathogen profile so multipliers
are drawn consistently.

---

## 2. Cabin-Mate Tracking

### Mechanism

At ship initialization (`assign_cabin_mates()` in `orchestrator_init.py`, called from
`ShipSimulation.initialize()`), agents are grouped by `home_zone` into staterooms:

- Passenger standard cabins: 2 per cabin (1 cabin-mate)
- Crew cabins: 3 per cabin (shared berths)
- Override via `cabin_size` on zone metadata in `spatial_layout.json`

Each agent receives `cabin_mate_ids` (frozenset of co-occupant agent IDs).

Regenerate mega-cruise layout: `python3 scripts/generate_mega_cruise_cabin_layout.py`

### Transmission modification

In `_pathway_direct_contact()` (`engines/transmission_core.py`), when either party is
confined in a `Cabin_Corridor` zone:

- **Cabin-mate pair:** full direct-contact dose (they share the stateroom)
- **Non-mate pair:** dose × `0.01` (`NON_MATE_CONFINEMENT_CONTACT_FACTOR`) — minimal
  hallway/closed-door contact

HVAC, droplet, and fomite pathways are unchanged. Confined agents still skip fomite
pickup; HVAC dose is not reduced by confinement.

### Cabin size configuration

Per-zone in `spatial_layout.json`:

```json
{"id": "Pax_Corridor_D6_Port_Fwd", "cabin_size": 2, "type": "Cabin_Corridor", ...}
```

Defaults when `cabin_size` is omitted:

| Zone prefix / type | Default `cabin_size` |
|--------------------|----------------------|
| `Pax_Corridor_*` (`Cabin_Corridor`) | 2 |
| `Crew_Corridor_*` (`Cabin_Corridor`) | 3 |
| Other zone types | (no cabin pairing) |

### Impact

Individual confinement is meaningful on `mega_cruise_5000`: a quarantined case
transmits via direct contact primarily to their 1–2 cabin-mates, not all ~67 corridor
neighbors. HVAC remains the primary inter-cabin aerosol route.

---

## Golden regression note

Adding `shedding_variance_log10` to `active_profiles.json` shifts the default
24-epoch destroyer baseline (seed 42, epoch 23):

| Metric | Pre-variance | Post-variance |
|--------|--------------|---------------|
| Susceptible | 6 | 1 |
| Recovered | 10 | 15 |
| Trigger | CONFIRMED | BASELINE |

Exact `total_financial_usd` may differ slightly between Python 3.11 and 3.12; golden
tests pin SIR summary and trigger, assert cost > 0, and verify reproducibility on repeat
runs. See `tests/test_golden_orchestrator.py`.
