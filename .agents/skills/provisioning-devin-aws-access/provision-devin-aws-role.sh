#!/usr/bin/env bash
# Provision role-based AWS access for Devin for one project.
#
# Creates (idempotently):
#   <prefix>-devin        IAM user, long-lived keys, ONLY sts:AssumeRole on the role below
#   <prefix>-devin-role   the working role, scoped to <prefix>-* resources, ExternalId required
#
# Run this with an ADMIN identity (console CloudShell is easiest), never with
# Devin's own credentials.
#
#   EXTERNAL_ID=$(openssl rand -hex 32)
#   PREFIX=gutibm REGION=us-east-1 EXTERNAL_ID=$EXTERNAL_ID ./provision-devin-aws-role.sh
#
# Preview the policies without touching AWS:
#   PREFIX=gutibm RENDER_ONLY=1 EXTERNAL_ID=dummy ./provision-devin-aws-role.sh
#
# Capability switches (default 1 = granted, scoped to <prefix>-*):
#   WITH_BATCH WITH_ECR WITH_S3 WITH_LOGS
set -euo pipefail

PREFIX="${PREFIX:?PREFIX is required, e.g. PREFIX=gutibm}"
REGION="${REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
USER_NAME="${USER_NAME:-${PREFIX}-devin}"
ROLE_NAME="${ROLE_NAME:-${PREFIX}-devin-role}"
SESSION_HOURS="${SESSION_HOURS:-4}"
RENDER_ONLY="${RENDER_ONLY:-0}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
WITH_BATCH="${WITH_BATCH:-1}"
WITH_ECR="${WITH_ECR:-1}"
WITH_S3="${WITH_S3:-1}"
WITH_LOGS="${WITH_LOGS:-1}"
ECR_REPO="${ECR_REPO:-${PREFIX}-campaign}"

if [[ -z "${EXTERNAL_ID:-}" ]]; then
  echo "EXTERNAL_ID is required. Generate one with: openssl rand -hex 32" >&2
  exit 1
fi

if [[ "${RENDER_ONLY}" == "1" ]]; then
  ACCOUNT="${ACCOUNT:-000000000000}"
else
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
fi
echo "account=${ACCOUNT} region=${REGION} prefix=${PREFIX} out=${OUT_DIR}"

# IAM policy documents accept ONLY the top-level keys Version, Id, Statement.
# Any other key (a Comment, a note) fails with MalformedPolicyDocument.
cat > "${OUT_DIR}/user-assume-only.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeDevinRoleOnly",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::${ACCOUNT}:role/${ROLE_NAME}"
    }
  ]
}
JSON

cat > "${OUT_DIR}/role-trust.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::${ACCOUNT}:user/${USER_NAME}" },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": { "sts:ExternalId": "${EXTERNAL_ID}" }
      }
    }
  ]
}
JSON

statements=()
if [[ "${WITH_BATCH}" == "1" ]]; then
  statements+=("$(cat <<JSON
    {
      "Sid": "BatchReadOnly",
      "Effect": "Allow",
      "Action": ["batch:Describe*", "batch:List*", "ecs:DescribeContainerInstances", "ec2:DescribeInstances"],
      "Resource": "*"
    },
    {
      "Sid": "BatchSubmitToOwnQueuesOnly",
      "Effect": "Allow",
      "Action": "batch:SubmitJob",
      "Resource": [
        "arn:aws:batch:*:${ACCOUNT}:job-queue/${PREFIX}-*",
        "arn:aws:batch:*:${ACCOUNT}:job-definition/${PREFIX}-*"
      ]
    },
    {
      "Sid": "BatchManageOwnJobs",
      "Effect": "Allow",
      "Action": ["batch:TerminateJob", "batch:CancelJob"],
      "Resource": "arn:aws:batch:*:${ACCOUNT}:job/*"
    },
    {
      "Sid": "BatchRegisterOwnJobDefinitions",
      "Effect": "Allow",
      "Action": ["batch:RegisterJobDefinition", "batch:DeregisterJobDefinition"],
      "Resource": "arn:aws:batch:*:${ACCOUNT}:job-definition/${PREFIX}-*"
    },
    {
      "Sid": "PassBatchRolesToEcsTasksOnly",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::${ACCOUNT}:role/${PREFIX}-batch-job-role",
        "arn:aws:iam::${ACCOUNT}:role/${PREFIX}-batch-execution-role"
      ],
      "Condition": { "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" } }
    }
JSON
)")
fi
if [[ "${WITH_ECR}" == "1" ]]; then
  statements+=("$(cat <<JSON
    {
      "Sid": "EcrAuthTokenIsAccountWide",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "EcrPushPullOwnRepoOnly",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "arn:aws:ecr:*:${ACCOUNT}:repository/${ECR_REPO}"
    }
JSON
)")
fi
if [[ "${WITH_S3}" == "1" ]]; then
  statements+=("$(cat <<JSON
    {
      "Sid": "S3OwnBucketsOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::${PREFIX}-*", "arn:aws:s3:::${PREFIX}-*/*"]
    }
JSON
)")
fi
if [[ "${WITH_LOGS}" == "1" ]]; then
  statements+=("$(cat <<JSON
    {
      "Sid": "ReadJobLogs",
      "Effect": "Allow",
      "Action": ["logs:GetLogEvents", "logs:DescribeLogStreams", "logs:DescribeLogGroups"],
      "Resource": "arn:aws:logs:*:${ACCOUNT}:log-group:/aws/batch/*"
    }
JSON
)")
fi

{
  echo '{'
  echo '  "Version": "2012-10-17",'
  echo '  "Statement": ['
  for i in "${!statements[@]}"; do
    printf '%s' "${statements[$i]}"
    if (( i < ${#statements[@]} - 1 )); then echo ','; else echo; fi
  done
  echo '  ]'
  echo '}'
} > "${OUT_DIR}/role-permissions.json"

python3 -c 'import json,sys; [json.load(open(p)) for p in sys.argv[1:]]' \
  "${OUT_DIR}/user-assume-only.json" \
  "${OUT_DIR}/role-trust.json" \
  "${OUT_DIR}/role-permissions.json"
echo "rendered policies validated as JSON in ${OUT_DIR}"

if [[ "${RENDER_ONLY}" == "1" ]]; then
  cat "${OUT_DIR}/role-permissions.json"
  exit 0
fi

if ! aws iam get-user --user-name "${USER_NAME}" >/dev/null 2>&1; then
  echo "creating user ${USER_NAME}"
  aws iam create-user --user-name "${USER_NAME}" >/dev/null
fi
aws iam put-user-policy --user-name "${USER_NAME}" \
  --policy-name "${PREFIX}-devin-assume-only" \
  --policy-document "file://${OUT_DIR}/user-assume-only.json"

if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  echo "updating trust policy on ${ROLE_NAME}"
  aws iam update-assume-role-policy --role-name "${ROLE_NAME}" \
    --policy-document "file://${OUT_DIR}/role-trust.json"
  aws iam update-role --role-name "${ROLE_NAME}" \
    --max-session-duration "$((SESSION_HOURS * 3600))"
else
  echo "creating ${ROLE_NAME}"
  aws iam create-role --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${OUT_DIR}/role-trust.json" \
    --max-session-duration "$((SESSION_HOURS * 3600))" \
    --description "Scoped ${PREFIX} access assumed by ${USER_NAME}" >/dev/null
fi
aws iam put-role-policy --role-name "${ROLE_NAME}" \
  --policy-name "${PREFIX}-devin-permissions" \
  --policy-document "file://${OUT_DIR}/role-permissions.json"

echo
echo "inline policies on ${USER_NAME}:"
aws iam list-user-policies --user-name "${USER_NAME}" --output text
echo "managed policies still attached to ${USER_NAME} (detach anything broader than assume-role):"
aws iam list-attached-user-policies --user-name "${USER_NAME}" --output text
echo
echo "access keys on ${USER_NAME} (quota is 2, delete one before creating a new one):"
aws iam list-access-keys --user-name "${USER_NAME}" \
  --query 'AccessKeyMetadata[].[AccessKeyId,Status,CreateDate]' --output text
echo
UPPER="$(printf '%s' "${PREFIX}" | tr '[:lower:]-' '[:upper:]_')"
cat <<SUMMARY
Store these as Devin secrets:
  ${UPPER}_AWS_ROLE_ARN         arn:aws:iam::${ACCOUNT}:role/${ROLE_NAME}
  ${UPPER}_AWS_EXTERNAL_ID      the EXTERNAL_ID used above
  ${UPPER}_AWS_ACCESS_KEY_ID    from: aws iam create-access-key --user-name ${USER_NAME}
  ${UPPER}_AWS_SECRET_ACCESS_KEY
Region ${REGION} is not a secret; keep it in AWS_DEFAULT_REGION or the blueprint.
SUMMARY
