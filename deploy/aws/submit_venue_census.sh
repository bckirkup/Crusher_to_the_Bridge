#!/usr/bin/env bash
# Submit one NORO-VENUE-01/02 placement-census cell block as an AWS
# Batch EC2 Spot array. NORO-VENUE-02 adds the ESCORT_DELAY_HOURS arm
# (order->admission delay; 0 = instant-admission baseline) and the
# _k<delay> cell-label suffix.
#
# One submission per cell block: child i runs the tier run whose
# run.random_seed equals SEEDS[i] through venue_census_entrypoint and
# uploads one run zip per cell under
# S3_PREFIX/<cell_label>/<run_id>.zip, where cell_label is PLATFORM_ID
# when set (classic/mega post-mutations share the spirit tier) else TIER.
# The zip carries summary.json in the campaign layout plus venue.json.gz
# with the emesis x confinement join, per-host timelines, confinement
# events and zone classification.
#
# Canary runs are single (non-array) jobs whose container override
# passes --index <flat cell index>; the array-index env var is reserved
# on Batch.
set -euo pipefail

USAGE="usage: submit_venue_census.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-venue-census}"

TIER="${TIER:-fl_spr_12d}"
SEEDS="${SEEDS:-8105,8114,8124,8129,8132,8135,8137,8148,8156,8158,8159,8106}"
PLATFORM_ID="${PLATFORM_ID:-}"
NUM_AGENTS="${NUM_AGENTS:-0}"
ESCORT_DELAY_HOURS="${ESCORT_DELAY_HOURS:-1}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_dose_refit_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_venue_02/}"
CELL_LABEL="${PLATFORM_ID:-$TIER}_k${ESCORT_DELAY_HOURS}"
JOB_NAME="${JOB_NAME:-picard-venue-census-${CELL_LABEL}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

# Array size is the seed count; the entrypoint resolves each seed to the
# tier's run index itself.
ARRAY_SIZE="$(awk -F',' '{print NF}' <<<"$SEEDS")"

echo "Submitting venue census array:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  tier        : $TIER"
echo "  seeds       : $SEEDS (array size $ARRAY_SIZE)"
echo "  platform_id : ${PLATFORM_ID:-<tier default>}"
echo "  num_agents  : $NUM_AGENTS"
echo "  escort k    : $ESCORT_DELAY_HOURS"
echo "  cell label  : $CELL_LABEL"
echo "  pathogen    : $PATHOGEN_ID"
echo "  prefix      : $S3_PREFIX"
echo "  queue       : $JOB_QUEUE"
echo "  jobdef      : $JOB_DEFINITION"

aws batch submit-job \
  --region "$AWS_REGION" \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "{\"size\": $ARRAY_SIZE}" \
  --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,tier=$TIER,seeds=$SEEDS,platform_id=$PLATFORM_ID,num_agents=$NUM_AGENTS,escort_delay_hours=$ESCORT_DELAY_HOURS"
