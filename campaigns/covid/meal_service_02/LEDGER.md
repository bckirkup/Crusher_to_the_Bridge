# MEAL-SVC-02 ledger — `contact_factor_to_host` door-drop attenuation sweep

Status: **declared** — implementation + design frozen and merged; Batch
execution pending (handed to the next session per owner direction).

- Design doc: `docs/covid/covid_meal_service_02_design.md` (frozen pre-run)
- Design JSON: `picard_framework/runs/covid_meal_service_02_design.json`
  (10 arms × 20 seeds = 200 cells, Θ7.9e6, verbatim CW-02 replay contract)
- Skeleton (contract): `docs/covid/covid_meal_service_02_design_skeleton.md`
- Parent design: `covid-crew-window-02` (`2df542ff`); supersedes
  `covid-meal-svc-01` (canary at `32b11ccf`, CHANNEL-FOUND / ~15× high)

## Registration

| item | value |
|---|---|
| campaign dir | `campaigns/covid/meal_service_02/` |
| blocks | 10 (one per arm) × 20 seeds |
| jobdef | `picard-covid-meal-svc-02` |
| image tag | `covid-meal-svc-02` (pinned digest at the merged impl SHA) |
| S3 prefix | `campaign/covid_meal_service_02/` |
| queue | `picard-analysis-queue` (On-Demand; Fargate fallback `picard-analysis-fargate-queue`) |
| resources | 1 vCPU / 2048 MB per cell |
| readout | `campaigns/covid/meal_service_02/readout.py` |

## Preflight checklist (campaign-preflight gate)

- [x] design doc + design JSON frozen before any cell ran
- [x] local smoke: armed scalar/interval host factor scales the host-side
      dose exactly and leaves the steward side on the shared draw;
      OFF credits zero; absent echoes the shipped tuple as `shared`;
      malformed values fail at spec-lands
      (`tests/test_caregiver_mechanism.py::TestMealSvc02`, 7 tests)
- [x] `--dry-run` count == 200 (10 blocks × 20; rendered
      `deploy/aws/jobdef_picard-covid-meal-service-02.rendered.json`)
- [x] local `run_cell` capped-voyage smoke (40 epochs, arm
      `zone_narrow_svc_dir_cf_lo`): host factor resolves `declared`,
      `service_host_factor_draws.n == service_deliveries`
- [x] image `covid-meal-svc-02` built at merged implementation SHA,
      digest-pinned (see Canaries / runs)
- [x] jobdef `picard-covid-meal-service-02` registered (see Canaries /
      runs for revisions incl. the Fargate variant)
- [x] manifest in S3 under `campaign/covid_meal_service_02/`
      (campaign.json + design json/md)
- [x] canary `zone_narrow_svc_dir_cf_lo` (20 seeds) read out, reported,
      and STOP before the array

## Canaries / runs

| run | detail |
|---|---|
| image | `covid-meal-svc-02` @ `54086e4ca8e6d9af301b7249707fdab10437b38f` → ECR `sha256:300b643733bb796de700077e0ea31535117f62d72053eac3a46193b343150696` |
| jobdefs | `picard-covid-meal-service-02:1` (manual digest-pinned), `:2` (submit path, tag→same digest); `picard-covid-meal-service-02-fargate:1` (Fargate variant — `linuxParameters` stripped, `platformCapabilities: [FARGATE]`, `assignPublicIp`, `platformVersion: LATEST`, 10800s timeout) |
| queue note | `picard-analysis-queue` (EC2 on-demand) was flooded by ~3,020 RUNNABLE children (noro `defpair` arrays + flu-reassess canary) with zero running capacity at submit time → canary executed on `picard-analysis-fargate-queue` per the fallback named above; the stranded EC2 single cell (`5c0eb397`) left queued as a dedup'd no-op |
| canary single | `405fdeff-314e-40c9-9bf3-f15a0ee6848b` (Fargate) — `zone_narrow_svc_dir_cf_lo` seed 20200205, SUCCEEDED ~22 min; contract verified (deliveries 170,141 == host-factor draws n; mode `declared` [0.005,0.02]) |
| canary block | `87ea79e5-44ad-4444-bf26-51fec3618279` — 20-cell array on `picard-analysis-fargate-queue`, 20/20 SUCCEEDED 2026-10-07 ~11:10–11:49Z |
| canary verdict | **STILL-HIGH** — confined-pax med 289 (>200; band [26,160]), during med 686, crew share 0.536 (record 0.29), deliveries 166,113 parity; 0 audit violations after the crew_window `service_`-prefix readout fix. Factor→~0.0125 moved the median 804→289 (~2.8×), not the naive ~14× linear |
| stop | HELD per gate — remaining 9 blocks (180 cells) await owner call |

## Verdict

_(fill in at readout — MAGNITUDE-LANDED / OVER-ATTENUATED / STILL-HIGH /
NONLINEAR-BREAK per the frozen grammar; record the landing arm and the
single open decision for the next stage)_
