# Morris screen over the norovirus box: what the scored outputs actually move on

Status: measurement, 2026-09-01. Design:
`docs/proposals/bounded_sensitivity_and_admissible_region_spec.md` §2. Harness:
`telemetry_buffer/observation_model/bounded_screen.py`. Raw output:
`telemetry_buffer/observation_model/bounded_screen_norovirus.json` and
`bounded_screen_floor.json`.

Nothing here selects a parameter value. The screen ranks factors; §6 of the
design forbids writing an admissible range back into a profile, and this
document does not.

**Superseded box, 2026-09-02.** These results were produced with
`surface_decay_per_day` swept over [0.10, 0.60].
[`../literature/consensus_tranche_5.md`](../literature/consensus_tranche_5.md)
§1 recut that interval to [0.14, 0.84] on the surrogate literature. Morris
elementary effects are differences taken across the whole box, so recutting one
interval changes the effects of **every** factor, not just that one: the ranking
below must be re-run before the admissible-region search and must not be patched
factor-by-factor. The measurement stands as a measurement of the old box.

## 1. What was run

400 simulations: 10 Morris trajectories over the 7-factor norovirus box of
design §3.2, 8 design points per trajectory, 5 seeds per point — **the same
five seeds (500–504) at every point**, so each elementary effect differences
two matched-seed means. 168 epochs, 450 agents, `norwalk_gi` from
`active_profiles`. 4 h 11 min wall clock.

The noise floor is 20 further runs at the box centre.

## 2. The floor, and the threshold derived from it

| Output | Single-run SD, 20 seeds | Threshold (SD/√5) |
|---|---|---|
| `attack_rate` | 0.01572 | 0.00703 |
| `ever_ill_attack_rate_passenger` | 0.00492 | 0.00220 |
| `reported_case_attack_rate_passenger` | 0.00429 | 0.00192 |
| `reported_case_attack_rate_crew` | 0.01867 | 0.00835 |
| `peak_epoch` | 62.08 | 27.77 |
| `vsp_posted` | 0.0 | — see §5 |

The elementary effect differences two 5-seed means, so the single-run SD is not
the right comparison — SD/√5 is. That threshold is an **upper bound** on the
true one: common random numbers make the two means positively correlated and
subtract a non-negative amount of shared variance, and that correlation was not
measured. A factor above the threshold is therefore above it conservatively; a
factor below it is *indistinguishable from stochastic noise at this design
size*, which is not the same claim as insensitive and does not license freezing
it.

## 3. The ranking

Three factors clear the threshold on all three passenger and whole-ship
outputs, in the same order every time:

| Rank | Factor | μ\* on `ever_ill_attack_rate_passenger` | Ratio to threshold | Sign |
|---|---|---|---|---|
| 1 | `innate_nonsusceptible_fraction` | 0.00730 | 3.3 | − |
| 2 | `emesis_titre_gec_per_ml` | 0.00466 | 2.1 | + |
| 3 | `environmental_faecal_release_log10_g_per_epoch` | 0.00390 | 1.8 | − |

Below threshold on **all four** attack-rate outputs:
`contact_transfer_fraction` (ratio 0.39–0.49) and `emesis_volume_ml_high`
(0.26–0.32). `emesis_volume_ml_high` is the only factor that moved nothing
above threshold anywhere.

`surface_decay_per_day` and `shedding_variance_log10` clear the threshold on
whole-ship `attack_rate` (ratios 1.09 and 1.18), and `shedding_variance_log10`
additionally on the crew reported-case channel (§4). Both fall below it on the
two passenger channels.

Three consequences, and none of them is what the provenance backlog assumed.

**The top-ranked factor is the one whose target we just withdrew.**
`innate_nonsusceptible_fraction` leads every passenger channel, and this screen
swept it over the 0.00–0.16 interval the open ledger carried at the time. Tranche
2 argued that box was too narrow because the arm is GI.1; **tranche 3 withdrew
that argument** — the profile declares itself GII in its `name`, `genotypes` and
`incubation.notes`, so the GII partial-susceptibility ceiling of ≈0.16 governs
and **the box swept here was the right one**
([`../literature/consensus_tranche_3.md`](../literature/consensus_tranche_3.md)
§1). The μ* values below are therefore measurements over the governing interval,
not lower bounds over a narrowed one. What remains unsettled is the *mechanism*:
a fully removed fraction is the wrong shape for partial GII susceptibility, so
the factor this screen ranks first is still the one whose provenance is least
settled — top of the queue on consequence rather than on how easy the citation
is.

**`contact_transfer_fraction` is not worth the sourcing effort it was queued
for.** Task #22 exists because the shipped 1.0 sits against a ~0.25 literature
anchor. Over the whole sourced 0.06–0.50 interval the factor moves no scored
output above the noise floor — ratio 0.39 at best, and identically zero on the
crew reported-case channel. The value should still be corrected, because a
wrong value is wrong, but it is not an exposure and it should not be ahead of
anything.

**The inert dose knob is not inert across the box.**
`environmental_faecal_release_log10_g_per_epoch` ranks third on both passenger
channels. That does not contradict the earlier finding that dose 10 → 24 was
byte-identical: the Morris steps of δ = 2/3 over 4–24 cross the low end of the
interval, where faecal release is still numerically comparable to the emesis
pool, so the factor is live below roughly 8 and dead above it. A screen over
the interval sees the live part; a two-point probe at 10 and 24 sees only the
dead part. Both are correct, and the knob remains unusable as a calibration
axis for exactly the reason recorded in the freedom audit.

## 4. Where the channels disagree

The crew reported-case channel ranks differently: `emesis_titre_gec_per_ml`
first (μ\* 0.01455, ratio 1.74), `shedding_variance_log10` second (1.13), and
`innate_nonsusceptible_fraction` *below* threshold (0.72). A parameter that
dominates the passenger channels does not dominate the crew one. Any single
scalar summary of "sensitivity" would have hidden this, and it bears on A5,
which is a passenger/crew comparison.

Two rows are non-monotone across the box — `surface_decay_per_day` on
`attack_rate` (μ\* 0.0077 against μ 0.0010) and the faecal-release factor on
`peak_epoch` — with σ exceeding μ\* in both cases. Everywhere else
μ ≈ ±μ\*, i.e. monotone within the box.

`peak_epoch` is noise-dominated (threshold 27.8 epochs on a 168-epoch horizon,
σ ≥ 20 everywhere) and is diagnostic only; it is not an anchor.

## 5. Posting fires, but only in a thin part of the box

`vsp_posted` never fired at the box centre — 0 of 20 floor runs — nor at either
corner probed. It does fire inside the box: μ\* between 0.03 and 0.09 across
six of the seven factors, with physically coherent signs (non-susceptibility,
surface decay and faecal release push posting down; titre, transfer fraction
and shedding heterogeneity push it up).

The honest reading is not "the expedition hull never posts" but **posting is
reachable only in a thin part of the sourced box**, and this design cannot
resolve how thin. σ ≈ 2–3 × μ\* on every row, so each μ\* is carried by one or
two trajectory steps out of ten; with 5 seeds the smallest resolvable seed-mean
difference is 0.2, so the statistic is coarsely quantised. The SD/√5 threshold
is structurally 0 for a Bernoulli output whose centre rate is 0 and cannot
discriminate. **A binary anchor needs a different treatment than the continuous
ones — more seeds per point, or a sign test over the trajectory steps — and
this document does not claim a ranking for it.**

## 6. Cost, and why the other classes are not screened here

Measured at the box centre, three runs each: 35.7 s at 450 agents, 207 s at
1900, 694 s at 5000 — roughly quadratic in complement. A full 400-run design
would be about 23 h at 1900 and 77 h at 5000 on two cores.

A caveat that must not be lost: those larger runs varied the agent count only
and left the platform at `mega_cruise_5000`, so they are 1900 and 5000 agents
on the *mega hull*, not the `classic_cruise_1900` and `mega_cruise_5000`
layouts. A per-class screen has to move the platform id with the complement,
and these timings will not transfer to it.

One observation from those runs that is worth an explanation before it is
relied upon: at the fixed box centre, attack rate *falls* as the complement
grows on the same hull — 0.0067 at 450, ~0.0038 at 1900, ~0.0015 at 5000. A
fixed per-capita hazard would not do that. It is consistent with dilution
across a fixed set of zones rather than with a larger epidemic, and it is a
property of holding the hull constant while adding agents, which is not a
configuration any anchor uses.

## 7. What this changes in the queue

- `innate_nonsusceptible_fraction` (#21) moves to the front — top-ranked factor,
  known-wrong mechanism.
- `contact_transfer_fraction` (#22) drops — below floor across every scored
  output over its whole sourced interval.
- Emesis titre becomes a first-order provenance target, which it was not before.
- The faecal-release factor stays withdrawn as a calibration axis and is now
  documented as interval-dependent rather than simply inert.
- The admissible-region search (§2.3, task #37) runs over the three factors that
  clear the threshold, with the rest held at their sourced central estimates.
