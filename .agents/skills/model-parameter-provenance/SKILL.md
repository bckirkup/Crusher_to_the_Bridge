---
name: model-parameter-provenance
description: Discipline for changing any epidemiological constant, rate, fraction or kernel in the transmission and natural-history model — sourcing, evidence grades, no-tuning rules, how to handle a moved golden, and the recurring defect archetype to look for first. Use when adding, replacing or re-deriving any physical constant, or when a model output misses a literature anchor.
---

# Model Parameter Provenance

Use this skill before changing any constant that claims to represent a physical
or behavioural quantity: transmission rates, transfer fractions, contact
kernels, decay rates, titres, areas, volumes, deposition fractions, shedding
curves, or clearance rates.

It exists because a year of "the model reproduces VSP attack rates" turned out
to rest on one fitted scalar absorbing at least two order-of-magnitude errors in
the mechanisms beneath it. The full record is `docs/norovirus_model_history.md`;
the live status of what is currently withdrawn is `docs/norovirus_open_ledger.md`.
Read the ledger before quoting any dose figure.

## The first rule: do not fit to the target

The model is scored against literature anchors (A1-A5), the VSP attack-rate
distributions, Park's surface-contamination measurements, and the observed
passenger/crew ratio. **No constant may be chosen to make any of those come
out right.** Not by search, not by hand, not by picking the end of a plausible
range that happens to help.

One fitted parameter can always match one number. Matching a target is
therefore not evidence that the mechanism is correct, and the whole point of
sourcing a constant independently is that the comparison afterwards is a real
test. Fitting it first destroys the only test you had.

If a sourced constant makes an anchor worse, **that is a result — report it**.
It says something is still missing, which is information. Silently choosing a
friendlier value converts information into a number that agrees with you.

Corollary: when a measured range is wide, take a stated central value or the
midpoint and say which. Do not take the end that helps.

## Every constant carries its provenance at the point of definition

A comment at the definition, not in a doc that will drift:

```python
SURFACE_CONTACTS_PER_HOUR = {
    # University dormitory primary shared surfaces, 10.4-25.4/h; midpoint.
    # Yuan et al. 2024, Building and Environment. Grade B.
    "cabin": 17.9,
    ...
}
```

State three things: **what was measured**, **in what setting**, and the
**evidence grade**. Grades used here:

- **A** — direct measurement of this quantity in this setting.
- **B** — direct measurement in an analogous setting (hotel lobby for a cruise
  lounge; dormitory for a cabin).
- **C** — inferred, estimated, or a declared assumption. Every Grade C constant
  is a standing liability and must be listed in the history document's
  "held fixed by assumption" section.

If no source exists, say so explicitly rather than inventing a plausible
number. Total high-touch surface area per room in m² has never been measured by
anybody — `HIGH_TOUCH_AREA_M2` is a permanent Grade C declaration and is
labelled as one. Knowing a gap is the field's rather than ours is worth
recording.

Watch the definition of the quantity, not just its magnitude. Behavioural
touch studies report an all-surface rate and a shared-surface rate that differ
by 10x; only the shared-surface one drives fomite transmission. Taking a
headline figure without checking what it counted is the same error as having no
source.

## Delete superseded constants; never alias them

When a constant is replaced, delete the old name and fix every reader. Do not
leave a compatibility alias. PR #351 left a dead `_decay_hand_load` behind and
a test went on asserting against dead code for a full PR cycle. A stale
duplicate of a corrected constant is how a correction silently fails to apply.

`grep` for the old name across `tests/`, `telemetry_buffer/` and `docs/` before
committing — measurement scripts and specs read these constants too, and a
measurement script that still reads the old value will report a stale result
with full confidence.

## Re-run the out-of-sample check, and record before/after

Changing a constant invalidates the measurements taken under the old one.
Re-run the relevant harness (`telemetry_buffer/observation_model/`) and record
the before and after side by side in the PR, against the observed target. A
measurement that moved and was not reported is indistinguishable from one that
was not taken.

Transcribe those numbers carefully. A misread baseline that turns a 3.9x rise
into a 25x fall inverts the sign of the finding, and the wrong version is the
one that gets quoted downstream.

## A golden may move — attribute it before you touch it

Numeric expectations legitimately change when the model changes. But:

1. **Never** edit an assertion so that output matches. That is fitting the test
   to the code.
2. Attribute the move to a **specific** change first, by reverting one part of
   your diff at a time and re-running. "It's probably the new kernel" is not
   attribution.
3. Update the expectation to the new value and comment why. Do not relax it to
   an inequality to make it robust — that discards the change detector.
4. If you cannot attribute it, **stop and escalate**. An unattributed baseline
   move is a possible defect, not a chore.

Repo rule, from `AGENTS.md`: do not modify tests to make them pass. This is how
that rule is applied when the model itself has legitimately changed.

## The recurring defect archetype

Five separate routes have now failed the same way, in five different
mechanisms:

> **A well-mixed pool standing in for a small number of concentrated events.**

- Direct contact delivered the zone-average dose rather than the dose from the
  partners actually contacted (#329).
- The fomite pool spread surface mass over the whole deck footprint and sampled
  a fingerpad from it (#350, #351).
- Vomiting did not exist at all; continuous faecal shedding stood in for a
  discrete 10^7-copy event (#352).
- Cabins are not environmental compartments: a `Cabin_Corridor` zone mixes ~37
  people in 800 m³ where reality is 2 people in ~40 m³ (open).
- The dose-response was evaluated per epoch, re-drawing host susceptibility
  hourly and treating each hour as a fresh person (#346).

**Look for this first.** When an anchor cannot be reached at any parameter
value, the usual cause is that a concentrated process has been replaced by its
mean. Rescaling a uniform process cannot recover a patchy one, so no amount of
tuning the aggregate will fix it — which is exactly why these defects survived
so long behind a fitted scalar that kept the aggregate looking right.

The diagnostic question: *is the real thing a smooth flow, or a small number of
large events?* If the latter, a per-zone pool is the wrong representation
regardless of whether its mean is right.

## Before you claim a constant explains anything

- Changing a constant and getting closer to a target is not validation. It is
  one number moving toward another number.
- A mechanism is necessary-for an anchor until shown sufficient-for it. Say
  which you have shown.
- Distinguish measured, inferred, and assumed in every claim. If a result rests
  on an unmeasured quantity (how much of a host's vomiting happens in its own
  cabin, say), report the sensitivity sweep and refuse to read the value off the
  target.
- Keep the count of fitted parameters visible. The defect was never the
  pedigree of any single knob; it was having one free parameter and several
  anchors, so the knob absorbed every mechanism error at once.

## Standing prior

Twelve distinct unit, dimension, time-origin, sign, scoping or magnitude
defects have been found in this effort, most by chasing an anomaly rather than
by a check designed to catch them. Every campaign before v4 was invalidated by a
defect found after it ran. Assume further defects exist; absence of a new
finding is not evidence of correctness. When a result looks good, that is the
moment to check the units.
