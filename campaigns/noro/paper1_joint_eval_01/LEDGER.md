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

## Next decision

Whether to run the 880 Stage-B children (bridge 720 + pilot 160) after
the bridge canary reports clean.
