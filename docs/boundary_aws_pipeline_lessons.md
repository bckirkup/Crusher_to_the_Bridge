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
| Phase 1 ABM shards | EC2 **Spot**, c7i/c7a (`picard-campaign-queue`) | Interruptible; `--resume` + shard logs make retries cheap |
| Phase 3 Stan | EC2 **On-Demand**, c7i/c7a (`picard-analysis-queue`) | MCMC does not resume mid-chain after Spot reclaim |
| Phase 4 MC | EC2 On-Demand, c7i/c7a (same analysis queue) | Modest CPU; keep off Spot reclaim noise |
| Phase 2 surface / bundle / report | EC2 On-Demand, r7i/r7a (`picard-analysis-memory-queue`) | Aggregation holds a whole campaign frame in RAM |

All three compute environments sit at `minvCpus: 0`, so an idle pathway runs no
instances at all.

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

1. Rebuild/push `picard-campaign` (manifest in image) → re-register job def if
   ACTIVE rev is pinned to a stale tag →
   `submit_boundary_surface.ps1 -ShardCount 200` (Tier-1 / `b1_*` only).
2. When Tier-1 zips look healthy → build/push `picard-boundary-analysis` →
   `ensure_analysis_infra.ps1` → `submit_boundary_analysis.ps1 -Phase surface`
   and `-Phase bundle` (entrypoint excludes `b2_*` so Tier-1 surfaces stay clean).
3. Per-pathogen: `-Phase stan -Pathogen …` and `-Phase mc -Pathogen …`.
   MC can start on **empirical** `outbreak_surface` while Stan is still sampling.
4. Optional Tier-2 Spot once Tier-1 is trusted:
   `submit_boundary_surface.ps1 -Tier b2 -ShardCount 200`
   (same S3 prefix; `--resume` skips completed `b1_*`). Then re-run surface/bundle
   **without** the `b2_*` exclude if you want the full 17.6k surface.
5. Optional `-Phase report` after MC artifacts land under `analysis/mc/<pathogen>/`.

## Job definition image tags

`submit-job` uses the **latest ACTIVE** `picard-campaign` revision. If that
revision pins an old ECR tag (e.g. `c14sf-…`) instead of `:latest`, children
will run a stale image and miss new manifests. After pushing `:latest`,
re-register from `batch_job_definition.json` (which uses `:latest`) before
submit, or pin `picard-campaign:<REV>` explicitly.

Lived failure: ACTIVE rev 23 pinned `c14sf-…` → 200/200 FAILED missing
`boundary_surface_v1_manifest.json`. Re-registering rev 24 with `:latest`
yielded **SUCCEEDED 200/200** and exactly **10,000** Tier-1 zips.

## Analysis image gotchas (lived)

1. **Import graph.** Surface/bundle import `picard_framework` paths that pull
   `crusher_labs`, `engines`, `decision_engine`, `telemetry_buffer`, and the
   root `orchestrator*.py` modules. A thin COPY of `picard_framework/` alone
   fails at runtime with `ModuleNotFoundError: crusher_labs`. Keep
   `Dockerfile.analysis` in sync with those deps; rebuild/push after any fix.
2. **`CMDSTAN` path.** `cmdstanpy.install_cmdstan(dir='/opt/cmdstan')` installs
   into `/opt/cmdstan/cmdstan-<version>/` (e.g. `cmdstan-2.39.0`). Setting
   `CMDSTAN=/opt/cmdstan` makes fits exit 0 while **skipping MCMC**. Pin both
   the Dockerfile `ENV` and the Stan job-def environment to the versioned dir,
   then re-register the Stan job definition.
3. **Tier-1 sync exclude.** Bundle/surface phases exclude `b2_*` prefixes so a
   concurrent Tier-2 Spot wave does not pollute Tier-1 surfaces. Drop that
   exclude only when intentionally building the full-matrix surface.
4. **Spot Tier flag.** `submit_boundary_surface.ps1 -Tier b2` (and
   `-IncludeDeferred`) now emits real `containerOverrides` — the job-def
   command template has no `--tier` placeholder.

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

`logs:DescribeLogGroups` must be on `Resource: "*"` (CloudWatch does not allow
log-group ARNs for that action). The deploy policy keeps stream/event actions
scoped to the two `/aws/batch/picard-*` groups and splits DescribeLogGroups
into its own statement.

Until execution-role ECR/log grants land, analysis containers may fail at
image pull or log init even though job definitions and the On-Demand CE exist.

## Local artifacts

Do **not** commit regenerable `boundary_analysis/` trees (local MC figures /
`policy_comparison.csv`). S3 under
`campaign/boundary_surface_v1/analysis/` is the campaign source of truth.
