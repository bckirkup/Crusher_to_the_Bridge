# Tranche 41 — the within-subject hand bridge computes, and is refuted for this engine

**Read first:** the headline this note originally carried — that Liu Table 3
sources a −4.14 log10 g/hand bridge that should replace the shipped −7.14 —
was **withdrawn**. The paired arithmetic below is the record; the
interpretation was wrong on two counts, and both corrections are in the body:
(1) `HAND_LOAD_REFERENCE_PEAK_LOG10 = 11.0` is the **shipped curve's own
peak** (`max(SYMPTOMATIC_SHEDDING)`), not Atmar's cohort median, so the
shipped pair `3.86 − 11.0` is a peak-normalised anchor — the hand load at a
host's own peak, exactly what Liu measures — and not a cross-cohort quotient;
(2) applied to the shipped curve the −4.14 offset predicts **6.86 log10
GEC/hand at peak**, exceeding the largest mean hand load Liu ever measured
(**4.45**), so it contradicts the hand column it was read from. It was never a
candidate value.

**Register rows fed / supersession.** Feeds the register rows for
`HAND_LOAD_LOG10_GEC` and `HAND_LOAD_REFERENCE_PEAK_LOG10`
(`engines/infection_dynamics_bridge.py`) and the open ledger's §4 items 22(f),
23 and 24(b). It does **not** close item 23(f)'s first option — the pairing
exists but cannot serve as this engine's offset. What survives as actionable
evidence from the same table is host-level carriage heterogeneity, now
implemented as `HAND_CARRIAGE_PROPENSITY_BETA`
(`engines/infection_dynamics_bridge.py`). It **moves no constant and adopts
none.**

**Status:** Evidence assembled, definitional check passed, arithmetic
reproduced in
[`hand_bridge_pairing.py`](../../telemetry_buffer/observation_model/hand_bridge_pairing.py)
— which reports the paired difference as the refutation input, not a
candidate offset. Nothing implemented from the bridge itself.

**Scope.** Item 22(f) asked for the mass of faecal material on a contaminated
hand, read independently of A9, so the hand and environmental channels sit on
one measured scale. Tranche 39 answered with a two-surrogate indicator
envelope; tranche 40 found the direct pairing existed in Liu's Table 3 but
recorded it as bounding rather than measuring. This tranche checked whether
Liu's two columns are the same unit as the shipped curve, computed the bridge
*within* each subject instead of across studies, and ran the test that refuted
it.

**Result in one line.** Liu's numerator and denominator are the same unit class
as Atmar's curve — verified verbatim from the Statistical analysis section —
and paired within subject they give a difference of **−4.14 log10 g of stool
per hand [−4.36, −3.75], n = 4 subjects, SD 0.29**, read from Table 3. Read as
an engine offset it fails immediately: it would put a peak-day hand at 6.86
log10 GEC against Liu's own maximum of 4.45. The shipped **−7.14** is a
peak-normalised convention between Liu's pooled hand load and the shipped
curve's own peak — the Class X anchor its definition comment declares — and
the cohort-gap observation beneath it (**every one of Liu's six stool maxima
falls below Atmar's 16-subject minimum**) remains true data about a cohort or
assay-standard discrepancy, not a defect the engine inherits.

---

## 1. E0 triage — what would settle the row

| Question | Unit that would settle it | Retrieved? |
|---|---|---|
| Are Liu's stool and hand columns the same unit as the shipped curve? | the paper's own unit statement | **Yes** — §2, Methods |
| Bridge within one subject | log10 g stool/hand, same subject both sides | **Yes** — §3, Table 3 |
| Does hand load scale with stool titre at all? | log-log slope, paired | **Retrieved, but wrong test** — §4's slope is across subjects at their own peaks, not within-host over time |
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

Against the shipped constant — the comparison this tranche originally drew,
kept as the record of the misreading:

```
shipped   = 3.86 (Liu, hands)  −  11.00 (Atmar, curve peak)  = −7.14
sourced   = mean over subjects of (that subject's hands − that subject's stool)
          = −4.14
difference                                                   = +3.00 log10
```

The correction: **11.0 is the shipped curve's own peak, not a reading of
Atmar's cohort.** `curve − 11.0` is the distance below the host's own peak, and
3.86 is Liu's hand load at peak — the pair is a peak-normalised anchor, the
Class X convention item 22(d) declared, not a cross-study quotient. And the
−4.14 figure is not an alternative anchor: shipped onto the curve it predicts
6.86 log10 GEC/hand at peak, which contradicts Liu's own hand column (maximum
subject mean 4.45). Refuted, not adopted.

## 4. The scaling assumption — the test that was run here does not reach it

The engine asserts a functional form —

```python
hand_gec = 10**HAND_LOAD_LOG10_GEC * 10**(curve - HAND_LOAD_REFERENCE_PEAK_LOG10)
```

— which is a log-log slope of exactly 1 between a host's *same-day* stool
titre and its hand load. Liu's four paired subjects give:

| Statistic | Value |
|---|---|
| OLS slope | **+0.93** log10 hand per log10 stool |
| Pearson r | **+0.80** |
| n | 4 subjects |
| p, two-sided | **0.20** |

But this slope is computed **across subjects, each at its own peak** — a
between-subject level relation, not a within-host time course. The engine's
assumption is about how one host's hand tracks its own curve over days, and
this data contains no such pair of time series, so the +0.93 was never a test
of it. The original "direction supported, magnitude unestablished" verdict
overstated: the number is real; the test it was claimed to perform does not
exist in this data.

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
subjects had peaked at Atmar's median, their within-subject difference would
have been −7.14. That is numerology — the shipped constant is Liu's hand load
read against the shipped curve's own peak, not any assumption about the
cohort gap — and it is not evidence for either bound above.

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

## 7. What this does to the model — the comparison kept, the conclusion withdrawn

Composing the direct-contact route through the hand reservoir
([`direct_contact_hand_composition.md`](../proposals/direct_contact_hand_composition.md),
`DIRECT-HAND-01`) lowers the per-contact dose by ~4.7 logs. The arithmetic
below compared the shipped anchor against the −4.14 pairing as if both were
candidates; only the first is. The −4.14 column is the refutation record — the
offset that would put peak-day hands at 6.86 log10, above every hand Liu
measured. At the curve peak, on the 0.13 transfer arm — an explicit analogy
over tranche 12's person-to-person null, not an adopted constant:

| Route | Ingested, GEC/contact | P(establishment) |
|---|---|---|
| Shipped, uncomposed | 1.46 × 10⁵ | **0.6064** |
| Composed, shipped anchor | 3.19 | **0.0103** |
| Composed, refuted −4.14 offset | 3.17 × 10³ | **0.3987** |

What carries the work is in the same table and is not a level at all — and it
is the part that survived the refutation:

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

The closing prediction of the original note — that a sourced bridge raises
the hand load and would make A9 worse — is withdrawn with the bridge itself.
No hand-load constant moved on this evidence, and none may: the pairing that
would move it is refuted for this engine.
