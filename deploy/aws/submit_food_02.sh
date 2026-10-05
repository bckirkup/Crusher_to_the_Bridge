#!/usr/bin/env bash
# Submit one NORO-FOOD-02 cell as an AWS Batch array.
#
# One submission per (hull, rung) cell: child i runs tier
# fl_{exp,cls,spr}_12d_scr_l{1..4} at seeds[i] through
# import_map_entrypoint.py (jobdef picard-noro-food-02 embeds the
# manifest and the common_source param-map patch in its -c bootstrap)
# and uploads S3_PREFIX/<tier>/<run_id>.zip.
#
# Required env: TIER (manifest tier id), SIZE (array size = seed count).
# Optional env: INDEX_OFFSET (default 0), MANIFEST, PATHOGEN_ID,
#               S3_PREFIX, JOB_NAME, JOB_QUEUE, JOB_DEFINITION.
set -euo pipefail

USAGE="usage: submit_food_02.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-noro-food-02:1}"

TIER="${TIER:?'set TIER to a manifest tier id (e.g. fl_exp_12d_scr_l2)'}"
SIZE="${SIZE:?'set SIZE to the array size (= seed count)'}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_food_02_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_food_02/}"
JOB_NAME="${JOB_NAME:-picard-food02-${TIER}-$(date +%Y%m%d-%H%M%S)}"
INDEX_OFFSET="${INDEX_OFFSET:-0}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

echo "Submitting food-02 sweep array:"
echo "  name         : $JOB_NAME"
echo "  manifest     : $MANIFEST"
echo "  tier         : $TIER"
echo "  size         : $SIZE"
echo "  index_offset : $INDEX_OFFSET"
echo "  pathogen     : $PATHOGEN_ID"
echo "  prefix       : $S3_PREFIX"
echo "  queue        : $JOB_QUEUE"
echo "  jobdef       : $JOB_DEFINITION"

PARAMS="$(python3 -c '
import json, sys
print(json.dumps({
    "s3_prefix": sys.argv[1], "manifest": sys.argv[2],
    "pathogen_id": sys.argv[3], "tier": sys.argv[4],
    "index": sys.argv[5], "index_offset": sys.argv[6],
}))
' "$S3_PREFIX" "$MANIFEST" "$PATHOGEN_ID" "$TIER" "-1" "$INDEX_OFFSET")"

if [ "$SIZE" -le 1 ]; then
  # Single seed: the array-index env var is reserved on Batch, so the
  # run index travels as a parameter the entrypoint reads via --index.
  PARAMS="$(python3 -c '
import json, sys
p = json.loads(sys.argv[1]); p["index"] = sys.argv[2]; print(json.dumps(p))
' "$PARAMS" "${INDEX:-0}")"
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --parameters "$PARAMS"
else
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --parameters "$PARAMS" \
    --array-properties "size=${SIZE}"
fi
