#!/usr/bin/env bash
# Submit the COVID-RHYTHM-01 rhythm-layer A/B as an AWS Batch EC2 Spot array —
# one child per cell of the declared design (4 classes x 2 arms x 20 seeds).
#
# The design is picard_framework/runs/covid_rhythm_ab_v1_design.json; each
# cell uploads its own object under S3_PREFIX and already-uploaded cells are
# skipped on retry. Use --index via a single (non-array) submit for the
# canary: ARRAY_SIZE=1 INDEX_OVERRIDE=<n> runs exactly that cell.
set -euo pipefail

USAGE="usage: submit_covid_rhythm_ab.sh <bucket> [region] [queue] [job-definition] [--dry-run]"
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
JOB_DEFINITION="${4:-picard-covid-rhythm-ab}"

STRIDE="${STRIDE:-1}"
DESIGN="${DESIGN:-covid_rhythm_ab_v1}"
DESIGN_REL="picard_framework/runs/${DESIGN}_design.json"
SHA="${SHA:-$(git rev-parse --short HEAD)}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/covid_rhythm_ab_v1/${SHA}/}"
JOB_NAME="${JOB_NAME:-picard-covid-rhythm-ab-$(date +%Y%m%d-%H%M%S)}"
INDEX_OFFSET="${INDEX_OFFSET:-0}"
INDEX_OVERRIDE="${INDEX_OVERRIDE:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${ARRAY_SIZE:-}" ]; then
  ARRAY_SIZE="$(cd "$HERE/../.." && python3 -c "
from picard_framework.covid_rhythm_cells import enumerate_rhythm_cells, load_rhythm_design
design = load_rhythm_design('$DESIGN_REL')
cells = list(enumerate_rhythm_cells(design))
assert cells, 'no cells'
print(-(-len(cells) // $STRIDE))
")"
fi

echo "Submitting COVID rhythm-A/B array:"
echo "  name       : $JOB_NAME"
echo "  design     : $DESIGN"
echo "  stride     : $STRIDE cells/child"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  job def    : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"
echo "  index off. : $INDEX_OFFSET"
echo "  index      : ${INDEX_OVERRIDE:-<array>}"

PARAMETERS=$(printf '{"stride":"%s","s3_prefix":"%s","design":"%s","index_offset":"%s"}' \
  "$STRIDE" "$S3_PREFIX" "$DESIGN_REL" "$INDEX_OFFSET")

OVERRIDES=()
if [ -n "$INDEX_OVERRIDE" ]; then
  # The canary pins one cell: AWS_BATCH_JOB_ARRAY_INDEX is reserved, so the
  # worker takes --index via a container-override command instead.
  OVERRIDES=(--container-overrides
    "command=[deploy/aws/covid_rhythm_ab_entrypoint.py,--stride,$STRIDE,--s3-prefix,$S3_PREFIX,--design,$DESIGN_REL,--index,$INDEX_OVERRIDE]")
  ARRAY_ARGS=()
  echo "  (canary: --index $INDEX_OVERRIDE, submitted without array properties)"
elif [ "$ARRAY_SIZE" -eq 1 ]; then
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
  "${OVERRIDES[@]}" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
