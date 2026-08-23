---
name: aws-batch-campaign
description: Deploy and run the ~17780-run mega cruise campaign as an AWS Batch Fargate Spot array job using role-based (no-root) access; build/push the ECR image, register the job definition, create the compute environment + queue, submit, monitor, and sync results back locally. Use when running large Crusher simulation batches on AWS.
---

# AWS Batch mega cruise campaign

Deploy and run the ~17,780-run mega cruise campaign
(`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`) as a single
**AWS Batch array job** on **Fargate Spot**. Each array child runs a disjoint
shard and uploads one periodically refreshed fused zip plus one JSON manifest
per shard to one shared S3 prefix.
Each simulation runs in a **subprocess** by default (OS reclaim of RSS); the
job definition defaults to **1 vCPU / 2048 MB** after compact history retention.
Escalate memory if `classify_batch_failures.py` reports OOM.

**`deploy/aws/README.md` is the canonical command reference** — the exact
`aws` invocations, the file table, and the IAM grammar note live there. This
skill does **not** repeat those commands; it captures the operational gotchas
that the README does not make obvious, the ones that actually cost time in a
real deployment. Read the README first, then use this skill as the "what will
bite you" companion.

## Prerequisites

- AWS CLI v2 and Docker installed locally. Repo root is the Docker build
  context (the `Dockerfile` lives at repo root).
- The one-time IAM setup in `deploy/aws/README.md` **section 1** already done
  by an **admin** identity (root or an admin IAM user). Day-to-day deploys do
  **not** need admin.
- An S3 results bucket and a Fargate Spot compute environment + queue (README
  sections 4–5).

## Devin Secrets Needed

- **`devin-bootstrap` access key** — the only long-lived credential. It has
  **exactly one** permission (`sts:AssumeRole` on `picard-deploy-role`) and is
  useless without the `ExternalId`. Store it under a `~/.aws/credentials`
  `[devin-bootstrap]` profile and reference it through the `~/.aws/config`
  `[profile picard]` block (`role_arn` + `source_profile = devin-bootstrap` +
  `external_id`), which auto-assumes `picard-deploy-role` and auto-refreshes the
  short-lived (≤1h) creds. **Every** ECR/Batch/S3 command runs with
  `--profile picard` (or `AWS_PROFILE=picard`).
- The **one-time IAM setup** (README section 1) needs a separate **admin**
  identity — `devin-bootstrap` cannot create users/roles.
- No secrets go into the container: it uses `picard-campaign-job-role` via the
  boto3 ambient credential chain.

## Identity / role model

Three distinct identities — do not confuse them:

| Identity | Creds | Can do | Used for |
|----------|-------|--------|----------|
| **admin** (root or admin IAM user) | admin | everything | one-time IAM setup only (README §1); IAM re-application; EC2 discovery |
| **`devin-bootstrap`** (IAM user) | long-lived keys | **only** `sts:AssumeRole` | source profile that `picard` assumes from |
| **`picard` profile** → `picard-deploy-role` | short-lived (≤1h), needs `ExternalId` | ECR + Batch + S3 + Logs + PassRole | all deploy actions |
| **`picard-campaign-job-role`** | ambient, in-container | S3 write to `campaign/*` | the running container (boto3) — no keys in image |

**CloudShell runs under your console-login (admin) identity.** That makes it
the easiest place to run the **privileged EC2 discovery** (subnet / security
group lookups) and any **IAM re-application**, because neither
`devin-bootstrap` nor `picard-deploy-role` has `ec2:Describe*` by default. When
a step needs describe/IAM perms it does not have, do it in CloudShell rather
than granting the deploy role more power.

## Windows PowerShell vs bash (major friction source)

The README is written in bash. If you deploy from **Windows PowerShell**, its
constructs do **not** translate:

- The README's `render()` is a **bash `sed` function** and `$(...)` is **bash
  command substitution** — neither exists in PowerShell. Use a PowerShell
  `Render` equivalent with chained single-line `.Replace()` calls, write to a
  temp file, and pass `file://<path>` to the CLI:

  ```powershell
  function Render($file, $out) {
    (Get-Content -Raw $file).Replace('<ACCOUNT_ID>', $env:ACCOUNT_ID).Replace('<REGION>', $env:REGION).Replace('<BUCKET>', $env:BUCKET).Replace('<EXTERNAL_ID>', $env:EXTERNAL_ID) | Set-Content -NoNewline $out
  }
  Render deploy_role_permissions_policy.json $env:TEMP\deploy-perms.json
  aws --profile picard iam put-role-policy --role-name picard-deploy-role --policy-name picard-deploy-permissions --policy-document file://$env:TEMP\deploy-perms.json
  ```

  **Warn:** backtick line-continuation combined with `-replace` breaks easily
  when pasted (the backtick is fragile and `-replace` treats its pattern as a
  regex, so `.` etc. are special). Prefer a **single-line `.Replace()` chain** —
  `.Replace()` is literal and needs no escaping.

- Use `$env:REGION` / `$env:BUCKET` / `$env:ACCOUNT_ID` / `$env:ECR` in
  PowerShell, **not** bash `$REGION`. A bash-style `$REGION` expands to empty in
  PowerShell, producing a malformed ECR endpoint with a **double dot** like
  `https://api.ecr..amazonaws.com`. Confirm `$env:REGION` is set before any ECR
  login.
- **Remove trailing `|| true`** from README commands — that is bash-only and is
  a syntax error in PowerShell (e.g. the `ecr create-repository ... || true`
  line). Just run the command and ignore an "already exists" error.
- **Prefer single-line commands.** Multi-line inline JSON and multi-line
  JMESPath `--query` expressions repeatedly garbled/failed when pasted into the
  user's shells. Put JSON in a file and pass `file://...`; keep `--query` on one
  line.

## IAM policy grammar

Every IAM policy/trust JSON may contain **only** the top-level keys `Version`,
`Id`, `Statement`. Adding a `Comment` (or any other top-level key) causes
`MalformedPolicyDocument` — *"Syntax errors in policy."* This is already
documented in the **IAM policy grammar** note in `deploy/aws/README.md`
(the blockquote after the file table); the per-file explanations live in that
README table, not inside the JSON. `batch_job_definition.json` is exempt (it is
a Batch input, not an IAM document).

## Credentials file gotcha

- `~/.aws/credentials` does **not** support inline `#` comments on the same
  line as a value. A trailing comment gets parsed **into** the secret, so any
  signed call (even `aws sts get-caller-identity`) fails with:
  `IncompleteSignature ... Invalid key=value pair (missing equal-sign) in
  Authorization header`. **Fix:** strip all inline comments — put comments on
  their own line or delete them.

  ```ini
  [devin-bootstrap]
  aws_access_key_id = AKIA...
  aws_secret_access_key = ...          # <-- this trailing comment breaks signing
  ```

- **`AccessKeysPerUser` quota is 2.** To rotate the bootstrap key you must
  delete one first:

  ```bash
  aws iam list-access-keys --user-name devin-bootstrap
  aws iam delete-access-key --user-name devin-bootstrap --access-key-id AKIA...
  aws iam create-access-key --user-name devin-bootstrap
  ```

## Build / push

- `docker build -t picard-campaign .` **requires the trailing `.`** (the build
  context). Omitting it yields `"docker build" requires exactly 1 argument`.
  The `Dockerfile` is at the **repo root**, so build from there.
- Validate locally before pushing: `docker run --rm picard-campaign --smoke`.
- Push follows README §3 (ECR login + tag + push). In PowerShell drop the
  `|| true` on `ecr create-repository`.

## Job definition

Fixes below **should already be committed** in
`deploy/aws/batch_job_definition.json` — verify they are present before
re-registering:

- **`evaluateOnExit` restricted characters.** A leading-asterisk pattern like
  `"*Spot*"` and uppercase actions `RETRY`/`EXIT` cause
  `ClientException: Evaluate on exit condition contains restricted characters`.
  Use **lowercase** `retry`/`exit` and **no leading asterisks**. Fargate Spot
  reclaim arrives as exit **137** with
  `statusReason: "Your Spot Task was interrupted."` — match Spot **before**
  the bare exit-137 OOM rule:

  ```json
  "evaluateOnExit": [
    { "onStatusReason": "Your Spot Task was interrupted*", "action": "retry" },
    { "onReason": "OutOfMemoryError*", "action": "exit" },
    { "onExitCode": "137", "action": "exit" },
    { "onExitCode": "0", "action": "exit" },
    { "onReason": "*", "action": "retry" }
  ]
  ```

  (Max **five** rules. This stack is Fargate Spot only, so omit `Host EC2*`.)
  Keep OOM (`137` / `OutOfMemoryError*`) on **exit** so memory kills stay
  countable via `classify_batch_failures.py`; Spot interrupt still retries.


- **Fargate resource sizing.** Two layers: (1) **subprocess-per-run** stops
  cumulative RSS growth across a shard; (2) **campaign compact history**
  (`run.history_retention=compact`) stops within-run telemetry from growing
  linearly with epochs; (3) default **1 vCPU / 2048 MB** with per-run
  `--timeout 3600` (old 600s cap was too short for ~30 min 7000-agent runs).
  The runner logs `RESOURCE peak_rss_kb=…` and writes `{run_id}.resource.json`
  / `{run_id}.failure.json`. OOM (exit 137 / `OutOfMemoryError*`) **exits
  without retry** so memory kills are countable via
  `deploy/aws/classify_batch_failures.py`. Escalate 1/4096 → 1/8192 → 2/16384
  → 4/30720 if OOM rate is non-zero. See README "Container sizing".

- **Revision pinning.** `submit-job --job-definition picard-campaign` uses the
  **latest ACTIVE revision at submit time**. So **register the new revision
  BEFORE submitting**, or pin explicitly with `picard-campaign:<REV>`. Confirm
  what the running job actually used:

  ```bash
  # revision + sizing the running job is using
  aws --profile picard batch describe-jobs --jobs <jobId> --region us-east-1 --query "jobs[0].jobDefinition"
  aws --profile picard batch describe-job-definitions --job-definition-name picard-campaign --status ACTIVE --region us-east-1 --query "jobDefinitions[-1].[revision,containerProperties.resourceRequirements]"
  ```

- **Job queue may be missing.** Inventory has seen `picard-campaign-spot` CE
  VALID while `picard-campaign-queue` was absent. Recreate the queue (README
  §5) before submit.
## CloudWatch log group (must exist BEFORE submit)

The **execution role** can create log *streams* and put events but **cannot
create the log group**. If `/aws/batch/picard-campaign` does not exist, **every**
array child fails at startup with:
`ResourceInitializationError ... ResourceNotFoundException: The specified log
group does not exist` (exit status 1). Create it **once** before README step 6:

```bash
aws logs create-log-group --log-group-name /aws/batch/picard-campaign --region us-east-1
```

## Compute environment timing

- `create-compute-environment` **returns immediately** but the environment sits
  in `status: CREATING`. `create-job-queue` then fails with
  *"Compute Environment ... is not valid"* until it reaches `VALID`. **Poll
  until `VALID`/`ENABLED` before creating the queue:**

  ```bash
  aws --profile picard batch describe-compute-environments --compute-environments picard-campaign-spot --region us-east-1 --query "computeEnvironments[0].[status,state]"
  ```

- If `create-compute-environment` complains about a **missing service-linked
  role**, create it once (needs an identity with `iam:CreateServiceLinkedRole`):

  ```bash
  aws iam create-service-linked-role --aws-service-name batch.amazonaws.com
  ```

- **Subnet / SG discovery needs `ec2:DescribeSubnets` / `ec2:DescribeSecurityGroups`,
  which `picard-deploy-role` lacks by default.** Either run discovery in
  **CloudShell (admin)** or add EC2 describe perms to the deploy role (an
  `Ec2Discovery` statement is included in `deploy_role_permissions_policy.json`).
  When querying, `--query` must **precede** the JMESPath expression, else the
  CLI tries to parse `Subnets[].SubnetId` as another `--filters` value:

  ```bash
  aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-xxxx --query "Subnets[].SubnetId" --output text
  aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxx --query "SecurityGroups[].GroupId" --output text
  ```

## Monitoring

- Prefer `deploy/aws/monitor_campaign.ps1 -JobId … -Prefix campaign/<name>/ -Watch`
  on Windows. It requires `-Bucket` / `CAMPAIGN_BUCKET`, or a local
  `deploy/aws/.env` copied from `.env.example` (auto-loaded; never commit it).
- Single-line status poll with a UTC timestamp prefix and trailing newline:

  ```bash
  aws batch describe-jobs --jobs <jobId> --region us-east-1 --query "jobs[0].arrayProperties.statusSummary" --output json | tr -d '\n' | sed "s/^/$(date -u +%Y-%m-%dT%H:%M:%SZ) /"; echo
  ```

- **RUNNING↔RUNNABLE bouncing on FARGATE_SPOT is normal** — it is Spot reclaim
  followed by Batch retry. Because of `--resume` + `completed_runs.txt` under
  `s3://<bucket>/campaign/_resume/`, a retried child **skips runs already
  completed** in its shard, so retries are cheap.
- **Distinguish reclaim from OOM.** After or during a campaign:

  ```bash
  AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \
    --job-id <jobId> --region us-east-1 \
    --out-json failure_report.json
  ```

  Compare `jobs_with_spot_reclaim` vs `jobs_with_oom`. OOM attempts exit
  without retry (job def `evaluateOnExit`), so they stay visible as FAILED.
- **`SUCCEEDED` stays 0 for a while.** A child is `SUCCEEDED` only when its
  **entire shard** finishes. Shard zips and manifests are refreshed
  **continuously** well before any child flips to SUCCEEDED — watch resume-log
  line counts, not just `statusSummary`, for early progress.
- **Resume must download.** On `--resume` with `--s3-prefix`, the runner pulls
  `_resume/completed_runs.shard-<i>.txt` plus the shard zip and manifest from S3
  before skipping — uploads alone do not seed a fresh Spot container.
- Terminal progress can be counted from the resume logs:

  ```bash
  aws s3 sync s3://$BUCKET/$PREFIX/_resume/ ./_resume/ && cat ./_resume/completed_runs.shard-*.txt | wc -l
  ```
- Inspect a failed child:

  ```bash
  aws --profile picard batch list-jobs --array-job-id <jobId> --job-status FAILED --region us-east-1
  aws --profile picard batch describe-jobs --jobs <childJobId> --region us-east-1 --query "jobs[0].statusReason"
  # then pull its logs (log stream name is in the child's container.logStreamName)
  aws logs get-log-events --log-group-name /aws/batch/picard-campaign --log-stream-name <stream> --region us-east-1
  ```
## Results back to local → edison

Run from the **LOCAL** machine under `--profile picard` — that is where the
files are needed for the downstream edison upload:

```bash
aws --profile picard s3 sync s3://<bucket>/campaign/ ./results/
python3 deploy/aws/aggregate_results.py ./results/ --out-csv campaign_summary.csv --out-json campaign_summary.json
```

`aggregate_results.py` reads nested run artifacts from each shard zip plus
shard manifests, and flattens `summary` / `cost_accounting` / `derived` into
one row per run. For stacked epidemic curves / OA–immunity frontiers use
`deploy/aws/analyze_campaign_curves.py`.

## Illustrative campaign parameters

Do **not** commit real account IDs, bucket names, ExternalIds, or access keys.
Use placeholders (or env vars) only — examples of the *shape*:

- region `<REGION>` (e.g. `us-east-1`)
- bucket `<BUCKET>`
- account `<ACCOUNT_ID>`
- `--shard-count 200` over ~17780 runs (~89 runs / shard)

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `IncompleteSignature ... Invalid key=value pair (missing equal-sign) in Authorization header` on any signed call | Inline `#` comment on a value line in `~/.aws/credentials` was parsed into the secret. Strip all inline comments. |
| `MalformedPolicyDocument` / "Syntax errors in policy" | A non-`Version`/`Id`/`Statement` top-level key (often `Comment`) in an IAM JSON. Remove it. |
| `https://api.ecr..amazonaws.com` (double dot) at ECR login | `$REGION` empty — in PowerShell use `$env:REGION`, not bash `$REGION`. |
| `"docker build" requires exactly 1 argument` | Missing trailing `.` (build context) in `docker build -t picard-campaign .`. |
| `ClientException: Evaluate on exit condition contains restricted characters` | Uppercase `RETRY`/`EXIT` or a leading-asterisk pattern in `evaluateOnExit`. Use lowercase actions and no leading `*`. |
| Array children exit **137** / `OutOfMemoryError: container killed due to memory usage` | Confirm subprocess isolation (no `--in-process`). Run `classify_batch_failures.py`. Escalate from 1/2048 → 1/4096 → 1/8192 → 2/16384. Re-register a new revision, then resubmit. |
| Spot retry re-runs already-finished sims | Resume log not downloaded. Ensure `--resume --s3-prefix …` and that `_resume/completed_runs.shard-*.txt` uploads succeeded. |
| Every child fails startup: `ResourceInitializationError ... ResourceNotFoundException: The specified log group does not exist` | `/aws/batch/picard-campaign` missing. `aws logs create-log-group --log-group-name /aws/batch/picard-campaign` once before submit. |
| `create-job-queue` → "Compute Environment ... is not valid" | Environment still `CREATING`. Poll `describe-compute-environments` until `VALID`/`ENABLED`. |
| `create-compute-environment` complains about a missing service-linked role | `aws iam create-service-linked-role --aws-service-name batch.amazonaws.com` once. |
| `ec2 describe-subnets`/`describe-security-groups` AccessDenied | `picard-deploy-role` lacks `ec2:Describe*` — run in CloudShell (admin) or use the `Ec2Discovery` statement in the deploy role policy. Also ensure `--query` precedes the JMESPath expression. |
| Submitted job used the wrong sizing / revision | `submit-job` uses the latest ACTIVE revision at submit time. Register the fixed revision first, or pin `picard-campaign:<REV>`. |
| `PowerShell` command errors on `|| true` | bash-only; delete the `|| true` tail. |

## See also

- `deploy/aws/README.md` — canonical commands, file table, IAM grammar note.
- `picard_framework/runs/mega_cruise_campaign/clock_arm_c1_v1_manifest.json`
  — focused C1 VSP refit manifest. Submit it twice with
  `CLOCK=hours` and `CLOCK=legacy_epoch_day` using distinct S3 prefixes
  (for example `campaign/clock_hours/` and `campaign/clock_legacy/`).
  The arms intentionally share run IDs, so a shared prefix would interleave
  models and make the second arm look complete to resume. The shell submitter
  and default job definition have no `--tier`; use a dedicated manifest or
  `submit_campaign_manifest.ps1 -Tier` for a single-tier submission.
  Keep Stan and Sentinel inference off the Spot queue; only independent
  checkpointed simulation tiers belong there.
- `deploy/aws/ensure_campaign_infra.sh` — recreate missing queue/log group +
  register current job def; optional `--smoke-submit N`.
- `deploy/aws/submit_boundary_surface.ps1` — boundary_surface_v1 Spot array.
- `deploy/aws/ensure_analysis_infra.ps1` / `submit_boundary_analysis.ps1` —
  On-Demand surface/Stan/MC (see `.agents/skills/boundary-aws-pipeline`).
- `deploy/aws/classify_batch_failures.py` — Spot reclaim vs OOM vs timeout.
- `.agents/skills/orchestrator-smoke-test/SKILL.md` — local smoke of the sim loop.
- `.agents/skills/adding-new-platform/SKILL.md` — platform data (`mega_cruise_5000`).
- `docs/boundary_aws_pipeline_lessons.md` — light validation, Spot vs On-Demand.
