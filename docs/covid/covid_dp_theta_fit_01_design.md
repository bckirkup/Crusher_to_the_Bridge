# covid-dp-theta-fit-01 — extended-horizon theta fit against covid.T3 (measured on three of seven θ)

**Status:** measured on θ {1e9, 3.16e9, 1e10}; the four θ below 1e9 were not run by owner decision after the canary. Criteria below are frozen before any fit cell ran;
no criterion may be altered after the surface is seen.

## Scope

Fit θ on the `replay_niid` arm against `covid.T3` on the extended
horizon (Benjamin 2026-11-23, "Go with A"). The pilot's 120-epoch
pre-quarantine window is not the fit window; the pilot design and
readouts are frozen references and are not modified.

- Design file: `picard_framework/runs/covid_dp_theta_fit_01_design.json`
  (`design_id` `covid-dp-theta-fit-01`, parent `covid-dp-theta-pilot-01`).
- Arm run: `replay_niid` only, overrides copied verbatim from the pilot
  (diamond_princess platform, `protocols_covid_dp_dedicated.json`,
  SOP-017-DEDICATED days 16–30 from 07:00, NIID `seed_patch` onset day
  3.0 / infection age 2.8 d, declared itinerary, diamond rhythm catalog).
  `replay_baseline` stays in the design file because the loader requires
  an empty-override first arm; no campaign block runs it.
- Seeds: 24 matched seeds, 20200205–20200228, matched across every θ.
- Horizon: the scenario's full declared voyage (35 days from 20 Jan
  2020, 840 epochs). No block passes a horizon. Quarantine activates at
  epoch 391 (5 Feb 07:00) and the published 5–20 Feb testing campaign
  (day indices 16–31) runs inside the cell.
- Thetas: **{1e7, 3.16e7, 1e8, 3.16e8, 1e9, 3.16e9, 1e10}** — seven
  half-decade values, 168 cells.
- No epidemiological constant changes; θ is the only swept quantity.

## Why the grid sits below the pilot bracket

Measured before the freeze, none of it scored:

- Pilot (120 epochs, 24 seeds, `replay_niid`): index-attributable
  (clean-bound) acquisitions pooled over seeds were 114 / 210 / 329 /
  486 / 674 at θ = 1e10 / 3.16e10 / 1e11 / 3.16e11 / 1e12 — a slope of
  about θ^0.39. Total acquisitions over clean-bound were 1.7 / 4.8 /
  18.6 / 29.0 / 43.1, so secondary generations already dominate inside
  120 h at the upper θs.
- Two pre-freeze smoke cells at the pilot's lowest θ (1e10, seeds
  20200205 and 20200212, full voyage, pilot worker, main da6365ba):
  3,414 and 3,333 of 3,711 infected (attack 0.92 / 0.90), 2,913 and
  2,600 of them before quarantine; campaign positives 745 and 821 on
  2,608 and 2,829 specimens. Those seeds had 20 and 3 secondaries at
  120 epochs in the pilot.

Inference: on the full voyage every pilot θ is at or beyond saturation
on seeds that take off, so the T3 bracket lies below 1e10. How far
below is not measured. If the per-generation yield kept the pilot's
θ^0.39 slope the bracket would be near 1e7–1e8; if it is linear in θ
(the low-dose limit of the dose-response) it would be near 1e9. The
grid spans both readings at half-decade spacing and keeps 1e10 as the
upper reference edge. Values below 1e10 are outside the window
DP-REPLAY-DOSE-DIAG-01 normalised; that is recorded, not corrected.

## Frozen criteria

**Scored quantity (the T3 mapping).** Per cell,
`P = dp_theta_fit.t3.positives_through_day`: the number of positive
rows in the campaign specimen log (`campaign_specimen_log`, channel
`campaign_confirmed`) whose specimen day index is ≤ 31 (20 Feb). The
observation process is the shipped scenario's: published daily test
volumes 5–20 Feb, `retest_negatives_on_indication` as shipped, the
23 Feb `crew_wave` not armed. `lab_confirmed_total` is a different
channel (every lab-confirmed host, not the campaign's specimens) and is
reported only. The target is `covid.T3` = **634** positives (of 3,063
tests).

**Per-θ statistic.** `S(θ)` = median of `P` over the 24 matched seeds.

**Side of the target.** θ is *above* T3 if `P > 634` on ≥ 18 of 24
seeds, *below* if `P < 634` on ≥ 18 of 24, otherwise *T3-compatible*.

**Edges.**
- dead cell: `P = 0` on ≥ 20 of 24 seeds;
- saturated cell: median seedwise secondaries ≥ 0.95 ×
  (`aboard_total` − 1). Secondaries are `infections_total` as written
  by the worker, which already excludes the seeded index host (the
  first draft of this line subtracted the index a second time; corrected
  before the canary, with no fit cell run).

**Bracket.** The lowest adjacent grid pair with
`S(θ_lo) < 634 ≤ S(θ_hi)`. The grid *covers* T3 iff such a pair exists.
The bracket's point estimate θ\* is the linear interpolation of `S`
against log10 θ at 634.

**Selected θ.** Among T3-compatible θs that are neither dead nor
saturated, the one minimising `|S(θ) − 634|`; ties go to the lower θ.
If no θ is T3-compatible the result is the bracket alone, and the
pre-declared refinement below runs.

**Representativeness flag (reported with the selection, does not change
it).** If fewer than 6 of 24 seeds at the selected θ have `P` within
[317, 1268] (half to twice the target), the selection is labelled
"median not representative" — the cell is a mixture of extinct and
taken-off seeds and no single seed resembles the target.

**Pre-declared refinement (a second submission, same criteria).** Three
θs log-equispaced inside the bracket (θ_lo × 10^(k/8), k = 1, 2, 3 for
a half-decade bracket), same 24 seeds, appended to the design's
`thetas`; the selector is then re-applied to the union. It needs its
own go-ahead.

**Secondary cross-check (reported, never selected on).** The onboard
table's 691 positives of 3,894 tests through 23 Feb requires the
`crew_wave` and retest sweeps to be armed, which is a different
observation process from the one T3 is scored on. It is run only at
the selected θ, on the same 24 seeds, after selection.

**Reported, never selected on:** attack rate and secondaries, extinct
seed count, `campaign_specimens` against 3,063, positive share against
0.207, `recorded_onsets` against `covid.T1` (197), the T2 turn,
`lab_confirmed_total`, infections before/during/after quarantine, the
by-day specimen table. Held-out anchors (`covid.H*`) are not read.

**Known limit of the scored quantity (measured at the two smoke cells,
stated before the fit).** At attack ≈ 0.9 the campaign returned 745
and 821 positives, 1.2–1.3 × the target. `P` is capped by the test
schedule and the assay's timing, so it compresses near saturation: a
θ can match 634 while its attack rate is far above the roughly 19 %
the outbreak record implies. The fit selects on `P` as decided; the
attack rate at the selected θ is reported beside it and the
interpretation must state it.

**Audit invariants (deviation = defect, not failed criterion):**

- resolved platform `diamond_princess`; `index_onset_day` 3.0;
- `dose_response.susceptibility_scale` = θ·(α+β)/α with α=0.18, β=58;
- quarantine witness activated at epoch 391;
- no `close_zones` protocol fired;
- testing ran: specimens through day 31 > 0 on every cell;
- no specimen after day 31 and no wave-tagged specimen;
- `P` equals `observables.campaign_positives`.

**Report immediately:** no in-window positives where infections exist
(machinery gap); no bracket on the grid; a dead or saturated cell.
The 1e10 edge is expected to be saturated or nearly so from the smoke
cells; it is still reported when measured on 24 seeds.

## Campaign

`campaigns/covid/dp_theta_fit_01/` — 8 blocks: θ=1e9 split canary 20 +
rest 4, six other θ blocks × 24 seeds. Worker `cell.py` reduces the
specimen log to the `dp_theta_fit.t3` block; `readout.py` applies the
criteria above with the thresholds as module constants.

Canary gate: `niid_t1e9_canary` (20 seeds, θ=1e9) read out before any
array submit. A cell took about 44 min on one vCPU at θ=1e10.
