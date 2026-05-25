# Pricing notes for `resource_costs.json`

Purpose: rough-order-of-magnitude (ROM) cost inputs for a shipboard public-health simulation. Values are not payer reimbursement rates and should not be used for procurement. They are intended to keep relative tradeoffs realistic: rapid tests are cheap/fast, qPCR is moderate, cultures require more hands-on time, and sequencing consumes both reagents and scarce batch/run capacity.

## Key assumptions

- Currency: USD, nominal 2024-2025 pricing unless a source page displayed 2026 pricing at retrieval time.
- Costs are all-in ROM simulation costs, not strict billable charges. For per-test entries, `financial_usd` includes consumables, controls, small disposables, and a practical allowance for overhead. The `materials` map separately tracks inventory depletion.
- Labor hours are hands-on shipboard staff time, not elapsed turnaround time. Culture incubation and sequencing run time are mostly elapsed instrument time and are not counted as labor unless active handling or analysis is needed.
- Shipboard sequencing is modeled as multiplexed. Fractional `sequencing_flow_cells` use in per-sample sequencing tests represents allocating one flow cell or reagent cartridge across multiple samples.
- qPCR costs assume onboard nucleic-acid extraction and assay reagents are already available. No instrument depreciation is charged per test.

## Source-backed pricing anchors

### 1. Rapid diagnostic tests (RDT)

- Public bulk COVID antigen test pricing can be as low as about $3.15-$3.60/test in large lots (iHealth bulk pricing surfaced in web search).
- Multi-pathogen or professional-use RDTs are commonly higher, so I used a conservative shipboard ROM of **$10/test kit** and **$12/test all-in**.
- Labor: **0.25 h/test**, consistent with point-of-care collection, running, and recording.

### 2. Clinical qPCR assays

- PANDORA/TGHN compared SARS-CoV-2 RT-qPCR kits and extraction kits, showing reagent-cost sensitivity across commercial master mixes and extraction choices: https://pandora.tghn.org/covid-19-diagnostic-tools/covid-19-kit-cost-analysis/
- Public qPCR kit pricing varies widely; reagent-only prices can be a few dollars per reaction, but clinical-grade sample prep, controls, extraction, consumables, and repeat/invalid-test allowance dominate practical costs.
- I used **$45 per `pcr_kits` reaction bundle** and **$50/test all-in** for `clinical_qpcr`.
- Labor: **1.0 h/test**, including extraction setup, plate loading, result review, and documentation.

### 3. Clinical microbiology cultures

- Culture consumables are cheap relative to labor. Example public pricing from search: BD BACTEC Standard/10 Aerobic/F culture vials listed at **$403.99/50**, about **$8.08/vial**; sheep-blood agar plates were surfaced at about **$6.17/10**, about **$0.62/plate**.
- A public fee schedule surfaced culture/susceptibility examples around **$43-$70** per test. Medicare CLFS pages provide federal lab-fee context but do not represent full internal shipboard cost: https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory-fee-schedule-clfs/files
- I used **$8 per `culture_media_sets`** and **$35/test** for `clinical_microbiology`.
- Labor: **1.5 h/test**, because cultures require accessioning, inoculation, follow-up reads, and possible susceptibility setup.

### 4. Targeted surface swabs, environmental PCR

- Surface collection itself is inexpensive, but targeted environmental PCR is essentially a swab plus qPCR workflow.
- I split the original `surface_swab` into:
  - `surface_swab_culture`: **$10**, **0.25 h**, `swab_kits`: 1
  - `surface_swab_pcr`: **$55**, **0.75 h**, `swab_kits`: 1 and `pcr_kits`: 1
- This preserves a low-cost environmental swab option while adding the requested targeted environmental PCR option.

### 5. Continuous air sniffer filters/assays

- Thermo Fisher's AerosolSense sampler has been publicly reported at **$4,995** with single-use cartridges anticipated at **less than $75** for users doing PCR in-house: https://www.fishersci.com/us/en/brands/I9C8L6UU/thermo-scientific-aerosolsense-sampler.html and reporting summarized in search result text.
- I used **$60 per `air_sniffer_cartridges`** and **$75/sample all-in** to cover cartridge + in-house qPCR/handling.
- Labor: **0.5 h/sample** for cartridge swap, accessioning, and assay setup. Continuous sampler capital cost is not included in per-test cost.

### 6. Wastewater sequencing grid panels

- Illumina's Viral Surveillance Panel v2 supports wastewater/environmental samples and has <9 h library prep time: https://supportassets.illumina.com/products/by-type/sequencing-kits/library-prep-kits/viral-surveillance-panel.html
- Public wastewater testing contracts and reporting vary widely. Search results surfaced Biobot examples ranging from a temporary **$120/test** demonstration price to normal rates around **$1,200/test** in early wastewater-COVID reporting. Current public-health contracts depend strongly on sampling frequency, logistics, and panel breadth.
- I used **$250/sample** for `wastewater_sequencing_panel`, which is a mid-low ROM for onboard concentration/extraction plus targeted sequencing.
- Labor: **3.0 h/sample**, reflecting concentration/extraction and library/panel handling.

### 7. Full metagenomic shotgun sequencing

- SeqCenter shotgun metagenomics public pricing: **$145, $265, $350, $475/sample** for increasing read packages: https://www.seqcenter.com/service/metagenome-sequencing/shotgun-metagenomics/
- Psomagen FAST-Meta public pricing surfaced at **$69/sample** for shallow shotgun, **$89/sample** for standard, and **$119/sample** for deep shotgun: https://www.psomagen.com/fast-meta-psomagen
- Nanopore MinION/GridION flow cells are publicly listed around **US$840**; Nanopore's product page also advertises flow-cell access from **$630/flow cell** depending on bundle/volume: https://store.nanoporetech.com/flow-cells.html and https://nanoporetech.com/products/sequence/minion-comparison
- I used **$300/sample** for `metagenomic_shotgun_sequencing`, with `library_prep_kits`: 1 and `sequencing_flow_cells`: 0.1, approximating 10 multiplexed samples per portable flow cell.
- Labor: **4.0 h/sample**, including extraction QC, library prep, run setup, and basic analysis/QC.

### 8. 16S amplicon sequencing

- SeqCenter 16S/ITS public pricing: **$45/sample** for 20k reads, **$55/sample** for 50k reads, and **$75/sample** for 100k reads: https://www.seqcenter.com/service/metagenome-sequencing/16s-its-sequencing/
- MiSeq v3 600-cycle reagent-kit pricing surfaced at about **$2,132.64/run** for up to ~50M total paired-end reads, consistent with low per-sample sequencing cost when highly multiplexed.
- I used **$65/sample** for `amplicon_16s_sequencing`, with `library_prep_kits`: 1 and `sequencing_flow_cells`: 0.04, approximating 25 samples/run.
- Labor: **2.5 h/sample**, mostly sample processing/library setup and basic taxonomy workflow.

## Inventory additions

Added materials needed for the requested surveillance stack:

- `culture_media_sets`: culture plates/broth/vials.
- `air_sniffer_cartridges`: single-use bioaerosol sampler cartridges/filters.
- `wastewater_collection_kits`: wastewater sample collection containers/preservatives.
- `library_prep_kits`: per-sample NGS library preparation reagents and indexes.
- `sequencing_flow_cells`: flow cells or reagent cartridges for portable sequencing / small Illumina runs.

## Limitations

- Public prices are heterogeneous: catalog list price, institutional core price, government contract price, and clinical charge can differ by >10x.
- Sequencing cost depends heavily on batching. Low sample count shipboard runs will cost more per sample than high-throughput core-facility pricing.
- No capital equipment depreciation is included except indirectly in ROM per-test overhead. If the simulation models acquisition of qPCR instruments, incubators, sequencers, or air samplers, those should be separate capital inventory items.
- Wastewater panel pricing is least certain because public contracts bundle logistics, sampling kits, reporting dashboards, and lab analysis.
