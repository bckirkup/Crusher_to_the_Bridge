# NORO-SUSCEPT-03
**Date:** 2026-09-19
**Commit:** 46cff41
**Pathogens:** norwalk_gi
**Status:** open

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

*(This section is written after the sweep, with `Measured at: <SHA>`. It is
empty at the commit that freezes the design above.)*
