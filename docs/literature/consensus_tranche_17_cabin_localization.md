# Tranche 17 — the cabin-localization fraction `f` is not measured anywhere, and the cruise data that exist bound it from above at well under a half

**Status:** Evidence assembled and interpreted, **sourcing only**. **No profile
constant, engine constant, config value or code path changes in this document**,
and the authoritative register is not edited here — this tranche's proposed
register row lives in [`fragments/cabin-localization.md`](fragments/cabin-localization.md)
for the lead to merge. Like every document in `literature/`, this is context,
not truth: where it and the register disagree, the register holds the status and
this document holds the citations.

**Scope:** unit `cabin-localization`, task **#12**. One quantity: the
cabin-localization fraction `f`.

**Method:** Consensus MCP, unfiltered on every pass (no `year_min`, no
`study_types`, no `exclude_preprints`; the filter set was never reached for).
Seven queries, recorded verbatim in §2. Truncated result sets were read to the
tail in the overflow files, which is how the two closed-setting room studies and
the transmission-chain reconstruction were found — they ranked below reviews.
Full texts were fetched by DOI where they exist openly; §7 records which ones do
not, because that limitation is the reason the bound in §5 is arithmetic rather
than read off a Results table.

**Result in one line:** **no study measures `f`.** The three cruise datasets
that report a cabinmate association bound it from above; the bound is
**`f ≤ 0.18–0.45`** depending on which dataset supplies the association, against
a hard structural ceiling of **`f ≤ 0.5`** for double-occupancy cabins. No
credible evidence supports a *lower* bound at all.

---

## 1. The quantity, and what would count as measuring it

`f` is the fraction of all norovirus transmission events on a voyage in which
infector and infectee shared a stateroom, as against every other location —
dining rooms, public areas, toilets, excursions, crew spaces.

Three things follow from the definition and constrain what can be adopted.

1. It is a **fraction of transmission events**, not a risk, a rate, a risk ratio
   or an attack rate. Nothing found in this tranche is reported in those units.
2. It is **route-attributive**: it requires knowing *where* each infection
   happened, which requires either a reconstructed transmission tree or a design
   that separates cabin exposure from the exposures cabinmates share anyway.
3. It is **structurally capped by cabin occupancy.** In a cabin of `n` occupants,
   at most `n−1` of the cabin's cases can have been infected in that cabin: the
   first case in any cabin was infected somewhere else, by construction. For the
   double-occupancy cabins that dominate cruise passenger decks, `f ≤ 0.5` even
   in the limiting world where every non-index cabin occupant was infected by
   their cabinmate and nobody was ever infected anywhere else. This ceiling
   requires no literature at all, only the occupancy distribution, and it is the
   single most robust statement in this document.

## 2. Queries, verbatim

All unfiltered; `search` called with `query` only.

1. `norovirus cruise ship outbreak ill cabin mate risk factor attack rate passengers`
2. `norovirus household secondary attack rate index case co-resident laboratory confirmed`
3. `norovirus household secondary attack rate pooled estimate household size susceptible contacts quantitative`
4. `norovirus outbreak room-level clustering shared room attack rate military barracks dormitory`
5. `hotel norovirus outbreak room clustering guests sharing room attack rate investigation`
6. `proportion of norovirus transmission occurring within household versus community setting attributable fraction`
7. `norovirus cruise ship outbreak secondary cases within cabins proportion of cabins with multiple cases travelling party`
8. `Diamond Princess attack rate by cabin occupancy within-cabin transmission quarantine passengers` — the one deliberately off-pathogen query, run because the Diamond Princess is the only closed-ship dataset in which cabinmate status was resolved by whole-genome sequencing (§4.4).

Queries 6 and 7 were written specifically to look for `f` in its own units — a
*proportion of transmission*, a count of *cabins with multiple cases*. Neither
returned a paper reporting either quantity for norovirus. That is the null in §6.

## 3. Grade A — direct measurement of `f` on cruise ships

**None.** No paper found reports the fraction of norovirus transmission
occurring within cabins, on any ship, in any outbreak. The register's existing
entry for #12 ("no measurement exists") survives this tranche unrefuted.

## 4. Candidates found, with grades

### 4.1 Cruise-ship cabinmate associations — right setting, wrong quantity, usable only as an upper bound

| Study | Design and population | Reported quantity | Value | Separates shared exposure? | Grade |
|---|---|---|---|---|---|
| Wikswo et al. 2011, *Clin Infect Dis* 52(9):1116–22, DOI [10.1093/cid/cir144](https://doi.org/10.1093/cid/cir144) ([Consensus](https://consensus.app/papers/details/815c23330d7c5ba1a10c3c22887727ab/?utm_source=unknown)) | Retrospective cohort, single ship, Jan 2009; 1,842 passengers, 1,532 (83.2%) responded, 236 cases = 15.4% of respondents; 12/14 stools RT-qPCR-positive, 5 sequenced GII.4 Minerva | Relative risk of being a case given an ill cabin mate | **RR = 3.0**, P < .01 (no CI reported in the abstract; full Results not openly accessible, §7) | **No.** Boarding-vomiting exposure (RR = 2.8) and public-activity participation were measured separately, but cabin exposure is not disentangled from shared dining, shared excursions or shared travelling party | **B** for `f` (A for the association it actually measures) |
| Chimonas et al. 2008, *J Travel Med* 15(3):177–83, DOI [10.1111/j.1708-8305.2008.00200.x](https://doi.org/10.1111/j.1708-8305.2008.00200.x) ([Consensus](https://consensus.app/papers/details/42c87a792cab5038b7d5bfb31a8c6125/?utm_source=unknown)) | Case-control within a VSP-investigated Alaska outbreak, May–Jun 2004; questionnaires to 2,018 cabins, 359 cases = 24.1% of respondents; 4/7 specimens norovirus-positive | Odds ratio of disease given a cabin mate sick with diarrhoea or vomiting, multivariable logistic regression | **OR = 3.40**, 95% CI 1.80–6.44 | **Partly.** No meal serving was associated with disease and no environmental deficiency was found, which weakens the shared-dining alternative; but a specific vomit-contaminated women's toilet *was* associated (OR = 5.13, 95% CI 1.40–18.78), which is precisely a shared public source, and travelling-party structure is not addressed | **B** for `f` |
| Mouchtouri et al. 2024, *Eurosurveillance* 29(10):2300345, DOI [10.2807/1560-7917.ES.2024.29.10.2300345](https://doi.org/10.2807/1560-7917.ES.2024.29.10.2300345) ([Consensus](https://consensus.app/papers/details/6dd55fef49eb505c977fab90d5b54e2d/?utm_source=unknown)) | Systematic review and meta-analysis, 45 outbreaks on 26 cruise ships, 1990–2020, from 13 articles and 5 reports; weighted attack rate 7% (95% CI 5–9) passengers, 2% (0–3) crew | "Having an ill cabin mate", reported as the most common risk factor across the reviewed investigations | **OR = 38.70**, 95% CI 13.51–110.86 | **No**, and it cannot: it is a synthesis across heterogeneous investigations with heterogeneous adjustment | **C** for `f` (review-level synthesis of primary associations) |

The Mouchtouri OR is two orders of magnitude away from the two primary studies'
associations, on the same setting and the same exposure. That disagreement is
reported here rather than resolved; it is exactly why §5 carries the bound at
three separate values rather than one.

### 4.2 Household secondary attack rates — the honest analogue, Grade B by construction

A cruise cabin is a small, poorly ventilated shared sleeping space with a shared
bathroom, shared for a week by two adults who usually chose each other. It is a
fair analogue for a household *bedroom pair* and a poor analogue for a household
as a whole, which typically includes children, a shared kitchen, and much longer
co-residence. Every value below is Grade B, and none of them is `f`: a SAR is
the probability that an exposed co-resident becomes a case, not the share of
transmission that happened at home.

| Study | Population and size | Quantity | Value | Household size | Grade |
|---|---|---|---|---|---|
| Quee et al. 2020, *Lancet Infect Dis* 20(9):1091–1100, DOI [10.1016/S1473-3099(20)30058-X](https://doi.org/10.1016/S1473-3099(20)30058-X) ([Consensus](https://consensus.app/papers/details/5f1f4a8c512f5cfd8a973257b555d166/?utm_source=unknown)) | Prospective Dutch household cohort, 604 households / 2,298 individuals; 150 norovirus-positive among 609 sampled AGE episodes; 34/96 households had a secondary norovirus AGE episode | Norovirus household SAR, laboratory-confirmed | **15% (37/244 participants)**; asymptomatic transmission 51% (52/102); microbiologically confirmed symptomatic transmission 10% (25/254) | ≥3 members by enrolment, children under two included | **B** |
| Balachandran et al. 2023, *Open Forum Infect Dis* 10(12):ofad619, DOI [10.1093/ofid/ofad619](https://doi.org/10.1093/ofid/ofad619) ([Consensus](https://consensus.app/papers/details/ebe23d880db15d7b930c71a3ef1213b4/?utm_source=unknown)) | US integrated health system, 2014–2016; 570 primary cases, 1,479 household contacts, 338 secondary cases | Secondary attack rate, **viral AGE (all enteric viruses, not norovirus-only)** | **23%** overall; contacts <5 y aOR 1.8 (1.2–2.6) | Mixed, includes young children | **B**, and the wrong denominator for a norovirus-specific value (§7) |
| Matsuyama et al. 2018, *J Int Med Res* 46(7):2705–2715, DOI [10.1177/0300060518776451](https://doi.org/10.1177/0300060518776451) ([Consensus](https://consensus.app/papers/details/adebee3eb0975a15adfed79e38632cb7/?utm_source=unknown)) | 380 households surveyed, 132 eligible, Japan | Household secondary attack risk for **noro-like** illness, clinical definition, not laboratory-confirmed | **13.8% (38/276)** | Not stratified | **B**, clinical case definition |
| Smoll et al. 2021, *PLoS ONE* 16(11):e0259145, DOI [10.1371/journal.pone.0259145](https://doi.org/10.1371/journal.pone.0259145) ([Consensus](https://consensus.app/papers/details/279c8bf34dd55005b6fbd14d70cae0cb/?utm_source=unknown)) | Childcare-centre-seeded outbreak, 52 symptomatic people in 19 household clusters | Household attack rate; also the split of transmission between settings | **36.5%, 95% CI 27.3–47.1**; 23 of 49 transmissions (46.9%) attributed to the childcare centre and the remainder to households | Not stratified | **B** — and see §5.3: this is the only paper found that reports a *setting split* of transmission at all |
| Phattanawiboon et al. 2020, *PLoS ONE* 15(7):e0236502, DOI [10.1371/journal.pone.0236502](https://doi.org/10.1371/journal.pone.0236502) ([Consensus](https://consensus.app/papers/details/d499aba31bd259fbba8ea83b3116bdef/?utm_source=unknown)) | 38 individuals in 16 Bangkok families, 716 stools over 12 months | Count of household transmissions, with asymptomatic source attribution | 4 household transmissions, 3 of them from asymptomatic individuals; 101/716 (14.1%) asymptomatic samples positive | Family units | **B**, no SAR denominator |
| Juniastuti et al. 2023, *J Med Virol* 95(10):e29164, DOI [10.1002/jmv.29164](https://doi.org/10.1002/jmv.29164) ([Consensus](https://consensus.app/papers/details/c7433d7ad5b05eb5b23ac34a331fa80e/?utm_source=unknown)) | 3 households, 1,105 weekly stools 2016–2020 | Intrafamily transmission counts; 3.4% of samples positive | 6 transmissions in one household, 2 in another, 0 in the third | 3 households | **B**, n too small to carry a rate |
| Marsh et al. 2017, *Epidemiol Infect* 146(2):159–167, DOI [10.1017/S0950268817002783](https://doi.org/10.1017/S0950268817002783) ([Consensus](https://consensus.app/papers/details/965fd1c2cece55dcb802e256aa3667ad/?utm_source=unknown)) | Household members of cases from three US norovirus outbreaks | Risk factors for secondary household transmission; reports IRRs, **not an SAR level** | Household with ≥2 primary cases adjusted IRR 2.0 (1.17–3.47); ≥1 primary case with diarrhoea adjusted IRR 2.8 (1.35–5.93) | Not stratified | **B**, ratios only |

Range across the laboratory-confirmed and clinical household SARs: **≈14–23%**
at household sizes of three or more. Note the direction of the analogue error:
these are per-contact probabilities in households with children and long
co-residence, and they are *not* interchangeable with a two-person cabin over
seven days in either direction.

### 4.3 Room-level clustering in other closed settings — Grade B, and the sharpest evidence in the tranche

| Study | Design | Quantity | Value | Grade |
|---|---|---|---|---|
| Fraenkel et al. 2021, *J Hosp Infect* 117:74–79, DOI [10.1016/j.jhin.2021.08.026](https://doi.org/10.1016/j.jhin.2021.08.026) ([Consensus](https://consensus.app/papers/details/53da3b582fcf5599b78290aead3a1402/?utm_source=unknown)) | Retrospective cohort, 33,788 room stays, five Swedish infectious-disease wards, 2013–2018, **with RNA sequencing of suspected room-transmission pairs** | Risk of acquiring norovirus from a prior room occupant; also risk from a roommate | 5/1,106 exposed vs 49 non-exposed acquired; univariable OR 3.3 (P = 0.01), **adjusted OR 1.9, P = 0.2 — not significant**; only 2 of the 5 exposed acquisitions carried an identical strain, giving an inferred **room transmission risk of 0.2% (95% CI 0.05–0.78%)**; **0 of 52** patients sharing a room with a roommate whose symptoms had resolved ≥48 h acquired norovirus | **B** |
| Fraenkel et al. 2018, *J Hosp Infect* 98(4):398–403, DOI [10.1016/j.jhin.2018.01.011](https://doi.org/10.1016/j.jhin.2018.01.011) ([Consensus](https://consensus.app/papers/details/669ea58d8c4b56ae86c3a30cb9d5a95d/?utm_source=unknown)) | Nested case-control, 65 outbreak index cases vs 186 sporadic cases, 192 wards | Odds of an outbreak per additional patient sharing the room with the index case | **OR 1.9 per additional roommate**, P < 0.01, multivariable | **B** |
| Harris et al. 2013, *BMJ Open* 3(12):e003060, DOI [10.1136/bmjopen-2013-003060](https://doi.org/10.1136/bmjopen-2013-003060) ([Consensus](https://consensus.app/papers/details/c0a70f0776f458cca4a01171905818cd/?utm_source=unknown)) | 149 hospital norovirus outbreaks, 65 with complete onset and bay position data; epidemic trees plus permutation test | Whether same-bay proximity is associated with transmission; serial interval estimated at **1.86 days (95% CI 1.6–2.2)** | Proximity significant, **P < 0.001**; robust while assumed serial interval < 2.5 days. **A hypothesis test, not a fraction** | **B** for the mechanism, **not a value for `f`** |

Fraenkel 2021 is the only study in this tranche that separates shared-source
from person-to-person transmission by sequence, and it is the only one that
lands on a *number* for a room-level route. Its number is very small, and it is
about a *prior occupant*, i.e. the environmental route, not a co-resident. Its
roommate arm (0/52) is a co-resident arm but only after symptom resolution, so
it bounds nothing about the infectious window.

### 4.4 Diamond Princess cabinmate attack rates — right ship geometry, wrong pathogen

Pluciński et al. 2020, *Clin Infect Dis* 73(10):e448–e457, DOI
[10.1093/cid/ciaa1180](https://doi.org/10.1093/cid/ciaa1180)
([Consensus](https://consensus.app/papers/details/bed816d36fa8598591638859d7316721/?utm_source=unknown)).
229 American passengers and crew interviewed after ship-based quarantine.
Attack rate **18% (58/329)** for passengers in single cabins or without infected
cabinmates, **63% (27/43)** with an asymptomatic infected cabinmate, **81%
(25/31)** with a symptomatic infected cabinmate; whole-genome sequences from
cabin-sharing passengers clustered together.

Reported here because it is the only cruise dataset found in which cabin
exposure is resolved by sequencing, and because it is the design template §8
asks for. It is **not** evidence about `f`: SARS-CoV-2, not norovirus; and the
cohort was under cabin quarantine, which is a deliberate maximisation of the
cabin route and the opposite of the free-mixing voyage `f` describes. **Grade C
for norovirus `f`; excluded from the bound in §5.**

## 5. The bound on `f`, and the arithmetic that produces it

### 5.1 The structural ceiling, which needs no literature

In cabins of occupancy `n`, `f ≤ (n−1)/n`. Passenger decks are predominantly
double occupancy, so **`f ≤ 0.5`**. Any value above 0.5 asserts that more cabin
occupants were infected in their cabin than there were non-index occupants to
infect. This holds whatever the literature says.

### 5.2 The bound implied by the cruise cabinmate associations

The three cruise studies report an association, not a fraction. Under two stated
assumptions the association plus the attack rate pins the *maximum* share of
cases that could be cabin-acquired.

Assumptions, both of which push the answer **up**, which is what makes the
result an upper bound rather than an estimate:

* **Double occupancy** for all cabins. Higher occupancy raises the ceiling in
  §5.1 and would loosen this bound; cruise passenger decks are mostly doubles.
* **The reported RR/OR is entirely causal cabin transmission.** It is not:
  cabinmates share dining rooms, excursions, toilets and travelling parties, so
  the association over-attributes to the cabin. Treating an OR as an RR (needed
  for Chimonas and Mouchtouri) inflates it further at these attack rates. Both
  errors run the same way, so the derived value is an over-estimate of `f`.

For a double cabin, let `p` be the passenger attack rate, so exposed persons per
cabin `= 2p` and unexposed `= 2 − 2p`; let `x` be the per-cabin expected number
of cases who have an ill cabinmate. Then
`RR = [x / 2p] / [(2p − x) / (2 − 2p)]`, giving `x = RR·(2p)² / (2 − 2p + RR·2p)`.
The share of cases with an ill cabinmate is `x/2p`; **at most half** of those can
be cabin-acquired, because one of every doubly-affected pair is that cabin's
index case and was infected elsewhere. The classical attributable fraction
`(x/2p)·(RR−1)/RR` is shown alongside as a cross-check; it is looser because it
does not impose the pair constraint.

| Source of the association | `p` | RR (or OR read as RR) | Share of cases with an ill cabinmate | **Upper bound on `f`** | Attributable-fraction cross-check |
|---|---|---|---|---|---|
| Wikswo 2011 | 0.154 | 3.0 | 0.353 | **0.177** | 0.235 |
| Chimonas 2008 | 0.241 | 3.40 | 0.519 | **0.260** | 0.366 |
| Mouchtouri 2024 pooled | 0.07 | 38.70 | 0.744 | **0.372** | 0.725 |
| Mouchtouri 2024, CI bounds | 0.07 | 13.51 / 110.86 | 0.504 / 0.893 | **0.252 / 0.446** | 0.467 / 0.885 |

**`f ≤ 0.18` from the single best-characterised cruise cohort (Wikswo), `f ≤ 0.26`
from the case-control study (Chimonas), `f ≤ 0.37` (CI 0.25–0.45) from the
pooled review association (Mouchtouri).** Every one of these sits under the
structural 0.5, as it must. Nothing in this tranche supports a **lower** bound:
`f = 0` is not excluded by any of these datasets, because a cabinmate
association is fully reproducible by shared non-cabin exposure.

This arithmetic is mine, not the papers'. It is Grade **C as a derivation**
resting on Grade A/B inputs, and it should be recorded as a bound, never as a
value.

### 5.3 The one direct setting-split in the tranche

Smoll et al. 2021 attribute **23 of 49 transmissions (46.9%)** to the childcare
centre and the remainder to households. That is the shape of number `f` is —
a split of transmission events between a shared-residence setting and a
public-mixing setting — measured for the wrong settings and a different
population structure. It is reported here as the closest existing analogue in
*units*, at **Grade B**, and it is emphatically not transferable to a cabin: the
attribution rests on an outbreak seeded in one identifiable public location.

## 6. Null results, stated explicitly

* **No paper reports the fraction of norovirus transmission occurring in cruise
  cabins.** Queries 1, 7 and 8 were written to find exactly that.
* **No paper reports the number or proportion of cabins with more than one case**
  in a cruise norovirus outbreak — the single summary statistic that would let
  §5.2 be replaced by a count instead of a derivation. Every cruise investigation
  found reports cabinmate *status* as a risk factor and never the cabin-level
  case distribution.
* **No paper reports a norovirus household SAR stratified to two-person adult
  households** with laboratory confirmation. Tsang 2018 reports a two-person
  stratum but by Bayesian model fit (§7).
* **No study of any closed setting reports within-room versus between-room
  transmission as a fraction of all transmission.** Harris 2013 tests the
  hypothesis and does not quantify the share; Fraenkel 2021 quantifies an
  absolute risk for one route.

## 7. Rejected candidates, with the reason

Recorded so the next person does not re-find them and read their absence as an
oversight.

| Candidate | Why rejected for `f` |
|---|---|
| **Towers et al. 2017**, *R Soc Open Sci* 4:170602, DOI [10.1098/rsos.170602](https://doi.org/10.1098/rsos.170602) ([Consensus](https://consensus.app/papers/details/af3a049d56f45b0581264ecd4e6854ad/?utm_source=unknown)) — combined R 6.1–9.5, environmental-only R 0.9–2.6 | **Fitted.** Route split inferred by fitting a transmission model to outbreak attack-rate data. Adopting it while scoring the model on attack rates is circular. Grade C |
| **Lei et al. 2018**, *Indoor Air* 28(3):394–403, DOI [10.1111/ina.12445](https://doi.org/10.1111/ina.12445) ([Consensus](https://consensus.app/papers/details/ef23b3eb72725babbfd3f8880bb5fba9/?utm_source=unknown)) — fomite contribution 85% (95% CI 83–87) | **Wrong quantity and modelled.** A route split (fomite vs other), not a location split (cabin vs elsewhere), produced by multi-agent simulation. Grade C |
| **De Bellis et al. 2025**, *J Travel Med*, DOI [10.1093/jtm/taaf059](https://doi.org/10.1093/jtm/taaf059) ([Consensus](https://consensus.app/papers/details/2d5c31362cfa53668e0f4eaee5850be1/?utm_source=unknown)) — Bayesian reconstruction of transmission chains from a 121-case cruise line-list, with a **cabin-sharing night-time route as an explicit free parameter** alongside on-board mixing and port acquisition | **Closest thing in existence to an estimate of `f`, and still rejected: it is fitted.** The per-route transmission rates are free parameters calibrated by MCMC to the outbreak's own line-list. The openly accessible manuscript text does not report the resulting cabin share; the abstract reports only R and superspreading (57% of secondary cases from 10% of infected individuals, 95% CrI 48–65). **Flagged for the lead**: if a cabin-route share is recoverable from its Appendix it is the single most relevant number in the literature, and it is *still* a model output fitted to attack-rate-like data, so it cannot be adopted while the model is scored on attack rates. Grade C |
| **Huang et al. 2020**, DOI [10.1101/2020.04.22.20074286](https://doi.org/10.1101/2020.04.22.20074286) ([Consensus](https://consensus.app/papers/details/33fce3654caf55c6ba2a70153ce0c94a/?utm_source=unknown)) — Diamond Princess chain-binomial model, "**proportion of infections in cabins 0.2**" | **Assumed, not measured**, and wrong pathogen. The 0.2 is an input to their scenario, not an output. Its numerical proximity to §5.2 is a coincidence and must not be read as corroboration. Grade C |
| **Tsang et al. 2018**, *Epidemiology* 29(5):675–683, DOI [10.1097/EDE.0000000000000855](https://doi.org/10.1097/ede.0000000000000855) ([Consensus](https://consensus.app/papers/details/72d39eb2cc935546a02245aeb96a5112/?utm_source=unknown)) — SAR 84% (95% CrI 60–96) in urban two-person households, 29% (9.6–53) in larger urban, 13% (0.51–54) rural two-person, 7.3% (0.38–27) rural larger | **Model-estimated, not directly observed**: Bayesian transmission model fitted to a community outbreak, with an environmental (water) route fitted simultaneously. It is also the *only* two-person-household stratum found, which is why it is documented rather than dropped — but a fitted 84% cannot enter a register that is scored against attack rates. Grade C |
| **Pluciński et al. 2020** (§4.4) | Wrong pathogen; cohort under cabin quarantine, which maximises the cabin route by design |
| **Balachandran et al. 2023** SAR 23% | Denominator is all viral AGE, not norovirus; retained in §4.2 as context only |
| **Kimura et al. 2010**, *Epidemiol Infect* 139(2):317–22, DOI [10.1017/S0950268810000981](https://doi.org/10.1017/s0950268810000981) ([Consensus](https://consensus.app/papers/details/29703bdeb68d54efb03bd74711df7dee/?utm_source=unknown)) — hotel outbreak, 372 guests and 72 employees, attack rate 15.0% (106/708) on the floor where a guest vomited vs 3.5% (163/4710) on another, RR 4.3 (3.4–5.5) | Right idea (spatial clustering in a lodging setting), **wrong unit of space**: floor-level, not room-level. Says nothing about shared-room transmission |
| Calderwood 2021 (13,092 LTCF outbreaks), Petrignani 2015, Parrón 2021, Lopman 2003, Bert 2013, Li 2023, Yu 2022, Zhang 2025, Wang 2026, Johnston 2007, Han 2020, Ourique 2024, Xu 2021, Ho 2015 | Setting-level surveillance and outbreak descriptions. They report attack rates by *population group* (residents vs staff, students vs teachers), never by room-sharing. No cabin- or room-level denominator |
| Xiao et al. 2017, DOI [10.3390/ijerph14121571](https://doi.org/10.3390/ijerph14121571) | Re-analysis of one hotel restaurant outbreak by multi-agent simulation; route inference by model fit to an attack-rate distribution. Grade C, and the wrong split |

**Access limitation, recorded because it bounds the tranche's precision.**
Wikswo 2011 and Chimonas 2008 are the two primary cruise datasets and **neither
has an openly accessible full text** (Europe PMC returns metadata and abstract
only for `10.1093/cid/cir144`; no PMC copy exists for either). Their Results
tables would contain the exposure prevalences and cabin-level counts that §5.2
has to derive from the attack rate instead. §5.2 should be redone against those
tables if the lead can obtain them; the derivation is the weakest link here.

## 8. What would actually measure `f`

A design that would produce `f` rather than an association, in decreasing order
of feasibility:

1. **Cabin-resolved line-list with onset times** — the minimum. Every case's
   cabin number and symptom onset, plus the cabin occupancy roster for the whole
   ship. This alone yields the count of cabins with 1, 2, 3… cases and the
   observed-versus-chance excess of multiply-affected cabins, which is a
   defensible upper bound on `f` without any model. De Bellis 2025 shows such
   line-lists exist in cruise-line GI logs; no investigation publishes the
   distribution.
2. **Sequencing of every case, or a systematic sample.** Whole-genome sequencing
   of within-cabin pairs versus randomly matched between-cabin pairs. Cabinmate
   pairs infected from a common dining-room source are as genetically close as
   pairs who infected each other, so sequence identity alone does not settle it —
   sequencing must be combined with 3.
3. **Onset-time sequencing within cabins.** Cabin pairs whose onsets are
   separated by about one serial interval (1.86 days, Harris 2013) are candidate
   within-cabin transmissions; co-primary pairs separated by less than an
   incubation period are common-source. The gap distribution within cabins,
   against the gap distribution between randomly paired passengers, separates the
   two without fitting a transmission model.
4. **Travelling parties split across cabins — the natural experiment that makes
   this identifiable.** Parties of four booked into two double cabins share
   dining, excursions and social contact but not a bathroom or a night's air.
   Comparing risk to a same-party different-cabin member against risk to the
   same-party cabinmate isolates the cabin's incremental contribution from every
   shared exposure that motivates the caveat in §5.2. Booking records already
   contain party identifiers. **This is the study that would settle `f`**, and
   nothing found in this tranche does it.
5. **Cabin environmental sampling with onset timing**, extending the cabin-swab
   approach the register already notes for Park 2015, to distinguish
   cabin-acquired infection from cabin-deposited contamination that follows an
   infection acquired elsewhere.

Absent 1–4, `f` remains bounded from above and unbounded from below, which is
what §9 records.

## 9. Outcome

**Evidence recorded, as an upper bound only. The direct measurement is a null.**

* No Grade A measurement of `f` exists. The register's existing null for #12 is
  correct and is not refuted by this tranche.
* The defensible statements are: `f ≤ 0.5` structurally at double occupancy, and
  `f ≤ 0.18–0.45` from the cruise cabinmate associations under the stated
  assumptions (§5.2), all of which over-attribute to the cabin.
* **No lower bound is supported.** No central value is proposed, and none should
  be read out of the numbers in §5.2 — every one of them is a ceiling.
* The register row this tranche proposes is in
  [`fragments/cabin-localization.md`](fragments/cabin-localization.md).
