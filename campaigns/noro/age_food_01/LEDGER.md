# NORO-AGE-FOOD-01 — campaign ledger

Design of record: `docs/norovirus/noro_age_food_01_sweep_design.md`
(frozen before any array submits). Manifest + specs regenerate from
`design/build.py` — never hand-edit.

## Status

| date | event |
|------|-------|
| 2026-10-05 | Design frozen; manifest (60 tiers / 55,728 cells) + campaign specs built; local smoke `fl_exp_12d_scr_fam_l1` index 0 clean — bundle resolved, fractions stamped, `common_source` fired (4 events / 26 takers), contract files present. |
| 2026-10-05 | Canary submitted at cb0f562153fc and verified. Image `picard-campaign:noro-age-food01` digest `sha256:4a66190ea85fa9a5ff11d9466209cdbcc114b60141fa677dc8754b68a31b1c3c` (root Dockerfile + `Dockerfile.campaign_stack` + `campaigns/` overlay — committed `Dockerfile.campaign` copies nothing, so a literal build yields an image with no `deploy/aws/`, `tools/`, or `campaigns/`; this is the first submit through `campaign_jobdef.json` + `campaign_entrypoint.py`, so the gap had never been exercised). `canary_exp_snr_l1`: 24 children, array `5838ac63-c13a-4b99-9dec-97bd7d80f46f`, jobdef `picard-noro-age-food-01:2`. `canary_exp_fam_l1`: 8 children, array `32ca9b12-a3ff-4d7d-81d6-711e4e0966c5`, jobdef `:3`. All 32 children SUCCEEDED (~4 min on `picard-campaign-queue` Spot); zips at `campaign/noro_age_food_01/{canary_exp_snr_l1,canary_exp_fam_l1}/`, manifest at `campaign/noro_age_food_01/manifest.json`. All 32 zips: 3-member contract (`summary.json`, `growth_census.json.gz`, `rss_samples.json`), non-degenerate voyages (snr 12–52, fam 20–46 cumulative ever-infected), `common_source.lot_event_probability` = [0.001, 0.0075] both arms. fam 8/8: bundle `family_cruise_u18.json`, `agent_class_fractions.passenger_family` = 0.25. snr 24/24: bundle `senior_cruise_dp2020.json`; `agent_class_fractions` NOT stamped — `_fill_demographic_params` only echoes a tier-declared `ship_graph.agent_classes` override and snr runs the base mix; resolved-spec materialization confirms `passenger_family` = 0.10 (`crusher_labs/config.yaml`). Echo gap only, arm verified correct. |
| 2026-10-05 | Canary fixes (canary-fixes PR): `Dockerfile.campaign` now COPYs `deploy/aws/` + `tools/` + `campaigns/` — literal `docker build -f deploy/aws/Dockerfile.campaign .` verified in-container (layout, `ENGINE_GIT_SHA`, seed→index, full `--local` snr voyage produced its zip). `design/build.py` declares the shipped `agent_classes` verbatim on gen/snr so `agent_class_fractions` stamps on every arm — resolved config identical, voyages bit-identical to the canary. |
| 2026-10-05 | WAVE 1 (exp+cls, 36 blocks × 1000 seeds) submitted at 9ab260d92229. Image `picard-campaign:noro-age-food01` + `noro-age-food01-mega`, digest `sha256:112247d3d7586b923a40e89cbf90f9e64c79301e98c24fc2d34f085d6a76fad5` (literal `Dockerfile.campaign` build, in-container verified). Jobdef `picard-noro-age-food-01` revs :4–:39 (one per submit, all pinning the tag). exp arrays: gen_off 850a41f8, gen_l1 3eb8918e, gen_l2 a33f9520, gen_ship 94b45a96, gen_p05 611ec963, gen_p20 b7f8eb5d, snr_off 42e22375, snr_l1 56d25653, snr_l2 0a7ad05d, snr_ship b1280205, snr_p05 2872c40a, snr_p20 909322b9, fam_off 5049a524, fam_l1 d6f110dc, fam_l2 d4ec6d62, fam_ship cca7762a, fam_p05 c905ccbc, fam_p20 f55855fe. cls arrays: gen_off 03459838, gen_l1 d1e829d8, gen_l2 2d3b549c, gen_ship ee33aa73, gen_p05 925d21b7, gen_p20 45316bba, snr_off c18868e6, snr_l1 a6c08add, snr_l2 fdbd3fe8, snr_ship 50847f65, snr_p05 230c0c0d, snr_p20 1a10fac9, fam_off 835d3bc2, fam_l1 642800d8, fam_l2 2731a1cb, fam_ship ac877d83, fam_p05 449ad357, fam_p20 0361b814. Health ~28 min in: 1837 SUCCEEDED / 109 RUNNING / 34,015 RUNNABLE / 39 FAILED — every FAILED child is a Spot reclaim ("Host EC2 terminated"); zero materialization/app failures; the jobdef template carries no retryStrategy so reclaim-killed cells stay missing until backfill — recovery = resubmit the affected blocks post-drain (`_already_uploaded` dedup skips landed cells, reruns only missing seeds). ~66 cells/min → ETA ~8–9 h. Early zips landing under `campaign/noro_age_food_01/fl_exp_*/`. |
| 2026-10-06 | WAVE 2 (spr, 18 blocks × 1000 seeds = 18,000 voyages) submitted at 2df542ff34d0. Same image as wave 1 — `picard-campaign:noro-age-food01`, digest `sha256:112247d3d7586b923a40e89cbf90f9e64c79301e98c24fc2d34f085d6a76fad5` (built at 9ab260d92229; spec/manifest unchanged since). Jobdef `picard-noro-age-food-01` revs :40–:57 — the first registrations carrying the `retryStrategy` (attempts 10, `Host EC2*`) merged in #918, so Spot reclaims now self-heal. spr arrays: gen_off 04bcad8a, gen_l1 1b6b74a2, gen_l2 f933e5dc, gen_ship 25c52297, gen_p05 8b05a9a4, gen_p20 aa7697f7, snr_off 54cf2130, snr_l1 67a6cfce, snr_l2 53013538, snr_ship 32909f85, snr_p05 ea5d9d04, snr_p20 c6d1c61f, fam_off c105e343, fam_l1 9c2c4aea, fam_l2 fc180b86, fam_ship d290999e, fam_p05 13923b34, fam_p20 034dd859. Health ~70 min in: 663 SUCCEEDED / 118 RUNNING / 17,219 RUNNABLE / 0 FAILED — zero materialization/app failures; blocks drain FIFO (~4× classic cost, ~12 min/cell at ~118 slots). Zips landing under `campaign/noro_age_food_01/fl_spr_*/` (~85 MB each, `spirit_cruise_3000` rung). |
| 2026-10-06 | WAVE 1 BACKFILL (214 reclaim-missing seeds across 14 blocks) submitted at ff4bae97 with filtered `--seeds` argv — same campaign dir/block names in-container, only the seed list narrowed (committed `campaign.json` untouched). Same image digest `sha256:112247d3`. Jobdef `picard-noro-age-food-01` revs :58–:71 (retryStrategy×10). Pre-submit checks: every requested seed ∈ its committed block list; zero collisions with landed zips; each block's landed+missing = exactly 1000. Arrays: exp gen_off a84d6c73 (n=18), gen_l1 a98bb306 (20), snr_l1 1717d576 (6), snr_l2 8a9f48c7 (4), snr_ship 93f966e9 (10), fam_p05 6cbea6c8 (13); cls gen_off f63ce3ce (7), gen_l1 28f68c01 (14), gen_l2 bd6b35c8 (7), gen_ship c0f73512 (52), snr_p05 062f6d2c (15), fam_l2 3a013fdb (33), fam_p20 84ff1d68 (14). `fl_cls_12d_scr_fam_l1` (n=1) submitted as a single indexed job `78af3c1c` on rev :69 (Batch arrays require size >1). Health ~15 min in: all 214 children RUNNABLE behind wave-2 spr (FIFO); first zips land under the same `campaign/noro_age_food_01/<block>/` dirs as wave 1 once the queue drains. |

## Grid

- 3 age arms `gen` / `snr` / `fam` (bundles under
  `data/scenarios/agent_profiles/`) × lot rungs `off` / `l1` / `l2` /
  `ship` + posture arms `p05` / `p20` (coupled, at l1).
- Blocks = tier ids: 18 exp + 18 cls + 18 spr + canaries
  (`canary_exp_snr_l1` ×24, `canary_exp_fam_l1` ×8). Mega cells live in
  `campaigns/noro/age_food_01_mega/` (6144 MB).
- S3 prefix `campaign/noro_age_food_01/`; image tag `noro-age-food01`
  (needs a build at the merged SHA — `campaign_runner` now stamps
  `common_source` / `agent_profile_bundle` / `agent_class_fractions`).

## Waves (stop order)

canary → STOP → user decides → wave 1 exp+cls → wave 2 spr → wave 3 mega
(independent `noro_age_food_01_mega` spec).

## Findings

(none yet — fleet has not run)
