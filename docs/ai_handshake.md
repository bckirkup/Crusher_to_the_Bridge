# AI Handshake & Context Manifest

**Purpose:** This document provides the complete architectural context that
external LLMs (Edison Science, Cursor, Copilot, ChatGPT, Claude, etc.) need
to safely generate code, configuration, and analysis for the
Crusher-to-the-Bridge biodefense digital twin platform.

---

## 1. System Identity

| Property | Value |
|----------|-------|
| **Platform** | Crusher-to-the-Bridge |
| **Domain** | Maritime biodefense — multi-pathogen outbreak simulation |
| **Architecture** | Decoupled bridging package connecting 5 independent simulation domains |
| **Language** | Python 3.11+ (orchestrator, instruments, transport) + Java 11 (upstream ABM) |
| **Output Contract** | JSON telemetry → Streamlit dashboard + CDC/fleet-ingestible lab notebook |
| **License** | MIT |

---

## 2. Core Architecture — The Five Decoupled Domains

The platform is a **bridging package** — it does not reimplement the
underlying scientific models.  Instead, it adapts their mathematical
contracts into a unified epoch-driven simulation loop.

### 2.1 Agent-Based Modeling (Korkin Lab `infection-dynamics`)

**Origin:** Korkin Lab, Worcester Polytechnic Institute (WPI).
*Srinivasan S, King J, Collins JM, Colubri A, Korkin D. "Real-time
spatiotemporal tracking of infectious outbreaks in confined environments
with a host–pathogen agent-based system." PNAS, 2026.*

**Bridge Module:** `engines/infection_dynamics_bridge.py`

The bridge adapts the Java ABM's dose-response model into Python:

```
P(infection) = 1 − (1 + dose/β)^{−α}
```

Where `α` and `β` are pathogen-specific parameters from `active_profiles.json`.

**Host shedding variance** (optional, `shedding_variance_log10` on pathogen profile):

```
shedding = 10^(curve[dpi] − dose_adjustment) × shedding_multiplier
shedding_multiplier = 10^(Normal(0, σ))   at infection time; persists for that infection
```

Default `σ = 0` → multiplier = 1.0. See `docs/SHEDDING_AND_CABINMATES.md`.

**Key Classes:**
- `KorkinAgent` — Python dataclass mirroring `Person.java` with
  `infection_status`, `illness_status`, `current_location`, `shedding_rate`,
  `shedding_multiplier` (per-pathogen host factor), `cabin_mate_ids` (stateroom
  co-occupants on cabin-corridor platforms), `susceptibility_multiplier`,
  `microflora_disruption_status`
- `IllnessStatus` / `InfectionStatus` — Enum states for SIR transitions
- `infection_probability(dose, alpha, beta)` — Scalar dose-response function

### 2.2 Six-Pathway Transmission Core

**Module:** `engines/transmission_core.py`

Pathogens navigate the shipboard environment through six distinct,
independent transport pathways:

| # | Pathway | Mechanism | Dose Source |
|---|---------|-----------|-------------|
| 1 | **Direct Contact** | Zone-colocation with avgR scaling; cabin-mate pairing under confinement on `Cabin_Corridor` zones | Agent shedding × contact pool × host multiplier |
| 2 | **Short-Range Droplet** | Immediate room-level aerosolization | 5% of total shedding → room aerosol pool |
| 3 | **Long-Range HVAC Airborne** | py-contam bridge distributes aerosol through ductwork | CONTAM mass-balance equation |
| 4 | **Fomite Deposition** | Surface pool accumulation + stochastic pickup | 10% pickup probability × 1% transfer fraction |
| 5 | **Food Contamination** | Pathogen mass deposited in dining zone food pools by infected food handlers | `food_contamination` profile block |
| 6 | **Environmental Colonization** | Persistent pathogen mass in zone environmental reservoirs | `environmental_contamination` profile block |

Each pathway produces:
- A **dose contribution** to susceptible agents
- A **contact-tracing record** for the surveillance inference hook

Combined dose feeds the Korkin Lab dose-response function.  All six
pathways are independently toggleable via protocol modifier scalars
(`direct_contact_scalar`, `droplet_scalar`, `hvac_airborne_scalar`,
`fomite_scalar`, `food_contamination_scalar`, `environmental_scalar`).

### 2.3 CONTAM-Style Airflow Transport (py-contam Bridge)

**Origin:** Von P. Walden, Washington State University.

**Bridge Module:** `engines/py_contam_bridge.py`

Implements the CONTAM multi-zone mass-balance equation:

```
dM_i/dt = Σ Q_ji · C_j · (1−η) − Q_out · C_i + S_i − λ · M_i
```

Where:
- `M_i` = pathogen mass in zone `i`
- `Q_ji` = volumetric flow from zone `j` to `i` (from `air_flow_paths.json`)
- `C_j` = concentration in source zone
- `η` = HVAC filter efficiency (configurable: MERV-8=20%, MERV-13=50%, HEPA=99.9%)
- `S_i` = source term (shedding by infected agents)
- `λ` = natural decay rate

Three airflow path types:
1. **Intra-zone HVAC recirculation** — filtered, within a single HVAC zone
2. **Cross-zone links** — ladder wells, shafts, and ducted connections
3. **Passive adjacency** — doors, hatches (unfiltered)

### 2.4 GRUMB Metagenomic Surveillance

**Origin:** GRUMB (Genome-Resolved Urban Microbiome Biosurveillance),
integrated bioinformatics pipeline.

**Integration Points:**
- `crusher_labs/observation_core.py` → `WastewaterSequencingGrid`
- 4-kingdom CLR (Centered Log-Ratio) arrays: Bacteria, Archaea, Fungi, Virus
- Dirichlet-multinomial sampling simulates real metagenomic sequencing runs
- CLR-space anomaly scoring detects microflora shifts independently of
  direct pathogen identification

**Critical Concept — Dual-Signal Shedding:**
When a host has disrupted microflora (e.g., from active Norovirus GI
infection), they shed an altered baseline microbial mass pool alongside
pathogen shedding.  The wastewater sequencing grid can detect these
background shifts even when pathogen mass is below detection limits.

### 2.5 Reactive Protocol Engine

**Module:** `crusher_labs/protocol_engine.py`

The protocol engine closes the feedback loop between diagnostic
observations and operational interventions.  The cycle is:

```
Instruments → LOW_FIDELITY stoplights → Protocol trigger evaluation
    → Active SOPs → Physics modifier injection → Next epoch
    → Cost ledger debits
```

**The feedback loop is fully autonomous.**  SOPs activate when trigger
conditions are met and deactivate when conditions clear.  There is
**no manual epoch-by-epoch scheduling** — this is a strict architectural
law (see `.cursorrules` Law 1).

---

## 3. Instrument Asset Scope

All six diagnostic instruments use **fast, matrix-driven sampling noise
models implemented natively in Python** (numpy).  They simulate realistic
instrument-level telemetry without requiring external bioinformatics
tool dependencies.

| # | Instrument | Class | Input | Output |
|---|-----------|-------|-------|--------|
| ENV 1 | Continuous Air Sniffer | `ContinuousAirSniffer` | zone airborne mass | Ct values, amplification curves |
| ENV 2 | Targeted Surface Swab | `TargetedSurfaceSwab` | zone surface mass + compliance | Ct values, technique variance |
| ENV 3 | Wastewater Sequencing Grid | `WastewaterSequencingGrid` | pooled pathogen mass + microflora shifts | Dirichlet-multinomial kingdom reads |
| CLN 4 | Clinical RDT | `ClinicalRapidDiagnostic` | agent shedding rate | Binary DETECTED/NOT DETECTED |
| CLN 5 | Clinical qPCR | `ClinicalQPCR` | agent specimen mass | Patient viral load Ct |
| CLN 6 | Clinical Microbiology | `ClinicalMicrobiology` | agent microflora status | Culture/staining, flora shift flags |

**Quality Control:**  All instruments share the `InstrumentQC` engine:
- Configurable `cross_contamination_rate` (default: 0.01% mass carryover)
- Automated negative control runs (frequency: low=1/12, medium=1/6, high=1/3)
- `QC_FAILURE` flagging when contamination exceeds detection threshold

**Noise Models (all native Python):**
- Log-normal multiplicative noise on captured mass
- Gaussian variance on collection efficiency (compliance-driven)
- Sigmoid amplification curve simulation (40 cycles)
- Dirichlet-multinomial sampling for metagenomic read counts

---

## 4. Strict Configuration Laws

These rules are extracted from `.cursorrules` and represent
**inviolable architectural constraints**.

### Law 1: No Hardcoded Epoch Schedules
All interventions evaluate dynamically via stoplight trigger conditions.
The protocol engine in `protocol_engine.py` reads LOW_FIDELITY stoplights
from the observation engine at each epoch and autonomously
activates/deactivates SOPs based on `protocols.json` definitions.

### Law 2: No Hardcoded Zone or Pathogen Names
Zone names are read from `spatial_layout.json`.  Pathogen IDs are
iterated from `active_profiles.json`.  Code must never assume specific
zone names (e.g., "Bridge", "MedBay") or pathogen IDs exist.

### Law 3: Scalar Bounds Are Physical Laws
Probabilities, compliance rates, and filtration efficiencies: `[0.0, 1.0]`.
Volumes, budgets, ACH values, recovery days: `≥ 0`.
Run `python3 tools/sanity_checker.py` to validate before committing.

### Law 4: Referential Integrity Is Mandatory
Every room reference in airflow paths, protocol zone closures, and
HVAC zone membership MUST resolve to an entry in `spatial_layout.json`.

### Law 5: Native Python Noise Models Only
Instruments simulate diagnostic noise natively in Python.  Do not
introduce command-line bioinformatics dependencies (BLAST, Bowtie2,
MEGAHIT, etc.) into the instrument pipeline.

### Law 6: Sibling Repos Are Read-Only
Never modify `infection-dynamics`, `py-contam`, `GRUMB`, `EMOD-Generic`,
or `FRED` from this project.

---

## 5. Cross-Module Data Pipeline

```
orchestrator.py (epoch loop)
  │
  ├─ infection_dynamics_bridge → agents: list[KorkinAgent]
  │                             → zone_pathogen_mass: dict[str, float]
  │
  ├─ transmission_core.execute_transmission(epoch, agents, zone_pathogen_mass)
  │   → ContactTracingMatrix     (shared_room, droplet, hvac_downstream, fomite_trailing)
  │   → list[TransmissionEvent]  (pathway, source_agent, target_agent, dose)
  │
  ├─ py_contam_bridge.step(zone_pathogen_mass)
  │   → updated_masses: dict[str, float]  (HVAC-transported)
  │
  ├─ observation_core instruments:
  │   ├─ AirSniffer.sample_all_zones(zone_airborne, zone_volumes)
  │   ├─ SurfaceSwab.swab_zones(zone_surface, compliance)
  │   ├─ WastewaterSeq.sample_all_zones(ww_mass, microflora_shifts)
  │   ├─ ClinicalRDT.test_agent(agent)
  │   ├─ ClinicalQPCR.test_agent(agent)
  │   └─ ClinicalMicro.test_agent(agent)
  │
  ├─ lab_notebook.log_*(epoch, instrument_results)
  │   → records[] in flat biosurveillance schema
  │
  ├─ protocol_engine.evaluate(stoplights)
  │   → active SOPs, merged physics modifiers
  │
  └─ cost_ledger.debit_*(epoch, category, amounts)
      → running financial/material/labor balances
      → FINANCIAL_AUDIT block at run end
```

**Key Type Contracts:**
- `zone_pathogen_mass: dict[str, float]` — zone name → total mass (copies)
- `zone_airborne = pathogen_mass × 0.6` — 60% airborne fraction
- `zone_surface = pathogen_mass × 0.4` — 40% surface fraction
- `ww_pathogen_mass = zone_surface × 0.1` — 10% greywater fraction
- All instrument outputs are `dict[str, Any]` keyed by zone name

---

## 6. Configuration File Relationships

```
active_profiles.json ──────────────────────────────────────────────────┐
  (pathogen definitions: shedding curves, shedding_variance_log10,      │
   dose-response, microflora)                                          │
  Default: 2 pathogens (destroyer baseline)                           │
  Alt: edison_10pathogen_profiles.json (10 pathogens, QMRA-sourced)   │
                                                                       │
spatial_layout.json ────────────────────────────────────────────────┐  │
  (zone nodes: id, volume, deck, display coords)                   │  │
  8 pre-built platforms in data/platforms/                          │  │
                                                                    │  │
air_flow_paths.json ────────────────────────────────────────────┐  │  │
  (HVAC zones, cross-zone links, adjacency)                    │  │  │
  References rooms in spatial_layout.json ◄────────────────────┘  │  │
                                                                   │  │
protocols.json ─────────────────────────────────────────────┐     │  │
  (SOPs: stoplight triggers → modifiers + costs)           │     │  │
  References zones for close_zones ◄───────────────────────┘     │  │
  References instrument classes from observation_core ◄──────────┘  │
  Transmission scalars bound [0,1] ◄────────────────────────────────┘
                                                                      
resource_costs.json                                                   
  (budgets, material inventory, per-test costs)                      
  Alt: edison_resource_costs.json (expanded sequencing + culture costs)
  Protocols reference material items defined here                     
                                                                      
microbiome_profiles/                                                  
  (coastal_port, open_ocean baselines + zone_type_modifiers)          
  Seed profiles for GRUMB environmental microbiome simulation         
                                                                      
logging_profile.json                                                  
  (fidelity tier selection, QC parameters)                           
  Controls lab_notebook output verbosity                              
```

---

## 7. Output Data Contracts

### 7.1 `telemetry_buffer/simulation_history.json`

Array of per-epoch records.  Each record contains the complete
simulation state:

| Key | Type | Description |
|-----|------|-------------|
| `epoch` | int | Epoch index (0-based) |
| `trigger_status` | str | `BASELINE` / `SUSPECTED` / `CONFIRMED` |
| `summary` | dict | Aggregate epi metrics (susceptible, infected, isolated, recovered, immune, symptomatic, sick_call_count, disrupted_microflora_count) |
| `spaces` | dict | Per-zone state: `pathogen_mass`, `pathogen_mass_by_id`, `concentration_per_m3`, `volume_m3` |
| `agents` | list | Per-agent state: agent_id, status, location, shedding_rate, susceptibility_multiplier |
| `multi_pathogen` | dict | Per-pathogen aggregate: infected, symptomatic, recovered, co_infected_count |
| `contact_tracing` | dict | Four exposure matrices + transmission events |
| `reactive_protocols` | dict | Active SOPs, merged modifiers, stoplight states |
| `cost_accounting` | dict | Financial balance, labor hours, material consumption, **operational impact score** (`operational_impact_epoch`, `operational_impact_cumulative`, `operational_impact_breakdown`) |
| `observation_engine` | dict | **Delivered** instrument results per zone/agent (after TAT queue). Keys: `air_sniffer`, `surface_swab`, `wastewater_sequencing`, `clinical_rdt`, `clinical_qpcr`, `clinical_microbiology`, `long_read_verification`. Entries may include `status` (`pending`/`complete`), `ordered_epoch`, `available_epoch`. |
| `microflora_shifts` | dict | Per-zone CLR-space anomaly data |
| `hvac` | dict | CONTAM transport state: filter type, efficiency, transport active |

### 7.2 `telemetry_buffer/artificial_lab_notebook.json`

Flat, CDC/fleet-ingestible biosurveillance records:

| Key | Type | Description |
|-----|------|-------------|
| `sample_id` | str | `CLN-{epoch}-{zone}-{assay}-{hash}` |
| `timestamp_epoch` | int | Epoch when sample was collected |
| `collection_point_type` | str | Instrument category |
| `collection_zone` | str | Zone or patient identifier |
| `assay_type` | str | `aerosol_pcr`, `surface_pcr`, `metagenomic_sequencing`, `lateral_flow_antigen`, `patient_qpcr`, `culture_and_staining`, `oxford_nanopore_long_read`, `microflora_disruption_status`, `trigger_transition` |
| `fidelity_tier` | str | `HIGH_FIDELITY` / `MID_FIDELITY` / `LOW_FIDELITY` |
| `binary_result` | str | `DETECTED` / `NOT DETECTED` / `NORMAL` / `DISRUPTED` / etc. |
| `inferred_anomaly_score` | float | 0.0–1.0 (0=normal, 1=critical) |
| `qc_status` | str | `QC_PASS` / `QC_FAILURE` / `QC_NOT_RUN` |

Additional fields vary by fidelity tier and assay type (see `schemas/lab_notebook.schema.json`).

Includes `FINANCIAL_AUDIT` and `PROTOCOL_SUMMARY` blocks at the top level.

---

## 8. Formal JSON Schemas

All data contracts have formal JSON Schema (draft 2020-12) definitions
in `schemas/`:

| Schema File | Validates |
|-------------|-----------|
| `pathogen_profiles.schema.json` | `data/pathogens/active_profiles.json` |
| `spatial_layout.schema.json` | `data/platforms/*/spatial_layout.json` |
| `air_flow_paths.schema.json` | `data/platforms/*/air_flow_paths.json` |
| `protocols.schema.json` | `data/config/protocols.json` |
| `resource_costs.schema.json` | `data/config/resource_costs.json` |
| `logging_profile.schema.json` | `data/config/logging_profile.json` |
| `simulation_history.schema.json` | `telemetry_buffer/simulation_history.json` |
| `lab_notebook.schema.json` | `telemetry_buffer/artificial_lab_notebook.json` |

Validate with:
```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/pathogen_profiles.schema.json data/pathogens/active_profiles.json
```

---

## 9. Sibling Repositories — Reference Only

| Repository | Domain | Maintainer | Role in Platform |
|------------|--------|------------|-----------------|
| `infection-dynamics` | Agent-based Norwalk/SARS-CoV-2 outbreak simulation | Korkin Lab, WPI (Srinivasan, King, Collins, Colubri, Korkin) | Dose-response model, avgR contact arrays, SIR state machine |
| `py-contam` | CONTAM indoor air quality I/O library | Von P. Walden, WSU | Mass-balance equation, airflow path definitions |
| `GRUMB` | Genome-Resolved Urban Microbiome Biosurveillance | Kirkup et al. | 4-kingdom CLR arrays, taxonomic profiling, contamination risk index |
| `EMOD-Generic` | Epidemiological MODeling framework | Institute for Disease Modeling (IDM/Gates Foundation) | Stochastic SIR/SEIR compartmental transitions |
| `FRED` | Framework for Reconstructing Epidemiological Dynamics | Univ. of Pittsburgh PHDL / CMU / Epistemix | Agent scheduling, compliance modeling, spatial movement |

**These repositories are read-only from this project.**  The bridging
package adapts their mathematical contracts — it does not modify their
source code.
