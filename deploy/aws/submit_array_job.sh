#!/usr/bin/env bash
# ============================================================================
#  submit_array_job.sh — submit a Picard campaign as an AWS Batch array
#  job of N Fargate Spot children, each running a disjoint shard.
#
#  Each array child receives AWS_BATCH_JOB_ARRAY_INDEX automatically; the
#  campaign runner uses it as --shard-index, so we only pass --shard-count
#  (equal to the array size), the shared --s3-prefix, and optional --manifest.
#
#  Credentials: uses the ambient AWS credential chain. Set AWS_PROFILE=picard
#  (the named profile in ~/.aws/config that auto-assumes picard-deploy-role with
#  its ExternalId — see README.md) so the CLI submits with short-lived
#  credentials rather than long-lived keys.
#
#  Usage:
#    AWS_PROFILE=picard ./submit_array_job.sh <N> <s3://bucket/campaign/> \
#      [job-queue] [job-definition] [manifest-path] [clock]
#
#  Env overrides:
#    JOB_NAME   — Batch job name (default picard-campaign-YYYYMMDD-HHMMSS)
#    MANIFEST   — in-image path to campaign JSON (overrides 5th arg)
#    CLOCK      — natural-history clock arm (default hours; overrides 6th arg)
#
#  Examples:
#    # Mega-cruise (~17780)
#    AWS_PROFILE=picard ./submit_array_job.sh 200 s3://my-bucket/campaign/
#
#    # Calibration wave-1 (~2360; c2 deferred)
#    AWS_PROFILE=picard ./submit_array_job.sh 80 \
#      s3://my-bucket/campaign/calibration_v1/ \
#      picard-campaign-queue picard-campaign \
#      picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json
# ============================================================================
set -euo pipefail

ARRAY_SIZE="${1:?usage: submit_array_job.sh <N> <s3-prefix> [queue] [job-def] [manifest]}"
S3_PREFIX="${2:?usage: submit_array_job.sh <N> <s3-prefix> [queue] [job-def] [manifest]}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-campaign}"
DEFAULT_MANIFEST="picard_framework/runs/mega_cruise_campaign/campaign_manifest.json"
MANIFEST="${MANIFEST:-${5:-$DEFAULT_MANIFEST}}"
CLOCK="${CLOCK:-${6:-hours}}"
JOB_NAME="${JOB_NAME:-picard-campaign-$(date +%Y%m%d-%H%M%S)}"
# Optional named profile that assumes picard-deploy-role (see README.md §2).
AWS_PROFILE_ARG=()
if [[ -n "${AWS_PROFILE:-}" ]]; then
  AWS_PROFILE_ARG=(--profile "$AWS_PROFILE")
fi

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
echo "  manifest    : $MANIFEST"
echo "  clock       : $CLOCK"

aws "${AWS_PROFILE_ARG[@]}" batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "shard_count=$ARRAY_SIZE,s3_prefix=$S3_PREFIX,manifest=$MANIFEST,clock=$CLOCK" \
  --query 'jobId' --output text
