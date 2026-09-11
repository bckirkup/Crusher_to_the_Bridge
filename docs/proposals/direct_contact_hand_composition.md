# The direct-contact route has no physical composition, and it carries 99.7% of the delivered dose

Status: **proposed**. Nothing here is implemented. No constant is adopted,
narrowed, widened or proposed for a fit. The diagnosis in §1–§4 is arithmetic on
shipped constants plus a cross-check against an existing measurement
(`dose_concentration_findings.md`); the repair in §5 is a structural change
requiring an explicit decision before it is built, per
`patchiness_program_brief.md`.

## 1. What the route actually computes

`_pathway_direct_contact` → `_per_partner_contact_dose` sums, over the partners
a susceptible actually contacts, each partner's **whole-body per-epoch faecal
emission** as returned by `get_pathogen_shedding`, then multiplies by the
confinement/zone/exposure factors and, in `_apply_route_efficiencies`, by
`route_efficiency_multipliers["direct_contact"] = 0.35`.

That is the entire composition. Between a shedder's gut and a contact's gut
there is no hand reservoir, no per-contact transfer fraction, no hand-to-mouth
step, and no conservation: every sampled partner receives the donor's full
per-epoch emission independently in the same epoch.

The quantity `0.35` therefore stands for "the fraction of everything a host
sheds in an hour that is ingested by one person it touches".
[Tranche 12](../literature/consensus_tranche_12_contact_transfer.md) §6.3, §6.4
and §10 already searched for that quantity twice, unfiltered, and returned two
explicit nulls: no norovirus or norovirus-surrogate person-to-person transfer
measurement exists, and nothing in the literature measures the field's
denominator. It survived the C5 retirement (#22) as the route's single owner —
but what it owns is a convention, not a measurement.

Every other enteric route in the engine is composed from measured steps. The
fomite route runs faecal deposition → surface → hand (directional, moisture-
resolved transfer, tranche 12 §1–§4) → `_hand_to_mouth_dose`. The model even
maintains a fully specified donor hand reservoir —
`hand_load_by_pathogen`, replenished to the Liu ceiling at stool events,
decayed at a measured inactivation rate, and reduced by hygiene events — and
**the direct-contact pathway never reads it.**

## 2. The route overdelivers by a factor that does not depend on anything

For one host at shedding-curve index `c`, the two quantities the engine
computes from the same illness are

```
hand reservoir (Liu):   H(c) = 10^3.86 · 10^(c − 11.0)          gc per hand
direct dose per contact: D(c) = 0.35 · 10^(c − 4.0) / 24         gc ingested
D(c) / H(c) = 0.35 · 10^(7.14 − 4.0) / 24 = 20.1
```

The ratio is **independent of `c`**: at every point of every illness, one close
contact ingests about twenty times the entire virus population present on the
shedder's hands, and each further partner in the same epoch ingests the same
amount again. At the curve peak that is 1.46e5 gc ingested against a 7.24e3 gc
reservoir.

## 3. How far off the level is

Composing the same contact through the reservoir the model already maintains —
donor hand → recipient hand at the measured wet-deposit transfer fraction →
`_hand_to_mouth_dose` (`MOUTH_CONTACT_FRACTION_RANGE` × `HAND_TO_MOUTH_NORMAL`,
midpoint 3.39e-3 per contact) — gives:

| donor→recipient hand transfer | composed / shipped | logs below shipped |
|---|---:|---:|
| 0.30 (Sharps wet, upper) | 5.1e-5 | 4.30 |
| 0.13 (Tuladhar finger→steel, wet) | 2.2e-5 | 4.66 |
| 0.01 (dried) | 1.7e-6 | 5.77 |

**Independent cross-check.** `dose_concentration_findings.md` §5 measured the
realised per-draw `sD` medians on an instrumented voyage: direct contact
9.9e-6, fomite 1.3e-10 — a gap of **4.88 logs** between the unsourced route and
the sourced chain for the same hosts on the same voyage. The closed-form
prediction above is 4.66 logs. Two independent derivations agree to 0.2 log.

In per-contact infection probability (`1 − (1 + D/32.81)^−0.111`, shipped
Teunis coefficients):

| | shipped | composed (t = 0.13) |
|---|---:|---:|
| peak shedder, one close contact | **0.61** | 0.010 |
| curve index 10 | 0.35 (index 9) | 0.0011 |

0.61 per contact is certainty within a day of cabin sharing. 0.010 at peak
falling to 1e-3 mid-illness is the order that accumulates to a realistic
household/cabin secondary attack rate over an illness, and it is where the
dose-response is informative rather than saturated.

## 4. This is a sufficient explanation for the record

- Direct contact carries **9.40e6 of 9.43e6** total effective dose (99.7%); the
  sourced fomite chain carries 0.24% (`dose_concentration_findings.md` §3).
  The model is, in effect, a single-route model driven by its one unsourced
  route.
- That route spends 97% of its own potential — 95 establishments where the same
  mass spread flat would give 2,840 — and 98.7% of delivered dose lands on
  hosts already certain to be infected (§2, §4 of that document).
- Transmission is a sequence of **isolated near-certainties** (60 draws at
  `sD ≥ 1` in 59 distinct `(epoch, zone)` cells) because near-certainty is
  reached by a *single* partner contact. The coincidence structure the previous
  session went looking for is not missing so much as unnecessary: nothing needs
  to coincide when one handshake is sufficient.
- Every mean-field and mean-preserving-dispersion arm returned null because the
  one curved channel is 3 logs past saturation. Dispersion cannot act there.
- **Too many expedition voyages post.** Any voyage with a boarding case and
  ordinary contact rates establishes near-certainly per contact, so posting is a
  near-ceiling rather than a rate. A9 cannot be tested against a ceiling.
- **The symptomatic/asymptomatic R ratio must sit at 1.0** (§3 of the ledger
  predicted this): symptom state reaches `transmission_core` only through the
  emesis path, and 99.7% of dose flows through a route that is per-copy
  identical for a carrier and an ill case.

## 5. Why the release sweep could never find a good regime

`environmental_release_log10_per_day` is the normaliser for *every* route at
once. Person-to-person dose and environmental reservoir mass are tied to one
scalar, so there is no value that makes a handshake plausible while leaving the
environment loaded: at `adj = 4` contact is a firehose, and by `adj = 8` the
whole exposure stream is linear to four decimal places and nothing transmits at
all. The equivalent `adj` at which the shipped direct route would deliver the
hand-composed dose is **8.66** — past the far edge of the transmitting arm.

That is the "switch, not a gradient" finding (#497, ledger item 00) in full: the
sweep is a one-dimensional slice through a two-dimensional problem, and the two
dimensions are currently the same number. Decoupling them is the point of the
repair, not a side effect.

## 6. Proposed repair — DIRECT-HAND-01 (not built; requires a decision)

Compose the direct-contact pathway from the donor's hand reservoir instead of
its whole-body emission:

```
per contact:  delivered = donor_hand_load · transfer(donor→recipient hand)
              donor_hand_load -= delivered          # conservation across partners
              recipient_hand_load += delivered
              ingested = _hand_to_mouth_dose(recipient, epoch, recipient_hand_load)
```

Then retire `route_efficiency_multipliers["direct_contact"]` for this pathogen
by the same argument that retired `contact_transfer_fraction`: with a composed
chain in place the multiplier is a second scalar in the same position of the
same product, and the route must keep one owner. The surviving owner becomes a
chain of measured steps rather than a knob.

**What is sourced and what is not.** The reservoir is Grade A for ill cases
(Liu). `_hand_to_mouth_dose` and its two factors are already sourced. The
donor→recipient hand transfer step is a **declared analogy**: tranche 12 §6.3 is
an explicit null for person-to-person, so the value must come from the
directional wet-deposit hand↔surface measurements with skin as the recipient
surface, graded B/C, with the interval frozen and dated *before* any run. It may
not be chosen inside that interval by what helps A9.

**The normaliser this makes load-bearing.** Once person-to-person dose runs
through the hand, the `HAND_LOAD_LOG10_GEC = 3.86` against
`HAND_LOAD_REFERENCE_PEAK_LOG10 = 11.0` bridge — the unsourced −7.14 log10 g
convention, ledger items 22(f) and 23, itself a literature null — becomes the
single scale controlling all person-mediated transmission. That is a real
exposure and it must be declared as one, not hidden by the repair. It is also
an improvement on the present state, in which the same role is played by a
convention with *two* unsourced factors and no reservoir at all.

## 7. Falsifiable predictions, to be recorded before the arm runs

None of these is a target and none may be used to choose a value:

1. Per-contact direct dose falls 4.3–5.8 logs; curvature utilisation rises from
   0.013 toward the informative band.
2. Posting frequency falls by orders of magnitude, with most voyages fizzling
   and an explosive tail surviving — the offspring distribution gains dispersion
   it currently cannot have.
3. The realised symptomatic/asymptomatic R ratio moves off 1.0 toward Sukhrie's
   0.52 **without any constant being set to it**, because hand load is
   replenished at stool events whose rate is diarrhoea-conditioned.
4. The `adj` regime switch at 6–7 disappears, because `adj` no longer scales
   person-to-person dose.
5. Mean-preserving dispersion arms that returned null (zone sigma, hand point
   process, release tail index) become live, because the stream leaves
   saturation.

If (2) overshoots — if the composed model cannot post at all — that is a result
and it is reported, not rescued by widening the transfer interval. It would say
the remaining gap is in the hand bridge of §6 or in the food/environmental
routes, and it would say so on a scale where the question is answerable.
