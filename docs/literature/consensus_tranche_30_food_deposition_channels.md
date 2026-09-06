# Tranche 30 — the three deposition channels the food route has no term for: one bounded on the wrong quantity, one measured at the provisioning point, one null; and the VSP score is a published null

**Register rows fed / supersession.** This tranche feeds three §3.1 rows —
`FOOD_HAND_CONTACTS_PER_DAY`, `FOOD_HANDLER_CONTACT_MULTIPLIER`,
`HAND_HYGIENE_*` reachability in food zones — and adds two rows that did not
exist: a **provisioning-side source-contamination prevalence** row, and an
**inspection-score null** row recording that the quantity the ship-year VSP
panel supplies cannot source or check a food parameter. It supersedes nothing.
It withdraws one thing: [tranche 29](consensus_tranche_29_food_and_environmental_deposition.md)'s
searched null "no bare-hand contact rate with communal food exists" is
narrowed — the *diner-side* rate is still null, but three measured
food-service quantities in that shape now exist and are recorded in §5.

**Status:** Evidence assembled and interpreted, **sourcing only**. **No profile
constant, engine constant, config value or code path changes numerically in
this document's change.** Like every document in `literature/`, this is
context, not truth: where it and the register disagree, the register holds the
status and this document holds the citations.

**Scope:** the deposition channels `FOOD-ARCH-01` (#450) left the route without
and `FOOD-PERHEAD-01` (#452) confirmed the allocation rule cannot explain —
(1) a food handler working while ill or while shedding, (2) product
contaminated at source before it meets a hand, (3) emesis into or near food —
plus the operational leg the CDC/VSP inspection and remediation records were
proposed for.

**Method:** Consensus MCP, unfiltered, `include_full_text_chunks: true`, twelve
queries recorded verbatim in §7. One returned a rate limit and was re-run
rather than recorded as a null. On the standing instruction that the food
route may be sourced from the **general food-service literature and not only
cruise ships**, §2 and §5 are US/UK/EU retail, restaurant, catering and
food-manufacturing settings; every such row is graded **B** on the
analogous-setting rule and the setting is named at each number, because a
sandwich factory and a cruise galley are not the same workplace.

**Result in one line.** The food-handler channel is bounded, but on the
**wrong quantity** — the literature reports a 12-month worker-level recall
(11.9–20 % of workers worked at least one to two shifts while vomiting or
with diarrhoea) where the model needs a per-shift probability, and the
conversion needs a shifts-per-year and episodes-per-worker denominator none of
these papers carry. Source-contaminated product is the one channel measured
**at the point a ship provisions**: EU coordinated survey, 10.8 % of oyster
batches at dispatch centres positive at a mean 168 copies/g, against 34.5 % in
production areas — and it deposits into the food pool with no occupant
involved at all, which makes it the only candidate here that is structurally
identifiable separately from the hand route. Emesis-into-food is **∅ null**,
and the reason is stronger than absence of evidence: in the one detailed
dining-room vomiting outbreak, food could not be implicated and the dose
tracked distance from the vomiter, i.e. the event is already carried by the
emesis-conditioned airborne route, so a food-pool emesis term would
double-count it. And the ship-year VSP score panel is a **published null**:
1,197 inspections, pre-outbreak mean 96.4 against 95.1, p = 0.42.

---

## 1. What the route is missing, stated as quantities

`FOOD-ARCH-01` gave the route hand load → contact count → per-event hand→food
transfer → depletion. Every leg of that is a *diner or crew occupant* touching
food with a contaminated hand. Three channels are absent, and each needs a
different quantity:

| Channel | Quantity the model would need | Status after this tranche |
|---|---|---|
| Handler working while ill/shedding | probability a food-handling crew shift is worked while shedding | **B on a different quantity** (§2) — annual worker recall, not per-shift |
| Product contaminated at source | prevalence × load per serving at provisioning | **A/B for prevalence and load** (§3); servings and grams per serving are model-side and absent |
| Emesis into or near food | fraction of emesis mass reaching a food pool | **∅ null**, with a structural reason not to add the term (§4) |

## 2. The handler channel: measured, and on the wrong quantity

| Source | Setting and design | Number | Grade | Origin |
|---|---|---|---|---|
| **Sumner 2011**, *J Food Prot*, DOI [10.4315/0362-028x.jfp-10-108](https://doi.org/10.4315/0362-028x.jfp-10-108) | 491 food workers + 387 managers, nine US EHS-Net sites, interview | **58/491 = 11.9 %** worked while vomiting or with diarrhoea on **two or more shifts** in the previous year | B | **Ab** |
| **Carpenter 2013**, *J Food Prot*, DOI [10.4315/0362-028x.jfp-13-128](https://doi.org/10.4315/0362-028x.jfp-13-128) | 491 workers from 391 restaurants, nine states | **≈20 %** worked while ill with vomiting or diarrhoea for **at least one shift** in the previous year; **≈60 %** recalled working while ill with *any* symptom | B | **R** |
| **Norton 2015**, *J Food Prot*, DOI [10.4315/0362-028x.jfp-14-134](https://doi.org/10.4315/0362-028x.jfp-14-134) | 426 restaurant managers, nine EHS-Net sites | **≈70 %** of *managers* had worked while ill; **10 %** while having nausea or "stomach flu"; **one-third** of restaurants' policies do not specify when an ill worker is excluded. Reasons given for working ill: obligation/work ethic 33 %, understaffed 26 %, symptoms judged mild 19 %, irreplaceable managerial duty 11 %, non-food work available 7 %, unpaid/no sick-leave policy 5 % | B | **Ab** |
| **Moritz 2023** (in tree), MMWR Surveill Summ 72(6), DOI [10.15585/mmwr.ss7206a1](https://doi.org/10.15585/mmwr.ss7206a1) | NEARS 2017–2019 retail outbreaks | ~**40 %** of outbreaks with identified contributing factors had food contamination by an **ill or infectious food worker** | B | — |

**Why this is not adoptable as it stands.** All three prevalence figures are
**worker-level, 12-month recall of at least one (or two) shift(s)**. The model
needs a **per-shift, per-epoch** probability that a food-handling crew agent
deposits while shedding. Converting the one into the other requires shifts
worked per year and symptomatic episodes per worker per year, and **none of
these papers report either**; nor does the recall design distinguish a worker
who worked two shifts of one episode from one who worked two episodes. A
naive division (0.119 over ~250 shifts/year) is arithmetic on a quantity the
study did not measure, and it is exactly the move this repository's provenance
rule forbids.

What the interval **does** license: the channel is **real and common**, at
Grade B, in the analogous setting — an order of magnitude more common than a
"handlers never work while ill" idealisation, and Norton's reason breakdown
says *why* (staffing and pay, not ignorance), which is a policy lever rather
than a constant. Recorded as **bounded, not adoptable**, with the missing
denominator named.

**Note on which agents this would attach to.** The register's
`FOOD_HANDLER_CONTACT_MULTIPLIER` row already records the open question of
whether crew in a service zone are the right proxy for galley staff. This
tranche adds a second: the model has **no shift concept** for a food handler
at all, so "worked a shift while shedding" has no representation to attach a
probability to even if the probability were in hand.

## 3. Source-contaminated product: measured where a ship provisions

This is the channel with the cleanest provenance, and the only one whose
deposition **bypasses every occupant** — it enters the pool at provisioning.

| Source | Setting and design | Prevalence | Load | Grade | Origin |
|---|---|---|---|---|---|
| **EFSA / Aerts 2019**, *EFSA Journal*, DOI [10.2903/j.efsa.2019.5762](https://doi.org/10.2903/j.efsa.2019.5762) | EU coordinated baseline survey, raw oysters, **2,180** production-area + **2,129** dispatch-centre valid samples over two years | production areas **34.5 % (CI 30.1–39.1)** modelled, 38.1 % raw; **dispatch centres 10.8 % (CI 8.2–14.4)**, 10.6 % raw. Strong Nov–Apr seasonality. Class A source areas 3.7 % vs Class B 20.0 % at dispatch | mean **337 copies/g** among production-area positives; **168 copies/g** at dispatch. **< 10 %** of samples above the LOQ in either genogroup | **A** for the EU oyster supply; B transferred to a ship's provisioning | **T11–T21** |
| **Cook 2019**, *Food Microbiology*, DOI [10.1016/j.fm.2018.12.003](https://doi.org/10.1016/j.fm.2018.12.003) | UK retail produce, 1,152 samples | lettuce **30/568 = 5.3 %**; fresh raspberries **7/310 = 2.3 %**; frozen raspberries **10/274 = 3.6 %** | not quantified | B | **Ab** |
| **Torok 2019**, *Int J Food Microbiol*, DOI [10.1016/j.ijfoodmicro.2019.108327](https://doi.org/10.1016/j.ijfoodmicro.2019.108327) | Australian retail, year-long | leafy greens **2.2 %**; strawberries and blueberries **< 2 %** (none detected) | — | B | **Ab** |
| **Elmahdy 2022**, *Food Environ Virol*, DOI [10.1007/s12560-022-09516-1](https://doi.org/10.1007/s12560-022-09516-1) | Egyptian retail/farm, leafy greens and strawberry | GI **20–25 %**, GII **30–40 %** | GI 1.1 × 10⁴, GII 2.03 × 10³ GC/g (greens) | **excluded from the interval** — a different sanitation and irrigation regime, not analogous to cruise provisioning; recorded so the exclusion is visible | Ab |
| **Hardstaff 2018**, *Foodborne Pathog Dis*, DOI [10.1089/fpd.2018.2452](https://doi.org/10.1089/fpd.2018.2452) | Systematic review, 3,021 articles screened, Jan 2003 – Jul 2017 | **27** confirmed foodborne vs **47** definite food-handler outbreaks; of foodborne, **seafood 61 %**, of which **89 % oysters**; 57 % of reports European; median 59 exposed, 23 ill | B | **R** |

**Provisioning-side intervals, dated and frozen here:** oysters
**[0.082, 0.144]** positive at dispatch with a mean **168 copies/g** among
positives; leafy greens **[0.022, 0.053]**; berries **[< 0.02, 0.036]**.
Grade A for the oyster figure as a measurement of the EU supply, Grade B as a
statement about what a ship loads.

**Why this is still not a parameter.** The quantity is per **gram** of a
**specific commodity**; the model's food pool is per **zone**, in genome
copies, with no commodity, no servings-per-voyage and no grams-per-serving.
Adopting this channel is a **structure** change (a provisioning event that
seeds a zone pool at embarkation, sized by servings × grams × prevalence ×
load), not a constant, and the two model-side quantities it needs do not exist
yet. It is recorded as the **best-sourced candidate channel**, with the
structure it would require named.

Hardstaff's 27-vs-47 split is also the first measured statement of the two
channels' **relative** frequency: the handler channel appears in ~1.7× as many
outbreaks as the source-contaminated channel in the same review window. That
is a mode count, in the same class as Mouchtouri 2024's Table 3 — a
**non-circular external check**, never a target.

## 4. Emesis into or near food: ∅ null, and the reason is structural

| Source | What it establishes |
|---|---|
| **Marks 2000**, *Epidemiol Infect*, DOI [10.1017/s0950268899003805](https://doi.org/10.1017/s0950268899003805) | The canonical dining-room emesis outbreak: one diner vomited during a hotel meal. **No food served could be implicated** on univariate analysis; attack rate by table showed an **inverse relationship with distance from the vomiter**; nobody in a separate restaurant fell ill; **1 of 12** serving staff — a much lower rate than diners, attributed to intermittent occupancy of the room. The authors' conclusion is airborne spread with subsequent swallowing, while explicitly leaving aerosol-onto-food-or-hands open |
| Hotel outbreak cited by Marks 2000 and Hardstaff 2018 | A kitchen assistant vomited into a sink later used to prepare potato salad. **N = 1 anecdote; no fraction, no mass, no denominator** |

No study measures a fraction of emesis mass reaching food or a food-contact
surface. Two attempts naming the quantity (§7 queries 3 and 12) returned
outbreak narratives and the airborne literature.

**The structural reason not to add the term anyway.** The model already
carries emesis as a discrete event feeding the **airborne** reservoir under
`airborne_emission_mode = emesis_conditioned` with a measured per-event
aerosol fraction. Marks 2000 is the observation that route was built for: in
the one dining-room emesis event described in detail, **the dose did not
arrive via the food**. Adding a food-pool emesis deposition term sized by the
same event would **double-count** it unless the split between the two
destinations is measured, and it is not. Recorded as **∅ null, and refused on
structure as well as on evidence.**

## 5. The operational leg: what the general food-service literature does measure

[Tranche 29](consensus_tranche_29_food_and_environmental_deposition.md)
recorded a searched null: no bare-hand contact rate with communal food. That
holds for the **diner** side. On the **food-service** side the general
literature supplies three things, and none of them is the rate either:

| Source | Setting | What was measured | Grade | Origin |
|---|---|---|---|---|
| **Hoover 2023**, *J Food Prot*, DOI [10.1016/j.jfp.2023.100182](https://doi.org/10.1016/j.jfp.2023.100182) | CDC EHS-Net; manager interviews + **kitchen observation in 312 restaurants**, six sites, five states | at least one worker action that could lead to contamination in **63.1 %** of restaurants; the most frequent single action was **bare-hand or dirty-glove contact with ready-to-eat food, 35.9 %**. Higher counts in independently-owned restaurants, and where there was no handwashing policy and no policy minimising bare-hand RTE contact | **B** | **Ab** |
| **Verrill 2021**, *J Food Prot*, DOI [10.4315/jfp-20-412](https://doi.org/10.4315/jfp-20-412) | 2014 FDA Retail Food Risk Factor Study, handwashing observations | out of compliance for **washing hands correctly**: fast food **45 %**, full service **57 %**; out of compliance for **hands washed when required**: **57 %** and **78 %** | **B** | **Ab** |
| **Lubran 2010**, *J Food Prot*, DOI [10.4315/0362-028x-73.10.1849](https://doi.org/10.4315/0362-028x-73.10.1849) | Notational analysis, retail deli departments, 6 chain + 3 independent stores | **3,073** total actions (chain) and **1,098** (independent), of which **439** and **273** required handwashing; compliance **73/439** and **5/273**. **67 %** (chain) and **86 %** (independent) of handwash-requiring actions arose from **touching a non-food-contact surface before handling RTE food** | **B** | **Ab** |
| **Mohamed 2024**, *J Food Prot*, DOI [10.1016/j.jfp.2024.100386](https://doi.org/10.1016/j.jfp.2024.100386) | Covert CCTV, sandwich-making factory, **12** handlers over **16 h** across two shifts | **588** occasions requiring hand hygiene → **≈3.1 occasions per handler-hour**; hands not washed on **32 %** of them; of 401 attempts, **1 %** protocol-compliant and **95 %** under the recommended 20 s | **B** | **Ab** |
| **Clayton 2004**, *Br Food J*, DOI [10.1108/00070700410528790](https://doi.org/10.1108/00070700410528790) | Notational analysis, **115** food handlers, 29 catering businesses | **31,050** food-preparation and hygiene actions = **270 actions per handler**; the **observation duration is not retrievable**, so no rate | B for the count | **?nr** for the denominator, two attempts |
| **Wilson 2020**, *J Expo Sci Environ Epidemiol*, DOI [10.1038/s41370-020-0249-8](https://doi.org/10.1038/s41370-020-0249-8) | 263 people observed 30 min each, multiple locations; **eating** vs non-eating macro-activities | hand-to-**mouth** during eating: median **7/h** (SD 3.9); adults **6/h**, adult 75th percentile **11/h**; non-eating **4/h** | **B** for hand-to-mouth during eating | **R** |

Three readings, kept separate:

1. **Lubran's 67–86 % is a measurement of the sequence `FOOD-ARCH-01` built.**
   The dominant reason a handwash was indicated was **touching a non-food
   surface and then handling ready-to-eat food** — surface → hand → food,
   which is precisely the composed route now in the engine. It does not size
   the route; it says the route's *shape* is the one the observational
   literature records as dominant.
2. **The hygiene lever has a measured ceiling, and it is low.** Verrill's
   45–78 % out-of-compliance and Mohamed's 32 % omission with 1 % protocol
   compliance bound how much a handwashing intervention can remove in a food
   zone. This is a **reachability** statement about the NPI interface (#9/#10),
   not a transfer fraction, and it belongs against the hygiene efficacy row
   rather than the deposition constants.
3. **`FOOD_HAND_CONTACTS_PER_DAY` = 0.6/day sits an order of magnitude below
   the nearest measured eating-associated contact frequency, and this is a
   flag, not a replacement.** Wilson's 6–7 hand-to-mouth contacts per hour
   during eating, over any plausible dining duration, is 10–20× the declared
   0.6 **food** contacts per day; Mohamed's 3.1 hand-hygiene occasions per
   handler-hour is of the same order. Neither measures hand→**food** contact:
   hand-to-mouth is the *ingestion* leg and hand-hygiene occasions are a
   protocol-defined event class. So the declared value is **not replaced here**
   — but it is recorded as **plausibly low by an order of magnitude**, which
   makes it a sweep axis, and the direction matters because the route's 2e-7
   dose share was measured at it.

**Still ∅ null after this tranche:** the number of times a person — diner or
handler — makes **bare-hand contact with communal or ready-to-eat food per
unit time**. Four differently-phrased queries across two tranches return
compliance rates, action counts without a time denominator, hand-to-mouth
frequencies, and CFU loads.

## 6. The CDC/VSP inspection panel: violation content is usable, the score is a published null

The ship-year score panel was proposed as a source of a between-ship spread in
food-handling practice. The literature has already run that join, and it is
negative.

| Source | Design | Result |
|---|---|---|
| **Taylor 2018**, *Int Marit Health* 69(4):225–232, DOI [10.5603/imh.2018.0037](https://doi.org/10.5603/imh.2018.0037) | All **1,197** VSP inspections published 2012–2017, mean score **95.7/100**; **50** separate AGE outbreaks in the same window; 47 previously-inspected ships | pre-outbreak mean **96.4** vs **95.1** for the 1,157 inspections **not** followed by an outbreak; **z = 0.81, p = 0.42**. Conclusion: the current inspection format "generates scores that have **no prognostic value** with regard to future outbreaks". Per-outbreak table carries agent, passenger %, crew %, pre-outbreak score, lead time in weeks, fleet and industry 12-month means |
| **Dahl 2018**, *Int Marit Health*, DOI [10.5603/imh.2018.0036](https://doi.org/10.5603/imh.2018.0036) | Editorial on Taylor | Records the **era split** explicitly: 1990–2000, as scores rose, failing vessels fell **27.3 % → 7.4 %** and diarrhoeal outbreaks **6.2 → 3.7 per 1,000 cruises**; after 2002 outbreak incidence rose again *despite* consistently high scores, as the dominant agent became viral. "Scores and specific categories of violations are clearly associated with common-source **foodborne** illness" while being uncorrelated with **norovirus** outbreaks |
| **Carling 2009** (in tree, Grade A for cleaning thoroughness), *Clin Infect Dis*, DOI [10.1086/606058](https://doi.org/10.1086/606058) | Covert thoroughness-of-disinfection-cleaning audit, **56** ships (~30 % of 180 across 9 lines), **273** public restrooms, **8,344** objects, 2005–2008 | TDC **37 % (range 4–100 %, CI 29.2–45.4)** of objects cleaned daily; **TDC does not correlate with the VSP score (r² = 0.002, p = 0.75)** — several ships with near-perfect scores had TDC < 30 %; TDC of the 3 ships audited within 4 months **before** an outbreak was **10.3 %** vs **40.4 %** for the 40 without (p < 0.004) |

**What this settles about the proposal.**

- The **numeric score** cannot source a food parameter, and it cannot serve as
  a between-ship spread in hygiene practice either. Not because a score→outbreak
  join would be circular against A4/A8 — it would be, and that alone bars it as
  a *source* — but because the join has been done and is **null** (Taylor), and
  because the one objective hygiene measurement that *does* discriminate
  pre-outbreak ships is **uncorrelated with the score** (Carling). A spread
  read off the score would be a spread in something that demonstrably does not
  track the mechanism.
- **Violation content remains the usable part**, at the standing this document
  gives §5's observational rows: what a 95 has that a 100 does not — bare-hand
  RTE contact, utensils held in stagnant water, holding temperature, ill-worker
  reporting — is a *mechanism* observable, and Hoover 2023 shows the same class
  of observation quantified in 312 restaurants, which is where the general
  food-service literature is stronger than the cruise-specific record.
- Dahl's era split is a **caution against pooling**: the score↔outbreak
  association that existed in the foodborne era does not exist in the
  norovirus era, so any use of the panel must be era-scoped the way E/#10's
  pre/post arms are.
- Carling's TDC-vs-outbreak contrast (10.3 % vs 40.4 %) is **not** admissible
  as a source: it is an outbreak-conditioned comparison, i.e. the same
  circularity a score→outbreak join has. Only the unconditional **37 %**
  is used, which is already the register's Grade A cleaning-thoroughness row.

## 7. Queries, verbatim

Unfiltered; `search` called with `query`, `include_full_text_chunks` and
`page_size` only.

1. `proportion of food handlers who worked while ill with vomiting or diarrhoea survey percent`
2. `norovirus genome copies per gram stool after symptom resolution duration of shedding days convalescent`
3. `norovirus concentration in vomitus genome copies per mL patients`
4. `norovirus prevalence in oysters at retail percent positive genome copies per gram shellfish survey`
5. `norovirus prevalence leafy greens berries retail survey percent positive genome copies per gram`
6. `fraction of vomiting events contaminating food or food preparation surfaces outbreak investigation`
7. `cruise ship galley inspection deficiency violations norovirus outbreak vessel sanitation program score`
8. `retail food risk factor study percent out of compliance bare hand contact ready-to-eat food employee handwashing observation`
9. `notational analysis deli employees number of contacts with ready-to-eat food per hour observation period actions`
10. `food handlers observed hours per person duration of observation period catering 31050 actions per hour rate`
11. `norovirus outbreak vomiting incident in dining area airborne contamination of buffet food attack rate proximity`
12. `food handler hands touch ready-to-eat food number of events per hour observed kitchen frequency`
13. `bare hand contact with ready-to-eat food observed percent of food preparation events glove use restaurant inspection`
14. `number of hand to food contacts per meal eating with hands self-service buffet consumers observed frequency`
15. `food workers not reporting illness to manager percent exclusion restriction policy compliance restaurant survey`
16. `observed frequency of touching food with hands per hour during meal preparation video observation contacts food items`

Query 6 hit `Rate limit exceeded` on the first attempt and was re-run; that is
not recorded as a null.

## 8. What this changes, and what it does not

**No constant moves.** Nothing in §2–§6 is used to choose a value, and
nothing is chosen to move the food route toward Mouchtouri 2024's 7.3–32 %
food-involved share. The shortfall recorded at #450 is **still open**, and
after this tranche the ranking of candidate explanations is:

1. **`FOOD_HAND_CONTACTS_PER_DAY` may be low by an order of magnitude** (§5.3)
   — the only candidate that would move the route's magnitude without new
   structure, and it is a sweep, not a value.
2. **Source-contaminated provisioning is an entirely absent channel** with the
   best-sourced inputs of the three (§3) and a well-defined structure, gated on
   two model-side quantities (servings per voyage, grams per serving).
3. **The handler channel is real and common but has no representation to
   attach to** (§2) — the model has no food-handler shift.
4. **Emesis-into-food is refused** (§4), on structure as well as evidence.

**One prior null is narrowed and one prior proposal is closed.** Tranche 29's
"no bare-hand food-contact rate exists" now reads: none *per unit time*, but
establishment-level prevalence (35.9 %), hand-hygiene non-compliance
(32–78 %), action counts without a time denominator, and eating-associated
hand-to-mouth frequency (6–7/h) all exist in the general food-service
literature and are recorded above. The VSP **score** panel is closed as a
source and as a spread proxy (§6); the VSP **violation content** stays open and
is the part worth pulling next.
