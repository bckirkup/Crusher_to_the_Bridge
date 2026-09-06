# Tranche 29 — the food route's four constants: one composes from measured parts, one is not a biological quantity at all, and two are aggregations nothing measures

**Register rows fed / supersession.** This tranche feeds four §3.1 rows —
`FOOD_DEPOSITION_FRACTION_OF_EMISSION`, `FOOD_INGESTION_FRACTION_PER_DAY`,
`ENV_DELIVERY_FRACTION_PER_DAY`, `ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION` —
none of which had a row before, and adds one external route-share constraint
row. It supersedes nothing. It withdraws nothing that the DIM-01 repair
(#447) had not already withdrawn.

**Status:** Evidence assembled and interpreted, **sourcing only**. **No profile
constant, engine constant, config value or code path changes numerically in
this document's change**; the four constants keep the values they have had
since they were authored, and the only code edit is the provenance header at
each definition. Like every document in `literature/`, this is context, not
truth: where it and the register disagree, the register holds the status and
this document holds the citations.

**Scope:** the four food and environmental pool fractions whose *units* #447
repaired and whose *provenance* it explicitly left open, plus the two open
questions recorded against them there (whole-gut transit; diarrhoeal liquid is
not ingested food).

**Method:** Consensus MCP, unfiltered, `include_full_text_chunks: true`,
eleven queries recorded verbatim in §7. One returned a rate limit and was
re-run rather than recorded as a null. Mouchtouri 2024's Table 3 was not
resolvable from the Consensus chunks, so it was read from the Europe PMC JATS
full text (PMC10986668) — origin **T3** below means that table, not the
abstract. Two of the four quantities were also checked against evidence
**already in this repository**: tranche 12 retrieved the hand→food transfer
legs in 2026 and excluded them *on material* for the fomite row, which is
precisely the material the food route needs.

**Result in one line.** The deposition constant is the only one of the four
that composes out of measured parts, and it does: hand load (Liu 2013, in
tree) × hand→food transfer (tranche 12's excluded food legs) makes the shipped
`1e-4` **equivalent to 0.3–46 bare-hand food-contact events per shedder per
day**, which is an admissible order of magnitude rather than a defect. The
ingestion fraction is **not a biological parameter** — 0.05/day means 85% of
contaminated food is still in the pool tomorrow, which is food-service
logistics, and it, not the deposition constant, is what makes the food route
dominant. The two environmental fractions are **aggregations no study
measures**; the only literature values in their shape are fitted compartmental
rates, rejected as model outputs. Separately, an external and non-circular
route-share constraint now exists (§5) and the food route's 93–99.9% share of
delivered dose is **inconsistent** with it.

---

## 1. The four quantities, and what would count as measuring each

Read to the epoch as #447 left them:

| Constant | Model meaning | Would be measured by |
|---|---|---|
| `FOOD_DEPOSITION_FRACTION_OF_EMISSION` = 1e-4 | share of a shedder's per-epoch faecal emission that enters the zone's communal food pool | a study reporting virus deposited on food *as a fraction of the depositor's stool output* |
| `FOOD_INGESTION_FRACTION_PER_DAY` = 0.05 | fraction of the standing food pool removed per day by consumption, compounding | food-service turnover: what share of served food is eaten or discarded per day |
| `ENV_DELIVERY_FRACTION_PER_DAY` = 0.01 | fraction of a standing environmental load delivered to occupants per day, without depleting it | a study reporting occupant intake as a fraction of a measured room load |
| `ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION` = 1e-4 | share of a per-epoch emission entering the environmental reservoir | the deposition analogue of the first row, for the non-food reservoir |

Two of these are **fractions of an emission** — the denominator is the
depositor's own output — and two are **rates on a standing stock**. No assay in
the enteric literature uses emission as its denominator (the same finding that
retired `contact_transfer_fraction` in #22), so rows 1 and 4 cannot be
measured directly; they can only be **composed** from a load and a transfer,
or left declared. Rows 2 and 3 are not virology at all.

## 2. `FOOD_DEPOSITION_FRACTION_OF_EMISSION` — it composes, and the composition holds

The fomite route already has the architecture this constant lacks: a per-hand
absolute load (`HAND_LOAD_LOG10_GEC` = 3.86, Liu 2013, six experimentally
infected GI.1 subjects, 18/71 hand rinses positive, mean 3.86 log10
genome-equivalent copies per hand, DOI 10.1128/aem.02576-13, Grade **B**),
a contact count, a transfer efficiency drawn per event, and **depletion of the
hand**. The food route has a single fraction of the whole faecal emission.

The transfer leg for food material was already retrieved by
[tranche 12](consensus_tranche_12_contact_transfer.md) §, where it was
excluded *on material* because that row is about non-porous maritime surfaces.
For food it is the governing evidence:

| Donor → food | Value | Source |
|---|---|---|
| bare finger pad → ham | 46 ± 20.3 % | Bidawid 2004, DOI 10.4315/0362-028x-67.1.103 (FCV, infectivity) |
| bare finger pad → lettuce | 18 ± 5.7 % | Bidawid 2004 |
| finger → cucumber slice | 7 ± 8 % | Tuladhar 2013, DOI 10.1016/j.ijfoodmicro.2013.09.018 (MNV-1) |
| finger → tomato | 0.3 ± 0.5 % | Tuladhar 2013 |
| glove → cucumber | 1.5 ± 1.9 % (HuNoV), 1.2 ± 0.6 % (MNV) | Rönnqvist 2014, DOI 10.1128/aem.01162-14 |
| hand → lettuce | 25 % | Grove 2015, DOI 10.1016/j.ijfoodmicro.2014.12.023 |

Interval, all norovirus or norovirus surrogate, food material, **Grade B**:
**0.3 – 46 %** per contact, spanning ~2 orders on food matrix alone (Tuladhar
attributes his own cucumber/tomato spread to moisture content). Human
norovirus figures are genome copies; every infectivity figure is a surrogate,
so **B is the ceiling here too**, not a provisional grade.

**The composition.** At the shipped GI.1 curve peak (11.0 log10 copies/g) and
`environmental_faecal_release_log10_g_per_epoch` = 4.0, a shedder releases
`10^(11−4)` = 1e7 copies/day, and the shipped constant deposits
`1e-4 × 1e7` = **1e3 copies/day** into the food pool. One hand carries
`10^3.86` = 7,244 copies, so one bare-hand food contact delivers 22–3,332
copies across the transfer interval, and the shipped constant is equivalent to

> **0.3 – 46 bare-hand food-contact events per shedder per day**
> (0.3 at ham-grade transfer, 46 at tomato-grade).

That is an admissible order of magnitude for a shedder who touches communal
food at all. **The constant's value is therefore not the food route's
defect** — its *structure* is (§6): it does not deplete the hand, it applies
to every shedder present rather than to food handlers, and because its
denominator is the faecal emission it tracks stool titre rather than hand
load, so the drying and handwashing levers the fomite route respects cannot
reach it.

Grade: the value stays **C, declared**, now with a **B-composed corridor**
around it. Promoting it to B would require a measured contact rate (§4).

## 3. `FOOD_INGESTION_FRACTION_PER_DAY` — not a biological quantity, and it is what makes the food route dominant

At 0.05/day consumption and the shipped `food_contamination.decay_rate_per_day`
= 0.1, the pool retains `0.95 × 0.90` = **85.5 % of its contents each day**:
contaminated food is still there a week later. The literature does support
**virus** persistence on that timescale — HuNoV on berries, vegetables and
fruit shows < 1 log reduction in 1–2 weeks (Cook 2016 critical review, DOI
10.4315/0362-028x.jfp-15-570), and MNV infectivity on lettuce falls 1 log in
4 days ≈ 0.44/day (Fallahi 2011, DOI 10.4315/0362-028x.jfp-11-081), which is
**4× faster than the shipped 0.1/day**, so the decay rate is the conservative
choice within the evidence.

What the literature does **not** support is *food* persisting. Served food
leaves a buffet by consumption or discard within a service period; what is
measured in that space is plate waste in grams (e.g. hotel breakfast/dinner
buffet plate-waste studies retrieved in §7 query 6), not a per-day carry-over
fraction of a standing pool. So this constant is **food-service logistics
declared as a rate**, class **C**, and no literature search can raise it:
the quantity it would need is an operational holding/discard rule, not a
measurement.

**Consequence, and it is the substantive one.** With 85.5 %/day carry-over the
pool integrates every shedder's deposits over the whole voyage and delivers to
*every* occupant *every* day, whereas contact and fomite exposure are discrete
and rare. That accumulation — not the deposition constant of §2, whose
magnitude checks out — is the mechanism behind the food route's 93–99.9 % share
of delivered dose recorded in `clock_unit_safety_spec.md`. It is the pool
archetype: a persistent well-mixed reservoir standing in for discrete
servings.

**Identified but unretrieved:** the VSP Operations Manual's time/temperature
holding and discard requirements would bound the residence time of served
food directly, in the target setting, and would make this constant's ceiling
an operational fact rather than an assumption. Not retrieved in this pass.

## 4. What the food route would need, and what is null

| Leg of a decomposed food route | Status |
|---|---|
| virus on a shedder's hand | **B, in tree** — Liu 2013, `HAND_LOAD_LOG10_GEC` |
| hand → food transfer per contact | **B, retrieved** — 0.3–46 %, §2 |
| bare-hand contacts with communal food per person per day | **∅ null.** Nothing found. The nearest retrievals are bacterial loads on self-service touchscreens (0.07–2.0 CFU/cm², a fast-food pilot study) and phthalate hand-to-mouth touch frequencies (10.4–25.4 touches/h on desks and devices) — neither is a food-contact rate for a communal food surface |
| who deposits: any shedder, or food handlers | **B against the model's shape.** NEARS 2017–2019: norovirus is 47.0 % of retail foodborne outbreaks with a confirmed/suspected agent, and ~40 % of outbreaks with identified contributing factors had at least one factor of food contamination by an **ill or infectious food worker** (Moritz 2023, MMWR Surveill Summ 72(6), DOI 10.15585/mmwr.ss7206a1). The real route is worker-mediated; the model's is occupant-mediated |
| gut transit, and formed stool vs diarrhoeal liquid | **∅ null as a parameter, real as a mechanism.** #447 recorded both. Nothing retrieved maps either onto a fraction-of-emission field; they bear on *which* emission is available to deposit, which is a shape question, not this constant's value |

## 5. An external, non-circular route-share constraint now exists

Mouchtouri 2024 (*Eurosurveillance* 29(10), DOI
10.2807/1560-7917.es.2024.29.10.2300345) systematically reviews 45 norovirus
outbreaks on 26 cruise ships, 1990–2020; 41 report source and mode. Table 3
(read from the JATS full text, PMC10986668 — origin **T3**):

| Mode | Outbreaks |
|---|---|
| Person-to-person | 14 |
| Person-to-person and environmental | 11 |
| Multiple modes (a) | 10 |
| Food-borne | 3 |
| Waterborne | 3 |
| Unknown | 4 |

(a) is defined in the paper's footnote as four mixtures, three of which
include food or water. So **food as the sole mode is 3/41 = 7.3 %**, and food
involvement bounded from above by counting every mixed-mode outbreak as
food-involved is **13/41 = 32 %**. Text: person-to-person was the most frequent
mode in 35 of 45 outbreaks.

This is admissible as evidence because it is a **mode-attribution count**, a
different observable from the attack-rate and posting-rate anchors A1/A2/A4/A8
the model is scored against. Table 3's attack-rate columns are deliberately
**not** used here for exactly that reason.

Against it, a model in which the food route delivers 93–99.9 % of dose is
inconsistent with the setting's own outbreak record. This is recorded as an
external check the model currently fails, **not** as a target to tune to: no
constant in this tranche may be moved to bring the share to 7–32 %.

## 6. The structural finding, stated as a defect rather than acted on

`FOOD-ARCH-01`. The food route is the fomite route with three of its four
stages missing. The fomite path in `transmission_core.py` replenishes a hand
load from the measured target, draws a per-event transfer efficiency, counts
contacts, applies the drying multiplier, and **subtracts the deposit from the
hand**. The food path multiplies the whole faecal emission by one constant,
for every shedder in the zone, with no hand, no contact count, no depletion
and no hygiene lever — so the NPI interface (#9/#10), whose buffet-prompt arms
act on hand-mediated routes, has almost nothing to act on in the route that
carries the dose.

Repairing that is a **model-structure change** with a moved-golden footprint
on every food-route figure, and it is not done here. What §2 establishes is
that the parts for it are already sourced: hand load B (in tree), hand→food
transfer B (§2), contact rate null and therefore swept.

## 7. Queries, verbatim

Unfiltered; `search` called with `query` and `include_full_text_chunks` only.

1. `norovirus transfer efficiency from contaminated fingers to food percent`
2. `food handler transfer of norovirus to ready-to-eat food percentage of virus transferred`
3. `norovirus concentration on contaminated food genome copies per gram outbreak`
4. `faecal virus transfer to hands and environment fraction of shedding deposited`
5. `proportion of cruise ship norovirus outbreaks foodborne versus person-to-person mode of transmission attributed`
6. `buffet food holding time turnover discard ready-to-eat food service duration hours`
7. `norovirus survival persistence on food lettuce ham days reduction genome copies`
8. `hand to mouth surface contact fraction of surface load ingested per hour fomite exposure quantitative`
9. `hand contamination after toileting norovirus quantitative virus recovered from fingers of infected persons genome copies`
10. `self-service buffet serving utensil contamination virus bacteria touch frequency guests hands quantitative`
11. `food handler norovirus infected proportion of foodborne outbreaks attributable food worker CDC surveillance`
12. `quantitative microbial risk assessment norovirus foodborne dose per serving contaminated food genome copies ingested`
13. `fraction of environmental surface virus load transferred to occupants per day zone reservoir delivery rate measured`
14. `norovirus environmental reservoir to person transmission rate per day fraction of load delivered epidemiological model measured`

Query 2 hit `Rate limit exceeded` on the first attempt and was re-run; that is
not recorded as a null.

## 8. The two environmental fractions

`ENV_DELIVERY_FRACTION_PER_DAY` (0.01/day) and
`ENV_HOST_DEPOSITION_FRACTION_OF_EMISSION` (1e-4) are **∅ null**, on two
different grounds.

- The delivery fraction's shape — a fraction of a standing zone load reaching
  occupants per day, without depleting the load — appears in the literature
  only as the environmental transmission rate of **fitted compartmental
  models** (e.g. Gogovi 2025, DOI 10.1155/ijde/5517340, whose sensitivity
  analysis makes exactly this parameter the most influential). Those are model
  outputs fitted to incidence, and are **rejected on the register's standing
  rule**, the same rule that excluded the QMRA transfer fractions in tranche 12
  and the fitted cabin shares in tranche 17. Queries 8 and 13–14 found no
  measurement: the nearest empirical work in that shape is chemical
  (hand-to-mouth phthalate ingestion, Li 2021 DOI
  10.1016/j.envint.2020.106266; Yuan 2024 DOI 10.1016/j.buildenv.2024.111976),
  where hand-to-mouth contributes 35–55 % of total exposure — a **mechanism
  precedent, not a virus rate**.
- The host deposition fraction is the §1 emission-denominator problem again,
  and unlike the food case there is no matched pair of measurements to compose
  it from: the reservoir it feeds is not a defined material, so no transfer
  assay is commensurable with it.

Both stay **C, declared**, with the composition route open only for the food
side.
