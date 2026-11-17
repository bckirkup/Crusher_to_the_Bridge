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
- [x] Image built and digest pinned in `campaign.json`.
- [x] Manifest uploaded to S3 (`manifest.json`, `seed_selection.json`).
- [x] In-container build check: canary zip has expected members, `parameters.engine_git_sha=db899fd375b1c59585edab2d57864b46f4f7e60d`, `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`, `num_agents=7000`, and seed 1020931 resolved in the station_lots_continuous tier.
- [x] Full-length canary.
- [x] AWS canary child inspected.
- [x] ETA reported.
- [x] User approved array ("Go ahead").

## AWS Batch pins

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver03@sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a`
- `ENGINE_GIT_SHA`: `db899fd375b1c59585edab2d57864b46f4f7e60d`
- Queue: `picard-campaign-queue`
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/`

## Canaries

- meg `station_lots_continuous` index 0: Batch job `7d205140-f72c-42ae-834a-bc29be879d89`, jobdef `picard-noro-supply-solver-screen-03:1`, image digest `sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a`. Wall 1805 s. Zip `fl_norovirus_mega_cruise_5000_dose7p57_rung-shipped_nsf29_bp25c30_n7000_ep288_syndromic_comp65_s1020931.zip` (132,443,423 bytes); members `summary.json`, `growth_census.json.gz`, `rss_samples.json`; `parameters.tier_id=fl_meg_12d_sens_p06_paxv_station_lots_continuous`; `engine_git_sha=db899fd375b1c59585edab2d57864b46f4f7e60d`; `hand_occupancy.counters.continuous_path_calls=361620`; derived attack_rate 0.0821, passenger reported-case AR 0.0445, crew reported-case AR 0.0148, `vsp_trigger_epoch=75`; `mechanisms.common_source_events=511`, `common_source_takers=15984`, provisioned_source `n_contaminated=3`.

ETA basis: 88 cells; canary wall 1805 s (30.1 min) for the continuous station_lots cell. Using ~44.1 vCPU-hours total and the campaign compute environment (`picard-abm-campaign-spot`, max 256 vCPU, desired 32), expect roughly 1.5-2.5 h depending on Spot concurrency; array submission is held for user approval.

## Array

- User approved array submission ("Go ahead") after canary/preflight.
- Submitted 2026-11-17 to `picard-campaign-queue`; 88 cells total.
- `meg_station_lots_discrete`: `ddbdf74a-720d-4ca5-b630-06200f1fecf9` (16)
- `meg_station_lots_continuous`: `7e5ee99d-3a29-4aa5-a77b-48be4c1ea0fb` (16)
- `meg_single_line_receipt_discrete`: `e1af6706-a967-46ea-b9f8-4af3ddca8324` (10)
- `meg_single_line_receipt_continuous`: `9d358cfb-c4c9-482f-b53a-e42970d934ed` (10)
- `meg_declared_receipts_discrete`: `22483232-afbd-458f-8467-f04146894412` (10)
- `meg_declared_receipts_continuous`: `b8a62505-6a9f-4a16-9f35-95fdc6d1a727` (10)
- `meg_quiet_station_lots_discrete`: `c4e23469-56dd-49a3-b15f-2e4fbd72a68f` (8)
- `meg_quiet_station_lots_continuous`: `7f313ce4-08db-4442-8c1f-8ffef9036aaf` (8)

## Measurements

pending
