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
| 2026-11-19 | dp_contamx_canary | 20 | `0a894bc5-0dca-4554-816f-0ebc853067ae` | `8de77294` | jobdef `:2` | CANARY submitted → 20/20 SUCCEEDED, all cells resolved `ContamXTransportEngine` (audit: 0 wrong_engine, 0 duplicates). Note: image predates the cell fail-closed check and the GM funnel_echo flag — canary audit used the payload's resolved-engine echo instead of the post-run assert. |
| 2026-11-19 | (image v2) | — | — | `106a3583` (main HEAD post-merge) | `covid-transport-fit-01-v2` @ `sha256:56f860c8ebba8a128b9a308214fa2a8426b55529d770c74cfdb46f6c64b1f485` | rebuilt for fleet blocks (fail-closed cell + GM funnel_echo now in image); Docker Hub rate-limited, base FROM resolved via `public.ecr.aws` mirror |
| 2026-11-19 | dp_native | 20 | `bec97e14-7e51-4a49-9b1c-37a2eb60ad5c` | `106a3583` | v2 digest | 20/20 SUCCEEDED |
| 2026-11-19 | gm_native | 50 | `da861223-2b85-4479-80d3-21a343502fee` | `106a3583` | v2 digest | 50/50 SUCCEEDED |
| 2026-11-19 | gm_contamx | 50 | `a02bd464-8cb5-4ece-b427-351c0473f70c` | `106a3583` | v2 digest | 50/50 SUCCEEDED |

### Full readout — 140/140 cells, audit clean (0 wrong_engine, 0 missing, 0 duplicates)

**Engine verdict: the solver choice is immaterial at this grain.** Every
seed-paired contamx−native delta centres on zero — DP recorded_onsets
Δ0 [0–4], lab_confirmed Δ0 [0–11]; GM campaign_positives Δ−0.48 mean
[-11,+7]. The two solvers move individual seeds by a handful of
infections and flip nothing. Under the repaired airflow model the
outcome is set upstream of the HVAC transport operator on both hulls.

**DP `boxed_s1s2` @ Θ7.9e6 — both engines read the same failure:**

| Channel | native | contamx | Record |
|---|---|---|---|
| recorded_onsets | 8 [0–121] | 8 [0–121] | 197 |
| lab_confirmed | 10.5 [0–145] | 10.5 [0–145] | 712 |
| takeoff (≥10 onsets) | 9/20 | 9/20 | always |
| dated share | 0.835 | 0.807 | 0.277 |
| asym share day-31 | 0.146 | 0.146 | 0.505 |
| asym share final | 0.217 | 0.237 | 0.437 |
| crew share (DP-scale) | 0.425 (n=4) | 0.453 (n=4) | 0.29 |

The airflow repairs (B1–B3) turned DP takeoff into a coin flip: 9/20
seeds reach ≥10 recorded onsets, and the median cell records 8 onsets
vs the record's 197. Pooled confirmations are roughly preserved
(1,236–1,294 over 20 cells vs CREW-REACH-01's ~1,351–1,453 on the same
boxed design family) — the ensemble is now a few record-scale cells
carrying a mostly-fizzled set rather than a shift of the whole
distribution, so the deficit is outbreak *frequency*, not delivered
dose volume. When an outbreak does occur it is still too symptomatic
and still too crew-loaded — the settled ASC/DATING residuals, not new
structure.

**GM `hygiene_cycle` @ Θ2.37e11:**

| Channel | native | contamx | Record |
|---|---|---|---|
| campaign_positives | 110 [18–134] | 110.5 [18–134] | 128/217 (0.59) |
| takeoff | 48/50 | 48/50 | — |
| asym share (H2 window) | 0.24 [0.18–0.5] | 0.24 [0.18–0.5] | 0.8125 |

Magnitude is in the record's neighbourhood (110 vs 128 positives) and
takeoff is near-certain, but the asymptomatic-at-testing share misses
by ~3.4× — the same too-symptomatic residual as DP, now measured on a
held-out hull.

**Verdict:** the airflow repairs landed a transport layer whose solver
indistinguishability is clean (the operator barely matters to outcomes),
but under the repaired model DP takeoff is ~45% at Θ7.9e6 where the
record always took off — pooled volume is preserved while the
realization frequency halved. The shared residual across both hulls is
not solver or ascertainment: symptomatic-overweight composition.

### Canary readout — DP under ContamX (20 seeds, Θ 7.9e6)

Median [q05–q95] vs record:

| Channel | ContamX | Record |
|---|---|---|
| recorded_onsets | 8 [0–121] | 197 |
| lab_confirmed | 10.5 [0–145] | 712 |
| infections_total | 31 [0–299] | — |
| takeoff share (≥10 onsets) | 0.45 | 1.0 |
| dated share | 0.807 | 0.277 |
| lab crew share (DP-scale, n=4) | 0.453 [0.39–0.89] | 0.29 |
| asym share day-31 | 0.146 [0–0.29] | 0.505 |
| asym share final | 0.237 [0–0.33] | 0.437 |
| before_share | 0.062 | 0.173 |

ContamX carries substantially less transmission than the record (attack
rate under-read by ~20× at the median; takeoff in 9/20 seeds). Where a
non-trivial outbreak does occur it is far more symptomatic and much
more crew-loaded than the record shows. The native-arm comparison is
the pending dp_native block — engine delta cannot be attributed until
that lands.

## 6. Scoring

Record anchors read from `data/observation/covid_fit_targets.json`:
DP — recorded_onsets vs 197 [197,199], before_share vs 0.173,
lab_confirmed vs 712, lab-confirmed crew share vs 0.29 (DP-scale
conditioned), dated share vs 0.277, asym share vs 0.5047, T2 turn.
GM — campaign positives vs 128/217 (H1 0.5899), asym share vs 0.8125
(H2), takeoff (≥10 recorded onsets). Engine sensitivity is the
seed-paired contamx−native delta per channel.
