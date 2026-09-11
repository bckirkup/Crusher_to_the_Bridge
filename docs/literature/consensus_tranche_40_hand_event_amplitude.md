# Tranche 40 — the hand load is intermittent, its reference pair is cross-population, and the one direct dataset says hands are *cleanest* right after the toilet

**Register rows fed / supersession.** Feeds the register row for
`HAND_LOAD_LOG10_GEC` / `HAND_LOAD_REFERENCE_PEAK_LOG10`
(`engines/infection_dynamics_bridge.py`), the open ledger's §4 items 22–23, and
the event-mode declaration `stool_events_per_day` consumed by
`TransmissionCore._replenish_hand`. It **supersedes two recorded retrieval
states** in tranche 26 and tranche 39 — see §2 — and **moves no constant and
adopts none**.

**Status:** Evidence assembled and interpreted. Nothing implemented.

**Scope.** The question left open by tranche 39: if the hand route should carry
a *per-event* load rather than a routine one, what does the literature measure
about (a) how often a shedding host's hand carries anything at all, (b) how
large the load is when it does, (c) what the event is, and (d) whether the
amplitude distribution is heavy-tailed.

**Result in one line.** The direct norovirus dataset was opened in full for the
first time (E2 route switch, PMC HTML), and it does not describe a hand held at
a ceiling: **18/71 (25.4%)** of infected-subject rinses carried detectable
virus at a limit of **2.15 log10 GEC per rinse**, two of six infected subjects
never carried any, and per-subject means span **3.30–4.45 log10**. The same
paper contradicts the engine's current event trigger: rinses taken
**immediately after bathroom use** were *lower* and *less often positive*
(12.4%, mean 2.30 log10) than rinses taken at routine vital-sign checks
(37.5%, mean 3.32 log10, **P < 0.05**). And its Table 3 pairs each subject's
**stool titre with that subject's hand load**, which tranche 26 recorded as a
∅ null and tranche 39 carried forward — that null is **overturned**, and the
within-study pairing puts the bridge 2.7–3.6 logs **above** the shipped
`−7.14`.

---

## 1. E0 triage — what would settle "heavy-tailed, not routine"

| Question | Unit that would settle it | Retrieved? |
|---|---|---|
| How often is a shedding host's hand contaminated at all? | positive fraction of rinses, with a stated LOD | **Yes** — Liu 2013, §2 |
| How large is the load when positive? | log10 gc/hand, with a spread | **Yes, partially** — per-subject means only, §2 |
| Is the event defecation? | load conditioned on time since stool | **Yes, and against the model** — §3 |
| How much does one host's hand load vary in hours? | paired serial rinses, log10 difference | **Yes** — Ram 2011, §4 |
| Which activities raise it, and by how much? | log10 increment per activity | **Yes** — Pickering 2011, §4 |
| Is the amplitude distribution Pareto / power-law? | fitted tail index | **∅ / `?nr-term`** — §6 |
| Mass of faeces per release event | g/event | **Bounded only** — §5 |

## 2. The direct dataset, opened — Liu 2013 in full

Liu, Escudero-Abarca, Jaykus et al. 2013, *Appl Environ Microbiol* 79:7875,
[10.1128/AEM.02576-13](https://doi.org/10.1128/aem.02576-13). Six
experimentally infected GI.1 (Norwalk) secretor-positive adults and six
uninfected controls, 159 hand rinses, Emory University Hospital. Retrieval:
Consensus chunks returned the abstract only across three phrasings; the full
text was opened at **PMC3837815** (route switch, not rephrasing). Origins below
are **R** (Results) and **T3** (Table 3) unless marked.

| Quantity | Value | Origin |
|---|---|---|
| Positive fraction, infected subjects | **18/71 (25.4%)** | R |
| Combined-method limit of detection | **≈1.4 × 10² (2.15 log10) GEC per 50 mL rinse** | R |
| Mean load among positives | **3.86 log10 GEC/hand**, **range of subject means 3.30–4.45** | R |
| Per-subject positive rate | 12/22 (54.5%), 2/8, 2/8, 2/12, **0/12**, **0/9** | T3 |
| Per-subject **max stool titre** | **8.3, 8.1, 7.4, 7.5, 7.4, 8.2 log10/g** | T3 |
| Uninfected subject 42 | 2/88 (2.3%) positive, mean **2.81 log10** — significantly lower (P < 0.05) | R |
| Infected subjects with any positive hand | **4/6 (66.7%)**, all symptomatic and shedding on the sampling day | R |

Two recorded states change:

1. **Tranche 39's register note "the distribution behind the mean is `?nr`" is
   closed.** The distribution is a **censored mixture**: ~75% of rinses from
   symptomatic, stool-positive hosts are below a 2.15 log10 detection limit,
   and the positives cluster within ~1.1 log10 of each other. The published
   3.86 is a **mean over the positive quarter**, not a load a shedding host
   carries.
2. **Tranche 26's null "no study measures stool titre and hand load in the same
   subjects" is overturned.** Table 3 carries both, per subject. It is a weaker
   pairing than the null implied — *maximum* stool titre against the *mean of
   that subject's positive* hand rinses, not simultaneous samples — so it
   bounds rather than measures. It should be recorded as **retrieved and
   partial**, never as absent.

### What the within-study pairing does to the bridge

The engine reads Liu's load against the shipped curve peak of **11.0 log10/g**,
which comes from a different population, so the implied bridge is
`3.86 − 11.0 = −7.14 log10 g/hand`. Read against **Liu's own subjects' stool
titres**, the same arithmetic gives:

```text
3.86 − (7.4 … 8.3) = −3.5 … −4.4 log10 g/hand
```

i.e. **2.7 to 3.6 logs above the shipped convention**, and at the **top** edge
of tranche 39's independent indicator envelope (`10^-6.9 … 10^-4.1 g/hand`),
which was derived from E. coli per hand over E. coli per gram of stool with no
reference to this paper. Two independent routes now bracket the same quantity
and both sit **above** `−7.14`.

This is a **bound and a provenance finding, not a replacement**: the pairing is
max-versus-mean, the subjects are GI.1 challenge volunteers rather than a GII
cruise population, and the engine's 11.0 peak is a separate row with its own
sourcing. It also must not be read as an instruction to raise the hand load:
the occupancy correction in §3 pushes the *time-averaged* load the other way,
and the two have to be resolved together or not at all.

## 3. The event is not the one the engine models

`TransmissionCore._replenish_hand`'s event mode returns the hand to the Liu
ceiling **at a defecation event** and decays between events. Liu 2013 measured
exactly that contrast and found the opposite sign:

| Sample type | Positive | Mean load | Note |
|---|---|---|---|
| Routine vital-sign checks | **6/16 (37.5%)** | **3.32 log10** | highest of the three |
| **Immediately after bathroom use** | **11/89 (12.4%)** | **2.30 log10** | **P < 0.05 lower** on both, vs. vital-sign |
| Collection context not recorded | 10/40 (25%) | 2.46 log10 | not significantly different from either |

Read plainly: in the only controlled human dataset, a symptomatic norovirus
host's hands are **least** contaminated right after the toilet — consistent
with handwashing following defecation, and with contamination arriving at other
times by other contacts. The model's structure currently asserts the reverse.
That is a **structural finding about the trigger**, and it is independent of
any magnitude; the paper does not report what the subjects did between samples,
so *why* is `?nr`.

## 4. Amplitude is a state, not a host attribute

Two field studies measure the dispersion the user's heavy-tail hypothesis is
about, in faecal-indicator units rather than norovirus:

| Study | Measurement | Setting | Origin | Grade here |
|---|---|---|---|---|
| Ram et al. 2011, *Am J Trop Med Hyg*, [10.4269/ajtmh.2011.10-0299](https://doi.org/10.4269/ajtmh.2011.10-0299) | Serial hand rinses of the same 39 mothers hours apart: geometric mean faecal coliforms **307 → 3,001 CFU/100 mL** (P = 0.0006); **no correlation** between random and critical-time counts (R = 0.13, P = 0.43); mean absolute difference **3.5 log10 (SD 1.4)**, and **2.9 (SD 1.5) / 2.0 (SD 0.7)** for the second critical time. After supervised handwashing with soap, **all** participants had detectable faecal coliforms ~2 h later (GM 494 CFU/100 mL; E. coli quartiles 15/26/120, max 3,580) | Rural Bangladesh, mothers of young children | R, Discussion | C — indicator, wrong setting; **the dispersion, not the level, is what transfers** |
| Pickering et al. 2011, *Trop Med Int Health*, [10.1111/j.1365-3156.2010.02677.x](https://doi.org/10.1111/j.1365-3156.2010.02677.x) | Activity-conditioned **increments**: geometric-mean increases from **50 (cleaning dishes) to 6,310 (food preparation) CFU per two hands**; toilet use, cleaning a child's faeces, sweeping, dishes, food preparation all raise indicators; **bathing lowers** them; time since handwashing with soap raises them | 119 mothers, Dar es Salaam, household observation | Ab | C — indicator, wrong setting |
| Oie et al. (tranche 39) | **39,499 ± 77,768 CFU/glove** after defecation without a bidet; **4,147 ± 11,427** with one | Nursing students, Japan | Ab | C — total culturable units, no compatible denominator |

Together: a hand load is a **stateful, activity-driven quantity with ~2–3.5
log10 of within-person swing over hours**, whose *increment* depends on which
activity just happened and which is suppressed by washing. A single
per-host-per-epoch target of any value is the wrong shape, whatever the value
is; that conclusion does not depend on a number and cannot be tuned.

## 5. The rare-release mode — bounded per event, frequency only in pools

| Study | Measurement | Origin | Use here |
|---|---|---|---|
| Gerba 2000, *Quantitative Microbiology*, [10.1023/a:1010000230103](https://doi.org/10.1023/a:1010000230103) | Mean faecal material shed **per bather: 0.14 g**, *estimated* from bather faecal-coliform shedding, not weighed | Ab | Bound; derived, and a wash-off denominator, not a hand |
| Petterson et al. 2020, *Water Research*, [10.1016/j.watres.2020.116501](https://doi.org/10.1016/j.watres.2020.116501) | Faecal excretion per bathing event modelled as a **triangular reference distribution: 0.06 / 0.6 / 6 g**, explicitly chosen because data are lacking (WHO 2016 reference-distribution convention); accidental release modelled as **10¹² norovirus** in one event | R, Methods | **Declared, not measured** — it is another model's declaration and may not be adopted as evidence |
| Chalmers et al. 2021, *Water*, [10.3390/w13111503](https://doi.org/10.3390/w13111503) | Probability that **a bather contaminates the pool: 1 in 1,000 to worse than 1 in 10,000**, from oocyst occurrence in six UK leisure pools; on high-load days multiple events per day more likely than single events | Ab, R | An **event frequency on a per-person-visit denominator** — the only retrieved rare-event rate |

So the rare mode has a *frequency* (order 10⁻³–10⁻⁴ per person-event, pool
setting) and a per-event *mass* that is bounded at ~0.06–6 g only by a declared
reference distribution. Neither is a cruise measurement, and the mass figure is
a modelling convention — recording it as evidence would repeat exactly the
error tranche 39 avoided with the indicator envelope.

## 6. What distribution the evidence licenses — and what it does not

Supported by retrieved measurement:

- **Intermittency.** A Bernoulli occupancy of roughly a quarter among
  symptomatic, stool-positive hosts, at a stated LOD (Liu 2013). Continuous
  occupancy at the ceiling — the engine's non-event mode — is refuted for this
  pathogen in this setting.
- **Multi-log amplitude dispersion on a log scale.** Within-person differences
  of 2.0–3.5 log10 with SD 1.4–1.5 (Ram 2011); activity increments spanning
  ~2.1 log10 (Pickering 2011); an event-level SD ≈ 2× the mean on the raw scale
  (Oie).
- **Suppression terms that are measured**: bathing and handwashing lower the
  load (Pickering, Ram, Liu's post-bathroom samples), a bidet lowers the
  post-defecation load ~10× (Oie).

**Not supported:** no retrieved source fits a **power-law or generalized-Pareto
tail** to faecal contamination amplitude, reports a **tail index**, or
publishes the **raw per-event observations** needed to fit one. Records:
`?nr-term` for a fitted tail index after E1×3 and E2×2 (route switch to PMC for
Liu; the pool literature reports means and reference distributions only).

The honest statement of the user's hypothesis is therefore: the evidence
supports **intermittent, lognormal-scale dispersion with measured suppression
terms, plus a separate rare release mode of order 10⁻³–10⁻⁴ per person-event**
— *not* a fitted heavy tail. A lognormal with the measured σ ≈ 1.4–1.5 log10
and a ~25% occupancy is already far more dispersed than the shipped fixed
target; adopting a Pareto on top of that would be a declaration, and would have
to be labelled one.

## 7. Unresolved after this pass

- **∅** Raw per-event amplitude observations (any faecal indicator, any
  setting) sufficient to fit a distribution rather than a mean and SD.
- **∅** Norovirus hand load in a GII-infected host, in any setting.
- **∅** Hand load in a cruise population, symptomatic or not.
- **`?nr`** What Liu's subjects did between samples (handwashing frequency,
  compliance) — the paper reports sample context, not behaviour.
- **`?nr`** Whether the ~75% of below-LOD rinses are truly zero or between zero
  and 2.15 log10; the paper reports censoring, not a censored-data fit.
- **∅** Any measurement relating hand load to a *subsequent* surface, food or
  mouth deposit in the same subjects — the propagation question.
- **∅** Continuous background deposition onto seating (tranche 38's chair
  null stands).

## 8. What this does and does not authorise

It authorises nothing in the engine. Specifically:

- No constant moves. `HAND_LOAD_LOG10_GEC`, `HAND_LOAD_REFERENCE_PEAK_LOG10`,
  `environmental_faecal_release_log10_g_per_epoch`, the dose-response and the
  posting threshold are all untouched by this tranche.
- The `−3.5 … −4.4` within-study bridge is **not** adopted, and must not be
  read as "the hand load should be raised": §2's occupancy correction acts in
  the opposite direction on the time-average, and the two are one design
  question.
- The finding that the post-defecation trigger has the wrong sign is a
  **structural** result about `_replenish_hand`, not a licence to retime it by
  whatever improves A9. A9 is above target; every correction here has a
  determinate sign that was fixed before the anchor was looked at, and two of
  the three point the wrong way for the anchor.
