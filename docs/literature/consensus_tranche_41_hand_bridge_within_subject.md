# Tranche 41 — the hand bridge is sourceable after all, within one subject at a time, and the shipped −7.14 is an artefact of pairing two cohorts that disagree by 3 logs

**Register rows fed / supersession.** Feeds the register rows for
`HAND_LOAD_LOG10_GEC` and `HAND_LOAD_REFERENCE_PEAK_LOG10`
(`engines/infection_dynamics_bridge.py`) and the open ledger's §4 items 22(f),
23 and 24(b). It **closes** item 23(f)'s first option — norovirus copies per
hand *and* stool titre in the same subjects — which tranche 26 recorded as a
null, tranche 39 carried forward, and tranche 40 partly withdrew. It **moves no
constant and adopts none.**

**Status:** Evidence assembled, definitional check passed, arithmetic
reproduced in
[`hand_bridge_pairing.py`](../../telemetry_buffer/observation_model/hand_bridge_pairing.py).
Nothing implemented.

**Scope.** Item 22(f) asked for the mass of faecal material on a contaminated
hand, read independently of A9, so the hand and environmental channels sit on
one measured scale. Tranche 39 answered with a two-surrogate indicator
envelope; tranche 40 found the direct pairing existed in Liu's Table 3 but
recorded it as bounding rather than measuring. This tranche does three things
tranche 40 did not: it checks whether Liu's two columns are the same unit as
the shipped curve, it computes the bridge *within* each subject instead of
across studies, and it tests the proportionality that the bridge's functional
form assumes.

**Result in one line.** Liu's numerator and denominator are the same unit class
as Atmar's curve — verified verbatim from the Statistical analysis section —
and paired within subject they give a bridge of **−4.14 log10 g of stool per
hand [−4.36, −3.75], n = 4 subjects, SD 0.29**, read from Table 3. The shipped
**−7.14** is not a measurement of anything: it is Liu's hand load divided by
*Atmar's* peak, and **every one of Liu's six stool maxima falls below Atmar's
16-subject minimum**, so the shipped constant is precisely the width of an
unreconciled cohort discrepancy. Sourcing the bridge therefore **raises** the
hand load by 3.00 log10, which is the direction item 25(e) predicted and the
opposite of what A9 needs.

---

## 1. E0 triage — what would settle the row

| Question | Unit that would settle it | Retrieved? |
|---|---|---|
| Are Liu's stool and hand columns the same unit as the shipped curve? | the paper's own unit statement | **Yes** — §2, Methods |
| Bridge within one subject | log10 g stool/hand, same subject both sides | **Yes** — §3, Table 3 |
| Does hand load scale with stool titre at all? | log-log slope, paired | **Yes, and it is underpowered** — §4 |
| Why Liu's cohort sits 3 logs below Atmar's | assay standard or sampling window | **Partially — §5, direction only** |
| Mass of faeces on a hand, gravimetric | g/hand | **∅ null, unchanged** — §6 |
| Oie's per-gram denominator | total culturable microbes per g faeces | **`?nr-term`, and the route is now moot** — §6 |

## 2. The definitional check, which is the whole reason this row moves

Tranche 40 reported Liu's Table 3 pairing but did not establish that its two
columns were commensurable with each other or with the shipped curve. They are.
Liu, *Statistical analysis*, quoted verbatim:

> "NV concentrations in stool samples and hand rinse samples were expressed as
> **log10 GEC per gram of feces** and **total log10 GEC per hand**,
> respectively."

Liu, Escudero-Abarca, Jaykus et al. 2013, *Appl Environ Microbiol* 79:7875,
[10.1128/AEM.02576-13](https://doi.org/10.1128/aem.02576-13). Retrieval: three
Consensus phrasings returned the abstract only; full text opened at
**PMC3837815** (E2 route switch, PMC HTML). Origin **Me** for the unit
statement, **T3** for the table, **R** for the positivity fractions.

Atmar et al. 2008, *Emerg Infect Dis* 14:1553,
[10.3201/eid1410.080117](https://doi.org/10.3201/eid1410.080117) — the source
of `SYMPTOMATIC_SHEDDING`, per that constant's own provenance comment — reports
**genomic copies/g feces** by quantitative RT-PCR. Origin **R**.

Same analyte, same genogroup (GI.1 Norwalk, both experimental challenge), same
assay family, same unit. **No conversion is applied or needed, and there is no
unit error to find here.** That matters because it is the only thing standing
between this row and the standing prior that a three-log gap is a unit defect.

## 3. The bridge, paired within subject

Table 3 gives each infected subject's **maximum stool titre** over the day 0–4
sampling window and that subject's **mean positive hand load**. Four of six
subjects have both; two never had a positive hand rinse, which is data, not a
missing value.

| Subject | Max stool, log10 GEC/g | Mean hand, log10 GEC/hand | Bridge, log10 g |
|---|---|---|---|
| 34 | 8.3 | 3.94 | **−4.36** |
| 36 | 8.1 | 3.74 | **−4.36** |
| 46 | 7.4 | 3.30 | **−4.10** |
| 54 | 8.2 | 4.45 | **−3.75** |
| 37 | 7.4 | no positive rinse | — |
| 40 | 7.5 | no positive rinse | — |

**Within-subject bridge: −4.14 log10 g of stool per hand, range −4.36 … −3.75,
SD 0.29, n = 4 subjects.** Origin **T3**. Grade **B** — a direct measurement of
this quantity in an analogous setting: the right pathogen, genogroup and unit
in experimentally infected humans, but a hospital challenge ward rather than a
vessel, and see §5 for two bounds that act on it in opposite directions.

Against the shipped constant:

```
shipped   = 3.86 (Liu, hands)  −  11.00 (Atmar, curve peak)  = −7.14
sourced   = mean over subjects of (that subject's hands − that subject's stool)
          = −4.14
difference                                                   = +3.00 log10
```

The shipped value is a **cross-study quotient**, and its numerator and
denominator come from cohorts that do not overlap (§5). Item 22(d) called it a
Class X convention that no study has measured; that was right, and this tranche
adds *why* it takes the value it does.

## 4. The scaling assumption, tested for the first time

The engine does not merely need a level. It asserts a functional form —

```python
hand_gec = 10**HAND_LOAD_LOG10_GEC * 10**(curve - HAND_LOAD_REFERENCE_PEAK_LOG10)
```

— which is a log-log slope of exactly 1 between stool titre and hand load. No
tranche had ever checked it. Liu's four paired subjects give:

| Statistic | Value |
|---|---|
| OLS slope | **+0.93** log10 hand per log10 stool |
| Pearson r | **+0.80** |
| n | 4 subjects |
| p, two-sided | **0.20** |

**Consistent with proportionality and far too small to establish it.** The
stool titres span 0.9 log10 in total, so this sample cannot distinguish a
proportional hand load from a fixed one, and with two of six subjects at zero
the selection is not innocent either. Record as **direction supported,
magnitude unestablished** — it is evidence that the form is not refuted, and it
is not licence to call the form sourced.

## 5. What the shipped pairing actually spans

| Source | Stool titre, log10 /g | n |
|---|---|---|
| Liu 2013, max over day 0–4 | **7.4 … 8.3** | 6 |
| Atmar 2008, peak | **8.7 … 12.2** (median **11.0**) | 16 |
| Shipped curve peak | 11.0 | — |

**Every one of Liu's six maxima lies below Atmar's minimum.** Six subjects all
below the sixteen-subject floor of the other study is not sampling noise, and
§2 rules out a unit error, so this is a cohort or assay-standard discrepancy
between the two papers that jointly define the hand route. Two bounds act on
the within-subject bridge in opposite directions, and **neither is quantified**:

- **Liu's window is truncated.** Stool sampling ran days 0–4, while Atmar's
  peak fell at a median of day 4 and was highest *after* clinical resolution in
  11/16 subjects. Liu's maxima are therefore lower bounds on those subjects'
  true peaks, which biases the within-subject bridge **high**.
- **Hand rinse recovery efficiency is unmeasured.** 3.86 log10 GEC/hand is a
  lower bound on what was on the hand, which biases the bridge **low**.

Note the arithmetic coincidence, and do not read anything into it: if Liu's
subjects had peaked at Atmar's median, their bridge would have been −7.14. The
shipped constant is what you get by assuming the discrepancy away in one
particular direction. That is an explanation of the constant's provenance, not
a defence of its value, and not evidence for either bound above.

## 6. Rows that stay shut

- **Gravimetric faecal mass on a hand: ∅ null, unchanged.** Two further
  phrasings naming milligrams, tracer and anal cleansing returned indicator
  studies of the same class tranche 39 already recorded (Bauza 2019 Odisha,
  Adhikari 2026 Nepal latrine surfaces) and no gravimetric measurement. The
  field does not weigh faeces on hands.
- **Oie's per-gram denominator: `?nr-term`, and the route is now moot.** Item
  23(e) needed total culturable microbes per gram of faeces to convert Oie's
  39,499 CFU/glove. Van Houte & Gibbons 1966, *Antonie van Leeuwenhoek*
  ([10.1007/bf02097463](https://doi.org/10.1007/bf02097463), origin **R**) put
  *Bacteroides* at ≈10¹⁰/g wet weight with anaerobes outnumbering facultatives
  40-fold and coliforms, streptococci and lactobacilli at 10⁶–10⁸/g — so the
  denominator differs by 2–3 logs depending on whether Oie's count was aerobic
  or anaerobic, and Oie's culture conditions were not retrieved. The
  indicator→norovirus conversion this route needs is now unnecessary: §3
  supplies the quantity in norovirus genome copies directly, without a
  surrogate. **Do not spend further queries here.**

## 7. What this does to the model, recorded before any implementation

Composing the direct-contact route through the hand reservoir
([`direct_contact_hand_composition.md`](../proposals/direct_contact_hand_composition.md),
`DIRECT-HAND-01`) lowers the per-contact dose by ~4.7 logs. Sourcing the bridge
raises it by 3.00. They act against each other, and the net is **~1.7 logs
down, not 4.7**. At the curve peak, on the 0.13 transfer arm — an explicit
analogy over tranche 12's person-to-person null, not an adopted constant:

| Route | Ingested, GEC/contact | P(establishment) |
|---|---|---|
| Shipped, uncomposed | 1.46 × 10⁵ | **0.6064** |
| Composed, shipped −7.14 bridge | 3.19 | **0.0103** |
| Composed, sourced −4.14 bridge | 3.17 × 10³ | **0.3987** |

So the level repair alone takes per-contact establishment from 0.61 to 0.40,
and **that is not enough to make posting a rate rather than a ceiling.** What
carries the rest is in the same table and is not a level at all:

- **25.4% (18/71)** of rinses from symptomatic, stool-positive hosts were
  positive at a 2.15 log10 limit, so roughly three contacts in four carry
  nothing.
- **Two of six** infected subjects never had a positive hand — host-level
  heterogeneity, in the sourcing dataset itself.
- Per-subject positivity **0% … 54.5%**.

Item 24(c) already refuted the engine's non-event hand mode on these grounds.
This tranche adds that the intermittency is not a refinement to be added after
the level is fixed: **it is the part of Liu that does the work**, and a composed
route built on the mean alone would deliver 0.40 per contact to every partner of
every shedder.

Per the first rule of `model-parameter-provenance`, the sign is recorded here,
before implementation, precisely so that it cannot later be read off A9: a
sourced bridge raises the hand load and is expected to make A9 **worse**, and
that is a result about what is still missing, not a reason to prefer the
unsourced value.
