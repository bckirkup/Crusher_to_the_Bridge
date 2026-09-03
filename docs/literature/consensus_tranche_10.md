# Tranche 10 — who boards already shedding: the norovirus importation channel is measured, and it is not the chronic shedder

**Status:** Evidence assembled and interpreted. **No profile constant, engine
constant or screen interval changes in this document.** The arithmetic in §3 and
§4 is reproducible from the cited papers and the shipped profile; the change it
justifies is specified in §6 and left to its own item.

**Scope:** item #45 part 3 — the chronic-shedder boarding/importation channel,
which [tranche 7](consensus_tranche_7.md) §6 explicitly declined to license with
a point value. PR #383 landed parts 1 and 2 (the acquisition multiplier
withdrawn; the measured quantities entering as `chronic_shedder_fraction` 0.228
and a 218-day chronic duration). This is the sourcing tranche for the third.

**Method:** Consensus MCP, `exclude_preprints=true`, queries fixed from the
definition of the quantity before looking at what the model needs. The intended
derivation was stated in advance — boarding prevalence = incidence × chronic
fraction × mean chronic duration — and is carried out in §4. The search also
returned a **direct** measurement of the quantity, which §3 records, and the two
disagree about which mechanism matters.

---

## 1. The correction this tranche forces on my own claim

On the strength of van Beek's 218-day median I said, in #383 and again in the
summary of it, that "against a 7–14 day voyage the relevant immunocompromised
host is not someone who catches norovirus more easily on board — it's someone
who **boards already shedding**", and called that the first evidence-based
statement available about who brings norovirus aboard.

The first half survives and the emphasis was wrong. A chronic host does board
already shedding and never clears on board — that stands. But the quantity I
did not compute is **how many such hosts there are**, and when it is computed
(§4) it is between **one and three orders of magnitude below** the number of
ordinary asymptomatic adults who board shedding (§3). So chronic shedders are
not the importation channel; they are a rare, long-tailed slice of it.

The channel is real, measured, and mostly immunocompetent.

## 2. Why this is the parameter the model most lacks

The index case is currently **seeded by fiat**: a run picks an infected agent
because it must start somewhere. Nothing in the model states how many hosts
board infected, so the one quantity that links one voyage to the next — and the
one that a real operator can actually screen against — is a construction rather
than a measurement.

Note what a boarding prevalence is *not* free to be. It cannot be fitted to VSP
incidence: VSP incidence is what the model is scored against, and importation is
an input to it. This tranche therefore takes its value from populations that are
**not** in an outbreak, and §5 records the specific measurement that would have
been the circular choice.

## 3. The direct measurement: asymptomatic adults, not in an outbreak

| Source | Setting | Measured prevalence | Grade |
|---|---|---|---|
| Kobayashi 2021, *Clin Microbiol Infect*, DOI 10.1016/j.cmi.2021.06.004 | 4,536 apparently healthy asymptomatic adults, mean age **58.0**, voluntary health check-ups, Japan, real-time RT-PCR on stool | **2.5%** (112; GI 57, GII 54, both 1) | **B** |
| Qi 2018, *EClinicalMedicine*, DOI 10.1016/j.eclinm.2018.09.001 (81 studies) | pooled asymptomatic prevalence, **adults** subgroup | **4%** (overall 7%, 95% CI 6–9; Europe and North America 4%; children 8%) | **B** |
| Qi 2018, same | **food handlers** | **3%** | B |
| Jeong 2021, *J Food Prot*, DOI 10.4315/jfp-21-136 | 707 asymptomatic food handlers, rectal swab, PyeongChang 2018 Olympics surveillance | **0.71%** (5/707; GI.3, GII.4, GII.17) | B |
| Kobayashi 2022, *Infect Dis*, DOI 10.1080/23744235.2022.2134447 | 288 of the same cohort re-screened after a median 599 days | **4.9%** (2.7% among previously positive, 5.6% among previously negative) | B |

Two intervals follow, and they are deliberately separate because the model has
two populations:

- **Passengers: [0.025, 0.040].** Both endpoints are adult, high-income,
  non-outbreak measurements of exactly this quantity, and the lower one is in a
  cohort whose mean age (58.0) is nearer the cruise population than anything
  else available. Grade B, the setting being a health check-up rather than an
  embarkation terminal.
- **Crew: [0.007, 0.030].** The food-handler measurements. Crew are the closer
  analogue for an occupationally screened, symptom-excluded population, and the
  two food-handler figures are 4× apart, which is the honest width.

The width in both is population and screening intensity, not measurement error.

**What the interval is a prevalence *of*, precisely:** RT-PCR-detectable
norovirus RNA in stool in a person reporting no diarrhoeal symptoms. It is not a
prevalence of infectiousness, and it pools two mechanisms the model represents
separately — genuinely asymptomatic infection, and convalescent shedding after a
resolved illness (which, before tranche 8, this model could not represent at
all). Any adoption must state which of the model's states an imported host
enters, and that is a design question, not a search result.

## 4. The intended derivation, carried out — and it spans 2.5 orders

Boarding prevalence of *chronic* shedding = P(immunocompromised) × chronic
incidence × mean chronic duration. Both available routes are computed here
because they disagree, and the disagreement is the finding.

**Route A — van Beek's cohort denominator.** 23 of 2,182 solid-organ transplant
recipients developed chronic infection over the 2006–2014 study window
(9 calendar years) → 0.117% per patient-year; median shedding 218 days = 0.597
years:

```
0.00117 /yr × 0.597 yr  =  7.0e-4   point prevalence among SOT recipients
7.0e-4 × [0.02, 0.074]  =  [1.4e-5, 5.2e-5]   of a boarding population
```

using the immunocompromised fraction interval [0.02, 0.074] adopted in #45.

**Route B — Bok's positivity denominator.** 35 of 268 immunocompromised patients
(13%) were norovirus-positive and persistent infection ≥6 months was documented
in 8 of 18 genotyped (44%):

```
0.13 × 0.44             =  5.7e-2   chronic among immunocompromised
5.7e-2 × [0.02, 0.074]  =  [1.1e-3, 4.2e-3]   of a boarding population
```

**Route B is an upper bound, not a competing estimate.** Its denominator is
patients *tested* while enrolled in NIH research studies — tested because they
were symptomatic or under investigation — so it is a positivity rate among the
suspected, and using it as a population prevalence inherits that selection. Nor
is 44% a duration-weighted quantity: it is the proportion of genotyped patients
whose infection persisted, in a cohort assembled at a tertiary referral centre.

So the chronic channel is bounded at **[1.4e-5, 4.2e-3]** — a span of 2.5 orders
whose width is *which immunocompromised population you mean*, from
solid-organ recipients to inborn errors of immunity. **No point value is
licensed**, and tranche 7's refusal to license one was correct.

Against §3's [0.025, 0.040], the comparison is the result:

| | Boarding prevalence | Ratio to the passenger interval |
|---|---|---|
| Ordinary asymptomatic adults (§3) | 2.5–4.0 × 10⁻² | — |
| Chronic immunocompromised, route B (upper bound) | 1.1–4.2 × 10⁻³ | 6–36× smaller |
| Chronic immunocompromised, route A | 1.4–5.2 × 10⁻⁵ | 480–2,900× smaller |

Chronic shedders are therefore **at most about a tenth, and plausibly a
thousandth**, of the hosts who board shedding. They are also mostly *inside*
§3's measurement rather than additive to it: the two must not be summed, and the
error from treating them as included is at most the ratio above.

**What they retain is not magnitude but duration.** A chronic host boards and
never clears — the shipped 218-day median against a 7–14 day voyage — so the
distinguishable consequence is a shedder present for the *whole* voyage, at
10⁴–10¹¹ copies/g (Chaimongkol 2024) with infectivity confirmed in vitro
(Davis 2020). That is a mechanism worth a swept axis, and it is not a mechanism
worth a fitted prevalence.

## 5. The measurement that would have been circular

Qi's outbreak subgroup gives asymptomatic prevalence at **18%** (95% CI 10–30),
and Wang 2023 (*BMC Infect Dis*, DOI 10.1186/s12879-023-08519-y), pooling 44
articles and 8,115 asymptomatic individuals **in outbreaks**, gives **21.8%**
(95% CI 17.4–27.3).

Those are five to nine times §3's non-outbreak figures, and they are the numbers
a search that wanted an outbreak would have found. They are measured *during
outbreaks* — a population conditioned on the very event this model is scored on
— so adopting either as a boarding prevalence would seed the model with the
outcome it is supposed to predict, and would do it under a citation. Recorded
here as the excluded value, with the reason, so that nobody re-finds it later
and reads the exclusion as an oversight.

The same distinction is visible in the model's own vocabulary: 21.8% is what a
*ship in outbreak* should exhibit, and is therefore a candidate **observable to
score against** — an output, not an input. It is the strongest argument yet for
the register's S class.

## 6. What this tranche licenses, and what it does not

**Licensed as evidence (not applied here):**

1. A boarding-prevalence interval for asymptomatic norovirus RNA shedding,
   **[0.025, 0.040] for passengers** and **[0.007, 0.030] for crew**, Grade B,
   from five measurements in non-outbreak populations — as an interval to sweep,
   not a point to adopt.
2. An explicit **null** on a chronic-shedder boarding point prevalence: bounded
   to [1.4e-5, 4.2e-3] by two routes that disagree by 2.5 orders, both far below
   the general channel. Chronic shedding belongs in the model as a **swept
   duration axis on an imported host**, not as its own prevalence.
3. The observation that the two channels are **not additive**, with the ratio
   that bounds the error of treating chronic hosts as included.
4. Corroboration, in passing, of the direction of the shipped norovirus
   asymptomatic shedding offset — and a question about its size. The profile's
   asymptomatic curve peaks 0.5 log10 below the symptomatic one; measured
   symptomatic-versus-asymptomatic differences are 8.39 vs 7.15 log10 copies/g
   (1.24 log10, p = 0.011; Vitória cohort, children) and 2.69 × 10⁸ vs
   4.32 × 10⁷ GC/g (0.79 log10; Dábilla 2017, children). Both are paediatric, so
   this is a **direction confirmed and a magnitude open**: the shipped 0.5 is
   about half the measured offset, in the conservative direction. Not adoptable
   from paediatric data alone.

**Explicitly not licensed:**

- No boarding prevalence taken from an outbreak population (§5), and no boarding
  prevalence tuned so that VSP incidence comes out right.
- No point value for the chronic channel, in either route's units.
- No claim that RNA-positive means infectious, in either channel; the §3
  interval is a prevalence of detectable RNA.
- No decision, from the literature, about which model state an imported host
  enters (asymptomatic-infected versus convalescent). The measurement pools the
  two; the model separates them only since tranche 8; the mapping is a design
  choice to be made and declared.
- No maritime measurement of any of this. Nothing found measures norovirus
  prevalence at embarkation, in any population, at any date — which is itself
  the finding that makes the food-handler and health-check cohorts the closest
  available settings, and caps every grade here at B.
