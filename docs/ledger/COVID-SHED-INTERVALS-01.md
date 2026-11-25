# COVID-SHED-INTERVALS-01
**Date:** 2026-11-24
**Commit:** 1e8ee188
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 1e8ee188

Literature digitization table for the five SARS-CoV-2 shedding-curve
segments identified in [COVID-SHED-CURVE-01](COVID-SHED-CURVE-01.md). This
entry is documentation only: **no profile field, constant, engine behaviour,
simulation, campaign, or held-out status changes.** GM remains held out; H5
remains held out forever.

The target quantity is the one fixed by
[COVID-SHED-EVIDENCE-01](COVID-SHED-EVIDENCE-01.md): **viable-virus-weighted
emission on a symptom-onset-relative axis**. Culture kinetics are proxy
evidence; RNA kinetics are assay evidence; transmission-derived profiles are
external epidemiological checks. The intervals below are therefore literature
envelopes for a later owner decision, not a fitted curve, not a parameter box,
and not a licence to blend unlike endpoints.

## Digitization and grading conventions

- Grades follow `.agents/skills/model-parameter-provenance/SKILL.md`: no
  shipboard measurement exists, so nothing here is Grade A. Direct human
  challenge or community measurements are at most Grade B for the model
  setting; transferring swab RNA/culture kinetics into emitted viable material
  is Grade C.
- Origins use the register vocabulary: `R` Results, `Tn` Table n, `Fn·leg`
  figure legend text, `Fn·dig` figure digitized, `Ab` abstract only, `Sec` secondary. Consensus retrieval
  used `include_full_text_chunks: true`; open-access full text was opened for
  Killingley 2022, Hakki 2022, Wölfel 2020, Zhou 2023, He 2020,
  Casey-Bryars 2021, Kissler 2021 and Iyaniwura 2024.
- Rates written as `log10/day` are changes in log10 concentration per day.
  Hakki reports rates in e-foldings/day; conversion is
  `log10/day = (e-foldings/day) / ln(10)`.
- A “central-estimate envelope” spans published central estimates across the
  evidence classes. Statistical uncertainty intervals are digitized inside the
  evidence column rather than silently discarded; where they are much wider
  than the central envelope, the row is explicitly low-grade.
- The onset axis is self-reported symptom onset except where stated. Human
  challenge values measured post-inoculation are converted only as broad
  cross-axis brackets because symptoms began over a range, not at one exact
  time.

## Segment digitization table

| Curve segment | Declared literature interval for the target segment | Digitized evidence and caveats | Grade | Primary source(s) | Where-read |
|---|---|---|---|---|---|
| **Presymptomatic level/share** — share of total infectious/emitted material before symptom onset | **Unbounded within the physical range `[0, 1]` — retain with flag.** The useful digitized anchors are **0.07** for measured emitted RNA and **[0.30, 0.69]** for transmission outcomes, but neither bounds the target share of viable-virus-weighted emission. | Zhou 2023 human challenge: before the first reported symptom, viral RNA emissions were **9% (SD 26)** of air AUC, **10% (26)** mask, **2% (8)** hand and **8% (25)** surface; overall **7% (SD 21)** of emissions into air and environment. This is emitted **RNA**, not viable-virus-weighted emission; viable virus was recovered from masks and surfaces, but the paper does not report a viable-only pre-symptom AUC share. He 2020 corrected fit: **0.44 (95% CI 0.30–0.57)** of transmission before onset, sensitivity **0.37–0.48**. Casey-Bryars 2021 secondary contact-tracing analysis: **0.459–0.691** across contexts. Hakki 2022: **7/35 (20%)** shed infectious virus before broader symptom onset, but this is a fraction of cases, not a share of emitted material. Killingley 2022: throat RNA first quantifiable at **40 h** and nose RNA at **58 h** post-inoculation, while symptoms began **2–4 d** post-inoculation — evidence that shedding can precede onset, not a share. | **C overall**. Zhou is B for emitted RNA in an analogous human-challenge setting, but the transfer to viable-weighted emission share is C; transmission shares are outcome-side external checks. | Zhou 2023; He 2020 + Author Correction; Casey-Bryars 2021; Hakki 2022; Killingley 2022 | Zhou `R`; He `R`; Casey-Bryars `R`; Hakki `R`; Killingley `R` |
| **Peak position relative to onset** — day of maximum culture/RNA/emission relative to symptom onset | **`[−2, +6] d`**. Transmission-derived evidence occupies about **`[−2, +1]`**; culture/RNA evidence extends the envelope to **`+6`**. | He 2020 corrected fit peaks at onset **0 d (95% CI −0.9 to +0.9)**, sensitivity peaks **−2 to +1**. Casey-Bryars 2021 mean transmission time ranges **−2.6 to +1.4 d**; these are transmission outcomes, not emission. Hakki 2022: symptom onset median **3 d before** both peak RNA and peak infectious virus; IQR **3–5 d** for RNA and **3–6 d** for PFU. Wölfel 2020: maximum throat-swab RNA on illness day **4**, with peak concentrations before day 5. Killingley 2022: qPCR peaks at **4.7 d** (throat) and **6.2 d** (nose) post-inoculation; Figure 2c digitizes FFA peak timing at approximately **3.5–3.7 d** (throat) and **5.5 d** (nose). Against symptom onset at **2–4 d**, these are broad brackets of roughly **+0.7 to +4.2 d** for RNA and **−0.3 to +3.5 d** for culture. Jones 2021's **4.31 d (4.04–4.60)** is from onset of shedding, not symptom onset, and is not added to the onset-axis envelope. | **C overall** because the combined envelope crosses evidence classes and axes. Hakki/Wölfel/Killingley are B as human culture/RNA measurements; transfer to emitted viable material remains C. | Hakki 2022; Wölfel 2020; Killingley 2022; He 2020; Casey-Bryars 2021; Jones 2021 | Hakki `R`; Wölfel `R` + `F1·leg`; Killingley `R` + `F2·dig`; He `R`; Casey-Bryars `R`; Jones `R` |
| **Onset-to-peak rise** — upward slope through the onset day | **`[0, +2.3] log10/day`** as a wide cross-axis envelope; when a positive proliferation phase is conditional on being present, the central-estimate envelope is about **`[+1.5, +2.3] log10/day`**. **Axis-transfer flag:** no retrieved paper directly reports the slope of viable emission on the exact symptom-onset day. | Kissler 2021 acute-infection RNA proliferation rate **+1.5 log10 RNA copies/ml/day** overall (95% CrI **+1.2 to +2.0**). Hakki 2022 Bayesian kinetics: infectious-virus growth **5.0 e-foldings/day** (posterior mean), i.e. **+2.17 log10/day**; RNA growth **4.9 e-foldings/day**, i.e. **+2.13 log10/day**. Their published 95% credible intervals convert to a very wide **+0.61 to +12.94** and **+0.56 to +15.64 log10/day** respectively, so the central envelope is low-grade rather than precise. Iyaniwura 2024's dynamic-model fit to the untreated Killingley challenge data estimates infectious-virus growth **5.36/day** as an e-folding rate, i.e. **+2.33 log10/day** (about a 3 h doubling time); this is model-derived secondary evidence. He 2020's highest load at onset and Wölfel's already-declining first throat-swab courses permit zero remaining post-onset rise in some aggregate descriptions, while Hakki's median peak at onset+3 d requires positive rise after onset in those cases. | **C**. The rates are real measurements or fits of proliferation, but not measured as an onset-axis emission slope. | Kissler 2021; Hakki 2022; Iyaniwura 2024 using Killingley 2022; He 2020; Wölfel 2020 | Kissler `T1`; Hakki `T1` + `R`; Iyaniwura `R` + `T1`; He `R`; Wölfel `R` |
| **Post-peak decay** — downward slope after the peak | **`[−1.1, −0.17] log10/day` central-estimate envelope**. RNA-only central evidence is approximately **`[−0.70, −0.17]`**; culturable/infectious virus declines faster, centred near **−1.1**. | Jones 2021: mean decreasing RNA slope **−0.168 log10/day (95% CI −0.171 to −0.165)** in 4,344 longitudinally tested subjects. Kissler 2021: acute-infection RNA clearance magnitude **0.6 log10/day** overall (95% CrI **0.5–0.7**), i.e. **−0.6**. Hakki 2022: posterior mean decline **1.6 e-foldings/day** for RNA, i.e. **−0.695 log10/day**, and **2.6 e-foldings/day** for infectious virus, i.e. **−1.13 log10/day**; the published credible intervals convert to very wide **−2.30 to −0.22** and **−4.56 to −0.30**, respectively. Killingley 2022 does not publish a decay slope in the primary paper, but the assay distinction is direct: FFA detection lasted a median **6.5 d** in nose and **6.25 d** in throat, while qPCR remained quantifiable in all infected participants at day 14 and first undetectable qPCR occurred around **14.6–14.7 d** in those clearing in quarantine. Iyaniwura's later model of the challenge data explains the faster loss of infectious virus through a time-varying RNA-to-infectious-virus relationship; that mechanism is model-derived, not a measured slope. | **C overall**. Jones/Kissler/Hakki are B as human assay kinetics; use as viable-emission decay is C because RNA persistence and culturability loss are not emitted-material loss. | Jones 2021; Kissler 2021; Hakki 2022; Killingley 2022; Iyaniwura 2024 | Jones `R`; Kissler `T1`; Hakki `T1` + `R`; Killingley `R`; Iyaniwura `R` |
| **Total infectious period** — culture-positive/infectious window | **`[3, 21.8] d` wide outer envelope; direct central window `[3, 7] d`**. The upper edge is a sparse statistical outer bound, not an observed typical duration; observed/challenge tails are closer to **8–12 d** depending on axis and specimen. | Hakki 2022 community cohort: median duration of infectious viral shedding **5 d (IQR 3–7)** in 42 cases with both onset and end captured; **65%** still culture-positive 5 d after symptom onset and **24%** at 7 d. Killingley 2022 challenge: viable virus detectable by FFA for median **6.5 d** in nose and **6.25 d** in throat; mean clearance post-inoculation **10.2 d** from nose and **8.7 d** from throat; latest viable detection day **12** nose and day **11** throat. Wölfel 2020: no isolates after illness day **8**; probit estimate for `<5%` isolation success was day **9.78** after onset with a very wide 95% CI **8.45–21.78**. Çevik 2020's review reports no study detecting live virus beyond illness day **9**. The 21.8 d upper edge is retained only because the user-facing instruction asks for the best interval the literature honestly supports, including low-grade outer uncertainty; it must not be read as an observed culture-positive duration. | **B for the culture-positive assay window; C as an emission-period transfer**. Setting remains analogous rather than shipboard. | Hakki 2022; Killingley 2022; Wölfel 2020; Çevik 2020 | Hakki `R`; Killingley `R`; Wölfel `R` + `F1·leg`; Çevik `Sec`/`Ab` |

## Reading the five rows without overclaiming

1. **Presymptomatic share is the weakest row.** The only direct emission
   digitization found is Zhou's 7% pre-first-symptom share of emitted RNA.
   The much larger 30–69% values are shares of transmission outcomes under
   contact, isolation and observation processes. They are external checks, not
   measurements of emitted viable material. The physical lower bound is zero;
   the literature retrieved here does not supply a defensible positive lower
   bound for viable-virus-weighted emission share.
2. **Peak position is genuinely class-split.** Transmission-derived profiles
   peak near or before onset; culture/RNA cohorts often peak several days
   after onset. The wide `[-2, +6]` envelope records that disagreement rather
   than averaging it away.
3. **Rise and decay rates are assay slopes first.** No retrieved source
   directly measures emitted viable virus densely enough to report an
   onset-day rise slope or a post-peak emission decay slope. The table carries
   RNA and culture slopes as proxies and grades the transfer accordingly.
4. **Culture and RNA clocks must not be merged.** Killingley and Hakki both
   show viable virus ending days before RNA disappearance. A single decay or
   duration row is already a wide envelope across unlike endpoints; treating
   it as one precise biological clock would be a definitional error.
5. **The intervals are not implementation instructions.** Any later curve
   change still needs an owner decision about endpoint priority, host
   heterogeneity, axis definition, normalization and re-denomination. This
   entry deliberately stops at digitization.

## Sources

- Zhou et al., *The Lancet Microbe* 2023, “Viral emissions into the air and
  environment after SARS-CoV-2 human challenge”, DOI
  [10.1016/S2666-5247(23)00101-5](https://doi.org/10.1016/S2666-5247(23)00101-5).
- Hakki et al., *The Lancet Respiratory Medicine* 2022, “Onset and window of
  SARS-CoV-2 infectiousness and temporal correlation with symptom onset”,
  DOI [10.1016/S2213-2600(22)00226-0](https://doi.org/10.1016/S2213-2600(22)00226-0).
- Killingley et al., *Nature Medicine* 2022, “Safety, tolerability and viral
  kinetics during SARS-CoV-2 human challenge in young adults”, DOI
  [10.1038/s41591-022-01780-9](https://doi.org/10.1038/s41591-022-01780-9).
- Wölfel et al., *Nature* 2020, “Virological assessment of hospitalized
  patients with COVID-2019”, DOI
  [10.1038/s41586-020-2196-x](https://doi.org/10.1038/s41586-020-2196-x).
- He et al., *Nature Medicine* 2020, “Temporal dynamics in viral shedding and
  transmissibility of COVID-19”, DOI
  [10.1038/s41591-020-0869-5](https://doi.org/10.1038/s41591-020-0869-5), and
  Author Correction DOI
  [10.1038/s41591-020-1016-z](https://doi.org/10.1038/s41591-020-1016-z).
- Casey-Bryars et al., *BMJ Open* 2021, “Presymptomatic transmission of
  SARS-CoV-2 infection: a secondary analysis using published data”, DOI
  [10.1136/bmjopen-2020-041240](https://doi.org/10.1136/bmjopen-2020-041240).
- Jones et al., *Science* 2021, “Estimating infectiousness throughout
  SARS-CoV-2 infection course”, DOI
  [10.1126/science.abi5273](https://doi.org/10.1126/science.abi5273).
- Kissler et al., *PLoS Biology* 2021, “Viral dynamics of acute SARS-CoV-2
  infection and applications to diagnostic and public health strategies”, DOI
  [10.1371/journal.pbio.3001333](https://doi.org/10.1371/journal.pbio.3001333).
- Iyaniwura et al., *PNAS* 2024, “The kinetics of SARS-CoV-2 infection based
  on a human challenge study”, DOI
  [10.1073/pnas.2406303121](https://doi.org/10.1073/pnas.2406303121).
- Çevik et al., *The Lancet Microbe* 2020, “SARS-CoV-2, SARS-CoV, and
  MERS-CoV viral load dynamics, duration of viral shedding, and
  infectiousness”, DOI
  [10.1016/S2666-5247(20)30172-5](https://doi.org/10.1016/S2666-5247(20)30172-5).

## Limits

- Zhou's 7% is viral RNA emission AUC, not viable-virus-weighted emission;
  the paper does not provide a viable-only time split or a confidence interval
  for that mean.
- Killingley onset conversion is broad because symptom onset is reported as a
  2–4 d range, not as a participant-aligned onset time in the digitized text.
- Hakki's hierarchical credible intervals are very wide; the table exposes
  them but uses central-estimate envelopes for cross-study comparison. This is
  why the rise/decay rows remain Grade C rather than precise measurements.
- Figure digitization was limited to Killingley Figure 2c peak timing; no
  curve was digitized or reconstructed. No simulation, fitting or
  implementation decision was run.
