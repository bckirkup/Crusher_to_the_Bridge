# Diagnostic Instrument Parameterization for CTB Simulation
# Based on literature review (task:348b25c9-c2e4-4550-94a5-585672a4757b, 
# task:1c551396-501a-44cf-88ca-22bfb2cf7dcc, task:275f271c-fc32-475a-be02-227b35be97c0,
# task:09794313-a793-403b-bdda-afb0ba92db72)

## Instrument Definitions

### 1. Rapid Antigen Test (RDT) — pathogen-specific lateral flow
| Pathogen | Sensitivity (peak) | Sensitivity (early) | Sensitivity (late) | Specificity | TAT (min) | Cost (USD) | Sample | Notes |
|----------|-------------------|--------------------|--------------------|-------------|-----------|------------|--------|-------|
| Norovirus GII | 0.78 | 0.50 | 0.40 | 0.98 | 15 | 12 | Stool | Genotype-dependent; GI lower (~0.52) |
| SARS-CoV-2 | 0.82 | 0.52 | 0.52 | 0.99 | 15 | 12 | NP swab | Best evidence base; 56.8% asymptomatic |
| Influenza A | 0.68 | 0.40 | 0.35 | 0.99 | 15 | 12 | NP swab | Adults only 34% in some meta-analyses |
| Measles | 0.40 | 0.30 | 0.40 | 0.95 | 20 | 15 | Blood/serum | No mature commercial POC; IgM LFA prototype |
| Legionella | 0.86 | 0.60 | 0.80 | 0.98 | 15 | 15 | Urine | Serogroup 1 only; misses other serogroups |
| Vibrio | 0.50 | 0.30 | 0.40 | 0.90 | 20 | 15 | Stool | No validated POC RDT for V. parahaemolyticus |
| Campylobacter | 0.55 | 0.35 | 0.40 | 0.92 | 15 | 12 | Stool | False positives a concern; NAAT preferred |
| C. difficile | 0.70 | 0.50 | 0.60 | 0.97 | 30 | 15 | Stool | GDH screen + toxin; combined algorithm ~89% |
| Hantavirus | 0.00 | 0.00 | 0.00 | — | — | — | — | NO VALIDATED RDT EXISTS |
| Ebola | 0.86 | 0.60 | 0.70 | 0.95 | 15 | 20 | Blood | High-containment only; negative needs PCR |

### 2. Multiplex PCR Panel — BioFire FilmArray or equivalent
Coverage: GI panel covers norovirus, Campylobacter, C. difficile, Vibrio
          Respiratory panel covers influenza, SARS-CoV-2 (RP2.1 only)
          NO panel covers: measles, Legionella (on pneumonia panels), hantavirus, Ebola

| Pathogen | Panel | Sensitivity | Specificity | TAT (min) | Cost (USD) | Notes |
|----------|-------|-------------|-------------|-----------|------------|-------|
| Norovirus GI/GII | GI Panel | 0.95 | 0.99 | 60 | 45 | Excellent performance |
| SARS-CoV-2 | RP2.1 | 0.98 | 0.99 | 45 | 45 | RP2.1 only; older panels miss it |
| Influenza A/B | RP/RP2/RP2.1 | 0.98 | 0.99 | 45 | 45 | Strong concordance with individual PCR |
| Campylobacter | GI Panel | 0.95 | 0.97 | 60 | 45 | Better than antigen RDT |
| C. difficile (toxigenic) | GI Panel | 0.96 | 0.98 | 60 | 45 | Detects toxin gene, not free toxin |
| Vibrio spp. | GI Panel | 0.93 | 0.98 | 60 | 45 | V. cholerae on xTAG; broad Vibrio on FilmArray |
| Measles | NONE | — | — | — | — | Not on any standard multiplex panel |
| Legionella | Pneumonia Panel | 0.95 | 0.99 | 60 | 45 | Only on lower-respiratory pneumonia panels |
| Hantavirus | NONE | — | — | — | — | Not on any standard panel |
| Ebola | NONE | — | — | — | — | Not on any standard panel; BSL-4 pathogen |

### 3. Single-target qPCR — gold standard reference
| Pathogen | Sensitivity | Specificity | TAT (hours) | Cost (USD) | Notes |
|----------|-------------|-------------|-------------|------------|-------|
| Norovirus | 0.98 | 0.99 | 2-4 | 85 | RT-qPCR; detects ~48h before symptoms |
| SARS-CoV-2 | 0.98 | 0.99 | 2-4 | 85 | Detects 1-3 days before symptoms |
| Influenza A | 0.97 | 0.99 | 2-4 | 85 | RT-PCR reference standard |
| Measles | 0.98 | 0.99 | 2-4 | 85 | Throat swab + urine; best within 3d of rash |
| Legionella | 0.95 | 0.99 | 2-4 | 85 | Respiratory specimen + urine antigen |
| Vibrio | 0.97 | 0.99 | 2-4 | 85 | Culture also high-quality for Vibrio |
| Campylobacter | 0.97 | 0.99 | 2-4 | 85 | Culture takes 48-72h |
| C. difficile | 0.95 | 0.98 | 2-4 | 85 | NAAT detects gene, not active toxin |
| Hantavirus | 0.95 | 0.99 | 4-8 | 100 | RT-PCR; reference lab preferred |
| Ebola | 0.97 | 0.99 | 2-4 | 100 | BSL-4; Cepheid GeneXpert Ebola ~100 min |

### 4. Clinical Microbiology (Culture)
| Pathogen | Sensitivity | Specificity | TAT (hours) | Cost (USD) | Notes |
|----------|-------------|-------------|-------------|------------|-------|
| Norovirus | 0.00 | — | — | — | NOT CULTURABLE in routine labs |
| SARS-CoV-2 | 0.00 | — | — | — | BSL-3 required; not routine |
| Influenza | 0.70 | 0.99 | 48-96 | 50 | Slow; molecular preferred |
| Measles | 0.50 | 0.99 | 72-168 | 50 | Requires Vero cells; rarely done |
| Legionella | 0.50 | 0.99 | 72-120 | 50 | BCYE agar; definitive but slow |
| Vibrio | 0.90 | 0.99 | 24-48 | 30 | TCBS agar; good for Vibrio |
| Campylobacter | 0.85 | 0.99 | 48-72 | 30 | Microaerophilic; 42°C |
| C. difficile | 0.80 | 0.99 | 48-96 | 40 | Toxigenic culture = reference |
| Hantavirus | 0.00 | — | — | — | BSL-4 required |
| Ebola | 0.00 | — | — | — | BSL-4 required |

### 5. Wearable Biosensor (continuous monitoring)
| Parameter | Value | Source |
|-----------|-------|-------|
| Detection sensitivity (respiratory) | 0.67-0.80 | DETECT study, Stanford COVID wearables |
| Detection sensitivity (GI) | unknown | No adequate evidence |
| Pre-symptomatic lead time | 1-2 days (resp) | Mishra et al. 2020, flu challenge study |
| False positive rate (daily) | 5-15% | Exercise, stress, alcohol, sleep disruption |
| Specificity (infection vs. non-infection) | 0.60-0.75 | Low biological specificity |

### 6. Environmental Surveillance
| Method | Pathogen Coverage | Sensitivity | TAT | Cost | Notes |
|--------|-------------------|-------------|-----|------|-------|
| Wastewater PCR | Norovirus, SARS-CoV-2, others | Population-level; not individual | 4-8h | 100-200 | Early warning 4-7 days before clinical |
| Air sampling (bioaerosol) | Respiratory pathogens | Variable; depends on volume | 4-8h | 50-100 | HVAC integration possible |
| Surface swab PCR | Norovirus, SARS-CoV-2, others | Low; surface contamination ≠ transmission | 2-4h | 85 | Fomite detection |
