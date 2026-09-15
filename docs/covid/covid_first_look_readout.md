# COVID first look: replicated Theta on Diamond Princess, scored on Greg Mortimer

> **Status:** Findings (2026-09-14). Campaign `covid_first_look_v1`, run on AWS
> Batch at `main` = `654c0a4` (PR #529). 770 of 770 cells completed, zero
> failures. Outputs: `telemetry_buffer/observation_model/covid_theta_fit_v2.json`
> and `covid_theta_held_out_v2.json`. Merge command:
> `python3 tools/fit_covid_theta.py merge --cells <synced cells dir>`.

This replaces the single-seed fit of 2026-09-05 (`covid_theta_fit.json`) as the
current statement of how the COVID arm fits. It is a first look: it tells us
where the misfit is, not what the constant is.

## Design

| | Fit (Phase 1) | Held-out (Phase 2) |
|---|---|---|
| Hull | `diamond_princess_2020` (training) | `greg_mortimer_2020` (held out) |
| Grid | 11 half-decade points, Theta = 1e4 .. 1e9 | same grid |
| Seeds | 20, matched across Theta (20200205..24) | 50 (20200315..64) |
| Cells | 220 | 550 |
| Selection | smallest mean loss over seeds, against `covid.T1` + `covid.T3` only | none — scored at the Theta the fit picked, and its two neighbours |

Theta is the composite `respiratory emission scale x per-copy risk`; it is not
split into its factors and no beta is reported. Held-out cells carry no loss;
they were run alongside the fit for wall-clock reasons and could not influence
selection.

## Phase 1: the loss curve is now a curve, and it is not close

Per-Theta medians over 20 seeds (Diamond Princess, 32 days):

| Theta | recorded onsets | onsets before 6 Feb | campaign positives | specimens | loss (mean) | P(takeoff) | wins (paired bootstrap) |
|---|---|---|---|---|---|---|---|
| 1e4 | 178 | 59 | 118 | 2412 | 6.58 | 1.00 | 0.00 |
| **3.16e4** | **424** | **122** | **288** | **2252** | **3.27** | **1.00** | **0.82** |
| 1e5 | 894 | 207 | 564 | 1977 | 4.30 | 1.00 | 0.18 |
| 3.16e5 | 1273 | 312 | 738 | 1699 | 6.52 | 1.00 | 0.00 |
| 1e6 | 1648 | 453 | 833 | 1427 | 8.54 | 1.00 | 0.00 |
| 3.16e6 | 1941 | 608 | 712 | 1167 | 9.41 | 1.00 | 0.00 |
| 1e7 .. 1e9 | 1995 .. 2177 | 719 .. 1149 | 624 .. 369 | 1034 .. 676 | 9.5 .. 9.8 | 1.00 | 0.00 |
| *observed* | *197* | *34* | *634* | *3063* | | | |

- **Selected Theta = 3.16e4**, mean loss 3.27, not boundary-pinned. The paired
  bootstrap over the 20 matched seeds picks 3.16e4 in 82% of resamples and 1e5
  in the other 18%; nothing else ever wins. The selection is real, not a coin.
- **Takeoff is certain at every Theta**, including 1e4 (20/20 seeds exceed
  10 recorded onsets). The single-index-case extinction branch the plan worried
  about does not occur on this hull with this boarding configuration. The
  non-monotone single-seed curve of 2026-09-05 was seed noise on top of a
  different engine (see below), not extinction.
- **No Theta reaches the anchors, because the two training anchors pull in
  opposite directions.** `covid.T1` (197 onsets) is matched near Theta = 1e4;
  `covid.T3` (634 positives of 3063 tests) is matched near 1e5–3e5. At every
  Theta the model produces *more onsets than positives* (ratio ~1.5:1), where
  the ship produced three positives per recorded onset. The winner sits in the
  gap and misses both: 424 onsets (2.2x) and 288 positives (0.45x).
- **The early trajectory is too fast.** Onsets before 6 February are 59 at the
  lowest Theta and 122 at the winner, against 34 observed, while the total is
  near or above target. The model front-loads the epidemic relative to the
  ship: whatever is boarding infects too many people too early, or the
  incubation-to-onset delay is too short, or both. This is the
  boarding/index-age axis the plan declared and did not fit (Phase 1b), and it
  now has a number attached.
- **Specimens fall as Theta rises** (2412 -> 676) because symptomatic hosts
  leave the campaign-testing pool. The observed campaign ran 3063 tests; the
  model never reaches it. The testing-campaign observation process undercounts
  the real schedule independently of transmission.
- **Asymptomatic share among positives is 0.96–0.97 at every Theta**, against
  0.50 observed (`covid.T4`, a training diagnostic, not in the objective). This
  is flat in Theta, so it is not a transmission-scale problem; it is the
  respiratory arm's symptomatic-fraction / detection representation.

## Phase 2: Greg Mortimer at Theta = 3.16e4 (50 seeds)

| | Theta 1e4 | **Theta 3.16e4 (scored)** | Theta 1e5 |
|---|---|---|---|
| P(no positives) | 0.60 | **0.52** | — |
| P(takeoff, >=10 onsets) | 0.12 | **0.26** | — |
| campaign positives, median (5–95%) | 0 (0–6) | **0 (0–21)** | — |
| `covid.H1` positive share 0.59: hit/miss/undefined | 0/50/0 | **0/50/0** | — |
| `covid.H2` asymptomatic share 0.81: hit/miss/undefined | 1/19/30 | **0/24/26** | — |
| `covid.H3` share of seeds above cross-ship IQR (target 0.015) | 0.12 | **0.26** | — |

(The 1e5 neighbour is in `covid_theta_held_out_v2.json` `sensitivity`.)

- **H1 misses in 50 of 50 seeds.** The observed Greg Mortimer was 128 positives
  of 217 tested; at the fitted Theta the model produces a median of zero and a
  95th percentile of 21. The earlier "0/160" was not an unlucky draw: half of
  all seeds produce no positives at all, and no seed comes within a factor of
  five of the ship.
- **Extinction dominates on the small hull.** P(takeoff) is 0.26 at the fitted
  Theta. Diamond Princess (3,711 aboard) always takes off; Greg Mortimer (223
  aboard) usually does not. The same Theta gives certainty on one hull and a
  one-in-four on the other, which is what a single-import stochastic start
  should do, and is the reason a held-out verdict needs 50 seeds to state.
- **H3 is the one anchor the model is in range of**: 26% of seeds place Greg
  Mortimer above the Willebrand cross-ship IQR (0.03%–1.5% attack rate). The
  observed ship was far above it (57%), so "in range" here means the model
  puts a small hull in the bulk of the cross-ship distribution, which is where
  most of the 104 Willebrand voyages actually sit. That is consistent with the
  secular baseline point: most hulls in 2020 saw a handful of cases, and the
  detailed-trajectory hulls (Diamond Princess, Greg Mortimer, Ruby Princess) are
  the tail, not the centre.

## What changed since the 2026-09-05 single-seed fit

The recorded single-seed fit found Theta = 1e6 with 289 onsets at seed
20200205. The same cell at `654c0a4` produces **1,795 onsets** on the Batch
worker and **1,718 onsets** rerun locally. The first reading of that gap —
that shared norovirus-side engine changes had shifted the COVID arm's
effective scale by more than a decade, and that some unseeded entropy made the
cell host-dependent — was checked after the campaign (2026-09-14) and **both
halves were wrong**. What the controlled reruns show:

**The 289-onset artifact is not reproducible from its own commit.** Checking
out `b38e5ba` (the commit that wrote `covid_theta_fit.json`) and rerunning the
identical cell gives **2,098 onsets** under CPython 3.11 and **2,159** under
3.12, with the same `uv.lock` (numpy 2.5.0, scipy 1.18.1). The artifact's
grid is also internally odd: at every one of its six Theta values it reports
0–5 onsets before 6 February against 100–880 campaign positives, a pattern no
rerun at any commit produces. Whatever produced that file — an uncommitted
tree, a different data directory, a mis-recorded run — is not in the
repository history. `covid_theta_fit.json` is not evidence about a previous
engine; it is a record of unknown provenance, and this readout supersedes it.

**The cell moved between `b38e5ba` and `654c0a4` by ~15%, not a decade — and
one seed cannot say which commit moved it.** Same cell, same interpreter
(3.11): 2,098 → 1,795 recorded onsets; by day 17 (a 408-epoch truncation)
707 → 502. A first-parent bisection of the truncated cell over the 86 merges
in between read 707 (`9fafcc9`, #443), 604 (`3fff70c`, #486), 569
(`461be35`, #496), 502 (`bd634e2`, #507), 502 (`654c0a4`, #529): a graded
drift with no single step. That is the expected shape once the interpreter
result below is understood — a last-bit change anywhere in a dose re-rolls
every later Bernoulli draw, and that alone moves this cell by 5–13% (1,718 vs
1,795; 85 vs 96 on Greg Mortimer). Any commit that touches a float on the
transmission path re-rolls the trajectory, so a single-seed bisection cannot
separate "the engine's scale changed" from "the same engine took a different
path". Attributing a move to a commit needs the 20-seed distribution, i.e. a
Diamond Princess Theta-grid cell rerun at the candidate commit, which is a
Batch job rather than a local probe. The bisection was stopped there.

**1,795 vs 1,718 is the interpreter, not an entropy leak.** The Batch image
runs CPython 3.11; the local venv runs 3.12. Each interpreter is
bit-reproducible on its own (repeated runs, and a 3.11 venv on the local host
matching the Batch worker exactly); swapping numpy 2.5.0 ↔ 2.4.6 and scipy
1.18.1 ↔ 1.17.1 changes nothing. CPython 3.12 switched builtin `sum()` on
floats to compensated (Neumaier) summation, and the route-dose, shedding and
aerosol totals in `engines/transmission_core.py` (near lines 3120, 3128, 3830,
3952, 4972) go through `sum()`; a last-bit change in a dose moves the next
Bernoulli draw, and the two trajectories diverge from there. Same seed, same
code, two deterministic paths. The Greg Mortimer cell at Theta = 1e6, seed
20200333 reads 96/52/106/36/36 (onsets, pre-split, specimens, positives,
asymptomatic) on 3.11 and 85/51/102/30/30 on 3.12.

**The change-detector cell now exists:**
`tests/test_covid_hull_change_detector.py` pins that Greg Mortimer cell in the
fast tier, keyed by interpreter minor version (CI runs both 3.11 and 3.12),
alongside bounds and same-seed reproducibility checks. It is labelled a
change detector, not a correctness check: a move must be attributed to a part
of the diff before the pin is updated. Greg Mortimer rather than Diamond
Princess because it is the held-out hull (pinning it leaks nothing into the
fit) and costs ~25 s rather than ~18 min.

**On the norovirus parallel.** Nothing here shows that the COVID
early-trajectory excess (122 vs 34 onsets before 6 February) shares a
mechanism with the norovirus ignition/posting floor, whose documented cause is
the hand-route normaliser — a route the COVID arm does not use. The two share
a symptom (the model ignites and runs too readily). The 289 → 1,795
comparison, which looked like the strongest sign of a shared lever, does not
survive; what remains is the direct evidence — the early trajectory is 2–4x
too fast at every Theta, across 20 seeds — and that points at the boarding
axis (Phase 1b) and the observation process, not at inherited norovirus
changes.

## What this first look does and does not say

It says:

1. The fit is well-posed as a selection problem — 20 matched seeds pick one
   grid point 82% of the time — and the campaign machinery (770 cells,
   idempotent S3 writes, training-only selection, held-out scoring at merge)
   works end to end.
2. The composite Theta cannot fit Diamond Princess. Onsets and positives
   disagree by a factor of ~5 in their preferred Theta, the early trajectory is
   2–4x too fast, and the asymptomatic share is wrong by a Theta-independent
   factor of two. Those are three separate structural misfits, none of which a
   one-dimensional scale can absorb.
3. Greg Mortimer is not reproduced at any nearby Theta, and mostly does not
   take off at all.

It does not say what Theta is. No value from this campaign should be quoted as
an estimate of the composite, and nothing here bears on emission magnitude or
per-copy risk separately.

## Next steps, in the order the evidence suggests

1. **Engine change-detector for the COVID arm** — done (above).
2. **Phase 1b, the declared boarding axis.** Index infection age at boarding
   and 1 vs 3 imports, screened at the fitted Theta and its neighbours, scored
   on onsets-before-6-Feb vs total. The early-trajectory excess is the
   diagnostic that axis is meant to move.
3. **The onset/positive ratio.** The model detects fewer positives than
   onsets on a ship whose testing found three positives per onset. Before any
   refit, establish whether the campaign-testing observation process reaches
   the published schedule (3,063 tests) and whether asymptomatic infections are
   being tested at all — the 0.96 asymptomatic share says they are being
   *produced*, so the shortfall is in who gets swabbed.
4. **Phase 3 (cross-ship import rate by embarkation date)** only after 1–3;
   the H3 result says the small-hull centre of the distribution is roughly
   where the model already puts it, so the secular-shift question is about the
   tail, and the tail is what items 2 and 3 are about.

## Reproduction

```bash
# Devin session: --profile picard. Local operator machine: --profile
# PowerUserAccess-994254241749.
aws --profile picard --region us-east-1 s3 sync \
  s3://<bucket>/campaign/covid_first_look_v1/cells/ /tmp/covid_cells/
python3 tools/fit_covid_theta.py merge --cells /tmp/covid_cells/
```

Batch job ids: held-out `d37659e1-739d-4bd3-b88d-75b34b0c5246` (11 children,
stride 50), fit `b149e9de-68c4-4ba8-8a77-6dd94e6efddd` (220 children, stride 1),
job definition `picard-covid-hull:1`, image
`picard-campaign:covid-first-look-v1`, queue `picard-campaign-queue`. Fit cells
took roughly one hour each on the shared Spot fleet; the whole campaign ran in
under three hours wall-clock.
