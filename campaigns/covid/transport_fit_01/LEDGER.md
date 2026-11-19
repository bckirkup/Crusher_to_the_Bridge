# LEDGER — covid_transport_fit_01

Campaign mechanics for COVID-TRANSPORT-FIT-01: the post-airflow-repair
re-visit of the COVID outbreak replays, native vs ContamX transport at
one pinned revision, scored against the record. Frozen designs:
`picard_framework/runs/covid_transport_fit_01_dp_design.json` (the
CREW-REACH-01 `boxed_s1s2` configuration verbatim, Θ 7.9e6, 20 seeds)
and `picard_framework/runs/covid_transport_fit_01_gm_design.json` (the
COVID-GM-RESCORE-02 anchor row, Θ 2.37e11, 50 seeds). Engine axis is a
new `transport_engine` arm key (`picard_framework/covid_boarding_screen.py`,
values `native` | `contamx` — `auto` excluded so a solver failure can
never silently pass as the baseline).

## 1. Spec

| Field | Value |
|---|---|
| Queue | `picard-analysis-queue` (EC2 CE `picard-analysis-compute-ondemand`; the shared jobdef template emits no `platformCapabilities`, i.e. EC2 capability — `picard-analysis-fargate-queue`'s FARGATE-only CE rejects it) |
| Jobdef | `picard-covid-transport-fit-01` |
| Image tag | `covid-transport-fit-01` |
| S3 prefix | `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_transport_fit_01/` |
| Resources | 1 vCPU / 4096 MB |
| Designs | `covid_transport_fit_01_{dp,gm}_design.json` |

## 2. Binary

ContamX cells need the solver, which `.dockerignore` keeps out of images.
`campaigns/covid/transport_fit_01/cell.py` fetches
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_transport_fit_01/vendor/contamx3`
(under the campaign prefix: the deploy role has no PutObject on the
bucket's top-level `vendor/` path)
(NIST ContamX 3.4.0.3 64-bit Linux, U.S. public domain, sha256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`
— the same digest CONTAM-PHASE2 pinned) at cell start when no local
binary resolves, verifies the digest, and sets `CONTAMX_BINARY`.
Native cells never touch the fetch.

## 3. Blocks

| Block | Design | Arm | Seeds | Cells | Notes |
|---|---|---|---|---:|---|
| `dp_contamx_canary` | dp | contamx | 20200205–224 | 20 | CANARY — novel path on the big hull; STOP after readout |
| `dp_native` | dp | native | 20200205–224 | 20 | same-revision native leg |
| `gm_native` | gm | native | 20200205–254 | 50 | |
| `gm_contamx` | gm | contamx | 20200205–254 | 50 | |

Total: 140 cells (20 canary + 120 fleet).

## 4. Audit

Every payload echoes `delivery.transport_engine` (declared) and
`delivery.transport_engine_resolved` (the engine class that actually
ran). The readout fails the cell set if any `contamx` arm payload
resolves `ContamTransportEngine` (blocked fallback) or any `native`
arm payload resolves `ContamXTransportEngine`.

## 5. Runs

| Date | Block | Cells | Job | SHA | Digest | Result |
|---|---|---:|---|---|---|---|
| 2026-11-19 | (image) | — | — | `0d70c022` (code `8de77294`) | `sha256:7023d963f3a3ede96c7f47def3bb539ecef1b9c8bc2a112697c45e82e37719a0` | built root Dockerfile + Dockerfile.campaign, pushed |
| 2026-11-19 | dp_contamx_canary | 20 | `0a894bc5-0dca-4554-816f-0ebc853067ae` | `8de77294` | jobdef `:2` | CANARY submitted |

## 6. Scoring

Record anchors read from `data/observation/covid_fit_targets.json`:
DP — recorded_onsets vs 197 [197,199], before_share vs 0.173,
lab_confirmed vs 712, lab-confirmed crew share vs 0.29 (DP-scale
conditioned), dated share vs 0.277, asym share vs 0.5047, T2 turn.
GM — campaign positives vs 128/217 (H1 0.5899), asym share vs 0.8125
(H2), takeoff (≥10 recorded onsets). Engine sensitivity is the
seed-paired contamx−native delta per channel.
