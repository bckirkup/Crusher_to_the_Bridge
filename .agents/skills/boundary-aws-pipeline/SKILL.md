---
name: boundary-aws-pipeline
description: Run the boundary_surface_v1 pre-boarding outbreak-surface campaign on AWS — Phase 1 Fargate Spot ABM, then On-Demand surface/Stan/MC analysis. Use when submitting boundary Spot jobs, building the analysis image, or fitting Bernoulli+Beta-AR boundary Stan.
---

# Boundary surface AWS pipeline

End-to-end path for the pre-boarding decision-model **outbreak surfaces**
(4 pathogens × 4 platforms × k-sweep). Spec inputs lived as
`boundary_campaign_manifest.json` / `boundary_pipeline_spec.md`; the
repo artifact is
`picard_framework/runs/mega_cruise_campaign/boundary_surface_v1_manifest.json`.

Canonical ops notes (gotchas that already burned wall-clock):
`docs/boundary_aws_pipeline_lessons.md`.

## Phase 1 — Spot ABM

```powershell
# Light checks only (no full-matrix dry-run)
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian `
  picard_framework/runs/mega_cruise_campaign/boundary_surface_v1_manifest.json
python picard_framework/runs/mega_cruise_campaign/campaign_runner.py --smoke

docker build -t picard-campaign .
docker run --rm picard-campaign --smoke
# push to ECR (see deploy/aws/README.md), then:
# If ACTIVE job-def rev pins a stale tag, re-register batch_job_definition.json (:latest)
.\deploy\aws\submit_boundary_surface.ps1 -ShardCount 200
.\deploy\aws\monitor_campaign.ps1 -JobId <id> -Prefix campaign/boundary_surface_v1/ -Watch

# Tier-2 deferred wave (same S3 prefix; --resume):
.\deploy\aws\submit_boundary_surface.ps1 -Tier b2 -ShardCount 200
```

- Generator shorts: **`b1` / `b2`** share the c1/a2 calibration Cartesian path.
- Wave-1 = `b1_*` (10,000); `b2_*` are `deferred: true` (7,600).
- `-Tier` / `-IncludeDeferred` apply real `containerOverrides` (job-def template
  has no `--tier` placeholder).
- S3: `s3://$BUCKET/campaign/boundary_surface_v1/`

## Phases 2–5 — On-Demand analysis

Separate image (`deploy/aws/Dockerfile.analysis`) with CmdStan. Queue:
`picard-analysis-queue` (Fargate On-Demand CE `picard-analysis-ondemand`).

```powershell
docker build -f deploy/aws/Dockerfile.analysis -t picard-boundary-analysis .
# push ECR repo picard-boundary-analysis, then:
.\deploy\aws\ensure_analysis_infra.ps1
.\deploy\aws\submit_boundary_analysis.ps1 -Phase surface
.\deploy\aws\submit_boundary_analysis.ps1 -Phase bundle
.\deploy\aws\submit_boundary_analysis.ps1 -Phase stan -Pathogen norovirus
.\deploy\aws\submit_boundary_analysis.ps1 -Phase mc -Pathogen norovirus
```

Stan entrypoint: `python -m picard_framework.analysis.stan.fit_boundary_hurdle`
(`boundary_outbreak.stan` + `boundary_ar.stan`). Leave monograph NegBin
trajectory alone. MC may use empirical surfaces while Stan runs.

### Analysis image must-haves

| Item | Why |
|------|-----|
| COPY `crusher_labs/`, `engines/`, `decision_engine/`, `telemetry_buffer/`, `orchestrator*.py` | Surface/bundle import chain; missing → `ModuleNotFoundError` |
| `CMDSTAN=/opt/cmdstan/cmdstan-2.39.0` (versioned dir) in Dockerfile **and** Stan job def | Parent `/opt/cmdstan` makes fits exit 0 while skipping MCMC |
| Re-register Stan job def after ENV change | Submit uses latest ACTIVE revision |
| Surface/bundle sync excludes `b2_*` | Keeps Tier-1 surfaces clean during concurrent Tier-2 Spot |

## See also

- `docs/boundary_aws_pipeline_lessons.md`
- `.agents/skills/aws-batch-campaign/SKILL.md` — Spot gotchas / stale job-def tags
- `.agents/skills/preboarding-wearable-decision/SKILL.md` — local MC
