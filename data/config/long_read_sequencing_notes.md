# Long-Read Sequencing Parameters — Notes

## Purpose

This parameter file provides Oxford Nanopore sequencing parameters for the
`LongReadNanoporeSequencing` modality stub in `crusher_labs/modalities/long_read_sequencing.py`.
It fills in the assay parameters that the stub declares are "out-of-repo."

## Two Deployment Profiles

### Flongle Rapid ($137/run)
The primary shipboard profile. A Flongle flow cell with rapid library prep 
gives species-level pathogen ID in ~30 minutes and strain typing in ~2 hours.
This is the verification tool for Tier 1-2 escalation: when wastewater or 
wearables flag something ambiguous, run a Flongle to confirm or rule out 
before committing to costly confinement.

### MinION Standard ($800/run)
For deeper characterization when time allows. Full-genome assembly, 
phylogenetic placement, comprehensive AMR profiling. Takes 12-48 hours.
Use case: confirmed outbreak where strain characterization matters for 
treatment decisions or epidemiological investigation.

## Key Assumptions

### Throughput
- Flongle: 500k reads, 1.5 Gb. Based on FLO-FLG114 published specs.
  Real yields vary 0.5-2 Gb depending on library quality and pore activity.
- MinION: 5M reads, 30 Gb. Based on FLO-MIN114. Typical range 10-50 Gb.

### Accuracy
- R10.4.1 + SUP basecalling: Q20 modal accuracy (~99% per base).
  This is current-generation performance (2024-2025).
- Homopolymer errors remain the dominant residual error mode at ~8%.
- For pathogen classification, per-base accuracy matters less than 
  read-level classification accuracy, which is >96% at species level
  with 100+ reads using Kraken2 or WIMP.

### Detection Limits
- Without enrichment: target needs to be >0.01% (Flongle) or >0.005% 
  (MinION) of total reads for reliable detection.
- In wastewater, pathogen may be <0.1% of total DNA → detection is 
  possible but near the limit. A single infected person shedding 10^9 
  particles/day into a ship's greywater system may produce detectable 
  signal at the Flongle level.
- In clinical specimens, host depletion is critical. Without it, 
  >90% of reads are human and pathogen signal is diluted.
- Clinical culture isolates give near-pure target → highest sensitivity.

### Turnaround
- Flongle rapid prep: 15 min hands-on + 10 min to first classification.
  Species ID at ~30 min. This is sub-epoch (epoch_fraction = 0.04 at 
  1 epoch = 1 day), meaning results are available same-epoch.
- MinION ligation prep: 2h hands-on + 15 min to first classification.
  Full run 48h. Cross-epoch result (epoch_fraction = 0.08).

### Cost Sources
- Flongle FLO-FLG114: ~$90 (ONT store price, 2024)
- MinION FLO-MIN114: ~$675 (ONT store price, 2024; flow cell wash 
  allows 1-2 reuses at reduced yield)
- Rapid prep SQK-RAD114: ~$32/sample (8 reactions/kit at ~$255)
- Ligation prep SQK-LSK114: ~$85/sample (6 reactions/kit at ~$510)

## Wiring to the Simulation

### Config (crusher_labs/config.yaml)
The existing `long_read_sequencing` section needs a `params_path` key:
```yaml
long_read_sequencing:
  enabled: true
  params_path: "data/config/long_read_sequencing_params.json"
  default_profile: "flongle_rapid"
```

### Modality (crusher_labs/modalities/long_read_sequencing.py)
The `LongReadNanoporeSequencing.verify()` method needs to:
1. Load parameters from the JSON file
2. Select the deployment profile (flongle_rapid or minion_standard)
3. Simulate multinomial read sampling from the zone's compositional vector
4. Apply error injection per the accuracy model
5. Run classification against the pathogen taxonomy
6. Return pathogen_calls with read counts and confidence

### Escalation Integration
Long-read results should feed back to the decision engine:
- Pathogen confirmed → set clinical detection mode RED
- Mixed infection → flag coinfection for treatment adjustment  
- AMR detected → enhanced decontamination protocol
- Negative verification → downgrade escalation (avoid false alarm cost)

The last point is the key value proposition: a $137 Flongle run that 
rules out an outbreak saves $400k+ in unnecessary confinement.

## References

- ONT product specifications: https://nanoporetech.com/products
- Wick et al. 2023. "Performance of neural network basecalling tools 
  for Oxford Nanopore sequencing." Genome Biology 24:40.
- Sanderson et al. 2023. "Systematic comparison of metagenomic 
  classifiers for long-read sequencing data." BMC Bioinformatics.
- Mitsuhashi & Matsumoto 2020. "Long-read sequencing for rare human 
  genetic diseases." Journal of Human Genetics 65:11-19.
