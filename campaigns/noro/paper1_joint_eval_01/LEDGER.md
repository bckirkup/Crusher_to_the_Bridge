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
- [x] `tests/test_paper1_joint_eval_campaign.py`: 25 passed.

Not exercised locally: a posted voyage, a detected swab, a crew onset, and
any run longer than 96 epochs.

## Findings recorded during authoring

- Initialised role counts differ from the platforms' declared nominal split
  on three hulls (exp 316/134 vs 300/150; cls 1,338/572 vs 1,350/560; meg
  4,900/2,100 vs 5,000/2,000; spr equal). Measured at initialise on two
  seeds per hull. The campaign asserts the initialised counts; changing
  them is a baseline-block decision for WP1.
- Compact retention drops the swab and holding-tank results from the epoch
  record; the worker reads them through the read-only observer hook.
- The census row keys `provisioned_source` by pathogen id; the selection
  rule reads `provisioned_source[norwalk_gi].n_contaminated`.

## Gated (not run)

Declared freeze, then: census canary and array; `build.py --select` and
rebuild; reference fingerprints for the reproduction arm from the
`noro_supply_solver_screen_01` archive (`readout.py --reference-root`);
image build with digest pin (the image must contain this directory);
manifest upload; canary of 20 seeds at one bridge cell, then stop and
report. Owner: `campaign-preflight`.

## Next decision

Whether to declare the freeze as proposed or first change the baseline
block's class mix so role counts match declared nominal.
