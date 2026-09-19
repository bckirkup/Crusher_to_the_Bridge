---
name: stochastic-attribution
description: How to attribute a measured move in this seed-sensitive, float-sensitive model — paired seeds as the floor (8105/8106 for norovirus), replicate counts when the outcome is rare-event driven, declaring the attribution criterion before the run, and separating a real effect from RNG-stream disruption when a diff reorders draws. Use whenever a baseline, golden or campaign number moves and the question is what moved it, or when designing a run whose purpose is to attribute a difference.
---

# Stochastic attribution

The repo rule is in `AGENTS.md`: *"When a model change legitimately moves a
numeric expectation, attribute the move to a specific part of your diff before
updating it; an unattributed baseline move is a possible defect."* This skill
is how to satisfy that rule in a model where a last-bit float change anywhere
on the transmission path re-rolls every later Bernoulli draw.

## Why single seeds cannot attribute anything here

Measured, in `docs/covid/covid_first_look_readout.md`: CPython 3.12 switched
builtin `sum()` on floats to compensated (Neumaier) summation, and the
route-dose, shedding and aerosol totals in `engines/transmission_core.py` go
through `sum()`. Same seed, same code, two interpreters: **1,795 vs 1,718**
recorded onsets; 96 vs 85 on the Greg Mortimer cell. That is a 5-13% move from
*nothing but float association order*.

So any diff that touches a float on the transmission path — including a diff
that is mathematically a no-op — moves a single-seed trajectory. A single-seed
difference is therefore not evidence of an effect, and this is not a subtlety
you can eyeball your way past.

**The failed bisect.** The same readout records a first-parent bisection of a
truncated Diamond Princess cell across the 86 merges between `b38e5ba` and
`654c0a4`, reading 707 (`9fafcc9`, #443), 604 (`3fff70c`, #486), 569
(`461be35`, #496), 502 (`bd634e2`, #507), 502 (`654c0a4`, #529). Several
expensive single-seed probes, a graded drift with no single step, and **no
attribution**: the bisection could not separate "the engine's scale changed"
from "the same engine took a different path". It was stopped there, with the
conclusion that attributing the move needs the 20-seed distribution — a Batch
job, not a local probe. Do not repeat this bisect shape. If your attribution
plan is a sequence of single-seed runs across commits, it will not answer the
question no matter how many you run.

## The floor: paired seeds

Every contrast is run on **matched seeds** — the same seed list on both arms,
compared seed by seed, never arm-mean against arm-mean from different seeds.
The norovirus pair in use is **8105/8106**; the flush sweeps use matched
blocks (`8000-8199`, 200 paired seeds), and the readouts report "paired
contrasts (arm − off, seed by seed)" — see
`docs/norovirus/flush_sweep_v1_stage2_readout.md` and the stage findings.

Pairing removes the between-seed variance that dominates everything else here.
Report the paired difference and its interval (the flush readouts use the 95%
normal-approximation interval on the mean paired difference), and report the
number of discordant pairs when the outcome is binary
(`docs/norovirus/dutyexcl_matched_37.md` reports p = 0.20 from discordant
pairs at 1,440 seeds).

Two paired seeds is the **floor for a smoke** — enough to show a mechanism
fires, never enough to size an effect.

## Replicate counts when the outcome is rare-event driven

Voyage outbreaks here are rare-event driven: most voyages extinguish, a
minority burn. The mean is carried by the tail, so the replicate count is set
by how often the event happens, not by how precise the mean looks.

Working numbers from this repository, to size against:

| Question | Replicates actually used |
|---|---|
| Does the mechanism fire at all (smoke) | 1 paired pair (8105/8106) |
| Arm contrast on a common outcome | 100-200 paired seeds (flush stages 1-4) |
| Arm contrast on a rare outcome / VSP crossing | 180-200 paired seeds per point (`admissible_region_37_v2`: 256 points × 180 seeds) |
| Attributing a commit-to-commit move | the full distribution, ≥20 seeds per cell, as a Batch job |
| Matched exclusion contrast on discordant pairs | 1,440 seeds (`dutyexcl_matched_37`) |

If the arm's event rate is `p`, a paired design needs enough seeds that the
expected number of *discordant* pairs is comfortably above a handful; at
p ≈ 0.03 (the VSP threshold-crossing scale) that is hundreds, not dozens.
Compute that number before the run and put it in the design file.

## Declare the attribution criterion before the run

Write into the design file (`.agents/skills/campaign-preflight/SKILL.md`
Rule A), before any cell runs:

- the arms and the exact matched seed list;
- the statistic (mean paired difference, ratio of means, crossing fraction);
- the threshold that will be called an effect, and the interval that will be
  called a null;
- which quantities are reported and never selected on.

`docs/covid/covid_theta_screen_v7_readout.md` records that no criterion was
altered after the surface was seen; that is the standard. A threshold chosen
after looking at the surface measures the surface, not the mechanism, and the
resulting claim cannot be defended in a readout.

Note also that a **measured null is a result**: the stage-2e emesis
berth-share repair is recorded as "a measured null at 200 paired seeds", with
the interval reported. Declare the null band in advance so you can say that.

## Real effect vs RNG-stream disruption

When a diff reorders or adds draws, the two arms are no longer walking the
same random stream, and every downstream draw differs even where the mechanism
is untouched. Distinguish the two causes in this order:

1. **Is the diff stream-neutral?** If the change adds, removes or reorders any
   `self.rng.*` call on a path both arms execute, it is not. A default-off
   feature flag is the cheapest way to keep it neutral: the `off` arm must
   consume exactly the draws it consumed before the diff. The repo's labelled
   baselines exist for this (`cabin_air_mode: zone_pool`,
   `droplet_emission_mode: shipped_uniform`,
   `pathogen_pool_transport: none`, `near_field_air: off`) — each is "the
   labelled pre-change baseline", kept so a contrast can be run against the
   current engine rather than against an old commit.
2. **Run the null contrast.** Run the new code with the feature *off* against
   the pre-change code on the same paired seeds. If those two differ, the diff
   disturbed the stream (or is not a no-op), and no arm contrast from it is
   interpretable until you know which. This is far cheaper than a bisect and
   answers a question a bisect cannot.
3. **Only then read the arm contrast**, on-vs-off within the new code, on the
   same paired seeds.
4. **If the stream cannot be preserved** — a genuine reordering — attribution
   needs the distribution: same cell, ≥20 seeds (more if rare-event driven),
   both commits, and compare distributions, not trajectories. Expect graded
   drift of 5-13% from stream disruption alone and treat anything inside that
   band as unattributed.
5. **Pin the interpreter.** The Batch image is CPython 3.11; a local venv may
   be 3.12. Never compare a local number with a Batch number. Each interpreter
   is bit-reproducible on its own; swapping numpy 2.5.0 ↔ 2.4.6 and scipy
   1.18.1 ↔ 1.17.1 changes nothing, so the interpreter is the variable to
   control.

## What to do with an unattributed move

Per `AGENTS.md`, an unattributed baseline move is a **possible defect**, not a
new baseline. Do not update the golden. Instead:

- open a ledger entry under `docs/ledger/<ID>.md` recording the old and new
  values, the paired-seed design that measured them, and the stream-neutrality
  check;
- state explicitly that the move is unattributed and what run would attribute
  it (usually: the distribution at both commits);
- carry it into the handoff as evidence-against
  (`.agents/skills/session-handoff-ledger/SKILL.md`);
- if a golden must move to unblock CI, say in the same change which part of
  the diff moved it — and if you cannot, that is the finding.

## Related

- `.agents/skills/ci-test-design/SKILL.md` — graded-sensitivity tests instead of brittle single-seed goldens.
- `.agents/skills/model-parameter-provenance/SKILL.md` — moved goldens and the no-tuning rule.
- `.agents/skills/campaign-preflight/SKILL.md` — freezing the criterion and the seed list in the design file.
- `.agents/skills/transmission-blocker-cascade/SKILL.md` — before attributing a zero, check whether the expected count was ever above one.
- `docs/covid/covid_first_look_readout.md` — the interpreter result and the failed bisect.
