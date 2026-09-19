# NORO-EMESIS-CANARY-01
**Date:** 2026-09-19
**Commit:** 204ba42
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 204ba42

Bounded recovery canary for the replicated emesis study after three successor
sessions failed operationally. This entry declares the criterion before any
cell runs. It does not size an event rate or hull effect.

## Settled inputs

- `NORO-SUSCEPT-02`, measured at `9f4cd79`: the `classic_cruise_1900`
  8105/8106 reference dumps at 288 epochs.
- `NORO-SUSCEPT-03`, measured at `f5f9ff3`: alpha is closed.
- `NORO-DOSE-01`, measured at `f55e93f`: emesis sizing is the next recommended
  study; no constant change is licensed.
- `RNG-FRAILTY-STREAM-01`: no arm may move `dose_response.alpha` or `.beta`.

## Design frozen before execution

| Item | Declaration |
| --- | --- |
| Code | main `204ba42` |
| Instrument | `tools/noro_diag/per_host_dose_challenge.py`, read-only wrappers |
| Pathogen bundle | shipped default (`active_profiles`) |
| Seeds | matched pair 8105/8106 |
| Classic cell | `classic_cruise_1900`, declared complement 1,910, 288 epochs |
| Expedition cell | `expedition_cruise_450`, declared complement 450, 168 epochs |
| Forbidden | alpha/beta override; constant, profile, or engine change |
| Output | hull-specific subdirectories under `docs/norovirus/noro_emesis_canary_01/` |

Hull-specific output directories are mandatory: the instrument filename
contains the seed but not the platform, so a shared directory would overwrite
one hull's dump with the other.

## Pre-declared criteria

### Audit A: current-main classic replay

Compare the current-main classic 8105/8106 results with the
`NORO-SUSCEPT-02` reference on these fields:

- `emesis_events`
- `patch_mass_gec`
- `patch_pickup_dose_gec`
- summed evaluated hazard
- credited-scaled GEC

Exact equality is a **replay pass**. Any difference is a **replay failure** and
means the 20-seed prompt cannot be run as written against current main; report
the changed field and stop before claiming an event-rate estimate. Because
this canary spans commits, a failure is drift detection, not attribution.

### Audit B: mechanism-fired gate

For each hull:

1. both seeds must have non-zero `surface_mass_deposited_gec`; otherwise that
   seed is void;
2. the pair must contain at least one `emesis_event`; otherwise the emesis
   canary is unexercised for that hull and no emesis conclusion is allowed;
3. any seed with an event must have non-zero `patch_mass_gec`; a zero value is
   an instrument/engine defect;
4. patch pickup is allowed to be zero conditional on an event, but must be
   reported with `matched_unit_susceptible` and `patch_pickup_calls` so “no
   exposed recipient” is separated from “pickup moved no mass.”

### Firm output

- **GO** to the full 20-seed-per-hull study only if Audit A passes and Audit B
  is exercised without a defect on both hulls.
- **REVISE** the design if replay passes but one hull is unexercised: first run
  additional matched seeds until each hull has at least one event, then freeze
  the full seed list.
- **NO-GO** if replay fails or a mechanism witness is inconsistent. Repair the
  prompt/instrument contract before any long run.

The pair is a mechanism smoke only. Event fractions, means, medians, route
shares, secondaries, attack rates, host concentration, and individual draws
are reported but never used to size an effect or select a parameter.

## Stop condition

Commit this entry with the four dumps, a measured two-hull table, and one firm
GO / REVISE / NO-GO recommendation; open one PR and stop. Do not continue into
the 20-seed study in this session.

## Measured result

Measured at `204ba42`. Dumps under
`docs/norovirus/noro_emesis_canary_01/<hull>/`. Two matched seeds per hull,
plus two additional expedition seeds (8000/8001, `expedition_probe/`) run after
the declared pair returned no emesis witness; those two are diagnostic
replicates of Audit B only and are not used to size anything.

### Audit A: classic replay — PASS

| Field | `NORO-DOSE-01` at `f55e93f` | Here at `204ba42` |
| --- | --- | --- |
| seed 8105 credited scaled GEC | 0.100952 | 0.100952 |
| seed 8105 Σ evaluated hazard | 3.80909e-4 | 3.80909e-4 |
| seed 8105 emesis events | 1 | 1 |
| seed 8105 patch mass GEC | 1.9618e6 | 1961773.805 |
| seed 8105 patch pickup dose GEC | 2.610 | 2.6101716 |
| seed 8105 patch pickups | 2 | 2 |
| seed 8106 Σ evaluated hazard | 1.1871e-5 | 1.1871e-5 |

The instrument and engine have not drifted on the reference hull across the 25
commits between `f55e93f` and `204ba42`. The classic cell is sound.

### Audit B: mechanism-fired gate — FAIL on expedition

| Hull | Seed | credited GEC | surface deposited GEC | surface offered GEC | `phase_eligible` | emesis events |
| --- | --- | --- | --- | --- | --- | --- |
| classic | 8105 | 0.100952 | 220.318 | 5170.378 | 24 | 1 |
| classic | 8106 | 2.71299e-3 | (fomite fired, offered 3.867) | 3.867 | 0 | 0 |
| expedition | 8105 | 0 | 0 | 0 | 0 | 0 |
| expedition | 8106 | 8.096e-221 | 5.95e-218 | 9.02e-217 | 0 | 0 |
| expedition | 8000 | 0 | 0 | 0 | 0 | 0 |
| expedition | 8001 | 2.133e-32 | 25.943 | 3.28e-28 | 0 | 0 |

Three measured facts on `expedition_cruise_450` at 450 agents, 168 epochs:

1. **Emesis is structurally unexercised.** `phase_eligible` is 0 on all four
   seeds — every one of the 75,600 emit calls per voyage was phase-blocked, no
   schedule was ever drawn, and no host ever entered the emesis-eligible phase.
   The hull carries one norovirus import per voyage and none of the four
   imports became emesis-eligible inside 168 epochs. Audit B criterion 2 fails,
   so no emesis quantity may be reported for this hull.
2. **Two of four seeds are void** (8105, 8000): zero `norwalk_gi` accumulate
   calls and zero surface deposit, i.e. no dose path at all.
3. **The two non-void seeds are physically degenerate and internally
   inconsistent.** Credited totals of 8.1e-221 and 2.1e-32 GEC are not small
   effects; they are underflow-scale. Seed 8001 deposits 25.943 GEC to surfaces
   yet offers only 3.28e-28 GEC at pickup, while classic 8105 deposits 220.3
   and offers 5170.4. Mass deposited and mass offered do not reconcile on this
   hull. The engine's own `max_hand_target_gec` on 8001 is an ordinary 12.97
   against a hand load of 1.7e-29, so the collapse enters between target and
   load, not at the layout level; `classic_cruise_1900` and
   `expedition_cruise_450` have structurally comparable Sanitary and
   Cabin_Corridor zone sets.

Fact 3 is a **defect signature, not an attribution**. This canary spans
commits and cannot separate "the expedition chain is broken" from "the
expedition chain took a different path"; that requires the paired-seed
distribution at one commit. It is declared as `NORO-EXP-FOMITE-RECONCILE-01`
below and is not diagnosed here.

## Verdict: NO-GO on the two-hull design as written; REVISE to classic-only

The pre-declared decision rule gives NO-GO because Audit B is not exercised on
expedition and a mechanism witness is internally inconsistent there. Concretely:

- The withdrawn `NORO-EMESIS-SIZE-prompt.md` would have spent ~22 expedition
  voyages measuring an emesis event rate of exactly 0 on a hull where the
  mechanism cannot fire, and would have written both hulls' dumps into one
  directory under filenames that carry the seed but not the platform, silently
  overwriting one hull with the other. That prompt is removed in this change.
- `classic_cruise_1900` is GO on its own: it replays exactly, emesis fires, and
  the full witness chain is present.

The recommended next step is a **classic-only** `NORO-EMESIS-SIZE-01` at 20
paired seeds, unchanged in every other respect (shipped bundle, no alpha or
beta override, hull-specific output directory), with expedition deferred behind
the reconciliation study. Whether expedition belongs in an emesis design at all
is downstream of that study, not of a larger seed count.

## Declared follow-ons (not executed here)

1. **`NORO-EXP-FOMITE-RECONCILE-01`** — why `expedition_cruise_450` deposits
   ordinary surface mass and offers underflow-scale mass at pickup, and whether
   `phase_eligible = 0` is the 168-epoch horizon, the single-import design, or
   a gate. Paired seeds at one commit; classic as the control arm.
2. **`NORO-EMESIS-SIZE-01`** — classic-only replicated emesis sizing, 20 paired
   seeds, gated on nothing further.
3. `NORO-CARRIER-REDEPOSIT-01` and `NORO-TRANSFER-PRODUCT-01` carry over from
   `NORO-DOSE-01` unchanged.

No constant, profile, engine path, or test was changed by this entry.
