# Tranche 34 — crew are infected 4× less than passengers, the literature attributes it to segregation, and crew immunity is a null with a structural gap behind it

**Register rows fed / supersession.** Sharpens the A5 anchor row with a
measured passenger:crew ratio read from tables; adds nothing adoptable to
`ship_graph.immune_fraction` (§5 of the register) and records **three nulls**
— crew-specific prior immunity, comorbidity effects on norovirus
*susceptibility*, and any voyage-to-voyage carried immune state — as nulls. It
**supersedes nothing** and **withdraws no measurement**. It moves no constant.

**Status:** Evidence assembled and interpreted. Nothing implemented in this
tranche; the one structure it identifies (a carried immune state) is recorded
as a gap, not built.

**Scope:** the question raised after the class-mixed staged campaign — the
model's crew are infected as often as its passengers (A5 ratio 0.95–1.46 at
stage 0, 1.2–1.3 at depth on every hull; infection-AR ratio 1.05–1.6, so not an
observation-layer artefact) — and three candidate mechanisms for a real crew
deficit: acquired short-term immunity, absence of certain chronic illnesses
under fitness-for-duty screening, and immunity persisting from cruise to
cruise. The retrieval predates [FOOD-ROLE-01](../norovirus/norovirus_open_ledger.md)
(§1), which removed a structural over-exposure of crew; the A5 comparison
below is against the pre-repair campaign and must be re-measured.

**Result in one line.** The crew deficit is measured, large and consistent —
passenger:crew attack-rate ratio **4.3** pooled, **10.1** for person-to-person
outbreaks — and the cruise literature attributes it to **segregation** of crew
sleeping, dining and boarding areas, not to host biology; no study quantifies
crew prior immunity, and the model has no field in which a carried immune
state could live.

---

## 1. The measurement: crew attack rates on cruise ships

Mouchtouri et al. 2024, *Eurosurveillance* 29(10), DOI
10.2807/1560-7917.es.2024.29.10.2300345 — 45 norovirus outbreaks on 26 ships,
EU SHIPSAN record. Read from Tables 2–3 of the full text (**R**), not the
abstract:

| population | ill / at risk | AR | median AR [IQR] across outbreaks |
|---|---:|---:|---|
| passengers | 6,022 / 71,073 | 8.47% | 7% [5–9] |
| crew | 474 / 24,256 | 1.95% | 2% [0–3] |
| ratio | | **4.3** | |

By transmission mode (Table 3):

| mode | passenger AR | crew AR | ratio |
|---|---:|---:|---:|
| person-to-person | 8.83% | 0.87% | **10.1** |
| person-to-person + environmental | 4.47% | 1.45% | 3.1 |
| multiple modes | 14.6% | 2.6% | 5.6 |

Bert et al. 2013 (systematic review of cruise-ship norovirus outbreaks) report
crew attack rates **lower in every study reviewed**, and attribute it, after
McEvoy et al. 1996, to crew having **separate sleeping, dining and boarding
areas** — i.e. less contact with the passenger population, not a different
host. Mouchtouri's Discussion offers crew immunity, younger age and nationality
as **unquantified speculation** only.

The measured ratio sits inside the register's existing A5 band (2.5–4.5) and
sharpens it; the mode-specific ratio (10.1 for person-to-person) is a **check**
on how the model's crew deficit varies by route, not a target.

## 2. Acquired short-term immunity — generic, not crew-specific

No study measures crew-versus-passenger norovirus seroprevalence, prior
infection history, or prior-genotype exposure. Searches for cruise crew
seroprevalence, ship worker norovirus antibody, and repeated cruise exposure
immunity returned nothing on the crew population. **∅ null for the
crew-specific quantity.**

What is measurable is generic: norovirus immunity is short-term and
genotype-specific. Yu et al. 2023 (DOI as retrieved via Consensus, paper id
195323561885590182f198bc0ebdfb95) estimate GI blockade-antibody duration of
**~2.3–4.8 years**, decaying **3.6–5.9%/yr** — a community serology study, not
a shipboard one, and blockade titre is a correlate, not a measured protection
fraction. This licenses a **declared sensitivity axis** — a role-stratified
prior-immune share swept over a stated interval — and nothing more. No value
may be chosen for it by which value moves A5 or A9.

## 3. Cruise-to-cruise persistence — a missing field, not a missing number

A crew member's immune state is a **carried** state across consecutive
voyages, while every passenger boards fresh. The model resets both to one
global `immune_fraction` (0.2, Korkin's `IMMUNE_RATIO`, Grade I) at every
voyage start, allocated across classes without regard to role
(`engines/infection_dynamics_bridge.py`); `TransmissionCore` draws
susceptibility Beta(0.111, 32.81) and the secretor-negative fraction role-blind.
So the mechanism cannot be expressed at all until the engine carries an
immune state from one voyage into the next for resident agents. Recorded as a
**structural gap**, with no quantity attached: the recurrence-interval
literature for crew after a shipboard outbreak was not found, so even the
first number such a structure would need is null.

## 4. Chronic illness / fitness for duty — susceptibility, not severity

Crew are a screened working-age cohort, so comorbidity prevalence differs
from a passenger cohort. But the norovirus literature on comorbidity measures
**severity and duration** (hospitalisation, prolonged shedding in the
immunocompromised), not the probability of infection given a dose. Nothing
retrieved measures a comorbidity effect on norovirus *susceptibility*. **∅
null.** For `norwalk_gi` the profile's age bands are inert (no
`base_probabilities_by_age_band`; incubation `host_factors` omitted for lack of
support), and this tranche gives no reason to activate them.

## 5. A counter-example, so this is not read as a law

MS *Roald Amundsen*, SARS-CoV-2, 2020: crew attack rate **25.2%** against
passengers' **7.2%** — the opposite sign. Crew-lower is a property of the
segregated **norovirus** cruise record with its faecal–oral and food routes,
not of crew as hosts. Any structure built from §1 must be route-specific.

## 6. What this licenses

- Scoring the model's passenger:crew infection ratio against **4.3** (pooled)
  as an out-of-sample check, by route where the model reports it, after
  FOOD-ROLE-01 is re-measured.
- A **structural** change: crew–passenger contact segregation (separate
  sleeping, dining, boarding), which the literature names as the mechanism and
  which the model does the opposite of (crew dine in the same Dining set as
  passengers). This is a topology declaration with no free epidemiological
  magnitude.
- A **declared sensitivity axis** for a role-stratified prior-immune share, if
  and when the engine has a field for it — with no value adopted.

**Not licensed:** a crew immune fraction, a crew immunity duration, a
comorbidity susceptibility multiplier, or any move in `immune_fraction`,
`secretor_negative_fraction`, or the susceptibility Beta. None of these may be
read off A5, A9, or the observed crew attack-rate medians.
