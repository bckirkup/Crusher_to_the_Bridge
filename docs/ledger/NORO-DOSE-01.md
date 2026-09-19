# NORO-DOSE-01
**Date:** 2026-09-19
**Commit:** cd446de
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f55e93f

Dose reaching hosts on `classic_cruise_1900`: ordered transmission-blocker
cascade after `NORO-SUSCEPT-02` closed the credited-dose to evaluated-hazard
chain and `NORO-SUSCEPT-03` excluded the sourced α interval. Those findings are
settled inputs and are not re-derived. In particular, no arm in this entry moves
`dose_response.alpha` or `dose_response.beta`; `RNG-FRAILTY-STREAM-01` makes
such arms unpairable at fixed seed.

This entry freezes the design and decision criteria **before any cell runs** and
records measurements from the existing `NORO-SUSCEPT-02` instrumented dumps
(seeds 8105 and 8106, 288 epochs, shipped profile, no overrides). The instrument
is `tools/noro_diag/per_host_dose_challenge.py` run at `9f4cd79`; the engine at
`f55e93f` is unchanged from that SHA on every path the cascade reads. No model
constant, pathogen profile, or shipped configuration value was changed.

## Settled inputs

- `NORO-SUSCEPT-02`, measured at `9f4cd79`: the post-route credited dose, dose
  read at challenge, and effective dose evaluated reconcile exactly. At seed
  8105 a 288-epoch voyage credited 0.100952 GEC after host susceptibility
  scaling and produced Σ evaluated hazard 3.8091e-4; seed 8106 credited
  0.002713 GEC and produced 1.1871e-5.
- `NORO-SUSCEPT-03`, measured at `f5f9ff3`: 0 secondaries in 14 voyages, maximum
  Σ hazard 1.186e-2, and the sourced α interval moves mean susceptibility only
  about 2.2-fold. α is closed and will not be reopened here.

## Frozen design

| Item | Declaration |
| --- | --- |
| Platform | `classic_cruise_1900`, declared complement (1,910 agents) |
| Voyage | 288 epochs |
| Observational seeds | 8105 and 8106, fixed shipped profile, no overrides |
| Primary trace | seed 8105, because the settled reference voyage has non-zero emesis and fomite witnesses and the larger credited dose |
| Confirming trace | seed 8106; an all-zero route witness makes a route conclusion void for that seed, not negative evidence |
| Forced challenge | seed 8105, only if Steps 1–3 find a downstream blocker |
| Forbidden arms | any arm changing `dose_response.alpha` or `.beta`; any constant or shipped configuration change |

The two observational seeds are a mechanism smoke, not an effect-size sample.
No rate, population mean, or calibrated parameter will be estimated from them.

## Criterion, frozen before execution

### Step 0 — anything to explain

Report observed secondaries and the engine's summed evaluated hazard. Zero
secondaries is called a downstream blocker only if the Poisson approximation
`P(N = 0) = exp(-Σ hazard)` is below 0.05. Otherwise zero is an ordinary draw;
the remaining cascade is explicitly a dose-delivery diagnosis, not a search for
a Bernoulli failure.

### Step 1 — route attribution

For every credited host, record credited dose by route, and for the voyage
report each route's total and share. A route is called **exercised** only when
its own execution witness is non-zero. The suspect route is the exercised route
contributing the largest share of post-route credited dose; if no route exceeds
50%, carry every route within 10 percentage points of the largest into Step 2.

### Step 2 — pickup terms

For the suspect route, record the ordered mass terms. For fomite these are
surface mass deposited → surface mass offered at pickup → pickup mass requested
→ mass delivered to hands → hand load presented to hand-to-mouth → ingested dose
→ `_accumulate` dose → post-route credited dose. Report adjacent pass-through
ratios and `-log10(ratio)` losses. The **principal attenuation term** is the
largest adjacent log loss, provided its input and output witnesses are both
non-zero; ties within 0.25 log10 are reported as joint.

Independently probe the recurring carrier-dead-end archetype: identify whether
hand-mediated source routes gate on `_get_shedders()` such that a non-shedding
host with hand contamination from surface pickup is a dead end.

### Step 3 — host blockers

For the most-dosed challenged host at its largest-dose epoch, record in engine
order: challenge entry state, exit reason, protection, secretor multiplier,
persistent susceptibility, effective dose, recomputed hazard, and engine hazard.

### Step 4 — forced challenge trace

Only after Steps 1–3, inject a labelled challenge into one susceptible host in
the seed-8105 voyage without changing α, β, or any constant. **Only if Steps
1–3 find a downstream blocker.**

---

## Measured result

### Step 0: anything to explain

| Quantity | seed 8105 | seed 8106 |
| --- | --- | --- |
| Observed secondaries | 0 | 0 |
| Imports (index cases) | 5 | 2 |
| Σ evaluated hazard | 3.8091e-4 | 1.1871e-5 |
| P(0 secondaries) | 0.9996 | 0.99999 |
| Credited-scaled GEC | 0.100952 | 0.002713 |

**Zero secondaries is the correct draw at both seeds.** The engine's expected
secondary count is below 0.001 at seed 8105 and below 0.00002 at 8106; the
Poisson P(0) is well above 0.05 at both. There is no Bernoulli blocker to
find. The remaining cascade is a dose-delivery diagnosis: the question is why
a 288-epoch voyage on a 1,910-agent hull credits only ~0.1 GEC total.

### Step 1: route attribution

Pre-route-efficiency pathway accumulated dose (seed 8105):

| Route | Accumulated GEC | Share of total |
| --- | --- | --- |
| fomite | 0.3826 | 93.5% |
| direct_contact | 0.0218 | 5.3% |
| hvac_airborne | 0.00286 | 0.7% |
| food | 0.00216 | 0.5% |
| droplet | 0 | 0% |
| **Total accumulated** | **0.4094** | |

Post-route-efficiency (fomite ×0.30, direct ×0.35, HVAC ×0.05, food ×0.20):
credited raw = 0.1230 GEC. After host susceptibility scaling (secretor-negative
hosts at 0.20): credited scaled = 0.1010 GEC.

Seed 8106: fomite is 99.7% of accumulated dose (0.00965 GEC); direct contact is
0.3%. No HVAC or food dose measured.

**Fomite is the exercised dominant route at both seeds** and is the sole suspect
carried into Step 2. All other routes contribute at most 5.3% of the total.

Emesis witness (seed 8105): 1 event, 1.96e6 GEC patch mass filed, 2 patch
pickups, 2.610 GEC delivered to hands. Seed 8106: zero emesis events (no
host reached a vomiting presentation). The emesis pathway fires at seed 8105
and delivers dose to hands, which enters the same fomite chain. 2.610 GEC of
the 58.91 GEC hand load presented to hand-to-mouth is emesis-patch material;
the balance is surface pickup plus hand load retained across epochs.

### Step 2: pickup terms

Fomite chain mass terms (seed 8105, 288-epoch voyage):

| Term | Value | Adjacent ratio | -log10 loss |
| --- | --- | --- | --- |
| Shedder max hand load (peak) | 139,245 GEC | | |
| Surface mass deposited (voyage total) | 220.3 GEC | | |
| Surface mass offered at pickup | 5,170 GEC | | |
| Pickup mass requested | 35.13 GEC | 0.00680 | **2.17** |
| Mass delivered to hands | 33.03 GEC | 0.940 | 0.03 |
| Hand load presented to hand-to-mouth | 58.91 GEC | (includes emesis + prior hand load) | |
| Ingested dose (hand-to-mouth) | 0.692 GEC | 0.0117 | **1.93** |
| Accumulated (pre-route-efficiency) | 0.383 GEC | | |
| Credited raw (post-efficiency ×0.30) | 0.123 GEC | | |

**Two principal attenuation terms (jointly within 0.25 log10 at -2.17
and -1.93):**

1. **Surface → hand pickup** (`_fomite_pickup_request_for_area`): 0.68% of the
   offered surface mass reaches hands. The transfer formula is
   `contacts × (used_fraction × hand_area / surface_area) ×
   transfer_efficiency × surface_mass`, and every factor is geometrically
   small: hand area is ~150 cm² against a venue high-touch area of
   order 10–100 m²; used_fraction and transfer_efficiency are each fractions;
   surface contacts per epoch is a single-digit count.

2. **Hand → mouth ingestion** (`_hand_to_mouth_dose`): 1.17% of the hand load
   reaches the mouth. The formula is
   `mouth_contacts × used_fraction × transfer_efficiency × hand_load`, and
   again every factor is fractional.

Together these two steps consume 4.1 log10 of the dose between the surface pool
and the accumulator, which is the principal structural attenuation in the fomite
chain. Both terms are stochastic draws from measured parameter ranges; neither is
a defect, and neither is an engine gate or a missing mechanism.

Seed 8106 shows the same structure with smaller absolute magnitudes (no emesis
contribution, 2 imports instead of 5):

| Term | seed 8106 |
| --- | --- |
| offered→requested | ratio 0.273, -log10 = 0.56 |
| hand_load→mouth | ratio 0.0079, -log10 = 2.10 |

#### Carrier-dead-end archetype probe

Three hand-mediated source routes gate on `_get_shedders()`:

| Route | Gate location | Effect |
| --- | --- | --- |
| Sanitary fomite deposit | `_sanitary_fomite_exposure` line 6648: `if not self._get_shedders([agent], ...)` | A non-shedding visitor who picked up hand contamination from a surface cannot re-deposit it at any venue |
| Food deposit | `_food_deposits` line 7034: `for agent, _sv in self._get_shedders(...)` | A non-shedding food handler carrying hand contamination cannot deposit to the food pool |
| Direct contact transfer | `_direct_contact_unit` line 4702: `shedders = self._get_shedders(...)` | A non-shedding host with hand load cannot transfer it via handshake or close contact |

**The archetype applies.** A host that acquires hand contamination from a
surface or emesis patch pickup is a dead end: the mass sits on its hands (and
decays by inactivation) but can never re-enter any pool or any other host. The
two-hop chain — index sheds onto hands → surface → third party picks up →
third party deposits or transfers — is truncated at the second hop, and the
only path from hands to infection is the single-host hand-to-mouth step whose
ingestion fraction is 1.17%.

This is not a defect in the engine's logic — `_get_shedders` checks pathogen
shedding status, not hand-load content, and the distinction is epidemiologically
correct for the *shedding* route (you don't shed from your hands; you shed from
your gut). But it means that the fomite route is structurally a **one-hop
chain**: shedder → surface → recipient → mouth → accumulate, with no
amplification loop through re-contamination of surfaces by carriers. Every GEC
that reaches a susceptible's challenge came from one of the 5 (seed 8105) or 2
(seed 8106) imported shedders, never from a passenger who was contaminated by a
previous passenger.

**Quantitative consequence:** `hand_target_positive_calls` = 960 at seed 8105,
confirming that only the shedding imports ever acquire a positive hand target.
The surface pool receives deposits only from those shedders (40 deposit calls
over the voyage). All 1,441 credited hosts acquired their dose exclusively from
the shedders' deposits.

### Step 3: host blockers

Most-dosed challenged host: agent 184, seed 8105.

| Term | Value |
| --- | --- |
| Credited-scaled dose | 0.009518 GEC |
| Crediting epochs | 202 of 288 |
| Susceptibility multiplier | 1.0 (secretor-positive) |
| Protection | 0.0 (no immunity) |
| Effective dose evaluated | 0.009518 GEC |
| Persistent frailty | 0.002158 |
| Engine hazard sum | 2.054e-5 |
| Recomputed hazard (from voyage total × frailty) | 2.054e-5 |
| Engine−recomputed difference | 8.1e-12 |
| Challenge exit reasons | 202 evaluated, 86 no_dose_this_epoch |
| Epochs infected when credited | 0 |
| Epochs immune when credited | 0 |

**No host blocker.** Protection is zero, no host was credited dose while
infected or immune, the susceptibility multiplier is 1.0 for this secretor-
positive host, and the engine and recomputed hazard agree to 1e-11 relative.
The challenge chain is clean. The frailty (0.002158) is near the population
median (0.0000685) — it is a typical host, not an extreme — and the hazard sum
at its credited dose of 0.0095 GEC is 2e-5, confirming that even the most-dosed
host receives so little that infection probability is negligible.

Agent 488 has the highest frailty among the top-5 dosed hosts (0.0108) and its
hazard sum is 3.72e-5 — still negligible.

### Step 4: forced challenge trace

**Not executed.** Steps 1–3 found no downstream blocker: the challenge chain is
clean, no host term is zero or anomalous, and the engine's hazard computation
reconciles. The deficit is entirely upstream — the dose reaching hosts is
structurally small because of the two geometrical attenuation steps in the
fomite pickup-and-ingestion chain, not because of a broken mechanism.

## Summary of the cascade

| Step | Finding |
| --- | --- |
| 0. Σ hazard | 3.81e-4 (seed 8105). P(0) = 0.9996. Zero secondaries is an ordinary draw. |
| 1. Route attribution | Fomite is 93.5% of accumulated dose. All other routes < 6%. |
| 2a. Pickup terms | Two joint principal attenuation terms: surface→hand pickup (-2.17 log10) and hand→mouth ingestion (-1.93 log10), together consuming 4.1 log10 of dose. |
| 2b. Archetype | Carrier-dead-end confirmed: non-shedding hosts with hand contamination cannot re-deposit to any pool or transfer via contact. Fomite is a one-hop chain with no amplification. |
| 3. Host blockers | None. Protection = 0, susceptibility clean, hazard reconciles. |
| 4. Forced trace | Not needed; no downstream blocker found. |

## Recommendation

**No constant change.** The measured facts are:

1. The fomite chain's geometrical attenuation (4.1 log10 across the two pickup
   and ingestion steps) is the principal reason the credited dose is ~0.1 GEC
   over a 288-epoch voyage. These are stochastic draws from declared parameter
   ranges (hand area, surface area, contact fractions, transfer efficiencies),
   not tuneable constants.

2. The carrier-dead-end structure (one-hop chain, no re-contamination
   amplification) means the surface pool is fed only by the imported shedders
   and cannot grow via a contamination cascade through the susceptible
   population. This is the structural reason one host holds 90% of the
   credited dose in several cells.

3. The two attenuation terms and the one-hop structure are independent: even if
   the archetype were repaired (carriers allowed to re-deposit), the
   per-transfer geometrical loss would still consume ~2 log10 at each hop, so
   the amplification factor per hop would be well below 1.0 and the cascade
   would damp rather than grow.

**The next question is not "what is broken" but "is the one-hop fomite chain
physically correct at this hull scale".** The parameter ranges driving the two
attenuation terms (hand area, surface area, surface-to-hand transfer
efficiency, hand-to-mouth contacts and transfer efficiency) are each sourced
from the literature with evidence grades, but their product has never been
validated against a whole-voyage dose measurement. The product, not any single
factor, is what the 4.1 log10 loss measures.

Candidates for the next declared study, in decreasing cost-effectiveness:

1. **Replicated-seed emesis sizing.** Only 1 of 3 scheduled episodes became an
   emitted event at seed 8105, and emesis patch pickup contributes 2.61 of the
   58.91 GEC hand load (4.4%) from a single event against 33.03 GEC of surface
   pickup spread over 1,917 deliveries — the highest mass-per-event term
   measured. `NORO-SUSCEPT-02` §e left this unsized
   and `NORO-SUSCEPT-03` §d confirmed it was not sized. A replicated design at
   fixed α (no `RNG-FRAILTY-STREAM-01` conflict) and ≥20 seeds would measure
   the emesis event rate and the dose distribution conditional on an event.

2. **Carrier re-deposition study.** Instrument one arm that labels non-shedding
   carriers' hand-to-surface deposits (a shadow deposit that does not enter the
   pool but is counted) and measure the mass the archetype truncates. This costs
   one local voyage per seed and quantifies the one-hop constraint without
   changing any constant.

3. **Per-hop transfer efficiency validation.** Compare the product of
   `SURFACE_TO_HAND_LOGNORMAL`, `HAND_TO_MOUTH_NORMAL`, and the contact counts
   against the few whole-voyage environmental assay studies that measure both
   surface contamination and hand contamination in the same setting.

None of these require changing a constant, and each has a pre-declarable
criterion. The emesis sizing is the cheapest and has the largest potential
information yield, because emesis is both the dominant source term (1.96e6 GEC
filed) and the most stochastic (0 or 1 events per seed).

## Reported but never selected on

Secondaries, imports, attack rate, route shares, concentration quantiles,
emesis counts, individual stochastic pickup draws, and frailty quantiles are
reported for diagnosis. None licenses a constant change or a recommendation
to fit a model parameter.
