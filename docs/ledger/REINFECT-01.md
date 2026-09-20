# REINFECT-01
**Date:** 2026-09-20
**Commit:** 861a0b9
**Pathogens:** all
**Status:** open
**Measured at:** 861a0b9

## Defect

A host whose infection clears acquires no immunity unless a strain registry
is configured, and a second infection overwrites the record of the first.
Exposed on `sars_cov2_resp`; applies to any profile whose hosts clear before
the voyage ends.

- `engines/natural_history.py` `advance_infection`: when the last resident
  lineage clears (`days_infected >= shedding_clearance_day`, day 15 for
  `sars_cov2_resp`), `inf["status"] = RECOVERED`. `record_cleared_immunity`
  returns immediately when `strain_registry is None`; no COVID campaign
  configures one, so no `ImmuneRecord` is written and `agent.immune` stays
  false.
- `engines/transmission_core.py` `_get_susceptible` admits any host that is
  not `is_infected_with(pid)`; a `RECOVERED` record is not `INFECTED`, so the
  host is challenged on the next epoch at full `base_susceptibility`.
- `engines/infection_dynamics_bridge.py` `infect_with_pathogen` assigns a
  fresh dict to `self.infections[pathogen_id]`, replacing `infection_epoch`,
  `time_infected`, `acquired_particles_by_route` and the incubation draw.
- `crusher_labs/modalities/syndromic.py` keys `_presentation_onset_epoch` and
  `_onset_observations` on the agent and never resets them, so the second
  episode inherits the first episode's onset date.

The open-ledger item "795 repeat infection events at Θ = 1e9; hosts re-enter
the susceptible pool; lifecycle not yet traced" is this mechanism.

## Measurement

Cell `A0_declared`, Θ 1e9, seed `20200205`, `covid_quarantine_attribution_v1`,
`861a0b9`. Image payload (S3): truth channel 2,391 / 973 / 93 infections
before / during / after quarantine; event ledger (first event per host) 42
first infections during quarantine; syndromic record 2,836 onsets before the
split day, none after day 21.

Per-agent probe (`tools/covid_attribution_timing_probe.py`, same cell on the
local host — a different trajectory from the image, mechanism identical): of
3,443 infected hosts, 1,293 (37.6%) carry a first transmission event earlier
than their `infection_epoch`; 1,211 have `onset_day < infection_day`, lag −10
to −28 d with the mode at −15 d = `shedding_duration_days`; of 1,167
truth-channel during-quarantine infections, 1,138 are overwritten records of
hosts infected before day 16 and 29 are first infections. Every infected host
has a ledger event (`work.tx_events` is complete).

Campaign-wide (`A0`, 20 seeds pooled): reinfections are 7% of the
truth-channel during-quarantine count at Θ 1e5 and 32% at Θ 1e9.

## Consequences

- `infections_before/during/after_quarantine` in every COVID payload date the
  host's *latest* episode and are void as counts of hosts infected in the
  window. `infections_total`, `attack_rate` (distinct hosts) and
  `recorded_onsets` (first onset per host) are unaffected in count.
- Reinfected hosts shed again, so high-Θ attack rates and the pre-quarantine
  burn are inflated by an unmeasured amount (inference, not measured).
- The recorded onset curve has no tail after day 21 at Θ 1e9 because every
  late infection is a second episode that keeps its first onset date
  (inference from the probe; the record has onsets to day 30).

## Fix (not made)

Two candidate shapes, to be chosen with a provenance review, not here:
(a) write an `ImmuneRecord` on clearance without a strain registry, using the
profile's `immune_waning` block (`refractory_days` 90 for `sars_cov2_resp` is
already declared) so a cleared host is refractory for the voyage; (b) keep
the first record and append episodes rather than overwrite, so the truth
channel can count first infections irrespective of (a). (a) changes
trajectories; (b) changes only the payload. Paired measurement is the
canary cell (A0, Θ 1e5 and 1e9, seed `20200205`) inside the campaign image.

## Open decision

Whether the next COVID session fixes REINFECT-01 before any further campaign.
See `docs/ledger/QUAR-ATTR-V1.md`.
