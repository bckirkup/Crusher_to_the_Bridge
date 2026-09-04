# Tranche 14 — influenza A on non-porous surfaces is a matrix-and-humidity family of half-lives, and the dose-conditional illness form is refuted at its source

**Status:** Evidence assembled. **No profile constant, engine constant, schema or
config value changes in this document, and none is recommended.** Nothing here
converts a measured half-life or log10 reduction into `surface_decay_per_day`:
the unit semantics of that field are precisely what is unresolved, and a
converted number would hide it. The register row this tranche proposes lives in
[`fragments/influenza-surface.md`](fragments/influenza-surface.md) and is the
lead's to merge.

**Scope:** item #44, the two influenza quantities blocked in
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
§3.3 and listed as items 2 and 3 of its §4:

* **Q1** — measured persistence of infectious influenza A on non-porous
  maritime-relevant materials (stainless steel, plastic, glass), in the units
  the papers use: half-life, or log10 reduction over a stated interval, with
  temperature, relative humidity, suspending matrix, strain, and assay.
* **Q2** — whether the probability of **illness given infection** is
  dose-dependent in human influenza challenge studies, and whether Carrat 2008
  reports what this repository says it reports.

The influenza arm is not in `active_profiles.json`, so this is a profile being
defined rather than a shipped one being repaired. No candidate below was
selected, ranked or rejected by reference to VSP incidence, the Diamond
Princess, the Greg Mortimer or anything in `docs/anchors/`; no such quantity was
computed at any point.

**Method:** Consensus MCP `search`, unfiltered on every query (no `year_min`,
no `study_types`, no `exclude_preprints` — recall was the point, and the
measurement papers did in fact sit below the reviews). Truncated result pages
were read in full from the overflow files. For the load-bearing numbers the
primary text was fetched and the Results read, not the abstract:

* Carrat 2008 full text from the HAL open-access deposit
  (`hal.inrae.fr/hal-02668741`, the CC-BY-NC author copy of the AJE article);
  `academic.oup.com` serves a Cloudflare interstitial to this machine and could
  not be read, which is recorded here so the next person does not repeat it.
* Qian 2023, Greatorex 2011 from Europe PMC full text; Perry 2016 from PMC.
* Teunis 2010 (Epidemics) full text is **not** open; its abstract and the
  register's existing note are all this tranche has, and its grade below
  reflects that.

---

## 1. Queries, verbatim

All seven were run unfiltered.

1. `influenza A virus survival stainless steel half-life infectivity TCID50`
2. `influenza virus survival non-porous surfaces log10 reduction respiratory mucus versus culture medium`
3. `experimental human influenza infection challenge studies pooled analysis symptomatic fraction dose`
4. `influenza dose-response probability of illness given infection inoculum dose relationship volunteers`
5. `influenza virus survival hands and surfaces titre decline hours Greatorex fingerpad`
6. `probability of illness given infection independent of inoculum dose influenza volunteer challenge symptomatic fraction`
7. `dose-response model conditional probability of illness given infection respiratory virus hazard dose influenza`

## 2. Q1 — what is actually measured, in the paper's own units

Every row is **infectious virus** unless the assay column says RNA. The assay
column is not decoration: §2.2 shows the two diverge by more than an order of
magnitude on the same coupons.

| Source | Material / matrix / conditions | Quantity as the paper defines it | Value, dispersion, n | Assay | Grade |
|---|---|---|---|---|---|
| Qian 2023, *Appl Environ Microbiol* 89(8), DOI [10.1128/aem.00633-23](https://doi.org/10.1128/aem.00633-23) | Stainless steel, ABS plastic, PS plastic, glass, aluminium, copper; 1 µL droplets of H1N1pdm09 (A/CA/07/2009) **propagated in primary human bronchial epithelial (HBE) cultures, i.e. suspended in human airway surface liquid**; 23% RH; 22–24 °C | **Median half-life of viable virus**, Bayesian hierarchical regression on raw titration wells | Stainless steel **4.52 h** (95% CrI 2.41–8.56), ABS **5.10** (2.74–9.60), PS plastic **5.91** (3.17–10.9), glass **5.91** (3.07–11.4). By **donor culture** instead: 3.21 (1.71–6.16) to **8.13** (4.23–15.5) h. n = 4 HBE donor cultures, ≥3 per condition, 10 droplets/replicate, triplicate | TCID50 | **B** |
| Qian 2023, same | Same surfaces, 2 h exposure, RH **23 / 43 / 55 / 98%** | **log10 decay over 2 h** relative to sealed control | PS plastic 0.79 ± 0.42; steel, aluminium, glass ≤1.0; ABS **1.5 ± 0.39**; copper below detection. Steel and aluminium **worst at mid-range RH**, more stable at both 23% and 98%; no surface differences at 98% | TCID50 | **B** |
| Perry 2016, *Appl Environ Microbiol* 82(11):3239, DOI [10.1128/aem.04046-15](https://doi.org/10.1128/aem.04046-15) | Stainless steel coupons; A/New Caledonia/20/1999 and A/Brisbane/59/2007 (H1N1) in **three matrices** — 2% FBS, 5 mg/mL mucin, viral medium (DMEM/BSA/HEPES); six absolute humidities = 18 or 25 °C × 20/35/55% RH; up to **7 days** | **Mean change in log10 TCID50 per coupon** vs T0, by matrix × AH × time | ≈ **1.5 log10** over 168 h (A/NC) and **2 log10** (A/Br); GEE: AH (p<0.0001), AH×strain (p<0.0001), time (p=0.0013 at T168) significant; **strain not** (p=0.45). Cumulative −1.74 log10 going from 4.1×10⁵ to 17.9×10⁵ mPa AH. SDs 0.2–1.2 log10 | TCID50 by tissue-culture ELISA, Reed–Muench | **B** |
| Greatorex 2011, *PLoS ONE* 6(11):e27932, DOI [10.1371/journal.pone.0027932](https://doi.org/10.1371/journal.pone.0027932) | 14 household/workplace surfaces incl. stainless steel, glass, aluminium, plastic (tissue-culture dish control); A/PR/8/34 and A/Cambridge/AH04/2009; 10 µL of virus diluted 1:10 in **1% BSA in serum-free DMEM** (buffer-like, no mucus); **17–21 °C, 23–24% RH** | **t½ fitted to one-phase exponential decay** on the plastic control, plus log10 reduction in plaque titre at 0/4/9/24 h per surface | **t½ ≈ 1.5 h**. Stainless steel log10 reduction 1.7 / 3.2 / 3.9 / >4.2 at 0/4/9/24 h; steel was the only non-control surface with recoverable virus at 9 h; nothing detectable anywhere at 24 h. Mean of 2–3 replicates, 6 coupons/surface | Plaque assay (PR8), fluorescent focus (AH04) | **B** |
| Greatorex 2011, same | Same coupons, same run | **log10 reduction in genome copy number** | Stainless steel **0.06 at 24 h** (PR8) and 1.38 (AH04); most surfaces only 1–2 log10 down at 24 h | **RT-qPCR (RNA)** — not usable for the model | B for RNA, **not** infectivity |
| Thompson 2017, *J Hosp Infect* 95(2):194, DOI [10.1016/j.jhin.2016.12.003](https://doi.org/10.1016/j.jhin.2016.12.003) | Stainless steel, cotton, microfibre; five H1N1 strains, 10 µL of 10⁶–10⁸ pfu/mL cell-culture stock in **0.3% BSA**; sampled 1 h, 24 h, then weekly to 7 weeks | **Time to 99% reduction** as a function of seeding stock; viability duration | Stainless steel **174.9 h** (R²=0.98), microfibre 34.3 h, cotton 17.7 h. Viable virus recovered to **2 weeks** on steel; **PCR positive for the full 7 weeks**. No strain differences | Plaque assay + qRT-PCR reported separately | **B** |
| Bean 1982, *J Infect Dis* 146(1):47, DOI [10.1093/infdis/146.1.47](https://doi.org/10.1093/infdis/146.1.47) | Stainless steel and hard plastic vs cloth/paper/tissue; laboratory-grown influenza A and B; 27.8–28.3 °C, 35–50% RH (conditions as tabulated by Perry 2016) | **Duration of recoverable infectious virus**, and hand-transfer window | **24–48 h** on steel/plastic vs <8–12 h on porous; 3.5 log10 loss by 48 h; transferable to hands for 24 h. Sample size not stated | CPE / infectivity | **B** |
| Oxford 2014, *Am J Infect Control* 42(4):423, DOI [10.1016/j.ajic.2013.10.016](https://doi.org/10.1016/j.ajic.2013.10.016) | Four household surfaces, H1N1pdm09, 7 time points | **Duration infectious** | **24 h** on stainless steel and plastic, 48 h on wood, 8 h on cloth | Infectivity | B |
| Sakaguchi 2010, *Environ Health Prev Med* 15(6):344, DOI [10.1007/s12199-010-0149-y](https://doi.org/10.1007/s12199-010-0149-y) | Stainless steel, coated wood, PPE (glove, N95, mask, Tyvek gown); 0.5 mL laboratory H1N1; 1, 8, 24 h | **Duration infectivity maintained**, plus HA titre | Infectious **8 h** on all materials except rubber glove (**24 h**); **HA titre unchanged at 24 h everywhere** — a second, independent demonstration that a non-infectivity assay reads far longer than infectivity | TCID50/mL + HA | B |
| Noyce 2007, *Appl Environ Microbiol* 73(8):2748, DOI [10.1128/aem.01139-06](https://doi.org/10.1128/aem.01139-06) | Stainless steel vs copper; ~2×10⁶ particles; 22 °C, 50–60% RH | Infectious particles remaining | **~5×10⁵ still infectious at 24 h on steel** (≈0.6 log10 loss); on copper ~500 by 6 h | Infectivity | B |
| Hirose 2020, *Clin Infect Dis* 73(11):e4329, DOI [10.1093/cid/ciaa1517](https://doi.org/10.1093/cid/ciaa1517) | Human **skin** model, and stainless steel/glass/plastic as comparator; IAV in **culture medium or upper-respiratory mucus** | **Survival time** (time to inactivation), with CI | IAV on skin **1.82 h** (95% CI 1.65–2.00) medium and **1.69 h** (1.57–1.81) mucus. On non-skin surfaces IAV was inactivated **faster in mucus than in medium** — the opposite direction to the airborne mucus effect the register cites for `airborne_half_life_hours` | Infectivity | B for skin; **C** for the surface comparison (no per-material half-life tabulated in the abstract-level data available) |
| Rockey 2024, *Appl Environ Microbiol* 90(2), DOI [10.1128/aem.02010-23](https://doi.org/10.1128/aem.02010-23) | H1N1 and H3N2 in **human saliva** vs **respiratory mucus / airway surface liquid**, droplets across RH | Decay of infectious virus by matrix and RH; wet vs dry phase distinguished | Rapid decay in saliva at intermediate RH; ASL droplets retain infectivity. **Matrix, not material, is the dominant axis** | Infectivity | B |
| Kormuth 2018, *J Infect Dis* 218(5):739, DOI [10.1093/infdis/jiy221](https://doi.org/10.1093/infdis/jiy221) | H1N1pdm09 in differentiated HBE material, aerosols **and stationary droplets**, 20–98% RH | Infectivity retained over 1 h | Infectious at 1 h across all RH in mucus vs minutes in saline. Already cited in the register for `airborne_half_life_hours`; carried here as the matrix-effect corroboration, **not** as a deposited-surface half-life | Infectivity | B (airborne), C for surface decay |

### 2.1 What the family says, and what it does not

Read together, the Q1 rows do not converge on a number; they converge on a
**set of axes**, each of which moves infectious survival on the same material by
about an order of magnitude or more:

* **Matrix.** Buffer/BSA-in-DMEM (Greatorex, Thompson) against human airway
  surface liquid (Qian, Kormuth, Rockey) against saliva (Rockey) against
  mucin/serum (Perry). Qian's own donor-to-donor spread — 3.2 h to 8.1 h half-life
  from four human lungs, same virus, same coupons — is **wider than its
  spread across four surface materials**. That is the single most important
  finding for a model that carries one scalar.
* **Relative humidity, non-monotonically.** Qian: steel and aluminium decay
  fastest at mid-range RH and are more stable at both 23% and 98%. Any
  single-rate field is being asked to summarise a U-shaped curve.
* **Assay.** Greatorex: 0.06 log10 RNA loss on steel at 24 h against >4.2 log10
  infectivity loss. Thompson: 7 weeks of PCR positivity against 2 weeks of
  viability. Sakaguchi: HA titre flat at 24 h while TCID50 is gone by 8 h. A
  persistence figure sourced from an RNA study is wrong by orders of magnitude
  for this model's purpose.
* **Quantity definition.** A half-life (Qian, Greatorex), a 99%-reduction time
  (Thompson), a log10 change at a fixed time (Perry, Noyce) and a
  "duration recoverable" (Bean, Oxford, Sakaguchi) are **four different
  quantities**. Thompson's 174.9 h to 99% on steel and Greatorex's 1.5 h
  half-life are not two estimates of one number; and Perry's <2 log10 over
  **7 days** on steel flatly contradicts Greatorex's nothing-detectable at
  **24 h** on steel, with matrix and inoculum differing between them.

The contradiction is reported, not adjudicated. Perry (mucin/serum, 18–25 °C,
7 days, ~1.5–2 log10) and Greatorex (BSA/DMEM, 17–21 °C, 23–24% RH,
undetectable by 24 h) are both direct measurements on stainless steel by
infectivity assay, and they disagree by more than a factor of ten in time.

> A later reading of this same table on a different axis — time since
> deposition rather than matrix — is
> [`../proposals/surface_decay_biphasic_spec.md`](../proposals/surface_decay_biphasic_spec.md).
> It adopts no value and changes nothing recorded here.

### 2.2 The null result for Q1

**No study measures `surface_decay_per_day` as the field defines it.** Nothing
in the literature reports a material-, matrix- and humidity-independent
surviving *fraction* per day, or a single exponential rate per day intended to
hold across those axes, and no paper found here reports its result in any
per-day unit at all. What is measured is a half-life or a log10 reduction over a
stated interval, on a stated material, in a stated matrix, at a stated
temperature and RH, by a stated assay. The field as currently defined therefore
has no measured referent, and the register's existing ⊘ field state on this row
is confirmed by search rather than by argument.

This is a field-definition blocker, not a missing paper. The norovirus half of
the same defect was resolved by moving the field to
`surface_decay_log10_per_day` (#41); influenza measures in the same unit, so the
same move is available — but even after it, the sourced quantity is an interval
conditioned on matrix and RH, not a point.

## 3. Q2 — Carrat 2008, verified against the primary text

**Yes. Carrat 2008 reports the illness endpoint as dose-independent, and the
repository's `p = 0.12` is correct.** From the Results, "Clinical illness / Any
symptoms" (HAL author copy of *Am J Epidemiol* 2008;167:775–785, page 779):

> "Thirty-eight subgroups (522 infected individuals) were considered (table 2).
> The proportion of symptomatic infection (any symptoms) was 66.9 percent
> (95 percent CI: 58.3, 74.5). No significant difference was noted according to
> the virus type (refer to table 2 for p values) or the initial infectious dose
> (p = 0.12)."

Denominators and design, from the same paper:

* **56 studies, 1,280 healthy participants** challenged with wild-type virus,
  placebo-treated or untreated; 532 challenged with A/H1N1, 473 A/H3N2, 86
  A/H2N2, 189 type B.
* The illness endpoint's own denominator is **522 infected individuals in 38
  subgroups** — i.e. the endpoint is conditional on infection, which is exactly
  the endpoint the model's `illness_probability` claims to be.
* **Inoculum range: 3 to 7.2 log10 TCID50** — 4.2 orders of magnitude. The null
  is therefore tested over a wide dose span, not a narrow one.
* Lower respiratory symptoms, 21.0% (95% CI 14.0–30.3) in 119 infected
  participants, likewise "did not differ between virus types and subtypes or
  according to the inoculated dose".
* Duration of shedding averaged 4.80 days (95% CI 4.31–5.29) over 375
  participants; shedding **does** scale with dose ("a dose-ranging study showed
  that the duration of shedding was proportional to the intranasal dose"), which
  is why an infection- or shedding-indexed dose effect must not be read across
  to the illness endpoint.

And the one dose association Carrat does find on a clinical endpoint runs the
**wrong way** for a monotone increasing form:

> "A negative link was found between the dose and the proportion with fever (per
> log10 median tissue-culture infective dose increase: odds ratio = 0.56,
> 95 percent CI: 0.42, 0.73; p < 0.001)."

with, in the Discussion, "We found a striking negative link between the
inoculated dose and the proportion of fever. We have no explanation for this
result. Particularly, the apparent correlation was not due to a difference of
influenza subtypes or a time trend."

**Consequence for the shipped form.** `illness_probability` is
`1 − (1 + η·dose)^−γ`, strictly increasing in dose. Carrat's illness endpoint is
flat in dose across 4.2 orders (p = 0.12) and its fever sub-endpoint is
*decreasing*. The dose-conditional form is therefore **refuted at the source the
repository already cites**, and 0.67 is a pooled population fraction with a CI —
not a parameter of a dose curve. Recording this as refuted is the finding; what
replaces the form is a model decision and is not proposed here.

### 3.1 Does any other synthesis measure the same endpoint?

Nothing found measures illness-given-infection against dose as a *measurement*.
The candidates and what each actually measures:

| Source | Endpoint it actually measures | Same as ours? | Grade for this question |
|---|---|---|---|
| Carrat 2008, DOI [10.1093/aje/kwm375](https://doi.org/10.1093/aje/kwm375), Consensus `https://consensus.app/papers/details/90db659d948255848058d857a75c679f/` | Symptomatic **among infected**, pooled, tested against inoculum | **Yes** | **A** for the endpoint (pooled challenge studies are the target setting for a challenge-derived parameter); the dose test is a meta-regression across subgroups | 
| Teunis 2010, *Epidemics* 1(2):101, DOI [10.1016/j.epidem.2010.10.001](https://doi.org/10.1016/j.epidem.2010.10.001) | **Fitted** hierarchical dose-response over 12 challenge studies, aerosol vs intranasal; reports "droplet transmission results in a slightly higher illness risk due to the higher doses involved" | Related and **opposite in direction**, but it is a **model output**, not a measurement: the illness-risk statement is a property of the fitted hazard, in a scenario study | **C** — flag: fitted. It is the only thing found that asserts dose-dependent illness, and it asserts it as a modelling result, not a measured association. Full text not open to this machine; graded on the abstract, deliberately conservatively |
| Watanabe 2012, *Risk Anal* 32(3):555, DOI [10.1111/j.1539-6924.2011.01680.x](https://doi.org/10.1111/j.1539-6924.2011.01680.x) | Beta-Poisson / exponential **infection** dose-response fitted to attenuated-reassortant challenge data | No — infection, not illness-given-infection | **C** (fitted) |
| Memoli 2015, *Clin Infect Dis* 60(5):693, DOI [10.1093/cid/ciu924](https://doi.org/10.1093/cid/ciu924) | Mild-to-moderate influenza disease (MMID) **among all challenged**, dose-finding; 69% at 10⁷ TCID50 | No — denominator is challenged, not infected; MMID requires shedding **and** symptoms | B for MMID, not this endpoint |
| Han 2019, *Clin Infect Dis* 69(12):2082, DOI [10.1093/cid/ciz141](https://doi.org/10.1093/cid/ciz141) | MMID by dose, H3N2, dose escalation 10⁴–10⁷ | No, same reason. Worth recording anyway: MMID was **44% at 10⁶ and 40% at 10⁷** — non-monotone at the top, in 37 participants of whom 16 shed and 27 had symptoms | B for MMID |
| Watson 2015, *Virol J* 12:13, DOI [10.1186/s12985-015-0240-5](https://doi.org/10.1186/s12985-015-0240-5) | Laboratory-confirmed illness in a dose-ascending H1N1 challenge, 29 seronegative adults; 75% at 3.5×10⁶ TCID50 | No — denominator is challenged | B, small n |
| Shetty 2024, *J Virol* 98(12), DOI [10.1128/jvi.01612-24](https://doi.org/10.1128/jvi.01612-24) | 8-person H3N2 CHIM: shedding, aerosol emission, symptoms, environmental swabs | No — single dose level, n = 8; cannot test a dose association | B as primary data, ∅ for this endpoint |
| Canini 2010, *J Virol* 84(22):11957, DOI [10.1128/jvi.01318-10](https://doi.org/10.1128/jvi.01318-10) | Symptom and viral kinetics **fitted** to 44 challenged volunteers | No — model output | **C** (fitted) |

So the falsifiable shape resolves as: **refuted**, with the single dissenting
claim (Teunis 2010) being a fitted dose-response model rather than a
measurement, and therefore exactly the class of evidence the provenance skill
forbids adopting into a model that is scored on attack rates.

## 4. Rejected candidates, with reasons

Recorded so the next person does not re-find them and read the omission as an
oversight.

| Candidate | Why not used for the quantity |
|---|---|
| Weber & Stilianakis 2008, *J Infect* 57(5):361, DOI 10.1016/j.jinf.2008.08.013 | Review, and its "daily inactivation rate constants … in the order of 1–10²" is a **collation across media**, not a measurement; adopting a per-day rate from it would import the exact unit ambiguity this tranche is trying to expose |
| Zhang 2024, *Front Microbiol*, DOI 10.3389/fmicb.2024.1463056 | Narrative review of stability and disinfectants; no primary measurement |
| Thomas 2013, *Clin Microbiol Infect*, DOI 10.1111/1469-0691.12324 | Survival on **human fingers**, minutes; wrong material for `surface_decay_per_day`, and skin is a separate mechanism the model does not carry here |
| Mukherjee 2012, *Am J Infect Control*, DOI 10.1016/j.ajic.2011.09.006 | Naturally contaminated hands and household surfaces; the value it reports is a deposited **titre** (<2.15×10¹–2.94×10¹ TCID50/mL), useful for inoculum, not a decay quantity |
| Nan Zhang 2026, *Int J Hyg Environ Health*, DOI 10.1016/j.ijheh.2026.114766 | Hand↔fomite **transfer** rates, and measured as **RNA by RT-qPCR** on artificial skin. Wrong quantity (transfer, not decay) and wrong assay |
| Anderson 2021, *Appl Environ Microbiol*, DOI 10.1128/aem.01215-21 | Transfer rates, and uses **Phi6/MS2 surrogates**, not influenza |
| Ansari 1991, *J Clin Microbiol*, DOI 10.1128/jcm.29.10.2115-2119.1991 | Parainfluenza 3 and rhinovirus 14, not influenza A |
| Bandou 2022, *Emerg Infect Dis*, DOI 10.3201/eid2803.211752 | H5N1 on skin/plastic (~26 h plastic, ~4.5 h skin). Avian subtype and a skin-focused model; recorded for context, not adopted for a human seasonal arm |
| Szpiro 2023, *Materials*, DOI 10.3390/ma16072889 | Antiviral **active-material** efficacy testing; the surface is the intervention, not the setting |
| La 2021, *Biosyst Eng*, DOI 10.1016/j.biosystemseng.2021.05.005 | Animal-disease dose-response fitted with CFD; wrong host, and fitted |
| Jones 2018, *Risk Anal*, DOI 10.1111/risa.12854 | Occupational burden estimated by applying a dose-response function; a model output whose answer is "highly dependent upon the dose-response function" — i.e. it consumes the parameter we are sourcing |
| Noyce 2007 copper arm; Qian 2023 copper arm | Copper is a virucidal material, not a maritime cabin surface. Retained above only as the contrast that shows material can dominate when the material is active |

## 5. Null and unresolved findings, stated plainly

1. **`surface_decay_per_day` has no measured referent** as defined (§2.2). No
   paper reports a surviving fraction per day, or a single per-day exponential
   rate meant to span material, matrix, temperature, RH and drying state.
2. **No infectious-virus half-life was found for influenza A on stainless steel
   or plastic in *human saliva*, at cabin temperature, with a stated CI.** Rockey
   2024 measures saliva but reports matrix-and-RH decay behaviour rather than a
   tabulated per-material half-life at a maritime condition; Qian measures airway
   surface liquid, which is a different secretion.
3. **No study found measures illness-given-infection against dose in a single
   cohort.** Carrat's dose test is a meta-regression across 38 subgroups; every
   individual dose-escalation study uses MMID or laboratory-confirmed illness
   among *all challenged*, which is a different denominator.
4. **Teunis 2010's primary text could not be read** (paywalled; Cloudflare
   blocked the publisher on this machine). Its grade above is deliberately
   conservative in consequence, and its claim is a fitted model either way.
5. **Carrat's inverse dose–fever association is unexplained by its own authors.**
   It is reported here because it is inconvenient for any monotone dose form, and
   because omitting it would misrepresent the source.

## 6. What this tranche does not do

It does not choose a value, an interval endpoint, or a unit for the field; it
does not convert any measurement into a per-day quantity; it does not touch
`edison_10pathogen_profiles.json`, `active_profiles.json`, the register, the
schema or the engine. The proposed register row is in
[`fragments/influenza-surface.md`](fragments/influenza-surface.md).
