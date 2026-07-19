#!/usr/bin/env bash
# ============================================================================
#  submit_array_job.sh — submit the mega-cruise campaign as an AWS Batch
#  array job of N Fargate Spot children, each running a disjoint shard.
#
#  Each array child receives AWS_BATCH_JOB_ARRAY_INDEX automatically; the
#  campaign runner uses it as --shard-index, so we only pass --shard-count
#  (equal to the array size) and the shared --s3-prefix.
#
#  Usage:
#    ./submit_array_job.sh <N> <s3://bucket/campaign/> [job-queue] [job-definition]
#
#  Example:
#    ./submit_array_job.sh 200 s3://my-bucket/campaign/ picard-campaign-queue picard-campaign
# ============================================================================
set -euo pipefail

ARRAY_SIZE="${1:?usage: submit_array_job.sh <N> <s3-prefix> [queue] [job-def]}"
S3_PREFIX="${2:?usage: submit_array_job.sh <N> <s3-prefix> [queue] [job-def]}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-campaign}"
JOB_NAME="${JOB_NAME:-picard-campaign-$(date +%Y%m%d-%H%M%S)}"

if [[ "$ARRAY_SIZE" -lt 2 || "$ARRAY_SIZE" -gt 10000 ]]; then
  echo "ERROR: AWS Batch array size must be between 2 and 10000 (got $ARRAY_SIZE)." >&2
  exit 1
fi

echo "Submitting array job:"
echo "  name        : $JOB_NAME"
echo "  queue       : $JOB_QUEUE"
echo "  definition  : $JOB_DEFINITION"
echo "  array size  : $ARRAY_SIZE"
echo "  s3 prefix   : $S3_PREFIX"

aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "shard_count=$ARRAY_SIZE,s3_prefix=$S3_PREFIX" \
  --query 'jobId' --output text
