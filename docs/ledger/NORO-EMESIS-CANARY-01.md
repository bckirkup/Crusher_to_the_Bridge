# NORO-EMESIS-CANARY-01
**Date:** 2026-09-19
**Commit:** 204ba42
**Pathogens:** norwalk_gi
**Status:** open

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
