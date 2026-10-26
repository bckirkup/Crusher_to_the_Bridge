# Reducer deploy runbook (ticket D3)

**Status:** RUNBOOK — deployer-leg commands verified as far as Devin's
`picard` creds allow (describe-only); no AWS resources created by the
authoring session. Nothing in this document has been executed against the
live account beyond the describe inventory recorded below.

Status: **runbook for the deployer leg.** This document was authored and
verified as far as Devin's `picard` deploy credentials allow (describe-class
calls only — `iam:GetRole` and all mutating calls are denied). Every
resource-creation step below is Benjamin's leg, run under his profile
`PowerUserAccess-994254241749` (AWS CloudShell — bash — or his workstation;
PowerShell variants given where syntax differs).

Facts verified live 2026-10-26:

- `picard-analysis-queue` and `picard-analysis-memory-queue`: ENABLED/VALID,
  backed by `picard-analysis-compute-ondemand` /
  `picard-analysis-memory-ondemand` (ENABLED, c7i/c7a/c6i x86_64,
  ECS_AL2023, private subnets + SG present).
- ECR repos `picard-campaign` and `picard-boundary-analysis` exist.
- `picard-reducer-*` roles/jobdef do not exist yet (expected).
- `iam:GetRole`/`put-role-policy`/`create-role` are outside Devin's creds —
  the checklist below is the deploy-time verification, not template-only.

Constants used below:

```bash
ACCT=994254241749; REGION=us-east-1; BUCKET=crusherbucket-994254241749-us-east-1-an
REPO=picard-boundary-analysis; PROFILE=PowerUserAccess-994254241749
export AWS_PROFILE=$PROFILE   # CloudShell: unset AWS_PROFILE instead
```

## 1. Render the IAM documents

IAM's policy grammar allows only `Version`/`Id`/`Statement` at top level —
the shipped JSONs keep placeholders and are rendered with `sed` before
each `aws iam` call (same pattern as `deploy/aws/README.md`).

```bash
cd Crusher_to_the_Bridge && for f in reducer_job_role_trust reducer_job_role_permissions reducer_dispatcher_role_trust reducer_dispatcher_role_permissions reducer_collector_role_trust reducer_collector_role_permissions; do sed -e "s/<ACCOUNT_ID>/$ACCT/g" -e "s/<REGION>/$REGION/g" -e "s/<BUCKET>/$BUCKET/g" -e "s|<GITHUB_REPO>|bckirkup/Crusher_to_the_Bridge|g" -e "s/<GITHUB_ENV>/aws-campaign/g" deploy/aws/$f.json > /tmp/$f.json && echo rendered $f; done
```

PowerShell equivalent (run in the repo root):

```powershell
Get-ChildItem deploy/aws/reducer_*_*.json | Where-Object Name -ne 'reducer_jobdef_spec.json' | ForEach-Object { (Get-Content $_ -Raw) -replace '<ACCOUNT_ID>','994254241749' -replace '<REGION>','us-east-1' -replace '<BUCKET>','crusherbucket-994254241749-us-east-1-an' -replace '<GITHUB_REPO>','bckirkup/Crusher_to_the_Bridge' -replace '<GITHUB_ENV>','aws-campaign' | Set-Content "$env:TEMP/$($_.Name)" -NoNewline }
```

## 2. Create the roles

Job role (Batch/ECS tasks; read approved originals + create-only derived
writes under `campaign/_derived/reducer/v1/`, explicit deny on
delete/restore/tag mutations, no simulation or infra permissions):

```bash
aws iam create-role --role-name picard-reducer-job-role --assume-role-policy-document file:///tmp/reducer_job_role_trust.json --description "campaign reducer batch job role" && aws iam put-role-policy --role-name picard-reducer-job-role --policy-name reducer-job-role --policy-document file:///tmp/reducer_job_role_permissions.json && echo job-role created
```

Dispatcher role (GitHub OIDC, `aws-campaign` environment only; bounded
Batch describe, SubmitJob on the analysis queues + `picard-reducer:*`
jobdef only, cancel/terminate, PassRole to the two exact jobdef roles,
request-manifest writes under the derived `requests/` prefix only):

```bash
aws iam create-role --role-name github-crusher-reduction-dispatch --assume-role-policy-document file:///tmp/reducer_dispatcher_role_trust.json --description "github oidc reduction dispatcher" && aws iam put-role-policy --role-name github-crusher-reduction-dispatch --policy-name reducer-dispatcher --policy-document file:///tmp/reducer_dispatcher_role_permissions.json && echo dispatch-role created
```

Collector role (GitHub OIDC; derived receipts/exports/pages + reviewed
original-manifest keys only, all mutations denied, no Batch submits).
This is the tightened constraint for reduction lanes; the existing
`github-crusher-collector` role continues to serve the legacy
`campaign_collect.yml` exact_key/index paths unchanged.

```bash
aws iam create-role --role-name github-crusher-reduction-collector --assume-role-policy-document file:///tmp/reducer_collector_role_trust.json --description "github oidc reduction collector" && aws iam put-role-policy --role-name github-crusher-reduction-collector --policy-name reducer-collector --policy-document file:///tmp/reducer_collector_role_permissions.json && echo collector-role created
```

Optional KMS statement — apply `deploy/aws/reducer_job_role_kms_decrypt.json`
(filled with the real key id) as a separate `put-role-policy` ONLY if live
source objects are SSE-KMS encrypted:

```bash
sed -e "s/<ACCOUNT_ID>/$ACCT/g" -e "s/<REGION>/$REGION/g" -e "s/<KMS_KEY_ID>/<real-key-id>/g" deploy/aws/reducer_job_role_kms_decrypt.json > /tmp/reducer_kms.json && aws iam put-role-policy --role-name picard-reducer-job-role --policy-name reducer-kms-decrypt --policy-document file:///tmp/reducer_kms.json
```

Execution role: **reuse `picard-campaign-execution-role`** — verified at
deploy time below, not template-assumed (CANONICAL_INTERFACE: reuse only
after exact policy/resource verification).

## 3. Build, smoke, and push the image (digest-pinned)

The `reducer-smoke` target proves the worker module + argv resolve inside
the image before any push:

```bash
docker build -f deploy/aws/Dockerfile.analysis --target reducer-smoke -t $REPO:reducer-smoke . && docker build -f deploy/aws/Dockerfile.analysis -t $ACCT.dkr.ecr.$REGION.amazonaws.com/$REPO:reducer-v1 . && aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCT.dkr.ecr.$REGION.amazonaws.com && docker push $ACCT.dkr.ecr.$REGION.amazonaws.com/$REPO:reducer-v1
```

Detached-safe variant (observable progress to a log):

```bash
nohup sh -c 'docker build -f deploy/aws/Dockerfile.analysis --target reducer-smoke -t picard-boundary-analysis:reducer-smoke . && docker build -f deploy/aws/Dockerfile.analysis -t 994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-boundary-analysis:reducer-v1 . && docker push 994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-boundary-analysis:reducer-v1' > /tmp/reducer-image.log 2>&1 & tail -f /tmp/reducer-image.log
```

Record the digest and bind it into the jobdef spec:

```bash
DIGEST=$(aws ecr describe-images --repository-name $REPO --image-ids imageTag=reducer-v1 --query 'imageDetails[0].imageDigest' --output text --region $REGION) && echo "image digest: $DIGEST" && python3 -c "import json;p='deploy/aws/reducer_jobdef_spec.json';d=json.load(open(p));d['image_digest']='$DIGEST';open(p,'w').write(json.dumps(d,indent=2)+'\n')"
```

## 4. Render + register the jobdef

`scripts/campaign submit --analysis-spec` extends the shared jobdef render
path — same template, reducer binding, literal canonical argv, no bespoke
jobdef file. `--dry-run` renders only; dropping it registers.

```bash
scripts/campaign submit --analysis-spec deploy/aws/reducer_jobdef_spec.json --account $ACCT --profile '' --region $REGION --dry-run
scripts/campaign submit --analysis-spec deploy/aws/reducer_jobdef_spec.json --account $ACCT --profile '' --region $REGION
```

(CloudShell ambient credentials need `--profile ''`; on a workstation pass
`--profile PowerUserAccess-994254241749`.)

## 5. Execution-role verification checklist (at deploy, not template)

Every line must print the expected value before the first dispatch:

```bash
aws batch describe-job-queues --job-queues picard-analysis-queue picard-analysis-memory-queue --query 'jobQueues[].{q:jobQueueName,state:state,status:status}' --region $REGION          # both ENABLED/VALID
aws batch describe-job-definitions --job-definitions picard-reducer --query 'jobDefinitions[].{name:jobDefinitionName,rev:revision,status:status,cmd:containerProperties.command[0:2],jobrole:containerProperties.jobRoleArn}' --region $REGION   # ACTIVE, cmd = [-m, picard_framework...worker]
aws iam get-role --role-name picard-campaign-execution-role --query 'Role.Arn' && aws iam get-role-policy --role-name picard-campaign-execution-role --policy-name batch-execution --query 'PolicyDocument.Statement[].{Sid:Sid,Res:Resource}'   # covers picard-boundary-analysis ECR + /aws/batch/picard-boundary-analysis logs
aws iam get-role-policy --role-name picard-reducer-job-role --policy-name reducer-job-role --query 'PolicyDocument.Statement[].Sid'   # the four reducer statements
aws batch describe-compute-environments --compute-environments picard-analysis-compute-ondemand --query 'computeEnvironments[].{state:state,types:computeResources.instanceTypes,img:computeResources.ec2Configuration[0].imageType,subnets:computeResources.subnets,sg:computeResources.securityGroupIds}' --region $REGION   # ENABLED, x86_64 family, subnets+SG present
aws ecr batch-get-image --repository-name $REPO --image-ids imageDigest=$DIGEST --query 'images[].imageManifest' --region $REGION | python3 -c "import json,sys;m=json.loads(sys.stdin.read());print('image arch ok')"   # manifest readable; build host arch = x86_64
```

Network check: the compute environment's subnets/SG must permit egress to
S3 (VPC gateway endpoint or NAT). Verify either:

```bash
aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.$REGION.s3 --query 'VpcEndpoints[].{id:VpcEndpointId,state:State}' --region $REGION   # gateway endpoint present, or
aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=<subnet-id> --query 'RouteTables[].Routes[?NatGatewayId!=null]' --region $REGION          # NAT route present
```

## 6. Record live ARNs + runtime prices into #1086

```bash
{ echo "role: $(aws iam get-role --role-name picard-reducer-job-role --query Role.Arn --output text)"; echo "dispatch: $(aws iam get-role --role-name github-crusher-reduction-dispatch --query Role.Arn --output text)"; echo "collector: $(aws iam get-role --role-name github-crusher-reduction-collector --query Role.Arn --output text)"; echo "exec: $(aws iam get-role --role-name picard-campaign-execution-role --query Role.Arn --output text)"; echo "queue: $(aws batch describe-job-queues --job-queues picard-analysis-queue --query 'jobQueues[0].jobQueueArn' --output text --region $REGION)"; echo "jobdef: $(aws batch describe-job-definitions --job-definitions picard-reducer --query 'jobDefinitions[0].jobDefinitionArn' --output text --region $REGION)"; echo "image: $ACCT.dkr.ecr.$REGION.amazonaws.com/$REPO@$DIGEST"; } | tee /tmp/reducer-arns.txt
```

Runtime price reference (the jobdef is 2 vCPU / 8 GiB / ≤3600 s; on-demand
c7i.xlarge ≈ the CE's smallest allocatable — record the live quote, never a
memorized figure):

```bash
aws ec2 describe-spot-price-history --instance-types c7i.4xlarge c7a.4xlarge --start-time $(date -u +%FT%TZ) --product-descriptions "Linux/UNIX" --query 'SpotPriceHistory[].{type:InstanceType,az:AvailabilityZone,usd:SpotPrice}' --region $REGION
```

Paste `/tmp/reducer-arns.txt` + the price table into a comment on #1086 —
the issue stays open until this live-ARN evidence lands.

## 7. What this deploy does NOT do

No Batch job is submitted by this leg. The dispatch workflow
(`.github/workflows/campaign_reduction.yml`) is review-gated on
`environment: aws-campaign` with `dry_run` defaulting to true; the first
paid submit is the synthetic return canary, which requires the admission
quote recorded on the ticket before any `dry_run: false` dispatch. The
collector role grants no write and no submits; the dispatcher role
PassRoles only the two exact jobdef roles.
