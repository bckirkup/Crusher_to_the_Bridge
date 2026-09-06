# AWS Batch (EC2 Spot) deployment — mega cruise campaign

Package the ~17,780-run mega cruise campaign
(`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`) as a Docker
image in Amazon ECR and run it as a single **AWS Batch array job** across many
short-lived **EC2 Spot** containers on a scale-to-zero compute environment. Each array child executes a disjoint
shard of the run list and uploads one periodically refreshed fused zip plus one
JSON manifest per shard to one shared S3 prefix. Interrupted Spot containers
resume from the shard artifacts and `completed_runs.txt` on retry (the runner
downloads them from S3 at start).

This deployment uses **IAM role assumption (short-lived credentials)** — there
are **no long-lived access keys** in the deploy path beyond a single minimal
bootstrap user that can do nothing except assume a deploy role:

```
 devin-bootstrap (IAM user)          ── only sts:AssumeRole on ↓ ──►  picard-deploy-role
   long-lived keys, zero perms                                       (ECR + Batch + S3 + PassRole)
   ~/.aws/config profile "picard"  ── auto-assume w/ ExternalId ──►   short-lived creds (<=1h)
                                                                              │
                                        docker login / push, register job def, submit array job
                                                                              ▼
                    ┌──────────────────── AWS Batch array job (size N) ────────────────────┐
 docker image  ──►  │  child 0            child 1            …            child N-1         │
 in ECR            │  --shard-index 0    --shard-index 1                 --shard-index N-1  │
                   │  (from AWS_BATCH_JOB_ARRAY_INDEX, --shard-count N each)                │
                   │  identity = picard-campaign-job-role  (S3 write via boto3 chain)       │
                    └───────────────────────────────┬──────────────────────────────────────┘
                                                     ▼
                                     s3://<bucket>/campaign/shard-3.zip
                                     s3://<bucket>/campaign/shard-3.manifest.json
                                     s3://<bucket>/campaign/_resume/completed_runs.shard-*.txt
                                                     ▼
                        aws s3 sync  ──►  ./results/  ──►  aggregate_results.py  ──►  CSV/JSON
```

Two credential contexts, both short-lived:

- **Devin / operator (deploy side):** never uses static keys directly. The
  `devin-bootstrap` user's only permission is `sts:AssumeRole` on
  `picard-deploy-role`. A `~/.aws/config` named profile (`picard`) makes the CLI
  auto-assume that role (supplying the `ExternalId`) and auto-refresh the
  temporary credentials, which expire in ≤1h (`MaxSessionDuration=3600`).
- **Running containers (runtime side):** each Batch task gets its identity
  from two Batch roles — an **execution role** (image pull + logs) and a **job
  role** (S3 write). boto3 in `campaign_runner.py` reads the job role
  automatically from the ambient credential chain; no keys are baked into the
  image.

## Files in this directory

| File | Role | Placeholders |
|------|------|--------------|
| `bootstrap_user_policy.json` | Permission policy for the long-lived `devin-bootstrap` IAM user. Its **only** permission is `sts:AssumeRole` on `picard-deploy-role`; all ECR/Batch/S3 access comes from the assumed role's short-lived credentials, never from this user. | `<ACCOUNT_ID>` |
| `deploy_role_trust_policy.json` | Trust policy for `picard-deploy-role`. Only the `devin-bootstrap` user may assume it, and only when it supplies the shared-secret `sts:ExternalId`. Pair with `MaxSessionDuration=3600` (set on the role via `create-role`, not in this document) so issued credentials are short-lived. | `<ACCOUNT_ID>`, `<EXTERNAL_ID>` |
| `deploy_role_permissions_policy.json` | Permission policy attached to `picard-deploy-role` — the role Devin assumes (with an `ExternalId`) to build/push the `picard-campaign` image and run it as an AWS Batch array job. Least-privilege ECR + S3 + Batch + Logs + read-only EC2 subnet/SG/VPC discovery + `iam:PassRole`. | `<REGION>`, `<ACCOUNT_ID>`, `<BUCKET>` |
| `batch_execution_role_trust.json` | Trust policy for `picard-campaign-execution-role`. Assumed by the ECS agent so it can pull the ECR image and write logs on behalf of the task. | *(none)* |
| `batch_execution_role_permissions.json` | Permission policy for the execution role (the ECS agent): pull the `picard-campaign` image from ECR and write container logs. Equivalent to the AWS-managed `AmazonECSTaskExecutionRolePolicy`, scoped to this repo/log group. | `<REGION>`, `<ACCOUNT_ID>` |
| `batch_job_role_trust.json` | Trust policy for `picard-campaign-job-role` — the running container's own identity (used by boto3's ambient credential chain to upload results to S3). Assumed by the ECS task. | *(none)* |
| `batch_job_role_permissions.json` | Permission policy for `picard-campaign-job-role` (the container's own identity). boto3 in `campaign_runner.py` picks this up from the ambient credential chain to upload shard zips, manifests, and resume logs to the shared results prefix. S3 write to `campaign/*`. | `<BUCKET>` |
| `batch_job_definition.json` | EC2 Spot Batch job definition (ECR image, both role ARNs, vCPU/mem, shard/s3 command). Sized at **1 vCPU / 2048 MB (2 GB)** after compact history + subprocess isolation. Per-run `--timeout 3600` covers ~30 min 7000-agent sims. OOM (exit 137 / `OutOfMemoryError*`) **exits without retry** so memory kills are countable; Spot `Host EC2*` still retries. Escalate 1/4 → 1/8 → 2/16 GB if `classify_batch_failures.py` shows non-zero OOM. **Not an IAM document.** | `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` |
| `submit_array_job.sh` | Wrapper around `aws batch submit-job --array-properties size=<N>` (honors `AWS_PROFILE`) | — |
| `classify_batch_failures.py` | Classify array-child attempts: Spot reclaim vs OOM vs timeout vs other. Write JSON/CSV; optional upload to `s3://…/campaign/_ops/`. | — |
| `monitor_campaign.ps1` | Windows-friendly poller: Batch `statusSummary` + completed-run count from shard resume logs (optional `-Watch` / `-Classify`). | — |
| `ensure_campaign_infra.sh` | Ensure the EC2 Spot scale-to-zero campaign CE + queue + log group and register the current job definition (`AWS_PROFILE=picard`). Optional `--smoke-submit N`. | `ACCOUNT_ID`, `REGION`, `BUCKET`, `SUBNET_IDS`, `SECURITY_GROUP_IDS` |
| `ensure_batch_pathways.py` | Shared CE/queue provisioner behind both ensure scripts: native EC2, `minvCpus`/`desiredvCpus` 0, instance types from `instance_pathways.json`. `--dry-run` prints the CE body without calling AWS. | — |
| `instance_pathways.json` | Instance families per pathway (`abm_campaign`, `analysis_compute`, `analysis_memory`) and architecture. | — |
| `submit_boundary_surface.ps1` | Submit `boundary_surface_v1` Spot array (`-Tier b2` / `-IncludeDeferred` via containerOverrides). | — |
| `submit_campaign_manifest.ps1` | Submit any mega-cruise manifest Spot array (synthetic recovery, VSP degradation, …). | — |
| `Dockerfile.analysis` | CmdStan analysis image for surface / Stan / MC (not Spot ABM). Must COPY crusher_labs + orchestrator deps; pin `CMDSTAN` to versioned install dir. | — |
| `boundary_analysis_entrypoint.py` | Analysis container entrypoint (`--phase surface\|stan\|mc\|report`). | — |
| `batch_job_definition_boundary_*.json` | EC2 job defs for surface / Stan / MC. | `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` |
| `ensure_analysis_infra.ps1` | Both analysis pathways (`picard-analysis-compute-ondemand` + `picard-analysis-queue`, `picard-analysis-memory-ondemand` + `picard-analysis-memory-queue`) + register analysis job defs. `-Capacity spot` for interruption-tolerant runs. | — |
| `submit_boundary_analysis.ps1` | Submit one analysis phase job. | — |
| `sentinel_nuts_entrypoint.py` | One AWS Batch array child for a Sentinel Engine C NUTS cell. | — |
| `batch_job_definition_sentinel_nuts.json` | EC2 NUTS ladder job definition using the existing analysis image and log group. | `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` |
| `submit_sentinel_nuts.sh` / `monitor_sentinel_nuts.sh` | Submit and monitor rung-scoped Sentinel NUTS arrays. | — |
| `Dockerfile.design` | Slim worker image for the bounded designs (Morris screen, feasibility gate): no CmdStan, `ENTRYPOINT ["python3"]` so the job definition names the script. Pushed as the `bounded-design-*` tag of the `picard-boundary-analysis` repository, which with `picard-campaign` is the only repository the deploy role may push to. | — |
| `bounded_design_entrypoint.py` | One array child of a bounded design (`--design screen\|region`). Shard index from `AWS_BATCH_JOB_ARRAY_INDEX`; skips work whose artifact is already in S3, and a gate shard resumes its own point stream from S3 after a Spot reclaim. | — |
| `batch_job_definition_bounded_design.json` | EC2 Spot job definition for the bounded designs (1 vCPU / 4096 MB, 10 attempts). | `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` |
| `submit_bounded_design.sh` | Submit one bounded design as a Spot array of `<shard-count>` children (`screen` or `region`); design size via `TRAJECTORIES` / `SOBOL_M` / `SEEDS` / `DESIGN_SEED`. Shards pool only through the design's own merge step. | — |
| `aggregate_results.py` | Read shard zips/manifests under `./results/`, merge one row per run into CSV/JSON | — |

Replace `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>`, and `<EXTERNAL_ID>` placeholders
throughout.

> **IAM policy grammar.** Every `*.json` above except `batch_job_definition.json`
> is an IAM policy or trust document. AWS IAM's policy grammar permits **only**
> the top-level keys `Version`, `Id`, and `Statement`; any other top-level key
> (e.g. a `Comment` annotation) makes `aws iam put-user-policy` /
> `put-role-policy` / `create-role --assume-role-policy-document` fail with
> `MalformedPolicyDocument` ("Syntax errors in policy"). These files therefore
> carry no top-level annotations — the per-file explanations live in the table
> above. Keep them that way; the `render`/`sed` pipeline only substitutes
> placeholder values and does not add or strip any keys. `batch_job_definition.json`
> is exempt because it is a Batch job definition, not an IAM document.

## 0. Prerequisites

- AWS CLI v2 and Docker.
- Admin (or an equivalently privileged user) to perform the one-time IAM setup
  in step 1. After that, day-to-day deploys need only the `devin-bootstrap`
  credentials.
- An S3 bucket for results.
- A Batch **EC2 Spot** compute environment + job queue (see step 4).

```bash
export REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUCKET=my-campaign-bucket
export EXTERNAL_ID=$(openssl rand -hex 16)   # shared secret for role assumption
export ECR=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/picard-campaign
```

## 1. One-time IAM setup (role-assumption model)

Run once by an admin. Every JSON file below is templated with `sed` to fill in
the placeholders.

### 1a. Bootstrap user + deploy role

```bash
render() { sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
               -e "s/<REGION>/$REGION/g" \
               -e "s#<BUCKET>#$BUCKET#g" \
               -e "s/<EXTERNAL_ID>/$EXTERNAL_ID/g" "$1"; }

# (a) Minimal bootstrap user — long-lived keys, but ZERO permissions
#     beyond assuming the deploy role.
aws iam create-user --user-name devin-bootstrap
aws iam put-user-policy --user-name devin-bootstrap \
  --policy-name assume-picard-deploy-role \
  --policy-document "$(render bootstrap_user_policy.json)"
aws iam create-access-key --user-name devin-bootstrap   # capture into ~/.aws/credentials

# (b) Deploy role: trust policy (bootstrap user + ExternalId) and the
#     ECR/Batch/S3/PassRole permission policy. MaxSessionDuration caps the
#     lifetime of every assumed-role credential set at 1 hour.
aws iam create-role --role-name picard-deploy-role \
  --assume-role-policy-document "$(render deploy_role_trust_policy.json)" \
  --max-session-duration 3600
aws iam put-role-policy --role-name picard-deploy-role \
  --policy-name picard-deploy-permissions \
  --policy-document "$(render deploy_role_permissions_policy.json)"
```

### 1b. Batch execution + job roles (container runtime identities)

```bash
# Execution role — the ECS agent pulls the image and writes logs.
aws iam create-role --role-name picard-campaign-execution-role \
  --assume-role-policy-document "$(render batch_execution_role_trust.json)"
aws iam put-role-policy --role-name picard-campaign-execution-role \
  --policy-name picard-campaign-execution-permissions \
  --policy-document "$(render batch_execution_role_permissions.json)"

# Job role — the container's own identity; boto3 uploads results to S3 with it.
aws iam create-role --role-name picard-campaign-job-role \
  --assume-role-policy-document "$(render batch_job_role_trust.json)"
aws iam put-role-policy --role-name picard-campaign-job-role \
  --policy-name picard-campaign-job-permissions \
  --policy-document "$(render batch_job_role_permissions.json)"
```

### 1c. `~/.aws/config` named profile (auto-assume + auto-refresh)

Give Devin (or CI) only the `devin-bootstrap` access key, stored as a
`source_profile`. The `picard` profile then assumes the deploy role on demand
and transparently refreshes the temporary credentials — you never handle the
role's short-lived keys yourself.

`~/.aws/credentials`:

```ini
[devin-bootstrap]
aws_access_key_id = AKIA...            # from `aws iam create-access-key` above
aws_secret_access_key = ...
```

`~/.aws/config`:

```ini
[profile picard]
role_arn = arn:aws:iam::<ACCOUNT_ID>:role/picard-deploy-role
source_profile = devin-bootstrap
external_id = <EXTERNAL_ID>
region = us-east-1
```

Verify assumption works (should print the assumed-role ARN, not the user):

```bash
aws --profile picard sts get-caller-identity
```

From here on, **every** `aws` / `docker login` command uses `--profile picard`
(or `export AWS_PROFILE=picard`), so all deploy actions run under short-lived
assumed-role credentials.

## 2. Build the image

From the repo root (the `Dockerfile` lives there):

```bash
docker build -t picard-campaign .

# Validate locally with the built-in fast smoke path:
docker run --rm picard-campaign --smoke
```

## 3. Push to ECR

```bash
aws --profile picard ecr create-repository --repository-name picard-campaign --region "$REGION" || true

aws --profile picard ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker tag picard-campaign:latest "$ECR:latest"
docker push "$ECR:latest"
```

## 4. Register the Batch job definition

Substitute placeholders and register (the job definition references both the
execution role and the job role by ARN):

```bash
sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
    -e "s/<REGION>/$REGION/g" \
    -e "s#<BUCKET>#$BUCKET#g" \
    batch_job_definition.json > /tmp/picard-campaign-jobdef.json

aws --profile picard batch register-job-definition \
  --cli-input-json file:///tmp/picard-campaign-jobdef.json \
  --region "$REGION"
```

The command is `--manifest <path> --shard-count <N> --s3-prefix s3://<bucket>/campaign/ --natural-history-clock hours --resume --timeout 3600`.
`--shard-index` is **not** passed — the runner reads `AWS_BATCH_JOB_ARRAY_INDEX`,
which Batch injects into every array child, so child *i* runs shard *i*.
`Ref::manifest` defaults to `campaign_manifest.json` (mega-cruise); pass
`calibration_manifest_v1.json` for the CDC calibration wave-1 matrix
(~2360 runs; deferred `c2` skipped). On Windows:
`.\deploy\aws\submit_calibration.ps1 -ShardCount 80`.

### Spot reclaim vs OOM (`evaluateOnExit`)

Spot interruptions often arrive as exit code **137** with
`statusReason: "Your Spot Task was interrupted."` — the same exit code as an
OOM kill. The job definition **must** match Spot status reasons **before** the
exit-137 / `OutOfMemoryError*` exit rules, or Batch will treat reclaim as a
permanent OOM and stop retrying. Current order:

1. `Host EC2*` → `retry` (EC2 Spot reclaim / instance loss; must precede exit-137)
2. `OutOfMemoryError*` → `exit` (countable, no retry)
3. exit `137` → `exit` (bare memory kill without reason text)
4. exit `0` → `exit`
5. `*` → `retry`

(AWS Batch allows at most **five** `evaluateOnExit` rules. On EC2, reclaim
arrives as `Host EC2 <instance-id> terminated`, so the Fargate-only
`Your Spot Task was interrupted*` rule was dropped for the `Host EC2*` one
rather than added alongside it.)

`attempts` is **10** so a shard can survive repeated Spot reclaim. `--resume`
still skips completed runs after each restart.

### Container sizing (vCPU / memory)

Two separate memory problems, two fixes:

1. **Cumulative RSS across many runs** — CPython/`pymalloc` does not return
   pages between in-process simulations. The campaign runner defaults to
   **subprocess-per-run** so the OS reclaims each child's RSS on exit and the
   parent stays small.
2. **Single-run peak** — without compact retention, full per-epoch telemetry
   (agents + contact tracing + raw assays + lab notebook) grew roughly
   linearly with epochs. Campaign specs now default to
   `run.history_retention=compact` (summary / spaces / cost only; lab
   notebook logging skipped). Peak RSS should then track live O(N) physics
   state. The job definition requests **1 vCPU / 2048 MB (2 GB)**. Earlier
   revisions used 1/4 GB (OOM) and 2/16 GB (safe but expensive). The runner
   records per-run `peak_rss_kb` (Linux `VmHWM`) into
   `{run_id}.resource.json` / CloudWatch `RESOURCE …` lines, and writes
   `{run_id}.failure.json` on failure. Use `--full-telemetry` only when you
   need the full history dump.

On EC2 the vCPU/memory pairs are free-form — Batch packs jobs onto an instance
until either dimension is exhausted, so `MEMORY` must stay under the
instance's ECS-available memory (roughly 1 GiB below its nominal size).
Escalation if `classify_batch_failures.py` reports OOM:

| Step | VCPU | MEMORY |
|------|------|--------|
| default | 1 | 2048 |
| +1 | 1 | 4096 |
| +2 | 1 | 8192 |
| +3 | 2 | 16384 |
| last resort | 4 | 30720 |

Keep an escalated `MEMORY` inside `instance_pathways.json`'s families: the
`abm_campaign` c-family gives 2 GiB per vCPU, so anything above that ratio
strands cores and belongs on the memory pathway instead.

### Account inventory notes (us-east-1)

As of the 1 vCPU / 2 GB resize work:

| Resource | Status |
|----------|--------|
| `picard-abm-campaign-spot` compute env | EC2 `SPOT`, `minvCpus: 0`, `maxvCpus: 256`. The retired `picard-campaign-spot` (`FARGATE_SPOT`) can be deleted once the queue points at the EC2 CE. |
| `picard-campaign-queue` | May be missing — recreate (step 5) before submit |
| `picard-campaign` job definition | Register a new revision from this JSON after each sizing/timeout change |
| Deploy identity | Use `--profile picard` (assumes `picard-deploy-role`). The `devin-bootstrap` user alone cannot call ECR/S3/Logs. |

### Result bookkeeping

Each shard zip packs many runs as `<run_id>/summary.json` and
`<run_id>/timeseries.json`; its manifest carries a structured `parameters`
block (tier, pathogen, seed, HVAC/OA/decay/surveillance/… factors) next to
outcomes.
`aggregate_results.py` flattens `parameters.*` into CSV columns so you do not
need to parse opaque run_ids or reopen `run_spec.json` / the manifest.

## 5. Compute environments + job queues (one-time)

Three pathways, all native EC2 at `minvCpus: 0` / `desiredvCpus: 0` — Batch
terminates the last instance a few minutes after a queue drains, so an idle
pathway costs nothing:

| Pathway | CE | Queue | Capacity | Instances |
|---------|----|-------|----------|-----------|
| ABM campaign shards | `picard-abm-campaign-spot` | `picard-campaign-queue` | Spot | c7i / c7a / c6i |
| Analysis, core-bound (Stan fits, MC, sentinel) | `picard-analysis-compute-ondemand` | `picard-analysis-queue` | On-Demand | c7i / c7a / c6i |
| Analysis, memory-bound (surface / bundle / report) | `picard-analysis-memory-ondemand` | `picard-analysis-memory-queue` | On-Demand | r7i / r7a / r6i |

Shards are interruption-tolerant (`--resume` plus 10 attempts), so they stay on
Spot. MCMC does not resume mid-chain, so the analysis pathways default to EC2
On-Demand — still far below the Fargate On-Demand rate they replace. Pass
`-Capacity spot` to `ensure_analysis_infra.ps1` for runs that can afford a
restart.

Both ensure scripts call `ensure_batch_pathways.py`, which reads the instance
families from `instance_pathways.json`, creates or aligns the CE, waits for
`VALID`, and points the queue at it:

```bash
export SUBNET_IDS=subnet-xxxx,subnet-yyyy SECURITY_GROUP_IDS=sg-xxxx
./deploy/aws/ensure_campaign_infra.sh          # campaign pathway + job def
python3 deploy/aws/ensure_batch_pathways.py \
  --pathway analysis_compute --queue picard-analysis-queue --dry-run
```

`--dry-run` prints the compute-environment body and calls no AWS API; use it to
review instance families before provisioning.

A CE cannot change capacity type in place. Repointing `picard-campaign-queue`
from the old `FARGATE_SPOT` CE to the EC2 CE is an `update-job-queue` (the
script does it); the Fargate CE must then be disabled and deleted separately,
and a queue can never hold both kinds at once.

EC2 compute environments also need an ECS instance profile (default
`ecsInstanceRole`, override with `--instance-profile`) and `iam:PassRole` on it
for the deploy role. CmdStan jobs that need more than the AMI's 30 GiB root
volume take a launch template: create it once in CloudShell and pass
`BATCH_LAUNCH_TEMPLATE` / `--launch-template`.

**`create-compute-environment` returns immediately, but the environment sits in
`status: CREATING`** — `create-job-queue` fails with *"Compute Environment ... is
not valid"* until it reaches `VALID`; `ensure_batch_pathways.py` polls for it.

```bash
aws --profile picard batch describe-compute-environments \
  --compute-environments picard-abm-campaign-spot --region "$REGION" \
  --query 'computeEnvironments[0].[status,state]'
```

If `create-compute-environment` reports a missing service-linked role, create it
once (needs `iam:CreateServiceLinkedRole`):

```bash
aws iam create-service-linked-role --aws-service-name batch.amazonaws.com
```

Subnet / security-group discovery needs `ec2:DescribeSubnets` /
`ec2:DescribeSecurityGroups`. `deploy_role_permissions_policy.json` grants these
(`Ec2Discovery`), or run discovery in **CloudShell** (admin). `--query` must
precede the JMESPath expression, else the CLI parses it as another `--filters`:

```bash
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-xxxx --query 'Subnets[].SubnetId' --output text
aws ec2 describe-security-groups --filters Name=vpc-id,Values=vpc-xxxx --query 'SecurityGroups[].GroupId' --output text
```

### Create the CloudWatch log group (before step 6)

The execution role can create log **streams** and put events but **cannot create
the log group**. If `/aws/batch/picard-campaign` does not exist, every array
child fails at startup with `ResourceInitializationError ...
ResourceNotFoundException: The specified log group does not exist` (exit status
1). Create it once:

```bash
aws logs create-log-group --log-group-name /aws/batch/picard-campaign --region "$REGION"
```


### One-shot ensure (queue + log group + register)

If the Spot compute environment already exists but the queue was deleted, or
after changing `batch_job_definition.json` sizing/timeout:

```bash
export AWS_PROFILE=picard REGION=us-east-1 ACCOUNT_ID=<ACCOUNT_ID> BUCKET=<bucket>
./ensure_campaign_infra.sh
# optional smoke array (size must be >= 2):
./ensure_campaign_infra.sh --smoke-submit 2
```

Then classify Spot vs OOM with `classify_batch_failures.py --recent 1`.

## 6. Submit the array job

```bash
AWS_PROFILE=picard ./submit_array_job.sh 200 "s3://$BUCKET/campaign/" picard-campaign-queue picard-campaign
```

### Paired natural-history clock arms

Submit the same calibration manifest twice, using distinct S3 prefixes and
clock arms. The runner leaves generated run IDs unchanged, records the
selected arm in each summary's `parameters.natural_history_clock`, and keeps
each arm's resume log independent:

```bash
AWS_PROFILE=picard CLOCK=hours ./submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/calibration_hours/" picard-campaign-queue \
  picard-campaign \
  picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json

AWS_PROFILE=picard CLOCK=legacy_epoch_day ./submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/calibration_legacy/" picard-campaign-queue \
  picard-campaign \
  picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json
```

The `clock` Batch parameter defaults to `hours`, preserving existing
submissions. A local output directory marked for one arm refuses a later
invocation requesting the other arm; invocations without the flag remain
backward-compatible and do not hard-fail on a marked directory.

The focused C1 VSP refit uses
`picard_framework/runs/mega_cruise_campaign/clock_arm_c1_v1_manifest.json`.
Submit its paired arms with the same array size and manifest, but never reuse
one prefix:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/clock_arm_c1_v1_manifest.json
AWS_PROFILE=picard CLOCK=hours ./submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/clock_hours/" picard-campaign-queue \
  picard-campaign "$MANIFEST"

AWS_PROFILE=picard CLOCK=legacy_epoch_day ./submit_array_job.sh 80 \
  "s3://$BUCKET/campaign/clock_legacy/" picard-campaign-queue \
  picard-campaign "$MANIFEST"
```

The two clock arms intentionally produce identical run IDs. They must use
different S3 prefixes: putting both arms under one prefix silently interleaves
different models into the same shard bundles, and the resume log causes the
second arm's IDs to be treated as already complete. The shipped
`submit_array_job.sh` and default job definition do not expose `--tier`; use a
dedicated single-tier manifest, or use `submit_campaign_manifest.ps1 -Tier`
with a container-command override. This Spot path is for independent,
per-shard-checkpointed simulation tiers only. Do not submit Stan or Sentinel
inference tiers to the Spot queue because those fits do not survive an
interruption.

### Current C1 reported-case hourly refit

The corrected-model norovirus refit uses
`picard_framework/runs/mega_cruise_campaign/c1_reported_case_refit_v1_manifest.json`.
It has four `c1_*` tiers at 720 runs each, for 2,880 runs total, with the
hourly clock, `dose_adjustment` 12.0–14.0 in 0.25 steps, `n_init=1`,
`none_true` and `syndromic`, and matched seeds 760–799:

```bash
MANIFEST=picard_framework/runs/mega_cruise_campaign/c1_reported_case_refit_v1_manifest.json
python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py \
  --manifest "$MANIFEST" --tier all --natural-history-clock hours --dry-run
```

Score the `syndromic` branch on cumulative reported symptomatic passenger
cases divided by the passenger complement. This is a reported-case endpoint,
not infections divided by the complement; `none_true` is the matched
counterfactual. The campaign is hourly-only, so do not submit a new
`legacy_epoch_day` arm. Keep the independent simulation tiers on the
checkpointed Spot path and do not send Stan inference to Spot.

The unflagged 200-shard command at the top of this section submits one array
job of 200 children. Each child runs:

```
campaign_runner.py --shard-count 200 \
    --shard-index $AWS_BATCH_JOB_ARRAY_INDEX \
    --s3-prefix s3://<bucket>/campaign/ --resume --timeout 3600
```

so the ~17,780 runs are split into 200 disjoint shards (~89 runs each). On Spot
interruption Batch retries the child; `--resume` **downloads** the shard's
`completed_runs.txt` from `s3://<bucket>/campaign/_resume/` at start, then
skips those run_ids listed in the shard resume log or manifest.
The log is also re-uploaded periodically. Inside the container, boto3 uses the
**picard-campaign-job-role** automatically — no keys in the image.

Monitor progress (PowerShell-friendly wrapper — prefer this on Windows):

```powershell
# Status + completed-run count every 60s (Ctrl+C to stop)
$env:AWS_PROFILE = 'picard'   # or your SSO PowerUser profile
$env:CAMPAIGN_BUCKET = '<BUCKET>'
.\deploy\aws\monitor_campaign.ps1 -JobId <jobId> `
  -Prefix campaign/<campaign_prefix>/ -Watch -IntervalSec 60

# Or copy deploy/aws/.env.example → deploy/aws/.env (gitignored);
# monitor_campaign.ps1 loads CAMPAIGN_BUCKET / AWS_PROFILE / AWS_REGION from it.
```

One-shot Batch status only:

```bash
aws --profile picard batch describe-jobs --jobs <jobId> --region "$REGION" \
  --query 'jobs[0].arrayProperties.statusSummary'
```

**What to watch (three signals, not one):**

| Signal | Why |
|--------|-----|
| `statusSummary` (RUNNING / RUNNABLE / SUCCEEDED / FAILED) | Shard-level only — a child is SUCCEEDED only when its **entire** shard finishes. Early progress looks like RUNNABLE↔RUNNING bounce with SUCCEEDED=0. |
| S3 resume-log line count | Terminal progress — completed run_ids are appended and uploaded periodically while shards are still RUNNING. |
| `classify_batch_failures.py` | Separates Spot reclaim from real OOM / timeout. |

Classify Spot reclaim vs OOM vs timeout (during or after the run):

```bash
AWS_PROFILE=picard python3 classify_batch_failures.py \
  --job-id <jobId> --region "$REGION" \
  --out-json failure_report.json --out-csv failure_attempts.csv \
  --s3-uri "s3://$BUCKET/campaign/_ops/failure_report_<jobId>.json"
```

`RUNNING`↔`RUNNABLE` bounce on EC2 Spot is normal reclaim + retry. Use the
classifier's `jobs_with_spot_reclaim` vs `jobs_with_oom` counts to separate
reclaim noise from real memory pressure. True OOM attempts **do not retry**
(job def exits on `OutOfMemoryError*` / bare exit 137 after Spot rules) so they
stay visible as FAILED children.

**Profiles:** day-to-day submit/monitor can use `--profile picard`
(`picard-deploy-role`). Use your SSO **PowerUser** (or admin) profile when you
need broader read/ops (S3 listing, Logs describe, recreating a deleted queue,
ECR create). Containers still run as `picard-campaign-job-role` either way.
Never commit real account IDs, bucket names, ExternalIds, or access keys —
keep them in env vars / `~/.aws/` only.
## 7. Collect + aggregate results

```bash
aws --profile picard s3 sync "s3://$BUCKET/campaign/" ./results/
python3 aggregate_results.py ./results/ \
  --out-csv campaign_summary.csv --out-json campaign_summary.json
```

`aggregate_results.py` reads each shard zip's nested run artifacts and any
shard manifests, then flattens the `summary` / `cost_accounting` /
`derived` blocks into one row per run (plus `timeseries.present` /
`timeseries.n_epochs`). For stacked epidemic curves see
`deploy/aws/analyze_campaign_curves.py`.

Terminal progress can be counted directly from the resume logs:

```bash
aws s3 sync s3://$BUCKET/$PREFIX/_resume/ ./_resume/ && cat ./_resume/completed_runs.shard-*.txt | wc -l
```

## Boundary surface campaign (`boundary_surface_v1`)

Multi-pathogen k-sweep for pre-boarding decision surfaces (10,000 Tier-1 runs;
7,600 deferred Tier-2). Full notes:
[`docs/boundary_aws_pipeline_lessons.md`](../docs/boundary_aws_pipeline_lessons.md).

**Light validation only** (do not full-matrix dry-run):

```bash
python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian \
  picard_framework/runs/mega_cruise_campaign/boundary_surface_v1_manifest.json
# expect wave1=10000 wave2=7600
python picard_framework/runs/mega_cruise_campaign/campaign_runner.py --smoke
```

**Phase 1 Spot** (rebuild image after manifest changes):

```powershell
docker build -t picard-campaign .
# ECR login/tag/push as in §3
# Re-register batch_job_definition.json if ACTIVE rev pins a stale tag (not :latest)
.\deploy\aws\submit_boundary_surface.ps1 -ShardCount 200
# Tier-2 deferred (same prefix; resume):
.\deploy\aws\submit_boundary_surface.ps1 -Tier b2 -ShardCount 200
```

**Phases 2–5 On-Demand** (separate CmdStan image — never on Spot ABM workers):

```powershell
docker build -f deploy/aws/Dockerfile.analysis -t picard-boundary-analysis .
# create ECR repo picard-boundary-analysis; push; re-apply execution-role policy
.\deploy\aws\ensure_analysis_infra.ps1   # needs SUBNET_IDS + SECURITY_GROUP_IDS in .env if CE missing
.\deploy\aws\submit_boundary_analysis.ps1 -Phase surface
.\deploy\aws\submit_boundary_analysis.ps1 -Phase bundle
.\deploy\aws\submit_boundary_analysis.ps1 -Phase stan -Pathogen norovirus
.\deploy\aws\submit_boundary_analysis.ps1 -Phase mc -Pathogen norovirus
```

**Sentinel recovery Stan** (72-cell array on the same On-Demand queue / CmdStan
image; extract must already be under
`campaign/sentinel_synthetic_recovery_v1/analysis/`):

```powershell
.\deploy\aws\ensure_analysis_infra.ps1 -RegisterOnly
.\deploy\aws\submit_sentinel_recovery_stan.ps1
.\deploy\aws\submit_sentinel_recovery_stan.ps1 -Phase score
```

Re-apply `batch_execution_role_permissions.json` so the execution role can pull
`picard-boundary-analysis` and write `/aws/batch/picard-boundary-analysis`.
Lived gotchas (stale job-def tags, `CMDSTAN` versioned path, analysis COPY
deps, `DescribeLogGroups` on `*`): `docs/boundary_aws_pipeline_lessons.md`.

**Sentinel Engine C NUTS ladder** (one array child per enumerated cell):

```bash
docker build -f deploy/aws/Dockerfile.analysis \
  -t picard-boundary-analysis:sentinel-nuts-v1 .
docker tag picard-boundary-analysis:sentinel-nuts-v1 \
  "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/picard-boundary-analysis:sentinel-nuts-v1"
docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/picard-boundary-analysis:sentinel-nuts-v1"

sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
    -e "s/<REGION>/$REGION/g" \
    -e "s#<BUCKET>#$BUCKET#g" \
    deploy/aws/batch_job_definition_sentinel_nuts.json \
    > /tmp/picard-sentinel-nuts-jobdef.json
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch register-job-definition \
  --cli-input-json file:///tmp/picard-sentinel-nuts-jobdef.json \
  --region "$REGION"

# Submit only the requested rung; C1 is 20 cells.
./deploy/aws/submit_sentinel_nuts.sh C1 "$BUCKET" "$REGION"
./deploy/aws/monitor_sentinel_nuts.sh <JOB_ID> "$BUCKET" "$REGION"
```

The submit script writes the auditable `cells_manifest.json` once, then the
entrypoint resolves `AWS_BATCH_JOB_ARRAY_INDEX` against
`enumerate_cells(load_ladder())`, optionally filtered to the requested rung
ids. Cell JSONs land under
`s3://$BUCKET/campaign/sentinel_nuts_ladder_v1/`. Existing cell keys are
skipped so Spot retries are idempotent. The image reuses the existing
`picard-boundary-analysis` ECR repository and
`/aws/batch/picard-boundary-analysis` log group; it does not create either.
Containers use only the ambient Batch job role and never receive operator
credentials.

## Why role assumption (vs. static keys)

- The only long-lived secret is the `devin-bootstrap` access key, and it can do
  **nothing** except `sts:AssumeRole` on one role — useless if leaked without
  the `ExternalId`.
- Every action that touches ECR/Batch/S3 runs under credentials that expire in
  ≤1h and are minted on demand by the CLI, then auto-refreshed.
- The `ExternalId` condition on the trust policy blocks the
  [confused-deputy](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)
  problem.
- Containers never see the deploy credentials at all; they carry only the
  narrowly-scoped job role (S3 write to `campaign/*`).

## Troubleshooting

- **Array child exits with code 137 / `OutOfMemoryError: container killed due to
  memory usage`.** Confirm the image uses subprocess-per-run (default; do not
  pass `--in-process` in Batch). Run `classify_batch_failures.py` — OOM attempts
  exit without retry so they appear as `FAILED` children. Raise `MEMORY` (and,
  if already at the max for the current `VCPU`, raise `VCPU` too) in
  `batch_job_definition.json`, then re-register a new revision:

  ```bash
  sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
      -e "s/<REGION>/$REGION/g" \
      -e "s#<BUCKET>#$BUCKET#g" \
      batch_job_definition.json > /tmp/picard-campaign-jobdef.json

  aws --profile picard batch register-job-definition \
    --cli-input-json file:///tmp/picard-campaign-jobdef.json \
    --region "$REGION"
  ```

  Escalation ladder from the default **1 vCPU / 2048 MB**: 1/4096 → 1/8192 →
  2/16384 → 4/30720. Check CloudWatch `RESOURCE peak_rss_kb=…` lines and
  `{run_id}.resource.json` sidecars before jumping more than one step.
  Resubmit against the new revision — `--resume` skips shards already
  completed, so retries are cheap.
