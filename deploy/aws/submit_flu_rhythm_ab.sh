#!/usr/bin/env bash
# Submit the FLU-RHYTHM-01 paired A/B campaign as AWS Batch EC2 Spot arrays.
#
# One submission per arm (ARM=off|on): child i runs the (tier, seed) cell
# flu_rhythm_ab_entrypoint maps it to across the manifest's declared tiers
# (flu_exp_12d + flu_spr_12d + flu_cls_12d + flu_mega_12d) and uploads one
# run zip per cell under S3_PREFIX/<arm>/<tier>/s<seed>.zip. The zip carries
# summary.json in the campaign layout plus rhythm.json.gz with the cabin-pair
# challenge table, stage-resolved delivery decomposition, per-epoch dosed
# sets, acquisition pedigree, dealt-day commitments and state digests.
#
# Canary runs are single (non-array) jobs whose container override passes
# --index <flat cell index>; the array-index env var is reserved on Batch.
set -euo pipefail

USAGE="usage: submit_flu_rhythm_ab.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-flu-rhythm-ab}"

ARM="${ARM:?'set ARM=off or ARM=on'}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/flu_rhythm_01_manifest.json}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/flu_rhythm_01/}"
JOB_NAME="${JOB_NAME:-picard-flu-rhythm-ab-${ARM}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

# Array size is the sum of the declared tiers' cell counts.
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3}"
ARRAY_SIZE="$("${PYTHON_BIN}" - "${MANIFEST}" <<'PYEOF'
import json, sys
manifest = json.load(open(sys.argv[1]))
print(sum(int(t["seeds"]["count"]) for t in manifest["tiers"].values()))
PYEOF
)"

echo "Submitting flu rhythm A/B ${ARM} array:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  arm         : $ARM"
echo "  tiers       : flu_exp_12d + flu_spr_12d + flu_cls_12d + flu_mega_12d (array size $ARRAY_SIZE)"
echo "  pathogen    : influenza_a (k=0.0006 shipped, no overrides)"
echo "  prefix      : $S3_PREFIX"
echo "  queue       : $JOB_QUEUE"
echo "  jobdef      : $JOB_DEFINITION"

aws batch submit-job \
  --region "$AWS_REGION" \
  --job-name "$JOB_NAME" \
  --job-queue "$JOB_QUEUE" \
  --job-definition "$JOB_DEFINITION" \
  --array-properties "{\"size\": $ARRAY_SIZE}" \
  --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,arm=$ARM"
