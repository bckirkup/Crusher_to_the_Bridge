# Sourcing protocol: interval-first evidence, terminal states, and stopping rules

> **Status:** Living — process of record; no sourcing pass has run under it yet.

All six decisions in proposal §9 were approved on 2026-09-04. Decision 6 is
front-loading: one anchor-harness perturbation pass before any query spend.

## 0. What is wrong with both of the approaches we have tried

The fan-out declared blockage too early and recorded it as fact: "the binding
constraint is full-text access" was wrong, and it converted an unattempted route
into a documented conclusion. The re-verification pass went the other way: it
spent about half its queries re-attacking rows that were never going to close by
rephrasing, because nothing in the process could say *this row is finished*. A
`?nr` row is currently always eligible for one more query, which is Zeno's
staircase — every pass re-litigates the same eighteen rows and each one closes a
smaller fraction.

Neither failure is a budget problem. 118 queries to close six rows is fine. The
problem is that the process had no definition of *closed*, no definition of
*finished-without-closing*, and no rule about which rows deserve the next query.

## 1. The unit of work is the parameter, and the deliverable is an interval and shape

Today a row is treated as closed when a point value is verified against a
paper. That is the wrong target, because it is not what the model needs and it
is not what the evidence usually supports.

What the model needs is: **a believable interval and plausible shape per
parameter, and a fit that lands inside every one of them while the output lands
inside the observation window.** So a closed row delivers four things, not one:

| Field | Meaning |
|---|---|
| **Interval** | The bounds the evidence actually supports for *this quantity in this setting*, with the basis stated (measured range, pooled CI, across-study spread, declared bound) |
| **Shape** | The distributional form the evidence supports over those bounds — whether a sweep or a draw should be uniform over the range or concentrated near a central value |
| **Origin** | Axis 3, unchanged; use the vocabulary in [the register's §1](parameter_provenance_register.md#1-three-axes-because-each-was-hiding-what-the-others-could-not-say) |
| **Grade** | A/B/C, unchanged, and still independent of origin |

The shipped point value remains whatever the model runs; the interval and shape
are what make a later fit legitimate or illegitimate. This is not new
machinery — it is what `cleaning_schedule_sweep_spec.md` already does for
cleaning frequency and coverage, generalised to every row.

## 2. Two stopping rules, and they point in opposite directions

**S1 — the floor. Stop narrowing when the fit stops caring.** A row is closed
once its interval is narrow enough that further precision cannot change whether
the joint fit reaches the observation window. Chasing a row past that point buys
nothing and costs the queries the next pass needs.

**S2 — the ceiling. Never record an interval narrower than the evidence
supports.** Manufactured precision — one study's CI recorded as the parameter's
range, a midpoint pinned as a point, an interval inherited from a paper that
measured a different denominator — narrows the feasible box for free. It is the
mechanism by which the box goes empty, and an empty box from over-narrowing is
indistinguishable from an empty box caused by a wrong mechanism. When the
evidence is wide, the honest width *is* the result. Never record an interval
narrower than the evidence supports: manufactured precision is what makes the
feasible box go empty, and an empty box from over-narrowing cannot be told apart
from an empty box caused by a wrong mechanism.

Sourcing therefore runs to the width where S1 and S2 meet, and no further in
either direction.

## 3. Which rows get the queries: leverage first

Before any query is spent, every open row is assigned a leverage class by
one-at-a-time perturbation across its current interval, using the harness we
already have (`telemetry_buffer/observation_model/score_anchors.py` for the
anchors, the sweep specs for bounded knobs):

| Class | Test | Budget |
|---|---|---|
| **L2** | Moving the parameter across its interval changes whether an anchor verdict passes | full ladder, §4 |
| **L1** | Moves an anchor measurably but does not flip a verdict | E0–E2 only |
| **L0** | No detectable movement in any scored output across the whole interval | **zero queries**, recorded as L0 |

An L0 row is not a failure and does not need sourcing to be defensible — it
needs to be *declared* L0, with the perturbation that showed it. This is the
single largest saving available: the last pass spent its queries in register
order, which is uncorrelated with leverage.

## 4. Escalation ladder, with a cap per tier

| Tier | Action | Cap |
|---|---|---|
| **E0** | Triage, zero queries: is the quantity expressible in the field, measurable in principle, and commensurable with what assays report? Terminal classes in §5 are decided here, before any retrieval | 0 |
| **E1** | Consensus chunks, quantity **and** unit named, ≥2 differently-phrased attempts | 3 |
| **E2** | **Route switch**, not rephrasing: name the table or figure; Europe PMC JATS XML for any open-access record; publisher HTML; agency full text for MMWR-class documents | 2 |
| **E3** | Identity resolution — wrong author/year/paper is a distinct failure from wrong query | 2 |
| **E4** | Stop and escalate to you | — |

Seven queries per row, ceiling. The Kirby row is the worked case for why E2 is
a separate tier and must be reached before a `?nr` is recorded: three phrasings
all truncated Table 3 at the row we did not need, and the route switch resolved
it in one attempt. **Rephrasing after E1 is exhausted is the specific behaviour
this ladder exists to forbid.**

## 5. Terminal states: how a row stops being eligible for another query

| State | Meaning | Reopened only by |
|---|---|---|
| **closed** | Interval + shape + origin + grade recorded | New evidence that moves the interval or changes the supported shape |
| **L0** | No leverage on any scored output | A model change that gives it leverage |
| **∅def** | Unmeasurable by definition — the denominator is one no assay uses (contact transfer per unit emission) | A model change to the quantity's definition |
| **∅comm** | Commensurability null — the two sides are never measured in the same subjects (copies/g stool vs copies/m³ air) | A study measuring both |
| **∅lit** | Searched; no measurement of this quantity exists (high-touch area per cabin in m²) | A new publication |
| **Tr-class** | Not a journal article at all — VSP posting archive, DHS/industry report | Nothing; it is already at its best available origin |
| **?nr-term** | Ladder exhausted through E3 without retrieval | A **new route** or a new paper — never a new phrasing |

The last row is the load-bearing one. `?nr-term` keeps the epistemic meaning of
`?nr` (this route did not retrieve it; not absence from the paper, not absence
from the literature) while removing its standing invitation to try again. Every
reopening is recorded with *what new information* triggered it, which is what
makes the sequence of passes converge instead of oscillating.

## 6. Pass-level stopping rule

A wave ends, and the pass reports, when either holds:

- **marginal yield floor** — fewer than one row closed or terminated per 15
  queries across the wave; or
- **leverage exhaustion** — every remaining open row is L0 or L1.

A row that has hit E4 in two different passes is not queried a third time; it is
promoted to a decision for you, with the options written out. That is the
anti-asymptote rule: repeated failure escalates in *kind*, never in volume.

## 7. What "we are good" means on the fit side

1. **Freeze the box.** The intervals are dated and frozen before the fit runs.
2. **Fit inside the box.** The joint fit may move any parameter within its
   interval. This is not tuning-to-target: the interval was set from evidence,
   independently, before the fit, and that is exactly the condition
   `model-parameter-provenance` requires.
3. **Accept** iff the output lands in the observation window **and** every
   parameter sits inside its own interval.
4. **A parameter pinned at an interval boundary is a flag, not a pass.** It
   means the fit wanted to leave the box, and the boundary is doing work
   evidence should be doing.
5. **An empty box is a mechanism finding.** Run the archetype check first — a
   well-mixed pool standing in for a small number of concentrated events has
   caused this five times. Widening an interval to rescue a fit is forbidden;
   widening requires new evidence and a register entry, and never a fit failure
   as its justification.
6. **The count of parameters fitted rather than sourced stays visible**, as does
   the count sitting at a boundary. One knob absorbing several mechanism errors
   is the defect this whole discipline exists to prevent.
