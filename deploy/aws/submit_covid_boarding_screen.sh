#!/usr/bin/env bash
# Submit the COVID boarding-axis screen (Phase 1b) as an AWS Batch EC2 Spot
# array.
#
# The design is fixed in picard_framework/runs/<DESIGN>_design.json (DESIGN
# defaults to covid_boarding_screen_v1). Every cell is a full Diamond Princess
# run (~30 min), so the default stride is 1 cell per child. Each cell uploads
# its own object; pool with `tools/fit_covid_theta.py screen`.
set -euo pipefail

USAGE="usage: submit_covid_boarding_screen.sh <bucket> [region] [queue] [job-definition] [--dry-run]"
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
JOB_DEFINITION="${4:-picard-covid-boarding-screen}"

STRIDE="${STRIDE:-1}"
DESIGN="${DESIGN:-covid_boarding_screen_v1}"
DESIGN_REL="picard_framework/runs/${DESIGN}_design.json"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/${DESIGN}/}"
JOB_NAME="${JOB_NAME:-picard-covid-screen-$(date +%Y%m%d-%H%M%S)}"
INDEX_OFFSET="${INDEX_OFFSET:-0}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${ARRAY_SIZE:-}" ]; then
  ARRAY_SIZE="$(cd "$HERE/../.." && python3 -c "
from picard_framework.covid_boarding_screen import enumerate_cells, load_design
design = load_design('$DESIGN_REL')
assert design.design_id == '$DESIGN', design.design_id
print(-(-len(enumerate_cells(design)) // $STRIDE))
")"
fi

echo "Submitting COVID boarding-screen array:"
echo "  name       : $JOB_NAME"
echo "  design     : $DESIGN"
echo "  stride     : $STRIDE cells/child"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  job def    : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"
echo "  index off. : $INDEX_OFFSET"

PARAMETERS=$(printf '{"stride":"%s","s3_prefix":"%s","design":"%s","index_offset":"%s"}' \
  "$STRIDE" "$S3_PREFIX" "$DESIGN_REL" "$INDEX_OFFSET")

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
