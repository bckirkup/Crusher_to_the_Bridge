# #37 on the full box: the admissible region is empty, and three of the six anchors are why

Status: measurement, 2026-09-06. Design:
`../proposals/bounded_sensitivity_and_admissible_region_spec.md` §2.3, with the
deviations in §1 stated rather than assumed. Harness:
`../../telemetry_buffer/observation_model/admissible_region.py`. Raw output:
`../../telemetry_buffer/observation_model/admissible_region_37.json`, which
carries every point's factor coordinates, cell summary, verdicts and
measurements. The harness's `--stream` resume file is not committed: it is a
line-per-point subset of that same JSON.

Nothing here selects a parameter value. §2.3's own rule forbids writing a
marginal admissible range back into a profile, and the question is moot: there
were no admissible points to take a marginal range over. No interval was
widened, no anchor was dropped, and no constant was moved after the gate ran —
the plan's stop rule (§7) requires the binding constraint to be *reported*, and
that is what §3 does.

## 1. What was run, and where it departs from §2.3

640 simulations: 128 Sobol' points (scrambled, base-2, design seed 37) over the
**full six-factor box**, 5 matched seeds (500–504) per point, so every point is
the same five voyages under different parameters. 168 epochs, 450 agents,
`mega_cruise_5000`, `norwalk_gi` from `active_profiles`, other bundle pathogens
withdrawn at the boarding channel (`initiation.boarding.<pathogen>.enabled =
false`), pre-2020 era, no observation scenario override. 3 h 40 min wall clock
on two workers.

| Factor | Interval | Transform | Grade |
|---|---|---|---|
| `secretor_negative_relative_susceptibility` | 0.04 – 0.83 | linear | B |
| `emesis_total_shed_gec` | 3.6 × 10⁷ – 3.1 × 10⁸ | log10 | B |
| `hand_to_surface_drying_multiplier` | 0.008 – 1.0 | log10 | B |
| `surface_decay_log10_per_day` | 0.067 – 0.79 | linear | B |
| `shedding_variance_log10` | 0.5 – 1.5 | linear | C |
| `environmental_faecal_release_log10_g_per_epoch` | 4.0 – 24.0 | linear | D |

Four departures from the spec, each deliberate:

1. **The full box, not the screened subset.** §2.3 samples only factors that
   cleared #36's noise floor. #36 measured the retired one-index-case initial
   condition and is superseded on arrival by #54/#440
   ([`bounded_screen_isolated_36.md`](bounded_screen_isolated_36.md) §0), so its
   ranking licenses no restriction; and the one factor it did resolve is the
   box's only Grade D interval, so restricting to it would have made the gate a
   fit of the construction knob.
2. **2⁷ points, not 2¹⁰.** A wall-clock budget on two cores, not a claim that
   128 points sample the box as densely as 1,024. It bounds what §2 can say: a
   *nonempty* region could be missed by 128 points; an empty one is evidence
   about the anchors only as far as §3's arithmetic, which does not depend on
   the sample size, carries it.
3. **One hull, one era.** §2.3 asks for all four classes and both eras. The
   post-2020 arm needs the E/#10 configuration coordinates, which no shipped
   configuration carries, and mega/post has 3 postings — below the 10-posting
   floor — so it has no A4 target at all.
4. **A3 is not scored.** B1/#23 demoted it to a construction band. It is
   reported per point and kept out of the verdict; §3.3 is what it says.

**A9 is design-limited, and reported as such rather than waived.** Its target is
0.00419–0.00558 postings per eligible voyage, and a cell of five voyages can
only exhibit multiples of 0.2. The smallest cell in which one posting can land
inside the interval is 180 eligible voyages. A9 therefore cannot be passed or
failed at this design size; it is excluded from each point's verdict and still
tallied.

## 2. The result

**Empty. 0 of 128 points admissible; 128 inadmissible; none unscored.** The
admissible volume fraction is 0.0, and no point was admissible-pending-design.
The best point in the box passes **two** of the five scoreable anchors.

| Anchor | Target | Box span over 128 points | PASS | FAIL | misses low / high |
|---|---|---|---:|---:|---|
| A1 ever-ill AR, passengers | 0.10 – 0.22 | 0.0032 – 0.3228 | 8 | 120 | 118 / 2 |
| A2 ill / infected | 0.59 – 0.81 | 0.0389 – 0.6742 | 2 | 126 | 126 / 0 |
| A5 passenger/crew ratio | 2.5 – 4.5 | 0 – 10.12 (11 undefined) | 24 | 93 | 80 / 13 |
| A4 reported AR vs mega pre IQR | 0.0355 – 0.0749 | 0 – 0.3228 | 6 | 122 | 111 / 11 |
| A8 incidence /100k travel-days | pax 16.9 – 29.2; crew 5.2 – 16.0 | pax 63.4 – 4,385; crew 0 – 3,838 | 0 | 128 | 11 / 245 channels |
| A9 postings / eligible voyage | 0.00419 – 0.00558 | 0 – 1.0 | — design-limited — | | 10 / 118 |

Pairwise joint passes, which is what §2.3 asks for when the set is empty: **every
pair is zero except A5+A4, which two points satisfy together.** A1 and A2 never
pass together; A1 and A4 never pass together; A8 passes with nothing because it
never passes at all.

Unlike #36, this is not a design at the edge of extinction: **the take-off
fraction is 1.0 at all 128 points**, so the failures are the epidemics the box
produces, not the absence of one.

## 3. What the emptiness is about

The plan's §7 distinction — a missing mechanism, versus a wrong anchor, versus
insufficient coverage — resolves differently for each binding constraint, and
**two of the three bind for reasons that are not about the model at all.** This
result therefore does **not** license the conclusion that the literature-bounded
box is structurally infeasible.

### 3.1 A8 and A9 are unusable as mapped, not failed

A4 is the attack-rate distribution of the voyages VSP *posted*. A8 is incidence
over *all* travel-days. They read the same numerator. Divide A4's target by the
voyage length these runs actually have (5.19 days) and it lands at
**683–1,442 per 100,000 travel-days against A8's 16.9–29.2** — a factor of 23
apart. No parameter value can satisfy both in a cell of identically distributed
voyages; passing both requires a mixture in which posted voyages are as rare as
A9 says they are, which five replicate runs of one configuration cannot
represent. The gate computes this conflict and records it in its own output
(`a4_a8_definitional_conflict`).

That is an anchor-mapping and design-size defect, and it explains A8's clean
sweep independently: the quietest point in the box gives 63.4 per 100,000
passenger travel-days, still 2.2× above A8's ceiling, so **no point in this box
can pass A8** — but what a cell of five outbreak-capable voyages should be
compared against is not an unconditional fleet rate. A9 fails the same way for
the same reason, at a design size that cannot express its target.

**Consequence for the gate:** A8 and A9 must move to a design whose cell is a
*fleet* — enough eligible voyages, spanning outbreak and quiet ones, for an
unconditional rate to exist — before either can contribute a verdict. Until
then #37's verdict rests on A1, A2, A4 and A5.

### 3.2 A1 against A2 is the one genuinely structural tension

Both are within the box's reach individually (A1 8 passes, A2 2 passes) and
never together. The reason is visible in the ordering: ill/infected climbs with
epidemic size, because illness given infection is dose-dependent (Teunis η =
0.508, γ = 0.095), and the only points reaching A2's floor of 0.59 are at
**A1 ≈ 0.30–0.32, against A1's ceiling of 0.22**. Read the other way: over the 8
points where A1 *is* in band, ill/infected spans 0.413–0.544 and never reaches
A2's floor, short by a factor of 1.08. To make the literature's symptomatic
fraction, the model needs an epidemic about 1.4× larger than the literature's
attack rate allows.

This is the finding the gate exists to produce, and it is *not* repairable by
choosing a point: it is either a missing mechanism (something that makes
illness likelier per infection without making infection commoner — host factors,
dose distribution shape, or a dose-response family, which §2.2 leaves
categorical and unswept) or a wrong anchor pair. It is recorded, not resolved.

A5 sits the same way against A1: over the 24 points where the passenger/crew
ratio is in band, A1 never exceeds 0.073 — a third of its own floor — and the
ratio collapses toward 1 as the epidemic grows (0.996 at the largest A2).

### 3.3 A1 against A4 binds in the observation model, and A3 shows it

A4's band (reported, 0.0355–0.0749) lies **entirely below** A1's band (ever-ill,
0.10–0.22), so the two can only both hold if reported/ever-ill is roughly
0.16–0.75 — which is what A3, demoted to a construction band of 0.35–0.45 by
B1/#23, asserts. The shipped observation model does not deliver it: capture
**rises with epidemic size and saturates at 1.0**, and A3 lands out of band at
**123 of 128 points**. In exactly the region where A1 is in band, reported
equals ever-ill and A4 overshoots by the ratio of the two bands.

So the A1/A4 incompatibility is located in the observation process, not the
transmission box — the one place B2/#27 already declared the numbers are
assumed rather than sourced. That capture saturates rather than sitting in A3's
band is a defect of the observation model, and it is filed as one; it is not
grounds for widening either anchor.

## 4. What this licenses, and what it does not

- **Licensed:** the statement that no point of the sampled full box satisfies
  A1, A2, A4 and A5 simultaneously, with A1-vs-A2 and A1-vs-A4 as the binding
  pairs, and the A1-vs-A4 pair attributable to the observation model.
- **Not licensed:** "the model is structurally infeasible against the
  literature". Two of six required anchors never became evidence, one pair binds
  in an assumed observation process, and 128 points is 1/8 of the specified
  design.
- **Not done, and deliberately:** no interval widened, no endpoint selected, no
  anchor dropped, no constant refitted, and no nearest point reported as an
  admissible region.

Three follow-ups, in the order they change the verdict:

1. Re-map A8/A9 onto a fleet-scale cell (≥180 eligible voyages, outbreak and
   quiet), or withdraw them from the gate until such a design exists.
2. Fix the observation model's capture against A3's construction band, then
   re-read A4.
3. Only then is an A1/A2 infeasibility a statement about the structure — and at
   that point §2.2's categorical dose-response families are the first thing to
   vary, since they are the largest declared structural uncertainty in the box.
