# Consensus sourcing, tranche 3

**Status:** evidence discovery. Nothing here is adopted; no constant, profile
field or engine path is changed by this document. Candidate values become model
values only through `model-parameter-provenance`, with a unit check and an
evidence grade, and never by being quoted here.

Companions: [`parameter_sourcing_bundle.md`](parameter_sourcing_bundle.md)
(tranche 1, the per-arm citation count, the Edison question list),
[`consensus_tranche_2.md`](consensus_tranche_2.md) (tranche 2, the non-secretor
genogroup work).

This tranche was aimed at the two arms that cannot presently be scored — the
COVID severity and observation layer (tasks #31, #33) and the norovirus emission
term (task #30's norovirus twin) — plus the two nulls tranche 2 recorded. It
opens with a correction to tranche 2 that came from the repository, not from a
paper.

---

## 1. Correction to tranche 2: the arm is GII, and the profile always said so

Tranche 2 established the genogroup-stratified secretor evidence correctly, then
attached it to the wrong arm. It asserted that `norwalk_gi` "is GI.1 by name and
dose-response provenance" and concluded that a removed fraction of ≈0.20 was
defensible after all. The first half of that assertion is false. From
`data/pathogens/active_profiles.json`:

| field | value |
|---|---|
| `pathogen_id` | `norwalk_gi` |
| `name` | **`Norwalk Virus (Norovirus GII.4)`** |
| `strain_evolution.genotypes` | **`GII.4`, `GII.17`, `GII.2`** (equal prior, 0.3333 each) |
| `incubation.notes` | "Pooled norovirus **GII** … **GII rather than the GI the pathogen_id implies, because this profile's genotypes are GII.4/GII.17/GII.2**" |
| `dose_response` | `beta_poisson`, α 0.111, β 32.81 — inherited from `Person.java`; `norovirus_model_history.md` §9c records these as fitted to administered oral **Norwalk (GI.1)** inoculum |

So the arm simulates GII strains, incubates as GII, is named GII.4, and is
validated against GII-dominated cruise outbreaks. The only GI things about it are
the `pathogen_id` string and the inherited dose-response.

**Consequences.**

1. **The GII interval governs the susceptibility term.** #367's original
   conclusion stands: non-secretors are partially susceptible to GII (Teunis
   2020 Se− 0.015 vs Se+ 0.076; Frenck 2012 GII.4 1/17 Se− ill vs 13/23 Se+;
   Rouphael 2022 GII.2 4/8 vs 10/12), the removed-fraction mechanism is the
   wrong shape, and its ceiling is ≈0.16. The shipped 0.0 and Edison's 0.2 are
   both outside that interval, in opposite directions — which is what #367 said
   and #371 wrongly reversed.
2. **The chimera runs the other way round.** What is mis-genogrouped is the
   *dose-response*: a GI.1-inoculum infectivity curve driving a GII strain set.
   Teunis 2020 puts GI at 3.7× GII per genome copy in secretor-positive hosts,
   so the arm is plausibly over-infectious per copy and correcting it moves
   infectivity and susceptibility in opposite directions — the partial
   cancellation tranche 2 identified is real, but it is between the *dose-response*
   and the susceptibility term, not between two candidate genogroups.
3. **Edison Q5 is answered, and by us.** The question "which genogroup is this
   profile intended to represent?" has an in-repo answer: GII, declared in three
   places. What remains for Edison is narrower and sharper — Q1, what data α =
   0.111 / β = 32.81 were fitted to, since if they are Norwalk GI.1 the arm has
   a genogroup mismatch at its most sensitive point.

**The methodological lesson, recorded because it is the second time in this
sequence:** tranche 2 corrected a real error by reading the source table more
carefully. It then introduced a new one by not reading the *profile* as carefully
as the paper. A provenance audit has two halves — what the literature says, and
what the model actually contains — and the second half is the one we own.

---

## 2. COVID severity: three candidate sources, none of them a five-state vector

`sars_cov2_resp` carries `severity_model: null` and `observation_model: null`,
against the norovirus arm's five states (`asymptomatic`, `subclinical`, `mild`,
`moderate`, `severe_critical`) with Dirichlet prior and per-state reporting and
sampling vectors. Task #31 needs the COVID equivalent. What exists:

**Wu & McGoogan 2020, *JAMA*, DOI `10.1001/jama.2020.2648`** — China CDC, 44,672
laboratory-confirmed cases. **81% mild** (defined as non-pneumonia *and* mild
pneumonia), **14% severe** (dyspnoea, RR ≥30, SpO₂ ≤93%, PaO₂/FiO₂ <300, or
>50% infiltrates in 24–48 h), **5% critical** (respiratory failure, septic
shock, multi-organ failure). CFR 2.3% overall, 49.0% among critical, and **no
deaths among mild or severe cases**. Asymptomatic cases were 1% of the record.

That 1% is the reason this cannot be dropped into a five-state vector. The
denominator is *confirmed cases in a symptom-driven ascertainment system*: the
81/14/5 split is conditional on having been detected, and the asymptomatic
fraction is a statement about Chinese testing policy in February 2020, not about
SARS-CoV-2. Applied to a ship where everyone is tested, it would badly
understate the asymptomatic state and overstate severity. Grade A for the
conditional split, unusable for the marginal one.

**Buitrago-García et al. 2020, *PLoS Medicine*, DOI
`10.1371/journal.pmed.1003346`** — living systematic review, 94 studies. Overall
proportion asymptomatic throughout infection **20% (95% CI 17–25)**, with a
**prediction interval of 3–67%**. In the 7 studies of *defined populations
screened for SARS-CoV-2 and then followed*, **31% (95% CI 26–37, prediction
interval 24–38)**. Secondary attack rate lower from asymptomatic than
symptomatic index cases (RR 0.35, 95% CI 0.10–1.27).

The screened-and-followed subset is the estimator that matches our scenarios —
Greg Mortimer tested everyone, Diamond Princess approached it — and it is the
one to use, not the headline 20%. The 3–67% prediction interval is the honest
statement of between-study heterogeneity and is exactly the kind of bound the
admissible-region approach wants; note that it is wide enough to contain almost
any modelling choice, so this factor will not be pinned by literature alone.

**Tabata et al. 2020, *Lancet Infectious Diseases*, DOI
`10.1016/s1473-3099(20)30482-5`** — 104 Diamond Princess infections admitted to
the Self-Defense Forces Central Hospital, 11–25 Feb 2020, with explicit
operational definitions (asymptomatic = no clinical signs at any point; severe =
pneumonia symptoms, dyspnoea, tachypnoea, SpO₂ <93%, or need for oxygen; mild =
everything else). Useful for its *definitions* and as a Diamond Princess-specific
severity split, but it is a single-hospital referred subset of the outbreak, so
its proportions carry a selection filter of unknown size.

**Barred: Emery et al. 2020, *eLife*, DOI `10.7554/elife.58699`.** Estimates 74%
(70–78) of Diamond Princess infections proceeded asymptomatically and 53%
(51–56) went undetected despite intense testing. This is the most attractive
number in the tranche and we must not use it. It is a *transmission model
calibrated to Diamond Princess onset and test-frequency data* — the exact data
#365 designates as our training set. Importing it as a parameter and then fitting
to Diamond Princess would be training on the target twice, laundered through a
third party's posterior. It is a useful *comparator* for what our own fit
recovers, and nothing else.

**Where this leaves #31.** There is no single source for a five-state COVID
severity vector, and the three states the literature does supply are conditional
on three different observation processes. The honest construction is therefore
compositional and must be declared as such: asymptomatic fraction from
Buitrago-García's screened-population estimate with its own interval, the
mild/moderate/severe_critical shape from Wu & McGoogan *after* stating that its
denominator is detected cases, and Tabata for definitional alignment. That is a
Grade B/C composite, not a measurement — the same status as the norovirus arm's
15 numbers (task #27), and it should be entered in the interval ledger rather
than as point values.

---

## 3. PCR sensitivity as a function of time since exposure: the observation layer's missing curve

Both active profiles carry `observation_model.assay_sensitivity_by_time_since_infection: null`
(norovirus) or a null observation model entirely (COVID). The field wants a
vector; the literature supplies one.

**Kucirka et al. 2020, *Annals of Internal Medicine*, DOI `10.7326/m20-1495`** —
Bayesian hierarchical model over 7 studies, n = 1,330 upper-respiratory samples,
false-negative rate by day since infection:

| day since exposure | false-negative rate (95% CI) |
|---:|---|
| 1 | 100% (100–100) |
| 4 | 67% (27–94) |
| 5 — typical onset | **38% (18–65)** |
| 8 | **20% (12–30)** |
| 9 | 21% (13–31) |
| 21 | 66% (54–77) |

This is directly the shape `assay_sensitivity_by_time_since_infection` needs: a
U-curve in time, minimum false-negative around 3 days post-onset, rising again as
viral load falls. It matters more for us than for a clinical reader, because the
Diamond Princess testing campaign tested people at *widely varying* times since
their own exposure — a scalar sensitivity would systematically misattribute the
shape of the daily case curve we intend to fit. Grade B (a pooled model over
heterogeneous studies, with wide CIs the authors themselves flag), and its
`day since exposure` index must be aligned to our epoch clock and our incubation
draw rather than assumed to start at symptom onset.

**Oordt-Speets et al. 2024, *Journal of Global Health*, DOI
`10.7189/jogh.14.05005`** — systematic review, 14 serial *viral culture* studies.
Culture-positive samples from **4 days before to 18 days after** symptom onset;
daily culture positivity peaks at **44–50% on days −1 to +5**, falls to 28% on
day 7, 11% on day 9, and 0–8% on days 10–17.

Two uses and one caveat. It bounds infectious duration independently of RNA
detection, which is the quantity `recovery_day: 7` is supposed to encode — and 7
is defensible as a central value while the observed tail runs to day 10+, so the
interval is roughly 5–12 rather than a point. And it separates *infectiousness*
from *detectability*, which is the distinction the observation layer exists to
represent: Kucirka's day-9 detection is near its best while culture positivity is
already down to 11%. The caveat is that this review restricts to the
post-vaccination period, so it is not a clean surrogate for an immunologically
naive February-2020 cohort.

---

## 4. Norovirus emission: total shed genome copies, which removes the stool-mass problem rather than solving it

Tranche 2 recorded a null: no usable distribution of diarrhoeal stool mass per
day for acute norovirus in adults, only the >250 g/day diagnostic definition.
That null stands, and it is now less important, because the quantity we actually
need has been measured directly.

**Ge et al. 2023, *Emerging Infectious Diseases*, DOI `10.3201/eid2907.230117`**
— Bayesian mixed-effects reanalysis of a human challenge study. Across inoculum
doses from 4.8 to 4,800 RT-PCR units:

| quantity | low dose (4.8 units) | high dose (4,800 units) |
|---|---|---|
| total virus shed in **feces** | 4.5 × 10¹¹ GEC | 3.4 × 10¹² GEC |
| total virus shed in **vomit** | 6.4 × 10⁵ GEC | 3.0 × 10⁷ GEC |
| shedding onset | 1.4 d | 0.8 d |
| peak shedding | 2.3 d | 1.5 d |
| symptom onset | 1.5 d | 0.8 d |

The authors are explicit that the dose effect on total load and shedding was
inconclusive; the value of the paper for us is the *magnitudes*, which span less
than one order across a thousandfold dose range.

**Why this is structural rather than one more number.** The shipped emission term
is `environmental_faecal_release_log10_g_per_epoch` — grams of stool per epoch —
which forces the emission magnitude through a product of two quantities we cannot
source: stool mass (the standing null) and copies per gram. Ge measures the
product directly, as total genome copies shed per infected host over the
infection. An emission path parameterised in *copies* needs neither factor, and
the mis-dimensioned key can be retired rather than repaired. That is the same
move #366 argued for on the COVID side, where the identical grams-of-stool scaler
divides respiratory emission by a thousand; here the replacement measurement
actually exists.

**And it disagrees with our second-ranked factor by orders of magnitude.** Kirby
et al. 2016 (tranche 2) gives ≈1.7 × 10⁸ GEC total emesis shedding per average
subject; Ge gives 6.4 × 10⁵ to 3.0 × 10⁷ GEC in vomit — 1 to 2.4 orders lower.
Both are direct measurements from human challenge studies. Candidate
reconciliations, none verified: different genogroups (Kirby pools GI.1, GII.2 and
GII.1; Ge's challenge strain needs checking), titre × volume reconstruction versus
modelled total, and different definitions of "per subject" (per episode versus
summed over the illness). Until that is resolved, emesis titre — the
**second-ranked factor in the Morris screen** — has a sourced *interval spanning
two to three orders of magnitude*, and any single value inside it is a choice we
are making, not a measurement we are inheriting. This is the most consequential
finding in the tranche.

---

## 5. Norovirus illness duration: two independent sources, and `recovery_day: 3`

`norwalk_gi` ships `recovery_day: 3` with no citation.

**Devasia et al. 2014, *Epidemiology and Infection*, DOI
`10.1017/s0950268814003288`** — 1,022 outbreaks, of which 64 reported average
incubation and 87 average symptomatic period. Incubation mean **32.8 h** (95% CI
30.9–34.6), median 33.5 h. Symptomatic period mean **44.2 h** (95% CI 38.9–50.7),
median **43.0 h** (95% CI 36–48). No strong association found between either
period and reported host, agent or environmental characteristics.

**Lopman et al. 2004, *Clinical Infectious Diseases*, DOI `10.1086/421948`** —
prospective monitoring of 4 major hospitals, 11 community hospitals and 135
nursing homes in Avon, England. Median duration **2 days** for 482 hospital
staff, 166 nursing-home staff and 266 residents, 75% fully recovered within 3
days; median **3 days** for 730 hospital patients (75% within 5 days, P < 0.001
against the other groups).

So `recovery_day: 3` sits at the upper end of a genuinely measured distribution
whose central value is closer to 1.8–2 days (43 h) in a general adult population,
and 3 days is the *hospital-inpatient* figure. For a cruise population — mobile
adults, not inpatients — the sourced interval is roughly 1.5 to 3 days, and the
shipped value is at its boundary rather than its centre. Devasia also supplies an
incubation cross-check: 33.5 h median against the profile's 1.2-day (28.8 h)
lognormal median from Lee 2013 — consistent, from an independent outbreak-based
design rather than challenge studies.

**Bernstein et al. 2014, *JID*, DOI `10.1093/infdis/jiu497`** — incidentally, a
further GII.4 challenge dose-response point in the units that matter for §1:
4,400 RT-PCR units produced infection in 27/50 (54.0%) vaccinees and 30/48
(62.5%) placebo controls. The placebo arm is a clean GII.4 infection probability
at a stated dose, and belongs in any GII.4 dose-response refit.

---

## 6. Nulls and standing gaps

Recorded so they are not re-searched:

- **Adult acute-norovirus stool mass distribution** — still not found (tranche 2
  null confirmed). Superseded in importance by §4: parameterise emission in
  copies and the quantity is not needed.
- **A five-state COVID severity vector from one source** — does not exist. §2
  gives the compositional alternative and its honest grade.
- **A naive-cohort culture-positivity series for SARS-CoV-2** — the available
  systematic review (§3) is restricted to the post-vaccination period.
- **Reconciliation of Kirby 2016 against Ge 2023 emesis totals** (§4) — open, and
  it bounds the second-ranked factor in the screen. Needs the primary texts, not
  a further search.

## 7. What changes in the repository as a result

Documentation only:

- [`../norovirus/norovirus_open_ledger.md`](../norovirus/norovirus_open_ledger.md)
  — the `innate_nonsusceptible_fraction` entry rewritten a second time: the GII
  interval governs, #367's conclusion stands, #371's reversal withdrawn.
- [`../proposals/bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md)
  §3.3 — the interval is GII, 0.00 – 0.16, not genogroup-conditional-with-GI-shipped.
- [`../norovirus/bounded_screen_results.md`](../norovirus/bounded_screen_results.md)
  — the screen's 0.00 – 0.16 sweep was the correct box after all, so its μ* for
  that factor is a measurement rather than a lower bound.
- [`edison_provenance_request.md`](edison_provenance_request.md) — Q5 answered
  in-repo and closed; Q1 (what α = 0.111 / β = 32.81 were fitted to) promoted,
  since a Norwalk GI.1 origin makes it a genogroup defect at the arm's most
  sensitive point.
- [`consensus_tranche_2.md`](consensus_tranche_2.md) — §1 and §2 marked corrected
  with a pointer here.

No pathogen profile, engine path or scoring constant is changed.
