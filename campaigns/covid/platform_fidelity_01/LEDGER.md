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
| 2026-11-08 | `dp_t7e6_proxy` | 20200205–224 | 20 | `6a7e6185-951b-4bfb-987c-4eeb23f48554` | `bba29d19` | `sha256:cd59519a…` | `:1` | ~22 min | SUCCEEDED 20/20 |
| 2026-11-08 | `dp_t7e6_dedicated` | 20200205–224 | 20 | `4e914d4d-2bdf-4fd5-9c8e-178bb772b2b2` | `bba29d19` | `sha256:cd59519a…` | `:2` | ~22 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t7e6_proxy` | 20200205–224 | 20 | `533758d0-c7b7-4a11-97d5-f9980e1afaba` | `bba29d19` | `sha256:cd59519a…` | `:3` | ~8 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t7e6_dedicated` | 20200205–224 | 20 | `84caa2e3-43ed-4340-9407-67bc644d4015` | `bba29d19` | `sha256:cd59519a…` | `:4` | ~8 min | SUCCEEDED 20/20 |

| 2026-11-08 | `gm_t1e11_proxy` | 20200205–224 | 20 | `d8d4cbb7-57f3-4f27-a3ce-1ffb3466f3c9` | `bba29d19` | `sha256:cd59519a…` | `:5` | ~6 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t1e11_dedicated` | 20200205–224 | 20 | `411dc224-e945-4169-b966-be6ce202ff39` | `bba29d19` | `sha256:cd59519a…` | `:6` | ~6 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t2p37e11_proxy` | 20200205–224 | 20 | `a1aecf18-c51c-4b8d-95e1-eb5a10ef8d79` | `bba29d19` | `sha256:cd59519a…` | `:7` | ~6 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t2p37e11_dedicated` | 20200205–224 | 20 | `8bcc7cc2-87f4-4987-8526-407166738daf` | `bba29d19` | `sha256:cd59519a…` | `:8` | ~6 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t1e12_proxy` | 20200205–224 | 20 | `7ce2d5d3-eef7-4aa1-9b1a-efb1c655e699` | `bba29d19` | `sha256:cd59519a…` | `:9` | ~6 min | SUCCEEDED 20/20 |
| 2026-11-08 | `gm_t1e12_dedicated` | 20200205–224 | 20 | `41308e2f-dc55-4d2e-9413-16d21d5473c8` | `bba29d19` | `sha256:cd59519a…` | `:10` | ~6 min | SUCCEEDED 20/20 |

Canary = both event pairs' Θ=7.9e6 arm-rows (80 executions). The full array
(the 120 descriptive GM cells above) was submitted after the canary readout
and owner approval ("go ahead", 2026-11-08). Campaign COMPLETE: 200/200
cells, 0 technical failures. Canonical readout:
`docs/covid/covid_platform_fidelity_readout.md`; ledger entry:
`docs/ledger/PLATFORM-FIDELITY-01.md`.

## 7. Canary readout (2026-11-08, 80/80 cells, audit clean)

Audit: 0 failed comparisons (no `close_zones` fired anywhere), 0 missing
platform echoes, 0 missing/unexpected cells vs the design enumeration,
technical failure rate 0.0 (stop rule not breached). Every cell echoes
resolved `platform_id`, fired protocol ids, and 7–8 input SHA-256 hashes.

**DP row (Θ=7.9e6, 20 seeds/arm — the training-hull measurement):**

| Metric | proxy (`mega_cruise_5000`) | dedicated (`diamond_princess`) |
|---|---|---|
| P(takeoff) (recorded_onsets ≥ 10) | 0.50 (10/20) | 0.35 (7/20) |
| Takeoff-conditional median recorded_onsets | 64 | 243 |
| Takeoff-conditional asymptomatic share | 0.3665 | 0.4517 |

- Paired hull delta (dedicated − proxy), both-takeoff seeds only (n=6):
  median **+130**, q05–q95 **[−44.75, +297.5]** — the interval includes
  zero, so the prereg's report-immediately trigger does NOT fire.
- CRN diagnostic: Pearson ρ = 0.0124 on recorded_onsets across arms →
  ρ < 0.3, so the **unpaired analysis is declared** per prereg §4; the
  paired delta above is the small-n both-takeoff subset, not the primary
  read.
- MDE reference: 30% of the proxy takeoff-conditional median = 19.2
  onsets; the point estimate (+130) exceeds it but the interval does not
  exclude zero at n=6 — underpowered at this seed count, exactly what the
  full-array decision is for.

**GM row (Θ=7.9e6):** technical acceptance PASSED — 40/40 cells succeeded,
both arms resolved their hulls (`expedition_cruise_450` proxy,
`greg_mortimer` dedicated), SOP-017 fired, no `close_zones`, no technical
failures. Per prereg §6 the GM epidemiological outputs are NOT examined at
canary stage; they are in the cell payloads under the S3 prefix for the
owner's decision.

Cell payloads: `s3://crusherbucket-994254241749-us-east-1-an/campaign/
covid_platform_fidelity_01/{dp,gm}_t7e6_{proxy,dedicated}/cell_<seed>.json`.
Readout: `python3 campaigns/covid/platform_fidelity_01/readout.py --prefix
s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/`.
