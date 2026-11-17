# noro_supply_solver_screen_02

## Scope

Classic + spirit extension of the expedition supply solver screen: `classic_cruise_1900` (`fl_cls_12d_sens_p06_paxv`, 1910 agents) and `spirit_cruise_3000` (`fl_spr_12d_sens_p06_paxv`, 3000 agents), paired `transmission.contamination_solver` `discrete` vs `continuous` on stratified contaminated supply seeds plus quiet controls. Design is frozen in `DESIGN.md`; the frozen seed list is `seed_selection.json`.

## Frozen inputs

- Campaign: `noro_supply_solver_screen_02`
- Manifest: `campaigns/noro/supply_solver_screen_02/manifest.json`
- Cells: 176 runs = 2 hulls x 2 solver arms x 44 seeds. Per hull per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10 contaminated, `declared_receipts` 10 contaminated.
- Seed source: `noro_supply_seed_scan_01` cls/spr JSONL rows (boarding census only).
- Worker: `tools/noro_diag/growth_chain_census.py`, payload `lean`, `PYTHONHASHSEED=1`.
- Queue: `picard-campaign-queue`; resources 1 vCPU / 8192 MB / 512 MB shm.

## Preflight

- [x] Frozen design and seed-selection rule written before cells.
- [x] `seed_selection.json` generated from the cls/spr seed census: cls station 16 / single 10 / declared 10 / quiet 8; spr station 16 / single 10 / declared 10 / quiet 8.
- [x] `scripts/campaign describe noro/supply_solver_screen_02` resolves 16 blocks, array sizes 16+16+10+10+10+10+8+8 per hull (176 total).
- [x] `scripts/campaign submit --dry-run --block <all 16 blocks> --account 994254241749 --bucket crusherbucket-994254241749-us-east-1-an` OK.
- [x] Local 24-epoch smoke, cls `station_lots_continuous` seed 960473: zip members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_cls_12d_sens_p06_paxv_station_lots_continuous`; `continuous_path_calls=15116`.
- [x] Local 24-epoch smoke, spr `station_lots_continuous` seed 1000371: zip members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_spr_12d_sens_p06_paxv_station_lots_continuous`; `continuous_path_calls=24262`.
- [x] Image built and digest pinned in `campaign.json`.
- [x] Manifest uploaded to S3 (`manifest.json`, `seed_selection.json`).
- [x] In-container build check: campaign manifest/seed files present, `ENGINE_GIT_SHA=31bd92c525fb3656af9450f124d54b2c6ced5a54`, cls/spr station tier seed membership verified.
- [ ] Full-length canary per hull.
- [ ] AWS canary child inspected per hull.
- [ ] ETA reported; user approved array.

## AWS Batch pins

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver02@sha256:0dea8f12e65108edb995f65e2ade1392c5568c7c53b9672ba4f91af33694a092`
- `ENGINE_GIT_SHA`: `31bd92c525fb3656af9450f124d54b2c6ced5a54`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_02/`

## Measurements

None yet.
