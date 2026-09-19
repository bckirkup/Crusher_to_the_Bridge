# COVID Theta screen v9: extinction-or-burn at every decade, and an inert age axis

> **Status:** Findings (2026-09-19). Campaign `covid_theta_screen_v9`, declared
> in `picard_framework/runs/covid_theta_screen_v9_design.json` (#615) and run on
> AWS Batch at `main` = `0fb186b`, image
> `picard-campaign:theta-screen-v9-0fb186b`
> (`sha256:85936b12231738770db3bed90e0e3bdcf626c840e617efcc783c3b3a0ad22aa0`),
> job definition `picard-covid-boarding-screen:7`, array job
> `913e36b9-bad2-4f65-a1c6-9ea450bb395e` on `picard-campaign-queue`.
> 600 of 600 cells SUCCEEDED, zero failures, 51 min wall clock, no
> `--allow-partial`. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v9/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v9_design.json --cells <synced cells dir> --out <surface json>`.
> Surface: `docs/covid/covid_theta_screen_v9_surface.csv` (one row per
> (Θ, age) cell, per-seed `recorded_onsets` vector included).
> No Theta is claimed here, and no figure below may be quoted as a fit.

The screen is the stage-1 downward recentring declared after the v8 probes
(`docs/ledger/THETA-SCREEN-V8.md`): ten decade Θ from 1e1 to 1e10 × three
declared index infection ages (3.3 / 6.8 / 12.8 d) × 20 matched seeds (base
20200205), one declared import, `dwell_weighted` sanitary visits, on
`diamond_princess_2020` with the index's onset declared at day −1 and its
departure at day 5 (SEED-ONSET-01, INDEX-GEOM-01). `covid.T1` was the sole
selection criterion, frozen in the design file before any cell ran; `covid.T3`
and `onset_mass_near_target` were declared diagnostics. Nothing in the
criterion was changed after the surface was observed.

## 1. The index-geometry invariant holds everywhere

`index_onset_day == -1.0`, `index_shedding_at_day0 == true` and
`index_departed_epoch == 120` in all 600 cells (`index_geometry_pass_fraction`
= 1.0 in every (Θ, age) row). The sanitary witness is consistent in 600/600
cells. There is no seeding-path defect on this surface.

## 2. The infection-age axis is inert — measured, then explained

**Measured.** For every one of the 200 (Θ, seed) pairs, the three payloads at
ages 3.3, 6.8 and 12.8 d are byte-identical outside the `cell` block
(`observables`, `onset_curve`, `infections_total`, `attack_rate`, the index
geometry, the sanitary record — everything). The surface therefore has 200
distinct cells, each reported three times; every per-Θ row below is the same
row at all three ages.

**Explained (read in the tree, `engines/initiation.py::_apply_one_seed`).**
`diamond_princess_2020` declares `onset_day = -1.0` on its explicit seed.
When `onset_day` is declared the seed's incubation is not drawn: it is set to
`infection_age_days + onset_day − seed_day` = age − 1.0 d, and the host's
symptomatic history is stamped from `elapsed_since_onset = seed_day − onset_day`
= 1.0 d. `time_infected` moves with the age and the incubation moves with it by
the same amount, so the host's phase at epoch 0 — one day past onset, shedding
— is fixed by the record and the age cancels exactly. This is exactly what the
scenario's own provenance note says (`covid_hull_scenarios.json`,
`explicit_seeds[0].infection_age_days`: "with onset_day declared, the infection
age no longer states an independent fact"); the v8/v9 designs swept it anyway on
the belief that the implied incubation still shaped the index's shedding, and
it does not. A byte-identical triple in an agent-based model with a shared seed
is stronger than any statistical test: the age never reaches a draw.

**Consequences.**
- v9 is a 10-Θ × 20-seed locator, not a 30-cell surface. Its Θ conclusions
  below stand on 20 seeds each; the age axis carries no information and its
  600-cell cost was 400 cells of exact duplication.
- Any infection-age contrast on `diamond_princess_2020` under a declared
  `onset_day` is void — that includes the age axis of the never-run v8 design
  and the "three ages" framing in THETA-SCREEN-V8/V9. The v7 age axis is not
  affected (v7 ran before SEED-ONSET-01, with the incubation drawn), but v7's
  geometry rows were already void for the other reason recorded in
  `covid_open_ledger.md`.
- A future design that wants to vary the index's boarding state on this
  scenario must vary something the record leaves free (e.g. drop `onset_day`
  and declare the age, which re-opens the drawn-incubation lottery v7 had), or
  accept that the record pins it. This is a design decision, not a defect to
  patch in the engine: the engine is doing what the declared record says.

## 3. `covid.T1`: admissible set = {Θ = 1e9}, and the pass is vacuous

`covid.T1` as declared: the cell's seed 10th-to-90th percentile interval of
`recorded_onsets` contains 197, and the cell's median `before_share` is within
0.10 of 0.173. Per Θ (20 seeds; identical at all three ages):

| Θ | onsets p10 | onsets p90 | median | takeoff P (>10% attack) | mass in [98.5, 394] | before_share med | attack q50 | attack q90 | T1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1e1 | 0 | 0 | 0 | 0.00 | 0.00 | — | 0.000 | 0.000 | no |
| 1e2 | 0 | 0.1 | 0 | 0.00 | 0.00 | 1.00 | 0.000 | 0.000 | no |
| 1e3 | 0 | 1.1 | 0 | 0.00 | 0.00 | 1.00 | 0.000 | 0.000 | no |
| 1e4 | 0 | 2.5 | 0 | 0.10 | 0.05 | 1.00 | 0.000 | 0.001 | no |
| 1e5 | 0 | 285 | 0 | 0.15 | 0.10 | 1.00 | 0.000 | 0.115 | no |
| 1e6 | 0 | 152 | 0 | 0.10 | 0.00 | 1.00 | 0.000 | 0.047 | no |
| 1e7 | 0 | 994 | 1 | 0.20 | 0.00 | 0.56 | 0.000 | 0.327 | no |
| 1e8 | 0 | 2,865 | 1.5 | 0.35 | 0.05 | 0.34 | 0.001 | 0.804 | no |
| **1e9** | 0 | 3,323 | 1,008 | 0.60 | **0.00** | 0.21 | 0.315 | 0.924 | **yes** |
| 1e10 | 361 | 3,498 | 3,382 | 0.85 | 0.00 | 0.51 | 0.936 | 0.957 | no |

Per-seed `recorded_onsets`, sorted, at the cells that matter:

- Θ 1e8: `0 0 0 0 0 0 0 0 1 1 2 2 3 42 156 633 2657 2842 3072 3129`
- Θ 1e9: `0 0 0 1 1 1 1 2 969 982 1034 1474 2330 3103 3103 3187 3277 3318 3368 3379`
- Θ 1e10: `0 0 401 837 2980 3005 3245 3309 3318 3376 3387 3395 3434 3465 3466 3474 3484 3495 3522 3539`

**Reading.** Θ = 1e9 is the one T1-admissible cell, and it is interior (1e8 and
1e10 both fail), so it is not a boundary result. But it passes exactly the way
THETA-SCREEN-V8 warned the criterion could be passed: its interval runs from an
extinction floor (p10 = 0; 8 of 20 seeds record ≤ 2 onsets) to a burn ceiling
(p90 = 3,323; 12 of 20 seeds record 969–3,379), and it contains 197 by
spanning it. `onset_mass_near_target` at 1e9 is **0.00** — not one of its 20
seeds lands within a factor of two of the observed 197. The largest mass
anywhere on the surface is 0.10 (two seeds, 277 and 356, at Θ 1e5), and no Θ
reaches 0.15. There is no cell whose typical seed reproduces Diamond Princess.

The criterion is not rewritten here. Under `covid.T1` as declared, the measured
result of record is: **admissible set = {1e9}, interior, passing by
interval-span with zero mass near target.** A reader who takes the interval as
the criterion gets 1e9; a reader who takes the diagnostic gets an empty set;
both readings are on this page, which is what v8 asked the v9 readout to make
possible.

## 4. What the Θ axis actually shows

The surface is extinction-or-burn at every decade. Conditional on takeoff
(attack > 0.10), the median outcome is a burn from 1e6 upward (conditional
median `recorded_onsets` 1,821 at 1e6, 1,582 at 1e7, 2,657 at 1e8, 3,103 at
1e9, 3,391 at 1e10 — against 197 observed), and what Θ moves is the takeoff
probability: 0 at ≤ 1e3, 0.10–0.20 across 1e4–1e7, 0.35 at 1e8, 0.60 at 1e9,
0.85 at 1e10. The only cells that produce DP-sized outbreaks are the rare
takeoffs at 1e4–1e5 (16, 122, 277, 356, 775 onsets in five seeds out of 40),
and those sit at a takeoff probability of 0.10–0.15, i.e. one voyage in seven
to ten.

This is the same shape v7 and the v8 probes showed, now measured over the six
decades below 1e7 that no screen had visited: the 1e1 floor is inert as the
design predicted, so the sweep brackets the region — there is simply no
near-critical band inside it where a *typical* single-import voyage produces
~200 onsets. With one index case that disembarks on day 5 and a 3,711-host
hull, the model's single-Θ response is a step from extinction to saturation,
and Θ sets the step's height, not its location on the onset axis.

Diagnostics, reported and not selected on:
- `covid.T3` fails at every Θ. Campaign specimens saturate at ~3,030–3,060 for
  Θ ≤ 1e9 (2,100 at 1e10, where the ship burns before the campaign), as in v7.
- `before_share` (onsets before day 17 ÷ total) falls with Θ from 1.0 (the only
  onsets are early) to 0.21 at 1e9, then rises to 0.51 at 1e10 as the burn
  moves earlier. The 1e9 value is within 0.10 of the 0.173 target — the second
  T1 clause is genuinely met there, for what a bimodal median is worth.
- VSP threshold crossing fraction tracks takeoff probability (0.05 → 0.85).

## 5. What this does and does not settle

Settled (measured at `0fb186b`, 20 seeds per Θ):
- Θ ≤ 1e3 with one declared import is inert (no takeoff in 60 seed-voyages).
- No Θ in [1e1, 1e10] has more than 10% of seeds within [98.5, 394]
  recorded onsets; the T1 interval pass at 1e9 is a bimodality artefact of the
  criterion's interval form, exactly as pre-registered as a risk in
  THETA-SCREEN-V8.
- The declared-onset scenario makes `infection_age_days` a no-op; the age axis
  of v8 and v9 is void.

Not settled, and not to be inferred from this surface:
- Whether a *different* import geometry (several imports, or an import the
  record does not pin to day −1 / day 5) has a near-critical band. v9 ran one
  import at one declared geometry.
- Whether the takeoff-probability curve itself (0.10 at 1e4 → 0.85 at 1e10) is
  the right object to score against the fleet (`covid.H3` says the real fleet
  is near-critical, so a step response may be the *correct* single-voyage
  shape and the calibration target should be the step's height, not a
  reproduced DP trajectory). That is a criterion question and must be declared
  in a design file before any cell runs on it.

## 6. Recommendation to the successor (stage 1b is **not** what v9 planned)

The v9 design pre-committed a stage 1b as "a half-decade, 40-seed, six-age
refinement of whatever band this finds". Two of its three axes are now known
to be wrong: the age axis is inert, and there is no band to refine — a
half-decade 40-seed grid around 1e9 would measure the takeoff probability more
precisely and still find zero mass near 197. Spending a campaign on it is the
v8 mistake in a new place.

The one decision this surface poses is a **criterion decision, not a grid
decision**, and it belongs to Benjamin before any further cell runs: whether
the Θ calibration target on `diamond_princess_2020` should be
(a) the DP trajectory itself under `covid.T1` as declared — in which case this
surface says the single-import declared-geometry model cannot produce it at any
Θ and the import geometry, not Θ, is the next thing to vary; or
(b) the single-voyage takeoff probability against the fleet anchor `covid.H3`,
with the DP onset count scored *conditional on takeoff* — in which case the v9
surface already contains the measurement (takeoff P(Θ), conditional medians)
and the successor declares that criterion in a `covid_theta_screen_v10` design
file, with this readout as the stated reason, before running anything.

Either way the age axis is dropped, and a design that wants to exercise the
index's boarding state on this scenario must first decide what to un-declare.
