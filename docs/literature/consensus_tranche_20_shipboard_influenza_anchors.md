# Tranche 20 — Shipboard influenza: the anchor set, and the endpoint ladder inside it

> **Status:** Evidence assembled. No profile constant, engine constant, schema,
> grade, interval or adoption state changes in this document. Nothing here is
> adopted, and no anchor is declared: the authoritative per-quantity state
> stays in [`../parameter_provenance_register.md`](../parameter_provenance_register.md),
> and what activating the influenza arm would require is set out in
> [`../proposals/influenza_arm_activation_plan.md`](../proposals/influenza_arm_activation_plan.md).

**Scope.** The influenza arm (`influenza_a`, register §3.3) is not in
`data/pathogens/active_profiles.json`, so nothing on it is loaded by a run
today. Activating it raises a question the norovirus and COVID arms never had
to ask, because VSP answered it for them: **what would an influenza arm be
scored against?** VSP postings are acute *gastroenteritis* only — the reporting
rule itself is gastrointestinal (13-or-more passengers, foreign itinerary, US
ports) — so the 428-posting series is not an influenza anchor and never can be.
This tranche asks whether the shipboard influenza literature supplies one.

It does. It also shows that the answer is not a number but a **ladder**, and
that the rung matters more than the ship.

Search route: `consensus` MCP `search`, two queries, no filters. Full text for
the two anchor-quality reports through PubMed Central
(`efetch db=pmc`, PMC4869710 and PMC3294517) — both are open, so §1 and §2
are read off the papers' own Results, not their abstracts. Europe PMC reports
no open full text for Brotherton 2003 or Fernandes 2014; those two stay at
abstract level and are marked as such.

---

## 1. The anchor set

Five outbreak reports carry a denominator. Two of them are open full text and
usable at Results level; one is unusable as a rate.

| Ship / report | Voyage | Denominator | Endpoint as measured | Value |
|---|---|---|---|---|
| Millman 2015 Ship A (DOI [10.1111/jtm.12215](https://doi.org/10.1111/jtm.12215), PMC4869710) | 17 d, South America → Los Angeles, Mar 2014 | 2,595 pax, 1,057 crew | **MAARI** (ILI or ARI presenting to the infirmary) | pax **97/2,595 = 3.7%**; crew **33/1,057 = 3.1%** |
| Millman 2015 Ship B | 17 d, same itinerary shape, Mar–Apr 2014 | 2,987 pax, 1,157 crew | MAARI | pax **187/2,987 = 6.2%**; crew **54/1,157 = 4.7%** |
| Ward 2010 (DOI [10.3201/eid1611.100477](https://doi.org/10.3201/eid1611.100477), PMC3294517) | 10 d ex-Sydney, May 2009 | 1,970 pax, 734 crew | **NAT-confirmed infection**, sick during cruise or ≤7 d after | pax **76 (3.9%) pandemic + 98 (5.0%) seasonal + 2 (0.1%) both = 176/1,970 = 8.9%** |
| Ward 2010, same voyage | — | same | **ILI seeking medical attention on board** | pax **13/1,970 = 0.7%**; crew **20/734 = 2.7%** self-reported ILI |
| Brotherton 2003 (DOI [10.1017/s0950268802008166](https://doi.org/10.1017/s0950268802008166)) — abstract only | Sydney–Noumea, Sep 2000, in Sydney's influenza peak | 1,119 pax (836 responded, 75%), ~400 crew | **self-reported ILI**, postal questionnaire at 3 weeks | **310/836 = 37%**; 528 (63%) saw a doctor for cruise-related illness; 40 hospitalised, 2 deaths |
| Miller 2000 (DOI [10.1086/313974](https://doi.org/10.1086/313974)) | 10 d, North America, Sep 1997 (cruise 2 of 3) | 1,284 pax | **self-reported ARI** | **215/1,284 = 17%**; 77% of pax aged ≥65 |
| Fernandes 2014 (DOI [10.1111/jtm.12132](https://doi.org/10.1111/jtm.12132)) — abstract only, no open full text | off São Paulo, Feb 2012 | **not in the abstract** | ARI case count | 104 cases (54 crew, 50 pax) — **no rate is computable**; lower-deck crew OR 2.39 (1.09–5.25), age 18–32 OR 3.72 (1.25–11.16) |

Two reviews bound the set rather than adding to it: Bell 2014
(DOI [10.1016/j.amepre.2013.10.014](https://doi.org/10.1016/j.amepre.2013.10.014))
gives "reported attack rates range from 3.8% to 37%" and respiratory illness as
~27% of all recorded shipboard illness; Mouchtouri 2009
(DOI [10.2807/ese.14.21.19219-en](https://doi.org/10.2807/ese.14.21.19219-en))
counts nine confirmed influenza outbreaks linked to passenger ships across
1997–2005, "attack rates up to 37%". Gupta 2020
(DOI [10.1016/j.mjafi.2020.06.003](https://doi.org/10.1016/j.mjafi.2020.06.003))
reports H1N1 AR 4.83% on a **warship**, excluded on vessel class.

**The 3.8–37% span that both reviews quote is not a range of transmission.** It
is the ladder in §2 read as if it were one quantity.

## 2. The ladder, measured twice on the same voyage

Ward 2010 measures two rungs in one population, which is what makes it the most
valuable report in the set:

```
NAT-confirmed infection, passengers        8.9%   (176/1,970)
ILI presenting to the ship's infirmary     0.7%   (13/1,970)
                                          ------
implied on-board medically-attended capture  ≈ 0.08 of infections
```

For comparison, the norovirus arm's A3 infirmary capture is **0.60 ± 0.05**.
If ~0.08 survives scrutiny, respiratory illness is **roughly an order of
magnitude less visible to a ship's infirmary than gastroenteritis** — which is
mechanically plausible (self-limiting coryza against explosive vomiting and a
mandatory reporting culture) and is the single most consequential number in
this tranche for an observation model.

Three independent constraints on the same ladder, from outside the maritime
setting:

- **Carrat 2008** (already adopted on this arm, register §3.3): **66.9%**
  (95% CI 58.3–74.5) of infections are symptomatic, dose-independent over 4.2
  orders of inoculum.
- **Huang 2018 SHIVERS** (DOI [10.1093/infdis/jiy443](https://doi.org/10.1093/infdis/jiy443)):
  a population seroepidemiological cohort, 2015 New Zealand — infection in
  **321/911 = 35%** of unvaccinated participants; **only about a quarter of the
  infected reported PCR-confirmed ILI, and about a quarter of those sought
  medical attention** (≈6% of infections medically attended). Also:
  **31% of seroconversions were NAI-only**, so HAI-only serology undercounts
  infection by about a third.
- **Ortiz 2023** (DOI [10.1093/infdis/jiad021](https://doi.org/10.1093/infdis/jiad021)):
  H1N1pdm09 controlled human infection — MMID in **54/76 = 71.1%**; baseline
  HAI ≥40 gave 64.9% against <40's 76.9%, OR **0.81** per two-fold HAI
  (0.62–1.06, **p = 0.126**).

Ward's ship figure (≈8%) and SHIVERS' community figure (≈6%) agree to within
their own imprecision, from completely different designs. Carrat's 66.9%
symptomatic and SHIVERS' ~25% "reported PCR-confirmed ILI" do **not** agree,
and that disagreement is a definition, not an error: a challenge study with an
active symptom diary and a weekly community cohort with a self-reported ILI
trigger are measuring two different endpoints. This is the same pattern as
tranche 11, where the illness *definition* moved the never-symptomatic fraction
more than the population did.

**Consequence.** "Influenza attack rate on a cruise ship" is not a scorable
quantity until the rung is named. A model reproducing 3.7% MAARI and a model
reproducing 8.9% infection are not in conflict; a model tuned to reproduce 37%
would be reproducing a postal questionnaire in an influenza-peak embarkation
port.

## 3. What the full texts add that no abstract carries

### 3.1 The passenger/crew ratio is *not* norovirus's

| Report | pax | crew | ratio |
|---|---:|---:|---:|
| Millman Ship A (MAARI) | 3.7% | 3.1% | **1.19** |
| Millman Ship B (MAARI) | 6.2% | 4.7% | **1.32** |

The norovirus anchor A5 is **~2.9–3.5** on reported attack rates. On the same
kind of hull, in the same reporting frame, influenza's ratio is near unity.
Crew MAARI also concentrates in **food service** (57.6% of Ship A's crew cases,
38.9% of Ship B's) — the same occupational excess the Diamond Princess reported
for SARS-CoV-2 — so the difference is not "crew under-report" in general.
Whatever mechanism produces A5 ≈ 3 for norovirus must **not** be a
pathogen-independent crew/passenger structural term, or the influenza arm will
be wrong by ~2.5× the moment it is switched on. This is a test the ship and
crew models have never faced.

### 3.2 Vaccination, as measured, is not a susceptibility knob

- Millman Ship A: crew coverage **90%**, and **31/33 (93.9%)** of crew *with*
  MAARI reported vaccination. Ship B: coverage **95.5%**, and **all** crew with
  MAARI reported vaccination. Passenger vaccination among MAARI cases: 67.0%
  (A), 82.8% (B).
- Brotherton 2003: a third of passengers vaccinated, with neither ILI nor
  hospitalisation rates significantly different, and a case-control study
  finding no significant protective effect.
- Ortiz 2023: the putative seroprotective HAI titre ≥40 does not separate the
  infected from the uninfected (p = 0.126).

Read together, these say that a scalar `base_susceptibility` calibrated as
"fraction susceptible after vaccination and prior exposure" has **no measured
referent that behaves like a fraction**, and that vaccination coverage cannot
be converted into one. What *is* measured is subtype- and age-specific: Ward's
pandemic H1N1 relative risk was **17.4 (10.5–29.1)** in children 3–6 and
**zero cases** in passengers >65, while H3N2 was flat across every age band on
the same voyage.

### 3.3 Influenza has its own posting rule, and it is voluntary

CDC's maritime **ILI outbreak threshold is 1.38 cases per 1,000 traveler-days**
(Millman, Methods), and seasonal-influenza reporting is **voluntary** — unlike
VSP's mandatory AGE reporting. Millman records the cumulative rates at
threshold crossing: Ship A pax 2.70 and crew 1.89, Ship B pax 2.00, while
Ship B's crew rate **never** crossed.

Two consequences, both of which are about the observation model and neither of
which is a transmission parameter:

1. The influenza posting definition has a **traveler-day denominator**, so it
   is not the same functional form as VSP's 3%-of-passengers rule. A shared
   "posting" mechanism across arms would be wrong on this arm.
2. Because reporting is voluntary, the fleet count of influenza outbreaks is
   **self-selected**. This is a stronger version of the blocker tranche 18
   found for VSP: no absolute influenza posting rate is inferable, and a fleet
   count of influenza outbreaks cannot serve as a likelihood the way #399's
   ruling allows for norovirus.

### 3.4 Importation is pre-embarkation, and it is plural

On both Millman ships, laboratory-confirmed cases had onset **before** departure
(Ship A: the index case 5 days before Day 0, plus nine more symptomatic before
Day 0), while influenza activity at every port of call was low. Ship A carried
**three co-circulating viruses** — A(H1N1)pdm09, A(H3N2) and B — and Ward's
single voyage carried two subtypes with two co-infections.

That is a direct contradiction of the one-founder-per-voyage simplification
that the norovirus class decision leaned on: for influenza, multiple
independent importations at embarkation are the *observed* norm, not a tail
case. It also relocates the port signal — for influenza the informative
covariate is the **embarkation catchment** (passengers' countries of origin),
not the ports visited: Millman's affected passengers were 47.0% and 58.0% from
the United States.

### 3.5 Cabin co-illness, measured directly

Millman reports the proportion of MAARI passengers sharing a cabin with another
ill passenger: **22.7%** (Ship A) and **32.1%** (Ship B). Tranche 17 could find
no measurement of the cabin-localization fraction `f` and left only the
structural bound `f ≤ 0.5`. These two proportions are *not* `f` — they are a
co-illness proportion in cases, they inherit MAARI's ~2–5× syndromic
over-count (§3.6), and they are conditioned on outbreak voyages — but they are
measured rather than fitted, and they sit inside the structural bound.
Recorded as evidence, not proposed as a value.

### 3.6 MAARI is not influenza

Among MAARI cases actually tested: Ship A passengers **31/54 (57.0%)**
confirmed, crew **4/10 (40%)**; Ship B passengers **10/45 (22.0%)**, crew
**1/6 (17%)**. So the syndromic rung over-counts influenza by roughly **2–5×**,
with the multiplier differing between two ships three weeks apart. Any
influenza anchor stated as MAARI is a mixture of influenza and everything else
that causes cough on a ship, and the mixing fraction is itself variable.

## 4. Nulls and exclusions recorded

| Item | Finding | State |
|---|---|---|
| An influenza series in VSP | **Does not exist by construction**: VSP's reporting rule is gastrointestinal. The 428-posting series is not an influenza anchor | ∅ null, structural |
| An absolute influenza posting rate per voyage | **Blocked, and worse than norovirus's #13**: seasonal-influenza reporting is voluntary (§3.3), so the numerator is self-selected as well as the denominator being unpublished | ⊘ blocked |
| Fernandes 2014 as a rate | **Blocked read, not a null**: no open full text at Europe PMC, and the abstract gives cases without a denominator. Escalate before quoting a rate | blocked, recorded |
| Attack-rate-fitted shipboard influenza models | **Rejected as circular**, in advance: Zheng 2016 (DOI [10.1177/1420326x15600041](https://doi.org/10.1177/1420326x15600041)) validates an individual-scale cruise model *against a previous influenza outbreak* and then reports intervention effects. Its HEPA/UVGI and air-change conclusions are the kind of output the HVAC use case wants to produce, so it must not be an input | rejected, recorded |
| Vaccination coverage as prior immunity | Measured coverage exists (90–95.5% crew) but does **not** predict who fell ill (§3.2), so it is not convertible into a susceptible fraction | ∅ null as a conversion |
| A ship-measured influenza dose-response | None found; the arm's `dose_response.k` stays as register §3.3 has it, Grade C and unresolved (#44). No query in this tranche was aimed at, or may be used for, choosing a `k` that reproduces §1 | ∅ null; and see §5 |

## 5. What this tranche must not be used for

The five voyages in §1 are the arm's **likelihood**, under the same ruling
[`../proposals/fleet_emergence_decision.md`](../proposals/fleet_emergence_decision.md)
made for the norovirus fleet aggregates. Sourcing `dose_response.k`,
`base_susceptibility` or a route split *by which value reproduces 3.7% or 8.9%*
would destroy the only test this arm has. §1 is five ships, of which two share
an itinerary shape and one supplies no rate — a small enough set that fitting
more than one or two composites to it is not identifiable, which is the
counterpart of the degrees-of-freedom argument in the fleet ruling.

## 6. Citations

1. Millman AJ, et al. Influenza outbreaks among passengers and crew on two cruise ships. *J Travel Med* 2015;22(5):306–311. DOI 10.1111/jtm.12215. PMC4869710. Full text read.
2. Ward KA, et al. Outbreaks of pandemic (H1N1) 2009 and seasonal influenza A (H3N2) on cruise ship. *Emerg Infect Dis* 2010;16(11):1731–1737. DOI 10.3201/eid1611.100477. PMC3294517. Full text read.
3. Brotherton JM, et al. A large outbreak of influenza A and B on a cruise ship causing widespread morbidity. *Epidemiol Infect* 2003;130(2):263–271. DOI 10.1017/s0950268802008166. Abstract only.
4. Miller JM, et al. Cruise ships: high-risk passengers and the global spread of new influenza viruses. *Clin Infect Dis* 2000;31(2):433–438. DOI 10.1086/313974. Abstract only.
5. Fernandes EG, et al. Influenza B outbreak on a cruise ship off the São Paulo coast, Brazil. *J Travel Med* 2014;21(4):298–303. DOI 10.1111/jtm.12132. Abstract only; blocked read.
6. Bell TR, et al. Influenza surveillance on cruise ships. *Am J Prev Med* 2014;46(3):327–329. DOI 10.1016/j.amepre.2013.10.014. Abstract only; review.
7. Mouchtouri VA, et al. Preparedness for the prevention and control of influenza outbreaks on passenger ships in the EU. *Euro Surveill* 2009;14(21):19219. DOI 10.2807/ese.14.21.19219-en. Abstract only; review.
8. Huang QS, et al. Risk factors and attack rates of seasonal influenza infection (SHIVERS seroepidemiologic cohort). *J Infect Dis* 2019;219(3):347–357. DOI 10.1093/infdis/jiy443. Abstract only.
9. Ortiz JR, et al. A multi-center, controlled human infection study of influenza A(H1N1)pdm09 in healthy adults. *J Infect Dis* 2023;228(3):287–298. DOI 10.1093/infdis/jiad021. Abstract only.
10. Carrat F, et al. Time lines of infection and disease in human influenza: a review of volunteer challenge studies. *Am J Epidemiol* 2008;167(7):775–785. DOI 10.1093/aje/kwm375. Already adopted on this arm (R3).
11. Zheng L, et al. Evaluation of intervention measures for respiratory disease transmission on cruise ships. *Indoor Built Environ* 2016;25(8):1267–1278. DOI 10.1177/1420326x15600041. Abstract only; recorded as rejected.
