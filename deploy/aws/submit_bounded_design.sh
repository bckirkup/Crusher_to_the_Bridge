#!/usr/bin/env bash
# Submit one bounded design (Morris screen or feasibility gate) as an AWS Batch
# EC2 Spot array. The array size is the shard count: shard i evaluates the
# design units congruent to i, and the shards pool afterwards through the
# design's own merge step (bounded_screen.py --mode merge,
# admissible_region.py --merge). A shard is not a verdict.
#
# Size the array by wall-time, not by trajectory count: for the screen,
# SEED_SHARDS splits each trajectory's seed set into blocks, so
# shard-count = trajectory shards x SEED_SHARDS may approach the queue's
# vCPU ceiling (256). 20 trajectories x 30 seeds at SEED_SHARDS=10 gives
# 200 shards of 33 runs each (~15 min) instead of 20 shards of 330.
#
# For the gate, SEED_SHARDS does the same to a point's matched seed set, and a
# seed-sharded gate shard uploads rows rather than a scored cell: the merge
# pools a point's blocks and scores the whole cell, because A9 is a frequency
# over the matched seed set and a block of it is not a small cell.
# ONLY_POINTS="7,13,204" re-runs named indices of the same Sobol' grid at their
# own grid coordinates, which is how a region of the design is resolved more
# finely without moving any interval.
set -euo pipefail

USAGE="usage: submit_bounded_design.sh <screen|region> <shard-count> <bucket> [region] [queue] [job-definition]"
DESIGN="${1:?$USAGE}"
SHARD_COUNT="${2:?$USAGE}"
BUCKET="${3:?$USAGE}"
AWS_REGION="${4:-us-east-1}"
JOB_QUEUE="${5:-picard-campaign-queue}"
JOB_DEFINITION="${6:-picard-bounded-design}"

case "$DESIGN" in
  screen|region) ;;
  *) echo "$USAGE" >&2; exit 2 ;;
esac

# Design sizes come from the flags, not from this script: they are the
# arguments the local run used, so a Batch run and a local run are the same
# design at the same --design-seed.
TRAJECTORIES="${TRAJECTORIES:-20}"
SEED_SHARDS="${SEED_SHARDS:-1}"
ONLY_POINTS="${ONLY_POINTS:-}"
SOBOL_M="${SOBOL_M:-7}"
SEEDS="${SEEDS:-30}"
DESIGN_SEED="${DESIGN_SEED:-17}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/bounded_design_v1/}"
JOB_NAME="${JOB_NAME:-picard-bounded-${DESIGN}-$(date +%Y%m%d-%H%M%S)}"

echo "Submitting bounded design array:"
echo "  name         : $JOB_NAME"
echo "  design       : $DESIGN"
echo "  array size   : $SHARD_COUNT"
echo "  trajectories : $TRAJECTORIES (screen)"
echo "  seed shards  : $SEED_SHARDS"
echo "  only points  : ${ONLY_POINTS:-<whole grid>} (region)"
echo "  sobol m      : $SOBOL_M (region)"
echo "  seeds/point  : $SEEDS"
echo "  design seed  : $DESIGN_SEED"
echo "  queue        : $JOB_QUEUE"
echo "  s3 prefix    : $S3_PREFIX"

# JSON rather than key=value shorthand: a point selection is itself
# comma-separated, and the shorthand would read it as further parameters.
PARAMETERS=$(printf '{"design":"%s","shard_count":"%s","trajectories":"%s","seed_shards":"%s","only_points":"%s","sobol_m":"%s","seeds":"%s","design_seed":"%s","s3_prefix":"%s"}' \
  "$DESIGN" "$SHARD_COUNT" "$TRAJECTORIES" "$SEED_SHARDS" "$ONLY_POINTS" \
  "$SOBOL_M" "$SEEDS" "$DESIGN_SEED" "$S3_PREFIX")

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$SHARD_COUNT" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
