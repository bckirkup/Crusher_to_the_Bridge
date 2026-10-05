# NORO-AGE-FOOD-01 — campaign ledger

Design of record: `docs/norovirus/noro_age_food_01_sweep_design.md`
(frozen before any array submits). Manifest + specs regenerate from
`design/build.py` — never hand-edit.

## Status

| date | event |
|------|-------|
| 2026-10-05 | Design frozen; manifest (60 tiers / 55,728 cells) + campaign specs built; local smoke `fl_exp_12d_scr_fam_l1` index 0 clean — bundle resolved, fractions stamped, `common_source` fired (4 events / 26 takers), contract files present. |
| 2026-10-05 | Canary submitted at cb0f562153fc and verified. Image `picard-campaign:noro-age-food01` digest `sha256:4a66190ea85fa9a5ff11d9466209cdbcc114b60141fa677dc8754b68a31b1c3c` (root Dockerfile + `Dockerfile.campaign_stack` + `campaigns/` overlay — committed `Dockerfile.campaign` copies nothing, so a literal build yields an image with no `deploy/aws/`, `tools/`, or `campaigns/`; this is the first submit through `campaign_jobdef.json` + `campaign_entrypoint.py`, so the gap had never been exercised). `canary_exp_snr_l1`: 24 children, array `5838ac63-c13a-4b99-9dec-97bd7d80f46f`, jobdef `picard-noro-age-food-01:2`. `canary_exp_fam_l1`: 8 children, array `32ca9b12-a3ff-4d7d-81d6-711e4e0966c5`, jobdef `:3`. All 32 children SUCCEEDED (~4 min on `picard-campaign-queue` Spot); zips at `campaign/noro_age_food_01/{canary_exp_snr_l1,canary_exp_fam_l1}/`, manifest at `campaign/noro_age_food_01/manifest.json`. All 32 zips: 3-member contract (`summary.json`, `growth_census.json.gz`, `rss_samples.json`), non-degenerate voyages (snr 12–52, fam 20–46 cumulative ever-infected), `common_source.lot_event_probability` = [0.001, 0.0075] both arms. fam 8/8: bundle `family_cruise_u18.json`, `agent_class_fractions.passenger_family` = 0.25. snr 24/24: bundle `senior_cruise_dp2020.json`; `agent_class_fractions` NOT stamped — `_fill_demographic_params` only echoes a tier-declared `ship_graph.agent_classes` override and snr runs the base mix; resolved-spec materialization confirms `passenger_family` = 0.10 (`crusher_labs/config.yaml`). Echo gap only, arm verified correct. |

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
