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
pip install pyyaml numpy pydantic pytest

# Validate configuration
python tools/sanity_checker.py --from-config

# Run a 24-epoch simulation (default)
python orchestrator.py

# Override epoch count
python orchestrator.py --epochs 250

# Run the test suite
pytest tests/ -v --tb=short
```

Output is written to `telemetry_buffer/simulation_history.json` and
`telemetry_buffer/artificial_lab_notebook.json`.

## Architecture

```
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
├── transmission_core.py           Multi-route pathogen transmission
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
telemetry_buffer/            Runtime output (simulation_history, ground_truth, lab_notebook)
tests/                       238 tests across 10 modules
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
  read_depth: 100000
  pseudocount: 1.0e-6
  cadence: 8
```

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
```

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

## Standing Operating Procedures (SOPs)

Protocols are defined in `data/config/protocols.json` and activated
automatically by the protocol engine based on stoplight levels.

| SOP | Function | Trigger |
|-----|----------|---------|
| SOP-001 | Enhanced environmental sampling | AMBER stoplight |
| SOP-009 | Full-ship lockdown / zone closures | RED stoplight, `confine_all_to_quarters` |
| SOP-010 | Surface decontamination | RED stoplight, `surface_decontamination_factor` |

Zone closures (`close_zones`) relocate agents from closed zones to
their home zones.  Surface decontamination reduces zone pathogen mass
by a configurable factor.

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
# Full suite (254 tests)
pytest tests/ -v --tb=short

# Specific modules
pytest tests/test_orchestrator.py           # orchestrator, quarantine/SOP confinement
pytest tests/test_infection_counters.py     # attack-rate counters, exempt_classes
pytest tests/test_transmission_pathways.py  # food/environmental pool init
pytest tests/test_dashboard.py              # LCARS dashboard imports
pytest tests/test_sanity_checker.py         # config validation
pytest tests/test_law_compliance.py         # architectural law invariants
pytest tests/test_data_contracts.py         # JSON schema / referential integrity
pytest tests/test_telemetry_seams.py        # cross-module data flow
```

CI (`.github/workflows/ci.yml`) runs sanity checks, the full pytest suite,
import hygiene checks, a dashboard import smoke test, and a 24-epoch orchestrator run.

## Data Contracts

All JSON configuration and output files have corresponding JSON Schema
definitions in `schemas/`.  See `schemas/README.md` for the full
mapping and validation instructions.

## Constants

String literal constants are defined in `orchestrator_types.py` to
avoid hardcoded strings across the codebase:

| Constant | Value | Usage |
|----------|-------|-------|
| `STATUS_BASELINE` | `"BASELINE"` | Initial trigger status |
| `STATUS_SUSPECTED` | `"SUSPECTED"` | Syndromic threshold exceeded |
| `STATUS_CONFIRMED` | `"CONFIRMED"` | PCR-confirmed outbreak |
| `SYMPTOM_ASYMPTOMATIC` | `"asymptomatic"` | Agent symptom status |
| `SYMPTOM_SYMPTOMATIC` | `"symptomatic"` | Agent symptom status |
| `SYMPTOM_ISOLATED` | `"isolated"` | Agent in quarantine |
| `SYMPTOM_NON_COMPLIANT` | `"non_compliant"` | Agent refusing quarantine |
| `LOCATION_ISOLATED` | `"Isolated_In_Quarters"` | Quarantine location |

## License

MIT
