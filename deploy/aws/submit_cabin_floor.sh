#!/usr/bin/env bash
# Submit the CABIN-FLOOR-01 roster as an AWS Batch EC2 Spot array: one child
# per (bundle, pathogen, seed) cell of tools/cabin_floor_probe.py's ROSTER at
# the classic_cruise_1900 paired seeds. Each child uploads its JSON dump under
# S3_PREFIX/arm_<bundle>__<pathogen_id>/; the verdict table is assembled
# locally after `aws s3 sync` and a synced prefix resumes cleanly because a
# child's dump existing in S3 means its cell is done.
set -euo pipefail

USAGE="usage: submit_cabin_floor.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-cabin-floor}"

PLATFORM="${PLATFORM:-classic_cruise_1900}"
EPOCHS="${EPOCHS:-288}"
SEEDS="${SEEDS:-8105,8106}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/cabin_floor_01/}"
JOB_NAME="${JOB_NAME:-picard-cabin-floor-$(date +%Y%m%d-%H%M%S)}"

# 13 roster arms x the paired seeds.
SEED_COUNT=$(awk -F, '{print NF}' <<<"$SEEDS")
ARM_COUNT=13
ARRAY_SIZE=$(( ARM_COUNT * SEED_COUNT ))

echo "Submitting cabin-floor array:"
echo "  name      : $JOB_NAME"
echo "  platform  : $PLATFORM"
echo "  epochs    : $EPOCHS"
echo "  seeds     : $SEEDS"
echo "  array     : $ARRAY_SIZE = $ARM_COUNT arms x $SEED_COUNT seeds"
echo "  queue     : $JOB_QUEUE"
echo "  s3 prefix : $S3_PREFIX"

PARAMETERS=$(printf '{"s3_prefix":"%s","seeds":"%s","platform":"%s","epochs":"%s"}' \
  "$S3_PREFIX" "$SEEDS" "$PLATFORM" "$EPOCHS")

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
