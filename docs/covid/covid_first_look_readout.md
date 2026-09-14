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
worker and **1,718 onsets** rerun locally (1,104 s wall). Between `b38e5ba`
and `654c0a4` the engine's initiation, boarding and RNG-stream code moved for
the norovirus thread (`c823ea4`, `e98c68f`, `4d059c5`, `ef4c8d9`, `29ba558`,
`d44e01e`, among others). The most likely reading — not yet bisected — is
that the COVID arm inherited those changes with no COVID-side check, and its
effective transmission scale shifted by more than a decade.
`covid_theta_fit.json` is therefore a record of a previous engine, not a
result to compare against; this readout supersedes it.

The 1,795 vs 1,718 gap at an identical Theta, seed and commit is a second,
smaller finding: a fixed-seed hull run is **not bit-reproducible across
hosts**. Something in the run consumes entropy outside the seeded stream
(hash ordering, thread count, or an unseeded RNG). It does not affect the
campaign conclusions — all of them rest on 20–50 seed distributions — but it
must be found before a change-detector cell can be pinned to an exact value.

These are the first two items for the ledger: **the COVID arm needs a
change-detector cell** — one Diamond Princess run at a fixed Theta and seed,
in the fast test tier or a nightly, so an engine change that moves the
respiratory arm is seen when it lands rather than at the next campaign — and
the cell has to be host-reproducible first.

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

1. **Engine change-detector for the COVID arm** (above). Cheap; do it first.
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
