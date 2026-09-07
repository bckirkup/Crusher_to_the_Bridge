# Tranche 33 — the crew arm's regulation is a mandatory duty exclusion, the model has none, and the two crew exposure multipliers do not carry the excess

**Register rows fed / supersession.** One new §3.3 structural row —
`crew_age_duty_exclusion`, absent from the model — and one bounded-not-adoptable
companion quantity, the compliance share. It **supersedes nothing** and
**withdraws no measurement**. It moves no constant, and in particular it does
not move `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR`,
`FOOD_HANDLER_CONTACT_MULTIPLIER` or `crew_contact_multiplier`, all three of
which keep the standing [tranche 30](consensus_tranche_30_food_deposition_channels.md)
gave them. It narrows tranche 30 §1 on one point: that tranche's food-handler
presenteeism bound was drawn from the **land-based** food-service literature,
and the regulated maritime arm turns out to be the opposite regime.

**Status:** Evidence assembled and interpreted. Nothing implemented in this
change; the structure it identifies is a decision, recorded as one.

**Scope:** why the model's crew complement carries **51.5%** of the quiet
region's VSP postings (408 crew-only of 793, plus 115 both-channel, over 17,280
voyages at twelve low-posting Sobol' points, #467) when CDC's own posted record
carries **0.5–9.3%** — one crew-only posting in 208 as the direct measurement,
16 crew outbreaks against 156 passenger ones in MMWR as a non-disjoint ceiling.

**Result in one line.** VSP does not merely *advise* ill crew to stay off duty
the way it advises ill passengers to stay in their cabins — it **requires**
isolation, food employees until 48 h symptom-free with documented medical
clearance before return to work — so the observed crew channel is measured
under a mandatory exclusion regime that the model has no term for at all, while
the model gives its crew three exposure amplifiers and an ill crew member the
same mobility as an ill passenger.

---

## 1. The rule, from the primary document

CDC Vessel Sanitation Program, **2018 Operations Manual**, §4.4.1.1.1
*Symptomatic and Meeting the Case Definition for Acute Gastroenteritis (AGE)
(11 C)*, read from the CDC-hosted 508 PDF (origin **Tr** — a regulatory
document, not a journal):

> **FOOD EMPLOYEES:**
> - Isolate in cabin or designated restricted area until symptom-free for a
>   minimum of 48 hours.
> - Follow-up with and receive approval by designated medical personnel before
>   returning crew to work.
> - Document date and time of last symptom and clearance to return to work.
>
> The FOOD EMPLOYEE's supervisor or PERSON IN CHARGE **must** conduct an
> assessment of FOOD prepared or served by the FOOD EMPLOYEE while symptomatic
> and take appropriate corrective actions. […] Records must be maintained for 1
> year and available for review during inspections.
>
> **Nonfood employees:**
> - ISOLATION in cabin or designated restricted area until symptom-free for a
>   minimum of 24 hours.
> - Follow-up with and receive approval by designated medical personnel before
>   returning crew to work.

Against §4.4.2.1 for the other complement:

> **Isolate Ill Passengers (11 C)** — *Advise* symptomatic passengers and those
> meeting the case definition to remain isolated in their cabins until well for
> a minimum of 24 hours after symptom resolution. Follow-up by infirmary
> personnel is **advised**.

The manual's own glossary states the asymmetry directly: "isolation for
passengers with AGE symptoms is **advised** and isolation for crew with AGE
symptoms is **required**" (quoted, with the food/nonfood 48 h/24 h split, in
Maritime Health Systems' 2024 review of the policy, origin **Sec**; both halves
verified against the manual text above).

Three properties matter for the model, and none of them is a magnitude to fit:

1. It is **unconditional and immediate** — it attaches to the first symptomatic
   crew member, with no outbreak threshold, no escalation status and no
   diagnostic gate beyond self-report to the infirmary.
2. It **removes the exposure the model amplifies**: a food employee is isolated
   in cabin, i.e. out of the service zones where the model applies
   `crew_contact_multiplier` 2.0, `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR`
   545.4 and `FOOD_HANDLER_CONTACT_MULTIPLIER` 12.7.
3. Its **duration is stated by the regulation** — symptomatic period plus 48 h
   (food) or 24 h (nonfood) — so the structure carries no free parameter. The
   one quantity that *is* free is compliance, and that is §3.

## 2. What the model has instead

Symptom-triggered removal from duty exists in the model only as **SOP-008,
"Individual Symptomatic Confinement to Quarters", gated at escalation status
ALERT** — an outbreak-level trigger. In the quiet region that gate is exactly
the one that never fires: 55.1% of those voyages carry ~5% infection with zero
ill passengers, so a ship can run a whole voyage with symptomatic crew working
service zones under all three multipliers. Confinement's machinery is present
and adequate (`_cabin_confinement_active`, emission and direct-contact factors
0.05 / 0.01); what is absent is the **standing, non-reactive rule** that puts a
symptomatic crew member into it, and the asymmetry between that rule and the
advisory one for passengers.

This is the mirror image of the model's crew arm as built: crew are more
exposed than passengers by construction and are removed from exposure by
nothing. The direction of the regulated world is the opposite, which is the
right sign to explain a crew channel firing ~100× more often than the observed
record.

## 3. The compliance share — bounded, not adoptable, and now on the wrong population as well as the wrong denominator

Tranche 30 §1 recorded the food-handler presenteeism bound as *bounded, not
adoptable*: 11.9% of 491 US food workers worked two or more shifts while
vomiting or with diarrhoea in the previous year (Sumner 2011,
DOI 10.4315/0362-028x.jfp-10-108), ~20% at least one shift (Carpenter 2013,
DOI 10.4315/0362-028x.jfp-13-128), and one third of restaurant policies not
specifying exclusion at all (Norton 2015, DOI 10.4315/0362-028x.jfp-14-134,
whose reason breakdown is staffing and pay). Every figure is 12-month
worker-level recall where a per-shift probability is needed.

Two further reasons those numbers cannot be carried across, both of which
strengthen the direction rather than the magnitude:

- **Regime.** They measure a population where exclusion policy is often absent
  (Norton's one-third) and unpaid absence is the alternative. VSP's crew arm is
  a mandatory, inspected, records-retained regime with free onboard medical
  access. A land-based presenteeism rate is an upper bound on the maritime one
  at best, and there is no reason to think it a tight one.
- **∅ null for the maritime arm.** No measurement of the share of AGE-symptomatic
  cruise crew who continue working, or of time from symptom onset to isolation,
  was retrieved. Anecdote exists (passenger reports of visibly ill buffet crew)
  and is refused as a quantity.

So the compliance share stays **∅ null**, and the structure must be swept over
it rather than adopting a value — the standing of `FOOD_HAND_CONTACTS_PER_DAY`.
Perfect compliance is the regulation's own stated content and is the natural
first arm; it is not a claim that ships achieve it.

## 4. The two crew exposure multipliers do **not** carry the excess

Before reaching for a new term, the two crew-specific multipliers were removed
one at a time at the quietest gate point (index 46, 36 seeds, the shipped
structure otherwise untouched; `no_surface` sets the service-zone surface rate
to the generic dining rate, `no_food` sets the food-handler multiplier to 1.0):

| arm | crew ≥3% | pax ≥3% | mean crew reported AR | mean pax reported AR |
|---|---:|---:|---:|---:|
| baseline | 1/36 | 0/36 | 0.00290 | 0.00256 |
| `no_surface` | 1/36 | 0/36 | 0.00249 | 0.00352 |
| `no_food` | 1/36 | 1/36 | 0.00311 | 0.00291 |

Read as a **negative result with weak power**, which is what it is: at a point
that posts on ~3% of voyages, 36 seeds cannot resolve a factor-of-two change in
posting frequency, and the means move within noise in both directions. What it
does say is that neither multiplier is a *dominant* term at this point — there
is no order-of-magnitude effect hiding behind either — consistent with the
Morris screen, where the four food/faecal axes ranked 3rd–6th at 35–151× below
the top factor. That is the reason to go at a structure rather than at these
constants, and the reason not to touch their values.

## 5. What this licenses

- **Licensed:** the observed crew channel is measured under a mandatory duty
  exclusion whose trigger, scope and duration are stated in the regulation, and
  the model has no such term; its only symptom-triggered removal is gated at
  ALERT and does not fire in the quiet region at all.
- **Licensed:** the crew/passenger direction of the regulated world is the
  opposite of the crew/passenger direction the model is built with.
- **Not licensed:** any claim that adding the rule brings A9 into reach. The
  crew channel is 51.5% of the quiet region's postings; passenger-only scoring
  is still 2.23%, ~4× A9's ceiling, so this can at most remove half the excess
  and the frequency shortfall survives it.
- **Not licensed:** a compliance value, a minimum-case publication floor, or any
  move in the three crew exposure multipliers.
- **Refused:** reading the exclusion's effectiveness off A9. The rule's content
  is exogenous; its consequence for the posting rate is the measurement.
