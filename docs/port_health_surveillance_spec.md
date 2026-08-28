# Port Public Health Surveillance Model Spec
# Simulating what port-side authorities observe independently of ships

## Purpose

The sentinel model infers port-specific pathogen hazards from ship data.
To validate this, we need a model of what each port's public health system 
*independently* observes. This creates a ground truth that doesn't come 
from the ship — it comes from the port's own surveillance infrastructure.

The key insight: the same underlying community prevalence generates BOTH 
the ship's passenger infections AND the port's surveillance signals. If 
the sentinel model's inferred hazard correlates with the port's independent 
signal, the method is validated.

## Port surveillance model

Each port in the simulation has a `PortHealthAuthority` object that 
generates observable signals based on the port's true pathogen prevalence 
and its surveillance capabilities.

### Data model

```python
@dataclass(frozen=True)
class PortSurveillanceCapability:
    port_id: str                    # UN-LOCODE
    port_name: str
    region: str                     # WHO region
    population: int                 # catchment population

    # Syndromic surveillance
    syndromic_enabled: bool         # does the port report clinical cases?
    syndromic_delay_days: int       # reporting delay (1-14 days typical)
    syndromic_coverage: float       # fraction of cases captured (0.1-0.9)
    syndromic_pathogens: list[str]  # what's reportable

    # Wastewater surveillance  
    wbe_enabled: bool               # does the port have municipal WBE?
    wbe_assay: str | None           # "qpcr" | "metagenomic" | None
    wbe_frequency_days: float       # sampling cadence (1-7 days)
    wbe_pathogens: list[str]        # what's tested
    wbe_lod_gc_per_L: float         # limit of detection

    # Laboratory capacity
    lab_confirmation: bool          # can the port confirm pathogen ID?
    lab_turnaround_days: float      # days from sample to result
    genotyping_available: bool      # can they sequence/genotype?

    # Reporting pathway
    reports_to: str                 # "CDC_VSP" | "CARPHA" | "ECDC" | "WHO_IHR" | "local_only"
    reporting_threshold: str | None # e.g., "3% AGE" for VSP

    # Tourism health interface
    cruise_arrival_screening: bool  # does the port screen arriving ships?
    departure_health_cert: bool     # does the port issue health certs?


@dataclass(frozen=True)
class PortEpidemiologicalState:
    port_id: str
    pathogen: str
    date: date

    # True state (known to the simulation, not to the port)
    true_community_prevalence: float   # fraction actively infectious
    true_incidence_per_100k_day: float
    true_ww_gc_per_L: float            # if WBE existed, what would it see?

    # Observable signals (what the port authority actually sees)
    syndromic_cases_reported: int | None    # None if not enabled
    syndromic_rate_per_100k: float | None
    wbe_gc_per_L_observed: float | None    # None if not enabled
    wbe_detected: bool | None
    lab_confirmed_cases: int | None

    # Derived
    alert_level: str    # "normal" | "elevated" | "outbreak" | "unknown"
```

### Port profiles for cruise regions

```json
{
  "port_surveillance_profiles": {

    "USMIA": {
      "port_name": "Miami",
      "region": "AMR",
      "population": 450000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 3,
      "syndromic_coverage": 0.6,
      "syndromic_pathogens": ["norovirus", "influenza", "SARS-CoV-2", "measles"],
      "wbe_enabled": true,
      "wbe_assay": "qpcr",
      "wbe_frequency_days": 2,
      "wbe_pathogens": ["SARS-CoV-2", "influenza", "norovirus", "RSV", "mpox"],
      "wbe_lod_gc_per_L": 100,
      "lab_confirmation": true,
      "lab_turnaround_days": 1,
      "genotyping_available": true,
      "reports_to": "CDC_VSP",
      "reporting_threshold": "3% AGE",
      "cruise_arrival_screening": true,
      "departure_health_cert": false
    },

    "MXCZM": {
      "port_name": "Cozumel",
      "region": "AMR",
      "population": 100000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 7,
      "syndromic_coverage": 0.2,
      "syndromic_pathogens": ["dengue", "norovirus"],
      "wbe_enabled": false,
      "wbe_assay": null,
      "lab_confirmation": false,
      "lab_turnaround_days": null,
      "genotyping_available": false,
      "reports_to": "local_only",
      "reporting_threshold": null,
      "cruise_arrival_screening": false,
      "departure_health_cert": false
    },

    "KYGEC": {
      "port_name": "George Town",
      "region": "AMR",
      "population": 35000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 5,
      "syndromic_coverage": 0.3,
      "syndromic_pathogens": ["dengue", "norovirus"],
      "wbe_enabled": false,
      "lab_confirmation": false,
      "reports_to": "CARPHA",
      "cruise_arrival_screening": false
    },

    "ESPMI": {
      "port_name": "Palma de Mallorca",
      "region": "EUR",
      "population": 420000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 2,
      "syndromic_coverage": 0.7,
      "wbe_enabled": true,
      "wbe_assay": "qpcr",
      "wbe_frequency_days": 3,
      "wbe_pathogens": ["SARS-CoV-2", "influenza"],
      "lab_confirmation": true,
      "genotyping_available": true,
      "reports_to": "ECDC"
    },

    "GRPIR": {
      "port_name": "Piraeus (Athens)",
      "region": "EUR",
      "population": 160000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 3,
      "syndromic_coverage": 0.5,
      "wbe_enabled": true,
      "wbe_assay": "qpcr",
      "wbe_frequency_days": 7,
      "wbe_pathogens": ["SARS-CoV-2", "norovirus"],
      "lab_confirmation": true,
      "genotyping_available": true,
      "reports_to": "ECDC",
      "cruise_arrival_screening": true,
      "note": "Mouchtouri group operates ship WW pilot from this port"
    },

    "BSBGI": {
      "port_name": "Bridgetown (Barbados)",
      "region": "AMR",
      "population": 110000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 4,
      "syndromic_coverage": 0.4,
      "wbe_enabled": false,
      "lab_confirmation": true,
      "lab_turnaround_days": 3,
      "reports_to": "CARPHA",
      "cruise_arrival_screening": true,
      "note": "CARPHA Regional Tourism Health Program hub"
    },

    "DKCPH": {
      "port_name": "Copenhagen",
      "region": "EUR",
      "population": 800000,
      "syndromic_enabled": true,
      "syndromic_delay_days": 1,
      "syndromic_coverage": 0.8,
      "wbe_enabled": true,
      "wbe_assay": "qpcr",
      "wbe_frequency_days": 2,
      "wbe_pathogens": ["SARS-CoV-2", "influenza", "norovirus", "RSV"],
      "wbe_lod_gc_per_L": 50,
      "lab_confirmation": true,
      "genotyping_available": true,
      "reports_to": "ECDC"
    }
  }
}
```

### Signal generation

Each simulation day, each port generates its observable signals:

```python
def generate_port_signals(
    port: PortSurveillanceCapability,
    true_prevalence: float,
    pathogen: str,
    population: int,
    rng: np.random.Generator,
) -> PortEpidemiologicalState:

    # True incidence (shared generator for both ship exposure and port signals)
    true_incidence = true_prevalence * population

    # Syndromic signal (delayed, underascertained)
    if port.syndromic_enabled and pathogen in port.syndromic_pathogens:
        # Cases are ascertained with probability = coverage, delayed
        syndromic_cases = rng.binomial(int(true_incidence), port.syndromic_coverage)
        # Delay is applied at the reporting layer, not here
    else:
        syndromic_cases = None

    # Wastewater signal
    if port.wbe_enabled and pathogen in port.wbe_pathogens:
        # gc/L from community shedding
        shedders = true_prevalence * population
        gc_per_L = shedders * SHEDDING_RATE_GC_PER_PERSON_DAY / port.daily_wastewater_volume_L
        # Add measurement noise
        log_gc = np.log10(max(gc_per_L, 1e-3)) + rng.normal(0, 0.5)
        observed_gc = 10**log_gc
        detected = observed_gc >= port.wbe_lod_gc_per_L
    else:
        observed_gc = None
        detected = None

    return PortEpidemiologicalState(...)
```

### How this connects to the sentinel model

The sentinel inference produces: `lambda_port[p]` — hazard per person-hour ashore.

The port surveillance produces: independent signals of community prevalence.

The validation is:
```
corr(ship_inferred_lambda[p, week], port_observed_signal[p, week])
```

For ports WITH surveillance: this correlation validates the sentinel model.
For ports WITHOUT: the sentinel model fills the gap. The ship IS the 
surveillance system.

## Reporting pathways to model

### CDC Vessel Sanitation Program (US-bound ships)
- Ship reports AGE cases exceeding 3% to CDC 24h before arrival
- Port health officer may board and inspect
- VSP publishes outbreak reports publicly
- **In the model**: ships generate VSP reports; US homeports receive them

### CARPHA Regional Tourism Health Program (Caribbean)
- Tourism Health Information System (THiS) — electronic reporting
- Ship Inspection reporting tool
- Covers 24 Caribbean member states
- Syndromic surveillance, NOT wastewater
- **In the model**: Caribbean ports report syndromic data to CARPHA hub

### EU SHIPSAN / ECDC (European ports)
- EU Ship Sanitation Inspection programme
- ECDC coordinates cross-border surveillance
- EU Sewage Sentinel System provides WBE for member state cities
- **In the model**: European ports have both WBE and syndromic channels

### WHO International Health Regulations
- Ships must report disease events to port health authorities
- IHR notification for diseases of international concern
- Ship Sanitation Certificates (SSC) issued by designated ports
- **In the model**: IHR notifications generated for qualifying events

## Implementation location

```
picard_framework/analysis/sentinel/
├── port_health.py              # PortSurveillanceCapability + signal generation
├── port_profiles.py            # Regional port profile libraries
├── data/
│   ├── port_surveillance_caribbean.json
│   ├── port_surveillance_mediterranean.json
│   ├── port_surveillance_nordic.json
│   └── port_surveillance_alaska.json

schemas/port_surveillance.schema.json
```

## For the sentinel paper

The port health model serves three roles:
1. **Validation**: compare ship-inferred hazards against port WBE where available
2. **Gap identification**: quantify the surveillance desert at Caribbean ports
3. **Value proposition**: demonstrate the ship fills a gap no other system covers

The narrative: "At ports with WBE (Miami, Barcelona, Copenhagen), the ship's 
inferred hazard tracks the municipal signal. At ports without WBE (Cozumel, 
Nassau, Grand Cayman), the ship provides the only pathogen-level data."
