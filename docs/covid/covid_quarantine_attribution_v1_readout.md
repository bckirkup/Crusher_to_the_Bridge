# COVID quarantine attribution v1: no channel is load-bearing on the frozen measure, and the measure itself counts reinfections

> **Status:** Findings (2026-09-20). Campaign `covid_quarantine_attribution_v1`,
> declared in `picard_framework/runs/covid_quarantine_attribution_v1_design.json`
> (#633) and run on AWS Batch at `main` = `861a0b9`, image
> `picard-campaign:attribution-v1-861a0b9`
> (`sha256:d38988416a971a5b7f0dadf43f5bedb29638fbbc64ad042d97905589c8ccea31`),
> job definition `picard-covid-boarding-screen:8`, canary child
> `5a18f6fe-68b4-45c3-b230-da6154a351ba`, array job
> `f3e71e02-1231-46dd-a0b2-8e173fd6df64` (`picard-attribution-v1-861a0b9`) on
> `picard-campaign-queue`. 240 of 240 children SUCCEEDED, zero failures, zero
> Spot retries, 29 min wall clock; every payload has `invalid_reason == null`
> and `sanitary_visit_mode == dwell_weighted`. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quarantine_attribution_v1/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_quarantine_attribution_v1_design.json --cells <synced cells dir> --out <surface json>`;
> criterion readout and per-cell CSV:
> `python3 tools/covid_attribution_readout.py --cells <synced cells dir> --design <design> --csv docs/covid/covid_quarantine_attribution_v1_surface.csv`.
> Surface: `docs/covid/covid_quarantine_attribution_v1_surface.csv` (one row
> per (Θ, arm, seed) cell). No Theta is claimed here; arms A1–A5 are
> counterfactuals and score no anchor.

The campaign is the stage the v9 readout asked for
(`docs/covid/covid_theta_screen_v9_readout.md` §7,
`docs/covid/covid_theta_handoff_2026_09_19.md` §12–13): the v9 surface said
Θ moves *whether* the Diamond Princess takes off, not *how large* the outbreak
is once it does, and that the outbreak keeps growing through the enforced
quarantine from day 16. Rather than refine Θ, this design asks which
transmission channel carries infections through the quarantine, by removing
channels one at a time on 20 matched seeds at two Θ (1e5, 1e9), with the
attribution criterion frozen before any cell ran (design §`attribution_criterion`).

Every figure below is measured at `861a0b9` inside the campaign image, seeds
`20200205 + k`, k = 0..19, `diamond_princess_2020`, one declared import,
declared index onset day −1. Sections 1–3 are measurements; §4 is the
diagnosis of a defect the measurements exposed; §5 separates what is inferred
from what is hypothesised.

## 1. Execution and witnesses

Every arm override reached the engine. `quarantine_witness.activated` is true
in 240/240 cells at epoch 384 (day 16) with 2,739 hosts confined at
activation and the four crew classes exempt under `A0`/`A2`/`A3`/`A5`; under
`A1`/`A4` (`SOP-017-ALLHANDS`) the exempt list is empty and 3,711 are
confined. `A2`/`A4`/`A5` read `hvac_airborne` during-quarantine dose events
at or near zero where `A0` reads hundreds; `A5` reads zero droplet and zero
`hvac_airborne` events in every cell, with only `direct_contact` and `fomite`
remaining (§3). The canary (A0, Θ 1e5, seed `20200205`) reproduces the
QUAR-EXEMPT-01 HEAD trajectory exactly: 1,171 infections, attack rate
0.3155, 931 recorded onsets, 678/455/38 before/during/after quarantine.

## 2. The frozen criterion, applied verbatim

Takeoff is `recorded_onsets >= 10`. The two declared medians of
`infections_during_quarantine` are (i) over all 20 seeds and (ii) over the
seeds that took off in both `A0` and the arm; a channel is load-bearing if
(ii) falls ≥ 50% *and* (i) also falls, non-load-bearing if (ii) moves < 20%,
indeterminate in between, and no verdict is issued without takeoff overlap.

| Θ | Arm | takeoff | med (i) arm | med (i) A0 | n both | med (ii) arm | med (ii) A0 on same seeds | shift (ii) | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1e5 | A0_declared | 3/20 | 0 | 0 | — | 455 | 455 | — | — |
| 1e5 | A1_crew_confined | 3/20 | 0 | 0 | 3 | 125 | 455 | −73% | indeterminate¹ |
| 1e5 | A2_pool_transport_off | 3/20 | 0 | 0 | 2 | 444.5 | 293.5 | +51% | indeterminate |
| 1e5 | A3_near_field_off | 4/20 | 0 | 0 | 3 | 258 | 455 | −43% | indeterminate |
| 1e5 | A4_crew_confined_and_pool_off | 3/20 | 0 | 0 | 2 | 160.5 | 293.5 | −45% | indeterminate |
| 1e5 | A5_all_shared_air_off | 0/20 | 0 | 0 | 0 | — | — | — | not eligible |
| 1e9 | A0_declared | 12/20 | 855 | 855 | — | 1,035.5 | 1,035.5 | — | — |
| 1e9 | A1_crew_confined | 12/20 | 211.5 | 855 | 12 | 820.5 | 1,035.5 | −21% | indeterminate |
| 1e9 | A2_pool_transport_off | 9/20 | 1.5 | 855 | 8 | 775 | 925.5 | −16% | non-load-bearing |
| 1e9 | A3_near_field_off | 12/20 | 812 | 855 | 8 | 1,034.5 | 1,000.5 | +3% | non-load-bearing |
| 1e9 | A4_crew_confined_and_pool_off | 9/20 | 1.5 | 855 | 8 | 715.5 | 925.5 | −23% | indeterminate |
| 1e9 | A5_all_shared_air_off | 1/20 | 0 | 855 | 1 | 212 | 973 | −78% | no verdict² |

¹ The conditional median falls 73%, but both all-seed medians are 0 (17 of 20
seeds go extinct at Θ 1e5 in every arm), so the "all-seed median also
decreases" clause cannot be met and the frozen rule returns indeterminate.
The 1e5 rows have two or three overlapping seeds each and are reported for
completeness, not as verdicts. ² One overlapping seed; the design's
eligibility clause is read as requiring an overlap, not a single trajectory.

**Result of the frozen criterion: no single channel is load-bearing at
either Θ.** At Θ 1e9, with 8–12 overlapping seeds, removing cross-zone pool
transport (A2) or near-field air (A3) leaves the conditional during-quarantine
count within 20% of `A0`; confining the crew (A1) and confining crew plus
removing pool transport (A4) each shave 21–23%. Removing all shared-air
routes (A5) collapses takeoff itself (1/20 at 1e9, 0/20 at 1e5).

Two things the criterion also shows, outside its verdict table. First, the
all-seed medians at Θ 1e9 fall from 855 (`A0`) to 1.5 (`A2`, `A4`) not because
outbreaks shrink but because three fewer seeds take off (9/20 vs 12/20): pool
transport moves *takeoff probability*, the same lever v9 found for Θ. Second,
whole-voyage attack rate is nearly arm-invariant once a seed takes off:
conditional median attack rate at Θ 1e9 is 0.86 (`A0`), 0.83 (`A1`), 0.91
(`A2`), 0.86 (`A3`), 0.87 (`A4`); at Θ 1e5 it is 0.19 (`A0`, n = 3), 0.11
(`A1`), 0.26 (`A2`), 0.19 (`A3`), 0.18 (`A4`). Whatever the quarantine
channel is, the ship is already committed before day 16: at Θ 1e9 the
conditional median has 2,060 of 3,711 hosts infected before quarantine
activates.

## 3. Routes and zones that actually fired

Aggregate during-quarantine event counts over takeoff cells (first infection
event per host, see §4; not paired effects):

| Θ | Arm | droplet | hvac_airborne | fomite | direct_contact |
|---|---|---:|---:|---:|---:|
| 1e5 | A0 | 1,127 | 16 | 0 | 0 |
| 1e5 | A1 | 278 | 0 | 0 | 0 |
| 1e5 | A2 | 817 | 0 | 0 | 0 |
| 1e5 | A3 | 977 | 0 | 0 | 0 |
| 1e5 | A4 | 241 | 0 | 0 | 0 |
| 1e9 | A0 | 7,949 | 671 | 0 | 0 |
| 1e9 | A1 | 3,434 | 1,160 | 0 | 0 |
| 1e9 | A2 | 3,090 | 19 | 0 | 0 |
| 1e9 | A3 | 7,034 | 650 | 0 | 0 |
| 1e9 | A4 | 1,622 | 0 | 0 | 0 |
| 1e9 | A5 | 0 | 0 | 204 | 6 |

Droplet (shared-room far-field dose, which under `A3` no longer includes the
meal-table near-field term) is the route of record for every during-quarantine
first infection in the declared arm; `hvac_airborne` is 8% of events at Θ 1e9
and rises under `A1` because confined crew are dosed in cabins through the
HVAC downstream path. The `A5` cell that took off (Θ 1e9, 271 infections, all
crew) ran on fomite alone; contact and fomite cannot ignite the ship at
either Θ. The `A5` smoke's premise holds in every cell: the profile
`route_efficiency_multipliers` override is honoured and both air accumulators
read zero.

## 4. `infections_during_quarantine` counts reinfections (REINFECT-01)

Reconciling the two channels of the payload exposed a defect. In cell (`A0`,
Θ 1e9, seed `20200205`) the truth channel dates 2,391 infections before day
16, 973 during quarantine and 93 after, while the event ledger — which keeps
each host's *first* transmission event — records 42 first infections during
quarantine. The syndromic record dates 2,836 onsets before the split day,
more than the truth channel's pre-quarantine infections, and the onset curve
is empty after day 21.

A per-agent probe (`tools/covid_attribution_timing_probe.py`, same cell on the
local host; the local stack follows a different trajectory from the image, so
its absolute counts differ, but the mechanism is the same) resolves this.
Of 3,443 infected hosts, 1,293 (37.6%) carry a ledger event *earlier* than
their `infection_epoch`; 1,211 have `onset_day < infection_day`, by −10 to −28
days with the mode at exactly −15 d (the profile's `shedding_duration_days`);
of the 1,167 truth-channel during-quarantine infections, 1,138 are hosts
infected earlier whose record was overwritten and 29 are first infections.
No infected host lacks a ledger event: `work.tx_events` misses nothing.

Mechanism, read from the code: when a host's last resident lineage clears
(`engines/natural_history.py` `advance_infection`, day 15 for
`sars_cov2_resp`), `inf["status"]` becomes `RECOVERED`. `record_cleared_immunity`
writes an immune record **only when a strain registry is configured**; no
COVID campaign configures one, so the host acquires no protection. On the next
epoch `TransmissionCore._get_susceptible` admits the host (it is no longer
`is_infected_with`), `_establish` calls `agent.infect_with_pathogen`, and
`infect_with_pathogen` (`engines/infection_dynamics_bridge.py`) **replaces the
whole per-pathogen record**, `infection_epoch` included. The truth window then
dates the host's latest episode; the event ledger dedupes on its first; the
syndromic modality keys `_presentation_onset_epoch` and `_onset_observations`
on the agent and never resets them, so the first onset date is carried into
the second episode. The three payload channels disagree because each measures
a different episode of the same host.

Across the campaign the share of the truth channel's during-quarantine count
that is reinfection is 7% at Θ 1e5 (`A0`, all seeds pooled) and 32% at Θ 1e9,
rising to 96% in the seed above, which had already infected 2,391 hosts
before day 16. The frozen measure is therefore not what the design declared
it to be: it is first infections *plus* second episodes of hosts recovered
from a first, and the second term dominates exactly where the ship is
saturated. The verdicts in §2 stand as the literal output of the frozen rule
and are recorded as such; they are not read as channel attribution.

## 5. What can be read, what is inferred, what is hypothesised

**Measured (valid regardless of REINFECT-01).** `infections_total` and
`attack_rate` count distinct hosts and are unaffected. `recorded_onsets` is
one onset per host (first episode) and is unaffected in count. The event
ledger's route/zone/role breakdowns are first-infection counts and are valid
as such. The witness fields, takeoff counts and the A5 zero-air proof stand.

**Post-hoc, on the ledger's first-infection count (`ledger_events_during` in
the CSV), same medians and thresholds as §2, declared here as a diagnostic
and not as the frozen criterion.** At Θ 1e9: `A1` 825.5 → 198.5 (−76%, n =
12), `A2` 351.5 → 123 (−65%, n = 8), `A4` 351.5 → 52.5 (−85%, n = 8), `A3`
470.5 → 538.5 (+14%, n = 8). At Θ 1e5 (n = 3/2): `A1` 393 → 102 (−74%), `A3`
393 → 202 (−49%), `A2` 247.5 → 403.5 (+63%), `A4` 247.5 → 117 (−53%). On first
infections, crew exemption and cross-zone pool transport each carry the
majority of what enters the confined population after day 16; the meal-table
near-field term carries none of it (its removal does not reduce the count at
either Θ). This is the reading the design was built to make, and it is
consistent across both Θ for `A1` and `A3`; `A2` disagrees in sign between Θ
at n = 2 and is not read at 1e5.

**Inferred.** Reinfected hosts shed again. With 37.6% of infected hosts
re-entering the infectious pool in the probe cell, the Θ 1e9 attack rate of
0.86 and the pre-quarantine burn of 2,060 hosts are inflated by an
unquantified amount; how much of the v9 "extinction-or-burn" shape is
reinfection is unknown until REINFECT-01 is fixed and the `A0` cells are
re-measured. The open-ledger item "795 repeat infection events at Θ = 1e9;
lifecycle not yet traced" is this mechanism.

**Hypothesis (not measured).** Fixing REINFECT-01 (an immune record, or at
least a non-overwriting record, on clearance without a strain registry) will
lower whole-voyage attack rates at high Θ and lengthen the recorded onset
tail into days 21–30, where the Diamond Princess record has onsets and the
model currently has none. Whether it moves the takeoff probability at Θ 1e5
is not predicted.

## 6. What this changes

- **Superseded:** the reading in `covid_theta_handoff_2026_09_19.md` §12 and
  the v9 readout §6 that the outbreak "continues through enforced quarantine"
  at the scale of the truth-channel counts (455 at Θ 1e5, ~1,000 at 1e9). The
  first-infection count through quarantine is 393 at Θ 1e5 (seed `20200205`)
  and a median 825 at 1e9 — smaller, and at 1e9 sitting on a saturated ship.
- **Still valid at their SHAs:** THETA-SCREEN-V9 (`0fb186b`) and QUAR-EXEMPT-01
  (`008c8c8`) totals, attack rates and recorded onsets; all count distinct
  hosts or first onsets. Their `infections_during_quarantine` style figures,
  where quoted, carry the same contamination.
- **Void:** any reading of `infections_during_quarantine`,
  `infections_before_quarantine` or `infections_after_quarantine` as counts of
  hosts infected in that window, in this or any prior COVID payload at Θ where
  hosts clear before the voyage ends.
- **Not changed:** no Θ is admissible or fitted; covid.T1/T3 were not scored
  here; the design's ban on reading counterfactual arms as the historical
  scenario holds.

## 7. Next stage

The next session's single decision is whether to fix REINFECT-01 before any
further COVID campaign — see `docs/ledger/REINFECT-01.md`. The attribution
question itself has a provisional first-infection answer (§5) that should be
re-measured only on the repaired engine, since the channel that reinfects a
recovered host is the same shared-air dose that infects a naive one.
