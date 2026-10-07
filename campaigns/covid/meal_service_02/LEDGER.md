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
- [ ] `--dry-run` count == 200
- [ ] image `covid-meal-svc-02` built at merged implementation SHA,
      digest-pinned (record `sha256:` + build SHA here)
- [ ] jobdef `picard-covid-meal-svc-02` registered (record revision)
- [ ] manifest in S3 under `campaign/covid_meal_service_02/`
- [ ] canary `zone_narrow_svc_dir_cf_lo` (20 seeds) read out, reported,
      and STOP before the array

## Canaries / runs

_(fill in at run time — job ID, image digest, design SHA, verdict)_

## Verdict

_(fill in at readout — MAGNITUDE-LANDED / OVER-ATTENUATED / STILL-HIGH /
NONLINEAR-BREAK per the frozen grammar; record the landing arm and the
single open decision for the next stage)_
