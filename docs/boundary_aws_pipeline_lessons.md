# Boundary surface AWS pipeline — lessons learned

Operational notes for `boundary_surface_v1` (Phase 1 Spot ABM + Phases 2–5
On-Demand analysis). Companion to [`stan_hurdle_lessons.md`](stan_hurdle_lessons.md).

## Validation: keep it light

Full-matrix `--dry-run` expands every Picard spec and becomes onerous at ~10k–17k
runs. Prefer:

1. Arithmetic count via
   `python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian …/boundary_surface_v1_manifest.json`
   (wave1=10000, wave2=7600 deferred).
2. Existing `--smoke` only (`destroyer_baseline`, 2 epochs, 20 agents, limit 1).
3. Spot array + S3 resume for real coverage — not local 7000-agent rehearsals.

## Spot vs On-Demand

| Workload | Compute | Why |
|----------|---------|-----|
| Phase 1 ABM shards | Fargate **Spot** (`picard-campaign-queue`) | Interruptible; `--resume` + shard logs make retries cheap |
| Phase 3 Stan | Fargate **On-Demand** (`picard-analysis-queue`) | MCMC does not resume mid-chain after Spot reclaim |
| Phase 2 surface / Phase 4 MC | On-Demand (same analysis queue) | Modest CPU; keep off Spot reclaim noise |

Do **not** put CmdStan in the `picard-campaign` Spot image.

## Stan models for this campaign

Boundary pipeline Stage B is **Beta regression on attack rate \| outbreak**
(`boundary_ar.stan`), indexed by `log(k)`. That is distinct from the norovirus
monograph NegBin **trajectory** model (`norovirus_trajectory.stan`), which stays
for the C12c/C14 analysis path.

Stage A: `boundary_outbreak.stan` (Bernoulli-logit with `log(k)` + dose +
platform + surveillance). Multi-pathogen via `--pathogen`.

Empirical `outbreak_surface` from Phase 2 unblocks Monte Carlo if Stan lags.

## S3 layout

```
s3://<bucket>/campaign/boundary_surface_v1/           # Phase-1 zips + _resume/
s3://<bucket>/campaign/boundary_surface_v1/analysis/
  surfaces/          # outbreak_surface.csv/json
  bundles/<pathogen>/  # campaign_bundle outputs for Stan
  stan/<pathogen>/   # hurdle fits
  mc/<pathogen>/     # policy_comparison, figures, report.md
```

## Operator sequence (manual; no Step Functions in v1)

1. Rebuild/push `picard-campaign` (manifest in image) →
   `submit_boundary_surface.ps1 -ShardCount 200`
2. When Tier 1 zips look healthy → build/push `picard-boundary-analysis` →
   `ensure_analysis_infra.ps1` → `submit_boundary_analysis.ps1 -Phase surface`
3. Build per-pathogen analysis bundles (local or future Batch step) under
   `analysis/bundles/<pathogen>/` → `-Phase stan -Pathogen …`
4. `-Phase mc -Pathogen …` (uses surface beside stan-fit or surfaces/)
5. Optional Tier 2: submit deferred `b2_*` with containerOverrides
   `--include-deferred` once Tier 1 is trusted

## Job definition image tags

`submit-job` uses the **latest ACTIVE** `picard-campaign` revision. If that
revision pins an old ECR tag (e.g. `c14sf-…`) instead of `:latest`, children
will run a stale image and miss new manifests. After pushing `:latest`,
re-register from `batch_job_definition.json` (which uses `:latest`) before
submit, or pin `picard-campaign:<REV>` explicitly.

## IAM notes

Execution role must pull **both** ECR repos (`picard-campaign`,
`picard-boundary-analysis`) and write both log groups. Re-apply
`batch_execution_role_permissions.json` and
`deploy_role_permissions_policy.json` with an **admin** identity
(`iam:PutRolePolicy` is not on PowerUser or `picard-deploy-role`):

```powershell
# After filling ACCOUNT_ID / REGION / BUCKET placeholders:
aws --profile <admin> iam put-role-policy --role-name picard-deploy-role `
  --policy-name picard-deploy-permissions --policy-document file://deploy-perms.json
aws --profile <admin> iam put-role-policy --role-name picard-campaign-execution-role `
  --policy-name picard-campaign-execution-permissions --policy-document file://exec-perms.json
```

Until that lands, analysis containers may fail at ECR pull or log init even
though job definitions and the On-Demand CE exist.
