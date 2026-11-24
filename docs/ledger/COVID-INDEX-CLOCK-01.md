# COVID-INDEX-CLOCK-01
**Date:** 2026-11-24
**Commit:** 5e9365fe
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 5e9365fe

Does the seeded index host on the DP-UNION-01 union arm fire the
presymptomatic shedding window `sars_cov2_resp` declares
(`presymptomatic_shedding_days` 2.0)? **Verdict: the clock is honest. No
defect. The seeded index does not bypass the presymptomatic window.** The
day-0 silence DP-PARTICIPATION-01 measured is what the declared seed
geometry prescribes.

Read-mostly: code path at `5e9365fe` plus one local instrumented trace.
No AWS Batch, no campaign, no θ work, no engine change.

## The premise that produced the contradiction

The question was posed as "infected 2.8 d before boarding, onset at
infection-day 3.0, so shedding should open at infection-day 1.0, 1.8 d
before boarding". `seed_patch.onset_day` is not an infection day. It is a
**voyage day** (`engines/initiation.py::_seed_onset_day`: "a declared onset
is a voyage day"), and `_seed_epoch_fields` derives the incubation from it:

    onset_incubation = infection_age_days + onset_day - seed_day
                     = 2.8 + 3.0 - 0.0 = 5.8 d

So the union-arm index boards 3.0 d before onset, and the 2.0 d window
opens at infection-day 3.8, which is voyage day 1.0. Day 0 is outside the
window by one day. (5.8 d also equals the profile's incubation median; that
is a coincidence of the NIID clock, not a draw.)

## 1. Which path the seed takes (read from code — measured by the trace in §2)

The seed does not bypass the bridge and no second gate exists.

- `engines/initiation.py::_apply_one_seed` calls
  `agent.infect_with_pathogen(..., time_infected=round(epochs_for_days(2.8)) = 67)`
  and then `_stamp_seed_onset`, which writes `incubation_days = 5.8` and
  `will_present = True`. Because the onset is still ahead
  (`elapsed_since_onset = -3.0 <= 0`), it returns before
  `_stamp_symptomatic_history`: `onset_time_infected` stays unset.
- Emission is `KorkinAgent.get_pathogen_shedding` →
  `_shedding_curve_point` (`engines/infection_dynamics_bridge.py`). With
  no `onset_time_infected`, `_shedding_age` takes the `incubation_days`
  branch: `days_since_onset = days_elapsed(time_infected) - 5.8`. The one
  gate is `days_since_onset < -presymptomatic_shedding_days → None`.
  Every route's source set (`transmission_core._get_shedders`) reads that
  same value.
- This is the same function and the same branch a lazily-incubating
  secondary host uses. There is no seed-specific emission path, no
  onset-typed emission gate, and no ramp weight. `time_infected` is a
  non-negative epoch count (67 at seeding), so there is no negative-epoch
  integer math on this path.
- `earliest_shed_epoch` is not on the emission path at all. Its only
  caller is `picard_framework/covid_boarding_screen.py::_first_secondary_shed_epoch`
  (the clean-attribution bound for non-seeded hosts). Its arithmetic agrees
  with the gate.
- `index_shedding_at_day0` (`covid_boarding_screen.py`) evaluates
  `age - incubation >= -presymptomatic` = `2.8 - 5.8 >= -2.0` = false. It
  is the same inequality as the engine gate, so the readback is faithful.
- The seed carries no `strain_id` and the trace shows no resident strains,
  so the per-lineage path (`_resident_emissions`, which reads the profile
  onset rather than the host's stamped incubation) is not exercised on
  this arm.

## 2. Trace (measured: one seed, one cell)

`tools/diag/covid_index_clock_trace.py --theta 3.16e9 --seed 20200205
--num-epochs 132`, arm `union_niid`, through the campaign's own
`run_pf_cell` with a read-only epoch observer. Evidence:
`reports/covid_index_clock_01/index_clock_trace_20200205.json`. Rows are
end-of-epoch state; index host is agent 1826, `shedding_multiplier` 57.79.

| epoch | voyage day | infection age (d) | days since onset | gate | curve index | shedding / epoch | state |
|---|---|---|---|---|---|---|---|
| 0–23 | 0 | 2.83–3.79 | −2.97 … −2.01 | closed | — | 0 | not ill |
| 24–47 | 1 | 3.83–4.79 | −1.97 … −1.01 | open | −2 → clamped 0 | 2.41e-6 | not ill |
| 48–71 | 2 | 4.83–5.79 | −0.97 … −0.01 | open | −1 → clamped 0 | 2.41e-6 | not ill |
| 72–95 | 3 | 5.83–6.79 | 0.0 … 0.96 | open | 0 | 2.41e-6 | symptomatic (onset stamped at epoch 72) |
| 96–119 | 4 | 6.83–7.79 | 1.0 … 1.96 | open | 1 | 2.41e-4 | symptomatic |
| 120– | 5 | 7.83– | 2.0 … | open | 2 | 2.41e-2 | departed at epoch 120 |

- The shedding column is `get_pathogen_shedding`, which does not check
  departure. From epoch 120 the host is off the ship and reaches no zone,
  so the 2.41e-2 row is what the curve would emit, not realized emission.
- First emission: **epoch 24**, infection age 3.83 d, 1.97 d before
  onset. The declared opening is 2.0 d before onset = infection-day 3.8 =
  epoch 24 on the hourly clock (`time_infected` 92 is the first integer
  epoch at or above 91.2). Consistent with the profile to the epoch.
- Witness that the window was exercised: 6 acquisitions on day index 1 and
  1 on day index 2, all before onset at epoch 72, and before any secondary
  host could emit (`first_secondary_shed_epoch` 115). Payload echoes:
  `index_onset_day` 3.0, `index_shedding_at_day0` false,
  `index_departed_epoch` 120.
- Aboard-window acquisitions for this cell: day 0: 0, day 1: 6, day 2: 1,
  day 3: 5, day 4: 38 (50 total; 42 `hvac_airborne`, 7 droplet, 1
  caregiver).

## 3. Not a defect

Nothing here is specific to seed-patch hosts and nothing is broken for
pre-symptomatic hosts in general: one gate, one branch, opening on time
(measured for the seeded host; read from code for lazily-incubating
hosts, which take the identical branch). The 0 of 868 day-0 acquisitions
and `index_shedding_at_day0` false across the 96 cells follow from the
declared geometry: the gate is closed for the whole of day index 0, so the
day-0 emission is exactly zero and the expected day-0 acquisition count is
zero (inferred for the other 95 cells: same arm, same seed patch, same
deterministic clock; only this cell was traced). The transmission-blocker
archetype (a route gated on shedder status making a carrier a dead end)
does not apply: the index is not a carrier holding a reservoir on day 0,
it is a host that has not started emitting.

Founder-creation measurements on NIID-clock arms are **not** invalidated
by this entry.

## 4. Emission magnitudes, and what they imply

Measured from the trace, relative to the curve's peak (log10 9.0 at
onset + 4 d):

| voyage day | curve value (log10) | emission vs peak | vs day 4 |
|---|---|---|---|
| 0 | gate closed | 0 | 0 |
| 1, 2 (presymptomatic) | 3.0 (clamped to `shedding_curve_log10[0]`) | 1e-6 | 1/100 |
| 3 (onset day) | 3.0 | 1e-6 | 1/100 |
| 4 (onset + 1 d) | 5.0 | 1e-4 | 1 |
| 5+ | 7.0 and up | 1e-2 and up | index gone |

- The presymptomatic window is flat at the onset-day value: negative
  curve indices clamp to index 0 (`idx = min(max(curve_index, 0), …)` in
  `_shedding_curve_point`). It is on, not ramped.
- The index's last full day aboard emits 100× each earlier shedding day:
  day index 4 carries 97% of everything the index emits aboard
  (2400 of 2472 in day-1-epoch units). The pooled 80% day-4 acquisition
  share in DP-PARTICIPATION-01 (76% in this cell) is the curve's step,
  not a participation event (inferred from one traced cell plus the
  96-cell day table).
- For the participation theory (inferred): the founder lottery under the
  union arm is not at boarding. It lives where the index emits, which is
  overwhelmingly day index 4 (a sea day), with a thin tail on days 1–3.
  A day-0 itinerary pin acts on zero emission. Option 1 of
  DP-PARTICIPATION-01's open decision (pin the shedding days) aims at the
  mass; option 2 (move the seed patch so the index sheds at boarding)
  would at most buy a 1e-6-of-peak day, unless the onset is moved too.

## Flagged, not settled here (hypothesis)

The profile cites He et al. Nat Med 2020 for the window's opening. The
authored `shedding_curve_log10` puts the peak at onset + 4 d and holds the
whole presymptomatic window at 1e-6 of it. Whether that shape is what the
cited source supports (it is usually read as infectiousness peaking near
onset) was not checked against the literature in this session; the profile's
`shedding_duration_notes` call the curve a nasal RNA concentration.
This is a profile-shape question under
`.agents/skills/model-parameter-provenance`, not a clock defect, and it is
the owner's call whether it gets its own leg. If the shape moved, day-of-
acquisition under every NIID-clock arm would move with it.

## What is not measured

- One seed, one θ. The clock is deterministic given the seed patch, so
  epoch-of-first-emission does not vary by seed; magnitudes scale with the
  per-host `shedding_multiplier` draw, which differs by seed.
- The absolute emission unit: the trace's values imply the cell resolves
  the curve against a normalizer of 9.0 rather than the profile's
  `environmental_release_log10_per_day` 1.93 (inferred from
  2.41e-6 × 24 / 57.79 = 1e-6; where the arm sets it was not traced).
  Ratios between days are unaffected.
- Venue and hour of the day-4 acquisitions (still open from
  DP-PARTICIPATION-01).
- The strain-resident emission path's onset anchoring (not exercised on
  this arm).

GM held out; H5 held out forever; nothing fitted.
