# FLU-CONTAM-SOLVER-01 — Campaign Ledger

> **Design:** `campaigns/flu/contam_solver_01/DESIGN.md`
> **Branch / Commit:** `devin/1795263522-flu-contam-solver-01` (worker commit `77235441f62e3a87e3ec6e45164fbfbec3d82879`)
> **Canonical 6-Hull Readout Artifacts:** `campaigns/flu/contam_solver_01/readout_6hull/` (`report.md`, `summary.json`, `paired_cells.csv`, `daily_dynamics.csv`, `deviation_analysis.json`)
> **Canary Readout Artifacts:** `campaigns/flu/contam_solver_01/readout_canary/`
> **Edison S3 Bundle:** `campaign/flu_contam_solver_01/readout_6hull/flu_contam_solver_01_6hull_bundle.tar.gz` (`294,254` bytes, SHA-256 `e25e54987cfe9504ea6ff8187ed7fe31fee6db19b0f3c7889bc0b835bcd07e58`)

## Status

- **Stage:** **6-hull paired campaign complete and read out** (120 paired seeds = 240 cells across `greg_mortimer`, `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, `diamond_princess`, `explorer_seas_06`). `mega_cruise_5000` remains **held** per user decision for higher memory/vCPU.
- **Roster (historic naval vessels excluded):** 6 completed current cruise hulls + 1 held (`mega_cruise_5000`). Uncommissioned directories `expedition_cruise_300` and `messy_cruise_500` (no `contam/` bundle, no `voyage_config.json`) excluded.

## Provenance

- **ECR image:** `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign@sha256:23c5e8286e25bbcb911772e05145d7f43781667c65da9760ff57b3751c0136f2` (tag `flu-contam-solver01`)
- **AWS Batch job definition:** `arn:aws:batch:us-east-1:994254241749:job-definition/picard-flu-contam-solver-01:1` (1 vCPU, 4096 MB)
- **ContamX binary SHA-256 (verified in worker):** `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b` (`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_transport_fit_01/vendor/contamx3`)
- **S3 campaign prefix:** `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_contam_solver_01/`
- **Submission note:** All 12 arrays (canary + 5 hulls) were submitted directly with `aws batch submit-job` against `deploy/aws/campaign_entrypoint.py` and `picard-flu-contam-solver-01:1`.
- **Batch jobs (all 12 arrays `SUCCEEDED`, 20/20 children each, 0 failed):**
  - 1-child ContamX smoke (`exp450_contamx`, seed `8105`): `04f18e35-24a8-464c-a793-545564750d32` — `SUCCEEDED`
  - Canary (`expedition_cruise_450`, seeds `8105`–`8124`):
    - `exp450_native`: `c601f929-531a-436c-b530-2ce08d5e8f4d` / `exp450_contamx`: `91ae3af2-79fe-466a-b55d-5dfc1516aaf6`
  - 5-hull paired arrays (`r2` resubmission; initial `r1` failed on startup with exit code 2 due to duplicate `"python3"` ahead of image `ENTRYPOINT ["python3"]` and was terminated):
    - `gm_native`: `1e68cfaf-4023-42fe-808e-f1312f493444` / `gm_contamx`: `26895bbc-ac95-4c31-88a2-318615202fd8`
    - `cls1900_native`: `9c2b3cf7-0ec0-403a-bb2a-5a890585f6c3` / `cls1900_contamx`: `308cb1d4-d0d5-4b44-b416-0b5caacdd62d`
    - `spr3000_native`: `5fd5978a-ab79-4f05-83b8-35767f61f359` / `spr3000_contamx`: `c96ef405-a445-4d15-ad8d-27ccc0d8eaa8`
    - `dp_native`: `204e9fdd-818c-4921-baac-9b9a9d48e2eb` / `dp_contamx`: `2c538c38-eba3-4d51-9b61-81a1467381ed`
    - `exp06_native`: `46368e11-f1ac-4518-b493-b6ca88959d3f` / `exp06_contamx`: `1637f3b3-05e0-4823-89f9-47116519169e`
  - `mega_cruise_5000` (`mega5000_native` / `mega5000_contamx`): **held** per user decision for higher memory/vCPU.
- **240-cell artifact audit:** 240/240 expected `cell_<seed>.json` files present (12 blocks × 20 seeds `8105`–`8124`); 0 missing, 0 extra, 0 duplicates; 120/120 `ContamTransportEngine` in native blocks, 120/120 `ContamXTransportEngine` in ContamX blocks; 240/240 `engine_git_sha` = `77235441f62e3a87e3ec6e45164fbfbec3d82879`, `epochs=288`, `pathogen_id=influenza_a`, `bundle=active_profiles`.

## Measured 6-Hull Results (120 Paired Seeds, 288 Epochs, Organic `influenza_a`, `active_profiles`)

### Epidemiological Comparison (Onboard Acquisitions & Paired Differences)

| Hull | Comp | Native (mean / med) | ContamX (mean / med) | Paired Diff (mean / med) | eq / Ctx>Nat / Ctx<Nat | Wilcoxon p | `hvac_airborne` Dom (Nat / Ctx) |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `greg_mortimer` | 243 | 5.00 / 1.5 | 4.35 / 1.5 | −0.65 / +0.0 | 8 / 6 / 6 | 0.8374 | 62 / 56 |
| `expedition_cruise_450` | 450 | 1.00 / 1.0 | 1.60 / 1.0 | +0.60 / +0.0 | 14 / 2 / 4 | 0.7812 | 0 / 0 |
| `classic_cruise_1900` | 1910 | 2.25 / 2.0 | 2.20 / 1.0 | −0.05 / +0.0 | 14 / 2 / 4 | 1.0000 | 1 / 1 |
| `spirit_cruise_3000` | 3000 | 3.05 / 2.5 | 2.50 / 2.0 | −0.55 / +0.0 | 9 / 4 / 7 | 0.1475 | 0 / 0 |
| `diamond_princess` | 3810 | 44.40 / 29.5 | 46.60 / 29.5 | +2.20 / +1.0 | 0 / 11 / 9 | 0.5752 | 741 / 744 |
| `explorer_seas_06` | 4428 | 2.95 / 3.5 | 3.30 / 3.0 | +0.35 / +0.0 | 8 / 7 / 5 | 0.3257 | 0 / 0 |
| **Pooled (120 pairs)** | — | — | — | **+0.32** | **53 / 32 / 35** | **0.9048** | **804 / 801** |

### Resource Comparison (Worker-Measured Wall Time, vCPU, ContamX Child CPU, Peak RSS)

> Note: Timings below are worker-measured (`timing.total_wall_s`, `timing.total_cpu_s`, `timing.total_cpu_children_s`) from the 240 cell artifacts on 1-vCPU / 4096-MB Batch children. Container-level AWS Batch billed wall time (`stoppedAt - startedAt`) was not separately tabulated; at 1 vCPU/child, worker wall time is a lower bound on billed vCPU-seconds (excluding container pull/startup overhead).

| Hull | Init Wall (Nat / Ctx, s) | Total Wall (Nat / Ctx, s) | Wall Ratio | Total CPU (Nat / Ctx, vCPU-s) | CPU Ratio | ContamX Child CPU (mean, s) | Max RSS (Nat / Ctx, MB) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `greg_mortimer` | 0.21 / 0.33 | 33.1 / 33.4 | 1.011× | 34.4 / 34.9 | 1.017× | 0.0060 | 144 / 171 |
| `expedition_cruise_450` | 0.26 / 0.37 | 64.7 / 61.9 | 0.957× | 65.5 / 62.6 | 0.956× | 0.0056 | 150 / 176 |
| `classic_cruise_1900` | 0.39 / 0.59 | 299.2 / 304.9 | 1.019× | 300.7 / 306.2 | 1.018× | 0.0114 | 227 / 256 |
| `spirit_cruise_3000` | 0.51 / 0.82 | 488.1 / 512.6 | 1.050× | 490.9 / 515.0 | 1.049× | 0.0237 | 297 / 326 |
| `diamond_princess` | 0.67 / 1.06 | 627.5 / 643.5 | 1.025× | 635.6 / 651.6 | 1.025× | 0.0502 | 328 / 353 |
| `explorer_seas_06` | 0.72 / 0.99 | 762.0 / 790.9 | 1.038× | 765.5 / 793.3 | 1.036× | 0.0274 | 359 / 385 |
| **Fleet Total (120 pairs)** | — | **12.64 / 13.04 h** | **1.032×** | **12.74 / 13.13 vCPU-h** | **1.031×** | **2.49 s total (0.005%)** | **359 / 385** |

## Outbreak Dynamics & Deviation Explanation

- **No statistically detected directional solver bias (measured; exploratory Wilcoxon):** Across all 6 hulls individually (exploratory Wilcoxon signed-rank p = 0.148–1.000) and pooled across all 120 paired seeds (W = 1120.0, p = 0.9048, mean paired diff +0.32 onboard acquisitions; median paired difference 0.0 on 5 hulls and +1.0 on `diamond_princess`, where arm medians are 29.5 vs. 29.5), `ContamXTransportEngine` and `ContamTransportEngine` show no statistically detected directional shift in ensemble outbreak size. Note: without a pre-declared equivalence margin and confidence interval, non-significance alone does not formally bound small residual bias.
- **Two distinct HVAC-airborne regimes (measured):**
  - *High-HVAC-airborne hulls (`diamond_princess`, `greg_mortimer`):* `hvac_airborne` accounts for **83.4% / 79.8%** of onboard acquisitions on `diamond_princess` (741/888 native, 744/932 ContamX; active on 20/20 seeds in both arms; sustained daily incidence of 2.5–5.4/day through day 11) and **62.0% / 64.4%** on `greg_mortimer` (62/100 native, 56/87 ContamX; active on 16/20 native and 14/20 ContamX seeds; early wave peaking days 2–4). Both hulls show large **symmetric per-seed variance** (e.g. `diamond_princess` seed `8108`: 191→109; seed `8113`: 70→140; `greg_mortimer` seed `8120`: 49→0; seed `8118`: 9→39) that cancels at the ensemble level. Notably, mean airborne particle sums on infected agents are higher under native than ContamX (`11,869` vs `6,960` on `diamond_princess`, `2,450` vs `1,508` on `greg_mortimer`), yet `hvac_airborne`-dominant infection counts are nearly identical (741 vs 744; 62 vs 56).
  - *Droplet + caregiver hulls (`expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, `explorer_seas_06`):* `hvac_airborne` is dominant in only **1 infection total per arm** across 80 paired seeds (`classic_cruise_1900` seed `8122`). Outbreaks remain small (1.0–3.3 onboard acquisitions, 0.07%–0.36% attack rate) with brief secondary bumps on days 2–5 that extinguish by days 6–8.
- **Why individual seeds diverge (inferred / hypothesis):** Even small floating-point differences in HVAC airflow/concentration solutions between `ContamTransportEngine` and `ContamXTransportEngine` alter single-agent infection draws early in a voyage, which then cascade stochastically through secondary droplet, caregiver, and HVAC-airborne transmission (including on low-airborne hulls such as `expedition_cruise_450` seed `8123`: 0→18 via 17 secondary droplet infections). Direct paired-epoch concentration tracing was not run in this stage, so the exact per-zone airflow difference driving the `11,869` vs `6,960` particle-sum ratio on `diamond_princess` remains a hypothesis for targeted follow-up if needed.
- **Compute overhead (measured):** ContamX adds **+0.11 to +0.39 s** at initialization (`contamx3` subprocess CPU is **2.49 s total across all 120 runs**, or **0.005%** of ContamX vCPU-hours), **~25–29 MB** extra peak RSS, and **+3.1% total vCPU / +3.2% total wall time** across the 6-hull fleet (13.13 vs 12.74 vCPU-h). Because `explorer_seas_06` peaked at 385 MB RSS (well under 4096 MB) and ~13 min wall, memory is not the bottleneck — single-vCPU wall time is.

## Edison Handoff (`campaign-collect`)

- Uploaded compact verified bundle (`294,254` bytes, all 240 raw cells + `readout_6hull/` summaries) to:
  - `s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_contam_solver_01/readout_6hull/flu_contam_solver_01_6hull_bundle.tar.gz`
  - SHA-256: `e25e54987cfe9504ea6ff8187ed7fe31fee6db19b0f3c7889bc0b835bcd07e58`
- Also uploaded individual canonical readout files (`report.md`, `summary.json`, `paired_cells.csv`, `daily_dynamics.csv`, `deviation_analysis.json`) under the same prefix.
- Dispatched `.github/workflows/campaign_collect.yml` with `exact_key=campaign/flu_contam_solver_01/readout_6hull/flu_contam_solver_01_6hull_bundle.tar.gz` (pauses on approval-gated `aws-campaign` environment for Benjamin's click to publish the Edison-readable GitHub issue index + workflow artifact).

## Next Decision

- **Approve `campaign-collect` run** in GitHub Actions (`aws-campaign` environment) so Edison receives the updated campaign index issue and the verified 240-cell + readout bundle artifact.
- **Decide on `mega_cruise_5000`:** held at ~39 min extrapolated wall/child on 1 vCPU (40 cells = ~26 vCPU-h). Launch `mega_cruise_5000` in a new session (same 4096 MB is likely sufficient based on 385 MB peak RSS on `explorer_seas_06`, or bump memory/vCPU if desired), or close the study at 6 hulls.
