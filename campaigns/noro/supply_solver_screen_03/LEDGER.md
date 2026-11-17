# noro_supply_solver_screen_03

## Scope

Mega extension of the supply solver screen: `mega_cruise_5000` (`fl_meg_12d_sens_p06_paxv`, 7000 agents), paired `transmission.contamination_solver` `discrete` vs `continuous` on stratified contaminated supply seeds plus quiet controls. Design is frozen in `DESIGN.md`; the frozen seed list is `seed_selection.json`.

## Frozen inputs

- Campaign: `noro_supply_solver_screen_03`
- Manifest: `campaigns/noro/supply_solver_screen_03/manifest.json`
- Cells: 88 runs = 1 hull x 2 solver arms x 44 seeds. Per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10 contaminated, `declared_receipts` 10 contaminated.
- Seed source: `noro_supply_seed_scan_01` mega JSONL rows (boarding census only).
- Worker: `tools/noro_diag/growth_chain_census.py`, payload `lean`, `PYTHONHASHSEED=1`.
- Queue: `picard-campaign-queue`; resources 1 vCPU / 8192 MB / 512 MB shm.

## Preflight

- [x] Frozen design and seed-selection rule written before cells.
- [x] `seed_selection.json` generated from the mega seed census: station 16 / single 10 / declared 10 / quiet 8.
- [x] `scripts/campaign describe noro/supply_solver_screen_03` resolves 8 blocks, array sizes 16+16+10+10+10+10+8+8 (88 total).
- [x] `scripts/campaign submit --dry-run --block <all 8 blocks> --account 994254241749 --bucket crusherbucket-994254241749-us-east-1-an` OK.
- [x] Local 24-epoch smoke, mega `station_lots_continuous` tier index 0 seed 1020931: zip members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`; `num_agents=7000`; `payload_profile=lean`; `hand_occupancy.counters.continuous_path_calls=50750`; `common_source.provisioned_source.n_contaminated=3`; `common_source.telemetry.events_provisioned_lot=28`, `takers_served=2126`; derived attack_rate 0.0521, passenger reported-case AR 0.0, crew reported-case AR 0.0005, `vsp_trigger_epoch=None` (24-epoch smoke).
- [ ] Image built and digest pinned in `campaign.json`.
- [ ] Manifest uploaded to S3 (`manifest.json`, `seed_selection.json`).
- [ ] In-container build check: campaign manifest/seed files present, `ENGINE_GIT_SHA=<commit>`, mega station tier seed membership verified.
- [ ] Full-length canary.
- [ ] AWS canary child inspected.
- [ ] ETA reported.
- [ ] User approved array.

## AWS Batch pins

- Image: pending
- `ENGINE_GIT_SHA`: pending
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/`

## Canaries

- pending

ETA basis: 88 cells; canary wall time pending. Array submission is held for user approval.

## Measurements

pending
