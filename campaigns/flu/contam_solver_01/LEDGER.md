# FLU-CONTAM-SOLVER-01 — Campaign Ledger

> **Design:** `campaigns/flu/contam_solver_01/DESIGN.md`
> **Branch / Commit:** `devin/1795263522-flu-contam-solver-01` (worker commit `77235441f62e3a87e3ec6e45164fbfbec3d82879`)
> **Canary Readout Artifacts:** `campaigns/flu/contam_solver_01/readout_canary/` (`report.md`, `summary.json`, `paired_cells.csv`, `daily_dynamics.csv`)

## Status

- **Stage:** 20-seed paired canary (`expedition_cruise_450`) **complete and read out**. Stopped for user decision before submitting the remaining 6 current cruise hulls.
- **Roster (draft, historic naval vessels excluded):** 7 commissioned current cruise platforms (`greg_mortimer`, `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, `diamond_princess`, `explorer_seas_06`, `mega_cruise_5000`). Uncommissioned directories `expedition_cruise_300` and `messy_cruise_500` (no `contam/` bundle, no `voyage_config.json`) excluded.

## Provenance

- **ECR image:** `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:23c5e8286e25bbcb911772e05145d7f43781667c65da9760ff57b3751c0136f2` (tag `flu-contam-solver01`)
- **AWS Batch job definition:** `arn:aws:batch:us-east-1:994254241749:job-definition/picard-flu-contam-solver-01:1` (1 vCPU, 4096 MB)
- **ContamX binary SHA-256 (verified in worker):** `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b` (`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_transport_fit_01/vendor/contamx3`)
- **S3 campaign prefix:** `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_contam_solver_01/`
- **Batch jobs:**
  - 1-child ContamX smoke (`exp450_contamx`, seed `8105`): `04f18e35-24a8-464c-a793-545564750d32` — `SUCCEEDED` (64.21 s wall, 65.51 s CPU, `ContamXTransportEngine`, 8 index / 2 onboard)
  - 20-seed native canary (`exp450_native`, seeds `8105`–`8124`): `c601f929-531a-436c-b530-2ce08d5e8f4d` — `SUCCEEDED` (20/20 children, 0 failed)
  - 20-seed ContamX canary (`exp450_contamx`, seeds `8105`–`8124`): `91ae3af2-79fe-466a-b55d-5dfc1516aaf6` — `SUCCEEDED` (20/20 children, 0 failed)
- **Submission note:** Both canary arrays were submitted with `aws batch submit-job` against `deploy/aws/campaign_entrypoint.py` and `picard-flu-contam-solver-01:1`.
- **Artifact audit:** 40/40 expected files present (`exp450_native`: 20, `exp450_contamx`: 20); 0 missing, 0 extra, 0 duplicates; 20/20 `ContamTransportEngine` in native, 20/20 `ContamXTransportEngine` in ContamX; 40/40 `engine_git_sha` = `77235441f62e3a87e3ec6e45164fbfbec3d82879`.

## Measured Canary Results (`expedition_cruise_450`, 20 Paired Seeds `8105`–`8124`, 288 Epochs, Organic `influenza_a`, `active_profiles`)

| Metric | Native (`ContamTransportEngine`) | ContamX (`ContamXTransportEngine`) | Diff / Ratio (ContamX vs Native) |
| --- | ---: | ---: | ---: |
| Onboard acquisitions (mean / median) | 1.0 / 1.0 | 1.6 / 1.0 | +0.6 / +0.0 |
| Onboard acquisitions (min–max) | 0–6 | 0–18 | −4 to +18 |
| Seeds identical / ContamX < Native / ContamX > Native | — | — | 14 / 4 / 2 |
| `hvac_airborne` dominant infections (mean) | 0.0 | 0.0 | 0.0 |
| `hvac_airborne` nonzero-dose seeds | 0 / 20 | 1 / 20 (seed 8123: 0.001 particles) | +1 seed |
| Init wall time (mean / median, s) | 0.26 / 0.22 | 0.37 / 0.34 | +0.11 s |
| Run wall time (mean / median, s) | 64.47 / 62.31 | 61.56 / 62.32 | 0.95× |
| Total wall time (mean / median, s) | 64.73 / 62.53 | 61.93 / 62.72 | 0.96× |
| Total CPU time (mean / median, vCPU-s) | 65.46 / 63.26 | 62.55 / 63.16 | 0.96× |
| ContamX child subprocess CPU (mean / range, s) | — | 0.0056 (0.0045–0.0068) | <0.01% of CPU |

### Divergent Seeds (`expedition_cruise_450`, 6 of 20)

- `8105`: native 3 (`droplet: 1, caregiver: 2`) vs ContamX 2 (`caregiver: 2`), diff `−1`
- `8109`: native 1 (`caregiver: 1`) vs ContamX 0, diff `−1`
- `8113`: native 2 (`droplet: 2`) vs ContamX 3 (`droplet: 2, caregiver: 1`), diff `+1`
- `8117`: native 1 (`caregiver: 1`) vs ContamX 0, diff `−1`
- `8121`: native 6 (`droplet: 5, caregiver: 1`) vs ContamX 2 (`caregiver: 2`), diff `−4`
- `8123`: native 0 vs ContamX 18 (`droplet: 17, caregiver: 1`; `airborne_any_count: 2`, `hvac_airborne` particles `0.001`), diff `+18`

## Pre-Canary Local Smokes (All 7 Hulls, Seed `8105`)

- Full 288-epoch pair on `expedition_cruise_450`: native 3 onboard (120.10 s wall) vs ContamX 2 onboard (103.09 s wall, 0.01 s child CPU) — identical infection counts to Batch seed `8105`.
- 24-epoch paired smokes on the other 6 hulls (seed `8105`): all 6 resolved cleanly to `ContamTransportEngine` / `ContamXTransportEngine` with zero fallbacks. `diamond_princess` showed an early `hvac_airborne` difference (14 vs 3 onboard, 1893.0 vs 111.9 `hvac_airborne` particles in 24 epochs); `mega_cruise_5000` took ~196 s for 24 epochs (~39 min extrapolated for 288 epochs on 1 vCPU; unmeasured at full length).

## Interpretation (Inferred / Hypothesis — Not Yet Proven Across Fleet)

- **Compute cost:** On `expedition_cruise_450`, ContamX adds ~0.11 s at initialization (5.6 ms child CPU) and **no measurable runtime overhead** over 288 epochs (`0.96×` wall and CPU ratio, within Spot variance).
- **Prediction divergence:** On `expedition_cruise_450`, 14/20 seeds are identical and median paired difference is `0.0`, with zero `hvac_airborne`-dominant infections in either arm. The 6 divergent seeds (including `8123`: `0 → 18` via secondary droplet spread) are consistent with small solver/RNG perturbations amplified stochastically rather than a large direct airborne shift on this small hull.
- **Fleet generalization caveat:** Because `diamond_princess` showed substantial `hvac_airborne` activity in the 24-epoch local smoke (14 vs 3 onboard), `expedition_cruise_450` alone does not test the high-HVAC-recirculation regime. Running the remaining 6 current cruise hulls is needed to measure solver differences where HVAC airborne transmission is active.

## Next Decision

- Approve launching the remaining 12 blocks (6 current cruise hulls × 2 solvers × 20 seeds = 240 children, excluding historic naval vessels) on AWS Batch, followed by full-fleet readout, deviation analysis, and Edison `collect` handoff — or adjust hull roster / seed count / `mega_cruise_5000` resources before submitting.
