# covid-dp-union-01 — Suite-1 union arm, joint scored contract over θ

**Status:** frozen design (2026-11-24); no cell run at freeze. Every
criterion below is frozen before any cell runs and may not be altered after
a surface is seen. Executes §2 (the arm) and §3 Suite 1 (the scope) of
`docs/covid/covid_theta_unification_plan.md`.

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
     `SOP-017-DEDICATED-QUARTER`, a new entry in
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
- Thetas: **{1e9, 3.16e9, 4.22e9, 1e10}** — the three θ DP-THETA-FIT-01
  measured plus its interpolated θ\*. 96 cells. 4.22e9 is included because
  FIT-01's bracket (3.16e9, 1e10) is where its only compatible θ sit and the
  joint contract needs an interior point there.
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
34), and `capture`. Takeoff seeds are those with `recorded_onsets` ≥ 10.

| Leg | Per-θ statistic | Passes when |
| --- | --- | --- |
| L1 `covid.T3` | `P31` = positive campaign specimens with day ≤ 31; median over 24 seeds, target 634 | side is *compatible* |
| L2 onboard table | `P34` = positive campaign specimens with day ≤ 34 (crew wave armed); median over 24 seeds, target 691 of 3,894 | side is *compatible* |
| L3 during-quarantine mass | takeoff-seed median `infections_during_window` | inside [150, 350] |
| L4 `before_share` | takeoff-seed median of `onsets_before_split_day / recorded_onsets` | within 0.10 of 0.173 |
| L5 conditioned capture | takeoff-seed median of confirmed / infections_reachable, reachable = funnel `infection_day` ≤ 29 | ≥ 0.80 |

- **Side rule (L1, L2), verbatim from FIT-01:** *above* if the count exceeds
  the target on ≥ 18 of 24 seeds, *below* if under it on ≥ 18 of 24,
  otherwise *compatible*.
- **L3–L5** are scored only with ≥ 5 takeoff seeds at the θ; otherwise the
  leg reads "insufficient takeoff mass" and does not pass. The L4 band
  (±0.10) and the L3 band are QUAR-TAIL-SEAM-01's frozen thresholds; the L5
  floor and day-29 basis are COVID-CAPTURE-01's (five days before the last
  armed campaign day, 34).
- **Edges, verbatim from FIT-01.** Dead cell: `P31` = 0 on ≥ 20 of 24
  seeds. Saturated cell: median seedwise secondaries ≥ 0.95 ×
  (`aboard_total` − 1), secondaries being `infections_total` as written
  (index already excluded).
- **Consistent θ.** A θ is *consistent* iff all five legs pass and the cell
  is neither dead nor saturated. The result is the set of consistent θ. No
  θ is selected among consistent ones by any further rule; if there are
  several they are all reported.
- **Failing leg.** A leg that fails at every run θ is reported as the named
  next structure (plan §3): L4 failing everywhere → founder/ignition
  (Suite 2); L3 or L1/L2 pinned above at every non-dead θ with growth
  overshoot → routine-stage coolant (Suite 3). This is a report, not a
  refit.
- **Representativeness flag, verbatim from FIT-01 (reported, changes
  nothing).** At each consistent θ, if fewer than 6 of 24 seeds have `P31`
  in [317, 1268], the θ is labelled "median not representative".
- **Partial rows.** A row with fewer than 24 seeds is `provisional`: its
  legs are computed and shown, and no consistency verdict is issued. The
  20-seed canary is provisional by construction; an L1/L2 side that already
  has ≥ 18 seeds on one side is final for the 24.

**Reported, never scored:** founder yield (aboard-window acquisitions,
`seed_ring`) and ignition day where the payload carries them, attack rate,
secondaries, extinct seeds, `lab_confirmed_total`, unconditioned capture,
`recorded_onsets` against 197, infections before/during/after quarantine,
crew share of during-window infections, specimens through day 31 and 34,
the by-day specimen table, duty-excluded host count, realized exempt share.

**Known limits, stated before any cell.** L1 compresses near saturation
(FIT-01). L1 and L2 are not independent: `P34` ≥ `P31` on every cell, so L2
adds only the crew-wave increment (record: 57). With retest sweeps armed
the day ≤ 31 observation process is not FIT-01's, so L1 here is not a
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
  `SOP-017-DEDICATED-QUARTER` is the fired confinement order
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

The exact payload paths for the echo invariants are pinned from the local
smoke cell before the canary submits; a path that the payload does not
carry is recorded as "not echoed" in the campaign LEDGER, not silently
dropped.

**Report immediately:** no in-window positives where infections exist
(machinery gap); a dead or saturated union cell; a leg that fails at every
run θ; any audit deviation.

## Campaign

`campaigns/covid/dp_union_01/` — 5 blocks, 96 cells: `union_t3e9_canary`
(20) + `union_t3e9_rest` (4), `union_t1e9`, `union_t4e9`, `union_t1e10`
(24 each). Queue `picard-analysis-queue`, 1 vCPU / 4096 MB.

Canary gate: `union_t3e9_canary` (20 seeds, θ = 3.16e9, the θ FIT-01
selected) read out, then stop; the array runs only on Benjamin's decision.
