#!/usr/bin/env bash
# Submit the COVID-TAKEOFF-ATTR-01 takeoff-burn attribution as an AWS Batch
# EC2 Spot array — one child per takeoff seed at the declared Theta.
#
# The design is the v12 stage-2 replay
# (picard_framework/runs/covid_theta_screen_v12_stage2_design.json); the
# array resolves it at THETA and the seed list. Each cell uploads its own
# object under S3_PREFIX and already-uploaded cells are skipped on retry.
set -euo pipefail

USAGE="usage: submit_covid_takeoff_attr.sh <bucket> [region] [queue] [job-definition] [--dry-run]"
DRY_RUN=0
ARGS=()
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=1
  else
    ARGS+=("$arg")
  fi
done
set -- "${ARGS[@]}"
if [ "$DRY_RUN" -eq 1 ] && [ $# -eq 0 ]; then
  BUCKET="dry-run"
else
  BUCKET="${1:?$USAGE}"
fi
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-covid-takeoff-attr}"

STRIDE="${STRIDE:-1}"
THETA="${THETA:-237000000000}"
SEEDS="${SEEDS:-}"           # comma list; empty = all seeds in the design
DESIGN="${DESIGN:-covid_theta_screen_v12_stage2}"
DESIGN_REL="picard_framework/runs/${DESIGN}_design.json"
SHA="${SHA:-$(git rev-parse --short HEAD)}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/covid_takeoff_attr_v1/${SHA}/}"
JOB_NAME="${JOB_NAME:-picard-covid-takeoff-attr-$(date +%Y%m%d-%H%M%S)}"
INDEX_OFFSET="${INDEX_OFFSET:-0}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${ARRAY_SIZE:-}" ]; then
  ARRAY_SIZE="$(cd "$HERE/../.." && python3 -c "
from picard_framework.covid_boarding_screen import enumerate_cells, load_design
design = load_design('$DESIGN_REL')
cells = [c for c in enumerate_cells(design)
         if abs(c.theta - $THETA) < $THETA * 0.001]
seeds = '$SEEDS'
if seeds:
    wanted = {int(s) for s in seeds.split(',')}
    cells = [c for c in cells if c.seed in wanted]
assert cells, 'no cells'
print(-(-len(cells) // $STRIDE))
")"
fi

echo "Submitting COVID takeoff-attribution array:"
echo "  name       : $JOB_NAME"
echo "  design     : $DESIGN"
echo "  theta      : $THETA"
echo "  seeds      : ${SEEDS:-all}"
echo "  stride     : $STRIDE cells/child"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  job def    : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"
echo "  index off. : $INDEX_OFFSET"

PARAMETERS=$(printf '{"stride":"%s","s3_prefix":"%s","design":"%s","index_offset":"%s","theta":"%s","seeds":"%s"}' \
  "$STRIDE" "$S3_PREFIX" "$DESIGN_REL" "$INDEX_OFFSET" "$THETA" "$SEEDS")

if [ "$ARRAY_SIZE" -eq 1 ]; then
  ARRAY_ARGS=()
  echo "  (single child: submitted without array properties)"
else
  ARRAY_ARGS=(--array-properties "size=$ARRAY_SIZE")
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "  (dry run: nothing submitted)"
  exit 0
fi

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  "${ARRAY_ARGS[@]}" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
