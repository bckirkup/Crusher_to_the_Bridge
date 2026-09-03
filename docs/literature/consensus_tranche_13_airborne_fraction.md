# Consensus tranche 13 — the airborne emission fraction has no measured referent, and the only calicivirus aerosol-decay rate is not norovirus

**Status:** Evidence assembled. **No pathogen-profile constant, no engine
constant and no register row changed by this document.** Nothing here is
adopted; the proposed register text is in
[`fragments/airborne-fraction.md`](fragments/airborne-fraction.md) for the lead
to merge.
**Scope:** task #42, two quantities on the norovirus airborne route —
`airborne_emission_fraction` (shipped 1e-4, Grade C unsourced-assumed) and
`airborne_half_life_hours` (shipped 1.1, cross-pathogen inheritance).
**Method:** six unfiltered Consensus MCP `search` calls (§2), then primary-text
verification of the two candidates whose exact definition decides whether they
can be read as either quantity: Tung-Thompson 2015 (full text, PLOS ONE) and
Zargar 2025 (PubMed abstract; full text paywalled, and that limit is recorded
rather than worked around).

The short answer: **quantity 1 is a null result and quantity 2 is a null result
for norovirus.** No study measures emission to air as a fraction of a host's
shedding — for norovirus or, in this search, for any pathogen. One study
measures an aerosolised fraction of a *single expelled bolus*, which is a
different denominator and cannot be substituted. No study measures the decay of
airborne human norovirus; one 2025 study measures aerosol decay of feline
calicivirus, a named calicivirus surrogate, in a room-sized chamber at stated
temperature and RH.

---

## 1. The two quantities as the model defines them

| Field | Shipped | Model meaning |
|---|---|---|
| `airborne_emission_fraction` (`norwalk_gi`) | 1e-4 | the fraction of a host's shedding that is emitted into the airborne zone reservoir |
| `airborne_half_life_hours` (`norwalk_gi`) | 1.1 | decay half-life of the airborne reservoir, in hours |

The register records the second as van Doremalen's SARS-CoV-2 figure, itself
mis-cited on the SARS-CoV-2 arm (van Doremalen measures 2.7 h), so 1.1 is
inherited twice over. This tranche does not touch either value; it establishes
what, if anything, the literature measures under those definitions.

## 2. Queries run

All six were run against the Consensus MCP `search` tool. **All unfiltered** —
no `year_min`, `study_types`, `controlled`, `domain` or other filter was
applied on any call, so the recall reported below is not narrowed by filtering.
Truncated result sets were read from their overflow files, so the tails are
included.

1. `norovirus air concentration genome copies per cubic metre air sampling hospital outbreak quantitative`
2. `aerosolization of virus during simulated vomiting event fraction of virus particles aerosolized MS2 tracer`
3. `murine norovirus feline calicivirus aerosol decay rate half-life relative humidity temperature rotating drum inactivation`
4. `airborne norovirus survival persistence in air decay rate aerosol chamber suspended infectivity loss over time`
5. `virus emission rate to air per hour from infected person quantified alongside faecal shedding fraction emitted aerosol source strength`
6. `toilet flushing bioaerosol emission enteric virus per flush washroom air concentration norovirus`

Query 5 was written to find the norovirus analogue of the SARS-CoV-2 emission
work (Alsved 2022, Zheng 2022) that converted an unsourceable fraction into a
bounded absolute rate. Its twenty results contain **no norovirus paper at all**:
every emission-rate measurement returned is respiratory (SARS-CoV-2, influenza),
and the enteric route is absent from that literature.

## 3. Quantity 1 — `airborne_emission_fraction`: null, and what is measured instead

### 3.1 The null, stated precisely

No study in these searches reports virus emitted to air as a fraction (or
percentage) of the same host's total shedding. The obstruction is structural,
not a gap in coverage: faecal and vomitus shedding are measured in genome
copies per gram or per specimen in one set of subjects, and airborne virus is
measured in copies per cubic metre of room air in another, with no study
measuring both in the same subject over the same period. A fraction requires a
numerator and denominator in commensurable units from the same host; that pairing
does not exist in this literature.

This is a negative search result, not a proof of non-existence: it establishes
that six differently-worded unfiltered queries covering the mechanism, the
number, the emission vocabulary and the washroom setting return nothing of the
kind.

### 3.2 What is measured instead — air concentration

Concentration in room air, all Grade B for a maritime cabin/zone analogue and
**not** interpretable as an emission fraction or an emission rate:

| Study | Setting, n | Quantity | Value |
|---|---|---|---|
| Alsved 2019, *Clin Infect Dis*, [10.1093/cid/ciz584](https://doi.org/10.1093/cid/ciz584) | hospital outbreaks, repeated sampling near 26 patients; 86 air samples, 21 positive from 10 patients | airborne NoV RNA concentration | **5–215 copies/m³**; positivity strongly associated with recent vomiting; RNA in both <0.95 µm and >4.51 µm fractions |
| Bonifait 2015, *Clin Infect Dis*, [10.1093/cid/civ321](https://doi.org/10.1093/cid/civ321) | outbreaks in 8 healthcare facilities; 48 air samples, positive in 47% | airborne NoV GII genomes | **1.35 × 10¹ – 2.35 × 10³ genomes/m³**; detected outside patient rooms and at nurses' stations |
| Rupprom 2024, *Sci Rep*, [10.1038/s41598-024-73369-w](https://doi.org/10.1038/s41598-024-73369-w) | tertiary hospital, Bangkok; 60 air samples, 13 positive | airborne NoV genome copies | GI **6.0 × 10²**; GII **3.4 × 10¹ – 5.0 × 10³ copies/m³** |
| Kittigul 2025, *Food Environ Virol*, [10.1007/s12560-025-09647-1](https://doi.org/10.1007/s12560-025-09647-1) | wastewater-treatment-plant aerosols; 24 samples, 8 RT-qPCR positive | airborne NoV genome copies | GI **9.8 × 10²** and **3.2 × 10³**; GII **1.5 × 10² – 5.5 × 10³ copies/m³** |
| Boles 2021, *Sci Rep*, [10.1038/s41598-021-02938-0](https://doi.org/10.1038/s41598-021-02938-0) | flushometer toilet seeded with MNV at 10⁵–10⁶ PFU/mL, sampling 0.15 m above bowl rim | airborne MNV RNA after flush | **383–684 RNA copies/m³**, against 2.18 × 10⁵ – 9.65 × 10⁶ total copies recovered from the bowl water |

Alsved 2019 is the figure already known here, and it is a **concentration**: a
standing amount per cubic metre of room air at the moment of sampling, which is
the product of emission, dilution, ventilation and decay. It is not an emission
rate and cannot be divided by anything in the profile to yield one.

Boles 2021 measures the airborne and the source term in the same experiment,
which is the closest structure in this set to a fraction. It is still not one:
converting it would require the effective mixing volume and the sampling
interval, neither of which the abstract reports, and the source is a seeded
toilet bowl rather than a host's shedding. **That arithmetic is deliberately not
performed here.** The register's existing SARS-CoV-2 note — that the fraction is
"derivable" from measured emission ÷ modelled specimen titre — has no norovirus
counterpart, because there is no measured norovirus emission rate to be the
numerator (§2, query 5).

### 3.3 The one measured aerosolised fraction, and why it is a different quantity

**Tung-Thompson 2015**, *PLOS ONE*,
[10.1371/journal.pone.0134277](https://doi.org/10.1371/journal.pone.0134277) —
"Aerosolization of a Human Norovirus Surrogate, Bacteriophage MS2, during
Simulated Vomiting". Verified against the Results and Methods, not the abstract.

- **Quantity as the paper defines it:** "the amount of MS2 aerosolized as a
  percent of total virus 'vomited'".
- **Value:** **7.2 × 10⁻⁵ % ± 0.00006 to 2.67 × 10⁻² % ± 0.03** (Table 2), i.e.
  as a *fraction* **7.2 × 10⁻⁷ to 2.67 × 10⁻⁴**. The paper states the same bound
  in prose: "In all cases, <0.03% of the initial concentration of MS2 in the
  artificial vomitus was aerosolized". **The units are percent.** Reading the
  tabulated numbers as fractions overstates the quantity by two decades, and
  that misreading is the single most likely way this paper enters a profile
  wrongly.
- **Setting and material:** one-quarter-scale simulated vomiting device;
  13.1 mL of artificial vomitus (scaled from 800 mL) at low viscosity
  6.24 mPa·s (0.1% CMC) or high viscosity 177.5 mPa·s (25% pre-gelatinised
  starch); MS2 at 10⁸ or 10¹⁰ PFU/mL; expulsion at 1,283 / 290 / 115.1 mmHg,
  plus a 290 mmHg condition with four simulated coughs at 233 mmHg.
- **Chamber and capture:** sealed 30.5 × 30.5 × 44.5 cm Plexiglas chamber
  (≈41 L); SKC BioSampler into 4 mL PBS at 12.5 L/min for 15 min (221 chamber
  volumes) after the event; **counts normalised for volume and for the measured
  8.5% biosampler capture efficiency**; deposition on dry chamber surfaces
  <0.1% of input.
- **Sample size:** experiments in **triplicate** per condition; percent
  recoveries non-normally distributed, compared by Kruskal-Wallis.
- **Grade: B** as an event-level aerosolisation fraction for an emesis event.
  MS2 is a surrogate, and the device is a physical analogue of a human, not a
  human.

Why it is **not** `airborne_emission_fraction`: the denominator is the virus in
a single expelled bolus, measured at the instant of expulsion. The model's
denominator is the host's shedding — the faecal/emesis shedding curve integrated
over an epoch, across a course of illness in which most emitted virus never
passes through a projectile vomiting event at all. Substituting one for the
other silently redefines the field as "fraction of vomitus aerosolised per
vomiting event", which is a different mechanism with a different time base. If
the field were redefined that way — an emesis-event-conditioned aerosolisation
fraction rather than a fraction of continuous shedding — this measurement would
be a Grade B source for it. That is a field-design decision and is not taken
here.

For the record and without inference: the shipped 1e-4 lies inside
Tung-Thompson's fraction range 7.2 × 10⁻⁷ – 2.67 × 10⁻⁴, near its top. Because
the denominators differ, that coincidence is not evidence for the shipped value
and must not be reported as sourcing it.

## 4. Quantity 2 — `airborne_half_life_hours`: no human norovirus measurement; one calicivirus surrogate rate

### 4.1 The null

No study in these searches measures the decay or half-life of **airborne human
norovirus**. Human norovirus cannot be routinely cultured, so airborne human
NoV work reports RNA, and RNA persistence is not infectivity decay. Tranche 5's
null stands and is reproduced by an independent search.

### 4.2 The one calicivirus aerosol-decay rate

**Zargar 2025**, *J Virol Methods* 335:115144,
[10.1016/j.jviromet.2025.115144](https://doi.org/10.1016/j.jviromet.2025.115144)
(PMID 40064377).

- **Quantity:** rate of **biological decay** of infectious aerosolised virus,
  assayed as plaque-forming units.
- **Surrogate:** **feline calicivirus** (FCV, ATCC VR-782) — a named calicivirus
  surrogate, assayed alongside HCoV-OC43 and RV-14.
- **Aerosolisation method:** six-jet Collison nebuliser into a **25 m³
  (900 ft³) room-sized aerobiology chamber**; muffin fan for uniform mixing and
  to keep aerosols airborne; all suspensions contained a soil load to simulate
  body fluids; sampling by slit sampler onto 3% gelatin plates, liquefied and
  assayed for PFU.
- **Temperature and RH:** **22 ± 2 °C**, **50 ± 10% RH**.
- **Value:** FCV **0.0081 ± 0.0031 log10 PFU/m³/min** (HCoV-OC43 0.0052 ±
  0.00026; RV-14 0.0034 ± 0.0027).
- **Grade: B** — direct measurement of a named calicivirus in an analogous
  indoor-air setting; **not** Grade A, because FCV is not human norovirus and a
  chamber is not a cabin.

As a unit transformation of the same quantity (not a conversion between
quantities): t½ = log10(2) / rate = 0.30103 / 0.0081 = **37.2 min = 0.62 h**;
carrying the reported ±1 SD on the rate gives **0.45–1.00 h**. Recorded so the
number is comparable with the field's units; it is not proposed for adoption
here.

**Two limits recorded rather than worked around.** (i) The full text is
paywalled (Europe PMC: subscription required), so the abstract's "biological
decay" label — implying total decay corrected for physical loss — could not be
verified against the Methods, nor could the fit form, the number of chamber
runs, or the sampling schedule. (ii) The work was funded by Reckitt and two
authors were Reckitt employees; the paper's purpose is air-purifier evaluation,
with the decay rates as the untreated baseline.

### 4.3 Persistence bounds, which are not half-lives

| Study | What it bounds |
|---|---|
| Purhonen 2024, *Food Environ Virol*, [10.1007/s12560-024-09595-2](https://doi.org/10.1007/s12560-024-09595-2) | MNV nebulised from 6 log10 TCID50/mL into a 3-L chamber stayed **infectious** across 30 and 90 min exposures (2.89 ± 0.29 and 3.20 ± 0.49 log10 TCID50/mL in exposed cell dishes; 6.20 ± 0.24 and 6.93 ± 1.02 log10 copies/mL). Demonstrates survival, not a decay coefficient |
| Alsved 2020, *Sci Rep*, [10.1038/s41598-020-72932-5](https://doi.org/10.1038/s41598-020-72932-5) | MNV aerosolised by bubble bursting vs nebulisation; infectivity per virus similar between generators, with drying in air identified as the likely driver of infectivity loss. A mechanism finding, no rate |
| Rupprom 2024, *Food Environ Virol*, [10.1007/s12560-024-09590-7](https://doi.org/10.1007/s12560-024-09590-7) | NoV GII **RNA** detectable in chamber air to 120 min (5 mL collection) and 240 min (20 mL); recoveries 25 ± 12% and 22 ± 19%. A sampling-method result on RNA, not infectivity |
| Sanka 2026, *J Aerosol Sci*, [10.1016/j.jaerosci.2026.106816](https://doi.org/10.1016/j.jaerosci.2026.106816) | MS2 and ΦX174 nebulised in buffer or artificial gastric fluid: infectious phage in air at 2 h, **absent from air at 24 h** (still infectious on steel and apple peel). Brackets airborne persistence between 2 and 24 h; two sampling times cannot yield a rate |
| Donaldson 1976, *Vet Microbiol*, [10.1016/0378-1135(76)90056-0](https://doi.org/10.1016/0378-1135\(76\)90056-0) | FCV and vesicular exanthema virus **sensitive to RH in the 30–70% range**; non-lipid viruses stable under aeration. Establishes that calicivirus aerosol decay is RH-dominated — the abstract gives no rate or half-life, so the RH dependence cannot be quantified from it |

Taken together these bound airborne calicivirus persistence at the order of
hours, consistent with Zargar's rate, and none of them can replace it.

## 5. Rejected candidates, with reasons

| Candidate | Reason for rejection |
|---|---|
| Dubuis 2020, *PLoS ONE*, [10.1371/journal.pone.0231164](https://doi.org/10.1371/journal.pone.0231164) — MNV-1 ≥2 log10 inactivation at 0.23 ppm ozone, 85% RH, 40 min | Intentional chemical disinfection. Measures ozone efficacy, not natural airborne decay |
| Buonanno 2024, *Sci Rep*, [10.1038/s41598-024-57441-z](https://doi.org/10.1038/s41598-024-57441-z) — 99.8% reduction of airborne MNV under 222 nm far-UVC | Engineered inactivation; the untreated arm is not reported as a decay rate |
| Boone 2025, *Am J Infect Control*, [10.1016/j.ajic.2025.04.008](https://doi.org/10.1016/j.ajic.2025.04.008) — air sanitiser after toilet flushing | Intervention efficacy; MS2 surrogate; no untreated decay rate or emission term |
| Higham 2024, *Indoor Environments*, [10.1016/j.indenv.2024.100069](https://doi.org/10.1016/j.indenv.2024.100069) — QMRA of toilet-plume exposure for SARS-CoV-2 and norovirus | **Model output, not measurement.** Combines measured particle concentrations with assumed faecal titres; adopting its norovirus numbers would import an exposure model into a transmission model |
| Buonanno 2020 / Aganovic 2022 / Mikszewski 2021 quanta-emission papers | Quanta emission rates back-calculated from outbreak attack rates or from viral-load assumptions. **Fitted quantities, and circular against this project's scored anchors** |
| Merhi 2022, *PNAS*, [10.1073/pnas.2204593119](https://doi.org/10.1073/pnas.2204593119) — suspension and infectivity times | Theoretical/physicochemical model of droplets, not a norovirus measurement |
| Uhrbrand 2018, *J Appl Microbiol*, [10.1111/jam.13588](https://doi.org/10.1111/jam.13588) — sampler and filter comparison for airborne NoV | Sampling-efficiency methodology; no emission, concentration-in-setting or decay quantity |
| Alsved 2022 / Zheng 2022 (SARS-CoV-2 emission rates), Alsved 2023 exhaled TCID50/s | Correct quantity, wrong pathogen and wrong route. Already carried on the SARS-CoV-2 rows; importing them onto norovirus would repeat the inheritance defect this tranche is documenting |
| Bozkurt 2012 and other MNV/FCV thermal-inactivation work; Cannon 2006, Bae 2007 surface/water persistence | Wrong phase. Thermal, surface and water decay are different mechanisms from aerosol decay and are not convertible to an airborne half-life |
| Fears 2020, Smither 2020, Oswin 2022, Schuit 2020, van Doremalen 2020 | SARS-CoV-2 aerosol stability. These are the source of the inherited 1.1/2.7 confusion; they are norovirus evidence of no kind |
| Tan 2024, *Viruses*, [10.3390/v16010151](https://doi.org/10.3390/v16010151); Paddy 2022 systematic review; Vardoulakis 2021 | Reviews. Useful for locating primaries, no primary measurement of either quantity |

## 6. What this tranche proposes

Recorded in [`fragments/airborne-fraction.md`](fragments/airborne-fraction.md);
in outline, and for the lead to accept, amend or reject:

1. `airborne_emission_fraction` (`norwalk_gi`) — **null result confirmed by
   search, not merely suspected.** The field has no measurable referent as
   defined. What exists instead is air *concentration* (§3.2) and one
   event-level aerosolisation fraction with an incompatible denominator (§3.3).
   The register's existing wording is already correct; this tranche upgrades its
   basis from assertion to searched-and-recorded, and names the redefinition
   that would make a measurement adoptable.
2. `airborne_half_life_hours` (`norwalk_gi`) — **null for human norovirus
   stands.** The nearest measurement is Zargar 2025's FCV rate at stated
   temperature and RH, Grade B, abstract-verified only. Whether a calicivirus
   surrogate rate may stand in for the norovirus field is an adoption decision,
   not a search finding, and is left to the lead.
