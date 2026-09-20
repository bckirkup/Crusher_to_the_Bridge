# REINFECT-01
**Date:** 2026-09-20
**Commit:** 7f105a7
**Pathogens:** all
**Status:** closed
**Measured at:** 7f105a7

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

## Fix

Both candidate shapes landed at `7f105a7`, plus two companions:

- (a) `engines/natural_history.py` `record_unlabeled_clearance_immunity`
  writes one genotype-blind `ImmuneRecord` (genotype `""`, origin
  `IMMUNITY_FROM_INFECTION`) at the pathogen-level RECOVERED transition when
  `record_cleared_immunity` wrote no lineage record.
  `engines/transmission_core.py` `_init_strain_tracking` now parses
  `strain_evolution` (including `immune_waning`) for every profile
  regardless of registry, and `_challenge_protection` takes
  `max(legacy, _unlabeled_resolution_protection)` — the declared
  `immune_waning.protection_at` window (`refractory_days` 90,
  `refractory_protection` 1.0 for `sars_cov2_resp`) applies per-epoch as a
  hazard multiplier, so a cleared host is refractory for the voyage.
- (b) `engines/infection_dynamics_bridge.py` `infect_with_pathogen` keeps
  `first_infection_epoch`, `episode` and `episode_epochs` across
  overwrites, so the truth channel can count first infections.
- `crusher_labs/modalities/syndromic.py` re-dates `_presentation_onset_epoch`
  and `_onset_observations` when a presenting infection's `infection_epoch`
  postdates the stored onset (second episodes get their own onset date).

Paired in-image canary (`994254241749.dkr.ecr.us-east-1.amazonaws.com/
picard-campaign@sha256:17d74c5dcecdcb9aafa80643dda973088d3d98581db9252
5174888dd16364341`, job-def `picard-covid-boarding-screen:9`, A0, seed
`20200205`, cells under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/reinfect01_canary/
7f105a7/`; jobs `f56507e0-1122-4d99-86ac-2fe68a5eee2d` Θ 1e5,
`b99cd613-356e-4ac0-a133-a84aa041fcb0` Θ 1e9):

| cell | total | AR | before/during/after | vs `861a0b9` during |
|------|-------|-----|--------------------|--------------------|
| Θ 1e5 | 950 | 0.2560 | 745 / 198 / 7 | 455 → 198 |
| Θ 1e9 | 3458 | 0.9318 | 3414 / 43 / 1 | 973 → 43 |

At Θ 1e9 the during-quarantine count collapses from 973 (overwritten
reinfection records) to 43 fresh infections, matching the probe's estimate
that only ~4% of during-window truth infections were first episodes. Local
probe re-run on the same cell (`reinfect01_probe_1e9.json`, host
trajectory): `episode >= 2` count 0, zero negative onset lags, zero
ledger-event epochs preceding `infection_epoch` — the overwrite path is
closed at every layer the probe measures.
