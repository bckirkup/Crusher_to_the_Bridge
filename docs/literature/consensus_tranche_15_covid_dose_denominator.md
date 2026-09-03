# Tranche 15 — the SARS-CoV-2 dose denominator in genome copies: no non-circular ID50 exists, and the conversion that would rescue Killingley is measured but ~2.7 logs wide

**Status:** Evidence assembled and interpreted. **No pathogen-profile constant,
no engine constant and no screen interval changes in this document.** Nothing
here is adopted; the register contribution is proposed in
[`fragments/covid-dose-denominator.md`](fragments/covid-dose-denominator.md) and
merged by the lead.

**Scope:** unit `covid-dose-denominator`, item #30 — the SARS-CoV-2
dose-response denominator (`dose_response.alpha` / `beta`, shipped 0.18 / 58.0),
in **genome copies**, which is the unit the emission side of this arm now works
in after [tranche 9](mql_tranche_9_sars_cov2.md) §1 bounded emission absolutely
(Alsved 2022, Zheng 2022).

**Method:** Consensus MCP `search`, eight queries, **all unfiltered** — no
`year_min`, `exclude_preprints`, `study_types`, `controlled` or `domain` filter
was used on any query, because the recall being established is exactly "does
anyone measure this at all". Full truncated result lists were read from the
overflow files. Every value that enters §4 or §6 was checked against the paper's
Results or figure legend, not its abstract; where that check failed the candidate
is recorded in §5 as unverified rather than used.

**Two things this document deliberately does not do.** It does not compose
Killingley's 10 TCID50 with a conversion factor to produce an ID50 in copies —
the two ingredients are reported separately in §3 and §4 with their own
uncertainties, and whether the composition is defensible is the lead's call
(§6.4 states what the composition would cost in logs). And no candidate was
selected, ranked or excluded by what its value would do to VSP, the Diamond
Princess, the Greg Mortimer or any anchor in `docs/anchors/`; that comparison was
not computed at any point in this unit.

---

## 1. The quantity, as narrowly as it can be stated

Two searchable objects, in priority order:

1. **A dose-response or ID50 for SARS-CoV-2 in immunologically naive humans that
   is not obtained by fitting a transmission model to observed attack rates,**
   reported in or convertible to **genome copies**.
2. **A measured conversion factor between infectious units and genome copies** —
   copies per TCID50 or copies per PFU — in **respiratory specimens** or
   **culture supernatant**, with its specimen type, variant, assay and spread.

Object 2 is the load-bearing one: Killingley 2022 is the only independent
infectious dose available and it is in TCID50, while the emission side is in
copies. A measured ratio is what would make the two commensurable.

## 2. Queries, verbatim

All eight were run against `mcp_tool(server="consensus", tool_name="search")`
with `query` as the only argument.

1. `SARS-CoV-2 genome copies per TCID50 ratio RNA copies to infectious virus titre`
2. `SARS-CoV-2 RNA copies per PFU respiratory specimen quantitative culture viral load infectivity relationship`
3. `SARS-CoV-2 human challenge study inoculum dose escalation seronegative volunteers intranasal TCID50 genome copies`
4. `hamster intranasal SARS-CoV-2 dose titration 50% infectious dose ID50 dose-response PFU animal model`
5. `infectious viral load focus forming units per mL and RNA copies per mL nasopharyngeal swab Omicron Delta ratio quantitative`
6. `specific infectivity SARS-CoV-2 genome copies per infectious unit ratio clinical specimens variation orders of magnitude`
7. `SARS-CoV-2 virus stock culture supernatant genome copies to TCID50 ratio quantified digital PCR titration`
8. `SARS-CoV-2 challenge inoculum characterisation genome copies RNA content of 10 TCID50 dose human challenge virus stock`

Queries 1–3 establish the two objects; 4 goes after an animal dose-response; 5–7
attack the ratio from the clinical, the mechanistic and the assay-calibration
vocabularies separately; 8 asks whether anyone characterised the challenge
inoculum itself in copies, which would answer object 1 outright.

## 3. Object 1 — null result, twice over

**No study reports a SARS-CoV-2 human or animal ID50 in genome copies.** Every
independent dose measurement found is in infectious units, and query 8 returned
no characterisation of the Killingley inoculum in copies.

| Study | Design | Dose, as the paper states it | Outcome | Grade |
|---|---|---|---|---|
| Killingley 2022, *Nat Med*, DOI [10.1038/s41591-022-01780-9](https://doi.org/10.1038/s41591-022-01780-9) | Human challenge, 36 seronegative unvaccinated adults 18–29, intranasal, pre-Alpha (SARS-CoV-2/human/GBR/484861/2020) | **10 TCID50**, single dose level | 18 of 34 per-protocol (~53%) infected; nasal peak 8.87 log10 copies/mL (median, 95% CI 8.41–9.53) | **B** — a real measured dose-response point, wrong unit, and the host is a young naive adult rather than a mixed-age ship population |
| Jackson 2024, *Lancet Microbe*, DOI [10.1016/S2666-5247(24)00025-9](https://doi.org/10.1016/S2666-5247(24)00025-9) | Human challenge, 36 **seropositive** adults 18–30, stepwise dose escalation, same virus stock | **10¹ → 10⁵ TCID50**, 4–8 volunteers per level | **No sustained infection at any dose**, including 10⁵ TCID50; 5 of 36 (14%) transient PCR positivity | **B** for the design, **C** as an input here — it bounds the dose-response of *previously infected* hosts, not naive ones |
| Rosenke 2020, *Emerg Microbes Infect*, DOI [10.1080/22221751.2020.1858177](https://doi.org/10.1080/22221751.2020.1858177) | Syrian hamster, intranasal titration | **ID50 = 5 infectious particles** | Consistent broncho-interstitial pneumonia at higher doses | **C** — animal, and "infectious particles" is a plaque/TCID50 unit, not copies |
| Lin 2022, *Sci Rep*, DOI [10.1038/s41598-022-09218-5](https://doi.org/10.1038/s41598-022-09218-5) | Syrian hamster challenged with patient-derived salivary isolate | **Minimum infectious dose ≤ 14 PFU** | Illness in the hamster model | **C** — animal, upper bound only |
| Blaurock 2022, *Sci Rep*, DOI [10.1038/s41598-022-19222-4](https://doi.org/10.1038/s41598-022-19222-4) | Golden Syrian hamster, orotracheal, doses 10⁵ → 10⁻⁴ TCID50 | **MID = 10⁻³ TCID50**; 10² TCID50 optimal for experimental infection | Shedding up to 10².⁷⁵ TCID50/mL at the MID | **C** — animal, and the route is orotracheal, not intranasal |

Two observations that matter more than the individual rows:

- **The animal dose figures span roughly five orders of magnitude in infectious
  units** (10⁻³ TCID50 orotracheal to ~14 PFU intranasal, with 5 infectious
  particles in between), across species-matched but route-mismatched designs. An
  animal ID50 is therefore not a tighter input than Killingley; it is a looser
  one, in the same wrong unit.
- **Jackson 2024 is the strongest non-circular dose-response measurement in the
  literature and it is a negative result.** It is recorded here because a unit
  that reported only Killingley would leave the next reader to re-find it: a
  five-log dose escalation that fails to infect seropositive adults says the
  denominator is not a property of the virus alone. On a ship whose population is
  overwhelmingly previously infected or vaccinated, that is a statement about the
  model's host structure, not about `beta`.

## 4. Object 2 — measured, and honestly wide

### 4.1 The measurements

| Study | Quantity as defined | Material | Variant / assay | Value and spread | n | Grade |
|---|---|---|---|---|---|---|
| **Lin 2022**, *Sci Rep*, DOI [10.1038/s41598-022-09218-5](https://doi.org/10.1038/s41598-022-09218-5) | **N-gene RNA copies per PFU**, computed per specimen from paired titre and copy number, log10-transformed, Gaussian fitted | Diverse **clinical and environmental** specimens (NP, throat, saliva, sputum, cough, hands, fomites) from 75 patients | Ancestral lineages; plaque assay on Vero CCL-81, re-titred on Vero E6/TMPRSS2 where needed | **mean 10⁵·² ± 1.0 SD** = **160,000 copies per PFU**, ±1 SD ⇒ **1.6 × 10⁴ – 1.6 × 10⁶**. Same paper, same assay: culture-harvested virus gives **~10⁴:1** | 151 of 459 specimens yielded plaques | **B** |
| **Zapata-Cardona 2022**, *Iran J Microbiol*, DOI [10.18502/ijm.v14i3.9758](https://doi.org/10.18502/ijm.v14i3.9758) | **E-gene RNA copies per PFU**, per isolate, plus PFU-vs-TCID50 offset | **Culture supernatant** of five propagated isolates | D614G, Alpha, Gamma, Delta, Mu; plaque assay + TCID50 + RT-qPCR, Vero E6 | **1:29,800** (D614G), **1:11,700** (Alpha), **1:8,930** (Gamma), **1:12,500** (Delta), **1:2,950** (Mu) ⇒ **2.95 × 10³ – 2.98 × 10⁴**, a 10-fold variant spread. TCID50 and PFU differ by **0.59–0.96 log10**, significant for D614G only | 5 isolates, 2 replicates per titration | **B** for supernatant, **C** as a stand-in for a specimen ratio |
| **Despres 2022**, *PNAS*, DOI [10.1073/pnas.2116518119](https://doi.org/10.1073/pnas.2116518119) | **Infectious units per quantity of E-gene RNA** (and per subgenomic E RNA) | **Clinical** swabs, identical kits, processed within days | Alpha, Delta, Epsilon; microfocus-forming assay + RT-PCR | "**A high degree of variation** in the relationship between viral titers and RNA levels." Delta and Epsilon carry **5.9×** and **3.0×** more infectious units per E-gene copy than Alpha (P < 0.0001, P = 0.014); **14.3×** and **6.9×** on subgenomic E | 162 samples | **B** — measures the *ratio's variability and variant dependence*, not a single ratio |
| **Puhach 2022**, *Nat Med*, DOI [10.1038/s41591-022-01816-0](https://doi.org/10.1038/s41591-022-01816-0) | Paired genome copies and infectious titre (FFU/mL) | **Nasopharyngeal swabs**, first 5 days post onset, Ct < 27 only | pre-VOC, Delta, Omicron BA.1; vaccinated and unvaccinated; focus-forming assay | **No usable conversion**: copies-vs-FFU correlation is **R² = 0.15** (pre-VOC), 0.31 / 0.40 (Delta unvacc./vacc.), 0.36 / 0.31 (Omicron unvacc./vacc.) | 565 samples | **B** — a direct refutation of a fixed ratio in clinical specimens |
| **Porter 2025**, *Access Microbiol*, DOI [10.1099/acmi.0.000732.v3](https://doi.org/10.1099/acmi.0.000732.v3) | RNA load vs culturable titre, longitudinally in one host | Nasal and saliva, daily | Omicron-era | The RNA-to-culturable-titre relationship moves by **> 5 orders of magnitude across one infection course** | n = 1 | **C** |
| **Huang 2020**, *J Clin Microbiol*, DOI [10.1128/jcm.01068-20](https://doi.org/10.1128/jcm.01068-20) | Lowest copy number at which isolation succeeded — a **threshold**, not a ratio | Throat, NP, sputum | Ancestral; Vero E6 culture | **5.4 / 6.0 / 5.7 log10 copies/mL** for nsp12 / E / N targets | 60 RNA-positive specimens | **B** for the threshold; **not** a conversion factor |

### 4.2 What the four independent studies agree and disagree about

They agree on the **magnitude and the setting split**, which is the part worth
carrying:

- **Propagated culture supernatant: ~10³·⁵ – 10⁴·⁵ copies per infectious unit.**
  Zapata-Cardona's five isolates (2.95 × 10³ – 2.98 × 10⁴) and Lin's incidental
  "~10,000:1 for the more homogeneous virus harvested from culture" are separate
  labs, separate assays, and land on the same decade.
- **Clinical respiratory specimens: ~1 to 1.5 logs higher.** Lin's specimen
  distribution centres on 10⁵·² with a 1.0-log SD. Both papers attribute the gap
  to non-infectious genome copies — free RNA, defective particles, neutralised
  virions — that culture supernatant does not carry in the same proportion.

They disagree about whether a **single number** exists at all, and the studies
designed to answer that say no: Puhach's R² of 0.15–0.40 in 565 paired
measurements, Despres's variant-dependent 3–6× (14× on subgenomic RNA), and
Porter's >5-log within-host swing are three independent refutations of a fixed
conversion factor. Lin's own caveat is in the same direction — the ratio "makes
assumptions about the efficiency of RNA extraction, PCR amplification, and
plating".

## 5. Rejected candidates, with the reason

Recorded so the next person does not re-find them and read the omission as an
oversight.

**Circular — fitted to attack-rate data (the trap this unit exists to avoid):**

| Candidate | Reason |
|---|---|
| Prentiss 2022, ID50 361–2,000 particles | Inferred by fitting a transmission model to **high-attack-rate superspreading events**. Adopting it and then scoring on Diamond Princess attack rates fits a physical constant to a scored anchor. Already rejected in [tranche 9](mql_tranche_9_sars_cov2.md); re-rejected here on the same grounds, not re-litigated |
| Riediker 2022, 500 / 300 / 100 copies (WT / Delta / Omicron) | Same defect — model output calibrated against observed transmission, not a measurement |
| Marc 2021, *eLife*, DOI [10.7554/elife.69302](https://doi.org/10.7554/elife.69302) | Maps viral load to **transmission probability** by fitting to contact-tracing/transmission-pair data. It is the same circularity in a different vocabulary, and its output is a probability, not a dose |
| Iyaniwura 2024, *PNAS*, DOI [10.1073/pnas.2406303121](https://doi.org/10.1073/pnas.2406303121) | Within-host model fitted to the Killingley data. Its infectious-virus-to-load power law (`h < 1`) is an inferred relationship, not a measured conversion, and it is fitted to the same 18 hosts whose dose we are trying to interpret |
| Xu 2025, *Epidemics*, DOI [10.1016/j.epidem.2025.100843](https://doi.org/10.1016/j.epidem.2025.100843) | New dose-response model fitted to Killingley by ABC-SMC. **Also a unit warning:** it states the 10 TCID50 inoculum as "approximately 55 PFU", where item #30's working note carries ~7 PFU. Both are conversions, neither is measured here, and they differ by ~8×. Do not treat either as the TCID50→PFU step |

**Preprints superseded by their own peer-reviewed versions** (the published
version was used instead; the preprint is not double-counted):

| Preprint | Superseded by |
|---|---|
| Lin 2021, medRxiv `10.1101/2021.07.08.21259744` | Lin 2022, *Sci Rep* — and note the ratio statement **changed**: the preprint abstract says "~10⁵ copies of N gene per PFU", the published Results and Fig. 8a give the fitted distribution, mean 10⁵·² ± 1.0 SD. §4.1 uses the published figure |
| Despres 2021, medRxiv `10.1101/2021.09.07.21263229` (n = 165, 6× and 11×) | Despres 2022, *PNAS* (n = 162, 5.9× and 14.3×) |
| Meyer 2022, medRxiv `10.1101/2022.01.10.22269010` | Puhach 2022, *Nat Med* |
| Killingley 2022, Research Square `10.21203/rs.3.rs-1121993/v1` | Killingley 2022, *Nat Med* |
| Jackson 2023, *Thorax* abstract, DOI [10.1136/thorax-2023-btsabstracts.115](https://doi.org/10.1136/thorax-2023-btsabstracts.115); Mann 2022 congress abstract | Jackson 2024, *Lancet Microbe*; Killingley 2022, *Nat Med* |

**Wrong quantity — does not measure a copies-per-infectious-unit ratio:**

| Candidate | Reason |
|---|---|
| Jones 2021, *Science*, DOI [10.1126/science.abi5273](https://doi.org/10.1126/science.abi5273) | Estimates **cell-culture isolation probability** against viral load (peak 0.75 at 10⁸·¹ copies/swab, 25,381 cases). A probability of isolation is not a number of copies per infectious unit |
| Fomenko 2022, *Rev Med Virol*, DOI [10.1002/rmv.2342](https://doi.org/10.1002/rmv.2342) | Meta-analysis of RT-PCR-vs-culture positive predictive value across 55 studies. Secondary, and again a probability |
| Ke 2022, *Nat Microbiol*, DOI [10.1038/s41564-022-01105-z](https://doi.org/10.1038/s41564-022-01105-z) | Daily paired RNA and infectious-virus sampling in 60 people, but the reported quantities are model-fitted expansion/clearance rates and an "infectiousness" summary, not a conversion factor |
| Viloria Winnett 2023, *PNAS Nexus*, DOI [10.1093/pnasnexus/pgad033](https://doi.org/10.1093/pnasnexus/pgad033) | Measures up to 10⁹ copies/mL differences **between specimen types in the same person** — decisive context for why one ratio cannot serve all specimens, but not itself a ratio |
| Yang 2023, *Anal Bioanal Chem*, DOI [10.1007/s00216-023-04855-9](https://doi.org/10.1007/s00216-023-04855-9); Craig 2022, *Viruses*, DOI [10.3390/v14030508](https://doi.org/10.3390/v14030508) | Assay-development papers calibrating sgRNA/gRNA copy number against titre of a **cultured Delta stock** (Yang: linear over 500–10⁵ TCID50/mL) or reporting a detection limit in TCID50 equivalents. They calibrate an assay against one lab's stock; neither reports a specimen ratio with dispersion |
| Brandolini 2021, *Viruses*, DOI [10.3390/v13061022](https://doi.org/10.3390/v13061022) | Explicitly builds a Ct → copies → TCID50/mL converter from a serially diluted stock, so it is the right *shape* of measurement — but the fetched full text yielded only figure legends, and the numeric conversion could not be read out of the Results. **Recorded as unverified and deliberately not used in §6**; a reader with PDF access should check it, as it would be a second supernatant-side anchor |
| Osterman 2022, de Michelena 2022, Mizoguchi 2021, Elie 2022, Lu 2020, Scutari 2023, van Kampen 2021, Yu 2020, Pan 2020, Walsh 2020, Kirby 2022, Takemae 2024, Johnson 2022, Zhou 2023, Wagstaffe 2024 | Returned by queries 1–8 and read; all measure viral load, assay sensitivity, isolation windows, emissions or immunology. None reports a copies-per-infectious-unit ratio or a non-fitted dose |
| Seyedalinaghi 2022, *SAGE Open Med*, DOI [10.1177/20503121221115053](https://doi.org/10.1177/20503121221115053) | Systematic review of "minimum infective dose". Secondary, and it aggregates the same primary sources plus modelled estimates without a copy-unit measurement |
| Blaurock 2022's claim that the hamster MID "equals the estimated MID for humans" | The hamster MID **is** measured (§3); the human equivalence is an inference in the discussion, not a measurement, and it inherits whatever human estimate it cites |
| Imai 2020, Handley 2023 | Hamster models with fixed challenge doses (and, in Handley, a demonstration that **inoculum volume** shifts severity as much as a 500-fold dose change). No ID50; Handley is strong evidence that animal dose figures are not portable |

## 6. What the evidence supports

### 6.1 Object 1: null

**No SARS-CoV-2 ID50 in genome copies exists in the peer-reviewed literature,
derived independently of attack-rate fitting or otherwise.** Every non-circular
dose measurement is in infectious units. The register's existing statement of the
denominator as "Killingley → ID50 ≈ 9.2 TCID50 ≈ 10³–10⁴ copies" therefore rests
on an unsourced conversion, and §6.3 is the first measured constraint on that
conversion.

### 6.2 Object 2: an interval, and it is wide

Copies per infectious unit, **reported by setting because the settings differ
systematically**, not averaged:

| Setting | Interval | Basis | Grade |
|---|---|---|---|
| **Clinical respiratory specimens** (per PFU, N gene) | **10⁴·² – 10⁶·²** copies/PFU (mean 10⁵·², ±1 SD) | Lin 2022, 151 infectious specimens | **B** |
| **Propagated culture supernatant** (per PFU, E gene) | **10³·⁵ – 10⁴·⁵** copies/PFU (2.95 × 10³ – 2.98 × 10⁴) | Zapata-Cardona 2022, 5 variants; corroborated by Lin's ~10⁴:1 remark | **B** |
| **Combined honest bound** | **≈ 3 × 10³ – 1.6 × 10⁶ copies per infectious unit**, i.e. **~2.7 logs** | the two rows above | **B**, as an interval only |

**No central value is proposed.** A single number would be false precision three
times over: the specimen-matrix split is ~1–1.5 logs, the variant spread is 3–14×
(Zapata-Cardona, Despres), and the within-host trajectory moves the ratio by >5
logs (Porter) while the paired-sample correlation is R² ≤ 0.40 (Puhach).

### 6.3 The one implication that follows without composing anything

The register's parenthetical "≈ 10³–10⁴ copies" for Killingley's 10 TCID50
implies **~10²–10³ copies per TCID50**. That is **below every measured ratio in
§4.1**, by one to three logs, and below them for both settings. This is stated as
a provenance observation about an existing unsourced conversion, not as a
correction of the sweep: the sweep endpoints are the lead's, and nothing here was
compared against an anchor.

### 6.4 What composition would cost, if the lead chooses to do it

Not performed here. If it is attempted, it needs **three** steps, each with its
own measured spread, and they multiply:

1. Killingley's dose in TCID50 → PFU. Measured offset **0.59–0.96 log10**,
   variant-dependent and significant for only one of five isolates
   (Zapata-Cardona). Published conversions of this exact inoculum disagree by ~8×
   (~7 PFU in item #30's note vs "≈ 55 PFU" in Xu 2025), and neither is measured.
2. PFU → genome copies. **~2.7 logs** (§6.2), and the choice of *which* setting's
   ratio applies to an inoculum drawn from culture but delivered to a nose is
   itself unmeasured.
3. A 53%-infection point at one dose level → an ID50 and a slope. One dose level
   cannot identify a two-parameter dose-response; Jackson 2024 shows the slope is
   not even a virus property once hosts are immune.

The composed uncertainty is therefore **wider than 3 logs**, i.e. wider than the
`10³–7 × 10⁵` sweep the register already carries. That is the honest reading, and
it is why this unit reports two ingredients rather than a product.

## 7. Definition problems the field cannot express as the model needs it

1. **The model's denominator is a constant; the measured ratio is not a
   constant.** `beta` is one number per pathogen. The literature's best-designed
   attempts to measure copies-per-infectious-unit report a *distribution* whose
   width is driven by specimen matrix, variant, day of infection and host
   immunity — three of which the model varies internally and one of which it
   fixes by profile.
2. **"Infectious unit" is not one unit.** PFU, TCID50 and FFU are different
   assays on different cell lines with different endpoints; the PFU↔TCID50 offset
   is itself measured at 0.59–0.96 log10 and is variant-dependent. Every ratio in
   §4.1 is a ratio to a *particular* assay.
3. **The inhaled dose and the assayed specimen are different objects.** All ratios
   are measured in swabs, saliva, sputum or supernatant; the model's dose is
   copies inhaled from a room reservoir or transferred by contact. Nothing
   measures the copies-per-infectious-unit of aerosolised, partly desiccated,
   room-aged virus, which is the material the airborne path actually delivers.
4. **The naive-host dose-response may not be the shipboard quantity at all.**
   Killingley is the only naive human dose point; Jackson 2024 shows five logs of
   dose failing in seropositive adults. A ship population is mostly not naive, so
   a single `beta` is standing in for a host-immunity distribution.

## 8. The nulls, stated plainly

- **No ID50 for SARS-CoV-2 in genome copies, from any design, circular or not.**
- **No measurement of copies per TCID50 in a respiratory specimen.** The
  specimen-side ratio that exists is per **PFU** (Lin 2022); the TCID50-side work
  is on culture stocks (Zapata-Cardona, and the unverified Brandolini).
- **No characterisation of the Killingley challenge inoculum in genome copies**,
  which query 8 was written to find and which would have answered object 1
  directly.
- **No fixed conversion factor exists in clinical specimens**, and this is a
  positive finding rather than a gap: Puhach (n = 565), Despres (n = 162) and
  Porter (longitudinal) each measured the relationship and each found it
  variable.
