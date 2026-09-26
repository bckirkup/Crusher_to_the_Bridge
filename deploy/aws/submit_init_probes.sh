#!/usr/bin/env bash
# Submit the initiation-probe matrix (COVID-SEED-GEOM-01 + NORO-IMPORT-YIELD-01)
# as one AWS Batch EC2 Spot array. Array size = len(MATRIX) in
# deploy/aws/init_probe_entrypoint.py — read back by the same import the
# worker uses, so the submitted count can never drift from the experiment.
set -euo pipefail

USAGE="usage: submit_init_probes.sh <bucket> [region] [queue] [job-definition] [--dry-run]"
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
JOB_DEFINITION="${4:-picard-init-probes}"

S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/init_probes_01/}"
JOB_NAME="${JOB_NAME:-picard-init-probes-$(date +%Y%m%d-%H%M%S)}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARRAY_SIZE="$(cd "$HERE/../.." && python3 -c "
import sys
sys.path.insert(0, 'deploy/aws')
from init_probe_entrypoint import MATRIX
print(len(MATRIX))
")"

echo "Submitting initiation-probe array:"
echo "  name       : $JOB_NAME"
echo "  array size : $ARRAY_SIZE"
echo "  queue      : $JOB_QUEUE"
echo "  job def    : $JOB_DEFINITION"
echo "  s3 prefix  : $S3_PREFIX"

PARAMETERS=$(printf '{"s3_prefix":"%s"}' "$S3_PREFIX")

if [ "$DRY_RUN" -eq 1 ]; then
  echo "  (dry run: nothing submitted)"
  exit 0
fi

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws batch submit-job \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "size=$ARRAY_SIZE" \
  --parameters "$PARAMETERS" \
  --region "$AWS_REGION" \
  --query 'jobId' --output text
