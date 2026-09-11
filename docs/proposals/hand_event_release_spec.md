# HAND-EVENT-01 — the hand load as a marked point process, with its own out-of-sample check

> **Status: Proposed, except §5.** No mechanism in §3 exists in-tree, no
> constant is adopted, no interval is narrowed, no distribution is chosen for a
> shipped profile; every field specified below is absent by default, and a run
> without the block is required to be bit-identical to today's engine.
> **§5 is not proposed — it is a measurement of the shipped structure**, taken
> with
> [`hand_occupancy_readout.py`](../../telemetry_buffer/observation_model/hand_occupancy_readout.py),
> which landed with this document. It refutes part of §1's original reading and
> fixes the sign of §7's leading prediction *against* the anchor.

**Feeds.** Open ledger §1 items 22, 23 and 24; the provenance register rows for
`HAND_LOAD_LOG10_GEC` / `HAND_LOAD_REFERENCE_PEAK_LOG10`,
`stool_events_per_day`, `hand_hygiene_rate_per_hour` and
`hand_inactivation_rate_per_hour`. Evidence base:
[tranche 40](../literature/consensus_tranche_40_hand_event_amplitude.md),
with [tranche 39](../literature/consensus_tranche_39_hand_release_bridge.md)
(bridge envelope), [tranche 38](../literature/consensus_tranche_38_environmental_release.md)
(chair background null) and tranche 32 (stool-event rate) behind it.

---

## 1. What is wrong with the present structure

`TransmissionCore._replenish_hand` maintains one host's hand load two ways, and
tranche 40 falsifies both.

```python
target = agent.get_pathogen_hand_target(pathogen_id, profile or {})
...
if events_per_day is None:                      # continuous mode
    hand = target + (current - target) * survival
else:                                           # event mode (norovirus ships this)
    hand = current * survival
    if self._stool_event_occurs(events_per_day):
        hand = max(hand, target)
```

| # | Defect | Evidence (tranche 40) |
|---|---|---|
| **D1** | **The occupancy is wrong only on the arm that matters.** The continuous mode (every non-enteric profile) holds the hand at the ceiling for the whole illness — occupancy 1 by construction. The event mode does *not*: §5's readout measures **0.12–0.25** occupancy on the baseline arm and **0.50–0.82** on the diarrhoeal arm, against Liu's 0.254. So the baseline arm already reproduces the measurement and the **diarrhoeal arm is 2–3× over-occupied** — and the diarrhoeal arm is the one carrying the ship's dose | **18/71 (25.4%)** of rinses from symptomatic, stool-positive hosts were positive at an LOD of **2.15 log10 GEC/rinse**; two of six infected subjects never had a positive hand |
| **D2** | **No within-host temporal dispersion.** The only spread is `shedding_multiplier`, drawn once at infection and persistent, so a host's hand is the same relative load at every epoch of its illness | Ram 2011: paired rinses on the same mother hours apart differ by **3.5 log10 (SD 1.4)** and are **uncorrelated** (R = 0.13, P = 0.43). Liu's per-subject positivity ran 0% to 54.5% |
| **D3** | **The trigger has the wrong sign.** The ceiling is re-attained *at* the stool event | Rinses **immediately after bathroom use** were *lower* and less often positive (**11/89 = 12.4%**, mean **2.30**) than at routine vital-sign checks (**6/16 = 37.5%**, mean **3.32**), **P < 0.05** on both |
| **D4** | **`3.86` is used as a ceiling, not as a conditional mean.** `get_pathogen_hand_target` returns `10^3.86 × 10^(curve−11.0) × multiplier` as the value a hand attains | `3.86` is the **mean over the positive quarter**, per-subject means 3.30–4.45. It is `E[load | load > LOD]`, not `max load` |

**This corrects the reading the spec was drafted with.** "The hand is held at
its ceiling" is true of the continuous mode and false of the event mode, whose
stationary occupancy was never computed before §5 — it emerges from the shipped
event rate and die-off, and on the baseline arm it lands on Liu's figure
without having been aimed at it. What is wrong in the event mode is **D4 and
the diarrhoeal arm's occupancy**, and §5 shows those two cannot be repaired in
the same direction. The A9 posting floor (#500) is insensitive to every swept
axis for the simpler reason that the hand channel's amplitude is a constant
that no swept axis touches.

## 2. Design principle — reshape the time profile, do not touch the scale

The hand route has two independent unknowns and this document deliberately
addresses **only the second**:

1. **The bridge** — what mass of stool `10^3.86` corresponds to. Shipped as an
   implicit `−7.14 log10 g/hand`; tranche 39's indicator envelope says
   `−6.9 … −4.1`, tranche 40's within-study pairing says `−3.5 … −4.4`. **Out
   of scope. Unchanged. Still open.**
2. **The time profile** — how often a hand carries a load, and how much, around
   whatever reference amplitude the bridge eventually fixes.

So every amplitude below is expressed as an **offset from
`HAND_LOAD_LOG10_GEC`**, never as a replacement for it. When the bridge row
closes, it multiplies through this structure without re-deriving it, and
neither row can absorb the other's error.

## 3. Structure

Per host, per pathogen, a hand-load state `L(t)` in the engine's existing
units, driven by a marked point process plus continuous terms. Four
independently switchable components under one profile block,
`hand_event_release`.

### 3.1 (A) Contamination arrivals — a marked point process

Arrivals at hazard `λ_arrive(state)` per hour. Each arrival adds mass

```text
log10 ΔL  =  HAND_LOAD_LOG10_GEC
           + (curve[idx] − HAND_LOAD_REFERENCE_PEAK_LOG10)   # unchanged coupling
           + log10 shedding_multiplier                        # unchanged, between-host
           + activity_offset[kind]                            # 3.2
           + ε,          ε ~ Normal(0, σ_within)              # 3.3
```

Additive in mass, not `max()`: two arrivals without an intervening removal
compound, which is what lets the process exceed a single event's amplitude at
all. **But §5's readout shows this change is nearly inert at the shipped
rates** — additive and `max()` differ by `< 0.1 log10` in time-averaged mass,
because arrivals at 1–5.63/day are sparse against a die-off of 0.61–1.7/h and
rarely overlap. It matters only for an arrival kind whose hazard approaches the
removal rate. It is specified because a ceiling that cannot be exceeded is the
wrong shape, not because it is expected to move anything, and §7 P5 fixes that
prediction.

`λ_arrive` is **not free**: §5 shows it is identified, jointly with `σ_within`
and the existing removal terms, by Liu's occupancy — and §5.2 shows the
sourced triple is infeasible, which is the reason the arrival process is
allowed to differ from the toilet process at all. No value is declared here.

### 3.2 (B) The arrival kinds, and why the toilet is not the big one

Arrival kinds are declared per activity, each with its own hazard and an
amplitude offset. The **ordering** is what transfers from Pickering 2011 —
geometric-mean increments from **50 (dish washing) to 6,310 (food preparation)
CFU per two hands**, a span of ~2.1 log10 — not the absolute levels, which are
household faecal indicators in Dar es Salaam.

The toilet visit is modelled as a **pair**: an arrival *and* a coupled removal
(3.4), fired in that order within the epoch. This is the mechanism that
reproduces D3's sign without asserting it — a rinse sampled just after the
pair is post-wash, while a rinse sampled between pairs has had arrivals
accumulate with no washing. Whether the coupling fully explains Liu's 12.4% vs
37.5% is a **prediction to be measured** (§7 P3), not an assumption.

`stool_events_per_day` (tranche 32: 1.0 baseline, 5.63 diarrhoeal, in tree) is
reused unchanged as the toilet-pair hazard. It is the one arrival hazard with a
source, and its meaning changes from "recontamination to the ceiling" to
"arrival plus coupled removal".

### 3.3 (C) Amplitude dispersion — declared interval, and not a Pareto

`σ_within` is **within-host across time**, distinct from `shedding_multiplier`
(between-host, already in tree via `shedding_variance_log10`). Keeping them
separate is required to avoid double-counting, and the evidence separates
cleanly:

| Quantity | Figure | Where it belongs | Note |
|---|---|---|---|
| Spread of Liu's per-subject positive means | **3.30 – 4.45 log10**, i.e. a range of **1.15** over four subjects | between-host — already `shedding_multiplier` | a **floor** on total spread, since averaging within a subject removes the within part. A range, not an SD: Liu reports the means, not their dispersion |
| Ram's SD of the paired within-person difference | **1.4 log10** | within-host | a difference of two draws has SD `√2 σ`, so this implies `σ ≈ 1.0` **if** the whole SD is dispersion |
| Ram's *mean* paired difference | **3.5 log10** | **not dispersion** — a contrast between a random time and a "critical" time | belongs to 3.2's activity offsets; treating it as σ would imply `σ ≈ 3.1`, which is not credible and would be a unit-of-meaning error |

**Declared interval: `σ_within ∈ [0.5, 1.4] log10`**, frozen here, with two
caveats on the record. The top comes from Ram's SD: `1.0` is the deconvolved
reading, `1.4` the same SD taken at face value. The bottom is **a declaration,
not a measurement** — it is roughly the between-subject range in the row above,
used on the assumption that the within-host part is no smaller than the
between-host part. No point value. Shape: `U`.

**On the heavy tail.** No retrieved source fits a power law or generalized
Pareto to faecal contamination amplitude, reports a tail index, or publishes
the raw per-event observations needed to fit one — recorded `?nr-term` after
E1×3 and E2×2 (tranche 40 §6). This spec therefore provides the tail as a
**swept axis with no value and a null default**:

```text
tail_index_xi:  0.0  → pure lognormal (the declared default)
                > 0  → generalized-Pareto upper tail spliced above a declared quantile
```

`ξ = 0` must be bit-identical to the lognormal path. Any `ξ > 0` run is
labelled a **declaration** in its own readout, never a sourced value. This is
how the heavy-tail hypothesis gets tested without being adopted.

### 3.4 (D) Removals — two exist, one is added

Unchanged and reused:

- exponential inactivation, `hand_inactivation_rate_per_hour` (register row
  unchanged);
- discrete hygiene events, `hand_hygiene_rate_per_hour` ×
  `hand_hygiene_efficacy_log10_reduction` (`_apply_hand_hygiene`, unchanged).

Added:

- `post_toilet_wash_probability` — the probability that a toilet pair's removal
  fires. **Value ∅ null for any maritime population.** Declared corners `0.0`
  and `1.0` are the two ends of what the structure can do, exactly as
  `compliance_fraction` was handled for the crew duty exclusion (#469): `1.0`
  is an *enforced upper bound on what the structure removes*, not an estimate.
- an optional `bidet` removal offset. Oie's **39,499 ± 77,768 → 4,147 ± 11,427
  CFU/glove** is a ~10× reduction, but in total culturable units with no
  compatible denominator (ledger 23(e)), so it enters as an **ordering only**
  and carries no value.

### 3.5 (E) Continuous background

A small constant arrival `b` per hour, standing for own-source recontamination
between discrete events. Its evidence is Ram's post-washing result — **every**
participant had detectable faecal coliforms about two hours after supervised
handwashing with soap (GM 494 CFU/100 mL) — i.e. a hand does not stay clean, so
a pure point process with a hard floor of zero is also wrong.

Bounded above, not valued: `b` may not be large enough that its own stationary
load alone exceeds Liu's positive mean. **This term may not be sourced from
seating or built-environment deposition**: tranche 38's chair background is a
∅ null (16S gives source *fractions*, and crAssphage is a water literature at
copies/100 mL), so `b` is own-source only and says nothing about furniture.

## 4. What does *not* change

- `HAND_LOAD_LOG10_GEC`, `HAND_LOAD_REFERENCE_PEAK_LOG10`, and the `−7.14`
  bridge (§2).
- `environmental_faecal_release_log10_g_per_epoch` and its `[4, 24]` interval —
  a different channel (#498), still void.
- The dose-response, `POSTING_THRESHOLD`, and the observation model.
- All three consumers of the hand load. `_deposit_*`/`_food_deposits`/
  `_hand_to_mouth_dose` each read `hand_load_by_pathogen` multiplicatively and
  deplete it with `min(hand, requested)`; that is already the right shape for
  an event-driven load and is left alone. **No propagation term is added** —
  which is what makes §7's predictions sharp.
- `shedding_multiplier` and `shedding_variance_log10` (between-host), for the
  reason in 3.3.

## 5. Identification — the hand route gets its own out-of-sample check, and it fails it in a fixed direction

The most important property of this structure: it is **not** a set of free
parameters. Liu 2013 reports two moments of the stationary process, and they
can be computed without touching a scored anchor.

| Observable | Liu's value | How it is reported |
|---|---|---|
| Occupancy | **25.4% (18/71)** of hand-epochs of symptomatic, stool-positive hosts | fraction of hand-epochs with `L > LOD` |
| Conditional mean | **3.86 log10** (subject means 3.30–4.45) | mean `log10 L` over those epochs |
| Context contrast | 12.4% / 2.30 after toilet vs 37.5% / 3.32 routine | the same two statistics split by epochs-since-toilet-pair |

`LOD` is applied **in the readout**, not in the engine: `2.15 log10 GEC per
rinse`. The model gains no censoring parameter.

### 5.1 The check, run against the shipped structure before proposing anything

[`telemetry_buffer/observation_model/hand_occupancy_readout.py`](../../telemetry_buffer/observation_model/hand_occupancy_readout.py)
reproduces `_replenish_hand`'s recurrence and reports both moments. Run on the
shipped values — ceiling `3.86`, `stool_events_per_day` 1.0 / 5.63,
`hand_inactivation_rate_per_hour` `[0.61, 1.7]`, no dispersion, hygiene at its
shipped `0.0`/h:

| Arm | `k` /h | Occupancy | ÷ Liu's 0.254 | `E[log10 L \| +]` | − Liu's 3.86 | time-avg `log10 L` |
|---|---|---|---|---|---|---|
| baseline 1.0/day | 0.61 | 0.249 | 0.98 | 3.11 | −0.75 | 2.78 |
| baseline 1.0/day | 1.70 | 0.116 | 0.46 | 3.14 | −0.72 | 2.55 |
| **diarrhoeal 5.63/day** | 0.61 | **0.805** | **3.17** | 3.30 | −0.56 | 3.42 |
| **diarrhoeal 5.63/day** | 1.70 | **0.503** | **1.98** | 3.24 | −0.62 | 3.25 |

Three results, none of which was aimed at an anchor:

1. **The baseline arm passes.** 0.116–0.249 brackets Liu's 0.254 at the slow
   end of the sourced die-off interval. Nobody arranged this: it is
   `λ/k` falling out of tranche 32's event rate and an independently sourced
   inactivation rate. It is the first out-of-sample check the hand route has
   ever passed.
2. **The diarrhoeal arm fails high on occupancy, by 2–3×** — and Liu's subjects
   *were* symptomatic challenge cases, so that is the arm his 25.4% should be
   compared against.
3. **Every arm fails low on amplitude, by 0.56–0.75 log10.** This is D4 made
   quantitative: a load that decays from `3.86` spends its supra-LOD time
   *below* `3.86`, so using the conditional mean as the ceiling necessarily
   under-reproduces the conditional mean.

### 5.2 The two failures have opposite signs, and the joint solve is infeasible

Searching `(peak, post-toilet wash probability)` for the pair reproducing both
of Liu's moments on the diarrhoeal arm — wash efficacy at the sourced `1.06`
and `1.89` log10 corners, `σ_within ∈ {0, 0.5, 1.0}` — returns **no feasible
cell**. The best cells reach the conditional mean only at occupancies of
0.29–0.86, and they do it with a per-event peak of **4.0–6.2 log10** in place of
`3.86`, for a time-averaged hand mass **+0.8 to +1.7 log10 above shipped**.
Only one corner (`k = 0.61`, wash efficacy 1.89) lowers the mass, and it misses
the conditional mean by 0.42 log10.

So three independently sourced quantities — tranche 32's diarrhoeal event rate,
the hand inactivation interval, and Liu's two moments — are **jointly
infeasible under the decay-plus-reset structure with the sourced removals**.
That is a structural refutation, and it is the argument for §3 that does not
come from an anchor. At least one of the following must be true, and the spec
must not pick by which one helps A9:

- removal after a toilet event is stronger or more frequent than the sourced
  hygiene envelope (§3.4 — and this is also D3's mechanism);
- the arrival rate for *hand contamination* is not the defecation rate
  (§3.2 — arrivals and toilet visits are different point processes);
- Liu's challenge-volunteer occupancy does not transfer to a cruise host
  (setting grade **C**; two of his six subjects never had a positive hand).

### 5.3 The direction this pushes the anchor, stated before implementation

The amplitude repair **raises** the hand-route mass by ~0.8–1.7 log10; the
occupancy repair **lowers** it by at most `log10(5.63/1.5) ≈ 0.57`. They do not
cancel, and the residual is positive. Since A9 is already **above** target, a
hand route reconciled with Liu is expected to make A9 **worse**, by up to an
order of magnitude. This is recorded here, in advance, precisely because it is
the outcome that a fit would have avoided — and by the provenance rule it is a
result, not a reason to choose differently.

Two moments constrain the combination of `λ_arrive`, `σ_within` and the
removal rates, so the process has roughly as many free directions as
constraints — which is the difference between this and a distribution chosen by
what it does downstream.

**Circularity bookkeeping, stated in advance** (the rule from
[`bayesian_inference_design.md`](bayesian_inference_design.md) §4: a datum in a
fit's likelihood is barred from that fit's prior). If Liu's occupancy and
conditional mean are used to constrain the event process, then:

- the same pair is **barred** from any later prior on the hand route, and
- `HAND_LOAD_LOG10_GEC` stops being readable as an independent amplitude —
  it becomes the conditional mean the constraint consumed. The register row
  must say so.

This is *calibration to the measurement that sources the mechanism*, and it is
categorically different from fitting to A9, VSP, Park or A5. **None of those
may be used to set any field in this spec**, and §7 fixes the signs before
anything runs.

## 6. Parameter table — intervals frozen here, values absent

| Field | Meaning | Declared interval | Source / grade | State |
|---|---|---|---|---|
| `hand_event_release.enabled` | master switch | — | — | **absent ⇒ today's engine, bit-identical** |
| `λ_arrive` per activity kind | contamination arrival hazard, /h | **no interval** — identified by §5, which also shows it cannot equal `stool_events_per_day` and satisfy Liu | ∅ for a direct measurement | **identified, not declared** |
| `activity_offset[kind]` | amplitude offset by arrival kind, log10 | span **≤ 2.1** (ordering only) | Pickering 2011, Ab. **C** — household indicators | ordering transfers; levels do not |
| `σ_within` | within-host amplitude dispersion, log10 | **[0.5, 1.4]**, shape U | Ram 2011 (R) for the top, deconvolution caveat in 3.3; the bottom is declared. **C** | **frozen interval, no value** |
| `tail_index_xi` | GP upper-tail index | **0 default**; sweep only | **`?nr-term`** — no retrieved fit | a **declaration** when non-zero |
| `stool_events_per_day` | toilet-pair hazard | 1.0 / 5.63 per day (in tree) | tranche 32. **B** | **unchanged, reused** |
| `post_toilet_wash_probability` | coupled removal fires | corners **0.0** and **1.0** | **∅ null** maritime | upper bound, not an estimate |
| `bidet_offset` | removal offset with a bidet | **no value** | Oie, unconvertible units | ordering only (~10×) |
| `b` | continuous background arrival, /h | bounded above by §3.5 | Ram post-wash (R). **C** | **bound, no value**; own-source only |
| `hand_inactivation_rate_per_hour` | removal | unchanged | unchanged | unchanged |
| `hand_hygiene_rate_per_hour`, efficacy | removal | unchanged | unchanged | unchanged |

## 7. Pre-registered predictions, with signs fixed before implementation

Written down now so the readout is a test. A9 is **above** target
(0.42–0.56% per eligible voyage; #500 measured ~2.5% at `adj ≥ 10`), and the
leading prediction moves it further the wrong way.

- **P1 (level, sign fixed: UP, against the anchor).** §5.3's arithmetic, not a
  hope: reconciling the diarrhoeal arm with *both* of Liu's moments raises the
  time-averaged hand mass by **+0.8 to +1.7 log10** (amplitude) against at most
  **−0.57** (occupancy). All three consumers are linear in `L`, so the posting
  floor should rise roughly with the residual — A9 is already 4.5–6× high and
  this is expected to make it **worse**. An implementation that reports A9
  improving should be suspected of a bug before it is believed. If a field is
  then adjusted until A9 closes, that is fitting, and it is forbidden.
- **P1b (the baseline arm, sign fixed: unchanged).** The non-diarrhoeal arm
  already reproduces Liu's occupancy (§5.1), so any structure that moves it far
  outside 0.12–0.25 has broken a check the shipped model passes. This is the
  negative control for the whole spec.
- **P2 (dispersion at fixed arithmetic mean, sign fixed: near-null).** Because
  the three routes are linear in `L` and Beta-Poisson is near-linear at low
  dose, adding `σ_within` while holding the *arithmetic* mean fixed should be
  close to a null on mean dose. It can only bite through (i) the `min(hand, ·)`
  depletion caps, (ii) the dose-response's nonlinear regime, (iii) the
  voyage-level posting threshold. **This is the sharp test of the heavy-tail
  hypothesis:** if dispersion matters, it must show up in the *posting rate at
  fixed attack rate*, not in the attack rate. A large P2 effect on attack rate
  would indicate a bug, not a tail.
- **P3 (the toilet pair, sign fixed: reallocation, not level).** Coupling a
  removal to the toilet event moves the high-load epochs out of the cabin and
  into dining and lounge zones. Expect a **route-share** shift with little
  change in total dose, and a simulated post-toilet/routine contrast with the
  same sign as Liu's 12.4% vs 37.5%. If the sign does not reproduce, the
  coupling is not the explanation and §3.2 is wrong.
- **P5 (additive arrivals, sign fixed: inert).** Replacing `max(decayed,
  target)` with summation must move the time-averaged hand mass by `< 0.1
  log10` at the shipped event rates — measured in §5 and locked by
  `tests/test_hand_occupancy_readout.py`. A larger move means an arrival hazard
  was raised somewhere, and that, not the summation, is what to report.
- **P4 (A5, sign fixed: no help).** The stratified re-read (ledger item 21) put
  A5 at **2.56 / 2.75 / 2.61 against ≈ 3.5** on the channel that readout
  reports — in the dead, transitional and burning dose regimes alike, and the
  fleet anchor is 4.3 — so a hand-route reshaping is not expected to move the
  crew deficit. If it does, that is a finding about the
  crew hand route, and it needs its own explanation before it is believed.

## 8. Staging, each gate independent

| Stage | Content | Gate |
|---|---|---|
| **S0** | *Done, in this change:* the readout module and its tests, run against the shipped structure | §5.1–5.3 — reported above, anchor-adverse, nothing adopted |
| **S1** | The point process: additive arrivals, `σ_within`, continuous background, existing removals. No activity conditioning, no toilet pair, `ξ = 0` | absent-block bit-identity; cross-grid invariance (1 h vs 24 h clock, per `clock_unit_safety_spec.md`); the §5 readout re-run in-engine, reproducing the module's occupancy for the same declaration |
| **S2** | Activity-conditioned arrivals and the toilet pair with its coupled removal | P3's sign reproduces, or S2 is reported as refuted |
| **S3** | `tail_index_xi` as a declared axis | P2 measured at fixed arithmetic mean; result labelled a declaration |
| **S4** | Plumb as a bounded-gate design arm (the #491/#495 pattern) and run a matched expedition campaign with today's engine as the paired control | finite-sample readout by channel, §5 checks reported **before** A9/A5 are read |

New draws take a **derived RNG stream** (the #411 pattern), so enabling the
block cannot perturb any other draw and the control arm stays reproducible.

## 9. Refusals

1. No value is adopted for `λ_arrive`, `σ_within`, `b`,
   `post_toilet_wash_probability`, `tail_index_xi` or any activity offset.
2. **No Pareto or generalized-Pareto default.** The tail is a swept axis whose
   default is off, because the tail index is `?nr-term`.
3. The `−7.14` bridge is not resolved, raised or lowered here, and this spec
   may not be used as an argument for moving it (§2).
4. No field here may be set, retimed or re-signed by what moves A9, A5, VSP,
   Park or the passenger/crew ratio. The signs in §7 are fixed now precisely so
   that following the anchor later would be visible.
5. The rare high-consequence release mode is **specified nowhere in §3 with a
   value**, deliberately: its frequency exists only on a pool-bather denominator
   (Chalmers 2021, 1 in 10³ to worse than 1 in 10⁴) and its per-event mass only
   as another model's declared triangular (Petterson 2020, 0.06/0.6/6 g). It can
   be built as a second arrival kind, and it cannot yet be valued.
6. `b` may not be sourced from seating, furniture or built-environment
   microbiome data (tranche 38 ∅ null).
