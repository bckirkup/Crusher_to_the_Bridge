# Tranche 38 — the release term is an event chain with four measured factors, and the chair background is a literature null

**Register rows fed / supersession.** Feeds the open ledger's §4 item 00 (the
dose scale governs the box). It **supersedes nothing**, **withdraws no
measurement**, **moves no constant and adopts none**. Nothing here narrows
`environmental_faecal_release_log10_g_per_epoch`; the tranche assembles the
factors that would *replace* it and records where the chain is measured, where
it is surrogate, and where it is empty.

**Status:** Evidence assembled and interpreted. Nothing implemented. The
event-structured release model this licenses is not designed here and is not
approved.

**Scope.** Four questions, in the order they were asked:

1. Has anyone normalised **crAssphage or another human faecal marker** onto
   built-environment seating — copies per cm², per contact, or per hour?
2. Is there **source-contribution microbiome data for chairs** (classrooms and
   similar), and does it report an absolute load or only a community fraction?
3. What does the **seeded-toilet** literature measure, on what denominator?
4. What is the **mass of a defecation event**, and does the record give a
   diarrhoeal arm?

**Result in one line.** The two "background deposition onto a chair" questions
are **null**: crAssphage is quantified only in water (copies/100 mL of sewage,
river, beach), and every built-environment chair study is 16S — relative
abundance and source *fractions*, with no mass, copies or cells per unit area.
The **toilet event** channel, by contrast, is measured on exactly the right
denominator by two seeded-flush studies (**log10 PFU per 100 cm²** against a
known bowl load) and closed at the other end by **Rose 2015's 128 g/cap/day
over 1.20 defecations/day**. Composing those factors gives a release envelope
about **five orders of magnitude wide**, against the twenty the current box
sweeps — and it straddles the `adj ≈ 6–7` switch rather than sitting on one
side of it.

---

## 1. crAssphage on surfaces (question 1) — ∅ null, and the field is elsewhere

Two differently phrased retrievals (crAssphage deposition per surface area /
per contact; human faecal marker on built-environment fomites) returned a
water-quality literature and nothing else. What exists, with its denominator:

| Study | Matrix | Quantity, as reported | Origin |
|---|---|---|---|
| Stachler et al. 2017, *Environ Sci Technol*, [10.1021/acs.est.7b02703](https://doi.org/10.1021/acs.est.7b02703) | Primary influent sewage | CPQ_056 / CPQ_064 qPCR; **1.49–3.37 log10 copies/ng total DNA**; assay range 10^1–10^5 copies/reaction | R, Me |
| Stachler et al. 2018, [10.1021/acs.est.8b00638](https://doi.org/10.1021/acs.est.8b00638) | Surface water | **4.02–6.04 log10 copies/100 mL** | R |
| Li et al. 2023, *Sci Total Environ*, [10.1016/j.scitotenv.2023.168840](https://doi.org/10.1016/j.scitotenv.2023.168840) | Rivers, beaches | **1.45–5.14 log10 copies/100 mL** | R |
| Ahmed et al. 2022, *Water Res*, [10.1016/j.watres.2022.119093](https://doi.org/10.1016/j.watres.2022.119093) | Untreated wastewater | Marker copies vs pathogenic virus copies, same matrix | R |

**Verdict: ∅ genuine null for the quantity asked for.** The marker is a
water-pollution tracer; its denominator is volume, and no volume-normalised
concentration converts to a surface deposition rate without the very transfer
term we lack. This is not `?nr` — the field has a large, consistent,
well-indexed literature, and the surface arm is absent from it.

## 2. Chairs in classrooms (question 2) — the study exists, and it is relative

**Meadow JF, Bateman AC, Herkert KM, O'Connor TK, Green JL (2014).** *Bacterial
communities on classroom surfaces vary with human contact.* Microbiome 2:7,
[10.1186/2049-2618-2-7](https://doi.org/10.1186/2049-2618-2-7). This is the
chair study: one University of Oregon classroom, **chair seats n = 18**, desks
18, floors 18, walls 16, each a **289 cm² (17 × 17 cm) swab** of the centre of
the upholstered seat, 16S rRNA, compared against public source datasets.

Its chair finding is specifically the one asked about — chair seats are
indicated by **gut-associated** taxa where desks are indicated by skin and oral
taxa (Table 1, all P ≤ 0.019):

| Indicator genus | Surface | Closest isolate | Isolate source | P |
|---|---|---|---|---|
| *Lactobacillus* | Chairs | *L. johnsonii* NR_075064.1 | **Human gut** | 0.001 |
| *Corynebacterium* | Chairs | *C. riegelii* NR_026434.1 | Human urinary tract | 0.001 |
| *Staphylococcus* | Chairs | *S. saprophyticus* NR_074999.1 | Human urinary tract | 0.019 |
| *Staphylococcus* | Chairs | *S. epidermidis* NR_074995.1 | Human skin | 0.011 |

**What it does not report:** any absolute quantity. No cells/cm², no copies/cm²,
no deposition per occupancy-hour, no viability, no viral target. Indicator
analysis and relative abundance cannot be converted into a mass flux, because
the sequencing denominator is *reads in this sample*, not *material on this
chair*. The same is true of the companions retrieved beside it:

- **Ye et al. 2024**, *Ecotox Environ Saf*,
  [10.1016/j.ecoenv.2024.116632](https://doi.org/10.1016/j.ecoenv.2024.116632)
  — university cafeterias, classrooms, dormitories, offices, restrooms; FEAST
  source tracking assigns **59–86% of bacterial sources**, human skin largest
  for most building types. **Source fractions, not loads.**
- **Flores et al. 2011**, *PLoS ONE*,
  [10.1371/journal.pone.0028132](https://doi.org/10.1371/journal.pone.0028132)
  — restroom biogeography; SourceTracker puts skin first and **gut important on
  and around the toilet**. Relative.
- **Lee et al. 2021**, *Indoor Air*,
  [10.1111/ina.12825](https://doi.org/10.1111/ina.12825) — classroom **air**;
  qPCR of total bacterial DNA is quantified, but the target is total bacteria in
  air, not faecal material on seating.

**The one partial exception, and it is a rate rather than a level.** **Kwan et
al. 2018**, *J Appl Microbiol*,
[10.1111/jam.13898](https://doi.org/10.1111/jam.13898), quantified ten school
**desk** surfaces by qPCR through a cleaning intervention: cleaning removed
**~50% of bacteria, fungi and human cells**, and the surface concentrations
**fully recovered in 2–5 days**; the dominant source at every time point was the
human microbiome (skin, oral, **gut**). That licenses a statement about the
*turnover* of a background surface community — a background that re-establishes
on a 2–5 day timescale after a 0.3 log removal — and it licenses nothing about
its magnitude in faecal grams, its viral content, or its infectivity.

**Verdict: the user's recollection is correct and the data are bacterial-only
and relative.** For the model's purpose this is **∅ for a level, ⊂ for a
timescale**, and it may not be dressed as either a deposition constant or a
crAssphage proxy.

## 3. The toilet event (question 3) — measured, surrogate, and on the right denominator

### 3.1 Goforth et al. 2023

*Impacts of lid closure during toilet flushing and of toilet bowl cleaning on
viral contamination of surfaces in United States restrooms.* Am J Infect
Control, [10.1016/j.ajic.2023.11.020](https://doi.org/10.1016/j.ajic.2023.11.020).
MS2 seeded into the bowl, flushed, surfaces sampled over **100 cm²**
(Table 1 and the floor/wall table, Origin **T1**; `*` = MS2 in the 2.8 L bowl
volume, `**` = MS2 per 100 cm² of sampled surface, all log10 PFU):

| Condition (bowl dose) | Bowl water* | Lid top** | Lid bottom** | Seat top** | Seat bottom** |
|---|---|---|---|---|---|
| Home, lid down (10^10) | 10.57 | 1.66 | 1.70 | 5.39 | 4.22 |
| Home, lid up (10^14) | 14.12 | 1.70 | 1.70 | 6.80 | 7.85 |
| Home, lid down (10^14) | 14.41 | 1.72 | 1.65 | 5.62 | 7.26 |
| Public, no lid (10^11) | 11.16 | NA | NA | 7.51 | 7.26 |

| Condition | Bowl water* | Floor L** | Floor R** | Floor front** | Wall R** | Wall L** |
|---|---|---|---|---|---|---|
| Lid up (10^14) | 11.02 | 3.64 | 6.23 | 4.25 | 1.77 | 2.31 |
| Lid down (10^14) | 11.23 | 5.11 | 4.81 | 5.17 | 1.86 | 1.61 |

Read as **deposition fraction of bowl load per 100 cm² per flush** (surface
minus bowl, in log10):

- seat top and bottom: **10^−3.7 to 10^−8.8**, public flushometer at the top of
  that range (−3.7 / −3.9), home siphonic toilets 1–5 logs below it;
- floor: **10^−4.8 to 10^−7.4**; wall and lid: **10^−9** and below.

**Three caveats that stay attached to those numbers.** (i) The fraction is
**not stable in dose**: the same home toilet gives −5.2 at a 10^10 load and
−8.8 at 10^14, which a linear deposition process cannot do, so recovery
efficiency, assay range or bowl carry-over is doing part of the work. (ii) The
dispersions as printed (`5.39 ± 5.75`, `10.57 ± 10.4`) cannot be standard
deviations of the log10 means they sit beside; the table's spread is **not
interpretable as published**, and the ordering is the usable content. (iii)
Lid position did not change contamination, so a "lid down" mitigation is not
available as a lever.

### 3.2 Sassi et al. 2018

*Evaluation of hospital-grade disinfectants on viral deposition on surfaces
after toilet flushing.* Am J Infect Control,
[10.1016/j.ajic.2017.11.005](https://doi.org/10.1016/j.ajic.2017.11.005).
~10^12 PFU MS2 in 1 L broth into a 2.8 L bowl; **sponge-stick over 100 cm²**
(flush handles 90 cm²); **LOD 1 PFU/100 cm²**. Toilet rim, seat top and seat
underside contaminated in **100%** of no-disinfectant trials. At a **10^6 PFU**
bowl load **nothing was detectable on any surrounding surface** — which is a
bound rather than a null: it puts the seat deposition fraction **below ~10^−6
per 100 cm²** for that toilet, consistent with the home-toilet end of Goforth's
range and inconsistent with the public-toilet end.

### 3.3 Boles et al. 2021

*Determination of murine norovirus aerosol concentration during toilet
flushing.* Sci Rep,
[10.1038/s41598-021-02938-0](https://doi.org/10.1038/s41598-021-02938-0).
MNV as the human-norovirus surrogate; seeded bowl **2.18 × 10^5 – 9.65 × 10^6**
RNA copies in the collected samples, airborne **383–684 RNA copies/m³**; uses
**107 g of waste per defecation** into a **3.1 L** bowl, citing Rose 2015. The
authors state the estimate is surrogate and seeded and that further data are
required. This is the **aerosol** half of the same event, and it is the arm that
would feed the emesis-pool near field rather than the seat fomite pool.

**Grade for §3 as a whole: B-minus, surrogate.** MS2 and MNV are not human
norovirus; PFU is not genome copies; a seeded broth bolus is not stool. The
**denominator** (per 100 cm², per flush, against a known bowl load) is exactly
what the model needs, and the **magnitude** carries a surrogate conversion that
this tranche does not attempt.

## 4. Mass per event (question 4) — measured, skewed, and with no adult diarrhoeal arm

**Rose C, Parker A, Jefferson B, Cartmell E (2015).** *The characterization of
feces and urine: a review of the literature to inform advanced treatment
technology.* Crit Rev Environ Sci Technol,
[10.1080/10643389.2014.1000761](https://doi.org/10.1080/10643389.2014.1000761).
Grade **A** for the general-population quantity, Origin **Ab + Conclusions**:

- median faecal **wet mass 128 g/cap/day**, dry mass **29 g/cap/day**;
- **1.20 defecations per 24 h** in healthy individuals → **~107 g/event**,
  which is where Boles's figure comes from;
- feces **74.6% water**, median pH 6.64;
- wet mass **×2 in low-income (high-fibre) populations** versus high-income —
  so a cruise population sits at the **lower** end, and 128 g/day is a
  high-fibre-weighted median, not a Western one;
- the review states explicitly that the **data sets were highly skewed** and
  cautions against the central tendency. That is the long tail, in the source.

**The diarrhoeal arm is not retrieved for adults.** Two differently phrased
searches for measured 24 h stool output in acute infectious diarrhoea returned
a paediatric prediction study (**Lembcke et al. 1989**,
[10.1097/00005176-198911000-00013](https://doi.org/10.1097/00005176-198911000-00013),
which brackets severity at **>50 and >100 g/kg/day** in 3–36-month-old boys) and
a critical-care dose-response study, neither of which gives an adult
norovirus-illness mass per event. Recorded as **`?nr` pending a third phrasing**,
not as a literature null. The existing diarrhoeal **event-rate** arm
([tranche 32](consensus_tranche_32_stool_event_frequency.md), **[3.0, 8.5]/day**,
Grade C, swept) stands and is unaffected.

## 5. What the four factors compose to

Written as a chain, with each factor's own grade — and **as an envelope, not a
value**:

```
release  =  titre (log10 gc/g, existing shedding curve, Grade A)
          × stool mass per event (Rose 2015: ~107 g median, skewed, Grade A)
          × deposition fraction per 100 cm² per flush (Goforth/Sassi:
            10^-3.7 .. 10^-8.8 on seats, Grade B-minus surrogate)
          × event rate per day (tranche 32: 0.43-3.0 well, 3.0-8.5 ill)
          + background surface deposition  (∅ null — §2)
```

In the model's own units, where `adj` is `−log10` of grams released per epoch,
the **grams-equivalent** deposited on a seat-sized surface per event is
`107 g × 10^−3.7..−8.8 = 10^−1.7 .. 10^−6.8 g`, and at 1.2–8.5 events/day
spread over a 1 h epoch grid this is an **`adj`-equivalent of roughly 3 to 8**.

Three things follow, and only these three:

1. The evidence-composed envelope is about **five logs wide**, against the
   **twenty** the current factor box sweeps. Four of the five logs are the
   surrogate deposition fraction; the biology contributes the least spread.
2. The envelope **straddles the `adj ≈ 6–7` switch** recorded in ledger §1 —
   it does not sit on one side of it. So the switch is inside the evidence, and
   a campaign stratified by regime is testing something the record admits, not
   an artefact.
3. The composition is **not yet a parameter**, because of a denominator
   mismatch that must be closed first: Goforth's denominator is a **100 cm²
   swab of a seat**, and the model's fomite pool has its own declared area and
   its own contact/transfer terms. Substituting one for the other without
   reconciling the areas would repeat the recurring defect archetype in a new
   place.

## 6. What this tranche refuses

- **No value is adopted** for `environmental_faecal_release_log10_g_per_epoch`,
  and the [4, 24] interval is **not narrowed** here. Narrowing it on the
  strength of §5 would be adopting a surrogate PFU deposition fraction as a
  norovirus genome-copy release fraction.
- **No anchor was consulted.** The five-log envelope was composed before it was
  compared with the switch, and the comparison in §5 item 2 is a report, not a
  selection criterion. That it brackets the switch may not be used to pick a
  point inside it.
- **Relative source fractions may not become deposition rates.** §2's chair
  finding is that gut taxa are indicators of chair seats. It is not evidence
  that a measurable mass of faecal material is deposited on a chair, and it may
  not be cited for the background term.
- **Surrogates keep their labels.** MS2 PFU, MNV RNA copies, 16S reads,
  crAssphage copies/100 mL and stool grams are five different quantities in
  this tranche and none of them is converted into another.
