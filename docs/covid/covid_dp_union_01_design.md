# covid-dp-union-01 — Suite-1 union arm, joint scored contract over θ

**Status:** frozen design, θ grid held (2026-11-24). No scored cell has
run. Every criterion below is frozen before any cell runs and may not be
altered after a surface is seen. Executes §2 (the arm), §3 Suite 1 (the
scope) and §5 (the adopted joint conditioned contract) of
`docs/proposals/covid_theta_unification_plan.md`.

**Revision before any cell (2026-11-24).** The first freeze of this file
(commit `d5273582`) scored five legs on takeoff seeds over θ {1e9, 3.16e9,
4.22e9, 1e10}. Two owner decisions the same day replaced that before any
cell ran: the contract is the joint multi-objective set conditioned on the
founder class (below), and the θ grid is held until the airborne fine-share
adoption re-denominates the emission scale. The confinement order was also
renamed `SOP-017-DEDQUARTER` (the protocol schema allows one id suffix).

## Scope

One declared arm carrying every already-expressible mechanism at once, scored
on a joint contract instead of one observable. Config-only: no mechanism
code, no epidemiological constant change, θ the only swept quantity.

- Design file: `picard_framework/runs/covid_dp_union_01_design.json`
  (`design_id` `covid-dp-union-01`, parent `covid-dp-theta-fit-01`); the
  thresholds live in its `joint_contract` block and the readout reads them
  from there.
- Arm `union_niid` = DP-THETA-FIT-01's `replay_niid` overrides verbatim
  (dedicated `diamond_princess` hull, declared itinerary, diamond rhythm
  catalog, confinement days 16–30 from 07:00, NIID index clock) plus three
  declared deltas:
  1. **Quarter-exempt confinement.** `scheduled_protocol_id`
     `SOP-017-DEDQUARTER`, a new entry in
     `data/config/protocols_covid_dp_dedicated.json`: SOP-017-DEDICATED with
     `exempt_work_zones` replaced by `exempt_fraction` `crew_general` 0.25
     (sticky exact-count draw at activation). The 0.25 is the headcount
     reading QUAR-TAIL-SEAM-01 declared for `SOP-017-QUARTERMB`, Grade C, not
     fitted. The boxed-hull protocol file is not used.
  2. **Symptomatic-crew removal.** `crew_duty_exclusion.enabled` true (VSP
     2018 OM 4.4.1.1.1), a standing policy that also binds before the
     confinement window.
  3. **Record testing structure.** `observation_overrides`
     `retest_negative_sweeps` true and `campaign_waves` `["crew_wave"]`
     (the 23 Feb, day-index-34, 831-test crew-only wave). The 15–20 Feb
     `retest_tiers` are scenario data and run on every arm.
- **Declared judgment (the one place this is not a verbatim transfer).**
  QUAR-TAIL-SEAM-01 measured the joint lever on `boxed_s1s2` with boxed crew
  meals. Here crew meals stay the dedicated hull's documented staggered
  four-seating mess, so the arm differs from `replay_niid` in exactly the
  two named confinement levers. Whether the joint effect needs boxed meals
  is therefore unmeasured on this hull; a during-band miss is read with
  that stated.
- Seeds: 24 matched seeds 20200205–20200228 at every θ. Horizon: the
  scenario's full declared voyage (35 days, 840 epochs); no block passes a
  horizon.
- **Thetas: held, none declared.** `thetas` is empty and the campaign
  declares no block, so no cell can run. The grid is declared on the
  post-fine-share emission scale after that leg merges (plan §4); no fit
  runs in old units. Rule for the declaration: 3–4 values at half-decade
  spacing bracketing the re-denominated images of FIT-01's 3.16e9 and 1e10.
  Declaring the grid and the canary θ is an amendment to this file made
  before any cell; it changes no criterion below.
- Pairing: the arm adds RNG draws (exempt draw, duty exclusion, retest
  nominations), so same-seed cells are not paired realizations of the
  FIT-01 cells. FIT-01 rows are quoted as context only; no seed-paired delta
  against them is scored.
- Retired axes (SUSCEPT-V1, HEAT-V1, SEED-GEOM-V1, PROPENSITY-V1,
  COVID-HAND-AB-01, COVID-COOP-V1, index dining placement, windowed
  embarkation intensity) are not legs. No index-participation channel, no
  routine-stage contact change, no fixed rings: those are Suites 2–4.
  `covid.H*` anchors are not read; GM is not run; imports stay 1.

## Frozen joint contract

Per cell the worker writes `dp_union`: `t3` and `onboard_table` (the FIT-01
`t3_block` reduction of the campaign specimen log through day index 31 and
34), `capture`, and `timing` (infections by day and the ignition day).

**Conditioning (plan §5).** The record is treated as one draw of the founder
lottery, so every leg is scored on the **founder class** at each θ: seeds
whose `seed_ring.aboard_window_acquisitions` ≥ 10 (COVID-IGNITION-01's
record-implied founder pool). Every leg is still scored; conditioning
changes which seeds count, not which objectives. A θ with fewer than 5
founder-class seeds reads "insufficient class mass" on every leg and passes
none. The founder-class count out of 24 is reported at every θ — it is the
probability of the record's class under the arm and is not hidden by the
conditioning. The same legs are also computed on the takeoff class
(`recorded_onsets` ≥ 10) and on all seeds, reported and never scored.

| Leg | Statistic on the founder class | Passes when |
| --- | --- | --- |
| `timing_ignition` | median ignition day (first day cumulative acquisitions, `acquisition_curve.total_by_day`, seeded index excluded, ≥ 50; never-ignited counts as +∞) | ≤ 9 |
| `timing_before_share` | median `onsets_before_split_day / recorded_onsets` | within 0.10 of 0.173 |
| `attack` | median `infections_total` | inside [712, 960] |
| `during` | median `infections_during_window` | inside [150, 350] |
| `capture` | median confirmed / infections_reachable, reachable = funnel `infection_day` ≤ 29 | ≥ 0.80 |
| `t3` | `P31` = positive campaign specimens with day ≤ 31, target 634 | side is *compatible* |
| `onboard_table` | `P34` = positive campaign specimens with day ≤ 34 (crew wave armed), target 691 of 3,894 | side is *compatible* |

- **Side rule (`t3`, `onboard_table`).** FIT-01's rule is ≥ 18 of 24 seeds
  on one side of the target; on a class of n seeds it is applied as the
  same fraction, ≥ ⌈0.75·n⌉ seeds *above* or *below*, otherwise
  *compatible*. On all 24 seeds this is FIT-01's rule verbatim.
- **Thresholds are inherited, not chosen here.** Ignition mass 50 and day
  ≤ 9: COVID-IGNITION-01. `before_share` ±0.10 and the during band:
  QUAR-TAIL-SEAM-01. Attack band [712, 960]: the growth-bound record band
  (plan §5). Capture floor 0.80 and the day-29 basis: COVID-CAPTURE-01
  (five days before the last armed campaign day, 34).
- **Stated before any cell:** conditioning on founders ≥ 10 and scoring
  ignition ≤ 9 are not independent — IGNITION-01 measured zero overlap
  between them on a different configuration. `timing_ignition` is therefore
  the weakest leg on this class; `timing_before_share` carries the timing
  objective, and the takeoff-class column shows ignition without that
  coupling.
- **Edges, verbatim from FIT-01, on all 24 seeds (not the class).** Dead
  cell: `P31` = 0 on ≥ 20 of 24 seeds. Saturated cell: median seedwise
  secondaries ≥ 0.95 × (`aboard_total` − 1), secondaries being
  `infections_total` as written (index already excluded).
- **Consistent θ.** A θ is *consistent* iff all seven legs pass and the
  cell is neither dead nor saturated. The result is the set of consistent
  θ; no further rule selects among them.
- **Split verdict (plan §3).** If no θ is consistent but every leg passes
  at some non-dead, non-saturated θ, the result is the split verdict: the
  per-leg passing-θ sets and every leg pair whose passing sets are
  disjoint are reported. That pair names the opposing structures; it is
  the measurement, not a failure to fit.
- **Leg failing at every θ.** Reported as the named next structure:
  `timing_*` → founder/ignition participation (Suite 2); `attack` or
  `during` or `t3`/`onboard_table` pinned above at every live θ → the
  routine-stage coolant (Suite 3). A report, not a refit.
- **Representativeness flag, verbatim from FIT-01 (reported, changes
  nothing).** At each consistent θ, if fewer than 6 of 24 seeds have `P31`
  in [317, 1268], the θ is labelled "median not representative".
- **Partial rows.** A row with fewer than 24 seeds is `provisional`: its
  legs are computed and shown, and no consistency verdict is issued. The
  20-seed canary is provisional by construction.

**Reported, never scored:** per-seed founder yield and ignition day, the
legs on the takeoff class and on all seeds, attack rate,
secondaries, extinct seeds, `lab_confirmed_total`, unconditioned capture,
`recorded_onsets` against 197, infections before/during/after quarantine,
crew share of during-window infections, specimens through day 31 and 34,
the by-day specimen table, duty-excluded host count, realized exempt share.

**Known limits, stated before any cell.** `t3` compresses near saturation
(FIT-01). `t3` and `onboard_table` are not independent: `P34` ≥ `P31` on every cell, so the latter
adds only the crew-wave increment (record: 57). With retest sweeps armed
the day ≤ 31 observation process is not FIT-01's, so `t3` here is not a
re-measurement of FIT-01's rows.

## Audit invariants (deviation = defect, not a failed leg)

Carried from FIT-01:

- resolved platform `diamond_princess`; `index_onset_day` 3.0;
- `dose_response.susceptibility_scale` = θ·(α+β)/α, α = 0.18, β = 58;
- quarantine witness activated at epoch 391;
- no `close_zones` protocol fired;
- testing ran: specimens through day 31 > 0;
- `P34` equals `observables.campaign_positives`.

Replaced for the armed wave (FIT-01 required no specimen after day 31):

- no specimen after day 34; every specimen after day 31 is on day 34 and
  wave-tagged `crew_wave`; wave-tagged specimens > 0 and ≤ 831.

Added for the union's arming keys:

- `platform_fidelity.protocols_path` is
  `data/config/protocols_covid_dp_dedicated.json` and
  `SOP-017-DEDQUARTER` is the fired confinement order
  (`SOP-017-DEDICATED` did not fire);
- `crew_window.exempt_fraction` == {`crew_general`: 0.25} and
  `exempt_fraction_drawn` is one entry whose count equals
  round(0.25 × `total_crew`); `exempt_work_zones` echo is null;
- `crew_duty_exclusion.resolved.enabled` is true (an excluded-host count
  of 0 on a takeoff seed is reported as a mechanism-did-not-fire witness);
- the resolved observation block echoes `retest_negative_sweeps` true and
  `campaign_waves` == [`crew_wave`];
- `funnel_hosts` was present: `capture.infections_funnel` > 0 whenever
  `infections_total` > 0.

The payload paths for the echo invariants are checked against a smoke
cell before the canary submits; a path the payload does not carry is
recorded as "not echoed" in the campaign LEDGER, not silently dropped.

**Report immediately:** no in-window positives where infections exist
(machinery gap); a dead or saturated union cell; a leg that fails at every
run θ; any audit deviation.

## Campaign

`campaigns/covid/dp_union_01/` — worker, argv hook and readout registered;
**no blocks declared while the grid is held**. On declaration: one 20-seed
canary block plus a 4-seed remainder at the canary θ, and one 24-seed block
per other θ. Queue `picard-analysis-queue`, 1 vCPU / 4096 MB. The image is
built and its digest pinned after the fine-share leg merges, from a `main`
that contains it.

Canary gate: 20 matched seeds at one declared θ, read out, then stop; the
array runs only on Benjamin's decision.
