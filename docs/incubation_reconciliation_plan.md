# Incubation reconciliation plan

Scope: everything in the repository that encodes "how long after exposure does a
case appear", now that PR 290 made incubation a per-infection draw for two
pathogens. Written to answer three questions in order:

1. what has to be reconciled,
2. whether a re-fit is pressing,
3. whether anything on `main` needs major adjustment.

Measurements quoted below were taken on `paper3-variant-surveillance` at
`eadcef1` (`expedition_cruise_450`, norovirus, 168 epochs, 5 seeds per arm,
incubation block present vs stripped).

A fourth representation surfaced later, in the *units* rather than the
distribution: the ABM advances its day-scale clocks once per hourly epoch. See
[`epoch_time_unit_audit.md`](epoch_time_unit_audit.md); it changes the size of
every effect measured below without changing which representation is which.

## 1. There are three incubation representations, not one

| # | Where | Form | Consumers |
|---|-------|------|-----------|
| A | `data/pathogens/active_profiles.json` `incubation` block, read by `engines/incubation.py` | per-infection lognormal draw, dose- and host-conditioned, truncated | symptom onset in `orchestrator_epoch`, hence syndromic sick call, clinical instrument day-since-onset, escalation counts, sentinel `onset_epoch` |
| B | `picard_framework/analysis/sentinel/data/incubation_distributions.json` | pathogen-level lognormal in *hours*, discretized to the epoch grid | Stan attribution likelihood, right-censoring factor, Richardson-Lucy back-calculation, port-resolution criterion (spec 1.8), MDHR |
| C | `ONSET_DAY` fallback in `orchestrator_epoch._incubation_days` | fixed 1.0 day | every profile without an `incubation` block |

Representation C still covers the remaining fixed-onset profiles, including
`measles_virus`, `ebola_virus`, and `legionella_pneumophila` in
`edison_10pathogen_profiles.json` — all of which currently present symptoms one
day after exposure. `norwalk_gi`, `sars_cov2_resp`, and now `influenza_a` use A
in their respective shipped bundles.

A and B remain separate representations, but linked entries in B are projected
from the active profiles and checked for drift. Edison-only profiles such as
`influenza_a` are outside that linked Sentinel catalog scope.

## 2. What the measurements show

**A vs C (simulator behaviour).** Ever-infected is unchanged within noise, but
symptomatic person-epochs inside the 7-day window fall 5–12% at fixed
`dose_adjustment` (672 → 638 at `dose_adjustment=3`; 381 → 336 at 7). The
observable the VSP calibration targets moved; the epidemic size did not.

**Dose coupling runs along the calibration axis.** Realized dose factors and
onsets, instrumented inside a real voyage:

| `dose_adjustment` | median simulated dose (particles) | median dose factor | median realized onset |
|---|---|---|---|
| 3 | 3.6e6 | 0.72 (some hosts at the 0.30 floor) | 0.85 d |
| 7 | 6.1e3 | 1.05 | 1.22 d |

Before PR 290 onset was 1.0 d at every point of that sweep. The map
`dose_adjustment → observed case curve` therefore changed *shape*, not only
level, and `dose_adjustment` is exactly the parameter
`calibration_manifest_v1.json` sweeps to match CDC VSP AGE rates.

**A vs B (kernel mismatch), on a 1-hour grid:**

| Kernel | median | mean | IQR |
|---|---|---|---|
| B, norovirus (33 h, σ 0.42) | 33 h | 35.9 h | 19 h |
| A at dose factor 1.0 | 28.8 h | 31.8 h | 17 h |
| A at dose factor 0.72 (`dose_adjustment=3`) | 20.7 h | 22.9 h | 12 h |
| A at the 0.30 floor | 8.6 h | 9.5 h | 5 h |

Two consequences. First, PR 290 *reduced* the headline mismatch — the previous
data-generating process was a fixed 24 h spike against a 33 h lognormal kernel.
Second, it introduced a dependence B cannot represent: the attribution kernel's
IQR is now a function of dose, and the port-resolution criterion (spec 1.8,
`IQR < min inter-port interval`) is evaluated against a fixed 19 h. In a
high-dose regime the true IQR is 5–12 h, so ports are *more* separable than the
catalog claims; in a low-dose regime, less.

The sentinel synthetic validation suite generates onsets from B and fits with B,
so it is self-consistent and unaffected. Only pipelines that feed a
CTB-generated line list into a Stan fit are exposed.

## 3. Reconciliation work items

Ordered by dependency. Sizing is in Devin sessions.

**R1 — one source of truth for pathogen delay parameters (1 session). DONE.**
Make B a projection of A rather than a parallel file: derive
`median_hours`/`sigma` for the sentinel catalog from the profile's
`incubation` block at build time, with a test that fails when they drift. Keep
B's `generation` and `shedding` kernels where they are — they are not incubation
and A does not carry them.

Delivered in `picard_framework/analysis/sentinel/profile_delays.py`: catalog
entries carrying `pathogen_id` are projections of that profile
(`median_hours = median_days * 24`, `sigma = log(dispersion)` because the profile
states a geometric standard deviation, `min_hours`/`max_hours` from the profile's
clamps), and `tests/test_sentinel_profile_delays.py` fails on any drift, on a
`pathogen_id` naming a profile the bundle lacks, and on a linked profile that
loses its incubation block. `lognormal_delay` gained left truncation so the
profile's `min_days` survives the projection instead of being dropped. Catalog
entries without `pathogen_id` (measles) stay sentinel-side and unchecked.
Consequence: the bundled norovirus kernel moved from 33 h / IQR 19 h / 120 h of
support to 28.8 h / IQR 17 h / 144 h, and `sars_cov2` gained an entry
(IQR ~86 h — `port_resolution: inadequate`, so single-onset port attribution is
not available for it at cruise inter-port intervals).

**R2 — state the dose-conditioning contract for the analysis side (1 session).**
The Stan kernel is pathogen-level by construction. Options, in preference order:
(a) document that the analysis kernel is the *marginal* incubation over the
run's realized dose distribution, and compute it from the run rather than the
catalog; (b) keep the catalog kernel and record the induced bias; (c) condition
the kernel on a run-level dose summary. Deliverable is a decision plus the
port-resolution criterion re-derived under it.

**R3 — incubation blocks for the remaining 13 profiles (1–2 sessions).**
`docs/ctb_incubation_spec.md` already carries literature values for influenza,
measles, Legionella, Vibrio, Campylobacter, C. difficile, hantavirus, and
Ebola. Until this lands, any multi-pathogen result is quoting a 1-day
incubation for measles. This is the largest fidelity gap of the three, and it is
independent of the paper 3 campaign.

**R4 — dose-anchoring calibration (1 session).**
`dose_reference_log10` is currently each profile's beta-Poisson N50 in model
units, chosen so a near-ID50 host sees no shift. The calibration arms sit
~2.3 log10 above it, which is why the median factor at `dose_adjustment=3` is
0.72 with hosts at the floor. Either map model particle units to an assay unit
and re-derive the reference, or bound `dose_log10_shortening` so the reachable
acceleration matches the literature's dose-shift evidence rather than the
floor.

**R5 — regression tests that lock the coupling (0.5 session).**
A graded test asserting realized median onset moves monotonically with
`dose_adjustment` across the calibration sweep range, and a bounds test that the
sentinel catalog IQR and the profile IQR stay within a stated tolerance
(the R1 drift test).

**R6 — re-fit the VSP calibration tier (1 session + compute).**
Re-run `calibration_manifest_v1.json` tier `c1_*` on both arms and publish the
shifted `dose_adjustment` per platform. This is the only item that needs
campaign compute; the four platform tiers are ~1200 runs.

**R7 — SEIQR formalization alignment (0.5 session, only if issue #103 proceeds).**
Issue #103 asks for an SEIQR model or a documented ABM approximation. Its E→I
transition must read A, not the 1-day fallback, or the repository will acquire a
fourth incubation representation.

## 4. Is a re-fit pressing?

Not today; it becomes pressing at two specific moments.

- **Nothing currently published is invalidated.** The monographs, the VSP
  degradation campaign (`dose_adjustment=10.6` pinned), and the synthetic
  recovery campaign were run and documented against the fixed-onset model, which
  is still what `main` contains.
- **It is pressing before any paper 3 campaign arm that reports absolute case
  counts, detection timing, or VSP threshold crossings.** Those numbers are
  ~5–12% low relative to the old calibration at the same `dose_adjustment`, and
  the sweep no longer has a constant onset, so relative comparisons across the
  sweep are also affected. Comparative arms that hold `dose_adjustment` fixed
  and vary a surveillance dial are much less exposed — the incubation change is
  common to both arms.
- **It is pressing before merging `paper3-variant-surveillance` into `main`**, if
  the merge is expected to reproduce existing calibrated behaviour.

## 5. Exposure of work on `main`

`main` is currently `e35b7b6`, which is the branch point plus one skills-doc
commit; it contains none of the incubation change. So there is no live breakage,
and no in-flight PR or branch to adjust (the repository has no open PRs).

What lands at merge time:

| Item | Effect | Severity |
|---|---|---|
| Golden orchestrator / Picard trigger fixtures | unchanged (verified; this constrained the dose reference choice) | none |
| Calibrated `dose_adjustment` values in campaign designs | re-runs will not reproduce prior case counts | moderate, needs R6 |
| CTB → Stan sentinel fits | onset DGP changed; kernel mismatch smaller than before but now dose-dependent | moderate, needs R1/R2 |
| Sentinel synthetic validation, MDHR power tests | self-consistent in B, unaffected | none |
| Remaining fixed-onset profiles | unchanged behaviour, now inconsistent with the three migrated ones | high fidelity debt, needs R3 |
| Published monographs and prior campaign reports | describe the previous model version | none, provided the model version is stated |

**The one decision that changes this table.** Representation A activates
whenever a profile carries an `incubation` block — it is not behind
`variant_surveillance.enabled`. Merging paper 3 therefore changes main-line
epidemiology for norovirus and SARS-CoV-2 at the same commit that adds strain
tracking. The alternative is to gate incubation sampling behind its own flag
(default off on `main`, on for paper 3 runs) so that the re-fit in R6 can happen
after the merge rather than blocking it. Gating costs one seam and keeps two
behaviours alive; not gating costs a campaign re-fit before merge. This is a
project-sequencing call, not a modelling one.

## 6. Recommended order

R3 and R1 first — they are fidelity fixes independent of the campaign and
neither requires compute. R5 alongside them. Then R2 and R4, which together fix
what the dose term is allowed to claim. R6 last, once A is stable, so the
calibration is not re-run twice. R7 only if issue #103 is picked up.
