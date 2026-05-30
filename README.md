# Crusher to the Bridge

An epidemiological testbed that bridges a shipboard agent-based outbreak
simulation with microbiome simulation and biosurveillance diagnostics.
The platform integrates **infection-dynamics** (agent-based model),
**py-contam** (HVAC/airborne transport), **FRED-style behavioral
compliance**, **EMOD-style clinical progression**, and **GRUMB
multi-kingdom microbiome** seeding into a unified digital twin for
maritime disease outbreaks.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Validate configuration (JSON + crusher_labs/config.yaml)
python tools/sanity_checker.py --from-config

# Run a 24-epoch simulation (default)
python orchestrator.py

# Override epoch count
python orchestrator.py --epochs 250

# Launch LCARS dashboard (after simulation)
streamlit run dashboard.py

# Run the test suite
pytest tests/ -v --tb=short
```

Output is written to `telemetry_buffer/simulation_history.json` and
`telemetry_buffer/artificial_lab_notebook.json` (gitignored runtime artifacts).

## Picard & Presidio

| Component | Entry | Role |
|-----------|-------|------|
| **Picard_Framework** | `orchestrator.py`, `picard_framework/` | Steppable single-ship simulation |
| **decision_engine** | `decision_engine/` | Multi-agent decisions (model-agnostic) |
| **Presidio** | `presidio_runner.py`, `presidio/data/` | Fleet meta-simulation + experience store |

```bash
python3 presidio_runner.py --fleet-config presidio/data/config/smoke_fleet.json --cruises 1
```

Manuals: [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md), [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md).

## Architecture

```
orchestrator.py              Legacy CLI → picard_framework.ShipSimulation
presidio_runner.py           Fleet loop: decision_engine + ShipSimulation
picard_framework/            PicardRunSpec, catalog, ShipSimulation
decision_engine/             Policies, observations, ExperienceStore
orchestrator.py              Thin coordinator: init → epoch loop → finalize
├── orchestrator_types.py    Dataclasses, constants, state container
├── orchestrator_init.py     Spatial/engine/observation/wearable setup
├── orchestrator_epoch.py    Per-epoch step functions
├── orchestrator_record.py   History recording and JSON export
└── orchestrator_display.py  Terminal output helpers

crusher_labs/                Dr. Crusher's Bio-Diagnostic Suite
├── __init__.py              Config loader, modality builder
├── config.yaml              ★ Master configuration file (see below)
├── observation_core.py      Six instrument classes (air, surface, wastewater, RDT, qPCR, microbio)
├── protocol_engine.py       Stoplight computation, SOP activation, modifier application
├── lab_notebook.py          Artificial lab notebook (audit trail)
├── cost_ledger.py           Financial/material/labor cost tracking
├── stoplight.py             Ct → stoplight conversion
└── modalities/
    ├── syndromic.py         Symptom-based screening
    ├── clinical_rdt.py      Rapid antigen lateral-flow test
    ├── targeted_pcr.py      RT-qPCR panel
    ├── sequencing.py        Metagenomic shotgun sequencing
    └── wearable.py          Wearable physiological data stream

engines/                     External simulation bridges
├── infection_dynamics_bridge.py   Korkin agent-based model (KorkinShipEngine)
├── py_contam_bridge.py            HVAC zone-to-zone airborne transport
├── transmission_core.py           Six-pathway pathogen transmission
└── wearable_monitor.py            Wearable device registry & physiological model

tools/
├── sanity_checker.py        Pre-run config validation (pydantic + cross-refs)
└── gis_spatial_bridge.py    GIS shapefile → spatial layout converter

data/
├── config/                  Standing protocols, resource costs, logging
├── pathogens/               Pathogen profiles (dose-response, shedding curves)
├── platforms/               Ship spatial layouts and HVAC definitions
│   ├── destroyer_baseline/
│   ├── expedition_cruise_300/
│   ├── fletcher_class_destroyer/
│   ├── legend_class_nsc/
│   ├── mega_cruise_5000/
│   └── san_antonio_class_lpd/
├── microbiome_profiles/     GRUMB kingdom profiles by environment
├── shp/                     GIS shapefiles for spatial bridge
└── templates/               Reference configs (cruise ship, multi-pathogen)

schemas/                     JSON Schema definitions for all data contracts
telemetry_buffer/            Runtime output (simulation_history, lab_notebook)
│   agent_axes.py            Orthogonal agent state (infection / presentation / compliance)
dashboard.py                 LCARS Main Bridge Display (4 stations)
tests/                       278 tests across 15 modules
AGENTS.md                    Cursor Cloud / agent development notes
```

## Configuration Reference (`crusher_labs/config.yaml`)

The master configuration file drives all simulation parameters.  The
sanity checker validates every section when run with `--from-config`.
Below is a section-by-section reference.

### Global

```yaml
random_seed: 42
num_epochs: 24           # override via --epochs CLI flag
```

### Ship Graph

Defines the spatial layout, agent population, and agent class taxonomy.

```yaml
ship_graph:
  num_agents: 20
  agent_roles:
    passenger_fraction: 0.70
    crew_fraction: 0.30
  spatial_layout: "data/platforms/destroyer_baseline/spatial_layout.json"
  air_flow_paths: "data/platforms/destroyer_baseline/air_flow_paths.json"
```

#### Agent Classes

Replaces the legacy binary passenger/crew split with a configurable
taxonomy.  Each class specifies a fraction of the total population,
role group, and preferred zones.  **Fractions must sum to 1.0.**

```yaml
  agent_classes:
    - class_id: "passenger_general"
      role_group: "passenger"       # "passenger" or "crew"
      fraction: 0.50
      home_zone_preference: "Berthing"
      free_zone_preference: ""
      duty_zone: ""
    - class_id: "crew_medical"
      role_group: "crew"
      fraction: 0.05
      duty_zone: "MedBay"
    # ... additional classes
```

Seven built-in classes: `passenger_general`, `passenger_family`,
`passenger_elderly`, `crew_general`, `crew_medical`, `crew_engineering`,
`crew_galley`.  Add new classes by extending this list.

#### Infection Counters

Per-group metrics in `ship_graph.infection_counters` (attack rates, thresholds,
`on_exceed: confine_symptomatic`, `exempt_classes`). See `crusher_labs/config.yaml`.

#### Gender Distribution

Orthogonal to agent class.  Assigned randomly at startup.
**Values must sum to 1.0.**

```yaml
  gender_distribution:
    male: 0.50
    female: 0.50
```

### HVAC / CONTAM Transport

```yaml
hvac:
  filter_efficiency: 0.50      # [0,1] — MERV-8=0.20, MERV-13=0.50, HEPA=0.999
  natural_decay_rate: 0.10     # fraction lost per epoch to settling/inactivation
  filter_type: "MERV-13"       # human-readable label
```

### EMOD-Style Clinical Progression

```yaml
emod_progression:
  incubation_epochs: 2
  shedding_phases:
    - {name: "early",  max_rate: 20.0, sensitivity_cap: 0.30}
    - {name: "peak",   max_rate: 80.0, sensitivity_cap: 0.95}
    - {name: "late",   max_rate: 40.0, sensitivity_cap: 0.80}
  phase_durations: [3, 5, 4]   # must match shedding_phases count
```

### FRED-Style Behavioral Compliance

```yaml
fred_behavior:
  quarantine_compliance: 0.85   # [0,1] — P(agent complies with isolation)
  compliance_delay_epochs: 1
  healthy_noise_categories:
    - {reason: "seasickness",  probability: 0.008}
    - {reason: "fatigue",      probability: 0.005}
    - {reason: "minor_injury", probability: 0.002}
```

### Escalation Thresholds

```yaml
escalation:
  syndromic_suspect_threshold: 3    # daily sick-call count → SUSPECTED
  pcr_confirm_ct_threshold: 35.0    # Ct ≤ this → CONFIRMED
```

### Diagnostic Modalities

```yaml
syndromic:
  sick_call_probability: 0.70       # [0,1]
  background_noise_rate: 0.015      # [0,1]
  cadence: 1

clinical_rdt:
  base_sensitivity: 0.95            # [0,1]
  sigmoid_k: 0.08
  sigmoid_midpoint: 50.0
  specificity: 0.97                 # [0,1]
  cadence: 1

targeted_pcr:
  extraction_efficiency: 0.35
  ct_slope: -3.322
  ct_intercept: 40.0
  lod_ct_threshold: 38.0
  cadence: 4

sequencing:
  read_depth: 100000                  # MetagenomicSequencing modality (environmental shotgun)
  pseudocount: 1.0e-6
  clr_shift_scale: 0.15
  cadence: 8

wastewater_sequencing:
  read_depth: 50000                   # WastewaterSequencingGrid instrument (pooled greywater)
  dirichlet_concentration: 100.0
  pseudocount: 1.0e-6
```

Read depths are centralized here (not hardcoded in observation modules). The
orchestrator and Crusher Labs loader use `wastewater_sequencing_params()` /
`sequencing_params()` from `crusher_labs/__init__.py`.

### Multi-Pathogen Configuration

```yaml
multi_pathogen:
  profiles_path: "data/pathogens/active_profiles.json"
  enable_coinfection: true
  immunocompromised_fraction: 0.05    # [0,1]
  immunocompromised_multiplier: 2.0
```

Pathogen profiles are defined in JSON files under `data/pathogens/`.
Each profile specifies dose-response parameters, shedding curves,
transmission routes, illness probabilities, and microflora disruption
signatures.  See `data/templates/multi_pathogen_cruise_ship.json` for
a reference example with concurrent Norovirus + SARS-CoV-2.

### Microflora Disruption

```yaml
microflora:
  enable_dual_signal: true
  disrupted_shed_mass: 50.0
  clr_shift_scale: 0.15
  graywater_zones: ["Engine_Room"]   # cross-referenced against spatial layout
```

### Wearable Physiological Monitoring

An extensible device registry that simulates Oura Ring / Garmin Watch
style wearable sensors.  Each device defines its sensor channels, noise
model, and per-pathogen infection-response profiles.

```yaml
wearable_monitoring:
  enabled: true

  devices:
    - device_id: "oura_ring"
      channels: [heart_rate, hrv, body_temp, spo2, sleep_score, respiratory_rate]
      noise:
        - {channel: heart_rate,  sigma: 2.5, drift_rate: 0.1, dropout_prob: 0.01}
        # ... per-channel noise parameters
      infection_responses:
        - pathogen_category: "enteric_viral"
          channel_responses:
            - {channel: heart_rate, early: 3.0, peak: 10.0, late: 5.0, recovery: 1.0}
            # ... per-channel deltas for each EMOD phase
        - pathogen_category: "respiratory_viral"
          channel_responses: [...]
      phase_boundaries:
        - {day: 0,  phase: "early"}
        - {day: 3,  phase: "peak"}
        - {day: 8,  phase: "late"}
        - {day: 12, phase: "recovery"}

    - device_id: "garmin_watch"
      channels: [heart_rate, hrv, body_temp, spo2, activity_score, respiratory_rate]
      # ... same structure

  class_device_map:
    - {agent_class: "default",           device_id: "oura_ring"}
    - {agent_class: "crew_medical",      device_id: "garmin_watch"}
    - {agent_class: "crew_engineering",  device_id: "garmin_watch"}
    - {agent_class: "crew_galley",       device_id: "garmin_watch"}
    - {agent_class: "passenger_elderly", device_id: "oura_ring"}

  observation_noise_sigma: 0.5     # ≥ 0
  sync_dropout_prob: 0.02          # [0,1]
  anomaly_z_threshold: 2.0         # > 0 — z-score threshold for anomaly detection

  fleet_thresholds:                # shipwide rates for wearable_fleet_monitor stoplights
    fleet_fever_rate_amber: 0.03
    fleet_fever_rate_red: 0.08
    fleet_anomaly_rate_amber: 0.05
    fleet_anomaly_rate_red: 0.12
```

Wearable stoplights feed SOP-012..SOP-014; integrated **detection escalation**
(SOP-015..SOP-016) fires when multiple detection modes (syndromic, wearable,
environmental, clinical) reach AMBER/RED together (`min_modes_affected` in
`protocols.json`).

**Adding a new device:** Add an entry to `devices` with a unique
`device_id`, its channel list, noise parameters, and infection response
profiles.  Then assign it to agent classes via `class_device_map`.
No code changes required.

**Noise model:** Each channel has independent Gaussian noise (`sigma`),
sensor drift (`drift_rate` per epoch), and random dropout probability
(`dropout_prob`).

**Infection response:** Per-pathogen-category deltas are applied to each
channel based on the agent's current EMOD phase (early → peak → late →
recovery).  Phase boundaries are configurable per device.

### GRUMB Multi-Kingdom Seeding

```yaml
grumb_seeding:
  kingdoms: ["Bacteria", "Archaea", "Fungi", "Virus"]
  pseudocount: 1.0e-6
```

## Platforms

Six ship platforms are included, each with spatial layout and HVAC
airflow definitions:

| Platform | Description |
|----------|-------------|
| `destroyer_baseline` | Gleaves-class destroyer (default, 6 zones) |
| `expedition_cruise_300` | 300-passenger expedition cruise ship |
| `fletcher_class_destroyer` | Fletcher-class WWII destroyer |
| `legend_class_nsc` | USCG Legend-class National Security Cutter |
| `mega_cruise_5000` | 5000-passenger mega cruise ship |
| `san_antonio_class_lpd` | USN San Antonio-class LPD |

To switch platforms, update the `spatial_layout` and `air_flow_paths`
paths in `config.yaml`, then validate:

```bash
python tools/sanity_checker.py --from-config
```

## Transmission Pathways

Six pathways in `engines/transmission_core.py`: direct contact, droplet,
HVAC airborne, fomite, food contamination (`food_contamination` profile block),
environmental (`environmental_contamination` profile block).

## Confinement: Quarantine vs. Isolation

- **Quarantine** (`quarantined`): confined to quarters, HVAC-connected
- **Isolation** (`isolated`): isolation ward, no HVAC shedding (rare capacity)

FRED compliance vs. `quarantine_refusers` tracked in telemetry and dashboard.

## Agent State (Orthogonal Axes)

Each agent in `simulation_history.json` carries three independent fields
(see `telemetry_buffer/agent_axes.py`):

| Axis | Values | Meaning |
|------|--------|---------|
| `infection_state` | susceptible, infected, recovered, immune | SIR / immune biology |
| `symptom_presentation` | asymptomatic, mild, symptomatic, severe | Clinical presentation |
| `compliance_status` | compliant, non_compliant, isolated, quarantined | FRED confinement |

The legacy `symptom_status` field is still emitted for backward compatibility
but is deprecated. Counters, syndromic logic, and confinement SOPs resolve
axes via `resolve_agent_axes()`.

## Cost Accounting

Per-epoch `cost_accounting` in simulation history includes
`materials_consumed` and `by_category` (surveillance vs. intervention).
The ledger debits `resource_costs.json` **`per_test_costs`** for each
environmental sample and sick-call clinical test, plus SOP activation and
per-epoch protocol costs. Budget balances are tracked for reporting only —
spending is never blocked when inventory is depleted.

## Standing Operating Procedures (SOPs)

Protocols in `data/config/protocols.json` (SOP-001..SOP-016), activated from
stoplights (no hardcoded epoch schedules).

| SOP | Name | Trigger instrument | Key modifiers |
|-----|------|-------------------|---------------|
| SOP-001–002 | Ventilation upgrades | Air sniffer | HVAC filters |
| SOP-003 | Surface Decontamination | Surface swab | `surface_decontamination_factor` |
| SOP-004–005 | PPE | Wastewater | Transmission scalars |
| SOP-006 | Diagnostics | Clinical RDT | `diagnostic_cadence_multiplier` |
| SOP-007 | Galley Closure | Clinical micro | `close_zones` |
| SOP-008 | Symptomatic Confinement | Clinical RDT | `confine_symptomatic_to_quarters` |
| SOP-009 | General Confinement | Clinical qPCR | `confine_all_to_quarters`, `exempt_classes` |
| SOP-010 | VSP Threshold | Clinical RDT | Confinement + surface decon |
| SOP-011 | Passenger-only Confinement | Clinical RDT | Crew `exempt_classes` |
| SOP-012 | Wearable Individual Triage | `wearable_physiological_monitor` | Symptomatic confinement |
| SOP-013 | Wearable Fleet Surveillance | `wearable_fleet_monitor` | 1.5× diagnostic cadence |
| SOP-014 | Wearable Fleet Outbreak | `wearable_fleet_monitor` | PPE + contact/droplet scalars |
| SOP-015 | Integrated Escalation (Elevated) | `detection_escalation` | 2× diagnostic cadence |
| SOP-016 | Integrated Escalation (Critical) | `detection_escalation` | Confinement + PPE + surface decon |

**Detection escalation** SOPs use `min_modes_affected` (default 2) instead of
zone counts — the protocol engine aggregates syndromic, wearable, environmental,
and clinical stoplight modes before evaluating the trigger.

## Sanity Checker

The pre-run validator (`tools/sanity_checker.py`) checks all
configuration files for structural and logical correctness:

```bash
# Validate using paths from config.yaml (recommended — also validates config.yaml itself)
python tools/sanity_checker.py --from-config

# Validate specific directories manually
python tools/sanity_checker.py --config-dir data/config \
                               --platform-dir data/platforms/destroyer_baseline \
                               --pathogen-file data/pathogens/active_profiles.json
```

**JSON data file checks** (always run):
- Pydantic schema validation (spatial layout, airflow, protocols, pathogens, resources)
- Mathematical bounds (probabilities in [0,1], non-negative constraints)
- Graph referential integrity (zone references, HVAC room mappings, adjacency edges)
- Logical contradictions (transmission routes, material references)

**config.yaml checks** (run with `--from-config`):
- Agent class fractions sum to 1.0, valid role_groups, no duplicate class_ids
- Gender distribution sums to 1.0, non-negative values
- Wearable device uniqueness, channel consistency, noise/dropout bounds, class_device_map validity
- Modality probabilities in [0,1], non-negative cadences
- HVAC filter_efficiency in [0,1], non-negative decay rate
- EMOD phase/duration count match, positive durations, sensitivity caps in [0,1]
- Escalation thresholds non-negative
- FRED compliance probability in [0,1], noise category probabilities
- Multi-pathogen fraction/multiplier bounds
- Microflora graywater_zones cross-referenced against spatial layout
- Infection counter metrics, thresholds, and `exempt_classes` referential integrity

## Testing

```bash
# Full suite (278 tests)
pytest tests/ -v --tb=short

# Specific modules
pytest tests/test_orchestrator.py           # orchestrator, quarantine/SOP confinement
pytest tests/test_infection_counters.py     # attack-rate counters, exempt_classes
pytest tests/test_agent_axes.py             # orthogonal infection/presentation/compliance
pytest tests/test_protocol_engine.py        # wearable + detection-escalation stoplights
pytest tests/test_sequencing_config.py      # config.yaml read_depth wiring
pytest tests/test_cost_accounting.py        # per-test debits and materials telemetry
pytest tests/test_transmission_pathways.py  # food/environmental pool init
pytest tests/test_dashboard.py              # LCARS dashboard imports
pytest tests/test_sanity_checker.py         # config validation
pytest tests/test_law_compliance.py         # architectural law invariants
pytest tests/test_data_contracts.py         # JSON schema / referential integrity
pytest tests/test_telemetry_seams.py        # cross-module data flow
```

Cloud agents and CI environments: see `AGENTS.md` (`python3`, headless Streamlit).

CI (`.github/workflows/ci.yml`) runs sanity checks, the full pytest suite,
import hygiene checks, a dashboard import smoke test, and a 24-epoch orchestrator run.

## Data Contracts

All JSON configuration and output files have corresponding JSON Schema
definitions in `schemas/`.  See `schemas/README.md` for the full
mapping and validation instructions.

## Constants

Trigger-status constants live in `orchestrator_types.py`. Orthogonal agent
axis literals are canonical in `telemetry_buffer/agent_axes.py` and re-exported
from `orchestrator_types.py`:

| Constant family | Module | Usage |
|-----------------|--------|-------|
| `STATUS_*` | `orchestrator_types` | BASELINE / SUSPECTED / CONFIRMED escalation |
| `INFECTION_*` | `agent_axes` | SIR infection axis |
| `PRESENTATION_*` | `agent_axes` | Clinical presentation (mild counts as symptomatic for counters) |
| `COMPLIANCE_*` | `agent_axes` | FRED confinement (quarantine vs. isolation ward) |
| `LOCATION_*` | `orchestrator_types` | Synthetic quarters locations for confined agents |

## License

MIT
