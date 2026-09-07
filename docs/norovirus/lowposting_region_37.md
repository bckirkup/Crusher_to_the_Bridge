# The quiet corner at 1,440 voyages a point: the posting floor is 3.2%, and half of it is crew

Status: measurement, 2026-09-05. Extends
[`admissible_region_37_v2.md`](admissible_region_37_v2.md) §3.6, which could only
bound the within-point distribution from cell means. Harness:
`../../telemetry_buffer/observation_model/gate37_lowposting.py`. Read-out:
`../../telemetry_buffer/observation_model/gate37_lowposting_v1_analysis.json`;
cell record: `../../telemetry_buffer/observation_model/gate37_lowposting_v1_cells.json`.
The 23,040 retained voyage rows it was computed from live in S3 under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/gate37_lowposting_v1/`
(AWS Batch job `da6965ec-ea4b-4ad7-b7ab-ae5cb706b406`, job definition
`picard-bounded-design:5`, image `bounded-design-v5`), and are 13 MB rather than
a result worth committing.

No parameter was moved, selected, or narrowed. Every number here is a count over
voyages that ran, with an exact binomial interval where it is a frequency.

## 1. What was run, and why these points

The #37 v2 gate scored 256 Sobol' points on 180 seeds each and kept **cells**,
so the question "what does a low-posting parameter set actually look like,
voyage by voyage" was unanswerable from the artifact, and 180 seeds cannot
resolve a 0.1% frequency at all (one posting in 180 is already 0.56%).

This re-runs **16 of those same grid indices** — same coordinates, same names,
same box — at **1,440 matched seeds each**, retaining one row per voyage
(`admissible_region.py --only-points … --seed-shards 24`, pooled by `--merge`,
which refuses a merge unless every point, block and seed is present). 384 array
children, 384/384 succeeded, 0 failed; 16 points × 24 blocks × 60 rows, no
duplicate block, 1,440 unique seeds per point. Resolution is 1/1440 = 0.069%,
so a frequency inside A9's target band of **0.42–0.56%** is now expressible.

The 16 are the 12 quietest cells of the 256 (6–8 postings in 180), 2 at the
quiet/A1 transition (9 in 180), and 2 inside A1's band as comparators.

## 2. The floor

| group | points | voyages | posted | frequency | exact 95% |
|---|---:|---:|---:|---:|---|
| quietest | 12 | 17,280 | 793 | **4.589%** | 4.282–4.912% |
| transition | 2 | 2,880 | 169 | 5.868% | 5.038–6.790% |
| A1 band | 2 | 2,880 | 2,875 | 99.826% | 99.595–99.944% |

The single quietest point of the whole box, index 46, posts **46 of 1,440 =
3.194% [2.348%, 4.238%]**. Its interval's *lower* bound is 4.2× A9's ceiling, so
this is not a resolution artifact of the 180-seed gate: the 1,440-seed
frequencies reproduce the 180-seed counts point for point (6/180 → 3.19%,
7/180 → 3.82–4.58%, 8/180 → 4.17–5.63%), which also says the twelve were not
selected by noise. **No point in the sample approaches 0.1%, and none of the
sixteen intervals contains A9's band.**

## 3. What the 1,440 seeds buy that 180 did not

**Extinction exists, and is rare.** #37 v2 reported take-off at 1.0 for all 256
points; at eight times the seeds, **45 of 17,280 quiet-region voyages (0.26%)**
fail take-off — peak prevalence 9 against the threshold of 10. So the model can
fizzle, at a rate two orders of magnitude below the ~99.5% quiet fraction A9
needs, and take-off remains distinct from posting.

**Every voyage infects someone.** In the quiet region the infection attack rate
has **zero mass 0.000** and a median of 5.38% (5–95%: 3.16–8.86%). The ever-ill
rate is exactly zero on **55.8%** of voyages and the reported passenger rate on
**66.6%**. The bimodality §3.6 inferred from cell medians is confirmed on rows:
the typical quiet voyage is not a small outbreak, it is ~5% infection with no
ill passenger.

**Conditional on posting, the outbreak is the right size — now measured, not
bounded.** §3.6 could only put a ceiling of ≤6.0% on the conditional mean. Among
the quiet region's passenger-channel postings the reported passenger attack rate
is median **4.11%**, IQR 3.48–5.06%, max 10.76% — inside A4's posted-outbreak
IQR of 3.55–7.49%. The frequency is wrong; the magnitude is not.

Voyage classes, quiet region, pooled (each voyage in exactly one):

| class | voyages | share |
|---|---:|---:|
| no infection | 0 | 0.00% |
| infected, no illness | 9,522 | 55.10% |
| ill, nothing reported | 1,862 | 10.78% |
| reported, below threshold | 5,103 | 29.53% |
| posted | 793 | 4.59% |

## 4. Half the postings are crew, and the crew denominator is coarse

The posting rule is an `or` over two complements. Splitting the quiet region's
793 postings by which one crossed 3%:

| channel | postings |
|---|---:|
| crew only | 408 (51.5%) |
| passenger only | 270 (34.0%) |
| both | 115 (14.5%) |

The crew complement is **134**, so the crew reported attack rate moves in steps
of 0.746% and **5 reported crew cases (3.73%) post a voyage**. Passenger side,
the step is 0.316% over 316 passengers and posting takes 10 cases. Counting only
the passenger channel, the quiet region posts on 385 of 17,280 voyages =
**2.228%** — still 4.0× A9's ceiling, so the crew channel is not the cause of
the excess, but it carries the majority of it through a five-case trigger on a
small denominator.

Two consequences worth separating:

1. The ship's own VSP trigger (`vsp_trigger_epoch`) is set on exactly the
   passenger-channel voyages and on no crew-only one — zero disagreements over
   all 23,040 rows — while the scorer's A9 counts both. The scorer is right
   about VSP's rule (3% of passengers *or* 3% of crew) and the in-sim trigger is
   the narrower of the two; the disagreement is a definitional gap in the
   simulation's trigger, not a parameter.
2. A9's excess should not be attributed to any single route until the crew
   channel's five-case granularity is stated: at n=134 the anchor's own target
   band (0.42–0.56%) is finer than one crew case.

## 5. What this licenses, and what it does not

- **Licensed:** within the sampled box, the region containing the lowest posting
  frequencies posts at 3.19–6.32% per point, every one of the sixteen exact
  intervals excludes A9's 0.42–0.56%, and the shortfall is a frequency
  shortfall, not a magnitude one — posted voyages land inside A4's IQR.
- **Licensed:** the quiet region's mass is symptomless infection (55.1%) and
  sub-threshold reporting (29.5%), not absent transmission (0%).
- **Not licensed:** "no parameter set can post at 0.1%." Sixteen points of a
  256-point Sobol' sample of a continuous ten-factor box is a sample; nothing
  here is a proof of emptiness, and no point was chosen for how it scored.
- **Not done, deliberately:** no constant moved, no interval narrowed to the
  quiet corner, no seed set truncated, and no posting rule relaxed to bring A9
  into reach.

Follow-ups, in the order they change the verdict:

1. The missing symptom-conditioned spreading-efficiency term (tranche 31) is
   still the binding gap: 55% of quiet voyages carry ~5% infection with zero
   ill passengers, so the model already separates infection from illness — what
   it does not do is make that separation change transmission.
2. State A9's conditioning on the crew complement, or score the two channels
   separately; at 134 crew the anchor band is sub-case.
3. Give the in-sim VSP trigger the crew arm the scorer already applies, so
   `vsp_trigger_epoch` and A9 count the same event.
