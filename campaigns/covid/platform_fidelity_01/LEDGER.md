# LEDGER — covid_platform_fidelity_01

Campaign mechanics for PLATFORM-FIDELITY-01: the paired hull-fidelity
contrast on the two frozen 2020 COVID event replays. Frozen design:
`picard_framework/runs/covid_platform_fidelity_{dp,gm}_design.json`;
pre-registration (criterion of record):
`docs/covid/covid_platform_fidelity_prereg_v1.md`. Settled design source:
`docs/covid/covid_platform_fidelity_handoff_2026_11_07.md` §8.

## 1. Spec

| Field | Value |
|---|---|
| Queue | `picard-analysis-queue` |
| Jobdef | `picard-covid-platform-fidelity-01` |
| Image tag | `covid-platform-fidelity-01` |
| S3 prefix | `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/` |
| Resources | 1 vCPU / 2048 MB |
| Designs | `picard_framework/runs/covid_platform_fidelity_{dp,gm}_design.json` |
| Protocols files | `data/config/protocols_covid_pf_{dp,gm}.json` (frozen per-event-pair) |

## 2. Blocks

`{design, theta, arm_id}` cells resolved inside the design JSONs' enumeration
— `entry.py` translates (block args, seed) into the cell worker argv; DP
blocks take the default DP design, GM blocks pass `args.design`.

| Block | Design | Θ | Arm | Seeds | Role |
|---|---|---|---|---|---|
| `dp_t7e6_proxy` | dp | 7.9e6 | proxy_mega_cruise | 20200205–224 (20) | CANARY (proxy) |
| `dp_t7e6_dedicated` | dp | 7.9e6 | dedicated_diamond_princess | 20200205–224 (20) | CANARY (dedicated) |
| `gm_t7e6_proxy` / `gm_t7e6_dedicated` | gm | 7.9e6 | proxy_expedition_cruise / dedicated_greg_mortimer | 20 | GM primary row |
| `gm_t1e11_*` | gm | 1e11 | both arms | 20 | descriptive lattice |
| `gm_t2p37e11_*` | gm | 2.37e11 | both arms | 20 | descriptive (anchor + lattice) |
| `gm_t1e12_*` | gm | 1e12 | both arms | 20 | descriptive lattice |

Total: 200 cells (40 DP canary + 160 GM). Canary = the two DP blocks (40
executions = 20 seeds × 2 platforms at one arm-row). GM blocks run only
after the DP machinery is proven and the owner approves; GM canary is
technical acceptance only, Θ frozen before any GM epidemiological output is
examined.

## 3. Bring-up repairs (data consistency, declared in prereg §8)

Two disabled worked-example blocks on
`data/platforms/diamond_princess/voyage_config.json` were referentially
invalid and crashed spec resolution before any cell ran:

- `hazard_sources.penetrations[0].zones` named `Promenade`/`LidoBuffet`
  (absent from the hull layout) → repointed to `PromGalleria`/
  `HorizonTerrace`. Block stays `enabled: false`.
- `ship_functions.functions` (6 entries, `enabled: false`) staffed classes
  the DP scenario's `agent_classes` does not declare (`crew_galley`,
  `crew_engineering`, `crew_medical`) → functions list emptied. Behaviorally
  identical (capacity runner `None` either way; sibling replay hulls carry
  no `ship_functions` block).

Neither touches an epidemiological constant.

## 4. Local smoke (2026-11-07, dev venv)

- GM `dedicated_greg_mortimer` θ7.9e6 seed 20200205, full 672-epoch voyage:
  PASS — resolved `greg_mortimer` vs declared `expedition_cruise_450`;
  `SOP-017` fired (window [8,27], activation epoch 192); no `close_zones`;
  aboard 223; 7 input hashes echoed.
- DP `dedicated_diamond_princess` θ7.9e6 seed 20200205, 400-epoch cap
  (covers the day-16 boxed-meal window): PASS — resolved `diamond_princess`
  vs declared `mega_cruise_5000`; `SOP-017-MESSBOX` fired (window [16,30]);
  `crew_meal_service.mode=boxed` active_epochs 16, diner_redirects 33;
  no `close_zones`; aboard 3711; 8 input hashes echoed (incl. agent profile
  bundle). ~3m51s for 400 epochs → full 840-epoch DP cell ≈ 8 min.

## 5. Image

| Field | Value |
|---|---|
| Tag | `covid-platform-fidelity-01` |
| Digest | `sha256:cd59519ab17135252fe13519fac37ad465c5dbb825a80a25c55bcbe0882dd346` |
| Built from | `bba29d19` (root `Dockerfile` + `deploy/aws/Dockerfile.campaign` overlay, both stamped `ENGINE_GIT_SHA=bba29d19`) |
| Preflight | ENTRYPOINT `["python3"]`; `deploy/aws/`, `tools/`, `campaigns/` layout present; designs + frozen protocols files + repaired `diamond_princess/voyage_config.json` inside; one full `campaign_entrypoint.py --local` GM proxy voyage wrote `cell_20200205.json` |

## 6. Runs

| Date | Block | Seeds | Cells | Job | SHA | Digest | Jobdef rev | Wall | Result |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-08 | `dp_t7e6_proxy` | 20200205–224 | 20 | `6a7e6185-951b-4bfb-987c-4eeb23f48554` | `bba29d19` | `sha256:cd59519a…` | `:1` | — | RUNNING (canary) |
| 2026-11-08 | `dp_t7e6_dedicated` | 20200205–224 | 20 | `4e914d4d-2bdf-4fd5-9c8e-178bb772b2b2` | `bba29d19` | `sha256:cd59519a…` | `:2` | — | RUNNING (canary) |

Canary = the DP pair only (40 executions). GM blocks (`gm_*`, 160 cells) are
NOT submitted — they await owner approval after the DP canary is read out,
and the GM canary is technical acceptance only with Θ frozen before any GM
epidemiological output is examined.
