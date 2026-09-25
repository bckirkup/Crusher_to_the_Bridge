#!/usr/bin/env bash
# Submit one per-host dose-challenge block as an AWS Batch EC2 Spot array.
# The array is 3 x SEED_COUNT children: child i runs seed
# SEED_BASE + (i % SEED_COUNT) under arm ARMS[i // SEED_COUNT]
# (per_surface_areal, per_surface_declared, pooled) and uploads its own
# .json.gz dump under S3_PREFIX/arm_<tag>/. The coincidence readout runs
# locally after `aws s3 sync`; a synced prefix resumes cleanly because a
# child's dump existing in S3 means its cell is done.
set -euo pipefail

USAGE="usage: submit_dose_challenge.sh <seed-count> <bucket> [region] [queue] [job-definition]"
SEED_COUNT="${1:?$USAGE}"
BUCKET="${2:?$USAGE}"
AWS_REGION="${3:-us-east-1}"
JOB_QUEUE="${4:-picard-campaign-queue}"
JOB_DEFINITION="${5:-picard-dose-challenge}"

# Cell parameters come from the environment, not from this script: they are
# the arguments the local block used, so a Batch cell and a local cell are
# the same run at the same seed.
SEED_BASE="${SEED_BASE:-8020}"
PLATFORM="${PLATFORM:-spirit_cruise_3000}"
BUNDLE="${BUNDLE:-norwalk_only}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
EPOCHS="${EPOCHS:-168}"
TOUCH_SHARE_TABLE="${TOUCH_SHARE_TABLE:-data/config/fomite_touch_share_declared.json}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/touch_share_rate_01/}"
JOB_NAME="${JOB_NAME:-picard-dose-challenge-$(date +%Y%m%d-%H%M%S)}"

ARRAY_SIZE=$(( 3 * SEED_COUNT ))

echo "Submitting dose-challenge array:"
echo "  name        : $JOB_NAME"
echo "  platform    : $PLATFORM"
echo "  bundle      : $BUNDLE"
echo "  pathogen    : $PATHOGEN_ID"
echo "  epochs      : $EPOCHS"
echo "  seed base   : $SEED_BASE"
echo "  seed count  : $SEED_COUNT (array size $ARRAY_SIZE = 3 arms x seeds)"
echo "  queue       : $JOB_QUEUE"
echo "  s3 prefix   : $S3_PREFIX"

PARAMETERS=$(printf '{"s3_prefix":"%s","seed_count":"%s","seed_base":"%s","platform":"%s","bundle":"%s","pathogen_id":"%s","epochs":"%s","touch_share_table":"%s"}' \
  "$S3_PREFIX" "$SEED_COUNT" "$SEED_BASE" "$PLATFORM" "$BUNDLE" "$PATHOGEN_ID" "$EPOCHS" "$TOUCH_SHARE_TABLE")

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
