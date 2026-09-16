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
> **v3 superseded 2026-09-16** by `covid_first_look_v4` (770/770, zero
> failures, `main` = `24e1d58`, #547 in): the declared index case and every
> secondary case incubated under a literal-zero / units-mismatched dose term,
> which made v3's takeoff seed-locked and pinned Theta to 1e9. On the corrected
> model **Theta = 3.16e7, interior**, P(takeoff) 0.95 at Theta_fit; the v4
> section at the end is the current statement of the fit.

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

## Index-case trace (local, 2026-09-16): why takeoff is seed-locked

One cell per seed, Theta = 1e6, CPython 3.12, the corrected scenario,
`execute_transmission` wrapped to record the index case's location, the
dose it put on its co-occupants each epoch, its symptom / isolation state,
and every transmission event. Seeds 20200205 and 20200221 (the two that
ignite at every Theta) and 20200206 / 20200207 (extinct at every Theta),
plus two counterfactuals with the index's incubation pinned.

**The index case's incubation is drawn at a dose of zero, and the model
reads zero as the lightest possible inoculum.** An explicit seed carries
`acquired_particles = 0.0` (`engines/initiation.py:_apply_one_seed`, and
the boarding path draws against a scratch record with the same value). The
incubation model (`engines/incubation.py:dose_factor`) floors that at 1e-9
particles, 12.4 log10 below the profile's reference dose (10^3.43), and
lengthens the median by the capped maximum factor 2.5: median 5.8 d becomes
14.5 d, lognormal GSD 1.57, clamped at 21 d. Shedding starts 2 d before onset
(`presymptomatic_shedding_days`), so the declared index case sheds nothing
for a median 12.5 days of a 23-day voyage. The twenty fit seeds' index
draws:

| incubation (d) | seeds | onsets at 1e6 / 1e9 |
|---|---|---|
| 5.1, 5.8, 7.5, 8.0 | 20200221, 15, 20, 17 | 309 / 979, 0 / 21, 4 / 161, 0 / 0 |
| 10.5, 12.4, 12.5 | 20200205, 06, 23 | 381 / 628, 1 / 8, 2 / 22 |
| 14.6 – 17.5 | 20200210, 13, 11, 16, 08 | 5 / 51, 0 / 8, 1 / 2, 1 / 2, 0 / 1 |
| 20.9 – 21.0 (clamp) | seven seeds | 0–1 / 0–6 |

Seven of twenty index cases hit the 21-day clamp and cannot present before
the voyage ends; only four draw under 8 d. Incubation plus the per-host
shedding multiplier (57.8 on 20200205, 0.00 on 20200217) orders the seeds.
Pinning 20200206's incubation at 4.96 d (its draw / 2.5) with its 0.27
multiplier still gave no transmission in 14 d; pinning 20200207 at 8.4 d
gave two.

**Every secondary case gets the same 2.5× penalty**, because acquisition
doses under the composite Theta are ~1e-7 in the units the incubation term
reads as particles (first transmission events in both igniting seeds carried
0.9e-7 – 3.6e-7). The generation interval is therefore ~13 d rather than
~5 d: seed 20200221 reached 1000 infections by voyage end but only 309 of
them had an onset to record. This is the "too slow conditional on
takeoff" finding above, and it is a units mismatch between Theta-scaled
doses and `incubation.dose_reference_log10`, not biology. The profile note
on `dose_reference_log10` chose the profile's own N50 (2670) precisely so
that "a near-ID50 host presents at the literature median"; on the composite
arm that premise fails, because Theta scales the dose in the infection
probability and not in the incubation term, so hosts are infected ten
decades below the N50 the incubation term is referenced to.

**Presentation isolates the index within one epoch, and the isolation
leaks inside the cabin block.** On 20200205 the index turned symptomatic at
epoch 251 and was confined at 252; all 37 of its transmissions came later
(epochs 312–361) inside its home zone `PC_D6_S_A`, a 38-occupant cabin
block that confinement does not leave. 20200207 (pinned) was the same
pattern with two events. 20200221 turned symptomatic at epoch 122 and was
**never** confined in 552 epochs; it kept its Aqua_Theater / dining rotation
and seeded 1000 infections. Why it escaped confinement was not traced
(inference: the bimodal compliance draw; it is consistent with a refuser).

**The index case's contacts are not the problem.** Both traced index cases
had 30–550 co-occupants every epoch from epoch 0 (cabin block, promenade,
main dining). Nothing strands the index case; it simply does not shed
until late, and when it does the shedding is 3–5 log10 for the two
presymptomatic days, which delivered no infections in any trace.

Implications, in order:

- The seed-locked takeoff is an initialisation defect, not evidence about
  imports. A declared import with no stated dose should draw its incubation
  at the reference dose (factor 1.0), not at the floor; until it does, the
  import-count sweep proposed above would be counting how many 14.5-day
  incubations it takes to get one short one.
- The same zero-dose draw sits under every norovirus explicit seed and every
  boarding-drawn host: `norwalk_gi` has `dose_log10_shortening 0.12` and
  reference 10^4.23, so its seeds and boarders take 1.2 d × 2.5 = 3.0 d
  median incubation against a 6 d clamp. Whether norovirus *transmitted*
  doses also sit below the reference depends on that arm's dose units and
  was not checked here.
- The 2.5× penalty on Theta-scaled secondary doses means the COVID arm's
  incubation term is currently reading a composite scale as an inoculum.
  Either the incubation dose term is disabled on the composite-Theta arm, or
  the acquired dose is converted to the units the reference is in, before
  any Theta or import count is interpreted.
- The infection-age result in the screen (age 6 d moving first onset by
  ~3 d) is what subtracting 6 d from a 14.5-d median predicts; it is not
  evidence about the record's index case.

Trace scripts and JSON are session artifacts, not in the tree; the mechanism
is checkable from the two functions named above and one 2-epoch run
(`incubation_days` appears on the index record after the first step).

The two changes recommended above landed as #547: a host with no inoculum on
record draws its incubation at the reference (factor 1.0), and the
composite-Theta arm re-references its incubation dose term to the N50 it
installs (ln 2 / Theta) rather than disabling it, so Theta stays the one
fitted dimension.

## covid_first_look_v4: the v3 grid on the corrected incubation model

Same grid, same 20 + 50 matched seeds, same objective as v3; the only
change is #547. Image `picard-campaign:covid-first-look-v4` from `24e1d58`
(CPython 3.11); 770/770 cells, zero Batch failures. Outputs:
`telemetry_buffer/observation_model/covid_theta_fit_v5.json` and
`covid_theta_held_out_v5.json`. Cells pair with v3 by (Theta, seed).

### Phase 1, Diamond Princess (20 seeds)

| Theta | recorded onsets, 20 seeds sorted | P(takeoff, ≥10) | v3 P | loss (mean) | wins |
|---|---|---|---|---|---|
| 1e4 | 0 ×11, 1 ×4, 2 ×2, 3 ×3 | 0.00 | 0.05 | 106.1 | 0.00 |
| 3.16e4 | 0 ×12, 1 ×2, 3, 8, 22 ×2, 131, 240 | 0.20 | 0.10 | 90.8 | 0.00 |
| 1e5 | 0 ×7, 1–8 ×8, 10, 17, 34, 143, 331 | 0.25 | 0.10 | 74.2 | 0.00 |
| 3.16e5 | 0 ×4, 1–3 ×8, 13–88 ×6, 242, 672 | 0.40 | 0.10 | 62.2 | 0.00 |
| 1e6 | 0 ×2, 1, 2, 4, 8, 11–258 ×11, 699, 763, 1384 | 0.70 | 0.10 | 30.8 | 0.00 |
| 3.16e6 | 0, 2, 5, 9, 12–233 ×13, 647, 791, 1718 | 0.80 | 0.25 | 20.0 | 0.00 |
| 1e7 | 0, 5, 27–570 ×14, 880, 938, 1024, 1961 | 0.90 | 0.25 | 12.0 | 0.26 |
| **3.16e7** | 0, 36–402 ×13, 685, 915, 1071, 1359, 1674, 2058 | 0.95 | 0.25 | **10.1** | **0.50** |
| 1e8 | 0, 82–999 ×13, 1116–2145 ×6 | 0.95 | 0.25 | 10.4 | 0.21 |
| 3.16e8 | 0, 366–1027 ×11, 1134–1710 ×8 | 0.95 | 0.25 | 11.2 | 0.03 |
| 1e9 | 0, 320–1245 ×10, 1352–2018 ×9 | 0.95 | 0.30 | 12.6 | 0.00 |
| *observed* | *197 (34 before 6 Feb)* | | | | |

**Theta = 3.16e7, and it is no longer boundary-pinned** (0.50 of
paired-bootstrap resamples; 1e7 0.26, 1e8 0.22, 3.16e8 0.03, 1e9 0.00). The
loss curve has an interior minimum for the first time in the campaign
series: below 1e7 the loss is takeoff-limited, above 1e8 it is
overshoot-limited (median totals 700–1245 vs 197).

**Takeoff is now decided by Theta, not by the seed.** Paired by seed,
no seed that ignited in v3 fails to ignite in v4 at any Theta from 3.16e4
up, and 11–14 of the 15–18 v3-extinct seeds ignite from 1e6 up. One seed
(20200217) never ignites at any Theta: 0 recorded onsets even at 1e9 with
2,696 campaign specimens, so its index case did not transmit at all
(inference: an index case isolated before its shedding window — not traced).
P(takeoff) rises 0.00 → 0.95 across the grid where v3 moved 0.05 → 0.30.
The seed-locked pattern of v3 was the 14.5-day median incubation of the
declared index case, as the trace predicted.

**Conditional on takeoff at the selected Theta, the early trajectory is
still slow and the total is too large.** At 3.16e7 (n = 19): median onsets
before 6 Feb 13 vs 34, median total 381 vs 197, campaign positives 311 vs
634, asymptomatic share of positives 0.90 vs 0.50. The early/total tension
is now the visible misfit: Theta values that give ~34 early onsets (1e9,
median 27) give 1,245 total; those that give ~200 total (3.16e6–1e7) give
4–5 early. A single composite scale does not set both the early speed and
the plateau. The asymptomatic share (0.89–0.91 across 1e6–1e9) did not
move with either incubation change; the campaign-roster drain described
under v2 remains the candidate.

### Phase 2, Greg Mortimer at Theta = 3.16e7 (50 seeds; 1e7 / 1e8 in parentheses)

| | v3 at 1e9 | v4 at 3.16e7 (1e7 / 1e8) | observed |
|---|---|---|---|
| P(no positives) | 0.20 | 0.06 (0.10 / 0.06) | — |
| P(takeoff, ≥10 onsets) | 0.04 | 0.64 (0.54 / 0.76) | — |
| campaign positives, median / q95 | 3 / 16 | 17.5 / 118 (12 / 94; 35.5 / 142) | 128 |
| H1 positive share | miss 50/50 | hit 6, miss 44 (median 0.08) | 0.59 |
| H2 asymptomatic share among positives | hit 7, miss 33 of 40 | hit 1, miss 46 of 47 (median 0.33) | 0.81 |
| H3 share above cross-ship IQR | 0.48 | 0.76 | 0.015 |

The held-out hull now takes off in most seeds and its positive count is a
distribution that reaches the observed 128 at its q95 rather than never;
across the held-out grid P(takeoff) rises 0.04 → 0.80 and the positive
share median reaches 0.52 only at 1e9. H1 is met only at the top of the
grid and H2 has flipped side: v3's Greg Mortimer positives were almost all
asymptomatic (median 1.00), v4's are one-third asymptomatic against 0.81
observed. Greg Mortimer's positives are therefore under-produced at
Theta_fit by roughly 7× at the median, and their composition now misses
in the opposite direction to Diamond Princess (0.33 vs 0.81 observed here;
0.90 vs 0.50 observed there) — the observation-process split between the
two hulls, not Theta, is where that lives.

### What v4 says

- v3's boundary-pinned Theta and seed-locked takeoff were the incubation
  defect. They should not be quoted; the v4 selection (3.16e7, interior)
  supersedes them.
- With one declared index case the corrected model *does* produce a
  Diamond Princess-sized outbreak in 19 of 20 seeds at Theta_fit. The
  "needs more imports" reading of v3 and the boarding screen is much
  weaker than it was: an import-count sweep would now measure how imports
  trade against Theta in the early trajectory, not whether the hull
  ignites at all.
- The remaining Diamond Princess misfit is shape, not scale: early onsets
  13 vs 34 while the total overshoots 2×. Candidates, in the order the
  evidence suggests: (a) the import axis (several early imports raise the
  early count without raising the plateau the way Theta does — the 1b
  screen's direction, now to be re-read on the corrected model),
  (b) the quarantine's effect on the plateau (the observed 197 onsets are
  under a 5 Feb cabin quarantine; whether the model's confinement leaks
  as much as the trace showed in cabin blocks is the total-side lever),
  (c) the campaign-roster drain for the asymptomatic share.
- The held-out result improved from "never" to "under-produced by ~7× at
  the median, with the observed value inside the distribution". That is
  the first held-out statement in this series that is a quantitative
  miss rather than a categorical one.

## Quarantine-leak and roster-drain trace (local, 2026-09-16)

Two full-voyage Diamond Princess cells at Theta_fit = 3.16e7 (v4 seeds
20200215 and 20200216, CPython 3.12) with the transmission core's dose
accumulation and the syndromic specimen ledger instrumented. Aggregate only:
`TransmissionEvent.source_agent_id` is `None` on every droplet/HVAC event, so
transmitter-specific chains cannot be read from the current event structure.

**Leak.** Pathways are 95% droplet, 5% HVAC, zero direct contact, so
`contact_mode` (`density_dependent` or otherwise) is inert on this arm. After
the day-16 (5 Feb) confinement, seed 16 infects 2,039 confined passengers
inside `Cabin_Corridor` zones, 1,043 crew (exempt, working Dining/Free/crew
corridors) and 413 unconfined passengers; infections/day peak at ~540 on
day 25, i.e. the epidemic runs inside the quarantine, opposite to the record.
Decomposing the droplet dose each confined passenger accumulated before
infection: **92% shared far-field cabin-block air, 8% cabin-mate add-back,
0% near-field** (near-field is off in the fit spec). The block is a single
900-1,200 m³ pool holding ~35 confined passengers 24 h/day; the 0.05×0.05
confinement factor on emission and inhalation does not beat a median 144
dosed epochs against several 1e9-copy shedders. The shared corridor pool, not
cabin-mate contact, is the leak; it is a ship-model architecture finding and
is *not* interpreted as an import effect in the sweep below.

**Drain.** (1) ~800 passengers receive a passive sick-call swab on days 16-17
with ~45 hosts infected: confinement → ~30% refuse → exported as
`compliance_status = non_compliant` → syndromic treats non-compliant as
symptomatic → sick-call hazard → PCR. All are then excluded from the campaign
roster for the rest of the voyage. (2) One specimen per host, ever: 1,758
hosts swabbed negative and infected later were never retested; 1,279 swabbed
while infected but below the day-of-infection sensitivity curve, likewise.
Campaign positives are 300 against 3,520 infected, and 74% crew (observed
~20%). The 0.90 asymptomatic share is mostly *timing* — campaign days 24-29
coincide with peak incidence, so positives are presymptomatic at swab (64%
record an onset later) — and will move with the leak before any roster change.

## covid_import_sweep_v1: adaptive-density imports × Theta, three stages (all three run 2026-09-16/17)

The next campaign measures how declared import count trades against Theta on
the corrected model, with **adaptive sampling density**: a coarse product grid
first, then two refinement stages that insert midpoints only where the
response moves fastest, each at closer resolution than the last.

**Stage 1** (`picard_framework/runs/covid_import_sweep_v1_design.json`): Theta
∈ {3.16e6, 1e7, 3.16e7, 1e8, 3.16e8} × imports ∈ {1, 2, 3, 5, 8, 13, 20} ×
the 20 matched v4 fit seeds, index case infected at embarkation, heads
visited (`dwell_weighted`). 700 cells, ~30 min each, roughly $10 on Spot.
Same worker, merge and pairing as the boarding screen (`screen` subcommand),
plus per-cell `conditional_on_takeoff` medians.

**Stage 2** (`tools/fit_covid_theta.py refine`, `picard_framework/covid_import_sweep.py`):
for every pair of neighbouring stage-1 cells along either axis, compute
`P(takeoff)` change, and the log change of the conditional medians of onsets
before 6 Feb and total recorded onsets. A pair is a candidate when
`|ΔP(takeoff)| > 0.25`, a conditional median changes more than 2×, or a
conditional median **crosses the observed count** (34 early / 197 total —
used to locate the crossing, never to prefer a cell). Candidates are ranked
by their largest normalised change; the top 12 geometric midpoints
(`sqrt(Theta_a Theta_b)`, `round(sqrt(n_a n_b))`, skipping midpoints that
collapse onto an endpoint) become an explicit point list — the same design
schema with `points` set — run on the same 20 seeds (≤240 cells). The refined
design records the stage, the rule, every candidate's scores and the pair it
sits between, so the choice of where to look is declared before the cells run.

**Stage 3** (`refine --stage 3 --surface <stage1> <stage2>`): the same rule
over the **union** of the stage-1 and stage-2 surfaces, with tolerances
tightened to `|ΔP(takeoff)| > 0.15` and a **1.5×** conditional-median change
(`--stage` sets these defaults: 0.25·0.6^(k−2) and 1+0.5^(k−2); either can be
overridden). Neighbours are taken along each Theta row and imports column *as
populated*, so a stage-2 midpoint pairs with the stage-1 cells on either side
of it and the pitch closes only where stage 2 still found the response moving.
On the imports axis integer midpoints saturate (a pair `(n, n+1)` has no
midpoint and is skipped), so stage 3 mostly closes the Theta pitch to a
quarter-decade or finer around the crossings. Another ≤240 cells at budget 12.
The stage-3 design records both surfaces it read; a cell present in two
surfaces is refused rather than silently averaged.

What the sweep reads: P(takeoff), early and total onsets and campaign
positives conditional on takeoff, first onset day, and positive composition,
all per (Theta, imports) and paired by seed. It declares imports; it does not
fit them, and the quarantine-leak finding above bounds how much of any total-
side mismatch may be attributed to the import axis.

### Result: 1,180 cells, zero Batch failures, and no point on the surface is the record

Stage 1 700 cells, stage 2 240, stage 3 240; 59 distinct (Theta, imports)
points, no point evaluated twice, heads visited in 1,180/1,180 cells. Every
figure below is a median over the 20 matched seeds **conditional on takeoff**
(a cell counts as taking off at 10 or more recorded onsets); `P(takeoff)` is
over all 20.

Stage 2 chose eight midpoints on the imports axis and four on Theta (imports 4
and 10 across the Theta rows, Theta 5.62e6 and 5.62e7 at low imports); stage 3,
with tolerances at 0.15 and 1.5x, split six and six — imports 11 and 16, and
quarter-decade Theta steps (7.5e6, 1.78e7, 4.22e7, 1.78e8). Both refinement
stages therefore closed the pitch around the *early-onset* crossing rather than
the takeoff boundary, which by v4 was already saturated: `P(takeoff)` is 0.80
or higher at every point on this surface, including one import.

| Theta | imports | stage | P(takeoff) | early | total | early/total | positives | asym share | crew share |
|---|---|---|---|---|---|---|---|---|---|
| 3.16e+06 | 1 | 1 | 0.80 | 4 | 118 | 0.038 | 137 | 0.88 | 0.01 |
| 3.16e+06 | 2 | 1 | 0.95 | 12 | 211 | 0.057 | 220 | 0.90 | 0.01 |
| 3.16e+06 | 3 | 1 | 1.00 | 30 | 597 | 0.049 | 360 | 0.90 | 0.03 |
| 3.16e+06 | 4 | 2 | 1.00 | 28 | 504 | 0.055 | 332 | 0.90 | 0.04 |
| 3.16e+06 | 5 | 1 | 1.00 | 52 | 797 | 0.065 | 411 | 0.89 | 0.06 |
| 3.16e+06 | 8 | 1 | 1.00 | 61 | 880 | 0.069 | 400 | 0.90 | 0.08 |
| 3.16e+06 | 10 | 2 | 1.00 | 74 | 1058 | 0.070 | 438 | 0.89 | 0.07 |
| 3.16e+06 | 11 | 3 | 1.00 | 133 | 1230 | 0.108 | 443 | 0.89 | 0.08 |
| 3.16e+06 | 13 | 1 | 1.00 | 248 | 1494 | 0.166 | 438 | 0.89 | 0.12 |
| 3.16e+06 | 16 | 3 | 1.00 | 397 | 1689 | 0.235 | 443 | 0.89 | 0.13 |
| 3.16e+06 | 20 | 1 | 1.00 | 488 | 1756 | 0.278 | 423 | 0.90 | 0.15 |
| 5.62e+06 | 1 | 2 | 0.95 | 5 | 173 | 0.029 | 200 | 0.89 | 0.01 |
| 5.62e+06 | 2 | 2 | 1.00 | 14 | 261 | 0.052 | 202 | 0.87 | 0.01 |
| 5.62e+06 | 3 | 2 | 1.00 | 42 | 855 | 0.049 | 410 | 0.91 | 0.05 |
| 5.62e+06 | 4 | 3 | 1.00 | 42 | 847 | 0.049 | 426 | 0.90 | 0.06 |
| 7.5e+06 | 2 | 3 | 1.00 | 16 | 394 | 0.042 | 284 | 0.89 | 0.03 |
| 1e+07 | 1 | 1 | 0.90 | 8 | 278 | 0.027 | 260 | 0.90 | 0.01 |
| 1e+07 | 2 | 1 | 0.95 | 21 | 497 | 0.042 | 378 | 0.91 | 0.04 |
| 1e+07 | 3 | 1 | 1.00 | 34 | 875 | 0.039 | 430 | 0.90 | 0.05 |
| 1e+07 | 4 | 2 | 1.00 | 50 | 969 | 0.052 | 456 | 0.90 | 0.05 |
| 1e+07 | 5 | 1 | 1.00 | 86 | 1168 | 0.074 | 456 | 0.90 | 0.08 |
| 1e+07 | 8 | 1 | 1.00 | 98 | 1392 | 0.070 | 470 | 0.91 | 0.10 |
| 1e+07 | 10 | 2 | 1.00 | 134 | 1398 | 0.096 | 452 | 0.90 | 0.10 |
| 1e+07 | 11 | 3 | 1.00 | 255 | 1538 | 0.166 | 463 | 0.90 | 0.13 |
| 1e+07 | 13 | 1 | 1.00 | 288 | 1604 | 0.179 | 430 | 0.89 | 0.16 |
| 1e+07 | 20 | 1 | 1.00 | 515 | 1856 | 0.277 | 404 | 0.89 | 0.17 |
| 1.78e+07 | 5 | 3 | 1.00 | 100 | 1390 | 0.072 | 426 | 0.89 | 0.09 |
| 1.78e+07 | 13 | 3 | 1.00 | 419 | 1744 | 0.240 | 428 | 0.89 | 0.18 |
| 3.16e+07 | 1 | 1 | 0.95 | 7 | 368 | 0.019 | 302 | 0.91 | 0.03 |
| 3.16e+07 | 2 | 1 | 1.00 | 28 | 794 | 0.035 | 466 | 0.89 | 0.05 |
| 3.16e+07 | 3 | 1 | 1.00 | 58 | 1298 | 0.045 | 452 | 0.90 | 0.09 |
| 3.16e+07 | 4 | 2 | 1.00 | 52 | 1126 | 0.047 | 491 | 0.90 | 0.07 |
| 3.16e+07 | 5 | 1 | 1.00 | 168 | 1488 | 0.113 | 452 | 0.90 | 0.12 |
| 3.16e+07 | 8 | 1 | 1.00 | 179 | 1573 | 0.114 | 462 | 0.89 | 0.15 |
| 3.16e+07 | 10 | 2 | 1.00 | 204 | 1606 | 0.127 | 460 | 0.89 | 0.15 |
| 3.16e+07 | 11 | 3 | 1.00 | 348 | 1724 | 0.202 | 448 | 0.89 | 0.16 |
| 3.16e+07 | 13 | 1 | 1.00 | 576 | 1874 | 0.308 | 397 | 0.89 | 0.20 |
| 3.16e+07 | 20 | 1 | 1.00 | 808 | 2020 | 0.400 | 366 | 0.90 | 0.21 |
| 4.22e+07 | 3 | 3 | 1.00 | 68 | 1250 | 0.054 | 464 | 0.90 | 0.09 |
| 5.62e+07 | 3 | 2 | 1.00 | 136 | 1428 | 0.096 | 454 | 0.90 | 0.11 |
| 1e+08 | 1 | 1 | 0.95 | 13 | 557 | 0.023 | 371 | 0.90 | 0.02 |
| 1e+08 | 2 | 1 | 1.00 | 40 | 1192 | 0.033 | 466 | 0.90 | 0.06 |
| 1e+08 | 3 | 1 | 1.00 | 189 | 1568 | 0.120 | 431 | 0.90 | 0.16 |
| 1e+08 | 5 | 1 | 1.00 | 268 | 1648 | 0.163 | 422 | 0.89 | 0.17 |
| 1e+08 | 8 | 1 | 1.00 | 279 | 1678 | 0.166 | 410 | 0.89 | 0.19 |
| 1e+08 | 10 | 2 | 1.00 | 266 | 1714 | 0.155 | 410 | 0.90 | 0.19 |
| 1e+08 | 11 | 3 | 1.00 | 514 | 1874 | 0.275 | 396 | 0.89 | 0.20 |
| 1e+08 | 13 | 1 | 1.00 | 870 | 2042 | 0.426 | 350 | 0.89 | 0.22 |
| 1e+08 | 20 | 1 | 1.00 | 1174 | 2189 | 0.537 | 322 | 0.89 | 0.23 |
| 1.78e+08 | 2 | 3 | 1.00 | 49 | 1277 | 0.038 | 477 | 0.89 | 0.08 |
| 3.16e+08 | 1 | 1 | 0.95 | 16 | 974 | 0.016 | 459 | 0.88 | 0.06 |
| 3.16e+08 | 2 | 1 | 1.00 | 75 | 1440 | 0.052 | 452 | 0.89 | 0.15 |
| 3.16e+08 | 3 | 1 | 1.00 | 294 | 1732 | 0.170 | 415 | 0.89 | 0.22 |
| 3.16e+08 | 5 | 1 | 1.00 | 279 | 1738 | 0.160 | 394 | 0.89 | 0.21 |
| 3.16e+08 | 8 | 1 | 1.00 | 460 | 1864 | 0.247 | 380 | 0.89 | 0.23 |
| 3.16e+08 | 10 | 2 | 1.00 | 482 | 1878 | 0.257 | 392 | 0.88 | 0.23 |
| 3.16e+08 | 11 | 3 | 1.00 | 760 | 2022 | 0.376 | 354 | 0.88 | 0.24 |
| 3.16e+08 | 13 | 1 | 1.00 | 955 | 2128 | 0.449 | 350 | 0.89 | 0.24 |
| 3.16e+08 | 20 | 1 | 1.00 | 1486 | 2309 | 0.644 | 291 | 0.89 | 0.25 |
| **observed** | — | — | — | **34** | **197** | **0.173** | **634** | **0.50** | **~0.20** |

**Takeoff no longer discriminates.** Five decades of Theta and imports 1-20
all ignite (0.80-1.00). Whatever the sweep measures, it is not the ignition
problem v3 had.

**The early and total anchors cannot be satisfied together.** Interpolating
each Theta row to where the early median crosses the observed 34:

| Theta | imports at the early crossing | total median there | observed total |
|---|---|---|---|
| 3.16e6 | 4.3 | 582 | 197 |
| 5.62e6 | 2.7 | 688 | 197 |
| 1e7 | 3.0 | 861 | 197 |
| 3.16e7 | 2.2 | 900 | 197 |
| 1e8 | 1.8 | 1,060 | 197 |
| 3.16e8 | 1.3 | 1,116 | 197 |

Matching the early count overshoots the voyage total by 3-6x on every row;
matching the total (3.16e6 with 2 imports: early 12, total 211) undershoots the
early count by ~3x. The reason is the **shape**: the model's early share of the
voyage total is 0.02-0.06 through the whole low-import region against an
observed 34/197 = 0.173, and it only reaches 0.17 at 11-20 imports, where the
total is 1,500-2,300 (the hull saturates near 2,300). Imports front-load the
epidemic, but they cannot front-load it without also finishing it.

**That missing suppression is the quarantine leak**, measured in the trace
above: the epidemic keeps running inside the 5 Feb confinement through the
shared cabin-block air pool (peak ~540 infections/day on day 25) instead of
being cut off by it. The sweep therefore brackets the import axis rather than
fitting it: the record's total is only reachable with ~2 imports, and at ~2
imports nothing on the Theta axis produces the observed early trajectory.

**Two invariants across all 59 points**, neither moved by imports or Theta:
the campaign asymptomatic share sits at 0.88-0.91 against 0.50 observed, and
campaign positives never exceed ~490 against 634 observed (they *fall* at high
Theta as hosts are drained off the roster). Both are roster/observation-process
properties, consistent with the drain trace, and neither is an import effect.

**What the sweep does not say.** It does not fit imports, and it does not
license "Diamond Princess had N imports": with the leak in place the total-side
constraint that picks ~2 imports is itself suspect. The ordering implied is
leak first, roster second, imports last.

## Observation-process correction (2026-09-17): sick call reads presentation; declared retest-after-negative

Two of the three drains above are closed in the observation process, ahead of
the cabin-air architecture change and before any v5 campaign.

**Sick call reads presentation only.** The syndromic roster treated a host with
`compliance_status = non_compliant` as symptomatic, a carry-over from the old
combined status in which `non_compliant` implied illness. Under general
confinement, ~30% of hosts refuse, so ~800 healthy refusers drew a passive
specimen on days 16-17 and were retired from the campaign roster for the
voyage. The roster now enters a host on symptomatic presentation alone;
compliance remains what the confinement logic reads (`agent_requires_confinement`
is unchanged).

**Declared retest-after-negative.** The campaign roster was without replacement
across days for every host; a host swabbed negative (or swabbed while below the
day-of-infection sensitivity curve) was never reached again. Diamond Princess
now declares `molecular_ascertainment.retest_negatives_on_indication: true`
(Grade C: the published 3,063 specimens include repeat tests of quarantined
negatives, and symptomatic/contact indications arose again during quarantine;
the per-host repeat assignment is not published). Under the policy a host with
a negative on record may be swabbed again on a *later* day when there is an
indication — it presents to sick call, or the campaign's
`symptomatic_or_contact` tier reaches it. Population sweep tiers do not return
to a swabbed host, a confirmed host is never swabbed again, one host never
yields two specimens on one day, and the daily capacities are the published
counts unchanged. Greg Mortimer does not declare it (one day, one rung), so the
default is the old behaviour.

**Change detector** (Greg Mortimer, Θ=1e6, seed 20200333): (5, 0, 217, 6, 4) →
(6, 0, 217, 6, 3) on both CPython 3.11 and 3.12. The move is the
presentation-only sick call alone (restoring the coupling returns the old
tuple); the retest policy is inert on this hull. The Diamond Princess effect
(campaign positives, asymptomatic share, crew share) is measured on the v5
campaign, not locally.

## AERO-CABIN-01: the leak closed, measured on one paired cell (local, 2026-09-16)

The repair is a declared mode, `transmission.cabin_air_mode`: `zone_pool`
(default, and what every campaign above ran) against `cabin_compartment`, which
runs the far-field inhalation pool per stateroom inside a `Cabin_Corridor`
block, dividing the block's declared volume by berths. Spec and its bounds:
[`../cabin_air_compartment_spec.md`](../cabin_air_compartment_spec.md);
norovirus ledger item 44. **No constant is added or fitted** — the stateroom
volume is a partition of the volume the hull already declares, and emitted mass
is still credited to the parent zone so the drift route and the aerosol
reservoir are unchanged.

**Paired full-voyage cell** (Diamond Princess, Theta_fit = 3.16e7, seed
20200216, 768 epochs, CPython 3.12, one declared index case, heads visited;
`/home/ubuntu/phase0/leak_mode.py`, artifacts `leak_pool.json` and
`leak_comp.json`). The two runs differ only in the mode. Both were traced on
the tree *before* the observation-process correction above, so the two specimen
rows are pre-correction counts; the transmission rows do not depend on the
observation channel and the change-detector readings below are on the merged
tree:

| | `zone_pool` | `cabin_compartment` |
|---|---|---|
| ever infected | 3,568 | **2** |
| transmission events | 3,588 | 1 |
| recorded onsets | 401 | 0 |
| campaign specimens / positives | 2,231 / 308 | 2,640 / 0 |
| passive specimens / positives | 1,480 / 187 | 1,071 / 0 |
| events in `Cabin_Corridor` | 2,358 | 1 |
| post-day-16 events (confined pax / crew) | 3,544 (2,088 / 1,043) | 0 |

So the block pool was not *a* leak, it was the epidemic: with the index case
dosing only its own stateroom, the outbreak does not reach a second
generation at the Theta fitted against the pooled block, and the 838 Dining and
392 Free events in the pooled run are downstream of cabin-block seeding rather
than an independent path. The change-detector cell moves the same way on the
merged tree (Greg Mortimer, Theta 1e6, seed 20200333, CPython 3.12):
`(6, 0, 217, 6, 3)` under `zone_pool` — the pinned golden, unchanged, because
the mode ships off — to `(0, 0, 217, 0, 0)` under `cabin_compartment`, which is
why that reading is recorded here and not pinned: an all-zero cell detects
nothing. That hull partitions 16 blocks into 114 staterooms over 223 berths, at
a median 60 m³ per berth (15-100).

**What this does and does not say.** It is one seed on one hull, and it is a
*mechanism* measurement, not a fit: it says the confined-passenger dose the
trace attributed 92% to shared block air disappears when the air is
partitioned, and therefore that **Theta_fit = 3.16e7 belongs to the pooled
block and cannot be carried over** — the v5 fit has to refit Theta with the
mode on, and should expect a substantially higher value. Nothing above is
retracted: every campaign in this document ran the default `zone_pool`, and the
mode ships off. Whether the early/total shape misfit survives the refit — the
question the sweep left open — is what v5 measures.

## Per-pathogen HVAC pool transport repair and the two default flips

The pre-repair CONTAM step transported only the legacy aggregate airborne
array. The aggregate is recomputed from the per-pathogen pools on the next
`set_pathogen_zone_mass` call, so the transported aggregate was discarded and
no profiled pathogen's airborne mass crossed a zone boundary. Within-zone
airborne dosing was unaffected. The repair transports each per-pathogen pool
through the declared airflow network with the engine decay rate set to zero,
because each pool is already aged by its own declared airborne half-life.

The shipped defaults also changed to
`hvac.pathogen_pool_transport: airflow` and
`transmission.cabin_air_mode: cabin_compartment`. The labelled pre-change
baselines remain available for paired measurement. The change-detector
attribution table is:

| pool transport | cabin air | pinned tuple |
|---|---|---|
| `none` | `zone_pool` | `(6, 0, 217, 6, 3)` |
| `none` | `cabin_compartment` | `(0, 0, 217, 0, 0)` |
| `airflow` | `zone_pool` | `(0, 0, 217, 0, 0)` |
| `airflow` | `cabin_compartment` | `(0, 0, 217, 0, 0)` |

The old change-detector cell at Θ=1e6 belonged to the pooled-air model and
became all-zero under either single default flip. The detector therefore moved
to the lowest live, unsaturated new-default point, Θ=1e10, which reads
`(149, 62, 217, 166, 30)` on the local CPython 3.12 run and is pinned for both
supported interpreter minors.

The full-voyage traces at Θ=3.16e7, seed 20200216 were:

| cabin air | onsets | hvac_airborne infections | witness: mass zones without a shedder |
|---|---:|---:|---:|
| `zone_pool` | 2258 | 1729 | 68 |
| `cabin_compartment` | 3 | 13 | 139 |

Artifacts: [`/home/ubuntu/phase0/pool_transport_logs/zone_pool.log`](file:///home/ubuntu/phase0/pool_transport_logs/zone_pool.log) and [`/home/ubuntu/phase0/pool_transport_logs/cabin_compartment.log`](file:///home/ubuntu/phase0/pool_transport_logs/cabin_compartment.log).

Θ=3.16e7 belongs to the pooled model, so a refit under the new defaults is
required before any v5 or v4 number is carried forward. Earlier campaigns are
not retracted; they are labelled pooled-air, no-between-zone-transport runs.

## covid_first_look_v5: refit with cabin compartments on, and a paired pooled control (Batch, 2026-09-17)

v5 refits Theta with `transmission.cabin_air_mode: cabin_compartment` — the
question AERO-CABIN-01 left open, now on the full 20-seed distribution rather
than the single paired cell. The grid runs half-decades **1e7 → 1e12** (11
points), the 20 matched Diamond Princess seeds and 50 Greg Mortimer held-out
seeds; 770 cells, zero Batch failures. A paired control, **v5c**, runs the same
seeds on the old `zone_pool` air at 1e7 / 3.16e7 / 1e8 (210 cells), so the
air-architecture effect is separable from the observation-process change (#555)
that both v5 and v4 differ in. Designs
[`../../picard_framework/runs/covid_first_look_v5_design.json`](../../picard_framework/runs/covid_first_look_v5_design.json)
and `..._v5c_design.json`; every landed cell records its `cabin_air_mode`.

### The compartment refit does not produce a fit — it makes the tension worse

Diamond Princess fit medians over 20 seeds (`recorded_onsets`, onsets before
day 17, campaign specimens, campaign positives, asymptomatic share of
positives); observed anchors are **197 onsets, 34 before 6 Feb, 634 positives**:

| Theta | onsets | before d17 | specimens | positives | asymp | P(takeoff) | mean loss | median loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1e7 | 1 | 1 | 2663 | 1 | 0.00 | 0.30 | 79.1 | 103.0 |
| 3.16e7 | 1 | 1 | 2662 | 1 | 0.00 | 0.25 | 79.3 | 103.0 |
| 1e8 | 2.5 | 1 | 2658 | 2 | 0.89 | 0.45 | 56.7 | 80.2 |
| 3.16e8 | 173 | 1.5 | 2470 | 186 | 0.90 | 0.65 | 41.9 | 7.4 |
| 1e9 | 709 | 2 | 1959 | 374 | 0.89 | 0.75 | 29.5 | 7.2 |
| 3.16e9 | 1272 | 13.5 | 1208 | 379 | 0.90 | 0.90 | 16.6 | 8.9 |
| 1e10 | 1685 | 176.5 | 731 | 355 | 0.89 | 0.90 | 15.7 | 9.3 |
| 3.16e10 | 2010 | 867.5 | 482 | 332 | 0.88 | 1.00 | 9.0 | 9.3 |
| 1e11 | 2440 | 1864.5 | 357 | 252 | 0.88 | 1.00 | 9.2 | 9.0 |
| **3.16e11** | **2458** | **2089.5** | **349** | **245** | 0.90 | 1.00 | **8.98** | 8.9 |
| 1e12 | 2499 | 2209 | 381 | 202.5 | 0.87 | 1.00 | 9.3 | 9.3 |

The objective (covid.T1 total + on/after-split onsets, covid.T3 positives)
selects **Theta = 3.16e11**, bootstrap frequency 0.37, not boundary-pinned. But
that selection is an artefact of ranking on the **mean** across a highly
variable extinction: at low Theta most seeds go extinct (a 0-onset seed costs
~35 in log-residual), inflating the mean, while the high-Theta plateau ignites
every seed to a *uniformly* mediocre loss (~9, q05–q95 8.2–10.2). It is
reliably wrong, so it wins on the mean.

**What the selected Theta actually produces is the whole ship, before
quarantine.** 2,458 onsets on a ~3,700-host hull, **2,089 of them before day 17
against 34 observed** — the outbreak burns out before the 5 Feb confinement it
was supposed to test. To ignite reliably from one index case with each
stateroom its own air unit, Theta has to reach ~3e11, at which point the implied
per-copy risk is ~1e11, decades outside the grade-B emission bracket
(4,200–5.8e7 copies/epoch). No point on five decades both ignites and matches
the trajectory. The objective does not score the before-split count, so it is
blind to that early overshoot; the channel table is not.

Held-out Greg Mortimer at the selected Theta does land its positive count for
the first time — median 123 against 128 observed, P(takeoff) 0.98, covid.H1 35
hit / 15 miss — but by the same runaway: 51.5 of 63.5 recorded onsets fall
before day 17, and the asymptomatic share collapses to 0.03 against 0.81
observed (covid.H2 0/50, covid.H3 above the IQR in 0.98 of seeds). A count
matched by burning the hull early is not the hull's trajectory, so it is
reported, not claimed.

### The pooled control refits cleanly to the old value

v5c, same seeds and observation process, pooled air:

| Theta | onsets | before d17 | positives | asymp | P(takeoff) | mean loss | median loss |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1e7 | 288.5 | 5 | 253 | 0.90 | 0.90 | 12.0 | 2.2 |
| **3.16e7** | **365** | **12.5** | **310** | 0.90 | 0.95 | 10.1 | **2.7** |
| 1e8 | 688.5 | 14.5 | 451.5 | 0.91 | 0.95 | 10.4 | 5.1 |

v5c selects **3.16e7 — the v4 value — with a median loss of 2.7**, three times
better per typical seed than the compartment plateau's 8.9, and a plausible
outbreak (365 onsets, 310 positives) rather than a whole-ship burn. Its mean
loss (10.1) reads worse than v5's (9.0) only because one extinct seed inflates
it; the median is the honest per-seed comparison. Held-out Greg Mortimer at
3.16e7 reproduces v4 (positives 17.5 vs 128 at q95, asymptomatic 0.33 vs 0.81),
confirming the control is the v4 regime with the air held fixed.

### What v5 says

**A hard per-stateroom partition over-isolates, exactly as the single pool
over-mixed.** The pooled block was not merely *a* quarantine leak to close: it
was the model's dominant between-cabin transport, and with it removed the HVAC
route that was expected to carry the between-cabin path is too weak to sustain
the outbreak from one index case. Neither extreme is the Diamond Princess: the
900–1,200 m³ block pool over-mixes (the total-side overshoot during quarantine,
Phase-sweep result), and the sealed stateroom cannot ignite without a
physically indefensible Theta. The real between-cabin path is corridor/HVAC
coupling stronger than the current HVAC route and weaker than a shared pool —
that coupling, not the confinement factor or the import count, is now the
open lever. The early-vs-total shape misfit the sweep flagged is unchanged by
either air model: even v5c's plausible cell has 12 early onsets against 34 and
365 total against 197.

**Nothing above is retracted.** v1–v4 and the sweep ran the pooled default,
which v5c refits to the same 3.16e7; the compartment mode remains default-off.

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

v4 (2026-09-16): fit `b5dd61d4-baa4-444f-ab44-c72642801040` (220 children),
held-out `a01111a4-192a-4a53-a7a3-c8fceae7215a` (11 children); job definition
`picard-covid-hull:4`, image `picard-campaign:covid-first-look-v4`, S3 prefix
`campaign/covid_first_look_v4/`.

Import sweep stage 1 (2026-09-16): array `54663e13-28e6-4957-ade7-fda67c5df76b`
(700 children, stride 1); job definition `picard-covid-boarding-screen:3`,
image `picard-campaign:covid-import-sweep-v1` built from `296fc82` (PR #551
branch, needed for the `points` / conditional-on-takeoff merge); S3 prefix
`campaign/covid_import_sweep_v1/`.

```bash
python3 tools/fit_covid_theta.py screen --cells <sweep v1 cells> \
  --design picard_framework/runs/covid_import_sweep_v1_design.json --out <s1.json>
python3 tools/fit_covid_theta.py refine --stage 2 \
  --design picard_framework/runs/covid_import_sweep_v1_design.json \
  --surface <s1.json> --design-id covid_import_sweep_v1r \
  --out picard_framework/runs/covid_import_sweep_v1r_design.json
```

v5 / v5c (2026-09-17): v5 fit `9b8d1ce7-e318-4987-853c-3c4d0c59f03f`
(220 children), v5 held-out `36cb4ee0-9440-4b8c-add8-211efc39a9ff` (11 children,
stride 50), v5c fit `94904a4c-2e85-42b2-b2a9-cfd5c3442123` (60 children), v5c
held-out `41dc98d9-f1cb-4a94-a2fb-bdae39a98b04` (3 children, stride 50); job
definition `picard-covid-hull:5`, image `picard-campaign:covid-first-look-v5`
built from `c6a3996` (PR #557 branch, needed for the `cabin_air_mode` seam and
the two design files); S3 prefixes `campaign/covid_first_look_v5/` and
`campaign/covid_first_look_v5c/`.

```bash
python3 tools/fit_covid_theta.py merge --cells <v4 cells> \
  --design picard_framework/runs/covid_first_look_v4_design.json \
  --fit-out telemetry_buffer/observation_model/covid_theta_fit_v5.json \
  --held-out-out telemetry_buffer/observation_model/covid_theta_held_out_v5.json
```
