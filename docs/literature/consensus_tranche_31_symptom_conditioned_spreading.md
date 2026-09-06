# Tranche 31 — the boarding prevalence measures what it says it measures, and the quantity the model is missing is symptom-conditioned spreading efficiency

**Register rows fed / supersession.** This tranche feeds two §3.1 rows that did
not exist — *symptom-conditioned spreading efficiency* (a quantity the model
does not have) and an external *symptomatic-to-asymptomatic reproduction-number
ratio* check — and rewrites the boarding-prevalence row's mechanism caveat with
the specific collision that makes it unresolved. It **supersedes nothing** and
**withdraws nothing**. In particular it does **not** move, narrow or reopen
either `asymptomatic_shedding_log10` row: both stay as tranche 16 and tranche 10
left them, the GII row's interval **[0, 1.2]** with 0.5 an authored placeholder,
the paediatric row ⊘ on setting, and the two still not poolable.

**Status:** Evidence assembled and interpreted, **sourcing only**. **No profile
constant, engine constant, config value or code path changes in this document's
change.** Like every document in `literature/`, this is context, not truth:
where it and the register disagree, the register holds the status and this
document holds the citations.

**Scope:** the interpretation question the #37 diagnosis left open — norovirus
boards at a **prevalence of asymptomatic RNA carriage** on every voyage, and
those boarded hosts are then transmission-competent per copy on every route
except emesis, so extinction cannot occur and the quiet-voyage half of the
mixture VSP measures cannot arise.

**Method:** Consensus MCP, `include_full_text_chunks: true`, four queries in
§6. Sukhrie 2012 is the one paper carrying the governing quantity and it is
**paywalled**: OUP returned HTTP 403 to a direct fetch and Europe PMC holds no
PMC record for it (`isOpenAccess: N`, no PMCID), so the retrieval ladder
terminated at E2. The publisher PDF was then supplied by the repository
maintainer via an Internet Archive copy, and its Results section and Figure 2
were read directly — origin **Sec** below, with the blocked-read attempts
recorded rather than dropped.

**Result in one line.** The boarding interval is **correct for what it is** —
asymptomatic faecal RNA prevalence, which is exactly the quantity the
wastewater sentinel detects — and the defect is not its magnitude and not the
asymptomatic shedding offset, both of which the adult literature declines to
shrink: Teunis 2014 finds asymptomatic shedding *markedly similar* to
symptomatic and states the consequence explicitly, that the greater
contribution of symptomatic cases to transmission **must** then be caused by
higher spreading efficiency. That efficiency term is measured — Sukhrie 2012
puts the reproduction number at **1.64 (95% CI 1.56–1.70)** with diarrhoea
against **0.85 (0.55–1.05)** without, a ratio of **0.52 (bounded 0.32–0.67)** —
and it is **absent from the model**, where symptom status reaches
`transmission_core` through the emesis path and nowhere else. It is admissible
as an **out-of-sample check** and **refused as a per-copy multiplier**, because
it is net of the emesis route already in tree.

---

## 1. What the boarding interval measures, and why that is not a licence to seed infectious cases

The row is Grade B on three non-outbreak measurements: 2.5% of 4,536 healthy
asymptomatic adults (Kobayashi 2021), pooled adult 4% / food handlers 3% across
81 studies (Qi 2018), 0.71% of 707 asymptomatic food handlers (Jeong 2021).
Every one is **RT-PCR positivity in stool in an asymptomatic person**. The
denominator is a screened population and the endpoint is genome detection.

Three things follow, and the register carried only the first:

1. The interval is admissible for the **carriage** quantity, and passengers
   [0.025, 0.040] / crew [0.007, 0.030] stand.
2. It is the **sentinel's** quantity. Wastewater surveillance reads faecal RNA,
   so boarded asymptomatic carriers *should* appear in the sentinel channel;
   any change that suppresses their RNA to buy quiet voyages would break a
   detection observable to fix a transmission one.
3. It is **not** an infectious-importation rate. RT-PCR positivity is not
   transmission competence, and the model currently treats it as though it
   were — not by any explicit conversion, but by having no term in which the two
   could differ.

## 2. The collision: one quantity serves both the observation and the transmission side

Read in tree:

- `get_pathogen_shedding()` returns a per-epoch emission from the
  symptomatic or asymptomatic curve, selected on `ever_presented(inf)`.
- That emission feeds the zone surface and environmental pools
  (`ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION`), from which the fomite route
  delivers dose (`ENV_DELIVERY_FRACTION_PER_DAY`).
- The wastewater sentinel samples the **greywater fraction of the same zone
  pools** (`build_wastewater_pathogen_mass`), which
  `WastewaterSequencing.sample_zone` converts to reads.

So the sentinel's sensitivity to asymptomatic carriage and the asymptomatic
host's infectiousness are **the same number**. There is no admissible edit to
one that does not move the other, which is why the #37 diagnosis could not be
resolved by adjusting the prevalence or the offset: **neither is the free
parameter, because there is no free parameter.** The missing quantity is a term
that separates emitted RNA from delivered infection risk *conditional on symptom
status*, and §3 is what the literature says about it.

This is the **same archetype** as the emesis-into-food refusal
(tranche 30 §4) and as `Θ` on the SARS-CoV-2 arm: two observables riding one
degree of freedom, where the defect is structural and the repair is a term, not
a value.

## 3. Symptom-conditioned spreading efficiency — measured, and absent from the model

### 3.1 Teunis 2014 states the inference, not just the null

Teunis 2014 (*Epidemiol Infect*, DOI
[10.1017/S095026881400274X](https://doi.org/10.1017/S095026881400274X)), 102
subjects — 71 symptomatic, 31 asymptomatic, patients and staff, adults, Dutch
hospital and nursing-home outbreak surveillance, RT-PCR, longitudinal
multilevel Bayesian model — reports peak levels averaging 10⁵–10⁹/g and
durations averaging 8–60 days, and finds the two groups' shedding "markedly
similar", with the posterior distributions of peak, time-to-peak, duration and
area under the curve giving no indication of a difference. Its Summary then
draws the consequence:

> "Given equal shedding, the greater contribution of symptomatic cases to
> transmission must be caused by their higher efficiency in spreading these
> viruses."

The register already cites this paper for `shedding_variance_log10` (its
between-host peak range) and tranche 16 §3.2 for its fitted peaks. **The
mechanism sentence is nowhere in the register**, and it is the part that bears
on the model: the paper that supplies our between-host variance also says the
symptom effect belongs somewhere other than the shedding curve.

### 3.2 Sukhrie 2012 supplies the magnitude

Sukhrie, Teunis, Vennema, Copra, Beersma, Bogerman, Koopmans, *Clin Infect Dis*
2012;54(7):931–7, DOI [10.1093/cid/cir971](https://doi.org/10.1093/cid/cir971),
"Nosocomial transmission of norovirus is mainly caused by symptomatic cases".
Five outbreaks in two types of Dutch healthcare facility, GII.4, all patients
and healthcare workers sampled with and without symptoms; enhanced sampling
raised the 28 recognised symptomatic patients by 65 further confirmed cases
(9 asymptomatic patients, 37 symptomatic HCWs, 11 asymptomatic HCWs). 50 (20%)
of participating HCWs had at least one PCR-positive stool; 43 (54%) of
participating patients tested positive.

Per-subject reproduction numbers were obtained by MCMC on a transmission matrix
with a fitted serial-interval distribution and the cohort's shedding kinetics,
then averaged by category (Results, "Transmission by Category" and Figure 2):

| Category | Mean R | 95% CI |
|---|---|---|
| All cases **with** diarrhoea | **1.64** | 1.56–1.70 |
| All cases **without** diarrhoea | **0.85** | 0.55–1.05 |
| Symptomatic patients | 1.89 | 1.71–2.12 |
| Symptomatic HCWs | 1.30 | 1.08–1.52 |
| Asymptomatic HCWs | **none detectable** | — |

Ratio of the two pooled arms: **0.52**, and **[0.32, 0.67]** taking the CI
corners against each other. The difference is significant pooled across
outbreaks, and not significant in one of the five (OB 4) taken alone.

Four caveats travel with it, all from the paper:

- **It is a model output.** R is an MCMC posterior over a transmission tree,
  not a counted quantity, so the register's standing rule caps it at **Grade
  C** — the same rule that records Teunis 2020's fitted infectivity rather than
  adopting it.
- **The exposed arm is "without diarrhoea", not "never symptomatic".** The
  authors stratify diarrhoea separately from vomiting, so vomiting-only cases
  sit in the 0.85 arm. Our `never_symptomatic` host has no symptoms at all, so
  **0.52 is an upper bound** on the ratio that applies to it.
- **The authors attribute the gap to hygiene, not virology**: "an infected
  person does not need to be infectious, most likely related to proper personal
  hygiene", with the significant patient-versus-HCW difference at equal
  shedding read the same way. That points at continence, toileting and
  hand-hygiene behaviour — mechanisms the model can hold — rather than at a
  per-copy infectivity constant.
- **Setting is nosocomial**, and the *levels* are not transportable to a ship
  (care contact, dependency, ward structure). The **ratio** is far more
  transportable than either level, because both arms are measured inside the
  same outbreaks and the setting's contact structure divides out to first
  order — but it is still a ratio measured under one contact structure.

### 3.3 Heijne 2012 is a role contrast, not a symptom contrast

Heijne et al.'s R of 0.25 for HCWs against 1.20 for patients is a **role and
care-dependency** difference, not a symptom-status one, and Sukhrie's own
stratification shows why the two must not be merged: symptomatic HCWs (1.30)
and symptomatic patients (1.89) differ from each other at the same symptom
status. Recorded; not used.

## 4. What is refused

### 4.1 A genome-copies-to-infectious-units conversion

The obvious way to separate the sentinel's RNA from the transmission side is a
GC:PFU factor. It is **refused twice over**.

*On the evidence*: the ratio is not a constant. Mirmahdi 2025 (*Food Environ
Virol*, DOI [10.1007/s12560-024-09632-0](https://doi.org/10.1007/s12560-024-09632-0))
reports a strong genome-copy-to-PFU relationship for the Tulane virus surrogate
with a median ratio of ≈**3.7 log10**, and states plainly that RT-qPCR cannot
distinguish infectious from non-infectious particles and that matrix, virus,
culture system, aggregation and passage all move the ratio — with murine
norovirus examples spanning far wider (≈28:1 in oyster tissue against
190–19,000:1 elsewhere). That is a **1.4–4.3 log10** span, which is the same
defect tranche 15 recorded for the SARS-CoV-2 dose denominator.

*On identifiability*: our dose-response is calibrated in **RT-PCR units**
(Ge 2023's challenge doses are RT-PCR units; the shipped α/β row's axis is
administered genome copies, tranche 23). A constant GC:PFU factor multiplying
every emission is therefore **absorbed exactly** by the dose-response intercept
— the STAN-03 non-identifiability, and the same finding as tranche 25's
"emission scale × β is one axis". It would add a parameter and no information.

### 4.2 Adopting the Sukhrie ratio as a per-copy route multiplier

R is **net of every route**, including emesis. The model already carries a
symptomatic-only emesis path with its own measured per-event aerosol fraction
and vomitus titres, i.e. part of Sukhrie's 1.64-versus-0.85 gap is **already
represented**. Multiplying the asymptomatic host's per-copy efficiency by 0.52
on top of that double-counts by exactly the amount the emesis route already
supplies — the identical objection that refused the emesis-into-food channel in
tranche 30 §4. What the residual is cannot be read off the paper.

So the ratio enters as a **check** on the model's realised R by symptom status,
in the same standing as Mouchtouri's route-share check: non-circular against
A1/A2/A4/A8 because it is a within-outbreak *ratio of reproduction numbers*
measured in hospitals, not a cruise attack rate or posting rate. **No constant
may be moved to make the model reproduce 0.52.**

### 4.3 Shrinking the boarding prevalence, or deepening the asymptomatic offset

Both are the failure mode this repository's sourcing rule exists to prevent.
The prevalence is Grade B on its own denominator (§1) and the offset's adult
evidence runs *against* deepening it: Teunis 2014 finds no significant
difference at all, and the GII row already spans [0, 1.2] with contradictory
studies on both ends. Moving either to reduce the VSP posting rate would be
fitting a physical constant to a scored anchor.

## 5. What this licenses, and what it leaves open

**Licensed now:** the two new register rows, and a realised-R measurement
against §3.2's check.

**The open decision** (recorded here, not taken): the model needs *some* term in
which a never-symptomatic carrier is less efficient per emitted copy than an
ill case, and there are two candidate shapes.

1. **Mechanism.** Hand contamination scales with **defecation events per day**,
   which differ by roughly an order of magnitude between diarrhoeal illness and
   a continent carrier. This is the shape the Sukhrie authors' own hygiene
   attribution points at, it is measurable on both arms, and it is the
   concentrated-versus-mean archetype the register has hit three times. It also
   subsumes the two open provenance gaps recorded at the deposition constants in
   #447 (whole-gut transit; diarrhoeal liquid is not ingested food).
2. **Declared axis.** A symptom-status route-efficiency term swept over a
   declared interval, with the *direction* Grade B from §3.1–3.2 and the
   magnitude declared — the standing `FOOD_HAND_CONTACTS_PER_DAY` currently has.

Either way the sentinel keeps reading the emitted RNA, which is the point of
§2: the repair separates the two consumers of the emission rather than
suppressing it.

**Not licensed:** a GC:PFU constant (§4.1), a 0.52 per-copy multiplier (§4.2),
any move in the prevalence or the offset (§4.3), and any use of Sukhrie's
*levels* as ship quantities (§3.2).

## 6. Retrieval record

| Query | Returned | Used |
|---|---|---|
| norovirus asymptomatic infection transmission secondary attack rate compared with symptomatic cases | Teunis 2014 (chunks), Sukhrie 2012 (abstract only), Wang 2023 meta-analysis, a SARS-CoV-2 meta-analysis | Teunis 2014 §3.1; the SARS-CoV-2 paper **discarded on pathogen** |
| norovirus peak shedding asymptomatic symptomatic multilevel Bayesian model table peak concentration genome copies per gram staff patients | Teunis 2014 (Results/Discussion chunks), Sabrià 2016, Ge 2023 | Teunis 2014 §3.1; Sabrià 2016 already in tree (decline-shape row); Ge 2023 §4.1 for the dose unit |
| norovirus genome copies to infectious units ratio | Mirmahdi 2025 (chunks), Chaimongkol 2024 (chunks) | Mirmahdi 2025 §4.1; Chaimongkol 2024 already in tree (chronic stratum) |
| asymptomatic norovirus prevalence food handlers adults | Qi 2018, Wang 2023 | already in tree (boarding row) |

**Blocked reads, recorded so they are not re-run blind:**

- Sukhrie 2012 body: Consensus returned **abstract only** on two separate
  queries (paywalled, no chunks). OUP `academic.oup.com/cid/article/54/7/931`
  → **HTTP 403**. Europe PMC → record present (PMID 22291099), `isOpenAccess:
  N`, **no PMCID**, so no JATS route. Obtained as the publisher PDF from an
  Internet Archive capture supplied by the maintainer; §3.2 is read from its
  Results and Figure 2. Origin **Sec**.
- Heijne 2012's per-role reproduction numbers were **not** re-retrieved this
  pass (§3.3 does not use them).

## 7. Findings against the model rather than the parameters

- **F31-1.** The wastewater sentinel and the fomite route consume the same
  emission, so no asymptomatic detectability change is expressible without an
  equal transmission change (§2).
- **F31-2.** Symptom status reaches `transmission_core` in exactly one place —
  the emesis path. Faecal deposition, hand load, food deposition and direct
  contact are per-copy identical for a never-symptomatic carrier and an ill
  case (§2).
- **F31-3.** The paper supplying `shedding_variance_log10` also states that the
  symptom effect does not belong in the shedding curve (§3.1). The register
  cited the variance and not the inference.
- **F31-4.** Sukhrie's asymptomatic arm is "without diarrhoea" and therefore
  includes vomiting-only cases, so **0.52 bounds our never-symptomatic ratio
  from above** (§3.2). The model's `never_symptomatic` host is a stricter class
  than any arm in the measurement.
