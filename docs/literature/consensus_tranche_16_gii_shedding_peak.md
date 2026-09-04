# Tranche 16 — the GII faecal shedding time course: measured, but not where the model reads it


**Register rows fed / supersession.** This tranche feeds the GII faecal shedding time-course, peak, time-to-peak, decline-shape and asymptomatic-offset rows in §3.1. The explanation that Teunis 2015 values were digitized because publishers' Results sections were unreachable is superseded for Teunis 2015: its body is chunk-indexed, though the specific medians were absent from what it returned — the digitization itself stands (tranche 21 §3.3).

**Status:** Evidence assembled. **No profile constant, engine constant, curve
entry or register row changes in this document.** Nothing here is adopted; the
register contribution is the fragment
[`fragments/gii-shedding-peak.md`](fragments/gii-shedding-peak.md), which the
lead merges. Literature documents are context, not model truth
([`docs/AGENTS.md`](../AGENTS.md) rule 3).

**Scope:** unit `gii-shedding-peak`, task **#47** — the norovirus faecal
shedding time course for **genogroup II**: peak titre in genome copies per gram
of stool, time from inoculation or onset to peak, and the shape and duration of
the decline, with symptomatic and asymptomatic subjects separated wherever the
paper separates them. The model reads a 15-entry day-indexed
`shedding_curve_log10` with separate symptomatic and asymptomatic variants, and
since PR #382 `shedding_duration_days` is a separate field from the illness
clock, so a shedding duration far longer than the 1–3 day illness is expected
rather than anomalous.

**The mismatch this unit addresses.** The shipped curve's peak magnitude,
11.0 log10 copies/g, is Atmar 2008's **GI.1** (Norwalk) median peak, while the
active arm is declared **GII** — recorded in
[the register](../parameter_provenance_register.md) §3.1 as a known defect
(`I → M, and mis-genogrouped`, state ⊘ joint). This unit gathers the GII
evidence. It does not fix the curve, does not propose a GI→GII correction
factor (the genogroup difference in titre trades off directly against the
dose-response axis, and a previously proposed 3.7× genogroup ratio in this
project turned out to be a unit error), and does not recommend a single central
value.

**Method:** Consensus MCP `search`, unfiltered on every pass — no `year_min`,
`controlled`, `study_types`, `sample_size_min` or `exclude_preprints` filter was
used on any query in §1, so the recall below is the unfiltered recall.
Truncated result sets were read from the overflow files rather than from the
visible head of the list; five of the papers that carry the actual numbers
ranked between 10th and 20th. Where the number mattered, full text was pursued
beyond the abstract; §5 records which full texts could **not** be reached, and
what remains unestablished as a result.

---

## 1. Queries, verbatim

All unfiltered, `tool_name="search"`, argument `query` only:

1. `norovirus GII faecal shedding peak viral load genome copies per gram stool time course`
2. `GII.4 norovirus human challenge study quantitative RT-PCR stool viral load peak titre duration`
3. `GII.4 norovirus experimental human infection vaccine challenge fecal virus quantity shed genome equivalents per gram`
4. `asymptomatic norovirus GII infection stool viral load compared with symptomatic community cohort quantitative`
5. `norovirus GII stool viral load kinetics serial samples days after symptom onset time to peak log10 decline per day`
6. `Snow Mountain virus GII.2 controlled human challenge inoculum dose response infection illness stool shedding`

Supplementary, **not** used as evidence of provenance: general web fetches to
obtain the full text of papers already identified through Consensus (Kirby
2014, Lee 2007, Teunis 2014, Rouphael 2022), and the `shedding-hub` public
dataset repository, whose role and limits are stated explicitly in §2.1.

## 2. The GII challenge arm

### 2.1 Kirby 2014 — the only GII challenge with serial quantified stool titres

- **Quantity as the paper defines it:** viral stool titre by strain-specific
  quantitative real-time RT-PCR, in genomic equivalent copies (GEC), for every
  stool passed in the first 7 days post-challenge and representative stools
  through day 35; cumulative shedding computed as titre × stool weight, so the
  titre denominator is **per gram of stool (wet weight)**.
- **Setting/population:** experimental human infection, healthy adults,
  GII.2 Snow Mountain virus (SMV) vs GI.1 Norwalk virus (NV), same challenge
  design and same laboratory.
- **Values reported by the paper itself:** NV titres approximately **2 logs
  higher** than SMV; shedding duration (first to last positive stool) median
  **5 days for SMV vs 17 days for NV** (P = 0.02), both explicitly **minimum**
  estimates because the last available sample was still positive for three NV
  and two SMV subjects; both genogroups shed **up to 3 weeks after resolution
  of symptoms**; SMV produced more symptoms and a higher frequency of painful
  symptoms than NV. Shedding titres and patterns did not correlate with subject
  demographics or clinical course.
- Kirby et al., *Journal of Medical Virology* 2014. DOI
  [10.1002/jmv.23905](https://doi.org/10.1002/jmv.23905). Consensus:
  <https://consensus.app/papers/details/bc459eb2b7635c2a876719711cd2e065/>
- Useful context from this paper's own introduction: **reported faecal titres in
  the literature range 10⁵ – 10¹² GEC/g stool** across nine cited studies, and a
  few studies observe asymptomatic mean loads similar to symptomatic. The spread
  this unit reports is not an artefact of the search; it is the state of the
  field.
- **Evidence grade B** — direct measurement, analogous setting (challenge
  volunteers, not a ship), and GII.2 rather than the GII.4 that dominates
  circulating disease.

**A peak titre with a number attached, and its provenance caveat.** The paper's
own peak-titre values sit in its Results tables and figures, which are behind
the publisher's paywall; the accessible full text stops after Methods (§5).
Per-subject series digitized from this paper's figures are published as
`kirby2014disease` in the public `shedding-hub` dataset repository
(<https://github.com/shedding-hub/shedding-hub/tree/main/data/kirby2014disease>,
unit declared `gc/wet gram`, LOD 1 790 GII / 3 570 GI, reference event
inoculation). Summarising that digitization per subject gives:

| Arm | n subjects | Peak, log10 gc/wet g, median (range) | Day of peak, median (range) | First-to-last positive, median (range) |
|---|---|---|---|---|
| **GII.2 SMV** | 9 | **7.06** (3.63 – 8.92) | **4** (2 – 6) | 5 d (1 – 24) |
| GI.1 NV | 15 | 8.73 (6.47 – 10.10) | 4 (3 – 15) | 16 d (2 – 26) |

These are **digitized values, not the paper's reported statistics**, and are
recorded here as indicative only; the ~1.7 log gap they show is consistent with
the paper's stated "approximately 2 logs", and the durations reproduce the
paper's 5 vs 17 day medians only loosely because digitization recovers a subset
of samples. Two further things follow, and both matter more than the numbers:

1. The digitized GI.1 median peak, 8.73 log10, is **~2.3 logs below** Atmar
   2008's GI.1 median peak of 10.98 in the same genogroup and the same kind of
   challenge. Whatever the cause — assay calibration, extraction, stool
   weighing — it is of the same magnitude as the genogroup difference this unit
   was asked about. A GI→GII offset taken from Kirby and applied to a peak taken
   from Atmar would be crossing two assays, which is the precise shape of the
   3.7× unit error already recorded in this project.
2. All 9 GII.2 subjects with quantified peaks are flagged symptomatic in the
   digitization, so this study yields **no asymptomatic GII peak**.

### 2.2 The GII.4 challenge literature does not quantify a peak

- **Frenck 2012** (first GII.4 human challenge; 40 adults, 23 secretors / 17
  nonsecretors, 5 × 10⁴ RT-PCR units): stools "evaluated for norovirus by
  RT-PCR", infection defined by detection and/or seroconversion; 16/23 secretors
  infected, 13 ill, illness 1–3 days; **no titre, no time course**.
  *J Infect Dis* 2012. DOI [10.1093/infdis/jis514](https://doi.org/10.1093/infdis/jis514).
- **Rouphael 2022** (GII.2 SMV dose-response, 44 adults, doses 1.2 × 10⁴ –
  1.2 × 10⁷ GEC, ID50 5.1 × 10⁵ GEC): duration of shedding is a registered
  outcome (NCT02473224) but no stool concentration appears in the abstract, and
  the full text was not reachable (§5). *J Infect Dis* 2022.
  DOI [10.1093/infdis/jiac045](https://doi.org/10.1093/infdis/jiac045).
- **Qu 2025** (two SMV inocula compared, 15 + 33 subjects): reports that the
  secondary inoculum gave **longer** shedding and milder illness (severity
  6.00 vs 2.94, P = 0.003); no titres in the abstract. *J Med Virol* 2025.
  DOI [10.1002/jmv.70546](https://doi.org/10.1002/jmv.70546).
- **Bernstein 2014** (GII.4 vaccine challenge): shedding reported as the
  *proportion* positive at day 10 (11/49 vaccinees, 17/47 controls); no titre
  curve. *J Infect Dis* 2014.
  DOI [10.1093/infdis/jiu497](https://doi.org/10.1093/infdis/jiu497).
- **Kirby 2016** (emesis from the GI.1, GII.2 and GII.1 challenge studies): GII
  mean **3.9 × 10⁴ GEC/mL of emesis** vs GI 8.0 × 10⁵ GEC/mL, average
  1.7 × 10⁸ GEC per subject in emesis. *PLoS ONE* 2015.
  DOI [10.1371/journal.pone.0143759](https://doi.org/10.1371/journal.pone.0143759).
  Different material and a **per-mL** denominator: not a stool titre (§4).

**Null result, stated plainly:** no GII.4 human challenge study reports a
quantitative faecal titre time course. The only GII challenge data with serial
stool quantification is GII.2 Snow Mountain.

## 3. Observational GII evidence: shape and decline are measured, peaks are ragged

### 3.1 Serial sampling, GII-specific

| Study | Setting, n | What is measured, in its own units | Grade |
|---|---|---|---|
| **Tu 2008**, *J Clin Microbiol*, DOI [10.1128/JCM.02198-07](https://doi.org/10.1128/JCM.02198-07) | GII outbreak, aged-care facility (NSW); 14 volunteers sampled every 3–7 d from onset to two consecutive negatives | Shedding "peaked in the acute stage of illness"; mean duration **28.7 days**; decay rate **0.76 per day**, half-life **2.5 days**. Digitized series (`shedding-hub` `tu2008norovirus`, `gc/wet gram`, LOD 8 930): 45 quantified samples, observed maximum **9.14 log10**, samples ≤3 d after onset 5.91 – 7.48 log10 | B |
| **Lai 2013**, *J Clin Virol*, DOI [10.1016/j.jcv.2012.10.011](https://doi.org/10.1016/j.jcv.2012.10.011) | GII.4 nursing-home outbreak, 19/42 residents + 12/33 employees | Initial faecal load higher in residents than employees (P = 0.024); reduction rate **0.66/day**, half-life **1.7 days**; excretion duration driven by age, not by initial load or diarrhoea duration. No absolute peak | B |
| **Aoki 2010**, *J Hosp Infect*, DOI [10.1016/j.jhin.2009.12.016](https://doi.org/10.1016/j.jhin.2009.12.016) | 13 subjects (11 elderly in aged-care facilities, 2 healthy adults), 63 follow-up stools | Mean excretion **14.3 d** (9–32, median 13); **all** follow-up samples taken 7–10 d after onset were positive; samples taken 14–18 d after onset divided into groups below and above **10⁴ copies/g**. Digitized (`aoki2010duration`, `gc/wet gram`): observed maximum **7.35 log10**, values ≤5 d post onset 2.70 – 7.35 log10 | B |
| **Cheng 2021**, *Medicine*, DOI [10.1097/MD.0000000000025123](https://doi.org/10.1097/MD.0000000000025123) (already cited in the register for duration) | 77 hospitalised children, GII.4 n=22, GII.4 Sydney n=21, GII.P16-GII.2 n=20, non-GII.4 n=14 | Load **rises days 2–9** from onset, irregular plateau, declines after day 9, most shedding ceased by **day 15**. No numerical peak in the abstract | B |
| **Lee 2021**, *J Microbiol Immunol Infect*, DOI [10.1016/j.jmii.2021.10.006](https://doi.org/10.1016/j.jmii.2021.10.006) | 58 isolates, GII.4 Sydney n=21, GII.P16-GII.2 n=19 | Load increases by **day 3** after onset, declines **days 10–15**, >1 month in one SCID patient; longer shedding with GII.4 Sydney (P < 0.01) and fever (P = 0.03). No numerical peak in the abstract | B |
| **Costantini 2015**, *Clin Infect Dis*, DOI [10.1093/cid/civ747](https://doi.org/10.1093/cid/civ747) | 62 cases, 34 exposed and 18 nonexposed controls, 10 LTCF outbreaks (GII.4 Den Haag/New Orleans/Sydney, one GI.1) | **47% of cases shed ≥21 days**; GII.4 Sydney loads significantly higher than other genotypes; **cases and controls shed similar amounts**. No absolute peak | B |
| **Sabrià 2016**, *J Clin Virol*, DOI [10.1016/j.jcv.2016.07.012](https://doi.org/10.1016/j.jcv.2016.07.012) | Food handlers and healthcare workers in outbreak settings, serial samples; >70% of the 59.1% positive were asymptomatic | Mean load **symptomatic 7.51 ± 1.80 → 5.28 ± 0.76** and **asymptomatic 6.49 ± 1.93 → 4.52 ± 1.45 log10 genome copies/g after 19 days** — i.e. ≈2.2 and ≈2.0 log10 lost over 19 d, ≈0.11 log10/day. Genogroup split not established from the abstract, so the *magnitudes* are genogroup-ambiguous even though the decline is usable | B for the decline, ambiguous for magnitude |

**The decline rate is unit-ambiguous as published.** Tu's pair (0.76 per day,
half-life 2.5 d) and Lai's pair (0.66 per day, half-life 1.7 d) are not
self-consistent under either reading of the rate: a half-life of 2.5 d implies
0.28/day natural-log or 0.12 log10/day, and 0.76 log10/day implies a half-life
of 0.40 d. Neither abstract states the units of the rate, and neither full text
was reachable (§5). Sabrià's ≈0.11 log10/day, computed from two stated means
19 days apart, is the only decline figure here whose units are unambiguous, and
it sits at the *slow* end. Recorded as ambiguous rather than averaged.

### 3.2 Teunis 2014 — measurement and model fit in the same paper, and they differ

The register already cites Teunis 2014 for `shedding_variance_log10` as "peaks
10⁵–10⁹/g". That range is the **fitted** output of a multilevel Bayesian
dynamic model (average peak levels 10⁵–10⁹/g faeces, average durations 8–60
days), not an observed peak, and is **grade C** for that reason. Its
conclusion that asymptomatic shedding is similar to symptomatic, and that
patients shed slightly more and longer than staff but not significantly so, is
a statement about the fit.

The underlying **observations** are GII.4, real-time quantitative RT-PCR
calibrated against a run-off transcript standard, from four nosocomial
outbreaks (one hospital, three nursing homes, The Netherlands; 102 subjects,
230 samples). Summarising the digitized subset published as
`shedding-hub` `teunis2015shedding` (`gc/wet gram`, 161 quantified values):

| Group | n samples | Median log10 gc/wet g | Range | Days covered |
|---|---|---|---|---|
| Symptomatic | 115 | 5.79 | 3.19 – 8.94 | 0 – 43 post onset |
| Asymptomatic | 46 | 5.91 | 3.60 – 8.75 | 0 – 25 post confirmation |

So the *observed* symptomatic and asymptomatic distributions are
indistinguishable in central tendency and in maximum — which is the paper's
finding, arrived at without the model — and the highest single observed value
in 161 samples is 8.94 log10, two logs below the shipped 11.0. Grade B for the
observations (digitized, §5), grade C for the fitted peak range.
Teunis, Sukhrie, Vennema, Bogerman, Beersma, Koopmans, *Epidemiol Infect* 2015;
143(8):1710–1717. DOI
[10.1017/S095026881400274X](https://doi.org/10.1017/S095026881400274X).

### 3.3 Single-specimen GII magnitudes — a different quantity, recorded as such

None of these is a per-subject peak: each is one specimen, usually at
presentation, so the distribution is the distribution of *sampled* loads, not
of maxima. They bound the acute-phase magnitude and nothing more.

| Study | Population, n | Value, exact units | Grade |
|---|---|---|---|
| **Lee 2007**, *Emerg Infect Dis*, DOI [10.3201/eid1309.061535](https://doi.org/10.3201/eid1309.061535) | 40 patients, **GII.4**, mean age 60.4 | Median **8.93 log10 copies cDNA/g stool** (IQR 8.22–10.24); assay LOD 2 × 10⁴ copies of cDNA/g stool; prolonged diarrhoea (>4 d) associated with **+2.11 log10 copies/g** vs limited diarrhoea (P = 0.001). Note the denominator is *cDNA copies* per gram, as the paper states it | B |
| **He 2017**, *J Mol Diagn*, DOI [10.1016/j.jmoldx.2017.06.006](https://doi.org/10.1016/j.jmoldx.2017.06.006) | 234 specimens / 152 cancer patients; 201 GII, 33 GI | GII geometric mean **9.03 ± 1.71 log10 copies/g stool (w/w)** vs GI 7.87 ± 1.49 (OR 3.22, P = 0.009); by severity, mild 7.97 ± 1.55 (n=85), moderate 9.09 ± 1.38 (n=23), severe **10.39 ± 0.91** (n=44) | B, immunocompromised |
| **Ozawa 2007**, *J Clin Microbiol*, DOI [10.1128/JCM.01516-07](https://doi.org/10.1128/JCM.01516-07) | 2 376 specimens, 55 outbreaks + 35 sporadic cases, food handlers | GII mean **3.81 × 10⁸ copies/g stool**; **GII/4 mean 7.96 × 10⁹ copies/g stool**; symptomatic and asymptomatic means similar | B |
| **Barreira 2009**, *J Clin Virol*, DOI [10.1016/j.jcv.2009.11.012](https://doi.org/10.1016/j.jcv.2009.11.012) | 319 children ≤3 y, 229 symptomatic / 90 asymptomatic; 51/52 strains GII | Median **8.39 (symptomatic) vs 7.15 (asymptomatic) log10 copies/g of faecal specimen**, P = 0.011; load lower in rotavirus co-infection (P = 0.0005) | B |
| **Sarmento 2021**, *Viruses*, DOI [10.3390/v13091724](https://doi.org/10.3390/v13091724) | 1 546 AGE stools, Brazil; 89.1% of positives GII | GII median **1.9 × 10⁷ GC/g of stool** vs GI 3.4 × 10⁵ | B |
| **Chaimongkol 2024**, *J Infect Dis*, DOI [10.1093/infdis/jiae440](https://doi.org/10.1093/infdis/jiae440) | Decade of chronic-infection surveillance, NIH Clinical Research Center; immunocompromised patients, GII.4 variants predominant | Chronic shedding **10⁴ – 10¹¹ genome copies/g of stool** | B, chronic/immunocompromised |
| **Dábilla 2017**, DOI [10.1016/j.jcv.2016.12.009](https://doi.org/10.1016/j.jcv.2016.12.009) | 219 hospitalised children, mixed GI/GII | Faeces median **2.69 × 10⁸ GC/g** symptomatic vs **4.32 × 10⁷ GC/g** asymptomatic; nasopharyngeal swabs 2.20 × 10⁷ **GC/mL** — a different denominator, recorded but not comparable | B for stool, mixed genogroup |

### 3.4 The symptomatic : asymptomatic ratio does not converge

The model carries separate symptomatic and asymptomatic curves and the ratio
between them is itself a modelled quantity, so this is reported as found —
contradictions included:

- **No difference:** Ozawa 2007 (food handlers, GII means similar); Teunis 2014
  observations (§3.2, medians 5.79 vs 5.91); Costantini 2015 (cases and
  controls shed similar amounts); Huynen 2013 (DOI
  [10.1016/j.jcv.2013.08.013](https://doi.org/10.1016/j.jcv.2013.08.013);
  418 stools — loads higher in symptomatic for **GI** (P = 0.03) but **not for
  GII**); Newman 2016 (DOI [10.1111/cei.12772](https://doi.org/10.1111/cei.12772);
  26 challenge subjects — symptoms not significantly associated with daily
  titre, shedding duration or cumulative shedding, but **GI.1**).
- **Symptomatic higher, ~0.8–1.2 log10:** Barreira 2009 (1.24 log10, P = 0.011,
  GII); Dábilla 2017 (≈0.8 log10, mixed genogroup); Sabrià 2016 (≈1.0 log10 at
  first sample, mixed genogroup); Parrón 2021 (DOI
  [10.1038/s41598-021-02348-2](https://doi.org/10.1038/s41598-021-02348-2);
  30 LTCF outbreaks, 70% GII — higher loads in symptomatic, P = 0.001, but
  reported as **cycle thresholds**, §4).

Spread from "no difference" to ~1.2 log10, with the sign consistent where a
difference is found. No single ratio is supportable from this set.

## 4. Rejected candidates, with the reason

Kept deliberately, so the next person does not re-find them and read their
absence as an oversight.

| Candidate | Why it cannot serve this quantity |
|---|---|
| **Gustavsson 2017**, DOI [10.1128/JCM.00061-17](https://doi.org/10.1128/JCM.00061-17) (24 GII.4 cases; 16/19 epidemic-strain cases shed >14 d vs 1/5 prior strains) | Samples are **rectal swabs**. Copies per swab is not copies per gram of stool, and the paper states no conversion. Duration finding is usable; magnitude is not |
| **Kirby 2016** emesis titres (GII 3.9 × 10⁴ GEC/mL) | **Per mL of emesis**, not stool. Different material *and* different denominator |
| **Anfruns-Estrada 2020**, DOI [10.3390/v12121369](https://doi.org/10.3390/v12121369) (saliva 3.16 ± 1.08 log10 GC/mL) | Saliva, **per mL** |
| **Shioda 2017**, DOI [10.1093/ofid/ofx131](https://doi.org/10.1093/ofid/ofx131); **Parrón 2021**; **Harris 2019**, DOI [10.1186/s12879-019-3706-z](https://doi.org/10.1186/s12879-019-3706-z) | Report **cycle threshold** as a proxy for load. Ct without the paper's standard curve is not a concentration, and none is given |
| **Teunis 2014** fitted peaks 10⁵–10⁹/g; **Teunis 2020**, DOI [10.1016/j.epidem.2020.100401](https://doi.org/10.1016/j.epidem.2020.100401) | **Model output, grade C.** Teunis 2020 additionally fits infectivity to challenge *and outbreak* data — adopting an emission scale from a fit to attack rates while scoring the model on attack rates is circular. Recorded, not adopted |
| **Ge 2023**, DOI [10.3201/eid2907.230117](https://doi.org/10.3201/eid2907.230117) (total faecal shedding 4.5 × 10¹¹ – 3.4 × 10¹² GEC; time to peak 2.3 → 1.5 d as dose rises) | Bayesian re-analysis (**grade C**) of a **GI.1** challenge. Wrong genogroup, and the peak-time gradient is a fitted quantity. Its own conclusion is that the dose effect on virus load and shedding was *inconclusive* |
| **Nyblade 2024**, DOI [10.3390/v16091432](https://doi.org/10.3390/v16091432) (gnotobiotic pigs, GII) | Animal model. Not a human faecal titre |
| **Miura 2018**, DOI [10.2188/jea.JE20170040](https://doi.org/10.2188/jea.JE20170040) | Measures the asymptomatic **fraction**, not shedding magnitude or its time course |
| **Qiu 2023**, DOI [10.3390/v15071541](https://doi.org/10.3390/v15071541); **Lincetto 2025** (LoewenKIDS birth cohort), DOI [10.1007/s15010-025-02670-1](https://doi.org/10.1007/s15010-025-02670-1); **Cannon 2026**, DOI [10.1542/peds.2025-072461](https://doi.org/10.1542/peds.2025-072461); **Kobayashi 2021**, DOI [10.1016/j.cmi.2021.06.004](https://doi.org/10.1016/j.cmi.2021.06.004) and **2022**, DOI [10.1080/23744235.2022.2134447](https://doi.org/10.1080/23744235.2022.2134447); **Mans 2019**, DOI [10.3390/v11040341](https://doi.org/10.3390/v11040341); **Kabue 2016**, DOI [10.1016/j.jcv.2016.09.005](https://doi.org/10.1016/j.jcv.2016.09.005) | Prevalence, comparative-detection or duration-only designs; no GII stool concentration in copies/g with a time course. Kabue 2016 separates symptomatic and asymptomatic children but the abstract gives neither values nor timing |
| **Atmar 2008**, DOI [10.3201/eid1410.080117](https://doi.org/10.3201/eid1410.080117) (median peak 95 × 10⁹ copies/g, range 0.5–1 640 × 10⁹, n=16; shedding median 28 d, 13–56) | **GI.1.** This is the source of the shipped 11.0 and is exactly the mis-genogrouping this unit documents. Reported here as the comparison, not as GII evidence |

## 5. What could not be established, and null results

1. **No grade A evidence exists for this quantity.** No study measures GII
   faecal titre in the target setting (a cruise ship). B is the ceiling.
2. **No GII.4 challenge study quantifies a stool titre time course** (§2.2). The
   only GII challenge with serial quantification is GII.2 Snow Mountain, a
   genotype that is not the pandemic GII.4.
3. **No prospective community cohort with serial GII quantification in copies/g
   was found.** The community and cohort designs recovered (LoewenKIDS, IID2,
   Kobayashi's matched healthy-adult cohorts, Cannon's US infant surveillance)
   report detection, genotype, Ct or symptom association, not per-subject
   quantified peaks.
4. **Paywalled Results, so paper-reported numbers unobtained:** Kirby 2014
   (only the front matter and Methods were reachable; the peak-titre tables were
   not), Rouphael 2022, Tu 2008, Lai 2013, Sabrià 2016, Barreira 2009. Every
   value attributed to those papers above is quoted from the abstract or, where
   marked, from the third-party `shedding-hub` digitization of their figures.
5. **Digitization caveat.** All values marked "digitized" come from
   `shedding-hub`, a public dataset repository, not from the papers' own tables.
   They are recorded because they are the only per-subject GII series available
   at all, and they are flagged everywhere they appear. A register adoption
   should not rest on them without the publisher full texts.
6. **The published decline rates are not usable as stated** (§3.1): Tu's and
   Lai's rate/half-life pairs are mutually inconsistent under any single unit
   convention, and neither states the units.
7. **The symptomatic : asymptomatic ratio is not resolvable** from this
   literature (§3.4).

## 6. What the evidence supports, stated as an interval, and why it is still not adoptable

Assembling only the GII measurements with an unambiguous **copies (or genome
equivalents) per gram of stool** denominator:

- **Per-subject peak, symptomatic GII, immunocompetent:** the observed envelope
  runs from **7.0** (Kirby GII.2 challenge, digitized median) to **9.1** (Tu
  2008 observed maximum in a GII outbreak), with acute-phase single-specimen
  GII medians landing inside it at 8.4 (Barreira, children) to 8.9–9.0 (Lee
  2007, He 2017) and Teunis's 161 observed GII.4 samples topping out at 8.9;
  Ozawa's GII/4 mean of 7.96 × 10⁹ copies/g (9.90 log10) sits just above it.
  Immunocompromised and chronic hosts reach 10.4–11 (He 2017 severe stratum in
  cancer patients,
  Chaimongkol 2024) — a different population from the model's ordinary
  passenger.
- **Time to peak:** **2–4 days** post inoculation in challenge (Kirby digitized
  median day 4, range 2–6), day **3** post onset with a rise continuing to day
  9 in paediatric cohorts (Lee 2021, Cheng 2021).
- **Decline and duration:** log-linear decline after the peak, ≈0.11
  log10/day where the units are unambiguous (Sabrià), reaching cessation
  between day 15 (Cheng) and day 29 (Tu mean 28.7 d), with 47% of GII.4 cases
  still shedding at ≥21 d (Costantini) — consistent with the register's
  existing `shedding_duration_days` interval [12, 30] and with a shedding clock
  far longer than the 1–3 day illness.
- **Asymptomatic:** no GII asymptomatic *peak* exists in the challenge
  literature; observationally the asymptomatic distribution is either
  indistinguishable from symptomatic (Ozawa, Teunis, Costantini, Huynen for
  GII) or ~0.8–1.2 log10 lower (Barreira, Dábilla, Sabrià).

**The shipped 11.0 log10 copies/g lies above every GII central estimate found
here and above every observed GII maximum in an immunocompetent host.** That is
recorded, not acted on, for the reason already in the register: emission scale
and dose-response enter the model as a **product** (#366), so a downward
emission correction adopted alone silently moves the dose axis with no evidence
for the move. Every dose figure in the repository is void pending a refit
([the open ledger](../norovirus/norovirus_open_ledger.md)), so the peak
magnitude stays **⊘ joint** — now with a measured GII interval attached to it
instead of a genogroup mismatch and no number. No GI→GII correction factor is
proposed, and none of the candidates above was selected, ranked or excluded by
reference to VSP rates, the Diamond Princess, the Greg Mortimer or any anchor
in `docs/anchors/`.

The register contribution is in
[`fragments/gii-shedding-peak.md`](fragments/gii-shedding-peak.md).
