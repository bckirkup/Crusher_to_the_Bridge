# noro_paper1_joint_eval_01

Paper-1 WP2 joint four-hull evaluation. Status: **authored and gated**. No
array, canary or census child has run. The WP1 freeze is proposed, not
declared; every Batch stage waits for the declaration.

## Frozen inputs

- Design: `DESIGN.md`. Strata, selection rule, technical-completion gate,
  diagnostic bands, continuation map and precision rules were fixed before
  the local smokes below and are carried in `manifest.json`
  (`joint_eval`).
- Builder: `design/build.py`; `--check` reproduces `manifest.json` and
  `campaign.json`; `--select DIR` applies the selection rule to census
  rows.
- Baseline block: freeze contract section 2, stored as
  `joint_eval.baseline_block` and carried verbatim as `config_overrides`
  by every census, bridge and pilot tier. 70 leaves; sha256 (sorted, compact
  JSON) `f6a603bed0ca…` (full value: `joint_eval.baseline_sha256`).
- Worker `cell.py` (schema `paper1_joint_eval_cell/2.0.0`), hook
  `entry.py` (`PYTHONHASHSEED=1`), readout `readout.py`.

## Counts

- Stage A (emitted): census 4 hulls x 200 children x 100 seeds = 800
  children; reproduction arm 16. Total 816.
- Stage B (emitted once `design/seed_selection.json` exists): bridge 36
  tiers x 20 = 720; joint-outcome pilot 8 tiers x 20 = 160. Total 880.

## Local gates (authoring)

All runs local, commit `77f429b3` plus the uncommitted working tree of this
PR, `PYTHONHASHSEED=1`. Each line is measured on the one seed named.

- [x] Criteria and rules written to `design/build.py` before any run.
- [x] `design/build.py --check`: build reproduces.
- [x] `scripts/campaign describe noro/paper1_joint_eval_01`: 5 blocks,
  816 children = Stage A in `DESIGN.md`.
- [x] `scripts/campaign submit --dry-run` on all 5 blocks: array sizes
  200 / 200 / 200 / 200 / 16; nothing registered or submitted.
- [x] Stage B shape checked by test with a synthetic selection: 36 bridge +
  8 pilot tiers, 880 runs, block verbatim on every tier.
- [x] Smoke, bridge arm, `expedition_cruise_450`, 48 epochs, seed 2000000
  (synthetic selection, out-of-tree manifest): members `summary.json`,
  `joint_eval.json.gz`; 70 declared leaves, 80 effective leaves after the
  runner's axes, 0 runner-changed, 0 engine-resolved mismatches; arm
  `changed_paths=[]`; roles 316 / 134 on agents and in the payload; six
  families `present`; 2,256 swabs (120 rows with recovered copies, all
  censored below LOD), 48 holding-tank assays (36 detected, first at epoch
  12); line list received with 0 cases.
- [x] Smoke, bridge arm, `mega_cruise_5000`, 24 epochs, seed 2300004: same
  checks pass; roles 4,900 / 2,100; line list received with 3 passenger
  onsets on day 0; 1,858 swabs, 24 tank assays (23 detected).
- [x] Smoke, reproduction arm index 0 (seed 900470), 24 epochs, from the
  committed manifest: declared arm differences accepted, roles 316 / 134,
  archive written.
- [x] Census worker, 4 seeds (2000000–2000003), 1 epoch, 100 agents, tier
  `fl_je_census_exp`: 0 errors; `provisioned_source.norwalk_gi` present
  with `q_source_drawn` between 0.0023 and 0.0042 (the registry interval,
  not a pin) and `n_contaminated=0` on all four.
- [x] `cell.py --verify-draws`, `expedition_cruise_450`, 96 epochs, seed
  2000000: instrumented and control voyage fingerprints equal
  (`3cbbe820…`). One seed, one hull.
- [x] `tests/test_paper1_joint_eval_campaign.py`: 30 passed.

Not exercised locally: a posted voyage, a detected swab, a crew onset, and
any run longer than 96 epochs.

## Amendment 2026-11-20: declared role split

Owner decision after the authoring PR (#1358): run each platform's declared
`nominal_complement`. Every census, bridge and pilot tier now declares one
difference from the block, `ship_graph.agent_classes` (`build.py`,
`class_mix`); the block itself is unchanged. Counts are unchanged (Stage A
816, Stage B 880). The smokes above predate this amendment; they ran the
template split.

Local gates re-run after the amendment (measured, one seed each, 24 epochs,
synthetic selection, `PYTHONHASHSEED=1`):

- [x] `design/build.py --check`: build reproduces; `describe`: 5 blocks,
  816 children.
- [x] Bridge-arm smoke per hull, tier `fl_je_<hull>_7d_quiet` index 0:
  roles on initialised agents and in the payload equal the declared
  nominal — exp 300/150 (seed 2000000), cls 1,350/560 (2100000), spr
  2,100/900 (2200000), meg 5,000/2,000 (2300000); arm `changed_paths` is
  `ship_graph.agent_classes` only; 0 runner-changed leaves, 0
  engine-resolved mismatches; six families `present`.
- [x] `ship_graph` keeps every shipped sibling key when only
  `agent_classes` is overridden (measured at initialise on all four hulls).
- [x] `tests/test_paper1_joint_eval_campaign.py`: 35 passed.

Not re-run after the amendment: `--verify-draws`, the census worker, and the
48- and 96-epoch smokes.

## Amendment 2026-11-20: hash seed pinned in the worker

Reported by the WP3 review and checked on main: neither the shared job
definition template nor the campaign image sets `PYTHONHASHSEED`, although
the freeze contract (section 2.5) says the job definition does. `cell.py`
now re-executes itself under `PYTHONHASHSEED=1` and records the value in
every archive; the readout requires it. `DESIGN.md` ("Hash seed: contract
versus actual") records the gap for WP1b's contract revision.

- [x] Worker run as a script with `PYTHONHASHSEED` unset (reproduction arm
  index 0, seed 900470, 24 epochs): archive records `python_hash_seed` =
  `"1"`. One seed.
- [x] `tests/test_paper1_joint_eval_campaign.py`: 36 passed.

## Findings recorded during authoring

- With the block alone, initialised role counts differ from the platforms'
  declared nominal split on three hulls (exp 316/134 vs 300/150; cls
  1,338/572 vs 1,350/560; meg 4,900/2,100 vs 5,000/2,000; spr equal).
  Measured at initialise on two seeds per hull. Resolved by the amendment
  above.
- Compact retention drops the swab and holding-tank results from the epoch
  record; the worker reads them through the read-only observer hook.
- The census row keys `provisioned_source` by pathogen id; the selection
  rule reads `provisioned_source[norwalk_gi].n_contaminated`.

## Stage A executed (2026-11-21)

- [x] Census arrays: 4 x 200 chunks x 100 seeds (80,000 census voyages, 1
  epoch, 100 agents) — `census_exp` `e54512b0`, `census_cls` `0cb75ca3`,
  `census_spr` `d0901e8b`, `census_meg` `0f104ec4` (Batch job ids, full
  ids in the session record). All 800 children SUCCEEDED.
- [x] Reproduction arm `fl_je_repro_exp_solver01_station_continuous`
  `2b30c05b` — all 16 children SUCCEEDED; archives carry
  `joint_eval` schema `paper1_joint_eval_cell/2.0.0`.
- [x] Census contract: 20,000 rows per hull, full declared seed frame per
  hull exactly once, 0 error rows. Contaminated-draw rate rises with hull
  size: exp 5.92%, cls 9.26%, spr 15.26%, meg 17.29%.
- [x] `build.py --select` applied the frozen rule:
  `design/seed_selection.json` — per hull 20 quiet + 20 near + 20 outbreak
  (diagnostic) and 20 + 20 evaluation seeds (hash-ranked over the
  uncontaminated/contaminated frames).
- [x] Rebuild emits 49 tiers / 49 blocks / 1,696 children = 816 Stage A +
  880 Stage B (bridge 36 x 20 + pilot 8 x 20, as declared).
- [x] `tests/test_paper1_joint_eval_campaign.py`: 39 passed (the
  Stage-A-count test now counts the five Stage-A blocks explicitly; total
  moved to 1,696 because the committed selection emits Stage B —
  attributable to this diff).

Job definition: `picard-noro-paper1-joint-eval-01` revs `:3`–`:7`; image
`sha256:354b27b6…55d82` (built at freeze commit `bf0ec168`).

## Gated (canary in flight)

Done: image rebuilt at `90aa3ec2` (the in-image manifest carries Stage
B); digest repinned to `sha256:80884d60b496c6f7dddd306390acb74f3f4b3a
72eca2c6d6fb898dddfb3f149a` (jobdef `:8`); `manifest.json` uploaded to
the campaign S3 prefix; bridge canary submitted —
`fl_je_exp_7d_outbreak`, 20 children, Batch job
`221787d3-d16d-495e-8da8-be62e1407257`.

Remaining: stop and report. Reference fingerprints for the reproduction
arm resolve at readout time from the `noro_supply_solver_screen_01`
archive (`readout.py --reference-root`). Owner: `campaign-preflight`.

## Bridge canary result (2026-11-21)

20/20 children of `fl_je_exp_7d_outbreak` SUCCEEDED
(`221787d3-d16d-495e-8da8-be62e1407257`, jobdef `:8`, image
`sha256:80884d60…f149a`, ENGINE_GIT_SHA `90aa3ec2`).

- [x] Audit clean: 20/20 archives read, no missing/unexpected/duplicated
  seeds, intended inputs resolved, outcomes extractable, attempts
  accounted; `engine_git_sha` = `90aa3ec2` on every archive;
  `python_hash_seed` = 1; expected state resolved (rhythm
  enabled+attached on exp).
- [x] Measured (20-cell canary, outbreak stratum = 20 highest-burden
  contaminated exp seeds): posting rate 1.00 [0.83, 1.00]; reported AR
  median 0.060, max 0.091; 20/20 detected by swab and tank; first
  reporter split 12 passenger / 8 crew. Contrast with the Explorer
  reconstruction's ~5% take-off under `declared_five`: on exp hull at
  the census's highest provisioned burdens, every cell takes.

## Stage B submitted (2026-11-21)

User approved after the canary readout. 43 arrays x 20 = 860 children on
`picard-campaign-queue`, jobdef `picard-noro-paper1-joint-eval-01:8`
(image `sha256:80884d60…f149a`); the canary's 20 cells of
`fl_je_exp_7d_outbreak` complete that block. Batch job ids:

- exp: `e1353fc1` 7d_quiet, `79cc438e` 7d_near, `221787d3` 7d_outbreak
  (canary), `66d49f51` 12d_quiet, `93892a0f` 12d_near, `fb3c5386`
  12d_outbreak, `80dae4af` 21d_quiet, `eef4a27f` 21d_near, `75e8a2c4`
  21d_outbreak, `d1d5252e` eval_uncontaminated, `3fe432ca`
  eval_contaminated
- cls: `742b2691` 7d_quiet, `b0b35743` 7d_near, `f8f5f223` 7d_outbreak,
  `898966e6` 12d_quiet, `6767c633` 12d_near, `4761bd22` 12d_outbreak,
  `462b1a0a` 21d_quiet, `5164b082` 21d_near, `9fbe3c1f` 21d_outbreak,
  `2e27f56b` eval_uncontaminated, `756f9c9e` eval_contaminated
- spr: `95efbf63` 7d_quiet, `95db961c` 7d_near, `f731d4eb` 7d_outbreak,
  `350b3b28` 12d_quiet, `daf1f1f6` 12d_near, `b02fc0c1` 12d_outbreak,
  `d3f85843` 21d_quiet, `eae3058d` 21d_near, `25aeeeb0` 21d_outbreak,
  `bb61a840` eval_uncontaminated, `827da078` eval_contaminated
- meg: `a978715f` 7d_quiet, `46be5cd9` 7d_near, `46a3c17e` 7d_outbreak,
  `3ab5ec56` 12d_quiet, `d25f3213` 12d_near, `59e648ac` 12d_outbreak,
  `5edd38dd` 21d_quiet, `7e6b99df` 21d_near, `806ef5de` 21d_outbreak,
  `88202e7c` eval_uncontaminated, `f6af2454` eval_contaminated

(Ids are the first 8 chars of each Batch job id; full ids are in the
session record.)

## Full readout (2026-11-21)

All 1,696 children SUCCEEDED (~3.5 h wall for Stage B at ~50-child
concurrency). Readout exits 0: **technically complete** — 45/45 tier
cells, 0 audit defects, intended inputs used, outcomes extractable,
attempts accounted, pairs meaningful. `engine_git_sha` verified:
`bf0ec168` on Stage-A archives, `90aa3ec2` on Stage-B archives (the two
declared commits); reference fingerprints resolved from
`noro_supply_solver_screen_01`.

Measured, posting rate (posted/20) by stratum: quiet 0/20 on all four
hulls at all three lengths (240/240 suppression); near exp 3-4/20 and
0/20 elsewhere; outbreak exp 20/20, cls 19/20, spr 11-12/20, meg 7/20.
Strict stratum ordering is verifiable only where near posts — exp,
which is "in" at every length; on cls/spr/meg quiet and near both post
~0 so ordering between them is undetermined by the frozen bands: cls
and spr quiet+outbreak in, near undetermined; meg quiet in only. Hull
states: exp "in", others "undetermined".

Continuation (predeclared, inferred): **justified_defect_fix** — the
reproduction arm does not reproduce: `fl_je_repro_exp_solver01_station_
continuous` compared seed by seed against the
`fl_exp_12d_sens_p06_paxv_station_lots_continuous` reference
fingerprints, 16/16 compared, **0/16 identical**. All 16 reposted
(AR median 0.057) so the cells ran; the joint-eval wiring produces a
different run than the solver-screen wiring on the same seed. Canonical
entry: `docs/ledger/NORO-JE-REPRO-01.md`.

Attribution (2026-11-21, paired-seed replays, measured): engine drift
across the campaign boundary, not a joint-eval wiring defect. The
solver-screen worker at `bf0ec168` reproduces the joint-eval
fingerprint; the engine set reverted to `3500c205` reproduces the
reference. Named causes: `9661da33` (ROOM-AIR-01, ambient openings
enter the room-air ACH map — PoolDeck ~73,400 m3/h becomes a live
removal path) and `63210391` (CONTAM-DUCT-EXCLUDE-01, PoolDeck
exchange_m3h re-solved 73376.0 -> 73493.4). First infection flip at
epoch 43; recording-level additions (`room_air_witness`,
`room_air_map_arm`) and an epoch-74 `total_pathogen_mass` float move
carry no infection effect. Open fix: re-baseline the reference at the
freeze commit or close the continuation as attributed — Benjamin's
call.

Pilots (measured): temporal prefix-identity — quiet 31-38/40 on
exp/spr/cls (17/40 meg), near 0-5/40, outbreak 0/40; truncation_valid
false on every cell. Joint-outcome estimates (288 ep, evaluation
seeds): exp 0.0533 ± 0.0040, cls 0.0278 ± 0.0095, spr 0.0076 ± 0.0074,
meg 0.0 (0 events); Neyman allocation puts all mass on the
contaminated stratum. Readout committed at
`telemetry_buffer/noro_paper1_joint_eval_01/`.

## Next decision

Whether to take the predeclared `justified_defect_fix` continuation:
find why the joint-eval cell diverges from the solver-screen run on the
same seed (16/16 seeds differ, all posted — a systematic, not
seed-specific, divergence).
