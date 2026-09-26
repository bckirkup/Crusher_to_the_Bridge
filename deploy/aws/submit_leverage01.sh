#!/usr/bin/env bash
# Submit the LEVERAGE-01 endpoint-perturbation matrix as an AWS Batch array.
# Array size = len(enumerate_runs(design)) (346 on the v1 design). Child i
# owns runs[i] and uploads its record under S3_PREFIX/<channel>/. A synced
# prefix resumes cleanly: an existing record means the point is done.
set -euo pipefail

USAGE="usage: submit_leverage01.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-leverage01}"

S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/leverage01/}"
JOB_NAME="${JOB_NAME:-picard-leverage01-$(date +%Y%m%d-%H%M%S)}"
ARRAY_SIZE="${ARRAY_SIZE:?set ARRAY_SIZE to the enumerate_runs count (346 for design v1)}"

echo "Submitting leverage01 array:"
echo "  name        : $JOB_NAME"
echo "  array size  : $ARRAY_SIZE"
echo "  queue       : $JOB_QUEUE"
echo "  job def     : $JOB_DEFINITION"
echo "  s3 prefix   : $S3_PREFIX"

PARAMETERS=$(printf '{"s3_prefix":"%s"}' "$S3_PREFIX")

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
