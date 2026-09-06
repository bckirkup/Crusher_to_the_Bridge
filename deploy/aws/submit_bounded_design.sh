#!/usr/bin/env bash
# Submit one bounded design (Morris screen or feasibility gate) as an AWS Batch
# EC2 Spot array. The array size is the shard count: shard i evaluates the
# design units congruent to i, and the shards pool afterwards through the
# design's own merge step (bounded_screen.py --mode merge,
# admissible_region.py --merge). A shard is not a verdict.
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
echo "  sobol m      : $SOBOL_M (region)"
echo "  seeds/point  : $SEEDS"
echo "  design seed  : $DESIGN_SEED"
echo "  queue        : $JOB_QUEUE"
echo "  s3 prefix    : $S3_PREFIX"

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$SHARD_COUNT" \
  --parameters "design=$DESIGN,shard_count=$SHARD_COUNT,trajectories=$TRAJECTORIES,sobol_m=$SOBOL_M,seeds=$SEEDS,design_seed=$DESIGN_SEED,s3_prefix=$S3_PREFIX" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
