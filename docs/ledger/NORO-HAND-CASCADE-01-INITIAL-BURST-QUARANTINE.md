# NORO-HAND-CASCADE-01-INITIAL-BURST-QUARANTINE
**Date:** 2026-11-15
**Commit:** 893cc54d
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 102c5407

Read-only initial-burst/quarantine join for the posted
`fl_exp_12d_sens_p06_paxv` cell (`expedition_cruise_450`, `norwalk_gi`, 288
epochs), arm `carriers_ordered`, seeds 8073/8038/8046/8047/8077 under
`PYTHONHASHSEED=1`. The observer is a plain `ShipSimulation` run with a
read-only `epoch_observer` that records post-record `quarantined_ids`,
`isolated_ids`, and per-agent `norwalk_gi` infection/illness sets each epoch;
it is joined to the existing full-payload `growth_chain_census` artifacts
`results/noro_growth_chain_probe/hash1/s<seed>_cs_full.json` for
`acquisitions_detail` and `common_source.events`. For an acquisition at epoch
`e`, the governing pre-transmission state is the observer's post-record state
at `e-1`. Observer rows are local at
`results/noro_initial_burst_quarantine/hash1/s<seed>.json`.

Neutrality: observer ever-infected/ever-symptomatic counts matched the
contact-binding controls exactly on all five seeds (103/56, 122/64, 102/52,
77/46, 80/37 for 8073/8038/8046/8047/8077). The measurement ran at `102c5407`;
`main` then advanced to `893cc54d` with Contam/platform changes including
`expedition_cruise_450` air-flow/PRJ data, so these numbers are historical
until a same-commit witness/observer rerun.

## Measured

| seed | first symptom epoch | first quarantine epoch | symptom→quarantine lag | CS acquisitions after first Q | susceptible CS taker exposures after first Q | fomite acquisitions | fomite while target quarantined | fomite symptomatic by end | caregiver acquisitions |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8073 | 37 | 50 | 13 | 27 | 154 | 7 | 1 | 4 | 3 |
| 8038 | 30 | 35 | 5 | 34 | 180 | 18 | 6 | 8 | 5 |
| 8046 | 19 | 24 | 5 | 0 | 13 | 17 | 6 | 5 | 10 |
| 8047 | 28 | 40 | 12 | 7 | 38 | 5 | 3 | 4 | 9 |
| 8077 | 4 | 24 | 20 | 0 | 0 | 21 | 3 | 6 | 3 |

- Common-source pan exposure is effectively pre-quarantine: across all seeds,
  1,565 taker exposures comprised 1,247 susceptible-at-exposure, 318
  already-infected, and 0 quarantined takers. The pan window can nevertheless
  outlast quarantine onset on seeds with later events: CS acquisitions after
  first quarantine are 27/34/0/7/0, and susceptible taker exposures after
  first quarantine are 154/180/13/38/0.
- Every fomite acquisition target was not infected and not symptomatic before
  the acquisition epoch. All 68 fomite acquisitions occur after the first
  quarantine epoch; 19/68 occur while the target is already quarantined, and
  49/68 while still open. Fomite symptomatic conversion by voyage end is
  27/68, with median symptom lag after acquisition of 34–45 epochs. Of the 27
  symptomatic fomite hosts, 22 were quarantined before symptom onset and 5
  were not quarantined before symptom onset.
- Caregiver acquisitions are few (3/5/10/9/3) and all occur in non-quarantined
  targets in the pre-state.

## Inferred

- The user's "effective initial exposure" framing is supported: the exposed
  susceptible cohort is large and mostly occurs before quarantine, but the
  missing posted tail is not explained by larger pan mass alone.
- Secondary transmission is present but late: fomite/caregiver acquisitions
  begin only after quarantine has started, many are too late to present before
  voyage end, and quarantine reduces onward transmission without preventing
  illness after exposure.
- Because the common-source source is `provisioned_lot` supply-chain food,
  case-based quarantine does not remove the pan source; extended pan windows
  can keep exposing susceptibles after outbreak recognition.

## Hypothesis and next decision

Hypothesis: rare-but-larger posted outbreaks require faster fomite/caregiver
conversion in roughly the first 20–40 epochs, shorter symptom→quarantine lag,
or a common-source window/quantity structure that recruits more susceptibles
before recognition. Per-contact hand/contact geometry remains a lower-priority
suspect for these cells because acquired route dose is dominated by
`common_source_food` and the only other material share is fomite. No constants
were fitted and no defaults were flipped. Next measurement should be a
same-commit (`893cc54d`) witness/observer rerun before using these timing
numbers for any arm comparison.
