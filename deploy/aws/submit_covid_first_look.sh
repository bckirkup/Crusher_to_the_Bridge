#!/usr/bin/env bash
# Submit one phase of the replicated COVID first look (covid_first_look_v1)
# as an AWS Batch EC2 Spot array.
#
# The design is fixed in picard_framework/runs/covid_first_look_v1_design.json;
# this script only chooses which phase runs and how many cells each array
# child owns. Array size = ceil(phase cells / stride). Every cell uploads its
# own object, so a reclaimed child resumes and the merge
# (tools/fit_covid_theta.py merge) pools cells rather than children.
#
#   fit       : 11 Theta x 20 seeds on Diamond Princess, ~30 min a cell.
#               Default stride 1 -> 220 children.
#   held_out  : 11 Theta x 50 seeds on Greg Mortimer, seconds a cell.
#               Default stride 50 -> 11 children, one Theta's seed set each.
set -euo pipefail

USAGE="usage: submit_covid_first_look.sh <fit|held_out> <bucket> [region] [queue] [job-definition]"
PHASE="${1:?$USAGE}"
BUCKET="${2:?$USAGE}"
AWS_REGION="${3:-us-east-1}"
JOB_QUEUE="${4:-picard-campaign-queue}"
JOB_DEFINITION="${5:-picard-covid-hull}"

case "$PHASE" in
  fit) DEFAULT_STRIDE=1 ;;
  held_out) DEFAULT_STRIDE=50 ;;
  *) echo "$USAGE" >&2; exit 2 ;;
esac
STRIDE="${STRIDE:-$DEFAULT_STRIDE}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/covid_first_look_v1/}"
JOB_NAME="${JOB_NAME:-picard-covid-${PHASE}-$(date +%Y%m%d-%H%M%S)}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARRAY_SIZE="$(cd "$HERE/../.." && python3 -c "
from picard_framework.covid_first_look import enumerate_cells, load_design
cells = [c for c in enumerate_cells(load_design()) if c.phase == '$PHASE']
print(-(-len(cells) // $STRIDE))
")"

echo "Submitting COVID first-look array:"
echo "  name       : $JOB_NAME"
echo "  phase      : $PHASE"
echo "  stride     : $STRIDE cells/child"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  job def    : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"

PARAMETERS=$(printf '{"phase":"%s","stride":"%s","s3_prefix":"%s"}' \
  "$PHASE" "$STRIDE" "$S3_PREFIX")

if [ "$ARRAY_SIZE" -eq 1 ]; then
  ARRAY_ARGS=()
  echo "  (single child: submitted without array properties)"
else
  ARRAY_ARGS=(--array-properties "size=$ARRAY_SIZE")
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
