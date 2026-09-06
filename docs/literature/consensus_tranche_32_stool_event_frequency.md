# Tranche 32 — defecation frequency is measurable on both arms, the norovirus-specific event rate is not, and the symptom axes are measured shares

**Register rows fed / supersession.** This tranche feeds three §3.1 rows that
did not exist — the non-diarrhoeal and diarrhoeal arms of `stool_events_per_day`
and the `symptom_axis_probabilities` block — and closes tranche 31's structural
row by recording which of its two candidate shapes the evidence licenses. It
**supersedes nothing** and **withdraws no measurement**. It does not move,
narrow or reopen either `asymptomatic_shedding_log10` row, the boarding
prevalence, or the Sukhrie R-ratio check, which stays an out-of-sample check.

**Status:** Evidence assembled and interpreted. The mechanism it licenses landed
in the same change; the arm magnitudes are **declared and swept**, not adopted
as values.

**Scope:** the quantity tranche 31 left open. Symptom status reached
`transmission_core` through the emesis path and nowhere else, so a
never-symptomatic carrier, a convalescent boarder and an acutely ill case
contaminated hands, surfaces and food per copy identically. The candidate
mechanism was hand recontamination at *defecation events*, which requires an
event rate on two arms: a host passing diarrhoeal stool, and a host not.

**Result in one line.** Both arms are measurable in the general adult
literature and neither is measurable *for norovirus*: the non-diarrhoeal arm is
Grade B at **0.43–3.0 events/day** from two large adult cohorts, the diarrhoeal
arm has a **definitional floor of 3/day** and one Grade C mixed-aetiology mean
of **5.63 ± 1.43/day**, and the norovirus challenge literature — which is the
only literature that observes the illness directly — reports case definitions
and total stool *weight*, never an event count per day. So the mechanism is
adoptable and its diarrhoeal magnitude is a swept axis, exactly the standing of
`FOOD_HAND_CONTACTS_PER_DAY`.

---

## 1. The non-diarrhoeal arm — Grade B, and it is not "once a day"

Mitsuhashi et al. 2017, *American Journal of Gastroenterology* (NHANES
2009–2010, N = 4,775 adults, bowel-health questionnaire): **95.9%** of
participants reported between **3 and 21 bowel movements per week**, which
converts mechanically to **0.43–3.0 per day**. The paper's purpose is
constipation/diarrhoea epidemiology, so the interval is the *normal* range by
construction rather than a fitted distribution. Origin **Ab**.

Heaton et al. 1992, *Gut* (838 men, 1,059 women, prospective diaries): once
daily is the single most common habit but **not a majority** — regular
24-hour cycling in only **40% of men and 33% of women**, with **7% of men and
4% of women** regularly twice or three times daily. Origin **Ab**.

Two consequences for the model. First, the shipped point 1.0/day is inside the
interval and is the modal habit, so it is a defensible default rather than a
selected value. Second, the arm is genuinely **U-shaped** across a passenger
complement: a seven-fold spread in recontamination frequency between continent
adults is a between-host heterogeneity the model previously did not have at all,
because the continuous path held every shedding host's hand at the measured
ceiling every epoch regardless of habit.

## 2. The diarrhoeal arm — a definitional floor, a Grade C mean, and no norovirus number

**What defines the arm.** The norovirus human-challenge literature scores
diarrhoea against **≥3 unformed stools or ≥400 g unformed stool in 24 h**
(Kirby et al. 2016, *PLoS ONE*, DOI 10.1371/journal.pone.0143759; Atmar et al.
2008, *J Infect Dis*, DOI 10.1086/590909 uses the same family of definitions).
That threshold is a **floor on the arm and not a mean of it** — a case-definition
cut point tells you what the least ill scored case did, and using it as the
rate would understate the arm by construction. It is recorded as the lower
bound for that reason and for no other.

**What the challenge studies do measure, and why it is not this.** Atmar 2008
(16 experimentally infected subjects, 11 with clinical gastroenteritis lasting
1–2 days, median peak shedding ≈95 × 10⁹ genome copies/g faeces) reports
*shedding magnitude and duration*, and where it reports stool it reports
**weight** — two infected subjects had watery diarrhoea under 200 g. Kirby 2016
reports vomiting *counts* (1–7 across GI studies, 1–4 in one GII study) and
vomiting *duration* (2.0–10.8 h) but no stool event count per day. So the
literature that watched norovirus illness hour by hour did not record the
quantity, and this is a **null**, not an omission from our search: four
differently-phrased queries returned case definitions, stool weight and
duration of illness.

**The one quantitative arm available.** Patel et al. 2025, *BMC Nutrition*
(MAESTRO: 683 acute-gastroenteritis patients, 239 sites, India): baseline stool
frequency **5.63 ± 1.43/day** at presentation, falling to **1.65 ± 0.65/day**
after seven days. **Grade C** — mixed aetiology, care-seeking, under probiotic
treatment, not norovirus-confirmed, and not a community cohort. It supplies the
only mean and it does not supply an adoptable value; the arm is declared as
**[3.0, 8.5]/day** (definitional floor to mean + 2 SD) and **swept**.

**Refused.** Setting the diarrhoeal arm to whatever reproduces VSP posting
rates, A4, A8, A9, the Mouchtouri food share or the Sukhrie R ratio. The whole
point of wiring the mechanism is that the arm is measurable independently of
every one of those, and the arm's width is now a screening axis whose effect on
the anchors is a *result*, not an input.

## 3. The symptom axes are measured shares, and one of the three is a logical closure

Kirby 2016, Tables 1–2, human challenge in adults, genotypes GI.1 Norwalk,
GII.2 Snow Mountain and GII.1 Hawaii:

| Quantity | GII value used | GI.1 comparison |
|---|---|---|
| Vomiting among symptomatic subjects | **0.72** (Snow Mountain) | 0.70 |
| Diarrhoea among vomiting subjects | **0.50** | 0.57 |

Grade **B**, origin **Tn** — challenge adults standing in for a passenger
complement — and the GII values are taken because the active profile's
genotypes are GII.

The third share, **diarrhoea among symptomatic non-vomiters, 1.0**, is **not
measured and is not asserted as a measurement**: illness in every one of these
studies is defined as *diarrhoea and/or vomiting*, so a symptomatic subject who
did not vomit met the definition through diarrhoea. It is a closure of the
definition, recorded as such at the profile key and in the register.

What this buys, in the profile's own declared terms: the norovirus arm already
declared `clinical_presentation.phases` as acute (dpi 0–2, features vomiting +
watery_diarrhea + cramps) and resolving (dpi 3+, watery_diarrhea only), and no
engine read `watery_diarrhea`. With the axes drawn once at symptomatic onset,
the four classes the maintainer asked for exist without a new state: acute
v / d / v&d, resolving d-only, never-symptomatic RNA-only, and the convalescent
boarder that sheds on its curve while drawing no acute event schedule.

## 4. What is separated, and what deliberately is not

**Separated.** Continuous RNA emission (`get_pathogen_shedding`,
`get_pathogen_hand_target`, the shedding curves, the wastewater/greywater
sentinel) is untouched by the event process. A never-symptomatic carrier sheds
exactly the RNA it shed before this change and remains detectable in wastewater;
what it no longer does is have its hand held at the Liu ceiling every epoch.

**Not separated, and still recorded as a defect.** The sentinel still samples
the greywater fraction of the *same* zone surface pools the fomite route
delivers dose from (tranche 31 §2). The event mechanism reduces how much a
carrier injects into those pools, so it *narrows* the collision; it does not
resolve it, and no row claims it does.

## 5. Measured consequence, reported and not tuned

A 48-epoch, 10-seed norovirus probe with lineage tracking on, comparing the
event arm against the continuous relaxation it replaces, holding everything else
fixed:

| | continuous | events |
|---|---|---|
| Total lineage-tracked surface mass, epoch 48 | **5.87 × 10⁶** | **53.0** |
| Mean hand load across infected hosts | 57.1 | 5.82 |
| Infected hosts at epoch 48 | 12 | 13 |

The infection counts are the load-bearing part: the surface reservoir fell five
orders while the epidemic did not move, so the continuous path was maintaining a
faecal mass injection — one ceiling-load per shedding host per *epoch*, 24 per
day on the hourly grid — that the dose pathway barely used. Two rebaselined
surface-recovery expectations are attributed to exactly this in the change, and
**every dose figure in the repository remains withdrawn** pending the refit the
open ledger records; these numbers are a before/after of one structural change,
not a result.

## 6. Queries

1. `bowel movement frequency per day healthy adults population distribution`
2. `stool frequency per day norovirus gastroenteritis adults diarrhoea episodes`
3. `number of unformed stools per 24 hours norovirus challenge study`
4. `acute gastroenteritis stool frequency per day adults cohort`
5. `norovirus challenge vomiting diarrhoea proportion symptomatic subjects`

Retrievals 2 and 3 returned case definitions and stool weight, never an event
rate; that is the null recorded in §2.
