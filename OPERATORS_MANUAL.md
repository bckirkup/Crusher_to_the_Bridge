# Crusher-to-the-Bridge — Operator's Manual

**Version:** 1.0  
**Platform:** Biodefense Digital Twin for Maritime Outbreak Simulation  
**License:** MIT

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Configuration Files Reference](#3-configuration-files-reference)
4. [Drafting Custom Standing Operating Procedures](#4-drafting-custom-standing-operating-procedures)
5. [GIS Spatial Bridge Tool](#5-gis-spatial-bridge-tool)
6. [Configuration Sanity Checker](#6-configuration-sanity-checker)
7. [The Artificial Lab Notebook — Fidelity Tiers](#7-the-artificial-lab-notebook--fidelity-tiers)
8. [The Streamlit Tactical Command Deck](#8-the-streamlit-tactical-command-deck)
9. [Simulation Output Reference](#9-simulation-output-reference)
10. [Contributors & Sibling Repositories](#10-contributors--sibling-repositories)

---

## 1. Quick Start

### Prerequisites

```bash
pip install pyyaml numpy streamlit plotly pandas pydantic geopandas networkx
```

### Run a Simulation

```bash
# Step 1: Validate configuration files
python tools/sanity_checker.py

# Step 2: Execute the 24-epoch simulation
python orchestrator.py

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
┌─────────────────────────────────────────────────────────┐
│                    orchestrator.py                       │
│         Main simulation loop (for epoch in epochs)      │
└───────────┬─────────────┬─────────────┬────────────────┘
            │             │             │
            ▼             ▼             ▼
  ┌──────────────┐ ┌────────────┐ ┌────────────────┐
  │ Korkin Lab   │ │ 4-Pathway  │ │ py-contam      │
  │ ABM Bridge   │ │ Transmis.  │ │ HVAC Transport │
  │              │ │ Core       │ │                │
  │ Agent states │ │ Direct     │ │ Mass-balance   │
  │ SIR model    │ │ Droplet    │ │ equation       │
  │ Dose-response│ │ HVAC Air   │ │ Filter η       │
  │              │ │ Fomite     │ │                │
  └──────────────┘ └────────────┘ └────────────────┘
            │             │             │
            └─────────────┼─────────────┘
                          ▼
  ┌──────────────┐ ┌────────────┐ ┌────────────────┐
  │ Observation  │ │ Protocol   │ │ Cost Ledger    │
  │ Engine       │ │ Engine     │ │                │
  │ 6 instruments│ │ Stoplight  │ │ $USD budget    │
  │ + QC         │ │ → SOP      │ │ Materials      │
  │              │ │ triggers   │ │ Labor hours    │
  └──────────────┘ └────────────┘ └────────────────┘
            │                           │
            ▼                           ▼
  ┌─────────────────────────────────────────────────┐
  │            Artificial Lab Notebook               │
  │  HIGH / MID / LOW fidelity output tiers          │
  └─────────────────────────────────────────────────┘
```

### The Feedback Loop

The simulation runs a closed-loop control cycle:

1. **Instruments** sample environmental and patient data each epoch
2. **Observation Engine** classifies results into LOW_FIDELITY stoplights (GREEN/AMBER/RED)
3. **Protocol Engine** evaluates stoplight conditions against SOP trigger rules
4. **Active SOPs** inject physics modifiers (HVAC efficiency, PPE scalars, zone closures)
5. **Transmission Core** reads modified scalars on the next epoch
6. **Cost Ledger** debits financial/material/labor costs for each active SOP

This loop is **fully autonomous** — SOPs activate and deactivate based
on diagnostic conditions.  There are no hardcoded epoch schedules.

---

## 3. Configuration Files Reference

### 3.1 Pathogen Profiles (`data/pathogens/active_profiles.json`)

Defines one or more pathogens that run concurrently with independent mass
pools per room.  Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `pathogen_id` | string | Unique machine-readable ID (e.g., `norwalk_gi`) |
| `category` | string | `enteric_viral`, `respiratory_viral`, `bacterial`, `fungal` |
| `transmission_routes` | array | Subset of: `direct_contact`, `fomite`, `droplet`, `hvac_airborne` |
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

### 3.2 Spatial Layout (`data/platforms/*/spatial_layout.json`)

Defines the room/zone node graph with display coordinates:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Zone name (no spaces — use underscores) |
| `type` | string | `Free`, `Dining`, `Room`, `Medical`, `Engineering` |
| `traffic` | string | `low`, `medium`, `high` — room-touch frequency |
| `volume_m3` | float | Compartment volume (must be > 0) |
| `deck` | string | `upper`, `main`, `lower` — vertical position |
| `display` | object | `{x, y}` — Plotly spatial deck map coordinates |

### 3.3 Airflow Paths (`data/platforms/*/air_flow_paths.json`)

Three edge types connecting the spatial graph:

| Edge Type | Description |
|-----------|-------------|
| `hvac_zones` | Groups of rooms sharing HVAC recirculation (with ACH rate) |
| `cross_zone_links` | Inter-zone links: ladder wells, shafts, ducted connections |
| `adjacency` | Direct physical connections: doors, hatches, passageways |

**Referential Integrity:** Every room referenced MUST exist in
`spatial_layout.json`.  The sanity checker enforces this.

### 3.4 Protocols (`data/config/protocols.json`)

See [Section 4](#4-drafting-custom-standing-operating-procedures) for
detailed SOP authoring guidance.

### 3.5 Resource Costs (`data/config/resource_costs.json`)

Defines three resource categories tracked by the cost ledger:

| Category | Starting Value | Description |
|----------|---------------|-------------|
| **Financial (USD)** | $50,000 | Total budget for surveillance + intervention |
| **Labor (person-hours)** | 480 | 20 crew × 24 hours available |
| **Material Inventory** | Per-item | Masks, respirators, test kits, filters, etc. |

Each material item has `starting_count`, `unit_cost_usd`, and a description.
SOPs reference materials by name — ensure SOP material keys match items
defined in this file.

### 3.6 Logging Profile (`data/config/logging_profile.json`)

Controls the diagnostic output fidelity.  Change `logging_fidelity`
to one of:

| Tier | Label | Output |
|------|-------|--------|
| `LOW_FIDELITY` | Command/Strategic | Stoplight only: GREEN / AMBER / RED |
| `MID_FIDELITY` | Certified Clinical | DETECTED/NOT DETECTED, Ct values, QC flags |
| `HIGH_FIDELITY` | Raw Synthetic Instrument | Full curves, Dirichlet params, raw reads |

---

## 4. Drafting Custom Standing Operating Procedures

SOPs are the heart of the Reactive Protocol Engine.  Each SOP maps a
diagnostic alert condition to a set of physics/behavior modifications
and a cost footprint.

### 4.1 SOP Structure

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

### 4.2 Trigger Configuration

The trigger defines **when** the SOP activates:

| Field | Options | Description |
|-------|---------|-------------|
| `instrument_class` | `continuous_air_sampler`, `targeted_surface_swab`, `wastewater_sequencing_grid`, `clinical_rdt`, `clinical_qpcr`, `clinical_microbiology` | Which instrument's stoplight to watch |
| `stoplight_level` | `GREEN`, `AMBER`, `RED` | Minimum alert level (AMBER = elevated, RED = critical) |
| `min_zones_affected` | integer ≥ 1 | How many zones must show this level |
| `min_agents_affected` | integer ≥ 1 | For clinical instruments: how many patients |

### 4.3 Available Modifier Keys

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
| `close_zones` | list of zone IDs | Zones to close (restrict occupancy) |
| `zone_occupancy_cap` | integer ≥ 0 | Max agents in closed zones |

### 4.4 Cost Accounting

Each SOP has two cost blocks:

- **`activation_costs`** — Deducted once when the SOP first fires
- **`costs_per_epoch`** — Deducted every epoch the SOP remains active

Material items in the `materials` dict MUST match items defined in
`resource_costs.json`.  If a material is depleted (reaches 0), the
cost ledger flags a `DEPLETED` warning in the executive summary.

### 4.5 Existing SOPs (Destroyer Baseline)

| SOP | Name | Trigger | Modifier |
|-----|------|---------|----------|
| SOP-001 | Enhanced Ventilation | Air sniffer AMBER | MERV-16 filter (80%) |
| SOP-002 | HEPA Lockdown Ventilation | Air sniffer RED | HEPA filter (99.9%) |
| SOP-003 | Surface Decontamination | Surface swab AMBER | 50% surface removal |
| SOP-004 | PPE — Standard | Wastewater AMBER | Surgical masks, 40% reduction |
| SOP-005 | PPE — Full N95 | Wastewater RED | N95 respirators, 80% reduction |
| SOP-006 | Increased Diagnostics | Clinical RDT AMBER | 2× testing frequency |
| SOP-007 | Galley Closure | Clinical micro RED | Close Galley + Mess_Hall |

---

## 5. GIS Spatial Bridge Tool

The GIS spatial bridge converts standardized GIS vector files
(Shapefiles or GeoJSON) into the platform's native JSON layout
specifications.

### 5.1 Basic Usage

```bash
python tools/gis_spatial_bridge.py --input data/shp/my_ship.shp --output data/platforms/my_ship/
```

### 5.2 Full CLI Reference

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

### 5.3 How It Works

1. **Polygon Ingestion:** Reads polygon features (compartments) via geopandas
2. **Centroid Computation:** Computes geometric centroids → dashboard `display.x`, `display.y`
3. **Attribute Mapping:** Maps shapefile columns to zone properties (case-insensitive with fallback candidates)
4. **Line Intersection:** Traces line features (ducts/corridors) to determine topological adjacency. If a line intersects two compartment polygons, a directed graph edge is generated.
5. **HVAC Zone Grouping:** Groups rooms by deck into HVAC zones with per-zone ACH
6. **Output:** Generates `spatial_layout.json` and `air_flow_paths.json`

### 5.4 GeoJSON/Shapefile Column Requirements

The tool uses case-insensitive column matching with fallback candidates:

| Target Property | Primary Column | Fallback Candidates |
|----------------|----------------|---------------------|
| Zone ID | `ROOM_NAME` | `NAME`, `ID`, `ROOM_ID`, `COMPARTMENT` |
| Room Type | `ROOM_TYPE` | `TYPE`, `FUNCTION`, `USE` |
| Volume (m³) | `VOLUME_M3` | `VOLUME`, `VOL_M3`, `VOL` |
| Base ACH | `BASE_ACH` | `ACH`, `AIR_CHANGES` |
| Deck | `DECK` | `LEVEL`, `FLOOR` |
| Traffic | `TRAFFIC` | `DENSITY`, `USAGE` |

### 5.5 Example Workflow

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
python orchestrator.py
```

---

## 6. Configuration Sanity Checker

The sanity checker scans all configuration files and throws explicit
errors if the data contains logical or physical contradictions.

### 6.1 Usage

```bash
python tools/sanity_checker.py
```

### 6.2 What It Checks

The checker uses pydantic models and performs three categories of validation:

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
| Unknown transmission routes | ERROR | Only `direct_contact`, `fomite`, `droplet`, `hvac_airborne` allowed |
| Material inventory mismatch | WARN | SOP material keys should match `resource_costs.json` items |

### 6.3 Output Format

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

## 7. The Artificial Lab Notebook — Fidelity Tiers

The lab notebook (`telemetry_buffer/artificial_lab_notebook.json`) is a
machine-readable diagnostic report structured for CDC/fleet
biosurveillance portal ingestion.

### 7.1 Tier Comparison

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

### 7.2 LOW_FIDELITY — Stoplight Indicators

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

### 7.3 MID_FIDELITY — Certified Clinical Reports

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

### 7.4 HIGH_FIDELITY — Raw Synthetic Instrument Telemetry

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

### 7.5 Selecting Fidelity

Edit `data/config/logging_profile.json`:

```json
{
  "logging_fidelity": "MID_FIDELITY"
}
```

All six instruments output at the selected fidelity.  You do not need
to change any other configuration — the notebook serializer
automatically adapts record structure per tier.

### 7.6 Top-Level Notebook Blocks

Beyond the `records` array, the notebook includes:

| Block | Description |
|-------|-------------|
| `FINANCIAL_AUDIT` | Itemized expenditure report: surveillance vs. intervention costs, material consumption, depleted supply warnings |
| `PROTOCOL_SUMMARY` | Which SOPs were triggered, first activation epoch, total activation/deactivation counts |
| `run_metadata` | Total epochs, platform, fidelity tier, active pathogens |
| `fidelity_tier_definitions` | Human-readable descriptions of each tier |

---

## 8. The Streamlit Tactical Command Deck

The dashboard (`dashboard.py`) provides four analytical tabs:

### Tab 1: Mission Summary & Ledger

- Epidemiological metrics: total infected, co-infections, person-hours remaining
- Epidemic curve (infections over time)
- Cumulative cost chart (surveillance vs. intervention)
- Material supply table with depletion warnings
- SOP activation history log

### Tab 2: Spatial Outbreak Deck

- Plotly room node map with epoch slider (scrub through all epochs)
- Color toggle between three visualization modes:
  - **Aerosol** — Airborne pathogen mass per zone
  - **Fomite** — Surface contamination per zone
  - **Symptomatic** — Count of symptomatic agents per zone
- Stoplight status row for each zone

### Tab 3: Crusher Labs Portal

- Lab notebook explorer with fidelity toggle (LOW/MID/HIGH)
- LOW: Stoplight grid
- MID: Clinical data table
- HIGH:
  - Interactive qPCR 40-cycle amplification curves (line charts)
  - GRUMB multi-kingdom relative abundance (stacked bar charts)
  - CLR anomaly delta visualization

### Tab 4: Protocol & Configuration Profile

- Active pathogen profiles with transmission routes and microflora disruption settings
- Standing protocols with trigger conditions and cost footprints

---

## 9. Simulation Output Reference

### 9.1 Executive Summary Box

At the end of every run, the orchestrator prints a formatted ASCII
executive summary with three sections:

1. **Epidemiological Metrics** — Total crew, infected, co-infections,
   escalation timeline, person-hours remaining
2. **Financial & Resource Audit** — Total spent (surveillance vs.
   intervention), depleted supply warnings
3. **SOP Activation History** — Which SOPs fired and at what epoch

### 9.2 Live Progress Bar

During execution, a single-line progress bar shows:
```
██████████████████████████████ 100.0%  Epoch 24/24  ■ CONFIRMED   SOPs:1  Budget:$26,145
```

### 9.3 Output Files

| File | Location | Description |
|------|----------|-------------|
| `simulation_history.json` | `telemetry_buffer/` | Per-epoch full state (24 records) |
| `artificial_lab_notebook.json` | `telemetry_buffer/` | Instrument records (595+ per run at HIGH_FIDELITY) |

Both files have formal JSON Schema definitions in `schemas/`.

---

## 10. Contributors & Sibling Repositories

Crusher-to-the-Bridge is a bridging package that connects work from
multiple research groups and open-source projects:

### 10.1 Core Platform

| Role | Contributor |
|------|------------|
| **Platform Architect** | Benjamin Kirkup |
| **Integration & Development** | Devin (Cognition AI) |

### 10.2 Infection Dynamics Engine

**Repository:** [`infection-dynamics`](https://github.com/KorkinLab/infection-dynamics)

**Citation:** Srinivasan S, King J, Collins JM, Colubri A, Korkin D.
"Real-time spatiotemporal tracking of infectious outbreaks in confined
environments with a host–pathogen agent-based system."
*Proceedings of the National Academy of Sciences.* 2026 Jan 27;123(4):e2422574123.

**Organization:** Korkin Lab, Worcester Polytechnic Institute (WPI)

**Role in Platform:** Agent-based Norwalk/SARS-CoV-2 outbreak simulation.
Provides the dose-response model (`P(inf) = 1 − (1 + dose/β)^{−α}`),
avgR contact arrays from `Person.java`, and SIR state machine transitions.

### 10.3 py-contam — Indoor Air Quality Modeling

**Repository:** [`py-contam`](https://github.com/vonw/py-contam)

**Maintainer:** Von P. Walden, Washington State University

**Role in Platform:** CONTAM I/O library for indoor air quality modeling.
Provides the multi-zone mass-balance equation used by `py_contam_bridge.py`
for inter-zone aerosol transport through HVAC ductwork.

### 10.4 GRUMB — Genome-Resolved Urban Microbiome Biosurveillance

**Repository:** [`GRUMB`](https://github.com/bckirkup/GRUMB)

**Organization:** Kirkup Lab

**Role in Platform:** Genome-resolved metagenomics pipeline providing the
mathematical framework for 4-kingdom CLR-space anomaly detection,
Dirichlet-multinomial sampling, and contamination risk indexing used by
the wastewater sequencing instrument.

### 10.5 EMOD-Generic — Epidemiological MODeling

**Repository:** [`EMOD-Generic`](https://github.com/InstituteforDiseaseModeling/EMOD)

**Organization:** Institute for Disease Modeling (IDM / Gates Foundation)

**Role in Platform:** Stochastic agent-based modeling framework for
disease simulation.  Provides reference implementations of SIR/SEIR
compartmental transitions and Euler-multinomial stochastic engines.

### 10.6 FRED — Framework for Reconstructing Epidemiological Dynamics

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

## Appendix A: JSON Schema Validation

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
| `pathogen_profile_schema.json` | 4-way path weights, shedding curves, microflora disruption |
| `protocol_playbook_schema.json` | Stoplight → modifier mapping, cost deduction rules |
| `spatial_layout_schema.json` | Node graph, volumes, room-touch coefficients |
