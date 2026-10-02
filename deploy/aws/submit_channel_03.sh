#!/usr/bin/env bash
# Submit one NORO-CHANNEL-03 cell as an AWS Batch array.
#
# One submission per (tier, match) cell: child i runs the tier's spec
# whose run_id contains every MATCH token at seeds[i] through
# observation_channel_funnel.py and uploads
# S3_PREFIX/<tier>/<matchtag>/observation_channel_funnel_<arm>_seed<S>.json.gz.
#
# Required env: TIER (manifest tier id), MATCH (comma-joined run_id
# substrings, e.g. "rung-shipped,bp32p5c18p5"), SEEDS (comma-joined
# seed list; array size = seed count).
set -euo pipefail

USAGE="usage: submit_channel_03.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-noro-channel-03}"

TIER="${TIER:?'set TIER to a manifest tier id (e.g. fl_exp_12d_scr)'}"
MATCH="${MATCH:?'set MATCH to comma-joined run_id substrings (e.g. rung-shipped,bp32p5c18p5)'}"
SEEDS="${SEEDS:?'set SEEDS to a comma-joined seed list (array size = count)'}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_outbreak_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_channel_03/}"
JOB_NAME="${JOB_NAME:-picard-chan3-${TIER}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

# Comma-joined SEEDS -> count; single seed -> non-array job with --index 0.
SIZE="$(awk -F',' '{print NF}' <<<"${SEEDS}")"

echo "Submitting channel-03 funnel array:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  tier        : $TIER"
echo "  match       : $MATCH"
echo "  seeds       : $SEEDS ($SIZE)"
echo "  pathogen    : $PATHOGEN_ID"
echo "  prefix      : $S3_PREFIX"
echo "  queue       : $JOB_QUEUE"
echo "  jobdef      : $JOB_DEFINITION"

if [ "$SIZE" -le 1 ]; then
  # Non-array job: the array-index env var is reserved on Batch, so the
  # run index travels as a parameter the entrypoint reads via --index.
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,tier=$TIER,match=$MATCH,seeds=$SEEDS,index=0"
else
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --array-properties "{\"size\": $SIZE}" \
    --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,tier=$TIER,match=$MATCH,seeds=$SEEDS,index_offset=0"
fi
