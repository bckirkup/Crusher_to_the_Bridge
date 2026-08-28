> **Status — resolved by PRs #327 and #328:** The `hour = 12` hard-code in
> `engines/infection_dynamics_bridge.py` is gone; the schedule is now
> clock-driven. Time-dependent parameters declare their units and are converted
> through `SimClock`. The canonical specification is now
> [`docs/clock_unit_safety_spec.md`](clock_unit_safety_spec.md), copied from the
> implementation contract that was previously kept in
> `telemetry_buffer/clock_audit/unit_safety_spec.md`.

# The epoch is a day in the ABM and an hour in the voyage layer

Written after the paired-arm incubation harness (PR #295) produced a degenerate
result: both arms reported a one-hour realized incubation, although the
distribution arm draws a 1.2-day median for norovirus. The harness is not the
problem. Two layers of the simulator disagree about what one epoch *is*, and the
disagreement has been in every voyage-configured run to date, including the runs
behind papers 1 and 2.

This document records the historical audit and decision request. The
implementation is resolved by PRs #327 and #328; the canonical implementation
contract is `docs/clock_unit_safety_spec.md`.

## 1. The two contracts

**The ABM says one epoch is one day.**

- `KorkinShipEngine.step()` is documented as "Advance the simulation by one
  epoch (≈ one day)", and it places every agent using a single *representative
  hour* — `hour = 12`, "midday activity peak" — rather than walking the 24-slot
  schedule.
- `orchestrator_epoch._advance_agent_pathogen_infections` increments
  `inf["time_infected"]` once per epoch, and `time_infected` is documented in
  `engines/infection_dynamics_bridge.py` as an epoch counter converted through
  `SimClock`; shedding curves are indexed by days since symptom onset.
- That day counter is compared against day-scale profile parameters:
  `recovery_day`, the incubation draw from `engines/incubation.py` (in days), and
  the 15-entry `shedding_curve_log10` (one entry per day post-onset).
- `data/config/instrument_turnaround.json` states it outright: "1 epoch = 1
  simulation day unless `hours_per_epoch` is overridden", with
  `hours_per_epoch: 24`. Assay turnaround in hours is converted to epochs by
  dividing by 24.

**The voyage, sentinel, and calibration layers say one epoch is one hour.**

- `engines/voyage_itinerary.py` defaults `epoch_duration_hours` to 1 and derives
  `epochs_per_day = round(24 / hours)`, so voyage day 1 spans epochs 1–24;
  `tests/test_sentinel_data_contracts.py` pins `epochs_per_day == 24`.
- `SentinelLedger` accrues person-hours ashore at `epoch_duration_hours` per
  epoch, and the Stan incubation kernel is specified in hours on a one-hour
  grid.
- `calibration_manifest_v1.json` is explicit: "7-day voyages (168 epochs)", with
  `c4_voyage_duration` sweeping 72 / 168 / 336 epochs as 3 / 7 / 14 day cruises.
  The mega campaign's `default_epochs: 240` reads the same way (a 10-day
  itinerary).

Both contracts are internally coherent. They cannot both hold in one run.

## 2. What that does to a run configured the second way

Measured on `main` at `6834ffa` by stepping a single host through
`_advance_agent_pathogen_infections` (200 hosts per pathogen, dose 1e5):

| pathogen | profile median incubation | profile `recovery_day` | median onset | median duration |
|---|---|---|---|---|
| `norwalk_gi` | 1.2 d | 3 | 2 epochs | 3 epochs |
| `sars_cov2_resp` | 5.8 d | 7 | 4 epochs | 7 epochs |

An infection lasts `recovery_day` *epochs*. In a 168-epoch "7-day" voyage that
is a norovirus case that incubates for two hours and clears in three, and a
SARS-CoV-2 case that clears in seven hours. Natural history runs 24× fast
against the itinerary calendar, so:

- the symptomatic window a syndromic system has to catch is ~1–2 epochs, not the
  1–2 days the profile describes;
- only the first 3–7 entries of a 15-day shedding curve are ever indexed;
- realized incubation, measured as onset minus shore exposure in the sentinel
  line list, collapses to about one hour — which is what made both arms of the
  PR #295 harness look identical;
- assay turnaround converted at `hours_per_epoch: 24` shrinks a 12-hour assay to
  one epoch, i.e. one calendar hour, so detection *delay* is compressed on the
  same factor as the biology it is racing.

Whole-ship effect, `expedition_cruise_450`, norovirus, 168 epochs, 3 seeds,
comparing current behaviour against a probe that advances progression once per 24
epochs:

| arm | peak prevalence | symptomatic person-epochs | ever recovered |
|---|---|---|---|
| current (day clock per epoch) | 230 | 606 | 360 |
| probe (day clock per 24 epochs) | 145 | 456 | 360 |

That probe understates the effect, and the reason is itself a finding: the day
clock is implemented **twice**. `KorkinShipEngine.step()` advances the legacy
per-agent `time_infected` and applies its own onset and `RECOVERY_DAY` checks
(§3 and §4 of the step), while `step_infection_progression` advances the
multi-pathogen records in `orchestrator_epoch`. `ShipSimulation.step()` calls
both. The summary counts a paper reads — `infected`, `symptomatic` — come from
the legacy fields, so a probe that slows only the multi-pathogen path moves
ship-level output by <6% and looks like a null result. Any correction has to
convert both, or the two clocks disagree with each other as well as with the
itinerary.

### 2a. Paper 1's operating point, both clocks converted

Probe at the VSP degradation campaign's operating point — `expedition_cruise_450`
at 450 agents, norovirus only, `dose_adjustment: 10.6`, 3 index cases, syndromic
surveillance with the cascade off, 168 epochs, seeds 200–202 — comparing current
behaviour against one where both the legacy `days_post_infection` and the
multi-pathogen progression read the hourly grid (medians of 3 seeds):

| outcome | current | hourly clock | factor |
|---|---|---|---|
| ever infected (attack rate) | 153 (0.34) | 141 (0.31) | ~1× |
| peak concurrent infected | 16 | 113 | ~7× |
| symptomatic person-epochs | 145 | 3285 | ~23× |
| epoch crossing 5% attack rate | 116 | 89 | earlier in 2 of 3 seeds |

The split matters more than any single number. **Cumulative incidence is close to
invariant** — per-seed 153/186/60 against 141/189/135, one seed doubling and two
unchanged — because the dose calibration that produced it is fit to a cumulative
target. **Everything that integrates over time is not**: concurrent prevalence
rises ~7× and symptomatic person-time ~23×, because a case that used to clear in
three epochs now occupies seventy-two.

Still an approximation, not the correction: it is a monkeypatch on three seeds
and one platform, it holds `dose_adjustment` fixed rather than re-fitting, and
detection timing is unresolved here because the seeded index cases put the first
sick call at epoch 0 in both arms. Sizing it properly needs the unsaturated
`dose_adjustment` tiers of `calibration_manifest_v1.json`, run both ways.

## 3. What is and is not affected

Not affected: bare `python3 orchestrator.py` runs with voyage effects off. With
no itinerary there is no calendar to contradict, and 24 epochs is a coherent
24-day run.

Affected: every voyage-configured Picard/Presidio run, hence the paper 1
detection-timing results, the paper 2 attribution campaign, the VSP
`dose_adjustment` tiers (which absorbed the compression when they were fit), and
every paper 3 arm that quotes a rate per day or a detection delay.

Paper 1's claims sort onto the §2a split:

| paper 1 claim | exposure |
|---|---|
| attack rate, epidemic size, route attribution | robust — cumulative, and near-invariant in the probe |
| VSP degradation monotone in the swept dial | qualitatively robust; the operating point shifts, so the curve is re-read after R6 |
| quarantine-bed occupancy, OIS and cost ledger | order-of-magnitude exposed — they integrate symptomatic person-time |
| time-to-detection, wearable lead time in hours | exposed in absolute units; partly self-cancelling because `hours_per_epoch: 24` compresses assay turnaround by the same factor |
| insurance / wearable ROI (arm difference) | least exposed; both arms carry the same clock, so expect the ratio to hold and the dollar figures to move |

Not a new defect: this predates paper 3. PR #290 (incubation as a distribution)
made it *visible* by putting a day-scale distribution where a constant 1.0 had
been, but the mismatch is as old as the voyage layer's hourly grid.

To be clear about where the defect is not: the pathogen profiles are correct.
`norwalk_gi` carries a 1.2-day incubation median and `recovery_day: 3`, which is
norovirus as published; `sars_cov2_resp` carries 5.8 days and 7. Nothing needs
re-parameterising. The defect is entirely in the consumer, which treats those
day-valued fields as epoch counts. The repository's own canonical definition —
"Epoch: one-hour discrete simulation time step" — agrees with the voyage layer,
which makes the ABM's `≈ one day` docstring the side that is wrong.

## 4. Options

**Option 1 — the ABM moves to the hourly grid.** Convert every day-scale clock
at read time (`time_infected` in hours, `recovery_day × 24`, incubation days ×
24, shedding curve indexed by days since onset rather than infection),
walk the 24-slot
schedule instead of `hour = 12`, and set `hours_per_epoch: 1` for instrument
turnaround. This is the physically correct reading and the one the itinerary,
sentinel kernel, and calibration manifest already assume. Cost: every calibrated
number moves. The VSP `dose_adjustment` tiers must be re-fit (already scheduled
as R6), and papers 1 and 2 need the sensitivity pass already agreed.

**Option 2 — the voyage layer moves to the daily grid.** Set
`epoch_duration_hours: 24`, run 7-epoch voyages, and accept one representative
hour per day. Cheap for the ABM, but it destroys the sentinel layer's premise:
port dwell, censoring, and MDHR all resolve sub-daily exposure, and a 7-epoch
voyage cannot carry a 33-hour incubation kernel. Not recommended.

**Option 3 — declare the epoch dimensionless and re-express the profiles.**
Rewrite pathogen parameters in epochs and drop the day language. Honest
bookkeeping, no code change beyond documentation, but it makes every literature
anchor (incubation medians, VSP AGE rates per person-day, shedding curves)
untranslatable, which is worse for the paper than the bug.

**Recommendation: option 1, behind a flag, measured before it is adopted.**
Concretely: add a per-run `epoch_duration_hours`-aware natural-history clock,
default to today's behaviour so no published output moves under our feet, then
run the `c1_*` calibration tiers in both modes and report the shifted
`dose_adjustment` values. That makes the correction a third arm of the existing
incubation sensitivity protocol rather than an unmeasured change to the
generating model, and it lets papers 1 and 2 be re-tested with one harness
instead of two.

## 5. Open questions for the PI

1. Adopt the hourly natural-history clock as the main line for paper 3, or keep
   it as a sensitivity arm until the re-fit lands?
2. Papers 1 and 2 are already scheduled for an incubation sensitivity pass. Does
   the clock correction fold into that pass, or does it warrant its own
   re-analysis?
3. Does the shedding curve interpolate between daily entries on the hourly grid
   (smooth, more realistic) or hold each day's value for 24 epochs (faithful to
   the curve as tabulated)?
