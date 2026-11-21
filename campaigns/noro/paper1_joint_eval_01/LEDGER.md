# noro_paper1_joint_eval_01

Paper-1 WP2 joint four-hull evaluation. Status: **authored and gated** — no
array, canary or census cell has run. The WP1 freeze is proposed, not
declared; every Batch stage waits for the declaration.

## Frozen inputs

- Design: `DESIGN.md` (strata, seed rule, criteria) — fixed before the smoke.
- Builder: `design/build.py`; `--check` reproduces `manifest.json` and
  `campaign.json`.
- Block: freeze contract section 2, carried verbatim as every `fl_je_*` tier's
  `config_overrides`; sha256 (sorted, compact JSON)
  `699263985ba90b81e78b9ce68a1f29562ac606ec5cd97fce38c466cead3d6aae`, 80 leaves.
- Worker `cell.py`, hook `entry.py` (`PYTHONHASHSEED=1`), readout `readout.py`.

## Counts

- Stage A (emitted): census 4 hulls x 200 chunks x 100 seeds = 800 children
  (80,000 one-epoch seeds); tail 4 x 1,000 = 4,000; baseline 16. Total 4,816.
- Stage B (emitted once `design/seed_selection.json` exists): 36 tiers =
  4 hulls x 3 lengths x 3 strata; 420 seeds per hull x length; 5,040 runs.

## Local gates (authoring)

- [x] Criteria and selection rule committed before any run.
- [x] `design/build.py --check`: build reproduces.
- [x] `scripts/campaign describe`: 9 blocks, 4,816 children = Stage A count.
- [x] Local 24-epoch smoke, `fl_je_exp_12d_tail` index 0, seed 2400000,
  commit `9aacfe37`: members `summary.json`, `joint_eval.json.gz`;
  `config_echo.n_leaves=80`, `mismatched=[]` (engine-resolved `sim.cfg`
  equals the block on every leaf); `parameters.tier_id` and
  `engine_git_sha` present; 1,128 swabs and 24 holding-tank assays observed.
  Measured on one seed. The line list was armed but held 0 cases in 24
  epochs, so the onset curve is wired but not exercised by this smoke.
- [ ] Remaining gates: see the PR / later entries in this file.

## Gated (not run)

Census, image build and digest pin, manifest upload, canary (>= 20 seeds at
one cell), array. Owner: `campaign-preflight`, after the declared freeze.
