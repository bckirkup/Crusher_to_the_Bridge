# Long-Read Sequencing Parameters — Notes

## Purpose

Parameter file for the `LongReadNanoporeSequencing` modality in
`crusher_labs/modalities/long_read_sequencing.py`. The simulation loads
this JSON at runtime via `long_read_sequencing.params_path` in
`crusher_labs/config.yaml`.

## Two Deployment Profiles

### Flongle Rapid ($137/run)

Flongle flow cell with rapid library prep: species-level ID in ~30 minutes,
strain typing in ~2 hours. Primary shipboard verification when routine
modalities flag ambiguous signals.

### MinION Standard ($800/run)

Deeper characterization (full-genome assembly, phylogenetics, AMR) over
12–48 hours when time allows.

## Wiring (implemented)

### Config (`crusher_labs/config.yaml`)

```yaml
instrument_turnaround:
  config_path: "data/config/instrument_turnaround.json"

long_read_sequencing:
  enabled: false
  params_path: "data/config/long_read_sequencing_params.json"
  default_profile: "flongle_rapid"
```

### Modality

`LongReadNanoporeSequencing.verify()`:

1. Loads deployment profile and `simulation_parameters.detection_model`
2. Builds compositional vector from zone `pathogen_mass_by_id` or agent infections
3. Draws multinomial reads, applies error injection
4. Emits `pathogen_calls` when fraction ≥ `min_fraction_for_detection`

### Turnaround

Profile `turnaround.epoch_fraction` &lt; 1.0 delivers same epoch; `full_run_hours`
maps to whole epochs (24 h/epoch default). See `instrument_turnaround.json` for
all observation instruments.

### Escalation integration

Long-read results feed stoplights (`long_read_verification_sequencing`) and the
decision engine when delivered. Confirmed pathogens → RED; negative verification → GREEN.

## References

- ONT product specifications: https://nanoporetech.com/products
- Wick et al. 2023. Genome Biology 24:40 (basecalling benchmarks)
- Sanderson et al. 2023. BMC Bioinformatics (metagenomic classifiers on long reads)
