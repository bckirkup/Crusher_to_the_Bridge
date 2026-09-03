# Tranche 11 — the never-symptomatic fraction: two designs, two answers, and no adult measured under natural exposure

**Status:** Evidence assembled and interpreted. **No profile constant, engine
constant, config value or register row changes in this document.** Every count
in §3 and §4 is reproducible from the cited papers; the register contribution is
in [`fragments/never-symptomatic.md`](fragments/never-symptomatic.md) and is the
lead's to merge.

**Scope:** task #53, tranche 11 — `never_symptomatic_fraction` (norovirus), the
sweep axis of the initiation engine that the model currently ships with **no
value at all**, enabling boarding without it being a load error rather than a
defaulted run. This tranche does not close that gate.

**Method:** Consensus MCP only, no filters on any query (§2 lists all nine
verbatim; query 10 was run to confirm counts at abstract level). Full text was fetched where the number mattered:
[Baker 2026](https://doi.org/10.1093/cid/ciag033) and
[Rouphael 2022](https://doi.org/10.1093/infdis/jiac045) are read at Results/table
level via PMC; the rest are marked in §3 and §4 as abstract-level, which is a
grade cap, not a formality — see §6.

---

## 1. The quantity, and why almost nothing measures it

The field is the fraction of **infected** hosts who never develop gastroenteritis
over the **whole course** of infection. Since PR #382 the model holds apart three
states the literature pools under "asymptomatic":

* never-symptomatic — infected, shedding, never ill;
* pre-symptomatic — infected, shedding, not yet ill;
* convalescent — ill, resolved, still shedding (Atmar 2008: 1–2 days of symptoms
  against a median 28 days of faecal shedding in the same 16 subjects).

Only a design that observed each infected subject across the episode can
separate them. That leaves **human challenge studies** and **prospective cohorts
with serial sampling and symptom diaries**. Everything else in the search —
cross-sectional stool-RNA prevalence, outbreak investigation, household
transmission attribution — measures a different quantity, and §5 rejects each
one by name. Bucardo's 2018 commentary on Qi makes the same point from the other
side: "norovirus detection in the convalescent phase might indicate long term
excretion rather than asymptomatic infection"
([DOI 10.1016/j.eclinm.2018.09.005](https://doi.org/10.1016/j.eclinm.2018.09.005)).

The finding of this tranche is that the two admissible designs **do not agree**,
that neither is in the model's population, and that within one design the answer
moves by a factor of nearly three depending on how "ill" is defined — in two
papers reporting the *same trial*.

## 2. Queries, verbatim

All unfiltered; the `search` tool's filters (`controlled`, `study_types`,
`year_min`, …) were not used on any of them. The probe query supplied with the
unit was not re-run.

1. `Norwalk virus human challenge volunteers number infected asymptomatic no gastroenteritis illness rate`
2. `prospective community cohort norovirus infections serial stool sampling proportion of infections that were symptomatic`
3. `adult household contacts norovirus infection prospective follow-up proportion of infected contacts remained asymptomatic`
4. `GII.2 Snow Mountain virus human challenge volunteers infection rate illness rate asymptomatic infected subjects`
5. `asymptomatic ratio norovirus volunteer challenge studies pooled reanalysis proportion of infections without symptoms`
6. `birth cohort norovirus infection to disease ratio secretor status Ecuador Nicaragua proportion of infections asymptomatic`
7. `adults longitudinal surveillance norovirus incidence of infection and illness ratio of infections to cases community population study`
8. `GII.4 norovirus human challenge secretor positive volunteers infected number developing gastroenteritis`
9. `Norwalk virus GI.1 vaccine placebo challenge trial infected subjects gastroenteritis proportion secretor positive`
10. `El-Heneidy norovirus community birth cohort Australian children weekly stool swabs asymptomatic infection episodes`

Consensus truncated most result sets; the overflow files were read in each case,
and query 6 is the reason Saito, Menon, O'Ryan, Lopman and Reyes appear in §5
rather than being missed — the cohort papers ranked below the reviews again.

## 3. Challenge studies — adults, but at doses far above natural exposure

Denominator throughout: **infected** subjects, as each paper defines infection
(RNA shedding and/or seroconversion). "Never-symptomatic" is the complement of
that paper's illness definition, computed here from its own counts.

| Source | Genogroup / inoculum | Secretor composition | Infected | Ill | **Never-symptomatic** | Grade |
|---|---|---|---|---|---|---|
| Graham 1994, *J Infect Dis*, [10.1093/infdis/170.1.34](https://doi.org/10.1093/infdis/170.1.34) | GI.1 Norwalk | not reported (pre-FUT2) | 41/50 (82%) | "68% symptomatic" | **32%**, denominator ambiguous | **C** — abstract only |
| Gray 1994, *J Clin Microbiol*, [10.1128/jcm.32.12.3059-3063.1994](https://doi.org/10.1128/jcm.32.12.3059-3063.1994) (17-subject subset of Graham) | GI.1 Norwalk | not reported | 14 | 9 | **5/14 = 36%** | B |
| Newman 2016, *Clin Exp Immunol*, [10.1111/cei.12772](https://doi.org/10.1111/cei.12772) (subjects pooled from two GI.1 challenge studies) | GI.1 | not reported | 26 | 19 | **7/26 = 27%** | B |
| Atmar 2011, *NEJM*, [10.1056/nejmoa1101245](https://doi.org/10.1056/nejmoa1101245), **placebo arm** | GI.1 Norwalk | per-protocol n = 77 across both arms | 82% of arm | 69% of arm | **≈16%**, derived as 1 − 0.69/0.82 | **C** — derived from two arm-level proportions, not a reported per-infected fraction |
| Atmar 2014, *J Infect Dis*, [10.1093/infdis/jit620](https://doi.org/10.1093/infdis/jit620) | GI.1 Norwalk | 8 secretor-negative excluded as nonsusceptible | 21 | 67% of infected | **33%** | B — abstract only |
| Frenck 2012, *J Infect Dis*, [10.1093/infdis/jis514](https://doi.org/10.1093/infdis/jis514) | **GII.4** (first GII.4 human challenge) | 23 secretors, 17 nonsecretors | 16/23 secretors | 12 norovirus-associated illness (13 "became ill") | **4/16 = 25%** (3/16 = 19% on the looser illness definition) | B — abstract only; no PMC deposit, OUP paywalled |
| Rouphael 2022, *J Infect Dis*, [10.1093/infdis/jiac045](https://doi.org/10.1093/infdis/jiac045) | **GII.2** Snow Mountain, 1.2×10⁴–1.2×10⁷ GEC | 36 secretor-positive, 8 secretor-negative | 24/38 (63%) | 75% of infected | **≈6/24 = 25%** | **B, Results/Table 1** |
| Qu 2025, *J Med Virol*, [10.1002/jmv.70546](https://doi.org/10.1002/jmv.70546), **primary** inoculum (2000–2002) | GII.2 Snow Mountain | not reported in abstract | 9/15 | 7 AGE | **2/9 = 22%** | B — abstract only |
| Qu 2025, same paper, **secondary** inoculum (2016–2018) | GII.2 Snow Mountain | as Rouphael | 25/33 | 9 AGE | **16/25 = 64%** | B — abstract only |

**The last two rows are the most important thing in this tranche.** Qu's
secondary-inoculum arm *is* the trial Rouphael reports. Rouphael, counting
"diarrhoea and/or vomiting" in infected subjects, gets 25% never-symptomatic;
Qu, counting subjects who "presented with acute gastroenteritis", gets 64% —
from the same volunteers. (The infected denominators also differ, 24/38 against
25/33, because the two papers take different analysis populations.) A factor of
2.6 in this parameter is available purely from the illness definition, with the
virus, the dose and the subjects held fixed.

Secretor status is a denominator, not a modifier, for GII.4: Frenck's 17
nonsecretors produced one ill subject and one single-day shedder, so a cohort's
nonsecretor share changes who can be infected at all. Rouphael's GII.2, by
contrast, infected secretor-negative subjects at 88% at the high dose — GII.2 is
not GII.4 in this respect and the two must not be pooled.

**Challenge interval, illness = diarrhoea and/or vomiting: [0.16, 0.36].**
Excluding the two rows graded C leaves **[0.22, 0.36]**. The 0.64 arm sits
outside it and is not averaged in; it is a different definition, recorded so that
the width of the definitional dependency is on the record.

## 4. Prospective community cohorts — the right design, the wrong population

| Source | Setting | Denominator | **Never-symptomatic** | Grade |
|---|---|---|---|---|
| Baker 2026 (PREVAIL), *Clin Infect Dis*, [10.1093/cid/ciag033](https://doi.org/10.1093/cid/ciag033) | 245 US children birth→2 y, **weekly** stool + weekly symptom survey; symptomatic = infection starting ≤4 d before or ≤14 d after AGE onset | 328 infections with known symptom status, coinfections excluded | **214/328 = 65.2%** | B |
| Baker 2026, adherent subset (≥18 mo, ≥70% of samples) | as above, 101 children | 219 infections | **143/219 = 65.3%** | B |
| Baker 2026, by genogroup (adherent, Table 2) | as above | GI 37; GII.4 Sydney 51; other GII 131 | **GI 30/37 = 81.1%**; **GII.4 Sydney 30/51 = 58.8%**; **other GII 83/131 = 63.4%** | B |
| El-Heneidy 2022, *Pediatr Infect Dis J*, [10.1097/inf.0000000000003667](https://doi.org/10.1097/inf.0000000000003667) | Australian community birth cohort, 158 children birth→2 y, **weekly** stool swabs (11,124) + daily vomiting/loose-stool diary; 183/221 (82.8%) of infection episodes GII | 209 infection episodes with symptom-diary data | **127/209 = 60.8%** (82 symptomatic, 39.2%) | B — abstract only |

**Community interval: [0.59, 0.68]**, and for GII specifically **[0.59, 0.63]**
(PREVAIL's two GII strata) with El-Heneidy's GII-dominated 0.61 inside it.
PREVAIL's GI figure of 0.81 is the highest number in this tranche and the model's
active arm is GII, so the genogroups are kept apart here rather than pooled.

Three properties of PREVAIL bear directly on adoption, and all three are
Results-level rather than inferred: symptomatic infections shed longer (median
18 d vs 10 d, p = .004); the median minimum Ct was lower in symptomatic
infections (23.0 vs 27.0, p < .001), **yet over half of the infections with the
highest viral loads were asymptomatic** (Ct < 20: 52.6%; Ct 20–24: 51.3%); and
symptom status was flatly not predicted by the mother's secretor status,
breastfeeding, childcare or prior infection, only by GII.4 Sydney, age and viral
load. The age term is the problem for this model — 71.1% of first-year
infections were asymptomatic against 61.2% in the second year, and **no child
had a symptomatic infection before 4 months**. The community figure is rising
with age across the only window it is measured in, and the model's population is
adults.

## 5. Rejected candidates, with the reason

**Outbreak-conditioned — the known trap, recorded so it is not re-found.** These
are the numbers the naive search surfaces first, they cluster at 18–22%, and
they are measured in populations conditioned on the very event this model is
scored against (VSP incidence, Diamond Princess, Greg Mortimer). Adopting one
would seed the model with its own outcome, under a citation.

* Miura 2018, *J Epidemiol*, [10.2188/jea.je20170040](https://doi.org/10.2188/jea.je20170040) — asymptomatic **ratio** 32.1% (95% CI 27.7–36.7) over 55 Japanese foodborne outbreaks; GII.4 40.7% (32.8–49.0). Doubly excluded: outbreak-conditioned, **and** a maximum-likelihood estimate from a statistical model of the surveillance process, i.e. an inferred quantity, not a count. Its own conclusion notes the ~30% is "consistent with those derived from volunteer challenge studies", which §3 independently reproduces from the counts.
* Wang 2023, *BMC Infect Dis*, [10.1186/s12879-023-08519-y](https://doi.org/10.1186/s12879-023-08519-y) — pooled asymptomatic **prevalence** in outbreaks 21.8% (17.4–27.3), 44 articles, 8,115 individuals; GII 20.1%, GI 19.8%.
* Wang 2024, *J Med Virol*, [10.1002/jmv.29393](https://doi.org/10.1002/jmv.29393) — 17.6% (14.1–21.3), China, 97 articles, 5,117 individuals; GII 17.1%.
* Qi 2018, *EClinicalMedicine*, [10.1016/j.eclinm.2018.09.001](https://doi.org/10.1016/j.eclinm.2018.09.001) — 18% (10–30) in outbreak contexts.
* Misumi 2021, *PeerJ*, [10.7717/peerj.11769](https://doi.org/10.7717/peerj.11769) — asymptomatic ratio 18.6%, GII.4 25.8%.

**Wrong quantity — prevalence, not a proportion of infections.** A prevalence of
RNA in a tested population has the tested population in its denominator, not the
infected; it also pools never-symptomatic, pre-symptomatic and convalescent
states, which is the distinction this unit turns on.

* Qi 2018, global 7% (6–9), adults 4%, children 8%, food handlers 3% — already carried by the register's boarding-prevalence row from [tranche 10](consensus_tranche_10.md) §3, where it belongs.
* Phillips 2010, *Epidemiol Infect*, [10.1017/s0950268810002839](https://doi.org/10.1017/s0950268810002839) — age-adjusted prevalence 12%.
* Yu 2024, *IJID Regions*, [10.1016/j.ijregi.2024.100549](https://doi.org/10.1016/j.ijregi.2024.100549) — norovirus in 219/2,031 (10.8%) asymptomatic stool samples. A per-sample prevalence, not a per-infection proportion.
* Kobayashi 2022, *Infect Dis*, [10.1080/23744235.2022.2134447](https://doi.org/10.1080/23744235.2022.2134447) — 14/288 (4.9%) adults RNA-positive at ~600-day follow-up. Longitudinal, but it re-screens for *positivity*; it never observes a symptom course, so it cannot say who never became ill.
* Phattanawiboon 2020, *PLoS ONE*, [10.1371/journal.pone.0236502](https://doi.org/10.1371/journal.pone.0236502) — 101/716 (14.1%) samples from symptom-free individuals positive, 89.1% of positives from people with no diarrhoea. Per-sample again.

**Wrong quantity — transmission attribution.**

* Quee 2020, *Lancet Infect Dis*, [10.1016/S1473-3099(20)30058-X](https://doi.org/10.1016/S1473-3099\(20\)30058-X) — asymptomatic transmission rate 51% vs symptomatic 10% in 604 households. A rate among exposed household members, not the symptom fate of infected subjects.
* Juniastuti 2023, *J Med Virol*, [10.1002/jmv.29164](https://doi.org/10.1002/jmv.29164) — 1,105 weekly samples from three households, 3.4% positive, most from asymptomatic individuals. No infection-episode denominator; n = 3 households.

**Right design, no per-infection symptom denominator.** These birth cohorts
sampled on diarrhoea plus a routine or random non-diarrhoeal draw, so an
"infection" is not observed as an episode with a symptom status.

* Lopman 2014, *J Infect Dis*, [10.1093/infdis/jiu672](https://doi.org/10.1093/infdis/jiu672) (Ecuador, 194 children) — norovirus in 79/438 diarrhoeal (18%) and 181/1,016 diarrhoea-free (18%) samples, p = .919. Striking, and not this quantity.
* Saito 2013, *Clin Infect Dis*, [10.1093/cid/cit763](https://doi.org/10.1093/cid/cit763) (Peru) — diarrhoeal samples plus randomly selected non-diarrhoeal ones; reports infection and diarrhoea incidence separately, not per-infection symptom status.
* Menon 2016, *PLoS ONE*, [10.1371/journal.pone.0157007](https://doi.org/10.1371/journal.pone.0157007) (India) — screens diarrhoeal and vomiting episodes only; asymptomatic infections are outside the sampling frame, as its own conclusion says.
* Reyes 2021, *J Infect Dis*, [10.1093/infdis/jiab316](https://doi.org/10.1093/infdis/jiab316) (Nicaragua, 443 children) — AGE-episode denominator throughout; measures incidence of *symptomatic* infection by HBGA.
* O'Ryan 2009, *Pediatr Infect Dis J*, [10.1097/inf.0b013e3181a4bb60](https://doi.org/10.1097/inf.0b013e3181a4bb60) (Chile) — monthly asymptomatic screening plus AGE sampling, reported as 8% of 2,278 samples and 18% of 145 AGE episodes; the two denominators cannot be combined into a per-infection fraction.

**Model output, not a measurement.**

* Lopman 2014, *Am J Epidemiol*, [10.1093/aje/kwt287](https://doi.org/10.1093/aje/kwt287) — a dynamic transmission model in which asymptomatic point prevalence moves from 3% to 48% with R₀. It is a simulation of the very quantity at issue, driven by a transmission parameter this model is scored on. **Flagged: fitted/simulated, not adoptable.** It is, however, the clearest available statement of *why* the outbreak figures in §5 are high.
* Teunis 2020, *Epidemics*, [10.1016/j.epidem.2020.100401](https://doi.org/10.1016/j.epidem.2020.100401) — dose-response fitted jointly to challenge studies and outbreaks. Its illness/infection risk ratios (≈0.2/0.28 GI, ≈0.035/0.076 GII in secretor-positives) would imply a far larger never-symptomatic fraction for GII, but they are fitted, dose-dependent, and partly fitted **to outbreaks**. Not a measurement of this field.

**Off-target.** Sah 2021 (*PNAS*), Oran 2021 (*Ann Intern Med*), Yanes-Lane 2020,
Buitrago-Garcia 2020 and the other SARS-CoV-2 asymptomatic-fraction
meta-analyses recur in every query on this phrasing. Different pathogen; the
20–31% they report is not evidence about norovirus and is recorded only because
the search returns it every time.

## 6. Null results, and the one that matters

1. **No study measures this quantity in adults under natural exposure.** Every
   adult figure in this tranche is a challenge dose orders of magnitude above a
   natural inoculum; every natural-exposure figure is in children under three,
   in a cohort where symptom probability is still climbing with age. The
   model's population — adult passengers and crew boarding a ship — is measured
   by neither. Query 7 was aimed squarely at this and returned incidence
   surveillance, seroprevalence and outbreak reviews; the closest adult
   longitudinal study (Kobayashi 2022) re-screens for positivity and never
   observes a symptom course. **This is the null result of the unit**, and it is
   why no interval here is adoptable as a point value.
2. **No maritime measurement of any of it**, consistent with tranche 10 §6.
3. **The illness definition is worth more than the population.** Qu against
   Rouphael on identical volunteers gives 22–64%; PREVAIL against the challenge
   set gives 25% against 65%. Before any value is adopted the model must state
   which definition of "presents symptoms" its `never_symptomatic` state means —
   any vomiting or diarrhoea, or an AGE case definition — because that choice is
   larger than the difference between a child in a birth cohort and an adult
   swallowing 10⁷ GEC.
4. **Three of eight challenge rows and one of two cohort rows are abstract-level
   only** (no PMC deposit; publisher paywall). Graham 1994's "68% symptomatic"
   has an ambiguous denominator in its abstract — 68% of 50 challenged and 68%
   of 41 infected are different quantities — which is exactly the failure mode
   the repository has been bitten by before, so it is graded **C** here rather
   than being read charitably. Gray's 5/14 and Newman's 7/26, both explicit
   counts from that same volunteer set, are what carry the GI.1 estimate.

## 7. What this tranche licenses, and what it does not

**Licensed as evidence (not applied here, and not merged into the register by
this document):**

1. A **challenge-study** interval for the never-symptomatic fraction among
   infected adults, **[0.22, 0.36]**, Grade B, from explicit counts in GI.1
   (Gray, Newman, Atmar 2014), GII.4 (Frenck, 4/16) and GII.2 (Rouphael, 6/24) —
   at inocula far above natural exposure, with illness defined as diarrhoea
   and/or vomiting.
2. A **community-cohort** interval, **[0.59, 0.68]** overall and **[0.59, 0.63]**
   for GII, Grade B, from weekly-sampled birth cohorts (PREVAIL 214/328;
   El-Heneidy 127/209) — in children under three, in whom the fraction is
   measurably falling with age.
3. The explicit statement that these are **not two estimates of one number**.
   They do not overlap, they are not to be pooled or averaged, and the gap
   between them is dose, age and case definition rather than measurement error.
4. A **null** on the field as the model's population defines it (§6.1), which
   leaves the boarding gate shut — the safe state, and the state the load error
   was built to protect.

**Explicitly not licensed:**

- No single central value, and no pooled challenge-plus-cohort figure.
- No value from an outbreak population (§5), and no value tuned so that VSP
  incidence, the Diamond Princess or the Greg Mortimer comes out right. No
  anchor effect was computed for any candidate in this tranche.
- No value from Miura's 32.1%, however closely it happens to match §3 — it is
  outbreak-conditioned and model-inferred, and the coincidence is not evidence.
- No adoption of Graham's 32% as a count; its denominator is not established
  from the abstract.
- No claim that the challenge figure transfers to natural exposure, or that the
  paediatric figure transfers to adults. Both transfers are unmeasured, and an
  adult natural-exposure cohort with serial sampling would settle the field
  outright.
