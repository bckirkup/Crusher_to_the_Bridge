# Wastewater Assay Mode Switch Spec
# Four analytical modes for shipboard wastewater pathogen detection

> **Status:** Modes 1 and 2 as specified

## Context

The current wastewater implementation uses GRUMB compositional metagenomics 
(WastewaterSequencingGrid), which treats the pathogen as one taxon competing 
for reads in a shotgun metagenomic library. At realistic cruise norovirus 
prevalence (~0.3% shedders), this produces ~0 pathogen reads per 250K library 
— the modality is functionally blind.

Real-world cruise wastewater surveillance uses RT-qPCR (Zafeiriadou 2026, 
Ahmed 2020). The codebase already has `TargetedPCR` with the right math 
(Ct from log10 mass + extraction efficiency + LOD gate). It just needs to 
be wired to wastewater collection points.

## Existing code to reuse

| Component | Location | What it does |
|---|---|---|
| `TargetedPCR` | `crusher_labs/modalities/targeted_pcr.py` | Ct = -3.322 × log10(M × η) + 40. LOD at Ct 38. |
| `WastewaterSequencingGrid` | `crusher_labs/modalities/sequencing.py` | GRUMB compositional multinomial draws |
| `LongReadNanoporeSequencing` | `crusher_labs/modalities/long_read_sequencing.py` | Nanopore reads with error injection |
| `ClinicalRDT` | `crusher_labs/modalities/clinical_rdt.py` | Phase-dependent sensitivity sigmoid |
| `clinical_qpcr` | `clinical_instrument_params.json` | Pathogen-specific Se/Sp for clinical specimens |
| `build_wastewater_pathogen_mass()` | `orchestrator_epoch.py` L54 | Aggregates shedder mass into wastewater zones |

## Four modes

### Mode 1: RT-qPCR (NEW — priority for sentinel paper)

**Assay**: Pathogen-specific RT-qPCR on wastewater concentrate.
**Observable**: Ct value (or genome copies/L via standard curve).
**Model**: Reuse `TargetedPCR._compute_ct()` on wastewater pathogen mass.
**Signal budget**: 
  - 18 shedders at 10^9 gc/g × 200 mL feces/day / 24h = 1.5×10^9 gc/h total
  - Into ~50,000 L/day ship wastewater = ~30,000 gc/L
  - After extraction (η=0.35): ~10,000 gc/L recovered
  - Ct = -3.322 × log10(10000) + 40 = -3.322 × 4 + 40 = 26.7
  - LOD at Ct 38 ≈ 10^0.6 = 4 gc/L recovered → easily detected
**Noise**: Add Ct measurement noise ~ Normal(0, 0.5) per replicate.
**Output per sample**: `{ct_value, detected, concentration_gc_per_L, pathogen}`.
**Temporal resolution**: Limited by sampling frequency × holding tank residence.

### Mode 2: Targeted amplicon sequencing (NEW)

**Assay**: PCR-amplified sequencing (e.g., norovirus capsid amplicon).
**Observable**: Pathogen read count + genotype/variant calls.
**Model**: Two-step: (1) `TargetedPCR` to determine if above LOD, 
(2) if detected, draw reads ~ Binomial(depth, enriched_fraction) where 
enriched_fraction reflects amplification efficiency (~0.1-0.9 depending 
on primer match and template quantity).
**Advantage over qPCR**: Provides genotype information for source attribution.
**Output**: `{pathogen_reads, total_reads, genotype, detected}`.

### Mode 3: Metagenomic short-read (EXISTING — current WastewaterSequencingGrid)

**Assay**: Shotgun metagenomic sequencing of wastewater.
**Observable**: Compositional read profile, CLR anomaly score.
**Model**: Current GRUMB multinomial with `pathogen_frac = mass / (mass + 100)`.
**Limitation**: Effectively blind at typical cruise pathogen prevalence.
**Use case**: Broad microbiome surveillance, not targeted pathogen detection.
**Fix needed**: Increase sensitivity by either (a) scaling the denominator or 
(b) adding a spike-in enrichment factor for known pathogens.

### Mode 4: Long-read Nanopore (EXISTING — LongReadNanoporeSequencing)

**Assay**: Oxford Nanopore MinION/GridION.
**Observable**: Species-level classification + AMR gene detection.
**Model**: Already implemented with error injection and host-scale filtering.
**Use case**: Confirmation/typing after qPCR or amplicon detection.
**Latency**: 6-24h turnaround, used for escalation not routine screening.

## Implementation

### Config switch

Add to wastewater surveillance config:

```json
{
  "wastewater_surveillance": {
    "enabled": true,
    "assay_mode": "qpcr",  // "qpcr" | "amplicon" | "metagenomic" | "long_read"
    "sampling_interval_epochs": 6,
    "holding_tank_residence_hours": 4,
    "collection_points": ["aft_main_sewer"],

    "qpcr": {
      "extraction_efficiency": 0.35,
      "ct_slope": -3.322,
      "ct_intercept": 40.0,
      "lod_ct_threshold": 38.0,
      "ct_noise_sd": 0.5,
      "sample_volume_mL": 100,
      "concentration_factor": 100
    },
    "amplicon": {
      "extraction_efficiency": 0.35,
      "lod_ct_threshold": 38.0,
      "amplification_efficiency": 0.5,
      "sequencing_depth": 50000,
      "primer_targets": ["norovirus_capsid", "sars_cov2_spike"]
    },
    "metagenomic": {
      "sequencing_depth": 250000,
      "background_read_fraction": 0.9999
    },
    "long_read": {
      "params_file": "data/config/long_read_sequencing_params.json"
    }
  }
}
```

### Wastewater mass-to-signal conversion

The key function to add (in a new `wastewater_qpcr.py` or by extending 
`targeted_pcr.py`):

```python
def wastewater_qpcr_sample(
    pathogen_mass: float,          # from build_wastewater_pathogen_mass()
    wastewater_volume_L: float,    # daily volume for the collection zone
    sample_volume_mL: float,       # how much is sampled (default 100)
    concentration_factor: float,   # ultracentrifugation etc (default 100×)
    extraction_efficiency: float,  # RNA extraction (default 0.35)
    ct_slope: float,               # standard curve slope (default -3.322)
    ct_intercept: float,           # standard curve intercept (default 40)
    lod_ct: float,                 # LOD threshold (default 38)
    ct_noise_sd: float,            # measurement noise (default 0.5)
    rng: np.random.Generator,
) -> dict:
    # Mass per liter of wastewater
    gc_per_L = pathogen_mass / wastewater_volume_L

    # Concentration step (e.g., 100× by ultrafiltration)
    gc_per_L_concentrated = gc_per_L * concentration_factor

    # In the sample volume
    gc_in_sample = gc_per_L_concentrated * (sample_volume_mL / 1000)

    # Extraction
    gc_recovered = gc_in_sample * extraction_efficiency

    # Ct value
    if gc_recovered <= 0:
        return {"detected": False, "ct_value": None, "gc_per_L": 0}

    ct = ct_slope * math.log10(gc_recovered) + ct_intercept
    ct += rng.normal(0, ct_noise_sd)  # measurement noise

    detected = ct <= lod_ct

    return {
        "detected": detected,
        "ct_value": round(ct, 2),
        "gc_per_L": gc_per_L,
        "gc_per_L_concentrated": gc_per_L_concentrated,
        "gc_recovered": gc_recovered,
    }
```

### Holding tank residence time convolution

The `pathogen_mass` passed to the assay should be convolved with an 
exponential residence kernel:

```python
# In orchestrator_epoch.py or a new wastewater_hydraulics.py
# Track a running exponential average of pathogen mass per collection point
mass_smoothed[t] = (1 - dt/tau) * mass_smoothed[t-1] + (dt/tau) * mass_raw[t]
```

where `tau = holding_tank_residence_hours` in epoch units. This smears 
the temporal signal — longer tau = more blurring = harder to attribute 
to specific port calls.

### Sentinel Stan model update

The wastewater observation in `sentinel_attribution.stan` becomes:

```stan
// qPCR mode: log-normal on concentration
data {
  int<lower=0> N_ww;
  vector[N_ww] log_gc_per_L;        // log10(gc/L), observed
  array[N_ww] int<lower=0> detected; // 1 if Ct <= LOD
  array[N_ww] int<lower=1> ww_epoch;
  real<lower=0> ww_sigma_prior;
  real<lower=0> shedding_scale;      // gc/person-hour for an infected person
  real<lower=0> ww_volume_L;         // daily wastewater volume
}

parameters {
  real<lower=0> sigma_ww;           // log-space observation noise
}

model {
  sigma_ww ~ exponential(1.0 / ww_sigma_prior);

  for (i in 1:N_ww) {
    // Expected gc/L from latent incidence convolved with shedding kernel
    real expected_shedders = incidence_total[ww_epoch[i]]; // from the renewal model
    real expected_gc_per_L = shedding_scale * expected_shedders / ww_volume_L;

    if (detected[i]) {
      log_gc_per_L[i] ~ normal(log10(expected_gc_per_L + 1e-12), sigma_ww);
    } else {
      // Censored below LOD
      target += normal_lcdf(log10(LOD_gc_per_L) | log10(expected_gc_per_L + 1e-12), sigma_ww);
    }
  }
}
```

## Priority for sentinel paper
1. Implement qPCR mode (reuse TargetedPCR math)
2. Add holding tank residence convolution
3. Wire into sentinel Stan model
4. Run the operations parameter scan (4,230 runs)
5. Amplicon mode deferred to genomics phase (PR 9 in sentinel spec)
