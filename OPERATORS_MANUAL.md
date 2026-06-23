# Crusher-to-the-Bridge — Operator's Manual

**Version:** 2.3  
**Platform:** Biodefense Digital Twin for Maritime Outbreak Simulation  
**License:** MIT

> **Manuals bifurcated (v2.3):**
> - **Ship / Picard:** [OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md) — single-cruise simulation, config.yaml, instruments, SOPs
> - **Fleet / game theory / Presidio:** [OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md) — multi-cruise decisions, experience, economics
>
> This file retains the full historical reference for the repository. GUI (dashboard) documentation is unchanged here but deferred for future LCARS updates.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Master Configuration (`config.yaml`)](#3-master-configuration-configyaml)
4. [Data Files Reference](#4-data-files-reference)
5. [Drafting Custom Standing Operating Procedures](#5-drafting-custom-standing-operating-procedures)
6. [GIS Spatial Bridge Tool](#6-gis-spatial-bridge-tool)
7. [Configuration Sanity Checker](#7-configuration-sanity-checker)
8. [The Artificial Lab Notebook — Fidelity Tiers](#8-the-artificial-lab-notebook--fidelity-tiers)
9. [The USS Crusher LCARS Command Deck](#9-the-uss-crusher-lcars-command-deck)
10. [Simulation Output Reference](#10-simulation-output-reference)
11. [Contributors & Sibling Repositories](#11-contributors--sibling-repositories)

---

## 1. Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
# Optional: pip install check-jsonschema
```

### Run a Simulation

```bash
# Step 1: Validate configuration files (including config.yaml)
python tools/sanity_checker.py --from-config

# Step 2: Execute the simulation (default 24 epochs from config.yaml)
python orchestrator.py

# Or override the epoch count via CLI:
python orchestrator.py --epochs 250

# Step 3: Launch the interactive dashboard
streamlit run dashboard.py
```

### Windows Launcher (Any Directory)

Double-click `run_dashboard.bat` or run it from any command prompt.
It auto-detects the repository root, runs the orchestrator, and launches
the dashboard.

### Linux/macOS Launcher

```bash
chmod +x run_dashboard.sh
./run_dashboard.sh
```

---

## 2. System Architecture Overview

Crusher-to-the-Bridge is a **bridging package** — middleware that
connects five independent simulation domains into a single orchestrated
epoch loop:

```
┌─────────────────────────────────────────────────────────────┐
│                    orchestrator.py                           │
│         Main simulation loop (for epoch in epochs)          │
│         Driven by crusher_labs/config.yaml                   │
└──────┬──────────┬─────────────┬──────────────┬─────────────┘
       │          │             │              │
       ▼          ▼             ▼              ▼
 ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐
 │ Korkin   │ │ Six-Pathway│ │ py-contam  │ │ Wearable       │
 │ Lab ABM  │ │ Transmis.  │ │ HVAC       │ │ Monitor        │
 │ Bridge   │ │ Core       │ │ Transport  │ │                │
 │          │ │ Direct–4   │ │ Mass-      │ │ Oura / Garmin  │
 │ Agents   │ │ Food/Env   │ │ balance    │ │ Agent + fleet  │
 │ SIR      │ │ 5–6        │ │ Filter η   │ │ stoplights     │
 │ Dose-resp│ │            │ │            │ │                │
 └──────────┘ └────────────┘ └────────────┘ └────────────────┘
       │          │             │              │
       └──────────┼─────────────┼──────────────┘
                  ▼             ▼
 ┌──────────────┐ ┌────────────┐ ┌────────────────┐
 │ Observation  │ │ Protocol   │ │ Cost Ledger    │
 │ Engine       │ │ Engine     │ │                │
 │ 6 instruments│ │ Stoplight  │ │ $USD budget    │
 │ + QC         │ │ → SOP      │ │ Materials      │
 │              │ │ triggers   │ │ Labor hours    │
 └──────────────┘ └────────────┘ └────────────────┘
       │                             │
       ▼                             ▼
 ┌─────────────────────────────────────────────────┐
 │            Artificial Lab Notebook               │
 │  HIGH / MID / LOW fidelity output tiers          │
 └─────────────────────────────────────────────────┘
```

### The Feedback Loop

The simulation runs a closed-loop control cycle:

1. **Instruments** sample environmental and patient data each epoch
2. **Observation Engine** classifies results into LOW_FIDELITY stoplights (GREEN/AMBER/RED)
3. **Wearable pipeline** adds per-agent (`wearable_physiological_monitor`) and
   fleet (`wearable_fleet_monitor`) stoplights from fever/anomaly rates
4. **Detection escalation** aggregates syndromic, wearable, environmental, and
   clinical modes into `detection_escalation` stoplights (SOP-015/016)
5. **Protocol Engine** evaluates stoplight conditions against SOP trigger rules
6. **Active SOPs** inject physics modifiers (HVAC efficiency, PPE scalars, zone closures)
7. **Transmission Core** reads modified scalars on the next epoch
8. **Cost Ledger** debits per-test surveillance costs, protocol costs, and
   material consumption (reported per epoch in telemetry)

This loop is **fully autonomous** — SOPs activate and deactivate based
on diagnostic conditions.  There are no hardcoded epoch schedules.

### Six-Pathway Transmission Core

Pathways 1–4: direct, droplet, HVAC airborne, fomite. Pathways 5–6: food
contamination and environmental colonization (per-pathogen profile blocks).
Dashboard uses `pathway_breakdown` in contact-tracing events.

### Quarantine vs. Isolation

| Mode | Field | HVAC |
|------|-------|------|
| Quarantine | `summary.quarantined` | Connected in home zone |
| Isolation | `summary.isolated` | No shedding (ward) |

`confine_symptomatic_to_quarters` / `confine_all_to_quarters` trigger quarantine.
`exempt_classes` skips confinement for listed agent classes.

### Wearable Monitoring Pipeline

In parallel with the diagnostic feedback loop, the wearable monitoring
system (`engines/wearable_monitor.py`) provides continuous physiological
surveillance:

1. **Device Registry** — Config-driven device definitions (Oura Ring,
   Garmin Watch, CGM Patch) with per-channel sensor specifications
2. **Multi-device Assignment** — Each agent can wear 0+ devices;
   class-based mapping with per-device coverage fraction (Bernoulli
   sampling) and visibility tier
3. **Chronic Disease Devices** — Agents with chronic conditions
   (e.g., type 2 diabetes) receive additional devices via
   `chronic_disease_device_map`
4. **Baseline Personalization** — Per-agent baselines adjusted by agent
   class (e.g., elderly passengers have elevated resting heart rate),
   gender, and chronic disease offsets
5. **Infection Response** — Pathogen-category-specific channel deltas
   modulated by EMOD shedding phase (early → peak → late → recovery)
6. **Confounder Injection** — Per-epoch Bernoulli sampling of confounders
   (seasickness, alcohol, exercise) that add bias and multiply noise on
   affected channels, filtered by susceptible agent classes
7. **Noise Injection** — Gaussian noise, sensor drift, and random
   dropout simulate real-world wearable data quality
8. **Anomaly Detection** — Per-channel signed z-scores flag physiological
   deviations; a confounder-aware scorer (`engines/wearable_anomaly_scorer.py`)
   computes weighted residual `infection_score` after template matching and
   fleet-wide downweighting
9. **Detection Profile Gating** — Per-device sensitivity/specificity
   probabilistically suppress or inject anomaly/fever flags; alert
   latency suppresses early-infection detections
10. **Cascade Entry** — Diagnostic cascade Tier-0 uses `infection_score`
    (default > 1.5) or fever via `cascade_entry.wearable_alert_fusion`;
    raw `anomaly_count` remains for fleet stoplights and per-agent RED/AMBER
11. **Visibility Filtering** — `medical_staff` data flows to fleet
    stoplights; `wearer_only` data influences agent behavior only;
    `both` does both
12. **Protocol triggers** — RED per-agent alerts can activate SOP-012
    (symptomatic confinement); fleet AMBER/RED rates activate SOP-013/014

### Orthogonal Agent State Axes

Ground-truth and per-epoch telemetry use three independent fields per agent
(`telemetry_buffer/agent_axes.py`), replacing the legacy combined
`symptom_status` string:

| Field | Role |
|-------|------|
| `infection_state` | SIR biology: susceptible, infected, recovered, immune |
| `symptom_presentation` | Clinical: asymptomatic, mild, symptomatic, severe |
| `compliance_status` | FRED confinement: compliant, non_compliant, isolated, quarantined |

Infection counters, syndromic sick-call logic, and confinement SOPs call
`resolve_agent_axes()`. Downstream tools should prefer the three-axis fields;
`symptom_status` remains in JSON output for backward compatibility only.

---

## 3. Master Configuration (`config.yaml`)

The file `crusher_labs/config.yaml` is the **single master configuration
file** that drives all simulation parameters.  The sanity checker
validates every section when run with `--from-config`.

### 3.1 Global Settings

```yaml
random_seed: 42
num_epochs: 24           # override via --epochs CLI flag
```

### 3.2 Agent Class Taxonomy

Replaces the legacy binary passenger/crew split with a configurable
taxonomy.  Each class specifies a fraction of the total population,
role group, and preferred zones.

```yaml
ship_graph:
  num_agents: 20
  agent_roles:
    passenger_fraction: 0.70
    crew_fraction: 0.30

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

**Seven built-in classes:**

| Class ID | Role Group | Fraction | Duty Zone | Description |
|----------|-----------|----------|-----------|-------------|
| `passenger_general` | passenger | 0.50 | — | General passengers |
| `passenger_family` | passenger | 0.10 | — | Family groups |
| `passenger_elderly` | passenger | 0.10 | — | Elderly passengers (elevated baseline HR, reduced SpO2) |
| `crew_general` | crew | 0.10 | — | General crew members |
| `crew_medical` | crew | 0.05 | MedBay | Medical staff |
| `crew_engineering` | crew | 0.10 | Engine | Engineering crew |
| `crew_galley` | crew | 0.05 | Galley | Galley / food service crew |

**Rules:**
- Class fractions **must sum to 1.0**
- Each class_id must be unique
- `role_group` must be `"passenger"` or `"crew"`
- `duty_zone` values are cross-referenced against `spatial_layout.json`

To add a new class, append an entry to the `agent_classes` list.
No code changes required.

#### Infection Counters

Configured under `ship_graph.infection_counters` in `config.yaml`. Supports
`attack_rate`, thresholds, `on_exceed: confine_symptomatic`, and `exempt_classes`.
Reported in telemetry and the LCARS Bridge Status Display.

### 3.3 Gender Distribution

Orthogonal to agent class.  Assigned randomly at startup.
**Values must sum to 1.0.**

```yaml
  gender_distribution:
    male: 0.50
    female: 0.50
```

Gender affects wearable baseline offsets (e.g., females have a +2 bpm
heart rate offset) but does not influence transmission dynamics.

### 3.4 HVAC / CONTAM Transport

```yaml
hvac:
  filter_efficiency: 0.50      # [0,1] — MERV-8=0.20, MERV-13=0.50, HEPA=0.999
  natural_decay_rate: 0.10     # fraction lost per epoch to settling/inactivation
  filter_type: "MERV-13"       # human-readable label
```

The filter efficiency (`η`) feeds into the CONTAM mass-balance equation:
`dM_i/dt = Σ Q_ji · C_j · (1−η) − Q_out · C_i + S_i − λ · M_i`

### 3.5 EMOD-Style Clinical Progression

Models the time course of infection through shedding phases aligned
with the EMOD epidemiological modeling framework.

```yaml
emod_progression:
  incubation_epochs: 2
  shedding_phases:
    - {name: "early",  max_rate: 20.0, sensitivity_cap: 0.30}
    - {name: "peak",   max_rate: 80.0, sensitivity_cap: 0.95}
    - {name: "late",   max_rate: 40.0, sensitivity_cap: 0.80}
  phase_durations: [3, 5, 4]   # must match shedding_phases count
```

| Phase | Duration | Shedding Rate | Diagnostic Sensitivity |
|-------|----------|--------------|------------------------|
| Incubation | 2 epochs | 0 (not yet shedding) | — |
| Early | 3 epochs | Up to 20.0 | 30% |
| Peak | 5 epochs | Up to 80.0 | 95% |
| Late | 4 epochs | Up to 40.0 | 80% |

These phases also drive the wearable infection response profiles
(heart rate elevation, temperature rise, SpO2 drop, etc.).

**Rules:**
- `phase_durations` count must match `shedding_phases` count
- All durations must be positive
- `sensitivity_cap` values must be in [0.0, 1.0]

### 3.6 FRED-Style Behavioral Compliance

Models human behavior and quarantine compliance based on the FRED
(Framework for Reconstructing Epidemiological Dynamics) approach.

```yaml
fred_behavior:
  quarantine_compliance: 0.85   # [0,1] — P(agent complies with isolation)
  compliance_delay_epochs: 1
  healthy_noise_categories:
    - {reason: "seasickness",  probability: 0.008}
    - {reason: "fatigue",      probability: 0.005}
    - {reason: "minor_injury", probability: 0.002}
```

- `quarantine_compliance` — Probability that an infected agent will
  comply with an isolation order.  Non-compliant agents remain in the
  general population, continuing to shed and transmit.
- `compliance_delay_epochs` — Delay before a non-compliant agent
  eventually isolates.
- `healthy_noise_categories` — Background sick-call reasons for healthy
  agents (seasickness, fatigue, minor injury).  These generate false
  positive syndromic signals that the observation engine must
  distinguish from true infections.

### 3.7 Escalation Thresholds

```yaml
escalation:
  syndromic_suspect_threshold: 3    # daily sick-call count → SUSPECTED
  pcr_confirm_ct_threshold: 35.0    # Ct ≤ this → CONFIRMED
```

The trigger status transitions through three phases:
`BASELINE → SUSPECTED → CONFIRMED`

### 3.8 Diagnostic Modality Parameters

Each diagnostic modality has configuration parameters controlling
sensitivity, specificity, noise, and sampling cadence.

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
  read_depth: 100000                  # MetagenomicSequencing modality
  pseudocount: 1.0e-6
  clr_shift_scale: 0.15
  cadence: 8

wastewater_sequencing:
  read_depth: 50000                   # WastewaterSequencingGrid instrument
  dirichlet_concentration: 100.0
  pseudocount: 1.0e-6

instrument_turnaround:
  config_path: "data/config/instrument_turnaround.json"

long_read_sequencing:
  enabled: false                      # Escalation-only Oxford Nanopore verification
  params_path: "data/config/long_read_sequencing_params.json"
  default_profile: "flongle_rapid"    # or minion_standard
```

**Instrument turnaround (TAT):** `data/config/instrument_turnaround.json` defines
how many epochs elapse before each observation instrument’s results appear in
`observation_engine` and drive stoplights. Defaults include wastewater +1 epoch
(next-day pooled result), clinical microbiology +3 epochs (culture incubation),
and rapid assays at 0 epochs. Long-read TAT is taken from the active Nanopore
deployment profile (`epoch_fraction` or `full_run_hours` in
`long_read_sequencing_params.json`).

**Long-read sequencing:** When `long_read_sequencing.enabled` is true, mixed-
infection, discordant, or unexpected signals from **delivered** routine results
queue Nanopore verification runs. Parameters (read depth, detection limits,
error injection) live in `data/config/long_read_sequencing_params.json`. Flow-
cell costs debit when a run is **ordered**, not when results deliver.

**Read depth** for shotgun environmental sequencing and pooled wastewater
grid sampling is defined only in `config.yaml`. The orchestrator passes
`wastewater_sequencing_params()` into `WastewaterSequencingGrid`; the lab
notebook and modalities read the same values (no duplicate constants in
instrument code).

### 3.9 Multi-Pathogen Configuration

Enables concurrent simulation of multiple pathogens with independent
mass pools, dose-response models, and shedding kinetics.

```yaml
multi_pathogen:
  profiles_path: "data/pathogens/active_profiles.json"
  enable_coinfection: true
  immunocompromised_fraction: 0.05    # [0,1]
  immunocompromised_multiplier: 2.0
```

- `enable_coinfection` — When `true`, agents can carry multiple
  pathogens simultaneously.  Each pathogen maintains independent SIR
  state and shedding curves.
- `immunocompromised_fraction` — Fraction of agents with elevated
  susceptibility (dose scaling multiplied by `immunocompromised_multiplier`).

### 3.10 Microflora Disruption

```yaml
microflora:
  enable_dual_signal: true
  disrupted_shed_mass: 50.0
  clr_shift_scale: 0.15
  graywater_zones: ["Engine_Room"]
```

When a pathogen has `microflora_disruption.causes_disruption == true`,
infected agents shed altered microbial signatures alongside pathogen
particles.  The wastewater sequencing grid can detect these
background kingdom-level CLR shifts even when pathogen mass is below
direct detection limits.

`graywater_zones` accumulate downstream microbial signatures and must
be cross-referenced against `spatial_layout.json`.

### 3.11 Wearable Physiological Monitoring

An extensible device registry that simulates wearable sensors
(Oura Ring, Garmin Watch, CGM Patch) for continuous physiological
surveillance.  Each agent can wear multiple devices simultaneously,
assigned by agent class (with coverage fraction) and chronic disease.

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
      detection_profile:              # imperfect sensing (optional)
        sensitivity: 0.78
        specificity: 0.92
        alert_latency_hours: 6
        fever_sensitivity: 0.85
        fever_specificity: 0.95
      confounders:                    # per-epoch noise sources (optional)
        - confounder_id: "seasickness"
          prevalence: 0.15
          affected_channels:
            heart_rate: {bias: 8.0, noise_mult: 1.5}
            hrv: {bias: -12.0, noise_mult: 1.8}
          susceptible_classes: [passenger_general, passenger_elderly, passenger_family]

    - device_id: "garmin_watch"
      channels: [heart_rate, hrv, body_temp, spo2, activity_score, respiratory_rate]
      # ... same structure (with its own detection_profile + confounders)

    - device_id: "cgm_patch"
      channels: [body_temp, glucose]
      channel_baselines:
        - {channel: glucose, mean: 95.0, std: 12.0}
      detection_profile:
        sensitivity: 0.72
        specificity: 0.88
        alert_latency_hours: 4
      # no confounders — glucose unaffected by seasickness/alcohol

  class_device_map:                   # multi-device per agent
    - agent_class: "default"
      devices:
        - {device_id: "oura_ring", coverage: 1.0, visibility: "medical_staff"}
    - agent_class: "crew_medical"
      devices:
        - {device_id: "garmin_watch", coverage: 1.0, visibility: "both"}
    - agent_class: "crew_engineering"
      devices:
        - {device_id: "garmin_watch", coverage: 1.0, visibility: "medical_staff"}
    - agent_class: "passenger_elderly"
      devices:
        - {device_id: "oura_ring", coverage: 0.60, visibility: "medical_staff"}

    # Old single-device format still supported (backward compatible):
    # - {agent_class: "default", device_id: "oura_ring"}

  chronic_disease_device_map:         # additive device assignment by disease
    - {disease_id: "type2_diabetes", device_id: "cgm_patch",
       coverage: 0.80, visibility: "both"}

  observation_noise_sigma: 0.5     # ≥ 0
  sync_dropout_prob: 0.02          # [0,1]
  anomaly_z_threshold: 2.0         # > 0 — z-score threshold for per-channel anomaly flag

  anomaly_detection:               # confounder-aware cascade entry scoring
    enabled: true
    anomaly_z_threshold: 2.0
    infection_score_threshold: 1.5 # weighted residual threshold for Tier-0 entry
    fleet_anomaly_floor: 0.15      # downweight channels above this fleet anomaly rate
    fleet_anomaly_downweight: 0.1
    confounder_match_threshold: 0.7
    channel_infection_weights:     # higher = more infection-informative
      heart_rate: 0.3
      hrv: 0.3
      body_temp: 1.0
      spo2: 0.8
      sleep_score: 0.2
      activity_score: 0.4
      respiratory_rate: 0.6
      glucose: 1.0

  fleet_thresholds:
    fleet_fever_rate_amber: 0.03
    fleet_fever_rate_red: 0.08
    fleet_anomaly_rate_amber: 0.05
    fleet_anomaly_rate_red: 0.12
```

Fleet thresholds drive `wearable_fleet_monitor` stoplights (SOP-013/014).
Per-agent fever and `infection_score` drive diagnostic cascade Tier-0 entry
via `data/config/diagnostic_cascade*.json` → `cascade_entry.wearable_alert_fusion`.
Per-agent RED stoplights (`wearable_physiological_monitor`, SOP-012) still use
fever or `anomaly_count >= 2`. Only `medical_staff` and `both` visibility data
enters fleet stoplights; `wearer_only` data influences agent sick-call behavior only.

#### Built-In Devices

| Device | Channels | Strengths |
|--------|----------|-----------|
| `oura_ring` | heart_rate, hrv, body_temp, spo2, sleep_score, respiratory_rate | Sleep quality tracking, low-profile form factor |
| `garmin_watch` | heart_rate, hrv, body_temp, spo2, activity_score, respiratory_rate | Continuous HR, activity tracking |
| `cgm_patch` | body_temp, glucose | Continuous glucose monitoring (Abbott FreeStyle Libre) |

#### Sensor Channels

| Channel | Unit | Default Baseline | Description |
|---------|------|-----------------|-------------|
| `heart_rate` | bpm | 68 ± 4 | Resting heart rate |
| `hrv` | ms | 45 ± 8 | Heart rate variability (RMSSD) |
| `body_temp` | °C | 36.6 ± 0.15 | Core/wrist temperature |
| `spo2` | % | 97.5 ± 0.5 | Blood oxygen saturation |
| `sleep_score` | score | 80 ± 5 | Composite sleep quality (Oura only) |
| `activity_score` | score | 50 ± 10 | Daily activity level (Garmin only) |
| `respiratory_rate` | breaths/min | 15 ± 1.5 | Breathing rate |
| `glucose` | mg/dL | 95 ± 12 | Blood glucose (CGM Patch only) |

#### Coverage Fraction & Visibility Tiers

Each device assignment in `class_device_map` specifies:

| Field | Description |
|-------|-------------|
| `coverage` | Bernoulli fraction [0.0–1.0]; each agent independently sampled at init |
| `visibility` | `medical_staff` (default) — flows to fleet stoplights; `wearer_only` — boosts agent sick-call only; `both` — both |

Agents can receive 0+ devices depending on coverage rolls.  When multiple
devices monitor the same channel, the merged summary prefers anomaly-flagged
readings over higher z-scores to avoid dropping legitimate detections.

#### Confounders

Per-device, per-epoch noise sources that bias specific channels:

| Field | Description |
|-------|-------------|
| `confounder_id` | Identifier (e.g., `seasickness`, `alcohol`, `exercise`) |
| `prevalence` | Bernoulli probability of being active each epoch |
| `affected_channels` | Map of channel → `{bias, noise_mult}` |
| `susceptible_classes` | Agent classes affected (empty = all) |

When active, a confounder adds `bias` to the channel baseline and
multiplies the noise `sigma` by `noise_mult` for that epoch.

#### Detection Profile

Per-device imperfect sensing parameters (all optional, default = perfect):

| Field | Description |
|-------|-------------|
| `sensitivity` | P(detect anomaly \| truly infected) [0–1] |
| `specificity` | P(no false alarm \| not infected) [0–1] |
| `alert_latency_hours` | Suppress alerts if infection < N hours old |
| `fever_sensitivity` | P(detect fever \| truly infected + febrile) |
| `fever_specificity` | P(no false fever \| not infected) |

#### Chronic Disease Device Map

Agents with chronic conditions receive additional devices after class-based
assignment:

```yaml
chronic_disease_device_map:
  - {disease_id: "type2_diabetes", device_id: "cgm_patch",
     coverage: 0.80, visibility: "both"}
```

The `disease_id` matches entries in `chronic_diseases.json`.  Duplicate
devices (already assigned via class map) are skipped.

#### Wearable Device Costs

Per-device procurement and subscription costs are defined in
`resource_costs.json` under `wearable_device_costs`:

| Field | Description |
|-------|-------------|
| `unit_cost_usd` | One-time procurement cost per device |
| `monthly_subscription_usd` | Recurring monthly subscription (0 if none) |
| `replacement_days` | Replacement cycle in days (optional, e.g., 14 for CGM patches) |

#### Noise Model

Each channel has three independent noise parameters:

| Parameter | Description |
|-----------|-------------|
| `sigma` | Gaussian noise standard deviation per reading |
| `drift_rate` | Cumulative sensor drift per epoch |
| `dropout_prob` | Probability of a missing/null reading |

#### Infection Response

Per-pathogen-category deltas are applied to each channel based on the
agent's current EMOD phase.  For example, a Norovirus (enteric_viral)
infection at peak phase adds +10 bpm to heart rate and +1.5°C to
body temperature.

| Phase | Heart Rate Δ | Body Temp Δ | SpO2 Δ | HRV Δ |
|-------|-------------|-------------|--------|-------|
| Early | +3 bpm | +0.3°C | 0 | −3 ms |
| Peak | +10 bpm | +1.5°C | −0.5% | −15 ms |
| Late | +5 bpm | +0.8°C | −0.3% | −8 ms |
| Recovery | +1 bpm | +0.1°C | 0 | −2 ms |

*(Values shown for enteric_viral; respiratory_viral has stronger
SpO2 and respiratory_rate effects.  Glucose response: early +5, peak +15,
late +8, recovery +2 mg/dL.)*

#### Class & Gender Baseline Offsets

Baselines are personalized per agent:

- **Class offsets:** `passenger_elderly` → +4 bpm HR, −1.5% SpO2,
  −10 ms HRV; `crew_engineering` → +10 activity score
- **Gender offsets:** Female → +2 bpm HR, +0.1°C body temp;
  Male → −1 bpm HR
- **Chronic disease offsets:** `type2_diabetes` → +35 mg/dL glucose,
  +4 bpm HR, −8 ms HRV, −0.5% SpO2

#### Adding a New Device

Add an entry to `devices` with a unique `device_id`, its channel list,
noise parameters, infection response profiles, and optionally a
`detection_profile` and `confounders` list.  Then assign it to agent
classes via `class_device_map` (with `coverage` and `visibility`).
No code changes required.

### 3.12 GRUMB Multi-Kingdom Seeding

```yaml
grumb_seeding:
  kingdoms: ["Bacteria", "Archaea", "Fungi", "Virus"]
  pseudocount: 1.0e-6
```

Seeds the four-kingdom environmental microbiome arrays used by the
wastewater sequencing instrument.  The pseudocount prevents log-zero
errors in CLR (Centered Log-Ratio) transformations.

---

## 4. Data Files Reference

### 4.0 Pre-Built Configurations (Edison Science)

A library of ready-to-use configuration files is included in the
repository, contributed by Edison Science.  These provide a range of
vessel platforms, pathogen profiles, microbiome baselines, and costing
models so that users can run meaningful simulations without creating
every configuration from scratch.

#### Available Vessel Platforms (`data/platforms/`)

| Directory | Vessel Type | Personnel | Zones | Key Feature |
|-----------|-------------|-----------|-------|-------------|
| `destroyer_baseline` | Generic baseline destroyer | 20 agents (config) | 6 | Default platform; minimal HVAC topology |
| `fletcher_class_destroyer` | WWII Fletcher-class DD | ~300 crew | 20 | Cramped, poor ventilation, hot-bunking |
| `legend_class_nsc` | USCG Legend-class cutter | ~150 crew | 18 | Modern HVAC with NBC filtration |
| `san_antonio_class_lpd` | San Antonio-class LPD | ~1,160 total | 22 | Extreme density in troop berthing |
| `expedition_cruise_300` | Small expedition cruise | ~450 total | 25 | Intimate scale, 6–8 decks |
| `mega_cruise_5000` | Mega cruise ship | ~7,000 total | 67 | Complex HVAC, 16+ decks, multiple dining venues |

Each directory contains `spatial_layout.json` and `air_flow_paths.json`.
To switch platforms, update the graph paths in `config.yaml`:

```yaml
graph:
  spatial_layout: "data/platforms/mega_cruise_5000/spatial_layout.json"
  air_flow_paths: "data/platforms/mega_cruise_5000/air_flow_paths.json"
```

> **Note:** The default `protocols.json` contains zone-closure SOPs
> (e.g., SOP-007 closing `Galley` and `Mess_Hall`) that reference zones
> in the `destroyer_baseline` platform.  When switching to a different
> platform, update `close_zones` targets in `protocols.json` to match
> the new platform's zone names, or remove zone-closure SOPs.
> Run `python tools/sanity_checker.py --platform-dir data/platforms/<your_platform>`
> to verify referential integrity.

#### Expanded Pathogen Library (`data/pathogens/edison_10pathogen_profiles.json`)

A 10-pathogen profile set with literature-grounded dose-response
parameters, shedding kinetics, and microflora disruption signatures:

| Pathogen | Category | Key Transmission | Dose-Response Source |
|----------|----------|-----------------|---------------------|
| Norovirus GII.4 | enteric_viral | fomite, droplet | Teunis et al. (beta-Poisson) |
| SARS-CoV-2 | respiratory_viral | airborne, droplet | Watanabe et al. (exponential) |
| Influenza A | respiratory_viral | droplet, airborne | Alford 1966 (exponential) |
| Measles | respiratory_viral | hvac_airborne | Riley-Wells airborne model |
| Legionella pneumophila | bacterial_waterborne | hvac_airborne | Armstrong & Haas (exponential) |
| Vibrio cholerae/parahaemolyticus | enteric_bacterial | food, water | Hornick et al. (beta-Poisson) |
| Campylobacter jejuni | enteric_bacterial | food | Black et al. (beta-Poisson) |
| C. difficile | enteric_bacterial | fomite, spore | QMRA estimates |
| Andes hantavirus | respiratory_viral | aerosol, direct_contact | Hamster LD50 proxy |
| Ebola virus | filovirus | direct_contact, fomite | Watanabe et al. (exponential) |

To use this profile set instead of the default 2-pathogen baseline:

```bash
cp data/pathogens/edison_10pathogen_profiles.json data/pathogens/active_profiles.json
python tools/sanity_checker.py
```

See `docs/pathogen_notes.md` for detailed literature justifications.

#### Microbiome Baseline Profiles (`data/microbiome_profiles/`)

Multi-kingdom (Bacteria, Archaea, Fungi, Virus) relative-abundance
profiles for seeding the GRUMB environmental microbiome simulation:

| File | Description |
|------|-------------|
| `coastal_port_profile.json` | Near-shore baseline (61 taxa). Enriched in Vibrio, Enterobacteriaceae, coastal phytoplankton. Based on Tara Oceans, ICOMM, and harbor studies. |
| `open_ocean_profile.json` | Off-shore oligotrophic baseline (52 taxa). Dominated by Prochlorococcus, SAR11/Pelagibacter, marine phages. Based on Tara Oceans, HOT/BATS. |
| `zone_type_modifiers.json` | Ship zone-type modifiers (Dining, Room, Free, Engine Room, Galley, Medical) that skew baselines based on built-environment microbiome literature. |

#### Expanded Resource Costs (`data/config/edison_resource_costs.json`)

An expanded cost model with literature-sourced ROM (rough order of
magnitude) pricing for sequencing platforms, bioaerosol samplers, and
culture-based diagnostics.  Adds material inventory items for
`culture_media_sets`, `air_sniffer_cartridges`, `wastewater_collection_kits`,
`library_prep_kits`, and `sequencing_flow_cells`.

See `docs/pricing_notes.md` for sourcing details.

> **Note:** The expanded cost file uses different per-test-cost keys
> (`surface_swab_culture`, `surface_swab_pcr`, `wastewater_sequencing_panel`,
> `metagenomic_shotgun_sequencing`, `amplicon_16s_sequencing`) than the
> default `resource_costs.json`.  Adopting it may require updating code
> references in the orchestrator and observation engine.

---

### 4.1 Pathogen Profiles (`data/pathogens/active_profiles.json`)

Defines one or more pathogens that run concurrently with independent mass
pools per room.  Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `pathogen_id` | string | Unique machine-readable ID (e.g., `norwalk_gi`) |
| `category` | string | `enteric_viral`, `respiratory_viral`, `bacterial`, `fungal` |
| `transmission_routes` | array | Subset of: `direct_contact`, `fomite`, `droplet`, `hvac_airborne`, `food`, `water`, `water_aerosol`, `bodily_fluids` |
| `shedding_curve_log10` | array | Day-by-day symptomatic shedding (log10 copies), typically 15 entries |
| `dose_response` | object | `{model, alpha, beta}` — Korkin Lab dose-response parameters |
| `recovery_day` | int | Day of infection → Recovered transition |
| `surface_deposition_fraction` | float | Fraction [0,1] of shed mass deposited on surfaces |
| `microflora_disruption` | object | Controls GRUMB dual-signal shedding (kingdom-level CLR shifts) |
| `introduction_epoch` | int | When pathogen enters simulation (0 = start, >0 = mid-cruise) |

**Example — Adding a Third Pathogen:**

```json
{
  "pathogen_id": "legionella_pn",
  "name": "Legionella pneumophila",
  "category": "bacterial",
  "transmission_routes": ["hvac_airborne", "droplet"],
  "shedding_curve_log10": [2.0, 4.0, 6.0, 7.0, 7.5, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 1.0, 1.0, 1.0],
  "dose_response": {"model": "beta_poisson", "alpha": 0.06, "beta": 10.0},
  "recovery_day": 10,
  "surface_deposition_fraction": 0.01,
  "base_susceptibility": 1.0,
  "microflora_disruption": {
    "causes_disruption": true,
    "disruption_type": "respiratory",
    "disruption_magnitude": 0.7,
    "affected_kingdoms": {
      "Bacteria": {"Pseudoalteromonas": 4.0, "Legionella_spp": 8.0}
    }
  },
  "introduction_epoch": 12,
  "initial_infected": 1
}
```

### 4.2 Spatial Layout (`data/platforms/*/spatial_layout.json`)

Defines the room/zone node graph with display coordinates:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Zone name (no spaces — use underscores) |
| `type` | string | `Free`, `Dining`, `Room`, `Medical`, `Engineering` |
| `traffic` | string | `low`, `medium`, `high` — room-touch frequency |
| `volume_m3` | float | Compartment volume (must be > 0) |
| `deck` | string | `upper`, `main`, `lower` — vertical position |
| `display` | object | `{x, y}` — Plotly spatial deck map coordinates |

### 4.3 Airflow Paths (`data/platforms/*/air_flow_paths.json`)

Three edge types connecting the spatial graph:

| Edge Type | Description |
|-----------|-------------|
| `hvac_zones` | Groups of rooms sharing HVAC recirculation (with ACH rate) |
| `cross_zone_links` | Inter-zone links: ladder wells, shafts, ducted connections |
| `adjacency` | Direct physical connections: doors, hatches, passageways |

**Referential Integrity:** Every room referenced MUST exist in
`spatial_layout.json`.  The sanity checker enforces this.

### 4.4 Protocols (`data/config/protocols.json`)

See [Section 5](#5-drafting-custom-standing-operating-procedures) for
detailed SOP authoring guidance.

### 4.5 Resource Costs (`data/config/resource_costs.json`)

Defines four resource dimensions tracked by the cost ledger:

| Category | Starting Value | Description |
|----------|---------------|-------------|
| **Financial (USD)** | $75,000 | Starting balance for spend tracking (not a hard limit) |
| **Labor (person-hours)** | 480 | 20 crew × 24 hours available |
| **Material Inventory** | Per-item | Masks, respirators, test kits, filters, etc. |
| **Operational Impact (OIS)** | 0 (cumulative) | Societal/operational degradation from confinement, galley closures, fleet PPE (tracker only) |

Each material item has `starting_count`, `unit_cost_usd`, and a description.
SOPs reference materials by name — ensure SOP material keys match items
defined in this file.

**Per-test costs** (`per_test_costs`) debit the ledger each epoch for
environmental samples (`air_sniffer_sample`, `surface_swab_pcr`,
`wastewater_sequencing_panel`) and per sick-call clinical tests (`clinical_rdt`,
`clinical_qpcr`, `clinical_microbiology`). Consumed materials appear under
`cost_accounting.materials_consumed`, `by_category`, and OIS fields
(`operational_impact_epoch`, `operational_impact_cumulative`,
`operational_impact_breakdown`) in `simulation_history.json`.

**OIS weights** (`operational_impact_weights`): per-passenger quarantine,
essential-crew quarantine, closed galley zones (matched by zone **type** from
spatial layout, not hardcoded zone names), and fleet-wide PPE. See
[OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md) for Stackelberg
and behavioral policy integration.

### 4.6 Logging Profile (`data/config/logging_profile.json`)

Controls the diagnostic output fidelity.  Change `logging_fidelity`
to one of:

| Tier | Label | Output |
|------|-------|--------|
| `LOW_FIDELITY` | Command/Strategic | Stoplight only: GREEN / AMBER / RED |
| `MID_FIDELITY` | Certified Clinical | DETECTED/NOT DETECTED, Ct values, QC flags |
| `HIGH_FIDELITY` | Raw Synthetic Instrument | Full curves, Dirichlet params, raw reads |

---

## 5. Drafting Custom Standing Operating Procedures

SOPs are the heart of the Reactive Protocol Engine.  Each SOP maps a
diagnostic alert condition to a set of physics/behavior modifications
and a cost footprint.

### 5.1 SOP Structure

```json
{
  "protocol_id": "SOP-008",
  "name": "Your Protocol Name",
  "description": "What this SOP does and why.",
  "trigger": {
    "instrument_class": "continuous_air_sampler",
    "stoplight_level": "AMBER",
    "min_zones_affected": 2
  },
  "modifiers": {
    "hvac_filter_efficiency_override": 0.80
  },
  "costs_per_epoch": {
    "financial_usd": 200.00,
    "materials": {"hvac_filters": 1},
    "labor_person_hours": 2.0
  },
  "activation_costs": {
    "financial_usd": 500.00,
    "materials": {"hvac_filters": 4},
    "labor_person_hours": 6.0
  },
  "category": "intervention"
}
```

### 5.2 Trigger Configuration

The trigger defines **when** the SOP activates:

| Field | Options | Description |
|-------|---------|-------------|
| `instrument_class` | See table below | Which instrument's stoplight to watch |
| `stoplight_level` | `GREEN`, `AMBER`, `RED` | Minimum alert level (AMBER = elevated, RED = critical) |
| `min_zones_affected` | integer ≥ 1 | How many zones must show this level |
| `min_agents_affected` | integer ≥ 1 | For clinical / per-agent wearable triggers |
| `min_modes_affected` | integer ≥ 2 | For `detection_escalation`: concurrent modes at level |

**Instrument classes:**

| Class | Source |
|-------|--------|
| `continuous_air_sampler` | Air sniffer |
| `targeted_surface_swab` | Surface swab |
| `wastewater_sequencing_grid` | Wastewater grid |
| `clinical_rdt`, `clinical_qpcr`, `clinical_microbiology` | Sickbay instruments |
| `long_read_verification_sequencing` | Escalation Nanopore verification (per request id) |
| `wearable_physiological_monitor` | Per-agent wearable RED (fever or `anomaly_count >= 2`) |
| `wearable_fleet_monitor` | Shipwide fever/anomaly rates |
| `detection_escalation` | Integrated syndromic + wearable + env + clinical modes |

### 5.3 Available Modifier Keys

| Modifier | Range | Effect |
|----------|-------|--------|
| `hvac_filter_efficiency_override` | [0.0, 1.0] | Override HVAC filter efficiency |
| `hvac_filter_type_label` | string | Dashboard display label |
| `surface_decontamination_factor` | [0.0, 1.0] | Fraction of surface mass removed/epoch |
| `surface_decay_rate_override` | [0.0, 1.0] | Override natural surface decay |
| `ppe_transmission_reduction` | [0.0, 1.0] | Overall PPE transmission reduction |
| `direct_contact_scalar` | [0.0, 1.0] | Scale Pathway 1 dose (1.0=no change) |
| `droplet_scalar` | [0.0, 1.0] | Scale Pathway 2 dose |
| `hvac_airborne_scalar` | [0.0, 1.0] | Scale Pathway 3 dose |
| `diagnostic_cadence_multiplier` | ≥ 0 | Multiply testing frequency |
| `fomite_scalar` | [0.0, 1.0] | Scale Pathway 4 dose |
| `close_zones` | list of zone IDs | Zones to close (restrict occupancy) |
| `zone_occupancy_cap` | integer ≥ 0 | Max agents in closed zones |
| `confine_all_to_quarters` | boolean | Relocate all agents to home zones (full-ship lockdown) |
| `surface_decontamination_factor` | [0.0, 1.0] | Emergency zone surface mass reduction factor |

### 5.4 Cost Accounting

Each SOP has two cost blocks:

- **`activation_costs`** — Deducted once when the SOP first fires
- **`costs_per_epoch`** — Deducted every epoch the SOP remains active

Material items in the `materials` dict MUST match items defined in
`resource_costs.json`.  If a material is depleted (reaches 0), the
cost ledger flags a `DEPLETED` warning in the executive summary.

### 5.5 Existing SOPs (Destroyer Baseline)

| SOP | Name | Trigger | Modifier |
|-----|------|---------|----------|
| SOP-001 | Enhanced Ventilation | Air sniffer AMBER | MERV-16 filter (80%) |
| SOP-002 | HEPA Lockdown Ventilation | Air sniffer RED | HEPA filter (99.9%) |
| SOP-003 | Surface Decontamination | Surface swab AMBER | 50% surface removal |
| SOP-004 | PPE — Standard | Wastewater AMBER | Surgical masks, 40% reduction |
| SOP-005 | PPE — Full N95 | Wastewater RED | N95 respirators, 80% reduction |
| SOP-006 | Increased Diagnostics | Clinical RDT AMBER | 2× testing frequency |
| SOP-007 | Galley Closure | Clinical micro RED | `close_zones` |
| SOP-008 | Symptomatic Confinement | Clinical RDT RED (≥2) | `confine_symptomatic_to_quarters` |
| SOP-009 | General Confinement | Clinical qPCR RED (≥3) | `confine_all_to_quarters`, `exempt_classes` |
| SOP-010 | VSP-Threshold Isolation | Clinical RDT RED | Confinement + surface decon |
| SOP-011 | Selective Passenger Confinement | Clinical RDT RED (≥2) | Crew `exempt_classes` |
| SOP-012 | Wearable Individual Health Triage | Wearable agent RED (≥1) | `confine_symptomatic_to_quarters` |
| SOP-013 | Wearable Fleet Surveillance Escalation | Wearable fleet AMBER | 1.5× `diagnostic_cadence_multiplier` |
| SOP-014 | Wearable Fleet Outbreak Response | Wearable fleet RED | PPE + contact/droplet scalars |
| SOP-015 | Integrated Detection — Elevated | Detection escalation AMBER (≥2 modes) | 2× diagnostic cadence |
| SOP-016 | Integrated Detection — Critical | Detection escalation RED (≥2 modes) | Confinement + PPE + surface decon |

---

## 6. GIS Spatial Bridge Tool

The GIS spatial bridge converts standardized GIS vector files
(Shapefiles or GeoJSON) into the platform's native JSON layout
specifications.

### 6.1 Basic Usage

```bash
python tools/gis_spatial_bridge.py --input data/shp/my_ship.shp --output data/platforms/my_ship/
```

### 6.2 Full CLI Reference

| Flag | Description |
|------|-------------|
| `--input`, `-i` | **Required.** Path to compartment polygon file (Shapefile or GeoJSON) |
| `--hvac` | Optional separate HVAC duct line layer |
| `--output`, `-o` | Output directory (default: `data/platforms/imported/`) |
| `--platform`, `-p` | Platform name (default: derived from filename) |
| `--col-id` | Column name for room/zone ID |
| `--col-type` | Column name for room type |
| `--col-volume` | Column name for room volume (m³) |
| `--col-ach` | Column name for air changes per hour |
| `--col-deck` | Column name for deck/level |
| `--col-traffic` | Column name for traffic density |

### 6.3 How It Works

1. **Polygon Ingestion:** Reads polygon features (compartments) via geopandas
2. **Centroid Computation:** Computes geometric centroids → dashboard `display.x`, `display.y`
3. **Attribute Mapping:** Maps shapefile columns to zone properties (case-insensitive with fallback candidates)
4. **Line Intersection:** Traces line features (ducts/corridors) to determine topological adjacency. If a line intersects two compartment polygons, a directed graph edge is generated.
5. **HVAC Zone Grouping:** Groups rooms by deck into HVAC zones with per-zone ACH
6. **Output:** Generates `spatial_layout.json` and `air_flow_paths.json`

### 6.4 GeoJSON/Shapefile Column Requirements

The tool uses case-insensitive column matching with fallback candidates:

| Target Property | Primary Column | Fallback Candidates |
|----------------|----------------|---------------------|
| Zone ID | `ROOM_NAME` | `NAME`, `ID`, `ROOM_ID`, `COMPARTMENT` |
| Room Type | `ROOM_TYPE` | `TYPE`, `FUNCTION`, `USE` |
| Volume (m³) | `VOLUME_M3` | `VOLUME`, `VOL_M3`, `VOL` |
| Base ACH | `BASE_ACH` | `ACH`, `AIR_CHANGES` |
| Deck | `DECK` | `LEVEL`, `FLOOR` |
| Traffic | `TRAFFIC` | `DENSITY`, `USAGE` |

### 6.5 Example Workflow

```bash
# 1. Convert GIS data
python tools/gis_spatial_bridge.py \
  --input data/shp/carrier_deck3.geojson \
  --hvac data/shp/carrier_hvac.geojson \
  --output data/platforms/carrier_deck3/ \
  --platform "CVN_Carrier_Deck3"

# 2. Validate the generated configs
python tools/sanity_checker.py

# 3. Run simulation with new platform
# (update config.yaml platform path, then run orchestrator)
python orchestrator.py              # uses num_epochs from config.yaml
python orchestrator.py --epochs 100 # or override via CLI
```

---

## 7. Configuration Sanity Checker

The sanity checker (`tools/sanity_checker.py`) scans all configuration
files — including `config.yaml` when `--from-config` is passed — and
throws explicit errors if the data contains logical or physical
contradictions.

### 7.1 Usage

```bash
# Validate JSON data files only
python tools/sanity_checker.py

# Validate JSON data files AND config.yaml (recommended)
python tools/sanity_checker.py --from-config

# Validate a specific platform directory
python tools/sanity_checker.py --platform-dir data/platforms/mega_cruise_5000

# Validate specific files manually
python tools/sanity_checker.py --config-dir data/config \
                               --platform-dir data/platforms/destroyer_baseline \
                               --pathogen-file data/pathogens/active_profiles.json
```

### 7.2 What It Checks

The checker uses pydantic models and performs four categories of validation:

#### Category 0: config.yaml Validation (`--from-config`)

| Check | Rule |
|-------|------|
| Agent class fractions | Must sum to 1.0; valid role_groups; no duplicate class_ids |
| Gender distribution | Must sum to 1.0; non-negative values |
| Wearable device config | Unique device_ids; channel consistency; noise/dropout bounds; valid class_device_map; detection_profile probabilities in [0,1]; confounder channel refs match device channels; chronic_disease_device_map device refs; coverage in [0,1]; visibility in {medical_staff, wearer_only, both} |
| Modality probabilities | Sensitivity, specificity, compliance rates ∈ [0.0, 1.0] |
| HVAC parameters | `filter_efficiency` ∈ [0,1]; non-negative `natural_decay_rate` |
| EMOD progression | Phase/duration count match; positive durations; sensitivity caps ∈ [0,1] |
| Escalation thresholds | Non-negative values |
| FRED compliance | Probability ∈ [0,1]; noise category probabilities valid |
| Multi-pathogen config | Fraction/multiplier bounds |
| Microflora config | `graywater_zones` cross-referenced against spatial layout |

#### Category 1: Mathematical Bound Violations

| Check | Rule |
|-------|------|
| Probabilities | `eta`, `gamma`, compliance rates ∈ [0.0, 1.0] |
| Filtration efficiencies | `hvac_filter_efficiency_override` ∈ [0.0, 1.0] |
| Transmission scalars | `direct_contact_scalar`, etc. ∈ [0.0, 1.0] |
| Physical quantities | `volume_m3`, `ach`, `flow_rate_m3h` > 0 |
| Financial values | `starting_balance`, `unit_cost_usd` ≥ 0 |
| Recovery/timing | `recovery_day`, `introduction_epoch` ≥ 0 |

#### Category 2: Graph Referential Integrity

| Check | Rule |
|-------|------|
| HVAC zone rooms | Every room in `hvac_zones[].rooms` must exist in `spatial_layout.json` |
| Cross-zone links | `from` and `to` fields must reference valid zones or HVAC zone IDs |
| Adjacency edges | Both endpoints must exist in `spatial_layout.json` |
| Protocol zone closures | Every zone in `close_zones` must exist in `spatial_layout.json` |
| No orphaned edges | No graph edge may reference a zone not in the spatial layout |

#### Category 3: Logical Contradictions

| Check | Severity | Rule |
|-------|----------|------|
| Cost exceeds budget | WARN | `costs_per_epoch.financial_usd` should not exceed `budgets.financial_usd.starting_balance` |
| Labor exceeds capacity | WARN | `labor_person_hours` should not exceed available hours |
| Unknown transmission routes | ERROR | Routes must match schema-allowed set (includes `food`, `water`, etc.) |
| Material inventory mismatch | WARN | SOP material keys should match `resource_costs.json` items |

### 7.3 Output Format

```
✓  VALIDATION PASSED — all configuration files are structurally sound.
```

or:

```
✗  VALIDATION FAILED — 3 errors, 1 warning

  [ERROR] spatial_layout.json → zone "Engine_Room": volume_m3 = -150 (must be positive)
  [ERROR] air_flow_paths.json → cross_zone_link "HVAC_Z1→Ghost_Zone": destination does not exist
  [ERROR] active_profiles.json → norwalk_gi: surface_deposition_fraction = 1.5 (must be ≤ 1.0)
  [WARN]  protocols.json → SOP-002: costs_per_epoch.financial_usd ($350) approaches starting budget
```

Exit code: `0` on pass, `1` on failure.

---

## 8. The Artificial Lab Notebook — Fidelity Tiers

The lab notebook (`telemetry_buffer/artificial_lab_notebook.json`) is a
machine-readable diagnostic report structured for CDC/fleet
biosurveillance portal ingestion.

### 8.1 Tier Comparison

| Aspect | `LOW_FIDELITY` | `MID_FIDELITY` | `HIGH_FIDELITY` |
|--------|---------------|----------------|-----------------|
| **Label** | Command/Strategic | Certified Clinical | Raw Synthetic Instrument |
| **Use Case** | Fleet commander overview | Lab director / CAP audit | Bioinformatician / researcher |
| **Stoplight** | GREEN / AMBER / RED | — | — |
| **Binary Result** | — | DETECTED / NOT DETECTED | DETECTED / NOT DETECTED |
| **Ct Values** | — | Formal numeric Ct | Formal numeric Ct |
| **QC Flags** | — | QC_PASS / QC_FAILURE | QC_PASS / QC_FAILURE |
| **Amplification Curves** | — | — | 40-cycle fluorescence arrays |
| **Background Fluorescence** | — | — | Raw baseline noise values |
| **Kingdom Read Counts** | — | — | Dirichlet-multinomial reads per kingdom |
| **CLR Anomaly Deltas** | — | — | Per-kingdom CLR-space shift magnitudes |
| **Dirichlet Parameters** | — | — | Concentration parameter for sampling |
| **Culture Plate Results** | — | — | Colony counts, gram stain, flora shift |
| **Control Line Intensities** | — | — | RDT control/test line measurements |
| **Host Microflora Variance** | — | Per-agent disruption level | Full kingdom-taxon breakdown |

### 8.2 LOW_FIDELITY — Stoplight Indicators

Each record contains only a `stoplight` field:

```json
{
  "sample_id": "CLN-000-BRIDGE-AIR_-565a0df6",
  "timestamp_epoch": 0,
  "collection_zone": "Bridge",
  "assay_type": "aerosol_pcr",
  "fidelity_tier": "LOW_FIDELITY",
  "stoplight": "GREEN",
  "inferred_anomaly_score": 0.0
}
```

**Stoplight Classification:**
- **GREEN** — Clear, no anomaly detected
- **AMBER** — Elevated anomaly, caution warranted
- **RED** — Critical hazard, isolate immediately

**Threshold Rules:**
- Air/Surface PCR: Ct ≤ 30 → RED, Ct ≤ 35 → AMBER, else GREEN
- Wastewater: anomaly_score ≥ 0.7 → RED, ≥ 0.3 → AMBER
- Clinical RDT: positive → RED
- Microflora: disruption ≥ 0.6 → RED, ≥ 0.3 → AMBER

### 8.3 MID_FIDELITY — Certified Clinical Reports

CAP-style certified laboratory reports with formal numeric metrics:

```json
{
  "sample_id": "CLN-000-BRIDGE-AIR_-565a0df6",
  "timestamp_epoch": 0,
  "collection_zone": "Bridge",
  "assay_type": "aerosol_pcr",
  "fidelity_tier": "MID_FIDELITY",
  "binary_result": "NOT DETECTED",
  "ct_value": 43.69,
  "captured_mass": 0.0012,
  "concentration_per_m3": 0.000001,
  "qc_status": "QC_PASS",
  "cross_contamination_carryover": 0.000001,
  "inferred_anomaly_score": 0.0
}
```

### 8.4 HIGH_FIDELITY — Raw Synthetic Instrument Telemetry

Full machine telemetry including raw cycle-by-cycle data:

```json
{
  "sample_id": "CLN-000-GALLEY-AIR_-d851b63b",
  "timestamp_epoch": 0,
  "collection_zone": "Galley",
  "assay_type": "aerosol_pcr",
  "fidelity_tier": "HIGH_FIDELITY",
  "binary_result": "DETECTED",
  "ct_value": 24.5,
  "captured_mass": 1250.4,
  "raw_amplification_curve": [142.3, 139.8, ..., 3987.2, 4012.1],
  "background_fluorescence": 148.7,
  "qc_status": "QC_PASS",
  "cross_contamination_carryover": 0.125
}
```

For **wastewater sequencing** at HIGH_FIDELITY:

```json
{
  "assay_type": "metagenomic_sequencing",
  "fidelity_tier": "HIGH_FIDELITY",
  "kingdom_reads": {"Bacteria": 33597, "Archaea": 6096, "Fungi": 4602, "Virus": 5705},
  "kingdom_clr_deltas": {"Bacteria": 0.019, "Archaea": -0.003, "Fungi": 0.008, "Virus": -0.012},
  "read_depth": 50000,
  "dirichlet_concentration": 100.0,
  "raw_read_counts_prenorm": {"Bacteria": 33597, "Archaea": 6096, "Fungi": 4602, "Virus": 5705}
}
```

### 8.5 Selecting Fidelity

Edit `data/config/logging_profile.json`:

```json
{
  "logging_fidelity": "MID_FIDELITY"
}
```

All six instruments output at the selected fidelity.  You do not need
to change any other configuration — the notebook serializer
automatically adapts record structure per tier.

### 8.6 Top-Level Notebook Blocks

Beyond the `records` array, the notebook includes:

| Block | Description |
|-------|-------------|
| `FINANCIAL_AUDIT` | Itemized expenditure report: surveillance vs. intervention costs, material consumption, depleted supply warnings |
| `PROTOCOL_SUMMARY` | Which SOPs were triggered, first activation epoch, total activation/deactivation counts |
| `run_metadata` | Total epochs, platform, fidelity tier, active pathogens |
| `fidelity_tier_definitions` | Human-readable descriptions of each tier |

---

## 9. The USS Crusher LCARS Command Deck

TNG LCARS-styled Streamlit UI (`dashboard/` package; entry: `streamlit run dashboard.py`).
Run `python3 orchestrator.py`, then `streamlit run dashboard.py` or `./run_dashboard.sh`.

**Ship class:** The dashboard resolves the active platform from telemetry zone
fingerprints, `crusher_labs/config.yaml`, or the sidebar selector. Precomputed deck
assets live under `data/platforms/<platform_id>/`:

```bash
python3 scripts/precompute_deck_assets.py   # all catalog platforms
```

This writes `deck_graphics.geojson`, `deck_hull.png`, and `deck_manifest.json`
(visual-only; simulation JSON unchanged). Regenerate after editing
`spatial_layout.json` zones. GIS import: `python3 tools/gis_spatial_bridge.py
--input data/shp/....geojson --output data/platforms/<id>/ --emit-deck-graphics`.

**USS Crusher — Main Bridge Display** with Condition Green / Yellow / Red Alert banners.

### Station 1: Bridge Status Display

Infection metrics, **confined to quarters** / **isolation ward** / refusers,
infection counter charts, Crew Manifest by Division, wearable monitoring,
transmission vector analysis, epidemic curves, cost ledger.

### Station 2: Tactical Sensor Grid

Class-accurate deck plan (pydeck or Plotly): hull silhouette, compartment footprints,
deck filter, epoch slider; aerosol / fomite / symptomatic overlays.

### Station 5: Fleet Operations

Presidio `output_root` (e.g. `presidio/data/experiences/smoke_runs`): cruise comparison,
per-cruise hull thumbnail, and tactical grid for each cruise.

### Station 3: Sickbay Diagnostic Console

Lab notebook LOW / MID / HIGH fidelity.

### Station 4: Standing Orders & Threat Profiles

Pathogen dossiers; SOP cards with **Exempt Divisions** when `exempt_classes` is set.

---

## 10. Simulation Output Reference

### 10.1 Executive Summary Box

At the end of every run, the orchestrator prints a formatted ASCII
executive summary with three sections:

1. **Epidemiological Metrics** — Total crew, infected, co-infections,
   escalation timeline, person-hours remaining
2. **Financial & Resource Audit** — Total spent (surveillance vs.
   intervention), depleted supply warnings
3. **SOP Activation History** — Which SOPs fired and at what epoch

### 10.2 Live Progress Bar

During execution, a single-line progress bar shows:
```
██████████████████████████████ 100.0%  Epoch 24/24  ■ CONFIRMED   SOPs:1  Budget:$26,145
```

### 10.3 Telemetry Highlights

`summary.quarantined`, `summary.isolated`, `summary.quarantine_refusers`,
`infection_counters`, `wearable_monitoring`, `contact_tracing.transmission_events`.

**Per-agent telemetry** uses `infection_state`, `symptom_presentation`, and
`compliance_status` (legacy `symptom_status` is deprecated).

**Cost accounting** per epoch includes `materials_consumed`,
`by_category.surveillance` / `by_category.intervention`, and remaining
balance fields. Per-test debits are tagged `test:<type>` in the ledger.

### 10.4 Output Files

| File | Location | Description |
|------|----------|-------------|
| `simulation_history.json` | `telemetry_buffer/` | Per-epoch state (gitignored) |
| `artificial_lab_notebook.json` | `telemetry_buffer/` | Instrument records (gitignored) |

JSON Schemas in `schemas/`. Regenerate before opening the dashboard.

---

## 11. Contributors & Sibling Repositories

Crusher-to-the-Bridge is a bridging package that connects work from
multiple research groups and open-source projects:

### 11.1 Core Platform

| Role | Contributor |
|------|------------|
| **Platform Architect** | Benjamin Kirkup |
| **Integration & Development** | Devin (Cognition AI) |

### 11.2 Infection Dynamics Engine

**Repository:** [`infection-dynamics`](https://github.com/KorkinLab/infection-dynamics)

**Citation:** Srinivasan S, King J, Collins JM, Colubri A, Korkin D.
"Real-time spatiotemporal tracking of infectious outbreaks in confined
environments with a host–pathogen agent-based system."
*Proceedings of the National Academy of Sciences.* 2026 Jan 27;123(4):e2422574123.

**Organization:** Korkin Lab, Worcester Polytechnic Institute (WPI)

**Role in Platform:** Agent-based Norwalk/SARS-CoV-2 outbreak simulation.
Provides the dose-response model (`P(inf) = 1 − (1 + dose/β)^{−α}`),
avgR contact arrays from `Person.java`, and SIR state machine transitions.

### 11.3 py-contam — Indoor Air Quality Modeling

**Repository:** [`py-contam`](https://github.com/vonw/py-contam)

**Maintainer:** Von P. Walden, Washington State University

**Role in Platform:** CONTAM I/O library for indoor air quality modeling.
Provides the multi-zone mass-balance equation used by `py_contam_bridge.py`
for inter-zone aerosol transport through HVAC ductwork.

### 11.4 GRUMB — Genome-Resolved Urban Microbiome Biosurveillance

**Repository:** [`GRUMB`](https://github.com/bckirkup/GRUMB)

**Organization:** Kirkup Lab

**Role in Platform:** Genome-resolved metagenomics pipeline providing the
mathematical framework for 4-kingdom CLR-space anomaly detection,
Dirichlet-multinomial sampling, and contamination risk indexing used by
the wastewater sequencing instrument.

### 11.5 EMOD-Generic — Epidemiological MODeling

**Repository:** [`EMOD-Generic`](https://github.com/InstituteforDiseaseModeling/EMOD)

**Organization:** Institute for Disease Modeling (IDM / Gates Foundation)

**Role in Platform:** Stochastic agent-based modeling framework for
disease simulation.  Provides reference implementations of SIR/SEIR
compartmental transitions and Euler-multinomial stochastic engines.

### 11.6 FRED — Framework for Reconstructing Epidemiological Dynamics

**Repository:** [`FRED`](https://github.com/PublicHealthDynamicsLab/FRED)

**Organizations:**
- University of Pittsburgh Public Health Dynamics Laboratory (PHDL)
- Pittsburgh Supercomputing Center (PSC)
- Carnegie Mellon University School of Computer Science
- Commercial version: [Epistemix](https://www.epistemix.com)

**Role in Platform:** Agent scheduling framework providing FRED-style
daily activity schedules, quarantine compliance modeling, and spatial
movement patterns used by the orchestrator's agent routing logic.

---

## Appendix A: Test Suite

```bash
python tools/sanity_checker.py --from-config
pytest tests/ -v --tb=short
```

The suite includes **~574 tests** across data contracts, sanity checker,
orchestrator/quarantine logic, infection counters, orthogonal agent axes,
wearable/detection-escalation protocol engine, enhanced wearable model
(multi-device, confounders, detection profiles, visibility, chronic disease
assignments), sequencing config wiring, long-read Nanopore verification,
instrument turnaround (TAT), per-test cost accounting, **operational impact
(OIS)**, **action applier**, **behavioral syndromic**, transmission pathways
(food/environmental), dashboard helpers, law compliance, telemetry seams, and
**Picard / Presidio / Stackelberg** framework tests. CI
(`.github/workflows/ci.yml`) runs sanity checks, full pytest (~574 tests),
Picard/Presidio import hygiene, Presidio smoke, long-read/TAT targeted tests,
orchestrator import hygiene, dashboard import (including LCARS theme),
24-epoch orchestrator run, and OIS telemetry verification. Framework-focused checks,
enterprise platform tests, and Stackelberg + platform JSON schema validation run in
`.github/workflows/picard-presidio.yml`.
See `AGENTS.md` for cloud agent commands.

| Module | Focus |
|--------|-------|
| `test_enterprise_platforms.py` | Enterprise platform HVAC referential integrity |
| `test_agent_axes.py` | Orthogonal infection / presentation / compliance axes |
| `test_protocol_engine.py` | Wearable and detection-escalation stoplights |
| `test_sequencing_config.py` | `config.yaml` read_depth for WW grid and modalities |
| `test_cost_accounting.py` | Per-test debits and materials in telemetry |
| `test_operational_impact.py` | OIS weight computation and galley-type matching |
| `test_action_applier.py` | `activate_sop`, verification queue, behavioral overrides |
| `test_behavioral_syndromic.py` | `hide_symptoms`, belief-scaled sick-call |
| `test_infection_counters.py` | Attack-rate counters, thresholds, `exempt_classes` |
| `test_transmission_pathways.py` | Food/environmental pool initialization |
| `test_dashboard.py` | LCARS dashboard imports, pathway aggregation |
| `test_orchestrator.py` | Epoch loop, quarantine confinement, SOP modifiers |
| `test_picard_framework.py` | PicardRunSpec, ShipSimulation, golden reproducibility |
| `test_decision_engine.py` | ObservationModel, DecisionRound, ExperienceStore |
| `test_presidio_runner.py` | Fleet smoke, experience store |
| `test_stackelberg.py` | Diffusion, contact graph, utility export/import |
| `test_golden_orchestrator.py` | 24-epoch reproducibility via Picard |

---

## Appendix B: JSON Schema Validation

All data contracts have formal JSON Schema (draft 2020-12) definitions
in `schemas/`:

```bash
pip install check-jsonschema

# Validate all config files
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/destroyer_baseline/spatial_layout.json
check-jsonschema --schemafile schemas/air_flow_paths.schema.json data/platforms/destroyer_baseline/air_flow_paths.json
check-jsonschema --schemafile schemas/protocols.schema.json data/config/protocols.json
check-jsonschema --schemafile schemas/resource_costs.schema.json data/config/resource_costs.json
check-jsonschema --schemafile schemas/logging_profile.schema.json data/config/logging_profile.json

# Validate simulation output
check-jsonschema --schemafile schemas/simulation_history.schema.json telemetry_buffer/simulation_history.json
check-jsonschema --schemafile schemas/lab_notebook.schema.json telemetry_buffer/artificial_lab_notebook.json
```

### Edison-Specific Upstream Schemas

For upstream tool integration (Edison Science), use the richly annotated
Edison schemas with detailed field descriptions:

| Schema | Purpose |
|--------|---------|
| `pathogen_profiles.schema.json` | 4-way path weights, shedding curves, microflora disruption |
| `protocols.schema.json` | Stoplight → modifier mapping, cost deduction rules |
| `spatial_layout.schema.json` | Node graph, volumes, room-touch coefficients |
