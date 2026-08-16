#!/usr/bin/env bash
set -euo pipefail

RUNG_IDS="${1:?usage: submit_sentinel_nuts.sh <rung[,rung...]> <bucket> [region] [queue] [job-definition]}"
BUCKET="${2:?usage: submit_sentinel_nuts.sh <rung[,rung...]> <bucket> [region] [queue] [job-definition]}"
REGION="${3:-us-east-1}"
JOB_QUEUE="${4:-picard-analysis-queue}"
JOB_DEFINITION="${5:-picard-sentinel-nuts}"
S3_PREFIX="s3://${BUCKET}/sentinel/nuts_ladder_v1/"
JOB_NAME="${JOB_NAME:-picard-sentinel-nuts-${RUNG_IDS//,/-}-$(date +%Y%m%d-%H%M%S)}"

ARRAY_SIZE="$(PYTHONPATH=. python3 - "$RUNG_IDS" <<'PY'
import sys
from picard_framework.analysis.sentinel.design_nuts import enumerate_cells, load_ladder

requested = set(sys.argv[1].split(","))
cells = [cell for cell in enumerate_cells(load_ladder()) if cell["rung"] in requested]
if not cells:
    raise SystemExit("No cells selected for requested rung ids")
print(len(cells))
PY
)"

echo "Submitting Sentinel NUTS array:"
echo "  name       : $JOB_NAME"
echo "  rungs      : $RUNG_IDS"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  definition : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "rungs=$RUNG_IDS,s3_prefix=$S3_PREFIX" \
  --region "$REGION" \
  --query 'jobId' --output text
