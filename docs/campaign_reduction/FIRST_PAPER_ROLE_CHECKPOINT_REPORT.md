# Role-checkpoint sidecar — invariance proof and baseline agreement (PAPER1-SENS Child A)

**Status:** instrumentation leg of the Paper-1 sensitivity campaign (venue02
follow-on). Emitter + `first_paper_scalar/1.5.0` delivered; no campaign
designed, submitted or ingested here (Child B).

Settled inputs (not re-derived): venue machinery PR #1147;
`first_paper_scalar/1.4.0`; venue02 delivered at SHA `526cf856`
(`FIRST_PAPER_VENUE02_REPORT.md`).

## What was added

| Piece | Where |
|---|---|
| Emitter (read-only, zero draws) | `picard_framework/simulation/role_checkpoints.py`; hooked in `ShipSimulation._step_record` after the epoch's surveillance + escalation phases, before `record_epoch`; scratch lives in the new `SimulationState.role_checkpoints` dict only |
| `summary.json` block | top-level `role_checkpoints` (copied from the final history record by `_attach_voyage_blocks` / `growth_chain_census._write_run_zip`, the venue02 campaign worker) |
| Contract | `FIRST_PAPER_SCALAR.json` → `first_paper_scalar/1.5.0`, 94 additive columns (`rc_d{3,7,10,12}_{available,epoch_index,hours_elapsed}`, `rc_d{d}_{passenger,crew}_<measure>`, `role_checkpoints_clock_json`, `role_checkpoints_definitions_json`) + a day-12 operand sum check (union partitions by eligibility); every 1.4.0 column untouched, definition hash changes |
| Config / sanity | `crusher_labs/config.yaml` `role_checkpoints: {enabled, days}`; `tools/sanity_checker.py::_check_role_checkpoints` |
| Tests | `tests/test_role_checkpoints.py` (timing, set identities, missingness, paired off/on smoke with RNG-state witness); `tests/analysis/campaign_reducer/test_d7_first_paper_scalar.py` (1.5.0 projection + explicit missingness on pre-sidecar summaries) |
| Evidence tool | `tools/diag/role_checkpoint_invariance.py` → ledgers in `role_checkpoint_evidence/` |

## Checkpoint timing (exact epoch mapping)

Day `d` is the hourly boundary `24·d` h after voyage start. With `h` hours
per epoch the snapshot is taken at the **end of epoch index
`24·d/h − 1`** (after that epoch's surveillance and escalation phases) and
is cumulative over epoch indices `0 .. 24·d/h − 1` inclusive.

| day | venue02 clock (`h = 1`, 288 epochs) | legacy epoch-day clock (`h = 24`) |
|---|---|---|
| 3 | epoch index 71 (72 epochs, 72 h) | 2 |
| 7 | 167 (168 h) | 6 |
| 10 | 239 (240 h) | 9 |
| 12 | 287 (288 h = terminal) | 11 |

A boundary that falls inside an epoch is covered by the epoch containing
it and flagged `exact_boundary: false`. A day the voyage never reaches is
emitted `available: false`, `status: not_reached`, all counts `null`
(never zero). Each checkpoint records its observed clock
(`epoch_index`, `epochs_completed`, `hours_elapsed`) and the block records
`clock.{mode, hours_per_epoch, num_epochs, observed_terminal_epoch,
epoch_mapping}`.

## Person sets and clinical eligibility

All counts are cardinalities of actual `set[int]` agent-ID sets
intersected with the role's roster (`role_group_for_agent`); union and
overlap are computed on the sets, never from totals or role proportions.
A person who reports on several epochs is one person.

| measure | set | clinically eligible? |
|---|---|---|
| `infected` | `ever_infected_ids ∩ role` (imports included) | n/a |
| `ill` | `ever_ill_ids ∩ role` — symptomatic presentation at any epoch (`update_ever_ill_ids`) | **reference set** for clinical-AGE eligibility |
| `unique_etiologic_reporters` | `ever_reported_ids ∩ role` — syndromic `true_positive_ids` ∩ symptomatic roster at report time (`update_ever_reported_ids`) | yes, by construction |
| `unique_clinical_noise_reporters` | `ever_reported_noise_ids ∩ role` — syndromic `noise_ids` (background sick-call presenters) | **no** — a noise presentation is not etiologic AGE |
| `reporter_overlap` | etiologic ∩ noise | mixed |
| `unique_person_union` | etiologic ∪ noise | **not a matched clinical-AGE endpoint** — a sick-call *presentation* set |
| `union_ever_ill` / `union_not_ill` | union ∩ `ever_ill_ids` / union − `ever_ill_ids` | the eligible / never-eligible partition of the union |
| `noise_reporters_ever_ill` | noise ∩ `ever_ill_ids` | noise reporters who had a genuine symptomatic episode at some point |
| `complement` | role roster size (departed included) — the same denominator the `summary` block uses | — |

Not counted anywhere: crew screening roster entries and caregiver reports
(neither reporter set). `cumulative_reported_cases*` in the existing
`summary` block **is** the etiologic set, so the sidecar's terminal
etiologic counts must equal it (checked below).

## Evidence design

Two distinct checks, run locally on the venue02 manifest
(`picard_framework/runs/mega_cruise_campaign/noro_provisioned_venue_02_manifest.json`),
seeds 8105/8106/8107 × two hulls (`fl_exp_12d_scr_q30_crewv`, n=450;
`fl_cls_12d_scr_q30_mixv`, n=1910), CPython 3.11 `.venv`, by
`tools/diag/role_checkpoint_invariance.py`. Edison's scout runs are not a
substitute for either (changed parameters cannot stand in for baseline replay).

1. **Paired replay** — the same implementation run twice per seed with
   `role_checkpoints.enabled` false then true. Pass criterion, declared before
   the runs: every `summary.json` block the emitter does not write
   (`summary`, `timeseries`, `derived`, `cost_accounting`, `trigger_status`,
   initiation) and the growth-chain census are **bit-identical**; the
   in-process RNG state after the final epoch is identical; the per-epoch
   history is identical once the `role_checkpoints` key is removed. Any
   difference fails.
2. **Baseline agreement** — the emitter-on run compared field-by-field with
   the same-seed zip produced by the delivered venue02 code at `526cf856`
   (a fresh worktree at that SHA, same `.venv`). Pass criterion: all
   epidemiological endpoints bit-identical; the day-12 sidecar counts equal
   the baseline `summary` cumulative endpoints
   (`cumulative_ever_infected_*`, `cumulative_ever_ill_*`,
   `cumulative_reported_cases_*`, `cumulative_reported_noise_cases`);
   float-only leaf differences below 1e-6 relative are **listed** as
   `float_drift` rather than failing (see the attribution below) — any
   integer, string, structural or larger-than-tolerance difference fails.

Ledgers: `docs/campaign_reduction/role_checkpoint_evidence/*.json`; the
tables below are rendered from them by
`tools/diag/role_checkpoint_report_tables.py` (no numbers typed by hand).

## Results

### Paired replay (emitter off vs on, same implementation)
| tier | seed | ledger | voyage blocks off==on | census off==on | initiation off==on | RNG state off==on | history off==on (minus sidecar) | sidecar off/on | pass |
|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_scr_q30_mixv | 8105 | cls_mixv.json | yes | yes | yes | not run | not run | absent/present | yes |
| fl_cls_12d_scr_q30_mixv | 8106 | cls_mixv.json | yes | yes | yes | not run | not run | absent/present | yes |
| fl_cls_12d_scr_q30_mixv | 8107 | cls_mixv.json | yes | yes | yes | not run | not run | absent/present | yes |
| fl_exp_12d_scr_q30_crewv | 8105 | exp_crewv.json | yes | yes | yes | yes | yes | absent/present | yes |
| fl_exp_12d_scr_q30_crewv | 8106 | exp_crewv.json | yes | yes | yes | yes | yes | absent/present | yes |
| fl_exp_12d_scr_q30_crewv | 8107 | exp_crewv.json | yes | yes | yes | yes | yes | absent/present | yes |

### Day-12 sidecar vs the run's own `summary` endpoints
| tier | seed | all.noise == cumulative_reported_noise_cases | crew.complement | crew.ill == cumulative_ever_ill_crew | crew.infected == cumulative_ever_infected_crew | crew.unique_etiologic_reporters == cumulative_reported_cases_crew | passenger.complement | passenger.ill == cumulative_ever_ill_passenger | passenger.infected == cumulative_ever_infected_passenger | passenger.unique_etiologic_reporters == cumulative_reported_cases_passenger | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_scr_q30_mixv | 8105 | 195 / 195 | 572 / 572 | 5 / 5 | 41 / 41 | 3 / 3 | 1338 / 1338 | 17 / 17 | 113 / 113 | 13 / 13 | yes |
| fl_cls_12d_scr_q30_mixv | 8106 | 178 / 178 | 572 / 572 | 8 / 8 | 41 / 41 | 7 / 7 | 1338 / 1338 | 19 / 19 | 116 / 116 | 13 / 13 | yes |
| fl_cls_12d_scr_q30_mixv | 8107 | 194 / 194 | 572 / 572 | 12 / 12 | 42 / 42 | 10 / 10 | 1338 / 1338 | 34 / 34 | 147 / 147 | 33 / 33 | yes |
| fl_exp_12d_scr_q30_crewv | 8105 | 50 / 50 | 134 / 134 | 0 / 0 | 5 / 5 | 0 / 0 | 316 / 316 | 5 / 5 | 29 / 29 | 5 / 5 | yes |
| fl_exp_12d_scr_q30_crewv | 8106 | 62 / 62 | 134 / 134 | 0 / 0 | 6 / 6 | 0 / 0 | 316 / 316 | 3 / 3 | 21 / 21 | 2 / 2 | yes |
| fl_exp_12d_scr_q30_crewv | 8107 | 59 / 59 | 134 / 134 | 2 / 2 | 4 / 4 | 1 / 1 | 316 / 316 | 5 / 5 | 22 / 22 | 5 / 5 | yes |

### Baseline agreement (same seed vs the venue02 526cf856 zip)
| tier | seed | baseline zip has sidecar | bit-identical | identical modulo float drift | float-drift leaves | float-drift paths | day-12 sidecar == baseline summary |
|---|---|---|---|---|---|---|---|
| fl_cls_12d_scr_q30_mixv | 8105 | no | yes | yes | 0 | — | yes |
| fl_cls_12d_scr_q30_mixv | 8106 | no | no | yes | 108 | `summary/sanitary_activity/dose_delivered`, `timeseries` | yes |
| fl_cls_12d_scr_q30_mixv | 8107 | no | yes | yes | 0 | — | yes |
| fl_exp_12d_scr_q30_crewv | 8105 | no | yes | yes | 0 | — | yes |
| fl_exp_12d_scr_q30_crewv | 8106 | no | yes | yes | 0 | — | yes |
| fl_exp_12d_scr_q30_crewv | 8107 | no | yes | yes | 0 | — | yes |

### Day-12 sidecar vs the 526cf856 baseline `summary` endpoints
| tier | seed | all.noise == cumulative_reported_noise_cases | crew.complement | crew.ill == cumulative_ever_ill_crew | crew.infected == cumulative_ever_infected_crew | crew.unique_etiologic_reporters == cumulative_reported_cases_crew | passenger.complement | passenger.ill == cumulative_ever_ill_passenger | passenger.infected == cumulative_ever_infected_passenger | passenger.unique_etiologic_reporters == cumulative_reported_cases_passenger | agree |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_scr_q30_mixv | 8105 | 195 / 195 | 572 / 572 | 5 / 5 | 41 / 41 | 3 / 3 | 1338 / 1338 | 17 / 17 | 113 / 113 | 13 / 13 | yes |
| fl_cls_12d_scr_q30_mixv | 8106 | 178 / 178 | 572 / 572 | 8 / 8 | 41 / 41 | 7 / 7 | 1338 / 1338 | 19 / 19 | 116 / 116 | 13 / 13 | yes |
| fl_cls_12d_scr_q30_mixv | 8107 | 194 / 194 | 572 / 572 | 12 / 12 | 42 / 42 | 10 / 10 | 1338 / 1338 | 34 / 34 | 147 / 147 | 33 / 33 | yes |
| fl_exp_12d_scr_q30_crewv | 8105 | 50 / 50 | 134 / 134 | 0 / 0 | 5 / 5 | 0 / 0 | 316 / 316 | 5 / 5 | 29 / 29 | 5 / 5 | yes |
| fl_exp_12d_scr_q30_crewv | 8106 | 62 / 62 | 134 / 134 | 0 / 0 | 6 / 6 | 0 / 0 | 316 / 316 | 3 / 3 | 21 / 21 | 2 / 2 | yes |
| fl_exp_12d_scr_q30_crewv | 8107 | 59 / 59 | 134 / 134 | 2 / 2 | 4 / 4 | 1 / 1 | 316 / 316 | 5 / 5 | 22 / 22 | 5 / 5 | yes |

### Cumulative checkpoints (emitter on)
| tier | seed | day | epoch | role | inf | ill | etio | noise | overlap | union | union∩ill | union−ill | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_scr_q30_mixv | 8105 | day_3 | 71 | passenger | 41 | 0 | 0 | 35 | 0 | 35 | 0 | 35 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_3 | 71 | crew | 13 | 0 | 0 | 16 | 0 | 16 | 0 | 16 | 572 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_3 | 71 | all | 54 | 0 | 0 | 51 | 0 | 51 | 0 | 51 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_7 | 167 | passenger | 67 | 4 | 2 | 81 | 0 | 83 | 2 | 81 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_7 | 167 | crew | 24 | 3 | 1 | 32 | 0 | 33 | 1 | 32 | 572 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_7 | 167 | all | 91 | 7 | 3 | 113 | 0 | 116 | 3 | 113 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_10 | 239 | passenger | 93 | 10 | 4 | 118 | 0 | 122 | 4 | 118 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_10 | 239 | crew | 33 | 4 | 3 | 43 | 0 | 46 | 3 | 43 | 572 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_10 | 239 | all | 126 | 14 | 7 | 161 | 0 | 168 | 7 | 161 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_12 | 287 | passenger | 113 | 17 | 13 | 144 | 0 | 157 | 13 | 144 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_12 | 287 | crew | 41 | 5 | 3 | 51 | 0 | 54 | 3 | 51 | 572 |
| fl_cls_12d_scr_q30_mixv | 8105 | day_12 | 287 | all | 154 | 22 | 16 | 195 | 0 | 211 | 16 | 195 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_3 | 71 | passenger | 40 | 4 | 4 | 40 | 0 | 44 | 4 | 40 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_3 | 71 | crew | 17 | 1 | 1 | 22 | 0 | 23 | 1 | 22 | 572 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_3 | 71 | all | 57 | 5 | 5 | 62 | 0 | 67 | 5 | 62 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_7 | 167 | passenger | 69 | 7 | 6 | 79 | 0 | 85 | 6 | 79 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_7 | 167 | crew | 28 | 4 | 2 | 37 | 0 | 39 | 2 | 37 | 572 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_7 | 167 | all | 97 | 11 | 8 | 116 | 0 | 124 | 8 | 116 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_10 | 239 | passenger | 101 | 13 | 8 | 102 | 1 | 109 | 9 | 100 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_10 | 239 | crew | 36 | 7 | 6 | 47 | 0 | 53 | 6 | 47 | 572 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_10 | 239 | all | 137 | 20 | 14 | 149 | 1 | 162 | 15 | 147 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_12 | 287 | passenger | 116 | 19 | 13 | 123 | 1 | 135 | 14 | 121 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_12 | 287 | crew | 41 | 8 | 7 | 55 | 0 | 62 | 8 | 54 | 572 |
| fl_cls_12d_scr_q30_mixv | 8106 | day_12 | 287 | all | 157 | 27 | 20 | 178 | 1 | 197 | 22 | 175 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_3 | 71 | passenger | 50 | 4 | 3 | 41 | 0 | 44 | 3 | 41 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_3 | 71 | crew | 15 | 2 | 0 | 17 | 0 | 17 | 0 | 17 | 572 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_3 | 71 | all | 65 | 6 | 3 | 58 | 0 | 61 | 3 | 58 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_7 | 167 | passenger | 94 | 11 | 8 | 73 | 1 | 80 | 8 | 72 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_7 | 167 | crew | 27 | 4 | 3 | 37 | 0 | 40 | 3 | 37 | 572 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_7 | 167 | all | 121 | 15 | 11 | 110 | 1 | 120 | 11 | 109 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_10 | 239 | passenger | 133 | 23 | 14 | 112 | 1 | 125 | 15 | 110 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_10 | 239 | crew | 38 | 7 | 4 | 51 | 0 | 55 | 4 | 51 | 572 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_10 | 239 | all | 171 | 30 | 18 | 163 | 1 | 180 | 19 | 161 | 1910 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_12 | 287 | passenger | 147 | 34 | 33 | 130 | 3 | 160 | 33 | 127 | 1338 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_12 | 287 | crew | 42 | 12 | 10 | 64 | 0 | 74 | 10 | 64 | 572 |
| fl_cls_12d_scr_q30_mixv | 8107 | day_12 | 287 | all | 189 | 46 | 43 | 194 | 3 | 234 | 43 | 191 | 1910 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_3 | 71 | passenger | 17 | 0 | 0 | 11 | 0 | 11 | 0 | 11 | 316 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_3 | 71 | crew | 2 | 0 | 0 | 3 | 0 | 3 | 0 | 3 | 134 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_3 | 71 | all | 19 | 0 | 0 | 14 | 0 | 14 | 0 | 14 | 450 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_7 | 167 | passenger | 22 | 3 | 2 | 20 | 0 | 22 | 3 | 19 | 316 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_7 | 167 | crew | 3 | 0 | 0 | 6 | 0 | 6 | 0 | 6 | 134 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_7 | 167 | all | 25 | 3 | 2 | 26 | 0 | 28 | 3 | 25 | 450 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_10 | 239 | passenger | 27 | 5 | 4 | 31 | 1 | 34 | 4 | 30 | 316 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_10 | 239 | crew | 4 | 0 | 0 | 11 | 0 | 11 | 0 | 11 | 134 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_10 | 239 | all | 31 | 5 | 4 | 42 | 1 | 45 | 4 | 41 | 450 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_12 | 287 | passenger | 29 | 5 | 5 | 35 | 1 | 39 | 5 | 34 | 316 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_12 | 287 | crew | 5 | 0 | 0 | 15 | 0 | 15 | 0 | 15 | 134 |
| fl_exp_12d_scr_q30_crewv | 8105 | day_12 | 287 | all | 34 | 5 | 5 | 50 | 1 | 54 | 5 | 49 | 450 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_3 | 71 | passenger | 9 | 0 | 0 | 14 | 0 | 14 | 0 | 14 | 316 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_3 | 71 | crew | 3 | 0 | 0 | 5 | 0 | 5 | 0 | 5 | 134 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_3 | 71 | all | 12 | 0 | 0 | 19 | 0 | 19 | 0 | 19 | 450 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_7 | 167 | passenger | 14 | 3 | 2 | 30 | 0 | 32 | 2 | 30 | 316 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_7 | 167 | crew | 5 | 0 | 0 | 12 | 0 | 12 | 0 | 12 | 134 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_7 | 167 | all | 19 | 3 | 2 | 42 | 0 | 44 | 2 | 42 | 450 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_10 | 239 | passenger | 18 | 3 | 2 | 39 | 0 | 41 | 2 | 39 | 316 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_10 | 239 | crew | 5 | 0 | 0 | 13 | 0 | 13 | 0 | 13 | 134 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_10 | 239 | all | 23 | 3 | 2 | 52 | 0 | 54 | 2 | 52 | 450 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_12 | 287 | passenger | 21 | 3 | 2 | 46 | 0 | 48 | 2 | 46 | 316 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_12 | 287 | crew | 6 | 0 | 0 | 16 | 0 | 16 | 0 | 16 | 134 |
| fl_exp_12d_scr_q30_crewv | 8106 | day_12 | 287 | all | 27 | 3 | 2 | 62 | 0 | 64 | 2 | 62 | 450 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_3 | 71 | passenger | 7 | 0 | 0 | 11 | 0 | 11 | 0 | 11 | 316 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_3 | 71 | crew | 1 | 0 | 0 | 5 | 0 | 5 | 0 | 5 | 134 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_3 | 71 | all | 8 | 0 | 0 | 16 | 0 | 16 | 0 | 16 | 450 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_7 | 167 | passenger | 11 | 2 | 2 | 24 | 1 | 25 | 2 | 23 | 316 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_7 | 167 | crew | 1 | 0 | 0 | 10 | 0 | 10 | 0 | 10 | 134 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_7 | 167 | all | 12 | 2 | 2 | 34 | 1 | 35 | 2 | 33 | 450 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_10 | 239 | passenger | 17 | 3 | 3 | 35 | 1 | 37 | 3 | 34 | 316 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_10 | 239 | crew | 2 | 1 | 0 | 14 | 0 | 14 | 0 | 14 | 134 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_10 | 239 | all | 19 | 4 | 3 | 49 | 1 | 51 | 3 | 48 | 450 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_12 | 287 | passenger | 22 | 5 | 5 | 42 | 1 | 46 | 5 | 41 | 316 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_12 | 287 | crew | 4 | 2 | 1 | 17 | 0 | 18 | 1 | 17 | 134 |
| fl_exp_12d_scr_q30_crewv | 8107 | day_12 | 287 | all | 26 | 7 | 6 | 59 | 1 | 64 | 6 | 58 | 450 |

## The baseline float difference, attributed

In the committed ledgers one of the six same-seed runs differs from its
526cf856 zip, in exactly one leaf family: classic 8106,
`sanitary_activity.dose_delivered` (`summary` and the 107 `timeseries`
epochs after the first divergent sum; 71271.690128 vs 71271.690033,
~1e-9 relative). The other five are bit-identical. An earlier pass of the
same check (first script revision, not committed) showed the same family on
expedition 8105 — 7241.824956 vs 7241.82451, ~6e-8 relative — while the
committed rerun of 8105 is bit-identical: the difference comes and goes
between processes with no code change, which is what the attribution below
measures. No epidemiological field, count, census or trigger differs on any
seed or hull in any pass.

Measured attribution (same checkout, same seed, same `.venv`, nothing but the
interpreter's string-hash seed varied):

| run | `PYTHONHASHSEED` | `summary.sanitary_activity.dose_delivered` |
|---|---|---|
| 526cf856 baseline zip (`.venv`, unset) | random | 7241.824956 |
| current branch, run A | 0 | 7241.824956 |
| current branch, run B | 0 | 7241.824956 |
| current branch | 1 | 7241.82451 |
| aa865ac2 worktree (unset) | random | 7241.82451 |
| 3271d862 fresh worktree (unset) | random | 7241.825132 |

Measured on expedition 8105 (the seed that drifted in the first pass);
classic 8106 is the same leaf family and is inferred, not separately
measured. The value is a deterministic function of `PYTHONHASHSEED`, not of
the commit:
that telemetry sum iterates a `str`-keyed set/dict in hash order, so its float
association order follows the interpreter's per-process hash seed. The
emitter off/on pair within one process agrees bit-for-bit on the same field,
so it is unrelated to this change. **Follow-up, not done here** (engine/runner
change, out of scope): pin `PYTHONHASHSEED=0` in the campaign entrypoint or
sort that iteration; until then that one sanitary telemetry leaf is
reproducible only within a hash seed. No epidemiological endpoint is affected.

## How to consume the sidecar

- `summary.json["role_checkpoints"]` (schema `role_checkpoints/1.0`): one
  entry per requested day with `available`, `status`, `epoch_index`,
  `epochs_completed`, `hours_elapsed`, `exact_boundary`, and
  `passenger` / `crew` / `all` count dicts; `clock` records
  `mode`, `hours_per_epoch`, `num_epochs`, `observed_terminal_epoch`,
  `epoch_mapping`; `definitions` states the set algebra above verbatim.
- `first_paper_scalar/1.5.0` projects it as `rc_d{day}_{role}_{measure}`
  columns plus `rc_d{day}_{available,epoch_index,hours_elapsed}`,
  `role_checkpoints_clock_json`, `role_checkpoints_definitions_json` —
  summary-only reads, no census decode. Pre-sidecar archives (venue02 as
  delivered) reduce with explicit nulls and a provenance flag; every 1.4.0
  column is unchanged in name, type and value.
- A day beyond the run length is emitted `available: false` with null counts,
  not an error; the sanity checker rejects only non-boolean `enabled`,
  non-distinct or non-positive days, and day boundaries that do not fall on
  an epoch boundary.

## Non-goals honoured

No campaign designed, submitted or ingested; no engine behaviour, draw order
or RNG consumption changed; no COVID/flu work; no constant touched.
