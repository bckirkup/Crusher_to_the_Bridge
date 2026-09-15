# COVID first look: replicated Theta on Diamond Princess, scored on Greg Mortimer

> **Status:** Findings (2026-09-14). Campaign `covid_first_look_v1`, run on AWS
> Batch at `main` = `654c0a4` (PR #529). 770 of 770 cells completed, zero
> failures. Outputs: `telemetry_buffer/observation_model/covid_theta_fit_v2.json`
> and `covid_theta_held_out_v2.json`. Merge command:
> `python3 tools/fit_covid_theta.py merge --cells <synced cells dir>`.
> **Rerun 2026-09-15** as `covid_first_look_v2` at `main` = `35207bc` (gate
> #537 + shared sanitary zones #538; PR #539): 770/770, zero failures, outputs
> `covid_theta_fit_v3.json` / `covid_theta_held_out_v3.json`; see the v2
> section at the end. Theta and the misfit pattern are unchanged.
> **Withdrawn 2026-09-14 pending rerun.** Every v1, v2 and
> `covid_boarding_screen_v1` cell boarded an undeclared cohort: the ship-wide
> boarding channel (`initiation.boarding.enabled`, default on since 09-11) read
> the `sars_cov2_resp` profile's screening prevalence (1% passengers, 0.6% crew,
> epoch 6) and boarded about 34 hosts on Diamond Princess on top of the one
> declared index case (probe: 25 passengers + 9 crew; 17 never-symptomatic, 15
> convalescent, 2 presymptomatic). Takeoff probability 1.0 at every Theta, the
> early-onset excess, the asymptomatic share, and the 1b result that neither
> infection age nor 1-vs-3 imports moved anything all sit partly on that cohort.
> The hull spec now opts the arm out (`HullScenario._initiation_block`); the
> change-detector cell moved from (53, 15, 217, 74, 39) to (1, 1, 217, 3, 2),
> attributed to that one change. **Reruns landed 2026-09-15** as
> `covid_first_look_v3` (770/770) and `covid_boarding_screen_v2` (180/180),
> zero failures, on `main` = `4de87ba` (#543): see the two sections at the
> end. Everything between here and those sections describes the model *with*
> the undeclared cohort and is kept as the record of what was measured; it is
> not the current statement of the fit.

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
   **Observation-process finding (post-campaign, one cell).** At Theta_fit,
   seed 20200205, CPython 3.12, 102 of 111 pre-6-February onsets were
   confirmed by a passive sick-call swab taken before 5 February — a test the
   ship did not have. The passive channel also skips a host for the campaign
   roster, so symptomatic cases were drained out of the campaign log. The
   scenario record now declares `molecular_ascertainment.start_day` (Diamond
   Princess day 14 = 3 February; Greg Mortimer day 20, the screen) and no
   specimen precedes it. On the change-detector cell (Greg Mortimer, 1e6,
   seed 20200333) this moved onsets 96→68, pre-split onsets 52→14, campaign
   specimens 106→217, positives 36→104 and the asymptomatic share of
   positives 1.00→0.57 (CPython 3.11). The 20-seed grid was rerun under
   the gate as `covid_first_look_v2`; see the section below. The numbers
   above in this readout are the pre-gate v1 numbers.
4. **Phase 3 (cross-ship import rate by embarkation date)** only after 1–3;
   the H3 result says the small-hull centre of the distribution is roughly
   where the model already puts it, so the secular-shift question is about the
   tail, and the tail is what items 2 and 3 are about.

## covid_first_look_v2: the same design on the corrected model

Same grid, same 20 + 50 matched seeds, same objective, same loss; the model
underneath now has the molecular-ascertainment gate (#537, no specimen before
Diamond Princess day 14 / Greg Mortimer day 20) and the shared sanitary-zone
ship model (#538). Image `picard-campaign:covid-first-look-v2` from `35207bc`
(CPython 3.11.16); 770/770 cells, zero Batch failures. Outputs:
`telemetry_buffer/observation_model/covid_theta_fit_v3.json` and
`covid_theta_held_out_v3.json`. Cells pair with v1 by (Theta, seed).

### Phase 1, Diamond Princess (medians over 20 seeds)

| Theta | recorded onsets | onsets before 6 Feb | campaign positives | specimens | asymptomatic share | loss (mean) | P(takeoff) | wins |
|---|---|---|---|---|---|---|---|---|
| 1e4 | 174 | 47 | 107 | 2532 | 0.95 | 8.97 | 0.90 | 0.00 |
| **3.16e4** | **435** | **119** | **303** | **2362** | **0.96** | **3.83** | **1.00** | **0.70** |
| 1e5 | 908 | 191 | 581 | 2051 | 0.96 | 4.38 | 1.00 | 0.30 |
| 3.16e5 | 1341 | 292 | 801 | 1758 | 0.96 | 6.61 | 1.00 | 0.00 |
| 1e6 | 1785 | 428 | 839 | 1453 | 0.96 | 8.98 | 1.00 | 0.00 |
| 3.16e6 | 1941 | 580 | 743 | 1238 | 0.96 | 9.62 | 1.00 | 0.00 |
| 1e7 .. 1e9 | 2041 .. 2093 | 667 .. 1067 | 639 .. 383 | 1098 .. 753 | 0.95 .. 0.93 | 9.9 .. 9.2 | 1.00 | 0.00 |
| *observed* | *197* | *34* | *634* | *3063* | *0.50* | | | |

**Theta is unchanged: 3.16e4** (0.70 of paired-bootstrap resamples; 1e5 the
other 0.30; not boundary-pinned). Paired per-seed at 3.16e4, v2 minus v1:
recorded onsets median −12 (9 of 20 seeds up), onsets before 6 Feb median −6
(8 up), campaign specimens **+140 (18 of 20 up)**, campaign positives −17
(9 up). Only the specimen count moved as a body; everything else is within
seed noise. The mean loss is worse (3.27 → 3.83) because the 95th-percentile
seed got worse (6.8 → 13.4); the median loss is flat (2.15 → 2.20).

**The early-trajectory excess did not move.** This contradicts the
one-cell diagnosis above, and the reason is in how onsets are recorded:
`onset_observation_curve` bins a confirmed host by *onset day*, whenever the
confirmation happens. Closing the passive swab channel until 3 February
delays confirmation of a January onset but does not remove it — the host
keeps presenting at sick call and is swabbed once the ship has a test. That
is the right behaviour (the published 34 is also a retrospective by-onset-date
count), so the v1 diagnostic showed *which channel* confirmed those onsets,
not that they were spurious. The ~120 vs 34 gap is transmission-side (or
boarding-side), not an ascertainment artifact. Item 2 (the boarding axis)
stands as the next lever.

**The asymptomatic share on Diamond Princess did not move either** (0.96 at
every Theta). The gate opens the passive channel on day 14, one day before
the campaign starts, so symptomatic hosts are still swabbed passively first
and still leave the campaign pool. The drain the v1 readout inferred is real
but the gate does not close it on this hull; only a later-starting passive
channel or a campaign that does not skip already-sampled hosts would.

### Phase 2, Greg Mortimer at Theta = 3.16e4 (50 seeds)

| | v1 | v2 | observed |
|---|---|---|---|
| P(no positives) | 0.52 | 0.48 | — |
| P(takeoff, ≥10 onsets) | 0.26 | 0.20 | — |
| campaign positives, median / q95 | 0 / 19 | 1 / 34 | 128 |
| H1 positive share | miss 50/50 | miss 50/50 (median 0.005) | 0.59 |
| H2 asymptomatic share among positives | miss 24/24 defined (median 1.00) | **hit 3, miss 23** of 26 defined (median 0.49) | 0.81 |
| H3 share above cross-ship IQR | 0.26 | 0.28 | 0.015 |

On the held-out hull the gate does what it was meant to: with no passive
swab before the day-20 screen, the campaign is the only observer and it sees
the symptomatic hosts, so the asymptomatic share falls from 1.00 to a
spread centred on 0.49 (still below the observed 0.81, in the other
direction now). Positives roughly double but remain an order of magnitude
short of 128; the hull still goes extinct in half the seeds.

### What v2 says

- The two model corrections did not change the fit or its shape; Theta is
  a compromise between the onset anchors and the positive anchors exactly
  as in v1.
- The early-trajectory excess survives the observation-process fix and is
  now the cleanest evidence that the *boarding* assumptions (index infection
  age, number of imports) are where the model is too fast.
- The asymptomatic-share misfit is a campaign-roster question (who gets
  swabbed by whom first), not an ascertainment-start question.

## covid_first_look_v3: the declared index case, and nothing else

Same grid, same 20 + 50 matched seeds, same objective and loss as v1/v2; the
only change is that the hull spec now opts `sars_cov2_resp` out of the
ship-wide boarding channel (#543), so each Diamond Princess cell starts from
one index case instead of one index case plus a prevalence-drawn cohort of
about 34. Image `picard-campaign:covid-first-look-v3` from `4de87ba` (CPython
3.11.16); 770/770 cells, zero Batch failures. Outputs:
`telemetry_buffer/observation_model/covid_theta_fit_v4.json` and
`covid_theta_held_out_v4.json`. Cells pair with v1 and v2 by (Theta, seed).

### Phase 1, Diamond Princess (20 seeds)

Medians are no longer the useful summary: the surface is bimodal. Recorded
onsets per seed, sorted, at each Theta:

| Theta | recorded onsets, 20 seeds sorted | P(takeoff, ≥10) | loss (mean) | wins |
|---|---|---|---|---|
| 1e4 | 0 ×12, 1 ×6, 4, 37 | 0.05 | 106.1 | 0.00 |
| 3.16e4 | 0 ×12, 1 ×6, 11, 91 | 0.10 | 104.9 | 0.00 |
| 1e5 | 0 ×12, 1 ×6, 47, 185 | 0.10 | 102.4 | 0.00 |
| 3.16e5 | 0 ×8, 1 ×9, 2, 153, 261 | 0.10 | 95.0 | 0.00 |
| 1e6 | 0 ×9, 1 ×6, 2, 4, 5, 309, 381 | 0.10 | 91.5 | 0.00 |
| 3.16e6 | 0 ×7, 1 ×6, 2, 5, 11, 18, 30, 321, 403 | 0.25 | 79.1 | 0.00 |
| 1e7 | 0 ×5, 1 ×7, 2 ×3, 13, 16, 23, 387, 597 | 0.25 | 75.0 | 0.00 |
| 1e8 | 0 ×4, 1 ×5, 2, 3, 3, 4, 4, 6, 20, 23, 37, 448, 724 | 0.25 | 59.8 | 0.01 |
| 1e9 | 0 ×3, 1 ×4, 2 ×4, 6, 8, 8, 21, 22, 51, 161, 628, 979 | 0.30 | 52.0 | 0.94 |
| *observed* | *197 (34 before 6 Feb)* | | | |

**Theta = 1e9, boundary-pinned** (0.94 of paired-bootstrap resamples; 3.16e8
the rest). This is not a fit either, and for the opposite reason to v1/v2:
the mean loss is dominated by the 14–18 seeds that never get past a handful
of onsets (loss ≈ 100 each against ≈ 3 for a seed that takes off), so
selection is chasing takeoff probability up the grid, and takeoff probability
saturates near 0.25–0.30 from 3e6 upward. Five decades of Theta move
P(takeoff) from 0.05 to 0.30.

**Takeoff is decided by the seed, not by Theta.** Two seeds (20200205 and
20200221) take off at every Theta from 1e4 up; seven seeds never exceed 3
onsets even at 1e9. Per-seed shedding multipliers of the index case
(`shedding_variance_log10` 1.2) do not explain it: the two seeds that always
take off drew 57.8 and 2.2, while 20200219 (54.2), 20200214 (28.8) and
20200223 (21.1) never do. Whatever separates them is set at initialisation
and is insensitive to the transmission scale across five decades — which
points at the index case's contact opportunity (cabin, schedule, isolation on
presentation) rather than at emission or per-copy risk. This is the open
question the campaign leaves; it has not been traced.

**Conditional on taking off, the trajectory is now too slow, not too fast.**
Among seeds with ≥10 onsets at 1e5–1e6 (n = 2 each): median onsets before
6 Feb 2–7 vs 34 observed, totals 116–345 vs 197, campaign positives 146–536
vs 634, asymptomatic share 0.89–0.95 vs 0.50. At 3e6–1e9 the taking-off
group (n = 5–6) is a mixture of two large outbreaks (600–980 onsets) and
three or four late clusters of 11–52. The ~120 early onsets of v1/v2 were
the undeclared cohort; with one index the model cannot produce 34 onsets in
the first 17 days from any Theta in the grid.

**The asymptomatic share (0.89–0.97 where defined) did not move.** The
cohort was not its cause; the campaign-roster drain described under v2
stands.

### Phase 2, Greg Mortimer at Theta = 1e9 (50 seeds; 3.16e8 in parentheses)

| | v2 at 3.16e4 | v3 at 1e9 (3.16e8) | observed |
|---|---|---|---|
| P(no positives) | 0.48 | 0.20 (0.24) | — |
| P(takeoff, ≥10 onsets) | 0.20 | 0.04 (0.04) | — |
| campaign positives, median / q95 | 1 / 34 | 3 / 16 (2.5 / 16) | 128 |
| H1 positive share | miss 50/50 | miss 50/50 (median 0.014) | 0.59 |
| H2 asymptomatic share among positives | hit 3, miss 23 of 26 defined | hit 7, miss 33 of 40 defined (median 1.00) | 0.81 |
| H3 share above cross-ship IQR | 0.28 | 0.48 | 0.015 |

At the selected Theta the held-out hull almost never takes off and its
median positive count is 3 of 217 against 128 observed; the H3 figure rises
because a 1e9 scale makes small clusters common on a small hull, not because
the outbreak is reproduced. Across the whole held-out grid P(takeoff) never
exceeds 0.04 and the q95 of positives never exceeds 18 — Greg Mortimer, with
its one declared import, does not produce its outbreak at any Theta.

### What v3 says

- v1 and v2 were fits to the wrong initial condition. Their Theta (3.16e4),
  the "three misfits a single scale cannot absorb", and P(takeoff) = 1.0
  were properties of a ~35-import experiment. They should not be quoted.
- With the declared single index case, the composite Theta is not the lever
  for takeoff at all; it moves the size of an outbreak that has already
  started (37 → 979 onsets across the grid on the seeds that ignite) and
  barely moves whether one starts.
- The record's one identified import is therefore too few for this hull, or
  a within-ship mechanism removes the index case's early contacts, or both.
  The boarding screen below separates the first from the second as far as
  10 seeds allow.

## covid_boarding_screen_v2: index infection age × imports × Theta

Declared axes, not fitted: infection age at boarding {0, 3, 6} d × imports
{1, 3} × Theta {1e4, 3.16e4, 1e5} × 10 matched Diamond Princess seeds
(20200205..14, the first ten of the fit set), shared heads visited
(`dwell_weighted`). 180/180 cells, zero failures, image
`picard-campaign:covid-boarding-screen-v2` from `4de87ba`. Output
`telemetry_buffer/observation_model/covid_boarding_screen_v2.json`. The
sanitary witness is consistent in all 180 cells (declared mode
`dwell_weighted`, visits recorded in every cell). `covid_boarding_screen_v1`
(same grid, undeclared cohort present) is superseded and was never written
up: its surface was flat because every axis was a perturbation on ~35
imports.

| Theta | age (d) | imports | P(takeoff) | onsets before 6 Feb, median / q95 | recorded onsets, median / q95 | first onset day, median | positives, median | asym. share, median |
|---|---|---|---|---|---|---|---|---|
| 1e4 | 0 | 1 | 0.10 | 0 / 1 | 0 / 19 | 17 | 0 | 0.00 |
| 1e4 | 0 | 3 | 0.30 | 2 / 2 | 3 / 39 | 14 | 3 | 0.67 |
| 1e4 | 3 | 1 | 0.00 | 0 / 1 | 0 / 1 | 11 | 0 | 0.00 |
| 1e4 | 3 | 3 | 0.10 | 0 / 4 | 2 / 14 | 14.5 | 1 | 0.25 |
| 1e4 | 6 | 1 | 0.00 | 0 / 1 | 0 / 6 | 14 | 0 | 0.67 |
| 1e4 | 6 | 3 | 0.20 | 1 / 12 | 2 / 206 | 13 | 1 | 0.25 |
| 3.16e4 | 0 | 1 | 0.10 | 0 / 1 | 0 / 54 | 17 | 0 | 0.00 |
| 3.16e4 | 0 | 3 | 0.30 | 2 / 2 | 8 / 106 | 14 | 8 | 0.64 |
| 3.16e4 | 3 | 1 | 0.00 | 0 / 1 | 0 / 4 | 14 | 0 | 0.25 |
| 3.16e4 | 3 | 3 | 0.20 | 0 / 3 | 3 / 34 | 11.5 | 2 | 0.66 |
| 3.16e4 | 6 | 1 | 0.10 | 0 / 1 | 0 / 9 | 14 | 0 | 0.65 |
| 3.16e4 | 6 | 3 | 0.40 | 2 / 15 | 4 / 258 | 13 | 6 | 0.44 |
| 1e5 | 0 | 1 | 0.10 | 0 / 1 | 0 / 93 | 17 | 1 | 0.00 |
| 1e5 | 0 | 3 | 0.50 | 1 / 5 | 9 / 172 | 14 | 11 | 0.82 |
| 1e5 | 3 | 1 | 0.00 | 0 / 1 | 0 / 4 | 14 | 0 | 0.50 |
| 1e5 | 3 | 3 | 0.50 | 2 / 6 | 9 / 75 | 11 | 6 | 0.68 |
| 1e5 | 6 | 1 | 0.20 | 0 / 1 | 1 / 16 | 20.5 | 1 | 0.78 |
| 1e5 | 6 | 3 | 0.60 | 2 / 19 | 13 / 310 | 11 | 16 | 0.52 |
| *observed* | | | | *34* | *197* | *—* | *634* | *0.50* |

First onset day, positives and asymptomatic share are medians over the seeds
where they are defined (a seed with no onsets has no first onset), so they
rest on 1–6 seeds per cell and are indicative only.

**Imports is the axis that moves.** Going from one import to three lifts
P(takeoff) from 0.0–0.2 to 0.1–0.6 at every Theta and every age, and lifts
the q95 of recorded onsets by one to two orders of magnitude. That is what a
per-import ignition probability of order 0.1–0.2 predicts, and it is
consistent with the fit grid above where P(takeoff) with one import sat at
0.05–0.10 in this Theta range.

**Infection age moves the first onset, weakly.** With three imports, first
recorded onset shifts from day 14 (age 0) to day 11–13 (age 3–6); with one
import the cell is mostly extinct and the median is noise. Age alone does not
rescue takeoff: age 3 or 6 with one import is 0.0–0.2 at every Theta. The
contrast is in the direction the mechanism predicts (an older index is
nearer its infectious peak at boarding), and it was invisible in screen v1.

**Nothing in the grid reaches the record.** The best cell (1e5, age 6,
three imports) has median 2 onsets before 6 Feb and 13 total against 34 and
197, with a q95 that overshoots (19 / 310). Ten seeds at these takeoff
probabilities leave 1–6 taking-off runs per cell; the screen shows the shape
of the surface, not its values.

### What the corrected screen says

- The number of imports, not the transmission scale and not the index case's
  age, is the first-order unknown for whether this hull's outbreak starts.
  That is the boarding baseline-shift question from the original plan, now
  posed as a measurable declared axis rather than hidden in a profile
  default.
- The next campaign, if approved, is a declared import-count sweep
  ({1, 3, 5, 10, 20}) at a few Theta values with 20 seeds, reporting
  P(takeoff), onsets before 6 Feb and totals — a report of how many imports
  the hull needs, not a fit of that number. Its result feeds Phase 3 directly.
- Separately, the seed-determined, Theta-insensitive takeoff in the fit grid
  wants a one-cell trace of the index case (contacts in its first infectious
  week; whether presentation isolates it) before any import count is
  declared, since a mechanism that removes the index case's contacts would
  masquerade as a need for more imports.

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

v3 / screen v2 (2026-09-15): fit `cd4e7b89-fc19-46a5-a9aa-63b29efc6919`
(220 children), held-out `242fccaa-f1d4-4b6e-8cb7-c435b65c6f5d` (11 children),
boarding screen `433d085c-646b-40b9-962b-89533b21f332` (180 children); job
definitions `picard-covid-hull:3` and `picard-covid-boarding-screen:2`; S3
prefixes `campaign/covid_first_look_v3/` and `campaign/covid_boarding_screen_v2/`.

```bash
python3 tools/fit_covid_theta.py merge --cells <v3 cells> \
  --design picard_framework/runs/covid_first_look_v3_design.json
python3 tools/fit_covid_theta.py screen --cells <screen v2 cells> \
  --design picard_framework/runs/covid_boarding_screen_v2_design.json
```
