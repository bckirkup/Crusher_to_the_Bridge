# AWS Batch (Fargate Spot) deployment — mega cruise campaign

Package the ~9080-run mega cruise campaign
(`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`) as a Docker
image in Amazon ECR and run it as a single **AWS Batch array job** across many
short-lived **Fargate Spot** containers. Each array child executes a disjoint
shard of the run list and uploads every per-run result zip to one shared S3
prefix. Interrupted Spot containers resume from `completed_runs.txt` on retry.

```
                    ┌──────────────────── AWS Batch array job (size N) ────────────────────┐
 docker image  ──►  │  child 0            child 1            …            child N-1         │
 in ECR            │  --shard-index 0    --shard-index 1                 --shard-index N-1  │
                   │  (from AWS_BATCH_JOB_ARRAY_INDEX, --shard-count N each)                │
                    └───────────────────────────────┬──────────────────────────────────────┘
                                                     ▼
                                     s3://<bucket>/campaign/<run_id>.zip
                                     s3://<bucket>/campaign/_resume/completed_runs.shard-*.txt
                                                     ▼
                        aws s3 sync  ──►  ./results/  ──►  aggregate_results.py  ──►  CSV/JSON
```

Files in this directory:

| File | Role |
|------|------|
| `batch_job_definition.json` | Fargate Spot Batch job definition (ECR image, roles, vCPU/mem, shard/s3 command) |
| `iam_policy.json` | Least-privilege IAM policy (ECR, S3, Batch, Logs, PassRole) |
| `submit_array_job.sh` | Wrapper around `aws batch submit-job --array-properties size=<N>` |
| `aggregate_results.py` | Unzip `<run_id>.zip` under `./results/`, merge `summary.json` into one CSV/JSON |

Replace `<ACCOUNT_ID>`, `<REGION>`, and `<BUCKET>` placeholders throughout.

## 0. Prerequisites

- AWS CLI v2, Docker, and credentials with the permissions in `iam_policy.json`.
- An S3 bucket for results.
- A Batch **Fargate Spot** compute environment + job queue (see step 4).
- Two IAM roles (see step 5):
  - **execution role** (`picard-campaign-execution-role`) — lets Fargate pull the
    image and write logs (`AmazonECSTaskExecutionRolePolicy`).
  - **job role** (`picard-campaign-job-role`) — the container's own identity;
    needs the S3 object permissions from `iam_policy.json`.

```bash
export REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUCKET=my-campaign-bucket
export ECR=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/picard-campaign
```

## 1. Build the image

From the repo root (the `Dockerfile` lives there):

```bash
docker build -t picard-campaign .

# Validate locally with the built-in fast smoke path:
docker run --rm picard-campaign --smoke
```

## 2. Push to ECR

```bash
aws ecr create-repository --repository-name picard-campaign --region "$REGION" || true

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker tag picard-campaign:latest "$ECR:latest"
docker push "$ECR:latest"
```

## 3. Register the Batch job definition

Edit `batch_job_definition.json` to substitute `<ACCOUNT_ID>`, `<REGION>`,
`<BUCKET>` (or template it with `sed`), then register:

```bash
sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
    -e "s/<REGION>/$REGION/g" \
    -e "s#<BUCKET>#$BUCKET#g" \
    batch_job_definition.json > /tmp/picard-campaign-jobdef.json

aws batch register-job-definition \
  --cli-input-json file:///tmp/picard-campaign-jobdef.json \
  --region "$REGION"
```

The command is `--shard-count <N> --s3-prefix s3://<bucket>/campaign/ --resume`.
`--shard-index` is **not** passed — the runner reads `AWS_BATCH_JOB_ARRAY_INDEX`,
which Batch injects into every array child, so child *i* runs shard *i*.

## 4. Compute environment + job queue (one-time)

Create a Fargate **Spot** compute environment and a queue pointing at it
(replace subnets / security groups):

```bash
aws batch create-compute-environment \
  --compute-environment-name picard-campaign-spot \
  --type MANAGED --state ENABLED \
  --compute-resources '{
    "type":"FARGATE_SPOT","maxvCpus":256,
    "subnets":["subnet-xxxx"],"securityGroupIds":["sg-xxxx"]
  }' --region "$REGION"

aws batch create-job-queue \
  --job-queue-name picard-campaign-queue \
  --state ENABLED --priority 1 \
  --compute-environment-order order=1,computeEnvironment=picard-campaign-spot \
  --region "$REGION"
```

## 5. Submit the array job

```bash
./submit_array_job.sh 200 "s3://$BUCKET/campaign/" picard-campaign-queue picard-campaign
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
`s3://<bucket>/campaign/_resume/`).

Monitor:

```bash
aws batch describe-jobs --jobs <jobId> --region "$REGION" \
  --query 'jobs[0].arrayProperties.statusSummary'
```

## 6. Collect + aggregate results

```bash
aws s3 sync "s3://$BUCKET/campaign/" ./results/
python3 aggregate_results.py ./results/ \
  --out-csv campaign_summary.csv --out-json campaign_summary.json
```

`aggregate_results.py` unzips every `<run_id>.zip`, reads its `summary.json`,
and flattens the `summary` / `cost_accounting` blocks into one row per run.
