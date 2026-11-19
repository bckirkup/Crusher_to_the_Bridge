# ROOM-AIR-PAIRED-VALIDATION-01: frozen paired design

> **Status:** Design, frozen before any run (2026-11-19, pinned to
> `74a6eff3ec45734b377acb07afe287ca6298f02f`). Ledger
> [`ROOM-AIR-PAIRED-VALIDATION-01`](../ledger/ROOM-AIR-PAIRED-VALIDATION-01.md).
> **Nothing here is a result and nothing here authorizes a run.** No
> simulation, smoke, canary, AWS job, fit or constant change was made to
> write it. The numbers in §9 are synthetic.

Settled inputs, not re-derived:
[`CONTAM-PHASE3-BASELINE-01`](../ledger/CONTAM-PHASE3-BASELINE-01.md), its
[handoff](../audits/2026-11-19_phase3_transport_baseline/README.md), the
[gate brief](../proposals/phase3_epidemiology_gate_decision_brief.md) and
[`ROOM-AIR-01-AMBIENT-EXCHANGE-01`](../ledger/ROOM-AIR-01-AMBIENT-EXCHANGE-01.md).
Transport is numerically verified; there is no as-built or outbreak validation.

## 1. Question and claim boundary

Within the respiratory model at one pinned revision, does adding the declared
ambient exchange to the room-air removal map shift whole-hull infections in
the protective direction by more than seed-to-seed variation?

A PASS is a statement about this model at this revision on one hull and one
profile. It is not evidence about a real ship, a real outbreak, any other
hull, or where on a ship exposure occurs. See §8.

## 2. Arms, cell and version pin

| Item | Frozen value |
|---|---|
| Profile | `sars_cov2_resp` |
| Scenario / hull | `greg_mortimer_2020` on `expedition_cruise_450`, full voyage |
| Reference arm | `ambient_off`: HVAC-only room-air map (labelled pre-change baseline) |
| Intervention arm | `ambient_on`: shipped map, positive `ambient_openings` exchange added |
| Emission scale | `theta = 1e10`, inherited from `ROOM-AIR-01-AMBIENT-EXCHANGE-01`; not calibrated, not selected on outcome |
| Everything else | identical between arms, at platform and profile defaults |
| Revision | one git SHA, one platform tree, one interpreter image digest for every run; recorded per run |

The scenario is used as a model-internal contrast only. No arm is scored
against the observed Greg Mortimer outbreak or any other anchor. If the
executing revision differs from the pin in `engines/`,
`picard_framework/simulation/`, the scenario file or the hull's platform
directory, this design is re-pinned by a docs amendment before any run.

## 3. Primary endpoint, estimand and direction

- **Endpoint** \(Y\): `cumulative_ever_infected` at voyage end, whole hull,
  one integer per run. It is an aggregate count with no zone, cabin or person
  breakdown.
- **Paired difference** \(d_i = Y_{\text{on},i} - Y_{\text{off},i}\) for
  seed \(i\).
- **Estimand** \(\Delta = E[d]\) over seeds at the pinned cell, with the
  relative form \(R = \sum d_i / \sum Y_{\text{off},i}\) (ratio of sums, so
  zero-count pairs need no special handling).
- **Direction**: protective means \(\Delta < 0\). The test is one-sided in
  that direction; the opposite tail is always computed and reported.

Secondary, reported for every pair and never selected on:
`cumulative_ever_infected_passenger`, `cumulative_ever_infected_crew`,
`recorded_onsets`, `campaign_positives`, `infections_by_dominant_route`,
`infection_dose_share_by_route`. No verdict is drawn from them.

## 4. Seeds, pairs and missing data

- **Stage 1 seeds**: `20261901`–`20261920`, the same seed on both arms.
  Seeds `20200333` and `20200334` are excluded because their outcomes were
  already seen.
- **Stage 2 reserve**: `20261921`–`20261960`, used only by a separate owner
  decision after a stage-1 INCONCLUSIVE, in order, all forty.
- **Twenty complete pairs is a diagnostic floor.** It is not a power
  calculation and guarantees no detection probability.
- A pair is **complete** when both arms reach the full horizon, emit the
  endpoint and carry identical provenance.
- An infrastructure loss (host reclaimed, upload failure) is rerun once with
  the same seed and pin, without reading the surviving arm's outcome.
- No replacement seeds. No pair is dropped for its outcome.
- A model exception in exactly one arm of a pair is informative missingness:
  STOP (§7).
- Any declared pair of the stage still incomplete after its rerun (all 20
  at stage 1, all 60 at stage 2): verdict INCOMPLETE, no inference. The
  test is never run on a subset.
- A K0 or K1 control output still missing after its one rerun is likewise
  INCOMPLETE; the primary contrast is not read.

## 5. Statistical rule

All arithmetic is exact on integers; zero differences (ties) stay in the
sample and are counted, not discarded.

1. **Primary test**: exact paired sign-flip randomization test on
   \(T = \sum d_i\). The reference distribution is all \(2^n\) sign
   assignments of the observed \(|d_i|\), computed by exact convolution.
   \(p_{\text{prot}} = P(T^\* \le T)\), \(p_{\text{adv}} = P(T^\* \ge T)\).
2. **Tie and sparsity guard**: let \(m\) be the number of nonzero pairs. The
   smallest attainable one-sided p is \(2^{-m}\). If \(m < 7\) the rule
   cannot reach the stage threshold and the verdict is INCONCLUSIVE
   regardless of \(T\).
3. **Sensitivity check**: exact one-sided binomial sign test on
   \((n_-, n_+)\) with ties excluded. It must agree in direction
   (\(n_- > n_+\)) for a PASS; its p-value is reported, not thresholded.
4. **Error budget**: each direction is tested one-sided at 0.025 across
   both looks, split 0.0125 at stage 1 (20 pairs) and 0.0125 at stage 2
   (all 60 pairs pooled). The chance of a false PASS is bounded at 0.025
   and of a false FAIL at 0.025; the chance of either false directional
   verdict is bounded at 0.05, not 0.025. No other looks.
5. **Descriptive interval**: 95% percentile bootstrap over pairs for
   \(\Delta\) and \(R\) (10,000 resamples, analysis seed `1326`). Reported
   with every verdict; it does not decide the verdict.

What the test separates: its null is that \(d\) is symmetric about zero,
which is what direction-free trajectory divergence produces (§8). A rejection
is a directional shift in the model. Failing to reject is never "no effect".

The test does not by itself show \(\Delta < 0\). A skewed distribution
(many small decreases, rare large increases) can be asymmetric with a mean
near zero. A PASS therefore claims a directional shift only. If the
bootstrap interval for \(\Delta\) in item 5 includes zero, the PASS is
labelled "direction supported, mean reduction not bounded away from zero";
the verdict itself does not change.

## 6. No-change control and contrast witness

**Controls** (both must hold before the primary contrast is read):

- **K1, inert-toggle control.** Same hull, scenario, theta and the 20
  stage-1 seeds, with `transmission.room_air_removal.mode: sealed` on both
  arms. Under `sealed` the residence factor is 1.0 whatever the map holds, so
  `ambient_off` and `ambient_on` must give identical values on every
  endpoint in §3 in all 20 pairs. Expected count of non-identical pairs: 0.
- **K0, repeat control.** `ambient_on` at default settings run twice for
  seeds `20261901` and `20261902`; both repeats must be identical.

**Witness** that the contrast existed and was encountered, as whole-hull
scalars only (no zone names, ranks or per-zone values are reported):

| Witness | Definition | Requirement |
|---|---|---|
| W1 existed | number of zones whose room-air rate differs between arms, plus the minimum and median residence-factor ratio | count ≥ 1 |
| W2 encountered | \(E\): susceptible person-hours spent in W1 zones, `ambient_off` arm, summed over zones; \(Q\): room-pool airborne dose delivered in W1 zones as a share of all airborne-route dose, `ambient_off` arm | \(E > 0\) in every complete pair; median \(Q\) reported |
| W3 diverged | number of pairs with any non-identical §3 field | reported; ≥ 1 expected if W2 holds |

\(Q\) bounds what the intervention can remove. If median \(Q < 0.01\), an
INCONCLUSIVE is labelled "contrast barely encountered" and stage 2 is not
recommended. The 0.01 line is a design declaration, not a physical constant.

## 7. Verdict rules

Evaluated in this order at each stage.

| Verdict | Condition | Consequence |
|---|---|---|
| **STOP** | K1 or K0 shows any non-identical pair; W1 count is 0; \(E = 0\) in any complete pair; provenance differs between arms or across pairs; a model exception in exactly one arm | No effect is read. Report the cause as a model or harness finding |
| **INCOMPLETE** | any declared pair of the stage (20 at stage 1, 60 at stage 2) or any K0/K1 control output still missing after its rerun | No inference; the test is not run on a subset |
| **PASS** | \(p_{\text{prot}} \le 0.0125\), sign test agrees in direction, W2 holds | "Directional protective shift in the model at this cell", with \(\Delta\), \(R\), interval, \(m\), \(Q\), and the mean-reduction label of §5 |
| **FAIL** | \(p_{\text{adv}} \le 0.0125\) | Adverse-direction finding. Stop; no extension; investigate before any further respiratory run |
| **INCONCLUSIVE** | anything else, including \(m < 7\) | "Not separable from random variation at n pairs." Not evidence of absence. Stage 2 only by owner decision |

No threshold, seed list, endpoint or direction changes after any outcome is
seen. A verdict from one hull and one profile is a hypothesis about any
other.

## 8. RNG and model limitations versus real-world effects

- **Common random numbers, not coupled trajectories.** Arms share a seed, and
  the map toggle is deterministic arithmetic that draws no random numbers
  (inferred from code reading at the pin; K1 is the check). Once one
  infection outcome differs, later draws meet different states and the
  trajectories diverge. Per-pair differences therefore contain divergence
  noise as well as any effect; a single pair shows nothing.
- **The earlier 5–13% single-seed band** was measured across interpreters
  and is not used as a threshold here. The paired distribution replaces it.
- **Interpreter.** Every run uses one image digest. Local and Batch numbers
  are never mixed.
- **Model scope.** The intervention scales room-pool dose by the epoch-mean
  residence factor in zones with positive declared exchange. It does not
  change inter-zone transport, ContamX fields, occupancy or behaviour.
  Exchange rates are Grade C declarations, not measurements from a vessel.
- **Real world.** No pressure, ventilation, tracer or outbreak observation
  enters this design. A PASS does not show that opening decks protects
  people; a FAIL or INCONCLUSIVE does not show that it does not.
- **Rare events.** If most voyages extinguish, most \(d_i\) are zero and
  the guard in §5 returns INCONCLUSIVE rather than a spurious null.

## 9. Synthetic worked example

Invented differences, 20 pairs each, to show the arithmetic only.

| Example | \(T\) | \(n_- / n_+ / \text{ties}\) | \(p_{\text{prot}}\) | Sign test p | Verdict |
|---|---:|---:|---:|---:|---|
| A: −4 −2 0 −7 3 −1 0 −5 −2 1 −3 0 −6 2 −1 −4 0 −2 −3 1 | −33 | 12 / 4 / 4 | 0.0076 | 0.038 | PASS if controls and witness hold |
| B: −9 4 0 −3 6 0 −1 5 −6 2 0 −4 3 −2 7 0 −5 1 −1 2 | −1 | 8 / 8 / 4 | 0.50 | 0.60 | INCONCLUSIVE |
| C: sixteen zeros, −1 −2 1 −1 | −3 | 3 / 1 / 16 | 0.25 | 0.31 | INCONCLUSIVE (\(m = 4 < 7\)) |

## 10. Observables: verified or blocked

Checked by reading the tree at the pin; nothing was executed.

| Need | State at the pin |
|---|---|
| `cumulative_ever_infected` and group splits | Present in the run summary (`orchestrator_record.py`) |
| Route counts and dose shares | Present in the run summary |
| `recorded_onsets`, `campaign_positives` | Present in `HullObservables` |
| W1 changed-zone count and ratio summary | Computable from `map_census` in `tools/room_air_ambient_exchange_attribution.py` |
| `sealed` mode for K1 | Present: `transmission.room_air_removal.mode` |
| **B1** arm selection | **Implemented and unit-tested in PR #1329; not campaign-validated.** `transmission.room_air_removal.map_arm` (`ambient_on` default, `ambient_off` baseline) is echoed as `room_air_map_arm` in the run summary. Neutrality was shown on synthetic fixtures only; K0/K1 on paired voyages are unmeasured. At the pin: `ambient_off` existed only as a patch inside the attribution tool |
| **B2** primary endpoint in the paired reader | **Blocker.** `HullObservables` and the paired tool carry onset and specimen fields only, not `cumulative_ever_infected` |
| **B3** W2 scalars \(E\) and \(Q\) | **Implemented and unit-tested in PR #1331; not campaign-validated.** W1 count and \(E\) as defined in §6. \(Q\) is reported as a proxy under the owner-authorized amendment in §11, not as defined in §6. Shown on synthetic fixtures only; no voyage was run. At the pin: no per-run aggregate of occupancy or delivered dose in the changed zones existed |
| **B4** second hull | **Blocker for any naval or cross-hull statement only.** No respiratory scenario exists on `destroyer_baseline`; scenarios cover `mega_cruise_5000` and `expedition_cruise_450`. K1 is the no-change control for this design |

B1–B3 must be closed, each as its own reviewed change with K1-style
neutrality shown, before the campaign-preflight sequence (smoke, dry run,
canary) can begin. None is implemented here.

## 11. Addendum: owner-authorized amendment to the reported Q (PR #1331)

Added after the freeze. §6 is left as written; this section records what is
reported in its place for \(Q\) and why. Thresholds, seeds, endpoint,
direction, the statistical rule and the verdict rules are unchanged. \(Q\)
is report-only in §6 and §7; the W2 gate is \(E > 0\).

**Why.** §6 defines \(Q\) as room-pool airborne dose delivered in W1 zones
as a share of all airborne-route dose. The tree has no such split: the
`droplet` pathway key carries room-pool and near-field dose together, and
the caregiver and cabin-service channels carry their air terms under the
same key as their other terms. Reading the §6 quantity exactly would mean
instrumenting about seven dose sites in the engine.

**Owner decision (Benjamin, 2026-11-18):** "Use the labelled upper-bound Q".

**What is reported.** With \(D\) the credited dose on the `droplet`,
`hvac_airborne`, `emesis_aerosol` and `flush_aerosol` pathways, hull-wide,
and \(D_W\) the part of it received by hosts located in W1 zones, the run
summary carries \(Q' = D_W / D\) as
`room_air_witness.airborne_dose_share_changed_zones_proxy`, with \(D\),
\(D_W\) and the caregiver-channel dose total \(C\) beside it. Numerator
and denominator use the same per-host pathway dose, after route-efficiency
and NPI factors, summed over the active pathogens.

**What the bound is, and is not.** Room-pool dose on those four pathways in
W1 zones is part of \(D_W\), so \(Q'\) is at least the room-pool share of
\(D\). It is an upper bound on the §6 \(Q\) in a run where \(C = 0\),
reading "all airborne-route dose" as at least those four pathways. When
\(C > 0\) the bound is not established: caregiver-channel air dose in a W1
zone is in the §6 numerator and absent from \(D_W\). In that case \(Q'\)
is a proxy only, and a readout must say so. The median reported under §6 is
the median of \(Q'\), labelled as the proxy.
