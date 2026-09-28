#!/usr/bin/env bash
# Submit one NORO-IMPORT-01 tier as an AWS Batch array.
#
# One submission per tier (TIER env, required): child i runs the tier's
# runs[i] through growth_chain_census.py and uploads one run zip under
# S3_PREFIX/<tier>/<run_id>.zip. Tiers are the design's arm families:
# *_scr (screening comparator: Axis A prevalence pairs x Axis B),
# *_ren (renewal: Axis C stream off/on x Axis B), and the expedition-12d
# flag/dose/alpha cells.
#
# Canary: SIZE + INDEX_OFFSET pick a run range inside one cell, e.g. the
# midpoint cell of fl_spr_12d_scr is runs 600-799 (nsf29 x bp32p5c18p5,
# seeds 8105+) and of fl_exp_12d_ren is runs 3000-3999 (reportable x
# nsf29). A single (non-array) job with --index runs exactly one run.
set -euo pipefail

USAGE="usage: submit_import.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-import-map}"

TIER="${TIER:?'set TIER to a manifest tier id (e.g. fl_exp_12d_ren)'}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_import_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_import_01/}"
JOB_NAME="${JOB_NAME:-picard-import-${TIER}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3}"
ARRAY_SIZE="$("${PYTHON_BIN}" - "${MANIFEST}" "${TIER}" <<'PYEOF'
import json, sys
sys.path.insert(0, 'picard_framework/runs/mega_cruise_campaign')
from campaign_runner import generate_tier_runs
manifest = json.load(open(sys.argv[1]))
print(len(list(generate_tier_runs(manifest, sys.argv[2]))))
PYEOF
)"
# Optional canary slicing: SIZE caps the array below the full tier size and
# INDEX_OFFSET shifts the window (run at offset + array index).
SIZE="${SIZE:-$ARRAY_SIZE}"
OFFSET="${INDEX_OFFSET:-0}"

echo "Submitting import-map array:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  tier        : $TIER (size $SIZE of $ARRAY_SIZE, offset $OFFSET)"
echo "  pathogen    : $PATHOGEN_ID"
echo "  prefix      : $S3_PREFIX"
echo "  queue       : $JOB_QUEUE"
echo "  jobdef      : $JOB_DEFINITION"

if [ "$SIZE" -le 1 ]; then
  # Non-array job: the array-index env var is reserved on Batch, so the
  # run index travels as a parameter the entrypoint reads via --index.
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,tier=$TIER,index=$OFFSET"
else
  aws batch submit-job \
    --region "$AWS_REGION" \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --array-properties "{\"size\": $SIZE}" \
    --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,tier=$TIER,index_offset=$OFFSET"
fi
