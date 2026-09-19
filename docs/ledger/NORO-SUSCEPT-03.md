# NORO-SUSCEPT-03
**Date:** 2026-09-19
**Commit:** 46cff41
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f5f9ff3

Swept-α axis on the classic hull: is the *expectation* wrong? `NORO-SUSCEPT-02`
closed the chain and the host set — credited dose and evaluated hazard are
taken over the same hosts at the same seam and reconcile exactly (0.100952 GEC
credited-scaled = dose read at challenge = effective dose evaluated, seed
8105), zero hosts and zero GEC reach a host that is never challenged, 106 and
48 hosts hold 90% of credited dose, and the emesis pathway fires end-to-end to
a patch pickup delivering 2.610 GEC onto a host's hands. The §1 figures of
`NORO-SUSCEPT-01` (394,281 GEC, 49,572 GEC, naive hazard 0.197) are void and
are not quoted here. What is left is the dose-response expectation itself.

This entry freezes the design and the admissibility criterion **before any cell
runs**, per the `campaign-preflight` skill (Rule A). Nothing is fitted here.
No α is selected. No constant in the repository moves: α is supplied per cell
as a Picard `pathogen_overrides` patch on a diagnostic run, and
`data/pathogens/active_profiles.json` is not edited in this session.

## 1. Frozen design

| Axis | Value |
| --- | --- |
| Swept parameter | `norwalk_gi.dose_response.alpha` |
| Grid | 0.0720, 0.0898, 0.1076, **0.1110**, 0.1254, 0.1432, 0.1610 |
| Held fixed | `beta = 32.81`, pinned explicitly in every override patch |
| Seeds | 8105 and 8106, paired, every cell |
| Platform | `classic_cruise_1900` at its declared complement (1,910 agents) |
| Epochs | 288 |
| Everything else | shipped `active_profiles` bundle, `crusher_labs/config.yaml`, no run overrides beyond the agent count the instrument already sets |
| Cells | 7 α × 2 seeds = 14 instrumented voyages |

**Endpoints and spacing.** The endpoints are the frozen evidence interval
`[0.072, 0.161]` recorded in `NORO-SUSCEPT-01`; they are not widened, and the
`model-parameter-provenance` rule that a boundary-pinned result is not a pass
is in force. Six points at a uniform spacing of 0.0178 (= 0.089 / 5) cover the
interval, plus the shipped 0.111 as an eighth-of-the-way reference cell so the
sweep contains its own comparison against the measured `NORO-SUSCEPT-02` arm
under identical code. Uniform rather than logarithmic spacing because the
quantity the decision reads is very nearly linear in α over this interval: at
the doses measured in -02 (≤ 0.101 GEC) the per-host hazard is
`1 − exp(−f·d) ≈ f·d`, so summed hazard scales with the mean frailty
`α/(α+β)`, which rises 2.23× monotonically and near-linearly from 2.190e-3 to
4.883e-3 across the interval. Finer spacing cannot change an order of
magnitude; the grid is sized to show the *shape* of that rise, not to resolve a
threshold crossing that the arithmetic already bounds.

## 2. Primary statistic and admissibility criterion (frozen)

**Primary statistic: the summed evaluated hazard per cell per seed,**
`reconciliation.sum_evaluated_hazard` — the sum over every challenge the engine
actually evaluated of `1 − exp(−frailty · effective_dose)`. This is the
model's own expected number of onboard secondary infections for the voyage: the
engine converts each hazard into one Bernoulli draw, so the sum is the Poisson-
binomial mean of the secondary count. It is chosen as primary *because* the
observed secondary count is the zero-inflated realisation of it: at the -02
level (3.8091e-04 at seed 8105) a two-seed observed count of zero carries
almost no information, whereas the expectation it is drawn from is measured
without sampling noise. Declaring the counter as primary would be declaring a
statistic this sweep is not powered to read.

Decision bands, fixed now:

- **Capable** — Σ hazard ≥ 1.0 at either seed at some α in the grid: the
  admissible interval can produce onboard secondary transmission, and the
  expectation, not the dose, is the suspect.
- **Marginal** — 0.1 ≤ max Σ hazard < 1.0: the interval is not sufficient on
  its own but is within one order of magnitude, and α stays on the table as a
  contributing term.
- **Excluded** — max Σ hazard < 0.1 across all 14 runs: no α in
  `[0.072, 0.161]` can explain onboard secondary transmission at 288 epochs on
  this hull. The conclusion is then that the interval is not the explanation
  and the suspect moves to the dose reaching hosts, not the dose-response.

**Confirming binary (reported, not selected):** observed challenge-acquired
infections per cell — an agent not infected with `norwalk_gi` on entry to
`_resolve_pathogen_challenge` that is infected on return. That count is
`secondaries`; imports (agents seen resident without a preceding
challenge-acquired infection) are counted separately, and
`ever_infected = imports + secondaries`. Attack rate, if any cell produces
secondaries, is `secondaries / 1910` and is reported across the interval.

**Hard gate — the reconciliation must still close at every cell.**
`sum_credited_scaled_gec`, `sum_dose_read_at_challenge_gec` and
`sum_effective_dose_evaluated_gec` must agree to a relative difference
≤ 1e-9 in all 14 runs, as they did in -02. α scales frailty, not dose, so any
cell in which the chain opens is a harness defect: the sweep is then stopped
and reported as a defect, not interpreted.

**Reported but never selected on:** `ever_infected`, imports, the concentration
curve (hosts holding 50/90/95/99% of credited dose), hosts credited, hosts
evaluated, challenge exit reasons, the frailty quantiles, the emesis witness,
the fomite witness. No α value will be recommended for adoption from this
sweep, and no cell will be preferred because it moves VSP, Park or the
passenger/crew ratio — the sweep answers a capability question about the
interval as a whole, which is the only question a swept axis can answer without
becoming a fit.

## 3. Override-reaches-the-engine proof (must pass before the sweep)

An α that does not move the frailty draw is a broken harness, not a null
result. Before any 288-epoch cell, one short paired arm at seed 8105 —
α = 0.072 and α = 0.161, 48 epochs, everything else identical — must satisfy
all three of:

1. **Spec read-back**: the α on the resolved `norwalk_gi` profile handed to
   `ShipSimulation` equals the requested α, and β equals 32.81, in both arms.
2. **Distribution shift**: the median engine-drawn per-host frailty at
   α = 0.161 is at least **10×** the median at α = 0.072, over at least 200
   drawn frailties per arm (if the short cell draws fewer, epochs are raised
   until it does). Predicted ratio from Beta quantiles is ≈ 220×; the 10×
   floor sits far below the prediction and far above the paired-seed spread
   at fixed α measured in -02 (median frailty 6.85e-5 vs 4.40e-5, 1.56×), so
   the test cannot be passed by seed noise.
3. **Two-sample KS** between the two arms' drawn frailties: p < 0.001. At
   n = 200 per arm, 200 simulated repetitions of this contrast gave a maximum
   p of 2.8e-4, so the floor is reachable whenever the harness works.

Failing any of the three stops the session with a harness defect and no sweep
result.

## 4. RNG-stream alignment check (reported)

Changing α changes the *value* of each `rng.beta` draw, not the number of
draws, so at a fixed seed the emesis schedule and the fomite witness should be
**identical** across every α cell. That invariance is checked and reported: if
the emesis witness moves with α, the override has perturbed stream alignment
and the cross-α comparison is confounded (`stochastic-attribution`), which is
reported as such rather than interpreted.

## 5. The two -02 §e observations

`NORO-SUSCEPT-02` §e left two things two seeds could not size: only 1 of 3
scheduled emesis episodes became an emitted event, and a patch localised to a
single-occupancy cabin can have no reachable susceptible at all. By §4 these
are properties of the emesis stream, which α does not perturb — the 14 runs are
7 repeats of 2 draws, not 14 replicates. **This sweep therefore does not size
either observation**, and it is not licensed to change a constant on the
strength of them. They are reported per seed for the record only.

## 6. Instrument

`tools/noro_diag/per_host_dose_challenge.py` is reused, not rewritten. It is
extended additively, and only to make the swept axis and the confirming binary
observable:

- `--alpha` (optional, rejected outside `[0.072, 0.161]`) writes
  `pathogen_overrides = {"norwalk_gi": {"dose_response": {"alpha": α,
  "beta": 32.81}}}`, which `apply_pathogen_overrides` deep-merges onto the
  bundle profile; with no `--alpha` the spec is byte-identical to the -02 run.
- the resolved α/β read back off the run spec are recorded in the output.
- the existing challenge wrapper records the susceptible→infected transition it
  already has the entry state for (`secondaries`, imports, and the epoch and
  dose of each).
- output filenames carry the α so cells cannot overwrite each other.

No engine file, no configuration value and no other constant is touched.

---

## Measured result

**Measured at `f5f9ff3`** — the instrument commit the 14 cells ran on; the two
later commits on the branch (`5c2e896`, and this one) touch documentation only,
and `f5f9ff3`'s tree is the one merged as `707ab14` (PR #618). Per-cell dumps
are left on disk uncommitted under `docs/norovirus/noro_suscept_03/raw/`; every
summary field except the per-host table is committed in
`docs/norovirus/noro_suscept_03/sweep_cells.json` and re-read by
`tools/noro_diag/alpha_sweep_readout.py`, which aggregates and never re-derives.

All 14 cells completed at 288 epochs. No run died and no cell dropped its
override: the resolved α equals the requested α in every cell and β resolves to
32.81 everywhere. The §3 proof passed before the sweep (at 96 epochs rather
than 48, taking the escalation §3.2 allows because the high-α arm drew 185 < 200
frailties at 48: n = 1442 / 1329, median ratio 268.8× against the 10× floor,
KS p = 3.25e-56).

### a. The frozen hard gate held; the frozen §4 invariance did not

**Reconciliation: PASS at every cell, worst relative difference 0.000e+00** —
credited-scaled, dose-read-at-challenge and effective-dose-evaluated agree
exactly in all 14 runs, as they did in -02. The chain -02 closed is still
closed at every α. No harness defect there.

**RNG-stream alignment: FAILED.** §4 predicted that α moves the *value* of each
`rng.beta` draw and not the number of draws, so the emesis and fomite witnesses
would be identical across α at a fixed seed. They are not. At seed 8105 the
emesis witness moves with α in every counter it has — `scheduled_episodes`
reads 3 / 1 / 6 / 3 / 2 / 1 / 1 across the grid and `emesis_events` 1 / 0 / 2 /
1 / 1 / 0 / 0 — and at both seeds all ten fomite counters move
(`deliver_calls`, `mass_requested_gec`, `mass_delivered_to_hands_gec`,
`max_hand_load_gec`, `hand_load_seen_gec`, `hand_to_mouth_calls`,
`hand_to_mouth_dose_gec`, `surface_deposit_calls`,
`surface_mass_offered_gec`, `surface_mass_deposited_gec`). The credited dose
itself — a quantity α cannot touch, because α scales frailty and not dose —
spans 7.11e-8 to 56.620 GEC across the seven α cells at seed 8105, nine orders
of magnitude. The voyages diverge completely.

**The mechanism, measured rather than inferred.** The frailty draw at
`transmission_core.py:2983` is taken from `self.rng`, the run's one shared
generator, which is read at 47 sites in that module — the emesis and fomite
paths among them. NumPy's `Generator.beta` is rejection-based, so the number of
64-bit words it consumes depends on its parameters: 2,000 draws at β = 32.81
consume 8,248 words at α = 0.072 and 8,401 at α = 0.161, monotonically across
this grid (measured directly off the PCG64 counter, seed 12345). Changing α
therefore re-phases every subsequent draw in the run. The frailty count per
cell is itself downstream of that divergence (182 to 1,441 draws). This is the
`stochastic-attribution` RNG-stream disruption case, and §4 says it is reported,
not interpreted: **the shape of the response across the α axis is not readable
from this design.** It is filed as its own defect entry,
`RNG-FRAILTY-STREAM-01`, with the declaration-shaped fix.

### b. The cells

| α | seed | α resolved | secondaries | ever_infected | imports | attack rate | Σ evaluated hazard | credited-scaled GEC | frailty median | frailty mean | hosts for 90% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0720 | 8105 | 0.072 | 0 | 5 | 5 | 0.0 | 3.044e-4 | 19.991 | 8.40e-7 | 2.547e-3 | 1 |
| 0.0720 | 8106 | 0.072 | 0 | 2 | 2 | 0.0 | 1.429e-5 | 0.00416 | 1.08e-6 | 2.577e-3 | 74 |
| 0.0898 | 8105 | 0.0898 | 0 | 5 | 5 | 0.0 | 9.12e-15 | 7.11e-8 | 8.25e-6 | 3.146e-3 | 1 |
| 0.0898 | 8106 | 0.0898 | 0 | 2 | 2 | 0.0 | 1.038e-5 | 0.00260 | 9.79e-6 | 2.908e-3 | 50 |
| 0.1076 | 8105 | 0.1076 | 0 | 5 | 5 | 0.0 | **1.186e-2** | 56.620 | 3.21e-5 | 3.066e-3 | 1 |
| 0.1076 | 8106 | 0.1076 | 0 | 2 | 2 | 0.0 | 1.141e-5 | 0.00271 | 3.61e-5 | 3.496e-3 | 48 |
| 0.1110 | 8105 | 0.111 | 0 | 5 | 5 | 0.0 | 3.809e-4 | 0.10095 | 6.85e-5 | 3.844e-3 | 106 |
| 0.1110 | 8106 | 0.111 | 0 | 2 | 2 | 0.0 | 1.187e-5 | 0.00271 | 4.40e-5 | 3.633e-3 | 48 |
| 0.1254 | 8105 | 0.1254 | 0 | 5 | 5 | 0.0 | 7.15e-3 | 1.787 | 8.65e-5 | 4.093e-3 | 75 |
| 0.1254 | 8106 | 0.1254 | 0 | 2 | 2 | 0.0 | 1.270e-5 | 0.00270 | 1.44e-4 | 3.919e-3 | 48 |
| 0.1432 | 8105 | 0.1432 | 0 | 5 | 5 | 0.0 | 3.27e-5 | 0.0305 | 1.66e-4 | 4.781e-3 | 32 |
| 0.1432 | 8106 | 0.1432 | 0 | 2 | 2 | 0.0 | 8.24e-6 | 0.0122 | 2.68e-4 | 5.101e-3 | 13 |
| 0.1610 | 8105 | 0.161 | 0 | 5 | 5 | 0.0 | 8.58e-5 | 0.0298 | 2.26e-4 | 5.140e-3 | 34 |
| 0.1610 | 8106 | 0.161 | 0 | 2 | 2 | 0.0 | 1.018e-5 | 0.00265 | 3.12e-4 | 6.189e-3 | 51 |

The α = 0.1110 / seed 8105 reference cell reproduces `NORO-SUSCEPT-02` exactly
(0.10095 GEC credited, Σ hazard 3.809e-4, 106 hosts for 90% of dose), which is
the evidence that the instrument's α path is additive: with the shipped α the
cell is the -02 arm.

What is *not* confounded by §a is the frailty distribution itself, because it is
the direct image of the override rather than a downstream consequence of stream
phase. It behaves as the design predicted: the drawn mean rises from 2.547e-3
at α = 0.072 to 5.140e-3 (6.189e-3 at the paired seed) at α = 0.161, against
the `α/(α+β)` prediction of 2.190e-3 → 4.883e-3, monotone and a factor of
**≈ 2.2 across the whole admissible interval**.

### c. The decision

**No α in `[0.072, 0.161]` produced secondary transmission on the classic hull
at 288 epochs.** Secondaries are 0 in all 14 voyages; every infection in every
cell is an import (5 at seed 8105, 2 at seed 8106); the attack rate is 0.0
across the interval, so there is no attack-rate behaviour across the interval to
report. On the primary statistic the maximum over all 14 runs is
**Σ hazard = 1.186e-2**, which is **8.4× below the 0.1 floor of the Marginal
band** and roughly two orders below the Capable band. That is the **Excluded**
verdict of §2.

The §a confound weakens *how* that verdict is supported but does not overturn
it, and the distinction matters:

- Each cell is still a legitimate voyage of the model at its own α — the
  override resolves correctly and the run is internally consistent, including
  its reconciliation. What the re-phasing costs is the *pairing*: the two seeds
  do not pair across α, so the sweep is 14 independent realisations, effectively
  one per α, not 7 paired contrasts.
- Read that way the sweep is *stronger* than the paired design on the magnitude
  question and silent on the shape question. The 14 realisations happen to span
  a dose range the design never asked for — credited dose from 7.11e-8 to
  56.620 GEC, 560× the -02 arm at the top — and the largest Σ hazard anywhere in
  that range is 1.186e-2. A voyage delivering 560× the -02 credited dose, at an
  α inside the interval, still expects 0.012 secondary infections.
- The interval cannot close that gap, and this is the one α statement §a does
  not touch: mean host susceptibility moves 2.2× from end to end (measured
  above), and `NORO-SUSCEPT-01` §4a puts the same move at 7.0× on population
  N50. Two orders of magnitude are missing and the admissible axis is worth
  less than one.

**So the expectation is not wrong in the way α could make it wrong.** The
sourced interval `[0.072, 0.161]` is not the explanation for the absent onboard
secondary transmission, and the suspect moves back to **the dose reaching
hosts** — not the dose-response. The credited dose spread in §b is the place to
look: at seed 8105 the total credited dose over a whole 288-epoch voyage is
under 0.11 GEC in the -02 realisation and the concentration column shows a
single host holding 90% of it in four of the seven cells. Whether that is the
emesis patch localisation, the fomite pickup terms, or the crediting seam is
exactly the `transmission-blocker-cascade` question, and it is not answered
here.

No α is recommended for adoption. No constant moved in this session:
`data/pathogens/active_profiles.json` is untouched, α entered only as a
per-cell `pathogen_overrides` patch on a diagnostic run, and nothing was chosen
against VSP, Park or the passenger/crew ratio.

### d. The two -02 §e observations were not sized

§5 said this sweep would not size them, for the reason that the 14 runs are 7
repeats of 2 emesis draws. §a makes the position worse rather than better: the
emesis stream is not even repeatable across α at a fixed seed, so the 14 cells
are 14 unpaired draws of it. For the record only: at seed 8105
`scheduled_episodes = 3` with `emesis_events = 1` in the reference cell, the
filed and matched unit is `CC_D1_F::cabin1581` and pickups land in ten `CC_D1_A`
cabins; at seed 8106 there is no emesis at all (`scheduled_episodes = None`,
`emesis_events = 0`, identical across α). **Neither observation is sized by this
entry**, and neither licenses a constant change. Sizing them needs replicate
seeds at fixed α, which is a different campaign — and one that `RNG-FRAILTY-
STREAM-01` does not block, because it does not vary α.

