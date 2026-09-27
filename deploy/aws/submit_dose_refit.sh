#!/usr/bin/env bash
# Submit the NORO-DOSE-REFIT-01 canary as an AWS Batch EC2 Spot array.
# Child i runs the (tier, index-in-tier) pair dose_refit_entrypoint maps it
# to across the manifest's declared tiers (fl_spr_12d then fl_mega_12d,
# 60 seeds each -> 120 children) and uploads one run zip per spec under
# S3_PREFIX/<tier>/<run_id>.zip. The zip carries summary.json in the
# campaign layout (score_anchors reads it directly) plus refit.json with
# the per-host emesis schedule/emit records and deposit callsite totals.
set -euo pipefail

USAGE="usage: submit_dose_refit.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-dose-refit}"

MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_dose_refit_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_dose_refit_01/}"
JOB_NAME="${JOB_NAME:-picard-dose-refit-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

# Array size is the sum of the declared tiers' run counts (the smoke tier is
# excluded by the entrypoint's _TIERS). The count needs the project venv.
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3}"
ARRAY_SIZE="$("${PYTHON_BIN}" - "${MANIFEST}" <<'PYEOF'
import json, sys
sys.path.insert(0, 'picard_framework/runs/mega_cruise_campaign')
from campaign_runner import generate_tier_runs
manifest = json.load(open(sys.argv[1]))
print(sum(len(list(generate_tier_runs(manifest, t)))
          for t in ('fl_spr_12d', 'fl_mega_12d')))
PYEOF
)"

echo "Submitting dose-refit canary:"
echo "  name        : $JOB_NAME"
echo "  manifest    : $MANIFEST"
echo "  tiers       : fl_spr_12d + fl_mega_12d (array size $ARRAY_SIZE)"
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
  --parameters "s3_prefix=$S3_PREFIX,manifest=$MANIFEST,pathogen_id=$PATHOGEN_ID"
