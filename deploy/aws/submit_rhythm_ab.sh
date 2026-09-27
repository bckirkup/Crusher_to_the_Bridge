#!/usr/bin/env bash
# Submit the NORO-RHYTHM-01 paired A/B campaign as AWS Batch EC2 Spot arrays.
#
# One submission per arm (ARM=off|on): child i runs the (tier, index-in-tier)
# pair rhythm_ab_entrypoint maps it to across the manifest's declared tiers
# (fl_exp_7d + fl_exp_12d + fl_spr_12d + fl_cls_12d + fl_mega_12d) and uploads
# one run zip per spec under S3_PREFIX/<arm>/<tier>/<run_id>.zip. The zip
# carries summary.json in the campaign layout (score_anchors reads it
# directly) plus rhythm.json.gz with the landing partition, acquisition
# pedigree, per-epoch occupancy, dealt-day commitments and state digests.
#
# Canary runs are single (non-array) jobs whose container override passes
# --index <flat cell index>; the array-index env var is reserved on Batch.
set -euo pipefail

USAGE="usage: submit_rhythm_ab.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-rhythm-ab}"

ARM="${ARM:?'set ARM=off or ARM=on'}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_rhythm_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_rhythm_01/}"
JOB_NAME="${JOB_NAME:-picard-rhythm-ab-${ARM}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

# Array size is the sum of the declared tiers' run counts. The count needs
# the project venv.
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3}"
ARRAY_SIZE="$("${PYTHON_BIN}" - "${MANIFEST}" <<'PYEOF'
import json, sys
sys.path.insert(0, 'picard_framework/runs/mega_cruise_campaign')
from campaign_runner import generate_tier_runs
manifest = json.load(open(sys.argv[1]))
print(sum(len(list(generate_tier_runs(manifest, t)))
          for t in ('fl_exp_7d', 'fl_exp_12d', 'fl_spr_12d',
                    'fl_cls_12d', 'fl_mega_12d')))
PYEOF
)"

echo "Submitting rhythm A/B ${ARM} array:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  arm         : $ARM"
echo "  tiers       : fl_exp_7d + fl_exp_12d + fl_spr_12d + fl_cls_12d + fl_mega_12d (array size $ARRAY_SIZE)"
echo "  pathogen    : $PATHOGEN_ID"
echo "  prefix      : $S3_PREFIX"
echo "  queue       : $JOB_QUEUE"
echo "  jobdef      : $JOB_DEFINITION"

aws batch submit-job \
  --region "$AWS_REGION" \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "{\"size\": $ARRAY_SIZE}" \
  --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID,arm=$ARM"
