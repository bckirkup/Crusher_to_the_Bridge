# NORO-AGE-FOOD-01 — campaign ledger

Design of record: `docs/norovirus/noro_age_food_01_sweep_design.md`
(frozen before any array submits). Manifest + specs regenerate from
`design/build.py` — never hand-edit.

## Status

| date | event |
|------|-------|
| 2026-10-05 | Design frozen; manifest (60 tiers / 55,728 cells) + campaign specs built; local smoke `fl_exp_12d_scr_fam_l1` index 0 clean — bundle resolved, fractions stamped, `common_source` fired (4 events / 26 takers), contract files present. |

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
