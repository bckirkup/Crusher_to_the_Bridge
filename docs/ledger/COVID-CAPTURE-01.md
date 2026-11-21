# COVID-CAPTURE-01
**Date:** 2026-11-21
**Commit:** 7b34405d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 7b34405d

Capture-rate leg of the `covid_theta_handoff_2026_11_20.md` Θ-on-DP
question: COVID-H5-RESCORE-01 measured that at the truth-in-band θ
(≈3–5e8) the specimen layer confirms ~0.60 of infections vs the
record's ~0.85, and named the per-infection capture rate as the lever
that makes any Θ scorable on DP. This entry measures
confirmed-per-infection at θ=3.162e8 (`dp_theta_8p50`, 20 DP
`boxed_s1s2` cells, seeds 20200205–24, committed
`funnel_echo` payloads — same realizations as THETA-REFIT-01, pure
readout, no re-run) by
`tools/covid_capture_rate_readout.py`; evidence
`reports/capture_01/dp_theta_8p50_capture.json`. The takeoff gate is
the scorer's (`recorded_onsets >= 10`): 16 takeoff cells.

## Result — the capture deficit is an incidence-timing deficit, not a specimen-machinery deficit

**Pooled takeoff:** 17,241 infections, 12,464 lab_confirmed →
capture 0.723 pooled, 0.525 per-cell median — the wide gap between
the two is itself the finding: capture is bimodal by incidence
timing, so the pooled figure hides a near-deterministic split.

| median infection day | cells | capture (per-cell) |
|---|---|---|
| 14 (record-timed) | 20200212, 20200219, 20200222 | **0.911, 0.926, 0.930** |
| 23–30 (late-peaking) | the other 13 takeoff cells | 0.138–0.694 |

The record's incidence peaked model-days 13–15 (at confinement,
`dp_growth_cooling_bound.md`). The three cells whose incidence
matches that shape already confirm **>0.91** of infections — above
the record's ~0.85 — with the specimen machinery exactly as
declared. The other cells peak days 25–34, inside/after the campaign
window; the same machinery then structurally cannot reach them.
Capture on DP is a readout of incidence timing, full stop.

**Drain decomposition of the 4,777 unconfirmed (pooled takeoff):**

| drain | hosts | infected days 25–34 |
|---|---|---|
| sensitivity_miss (swabbed while infected, last draw missed) | 2,717 | 87% |
| starved_never_swabbed | 1,469 | 80% |
| starved_pre_infection_negative (early negative, never re-swabbed) | 591 | 95% |
| tail_infected (infected after last campaign day 34) | 0 | — |

Where the sensitivity misses fall: 2,238 of 3,328 while-infected
campaign swab-draws on missed hosts landed at dpi 0–4 (declared
Kucirka sensitivity ≤0.33); 2,388 of the 2,717 are `miss_exhausted`
— the declared retest tiers ran out before these hosts reached
detectable dpi, vs 329 `miss_starved_retest` (a later campaign day
existed and did not reach them).

**Realized vs declared-curve calibration (per-draw, unbiased):**
23,369 while-infected specimen draws on the 15,181
swabbed-while-infected hosts → 10,822 realized negatives vs 12,276
declared-curve expectations — draws miss at **0.88×** the declared
rate, i.e. the assay detects at-or-above its declared sensitivity.
(The calibration is per-draw, not serial: confirmed hosts' draw
sequences truncate at first positive, so a serial-escape expectation
over observed draws would be outcome-biased.) The gap is not in the
observation machinery; it is that right-sized-Θ incidence peaks
~10–15 days too late for the declared test window.

**Bound on any observation-seam lever:** a universal exit swab at
the last campaign day (day 34) has declared-curve expectation
+1,337 captures → capture ≈0.80 pooled; even *perfect* detection of
every infected reaching dpi ≥5 adds at most the ~1,653 unconfirmed
hosts infected ≤ day 29 → ≈0.82. Either way it falls short of ~0.85
because ~3,100 unconfirmed infections (65% of the unconfirmed pool,
18% of all infections) sit at dpi ≤4 on the last campaign day —
unreachable at declared sensitivities by any in-voyage specimen
structure.
Real roster-reach residual (reachable-dpi hosts the declared
rosters never touch): ~660 hosts (~3.8% of infected — 260
never-swabbed infected ≤ day 24, ~330 missed despite a later
campaign day, ~70 pre-infection-negative infected ≤ day 24).

## Seam design — declared

The capture lever named by H5-RESCORE-01 is hereby re-located:
**specimen structure is not the seam.** Confirmed-per-infection on
DP is a two-factor score — incidence timing × specimen structure —
and the measurement above shows the specimen factor already
delivers ≥0.85 whenever incidence matches the record.

Declared seam for the next leg: **quarantine-shoulder incidence
timing** — why right-sized-Θ incidence peaks days 25–34 where the
record peaked days 13–15 at confinement. Hypothesis (untested, do
not quote as result): the confined-stratum transmission arrest
fires too weakly or too late — the record's Feb 5 confinement was
mid-growth and cut incidence within ±2 days; the boxed_s1s2
confinement lands day 16 but infection keeps climbing for ~10+ more
days. This is the same incidence-lag H5-RESCORE-01 flagged on the
serology side; CAPTURE-01 adds that it also is the entire capture
deficit.

Contract consequence (declared, owner-signable): a
confirmed-per-infection observable cannot be scored on DP
unconditionally — at any θ the score conflates the two factors. If a
capture contract is wanted it must be conditioned on incidence
timing, e.g. `confirmed / infections_reachable` where
`infections_reachable` = infected ≥5 days before the last campaign
day; unconditioned, the observable scores transmission timing and
belongs with the H5 timing tail, not the observation layer.

## Non-results

- No evidence of a specimen-sensitivity hotness defect: realized
  per-draw misses (10,822) run at 0.88× the declared-curve
  expectation (12,276).
- Tail-infection drain is zero; every infected host had at least
  one campaign day at-or-after infection day.
- Record anchor ~0.85 confirmed-per-infection is **not** a property
  of the serial-retesting structure alone — it requires the
  record's pre-confinement incidence peak. Any design that raises
  capture by strengthening retesting alone is bounded at ≈0.82 and
  would be fitting machinery to a timing artifact.
