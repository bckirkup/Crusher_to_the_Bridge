# AWS Batch (Fargate Spot) deployment — mega cruise campaign

Package the ~9080-run mega cruise campaign
(`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`) as a Docker
image in Amazon ECR and run it as a single **AWS Batch array job** across many
short-lived **Fargate Spot** containers. Each array child executes a disjoint
shard of the run list and uploads every per-run result zip to one shared S3
prefix. Interrupted Spot containers resume from `completed_runs.txt` on retry.

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
                                     s3://<bucket>/campaign/<run_id>.zip
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
- **Running containers (runtime side):** each Fargate task gets its identity
  from two Batch roles — an **execution role** (image pull + logs) and a **job
  role** (S3 write). boto3 in `campaign_runner.py` reads the job role
  automatically from the ambient credential chain; no keys are baked into the
  image.

## Files in this directory

| File | Role |
|------|------|
| `bootstrap_user_policy.json` | Policy for the `devin-bootstrap` IAM user — allows **only** `sts:AssumeRole` on the deploy role |
| `deploy_role_trust_policy.json` | Trust policy for `picard-deploy-role` — bootstrap user principal + `sts:ExternalId` condition |
| `deploy_role_permissions_policy.json` | Least-privilege ECR + S3 + Batch + Logs + `iam:PassRole` policy attached to `picard-deploy-role` |
| `batch_execution_role_trust.json` | Trust policy for the Batch **execution** role (`ecs-tasks.amazonaws.com`) |
| `batch_execution_role_permissions.json` | ECR pull + logs for the execution role |
| `batch_job_role_trust.json` | Trust policy for the Batch **job** role (`ecs-tasks.amazonaws.com`) |
| `batch_job_role_permissions.json` | S3 write to `campaign/*` for the job role (container identity) |
| `batch_job_definition.json` | Fargate Spot Batch job definition (ECR image, both role ARNs, vCPU/mem, shard/s3 command) |
| `submit_array_job.sh` | Wrapper around `aws batch submit-job --array-properties size=<N>` (honors `AWS_PROFILE`) |
| `aggregate_results.py` | Unzip `<run_id>.zip` under `./results/`, merge `summary.json` into one CSV/JSON |

Replace `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>`, and `<EXTERNAL_ID>` placeholders
throughout.

## 0. Prerequisites

- AWS CLI v2 and Docker.
- Admin (or an equivalently privileged user) to perform the one-time IAM setup
  in step 1. After that, day-to-day deploys need only the `devin-bootstrap`
  credentials.
- An S3 bucket for results.
- A Batch **Fargate Spot** compute environment + job queue (see step 4).

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
# Execution role — Fargate agent pulls the image and writes logs.
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

The command is `--shard-count <N> --s3-prefix s3://<bucket>/campaign/ --resume`.
`--shard-index` is **not** passed — the runner reads `AWS_BATCH_JOB_ARRAY_INDEX`,
which Batch injects into every array child, so child *i* runs shard *i*.

## 5. Compute environment + job queue (one-time)

Create a Fargate **Spot** compute environment and a queue pointing at it
(replace subnets / security groups):

```bash
aws --profile picard batch create-compute-environment \
  --compute-environment-name picard-campaign-spot \
  --type MANAGED --state ENABLED \
  --compute-resources '{
    "type":"FARGATE_SPOT","maxvCpus":256,
    "subnets":["subnet-xxxx"],"securityGroupIds":["sg-xxxx"]
  }' --region "$REGION"

aws --profile picard batch create-job-queue \
  --job-queue-name picard-campaign-queue \
  --state ENABLED --priority 1 \
  --compute-environment-order order=1,computeEnvironment=picard-campaign-spot \
  --region "$REGION"
```

## 6. Submit the array job

```bash
AWS_PROFILE=picard ./submit_array_job.sh 200 "s3://$BUCKET/campaign/" picard-campaign-queue picard-campaign
```

This submits one array job of 200 children. Each child runs:

```
campaign_runner.py --shard-count 200 \
    --shard-index $AWS_BATCH_JOB_ARRAY_INDEX \
    --s3-prefix s3://<bucket>/campaign/ --resume
```

so the ~9080 runs are split into 200 disjoint shards (~46 runs each). On Spot
interruption Batch retries the child; `--resume` skips run_ids already in the
shard's `completed_runs.txt` (uploaded periodically to
`s3://<bucket>/campaign/_resume/`). Inside the container, boto3 uses the
**picard-campaign-job-role** automatically — no keys in the image.

Monitor:

```bash
aws --profile picard batch describe-jobs --jobs <jobId> --region "$REGION" \
  --query 'jobs[0].arrayProperties.statusSummary'
```

## 7. Collect + aggregate results

```bash
aws --profile picard s3 sync "s3://$BUCKET/campaign/" ./results/
python3 aggregate_results.py ./results/ \
  --out-csv campaign_summary.csv --out-json campaign_summary.json
```

`aggregate_results.py` unzips every `<run_id>.zip`, reads its `summary.json`,
and flattens the `summary` / `cost_accounting` blocks into one row per run.

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
