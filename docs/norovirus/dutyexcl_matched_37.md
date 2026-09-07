# The regulated crew duty exclusion, measured: 17,280 matched voyages, and 13 postings

Status: measurement, 2026-09-05. Implements and then measures the mechanism
recorded in [`norovirus_open_ledger.md`](norovirus_open_ledger.md) §2 as the
crew arm's missing structure. Harness:
`../../telemetry_buffer/observation_model/dutyexcl_matched_37.py`. Read-out:
`../../telemetry_buffer/observation_model/dutyexcl_matched_37_v1_analysis.json`.
The 34,560 retained voyage rows behind it live in S3 under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/gate37_dutyexcl_off_v1/`
and `…/gate37_dutyexcl_on_v1/` (AWS Batch jobs
`2053e3e4-b67d-491b-a577-63128dfcdc66` and
`008935c1-bb9d-4932-bd90-5e31dc0db305`, job definition
`picard-bounded-design:6`, image `bounded-design-v6`); at 19 MB they are not a
result worth committing.

No parameter was moved, selected, or narrowed, and nothing here was fitted to
A9. The intervention is an operational rule with a regulatory source, run as its
own arm.

## 1. The rule, and what it is not

CDC VSP's 2018 Operations Manual **4.4.1.1.1** requires a crew member meeting
the AGE case definition off duty: food employees isolated until symptom-free for
at least 48 hours with a documented last-symptom time and medical approval
before returning to work, other crew for at least 24 hours. **4.4.2.1** only
*advises* the same of passengers. The model had the presenteeism half of that
asymmetry and none of the exclusion half — crew carry a ×2 service-zone contact
multiplier, 545.4 service-surface contacts/hour and a ×12.7 food-handler
multiplier, and SOP-008's symptomatic confinement is gated at `ALERT`, which the
quiet region never reaches.

`SOP-VSP-CREW-01` (`engines/crew_duty_exclusion.py`, PR #469) adds it as a
standing operational rule, **off by default** so every earlier campaign's
semantics are unchanged:

- it fires on the *first* identified symptomatic crew case, independent of
  escalation status, reusing `ever_reported_ids` so no second ascertainment
  probability is introduced;
- food employees are the crew whose work zone is one of the transmission core's
  existing service zones, held 48 h symptom-free; other crew 24 h;
- release is gated on the symptom-free clock in physical hours through
  `SimClock`, and a crew member independent escalation is also confining stays
  confined;
- passengers are untouched;
- no epidemiological constant, contact multiplier, shedding curve or dose
  parameter changed.

`compliance_fraction` is **1.0** in the arm measured here. That is the
enforced-regulation upper bound, declared as such: maritime compliance with
duty exclusion is null in the sourced literature, so a lower value would be a
number chosen to move A9. Any graded-compliance arm can only produce a *smaller*
effect than what follows.

## 2. The matched design

The baseline is the quiet corner of the #37 v2 box at the coordinates
[`lowposting_region_37.md`](lowposting_region_37.md) measured: the same twelve
grid indices `[0, 12, 18, 20, 36, 46, 126, 142, 145, 171, 172, 202]` of
`--sobol-m 8 --design-seed 37`, the same factor vectors, **1,440 seeds per
point** in 24 blocks, in the same order. The two arms differ in exactly one
thing: whether the rule is on. Because the seeds are common random numbers,
every voyage has a partner, so the comparison is paired and the harness refuses
a merge in which any point or seed is unmatched.

Both arrays completed **288/288 children, 0 failed**; each arm is 12 points ×
24 blocks × 1,440 unique seeds, no missing or duplicated block.

Two things had to be established before the arms could be compared at all, and
both are on the record:

- **The first submission was on the wrong grid.** It ran `--sobol-m 7
  --design-seed 17`, so its "point 46" was a different parameter vector. It was
  terminated and resubmitted; nothing from it is read.
- **The baseline is the archive.** Run *inside* the campaign image with the rule
  disabled, current `main` reproduces #467's archived rows exactly — 17,280 rows,
  0 differing — so the implementation is numerically inert when off. A *host* run
  does not: the image is Python 3.11.16 / NumPy 2.4.6 / SciPy 1.17.1 against the
  host's 3.12.8 / 2.5.0 / 1.18.1, and that difference alone moves voyages.
  **Campaign rows are only reproducible in the campaign image.** The in-image
  baseline re-run is used here rather than the archive.

## 3. What the rule moved

| | baseline | exclusion |
|---|---:|---:|
| voyages | 17,280 | 17,280 |
| posted (3% passengers **or** crew) | 793 | 780 |
| posting frequency | 4.589% [4.282%, 4.912%] | 4.514% [4.209%, 4.834%] |
| passenger-only | 270 | 272 |
| crew-only | 408 | 391 |
| both channels | 115 | 117 |
| quiet | 16,487 | 16,500 |
| crew at threshold, share of postings | 66.0% | 65.1% |

Thirteen fewer postings in 17,280 voyages. Paired, that is **51 voyages that
stop posting and 38 that start**, and McNemar's exact test on those 89
discordant pairs gives **p = 0.20**: at 1,440 seeds a point and 17,280 matched
voyages, a full-compliance, zero-clearance-delay duty exclusion produces **no
resolvable change in posting frequency**. No per-point difference resolves
either (smallest p = 0.39). The rule is real, it fires, and its effect on the
scored quantity is inside the noise of a campaign this size.

The channel it was aimed at moves the most and still barely moves: crew-only
postings 408 → 391, a net 17 voyages, against a crew-only share of 51.5% where
the observed record shows 0.5-9.3%.

Matched transitions, pooled (the 15 non-empty cells of a 4×4 table):

| | → quiet | → passenger-only | → crew-only | → both |
|---|---:|---:|---:|---:|
| quiet → | 16,449 | 8 | 26 | 4 |
| passenger-only → | 8 | 250 | 0 | 12 |
| crew-only → | 41 | 3 | 355 | 9 |
| both → | 2 | 11 | 10 | 92 |

Mean matched change in the principal outputs, with the share of pairs that moved
at all:

| output | mean change | pairs changed |
|---|---:|---:|
| crew infection attack rate | −0.0137 pp | 3.26% |
| crew ever-ill attack rate | −0.0089 pp | 2.99% |
| crew reported-case attack rate | −0.0090 pp | 3.00% |
| passenger infection attack rate | −0.0060 pp | 2.62% |
| passenger ever-ill (A1) | −0.0016 pp | 2.79% |
| passenger reported-case attack rate | −0.0014 pp | 2.77% |
| peak prevalence (concurrent cases, a count) | −0.017 cases | 1.77% |

Every mean is negative — the rule never helps transmission — and 97% of matched
voyages are numerically identical, which is what an intervention that only fires
after a crew case has been *identified* looks like.

## 4. Why it is this weak, and what that implicates

The mechanism was inspected directly in the campaign image at point 46 on seeds
that post crew-only. It behaves as specified: every reported crew case is
admitted to exclusion (12 admissions against 12 reported crew on seed 1366; 8
against 8 on seed 1344), and the first admission lands at epoch 59-93 of 168.

That timing is the finding. VSP's numerator is a *cumulative count of reported
cases over the voyage*, and with a 134-crew complement the threshold is five
cases. Duty exclusion removes forward transmission from a case that has already
been counted, and it cannot fire before the first case is identified, so it can
only ever prune the tail of the crew chain — and by the time the chain is
identified, most of the crew infections it would prevent have already happened.
An exclusion that starts at case one cannot retract cases one through five.

So, against the question it was implemented to answer:

- **Not sufficient.** The exclusion arm posts on 4.514% [4.209%, 4.834%]
  against A9's 0.42-0.56%. The interval is 7.5× above the anchor's ceiling and
  does not approach it.
- **Not necessary either.** Its measured effect on the posting rate is not
  distinguishable from zero (p = 0.20), so the A9 discrepancy is not explained by
  its absence, and adding it does not remove the discrepancy. It is a structure
  the regulated world has and the model was missing — worth having on its own
  terms, and it is not the A9 defect.

What that leaves implicated is upstream of the rule, and all three are testable
without moving a constant: the rate at which crew are *infected* (the exposure
multipliers, which a 36-seed leave-one-out probe could not resolve either), the
rate at which crew *cases are reported* relative to passengers, and the 3%-of-134
trigger itself — five cases on a small complement, where the observed series'
crew-only rows are one-case postings and no minimum-case publication rule is
sourceable from it.

## 5. What this does not show

The arms are 12 of 256 grid points, chosen as the quietest of the previous
gate — the quiet corner, not the box. A finite paired design cannot show that no
compliance value, clearance delay, or point of the continuous box would move A9;
it shows that at these coordinates, with the rule at its regulatory upper bound,
the measured effect is 13 postings in 17,280 voyages and not resolvable. The
non-result is a bound on this mechanism's leverage here, and nothing more.
