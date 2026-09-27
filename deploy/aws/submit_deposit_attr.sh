#!/usr/bin/env bash
# Submit the NORO-DEPOSIT-ATTR-01 arm grid as an AWS Batch EC2 Spot array:
# one child per (arm, seed) cell of tools/noro_diag/deposit_attr_trace.py's
# ARMS at the fl_spr_12d paired seeds. Each child uploads its gzipped dump
# under S3_PREFIX/arm_<arm>/; the attribution table is assembled locally
# after `aws s3 sync` and a synced prefix resumes cleanly because a child's
# dump existing in S3 means its cell is done.
set -euo pipefail

USAGE="usage: submit_deposit_attr.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-deposit-attr}"

SEEDS="${SEEDS:-8105,8106}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/deposit_attr_01/}"
JOB_NAME="${JOB_NAME:-picard-deposit-attr-$(date +%Y%m%d-%H%M%S)}"

# 7 arms x the paired seeds (base + 6 ablations).
SEED_COUNT=$(awk -F, '{print NF}' <<<"$SEEDS")
ARM_COUNT=7
ARRAY_SIZE=$(( ARM_COUNT * SEED_COUNT ))

echo "Submitting deposit-attribution array:"
echo "  name      : $JOB_NAME"
echo "  seeds     : $SEEDS"
echo "  array     : $ARRAY_SIZE = $ARM_COUNT arms x $SEED_COUNT seeds"
echo "  queue     : $JOB_QUEUE"
echo "  s3 prefix : $S3_PREFIX"

PARAMETERS=$(printf '{"s3_prefix":"%s","seeds":"%s"}' \
  "$S3_PREFIX" "$SEEDS")

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
